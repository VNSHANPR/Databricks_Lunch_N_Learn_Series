# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Find Metric-View candidates from your system tables
# MAGIC
# MAGIC > *"Stop circling the drain trying to get alignment."*
# MAGIC
# MAGIC The fastest way to decide **what to turn into a metric view** is to look at what your
# MAGIC organisation **already queries and joins**. Your system tables record this. This
# MAGIC notebook crawls them to surface:
# MAGIC
# MAGIC - **Most-queried / most-referenced tables** → likely gold facts worth a metric view.
# MAGIC - **Most-frequently-joined table pairs** → the natural `joins` in a metric view.
# MAGIC
# MAGIC Then it classifies columns into **measures vs dimensions** and emits a **suggested
# MAGIC metric-view skeleton** you refine in notebook `04`.
# MAGIC
# MAGIC **Note on access:** `system.query.history` and `system.access.table_lineage` must be
# MAGIC enabled by a metastore admin and granted to you. On a brand-new trial they're often
# MAGIC empty — so **Section C is a deterministic fallback** that works on the lab tables you
# MAGIC just built, using only `information_schema`.

# COMMAND ----------

# Read the config written by notebook 00. Serverless rejects custom spark.conf
# keys, so cross-notebook state travels through a JSON file on the lab Volume.
import json

DEFAULT_CATALOG, DEFAULT_SCHEMA = "workspace", "htg_metric_views_lab"
try:
    _cfg = json.loads(dbutils.fs.head(
        f"/Volumes/{DEFAULT_CATALOG}/{DEFAULT_SCHEMA}/raw_files/_htg_config.json"))
except Exception:
    _cfg = {}

dbutils.widgets.text("catalog", _cfg.get("htg.catalog", DEFAULT_CATALOG), "Catalog")
dbutils.widgets.text("schema", _cfg.get("htg.schema", DEFAULT_SCHEMA), "Schema")
dbutils.widgets.text("lookback_days", "90", "System-table lookback (days)")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
LOOKBACK = int(dbutils.widgets.get("lookback_days"))
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")
from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section A — Lineage: most-referenced tables & most-joined pairs
# MAGIC
# MAGIC `system.access.table_lineage` records every (source → target) data flow. Tables that
# MAGIC appear as a **source** most often are heavily consumed (good metric-view bases).
# MAGIC Tables that repeatedly feed the **same target** are being combined — i.e. **joined**.

# COMMAND ----------

HAS_LINEAGE = False
try:
    lineage = (spark.table("system.access.table_lineage")
        .where(F.col("event_date") >= F.date_sub(F.current_date(), LOOKBACK))
        .where(F.col("source_table_full_name").isNotNull()))
    # Exclude system / information_schema noise.
    lineage = lineage.where(~F.col("source_table_full_name").rlike("(?i)(^system\\.|information_schema)"))
    HAS_LINEAGE = lineage.limit(1).count() > 0
except Exception as e:
    print("table_lineage not available:", str(e)[:120])

if HAS_LINEAGE:
    print("Top referenced source tables (metric-view base candidates):")
    most_referenced = (lineage.groupBy("source_table_full_name")
        .agg(F.countDistinct("entity_run_id").alias("times_used"),
             F.countDistinct("target_table_full_name").alias("distinct_targets"))
        .orderBy(F.desc("times_used")))
    display(most_referenced.limit(25))
else:
    print("No lineage data in the lookback window — skipping to Section B/C.")

# COMMAND ----------

if HAS_LINEAGE:
    # Most-joined pairs: two source tables that feed the SAME target are being combined.
    a = lineage.select(F.col("source_table_full_name").alias("tbl_a"),
                       "target_table_full_name", "entity_run_id")
    b = lineage.select(F.col("source_table_full_name").alias("tbl_b"),
                       "target_table_full_name", "entity_run_id")
    pairs = (a.join(b, ["target_table_full_name", "entity_run_id"])
        .where(F.col("tbl_a") < F.col("tbl_b"))            # unordered, no self-pairs
        .groupBy("tbl_a", "tbl_b")
        .agg(F.countDistinct("target_table_full_name").alias("joined_in_n_outputs"))
        .orderBy(F.desc("joined_in_n_outputs")))
    print("Most-frequently-joined table pairs (natural metric-view joins):")
    display(pairs.limit(25))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section B — Query history: most-queried tables & co-queried pairs
# MAGIC
# MAGIC `system.query.history.statement_text` lets us see which tables actually appear in
# MAGIC `FROM` / `JOIN` clauses. Tables that co-occur in the same statement are being joined
# MAGIC by analysts right now — a very direct candidate signal.

# COMMAND ----------

HAS_HISTORY = False
try:
    qh = (spark.table("system.query.history")
        .where(F.col("start_time") >= F.date_sub(F.current_timestamp(), LOOKBACK))
        .where(F.col("statement_type") == "SELECT")
        .where(F.col("statement_text").isNotNull()))
    HAS_HISTORY = qh.limit(1).count() > 0
except Exception as e:
    print("query.history not available:", str(e)[:120])

if HAS_HISTORY:
    # Pull table-like tokens after FROM / JOIN. Illustrative regex (good enough for triage).
    tbl_regex = r"(?i)(?:from|join)\s+([a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+)"
    refs = (qh.select("statement_id",
                      F.expr(f"regexp_extract_all(statement_text, '{tbl_regex}', 1)").alias("tables"))
        .where(F.size("tables") > 0))
    exploded = (refs.select("statement_id", F.explode("tables").alias("tbl"))
        .where(~F.col("tbl").rlike("(?i)(^system\\.|information_schema)")))

    print("Most-queried tables:")
    display(exploded.groupBy("tbl").agg(F.countDistinct("statement_id").alias("n_queries"))
            .orderBy(F.desc("n_queries")).limit(25))

    # Co-queried pairs within the same statement = join candidates.
    x = exploded.select("statement_id", F.col("tbl").alias("a"))
    y = exploded.select("statement_id", F.col("tbl").alias("b"))
    coq = (x.join(y, "statement_id").where(F.col("a") < F.col("b"))
        .groupBy("a", "b").agg(F.countDistinct("statement_id").alias("co_queried_in_n"))
        .orderBy(F.desc("co_queried_in_n")))
    print("Most co-queried (joined) table pairs:")
    display(coq.limit(25))
else:
    print("No query history in the lookback window — use Section C.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section C — Deterministic fallback (always works on the lab schema)
# MAGIC
# MAGIC No system-table history yet? We can still find candidates from the model itself:
# MAGIC **FK constraints = join candidates**, and a **column-type heuristic** classifies
# MAGIC each column into *measure* vs *dimension*.

# COMMAND ----------

# Join candidates from declared foreign keys in this schema.
print("Declared relationships (join candidates) in", FQ, ":")
fks = spark.sql(f"""
    SELECT kcu.table_name          AS fact_table,
           kcu.column_name         AS fk_column,
           ccu.table_name          AS references_table,
           ccu.column_name         AS references_column
    FROM {CATALOG}.information_schema.referential_constraints rc
    JOIN {CATALOG}.information_schema.key_column_usage kcu
      ON rc.constraint_name = kcu.constraint_name
     AND kcu.table_schema = '{SCHEMA}'
    JOIN {CATALOG}.information_schema.constraint_column_usage ccu
      ON rc.unique_constraint_name = ccu.constraint_name
     AND ccu.table_schema = '{SCHEMA}'
""")
display(fks)

# COMMAND ----------

# Column classification heuristic for the chosen fact table.
FACT = f"{FQ}.fact_bookings"
cols = spark.sql(f"""
    SELECT column_name, data_type
    FROM {CATALOG}.information_schema.columns
    WHERE table_schema = '{SCHEMA}' AND table_name = 'fact_bookings'
""").collect()

measure_like = ("value", "amount", "price", "cost", "revenue", "commission",
                "refund", "qty", "quantity", "count", "pax", "fee", "ttv")
measures, dimensions = [], []
for r in cols:
    name, dtype = r["column_name"].lower(), r["data_type"].upper()
    is_numeric = any(t in dtype for t in ("INT", "DECIMAL", "DOUBLE", "FLOAT", "LONG", "BIGINT"))
    if is_numeric and any(k in name for k in measure_like) and not name.endswith("_id"):
        measures.append(r["column_name"])
    elif name.endswith("_id") or "DATE" in dtype or "STRING" in dtype:
        dimensions.append(r["column_name"])

print("Suggested MEASURES :", measures)
print("Suggested DIMENSIONS:", dimensions)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section D — Auto-suggested metric-view skeleton
# MAGIC
# MAGIC Combine the findings — fact base + FK joins + classified columns — into a starter
# MAGIC YAML. This is the *draft* you hand to the business to ratify, then flesh out in `04`.

# COMMAND ----------

skeleton = f"""version: 1.1
comment: "AUTO-SUGGESTED from candidate discovery — review & refine in notebook 04"
source: {FQ}.fact_bookings
joins:
  - name: customer
    source: {FQ}.dim_customer
    on: source.customer_id = customer.customer_id
  - name: destination
    source: {FQ}.dim_destination
    on: source.destination_id = destination.destination_id
  - name: product
    source: {FQ}.dim_product
    on: source.product_id = product.product_id
dimensions:
  - name: Booking Date
    expr: source.booking_date
  - name: Destination Region
    expr: destination.destination_region
  - name: Product Type
    expr: product.product_type
  - name: Customer Segment
    expr: customer.customer_segment
measures:
  - name: Total TTV
    expr: SUM(source.gross_booking_value)
  - name: Total Commission
    expr: SUM(source.commission_amount)
  - name: Booking Count
    expr: COUNT(1)
"""
print(skeleton)

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ You now have a data-driven shortlist and a starter view. In **`04_build_metric_views`**
# MAGIC we turn this into a production-grade, AI-ready metric view with filters, ratios,
# MAGIC window measures and agentic metadata.
