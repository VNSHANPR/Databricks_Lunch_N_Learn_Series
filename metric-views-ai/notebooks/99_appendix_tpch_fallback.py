# Databricks notebook source
# MAGIC %md
# MAGIC # 99 · Appendix — Zero-setup fallback on `samples.tpch`
# MAGIC
# MAGIC `samples.tpch` exists on **every** Databricks workspace. If someone can't ingest the
# MAGIC CSV (volume/permissions/compute), run this so they still build and query a real metric
# MAGIC view with joins, filters and ratios. No setup required beyond a catalog/schema you can
# MAGIC write to.

# COMMAND ----------

# Catalog & schema come from notebook 00's config if present. This appendix also runs
# standalone, so if 00 wasn't run we fall back to the current catalog + the lab schema and
# create it. Either way, no per-notebook catalog/schema widget to keep in sync.
import json

LAB_SCHEMA = "htg_metric_views_lab"   # lab's fixed schema name — used to locate 00's config / as fallback

def _read_lab_cfg():
    cats = []
    try:
        cats.append(spark.sql("SELECT current_catalog()").first()[0])
    except Exception:
        pass
    try:
        cats += [r[0] for r in spark.sql("SHOW CATALOGS").collect()]
    except Exception:
        pass
    for cat in dict.fromkeys(cats):
        try:
            return json.loads(dbutils.fs.head(
                f"/Volumes/{cat}/{LAB_SCHEMA}/raw_files/_htg_config.json"))
        except Exception:
            continue
    return None

_cfg = _read_lab_cfg()
if _cfg:
    CATALOG, SCHEMA = _cfg["htg.catalog"], _cfg["htg.schema"]
else:
    try:
        CATALOG = spark.sql("SELECT current_catalog()").first()[0]
    except Exception:
        CATALOG = "workspace"
    SCHEMA = LAB_SCHEMA
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")
print(f"Using {FQ}")

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
