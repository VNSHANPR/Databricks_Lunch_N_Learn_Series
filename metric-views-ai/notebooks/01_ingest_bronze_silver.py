# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze → Silver
# MAGIC
# MAGIC Notebook `00` landed the raw bookings into a **Bronze streaming table**
# MAGIC (`bookings_bronze`) with Auto Loader. Here we shape a clean, typed **Silver** table.
# MAGIC This mirrors what you'd do in the **Lakeflow Designer** visual data-prep canvas — we do
# MAGIC it in code so it runs the same on every workspace (see the callout for the no-code path).

# COMMAND ----------

# Catalog & schema are chosen ONCE in notebook 00 (its widgets) and recorded in a small
# JSON config on the lab Volume. Downstream notebooks READ that config — they define no
# catalog/schema of their own, so there's nothing to keep in sync. We locate the config by
# scanning the catalogs you can see for the lab schema's config file.
import json

LAB_SCHEMA = "htg_metric_views_lab"   # lab's fixed schema name — used only to locate 00's config

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
assert _cfg, ("Lab config not found — run 00_setup first. It picks the catalog/schema and "
              "writes _htg_config.json on the lab Volume, which every downstream notebook reads.")
CATALOG, SCHEMA = _cfg["htg.catalog"], _cfg["htg.schema"]
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")
print(f"Using {FQ} (from 00_setup config)")

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
# MAGIC ### 🏭 In production, Silver is a **Streaming Table** too
# MAGIC
# MAGIC Here we rebuild Silver with a full `overwrite` each run — simple and deterministic for a
# MAGIC lab, but it reprocesses *everything* every time and only refreshes when you run the cell.
# MAGIC In production you make Silver **incremental**: a Streaming Table that reads a **stream**
# MAGIC from Bronze and applies these same per-row casts/cleaning, so it stays in sync
# MAGIC automatically — no full recompute. Declaratively (serverless / Lakeflow pipeline):
# MAGIC
# MAGIC ```sql
# MAGIC CREATE OR REFRESH STREAMING TABLE bookings_silver
# MAGIC   (CONSTRAINT valid_booking EXPECT (booking_id IS NOT NULL) ON VIOLATION DROP ROW)
# MAGIC AS SELECT
# MAGIC      booking_id,
# MAGIC      to_date(booking_date) AS booking_date,
# MAGIC      CAST(gross_booking_value AS DECIMAL(12,2)) AS gross_booking_value,
# MAGIC      NULLIF(TRIM(customer_comments), '') AS customer_comments
# MAGIC      -- …the rest of the columns / casts…
# MAGIC FROM STREAM(bookings_bronze);
# MAGIC ```
# MAGIC
# MAGIC The full Bronze → Silver → Gold streaming version is in **`06_production_pipeline`**.

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Silver is ready. Continue to **`02_build_gold_star_schema`**.
