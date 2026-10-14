# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze → Silver
# MAGIC
# MAGIC Notebook `00` landed the raw bookings into a **Bronze streaming table**
# MAGIC (`bookings_bronze`) with Auto Loader. Here we shape a clean, typed **Silver** table.
# MAGIC This mirrors what you'd do in the **Lakeflow Designer** visual data-prep canvas — we do
# MAGIC it in code so it runs the same on every workspace (see the callout for the no-code path).

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
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Peek at Bronze
# MAGIC
# MAGIC Bronze is the raw, as-landed data (plus Auto Loader's `_rescued_data` column and our
# MAGIC ingestion metadata). We leave it untouched and derive Silver from it.

# COMMAND ----------

from pyspark.sql import functions as F

print("bronze rows:", spark.table(f"{FQ}.bookings_bronze").count())
display(spark.table(f"{FQ}.bookings_bronze").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 💡 The no-code alternative: Lakeflow Designer (presenter demo)
# MAGIC
# MAGIC Everything in this notebook — and the Auto Loader ingest in `00` — can be built
# MAGIC visually in **Lakeflow Designer**:
# MAGIC
# MAGIC 1. **New → ETL Pipeline → Designer (visual)**.
# MAGIC 2. **Add source** → point at the `landing/` Volume folder (Designer uses Auto Loader
# MAGIC    under the hood for incremental file ingestion).
# MAGIC 3. Drag **Clean / Cast** steps: trim strings, cast `booking_date` / `travel_date`
# MAGIC    to `DATE`, cast money columns to `DECIMAL`.
# MAGIC 4. Drag a **Filter** to drop rows with a null `booking_id`.
# MAGIC 5. **Publish** the result as `bookings_silver` in your schema.
# MAGIC
# MAGIC Designer generates the same Lakeflow Spark Declarative Pipeline under the hood —
# MAGIC great for the "data engineer who doesn't want to write Spark" persona. We use code
# MAGIC below so the lab is deterministic on every workspace.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver — clean & type
# MAGIC
# MAGIC Cast dates and money, trim text, standardise the free-text comment field, and drop the
# MAGIC Bronze bookkeeping columns (`_rescued_data`, ingestion metadata).

# COMMAND ----------

silver = (
    spark.table(f"{FQ}.bookings_bronze")
    .withColumn("booking_date", F.to_date("booking_date"))
    .withColumn("travel_date", F.to_date("travel_date"))
    .withColumn("gross_booking_value", F.col("gross_booking_value").cast("decimal(12,2)"))
    .withColumn("commission_amount", F.col("commission_amount").cast("decimal(12,2)"))
    .withColumn("refund_amount", F.col("refund_amount").cast("decimal(12,2)"))
    .withColumn("customer_comments", F.when(F.trim(F.col("customer_comments")) == "", None)
                                       .otherwise(F.trim(F.col("customer_comments"))))
    .filter(F.col("booking_id").isNotNull())
    .drop("_ingested_at", "_source_file", "_rescued_data")
)

(silver.write.mode("overwrite").option("overwriteSchema", True)
    .saveAsTable(f"{FQ}.bookings_silver"))

print("silver rows:", spark.table(f"{FQ}.bookings_silver").count())
display(spark.table(f"{FQ}.bookings_silver").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Silver is ready. Continue to **`02_build_gold_star_schema`**.
