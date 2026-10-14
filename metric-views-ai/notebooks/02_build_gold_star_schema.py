# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Build the Gold star schema
# MAGIC
# MAGIC From the denormalised `bookings_silver` we carve a classic **star schema**:
# MAGIC a `fact_bookings` table plus conformed dimensions. We also declare **primary- and
# MAGIC foreign-key constraints** — not just for correctness, but because they power
# MAGIC the metric-view **join optimiser** *and* the candidate-discovery heuristics in
# MAGIC notebook `03`.

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

from pyspark.sql import functions as F
silver = spark.table(f"{FQ}.bookings_silver")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dimensions

# COMMAND ----------

# dim_customer
dim_customer = (silver.select(
        "customer_id", "customer_name", "customer_segment",
        "loyalty_tier", "home_city", "home_country")
    .dropDuplicates(["customer_id"]))
dim_customer.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.dim_customer")

# dim_destination
dim_destination = (silver.select(
        "destination_id", "destination_city", "destination_country", "destination_region")
    .dropDuplicates(["destination_id"]))
dim_destination.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.dim_destination")

# dim_product
dim_product = (silver.select("product_id", "product_type", "brand")
    .dropDuplicates(["product_id"]))
dim_product.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.dim_product")

# dim_date (built from the booking + travel date range)
dates = (silver.select(F.col("booking_date").alias("d"))
         .union(silver.select(F.col("travel_date").alias("d")))
         .where(F.col("d").isNotNull()).distinct())
dim_date = (dates
    .withColumn("date_key", F.col("d"))
    .withColumn("year", F.year("d"))
    .withColumn("quarter", F.concat(F.lit("Q"), F.quarter("d")))
    .withColumn("month", F.date_format("d", "yyyy-MM"))
    .withColumn("month_name", F.date_format("d", "MMMM"))
    .withColumn("day_of_week", F.date_format("d", "EEEE"))
    .drop("d"))
dim_date.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.dim_date")

print("dims written: dim_customer, dim_destination, dim_product, dim_date")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fact table

# COMMAND ----------

fact = silver.select(
    "booking_id", "booking_date", "travel_date", "lead_time_days",
    "customer_id", "destination_id", "product_id", "consultant_id", "channel",
    "booking_status", "pax_count",
    "gross_booking_value", "commission_amount", "refund_amount",
    "customer_comments",
)
fact.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.fact_bookings")
print("fact_bookings rows:", spark.table(f"{FQ}.fact_bookings").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Declare keys (PK / FK with RELY)
# MAGIC
# MAGIC Keys must be `NOT NULL`. `RELY` tells the optimiser it can trust them — which lets
# MAGIC metric-view joins avoid fan-out and lets lineage/candidate tools reason about the model.

# COMMAND ----------

ddl = [
    # dimensions: NOT NULL + PK
    f"ALTER TABLE {FQ}.dim_customer    ALTER COLUMN customer_id    SET NOT NULL",
    f"ALTER TABLE {FQ}.dim_destination ALTER COLUMN destination_id SET NOT NULL",
    f"ALTER TABLE {FQ}.dim_product     ALTER COLUMN product_id     SET NOT NULL",
    f"ALTER TABLE {FQ}.dim_date        ALTER COLUMN date_key       SET NOT NULL",
    f"ALTER TABLE {FQ}.dim_customer    ADD CONSTRAINT pk_customer    PRIMARY KEY (customer_id) RELY",
    f"ALTER TABLE {FQ}.dim_destination ADD CONSTRAINT pk_destination PRIMARY KEY (destination_id) RELY",
    f"ALTER TABLE {FQ}.dim_product     ADD CONSTRAINT pk_product     PRIMARY KEY (product_id) RELY",
    f"ALTER TABLE {FQ}.dim_date        ADD CONSTRAINT pk_date        PRIMARY KEY (date_key) RELY",
    # fact: NOT NULL on booking_id + PK, then FKs
    f"ALTER TABLE {FQ}.fact_bookings   ALTER COLUMN booking_id SET NOT NULL",
    f"ALTER TABLE {FQ}.fact_bookings   ADD CONSTRAINT pk_booking PRIMARY KEY (booking_id) RELY",
    f"ALTER TABLE {FQ}.fact_bookings   ADD CONSTRAINT fk_customer    FOREIGN KEY (customer_id)    REFERENCES {FQ}.dim_customer(customer_id) RELY",
    f"ALTER TABLE {FQ}.fact_bookings   ADD CONSTRAINT fk_destination FOREIGN KEY (destination_id) REFERENCES {FQ}.dim_destination(destination_id) RELY",
    f"ALTER TABLE {FQ}.fact_bookings   ADD CONSTRAINT fk_product     FOREIGN KEY (product_id)     REFERENCES {FQ}.dim_product(product_id) RELY",
    f"ALTER TABLE {FQ}.fact_bookings   ADD CONSTRAINT fk_booking_date FOREIGN KEY (booking_date)  REFERENCES {FQ}.dim_date(date_key) RELY",
]
for stmt in ddl:
    try:
        spark.sql(stmt)
    except Exception as e:
        # Re-running the notebook will hit "already exists" — that's fine.
        print("skip:", stmt.split("ADD CONSTRAINT")[-1][:40], "->", str(e)[:80])

print("constraints applied")

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Gold star schema ready: `fact_bookings` + `dim_customer`, `dim_destination`,
# MAGIC `dim_product`, `dim_date`. Continue to **`03_candidate_discovery_system_tables`**.
