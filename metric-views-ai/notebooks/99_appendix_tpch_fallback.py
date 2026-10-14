# Databricks notebook source
# MAGIC %md
# MAGIC # 99 · Appendix — Zero-setup fallback on `samples.tpch`
# MAGIC
# MAGIC `samples.tpch` exists on **every** Databricks workspace. If someone can't ingest the
# MAGIC CSV (volume/permissions/compute), run this so they still build and query a real metric
# MAGIC view with joins, filters and ratios. No setup required beyond a catalog/schema you can
# MAGIC write to.

# COMMAND ----------

# Read the config written by notebook 00 if present (this appendix also runs
# standalone). Serverless rejects custom spark.conf keys, so we read a JSON file.
import json

DEFAULT_CATALOG, DEFAULT_SCHEMA = "workspace", "htg_metric_views_lab"
try:
    _cfg = json.loads(dbutils.fs.head(
        f"/Volumes/{DEFAULT_CATALOG}/{DEFAULT_SCHEMA}/raw_files/_htg_config.json"))
except Exception:
    _cfg = {}

dbutils.widgets.text("catalog", _cfg.get("htg.catalog", DEFAULT_CATALOG), "Catalog")
dbutils.widgets.text("schema", _cfg.get("htg.schema", DEFAULT_SCHEMA), "Schema")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {FQ}.mv_tpch_orders
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "TPC-H orders KPIs — demo metric view (zero setup)"
source: samples.tpch.orders

joins:
  - name: customer
    source: samples.tpch.customer
    on: source.o_custkey = customer.c_custkey

dimensions:
  - name: Order Month
    expr: DATE_TRUNC('MONTH', source.o_orderdate)
    synonyms: [month]
  - name: Order Status
    expr: CASE WHEN source.o_orderstatus = 'O' THEN 'Open'
               WHEN source.o_orderstatus = 'P' THEN 'Processing'
               WHEN source.o_orderstatus = 'F' THEN 'Fulfilled' END
    synonyms: [status]
  - name: Market Segment
    expr: customer.c_mktsegment
    synonyms: [segment, market]

measures:
  - name: Order Count
    expr: COUNT(1)
    format: {{ type: number, decimal_places: {{ type: exact, places: 0 }} }}
  - name: Total Revenue
    expr: SUM(source.o_totalprice)
    synonyms: [revenue, sales, turnover]
    format: {{ type: currency, currency_code: USD, decimal_places: {{ type: exact, places: 0 }} }}
  - name: Revenue per Customer
    expr: SUM(source.o_totalprice) / COUNT(DISTINCT source.o_custkey)
    format: {{ type: currency, currency_code: USD, decimal_places: {{ type: exact, places: 0 }} }}
  - name: Open Order Revenue
    expr: SUM(source.o_totalprice) FILTER (WHERE source.o_orderstatus = 'O')
    comment: "Revenue tied up in open orders"
    format: {{ type: currency, currency_code: USD, decimal_places: {{ type: exact, places: 0 }} }}
$$
""")
print("Created", f"{FQ}.mv_tpch_orders")

# COMMAND ----------

display(spark.sql(f"""
  SELECT `Market Segment`,
         MEASURE(`Total Revenue`)        AS revenue,
         MEASURE(`Order Count`)          AS orders,
         MEASURE(`Revenue per Customer`) AS rev_per_cust
  FROM {FQ}.mv_tpch_orders
  GROUP BY ALL
  ORDER BY revenue DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Same concepts as the HTG lab — joins, filtered measures, ratios, agentic metadata —
# MAGIC on data that's guaranteed to be present.
