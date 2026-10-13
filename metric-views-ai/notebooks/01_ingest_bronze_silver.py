# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Ingest → Bronze → Silver
# MAGIC
# MAGIC We land the raw CSV, then shape a clean, typed **silver** table. This mirrors what
# MAGIC you'd do in the **Lakeflow Designer** visual data-prep canvas — we do it in code here
# MAGIC so it runs the same on every workspace (see the callout for the no-code path).

# COMMAND ----------

dbutils.widgets.text("catalog", spark.conf.get("htg.catalog", "workspace"), "Catalog")
dbutils.widgets.text("schema", spark.conf.get("htg.schema", "htg_metric_views_lab"), "Schema")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# Resolve the CSV path saved by notebook 00 (fall back to the usual repo location).
import os
CSV_PATH = spark.conf.get("htg.csv_path", "")
if not CSV_PATH:
    guess = os.path.abspath(os.path.join(os.getcwd(), "..", "data", "htg_bookings_raw.csv"))
    CSV_PATH = guess if os.path.exists(guess) else f"/Volumes/{CATALOG}/{SCHEMA}/raw_files/htg_bookings_raw.csv"
print("Reading:", CSV_PATH)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze — land the raw file as-is
# MAGIC
# MAGIC Read with the schema inferred, keep everything, add simple ingestion metadata.

# COMMAND ----------

from pyspark.sql import functions as F

bronze = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(CSV_PATH)
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source_file", F.lit(os.path.basename(CSV_PATH)))
)

(bronze.write.mode("overwrite").option("overwriteSchema", True)
    .saveAsTable(f"{FQ}.bookings_bronze"))

print("bronze rows:", spark.table(f"{FQ}.bookings_bronze").count())
display(spark.table(f"{FQ}.bookings_bronze").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 💡 The no-code alternative: Lakeflow Designer (presenter demo)
# MAGIC
# MAGIC Everything in this notebook can be built visually in **Lakeflow Designer**:
# MAGIC
# MAGIC 1. **New → ETL Pipeline → Designer (visual)**.
# MAGIC 2. **Add source** → point at the `htg_bookings_raw.csv` Volume file.
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
# MAGIC Cast dates and money, trim text, and standardise the free-text comment field.

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
    .drop("_ingested_at", "_source_file")
)

(silver.write.mode("overwrite").option("overwriteSchema", True)
    .saveAsTable(f"{FQ}.bookings_silver"))

print("silver rows:", spark.table(f"{FQ}.bookings_silver").count())
display(spark.table(f"{FQ}.bookings_silver").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Silver is ready. Continue to **`02_build_gold_star_schema`**.
