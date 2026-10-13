# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — HTG Metric Views Lunch & Learn
# MAGIC
# MAGIC **Session:** Governed Metrics with Unity Catalog Metric Views + AI acceleration
# MAGIC
# MAGIC This notebook sets up the catalog, schema and data location you'll use for the
# MAGIC rest of the lab. Run it once, top to bottom.
# MAGIC
# MAGIC ### What you need
# MAGIC - A Databricks workspace (a **free trial is fine**) with **Unity Catalog** enabled.
# MAGIC - **Serverless notebook compute (current runtime)** — recommended; metric views and
# MAGIC   window/offset measures all work there. An old SQL warehouse (below DBR 16.4) rejects
# MAGIC   metric views with a "Failed to parse YAML" error — switch compute if you see that.
# MAGIC - Metric Views need **DBR 16.4+** (we use **v1.1 YAML**, best on **17.2+**).
# MAGIC   The *window / offset* measures in notebook `04` need **DBR 18.0+** — there's a
# MAGIC   clearly-marked fallback if your compute is older.
# MAGIC
# MAGIC ### Two ways you got here
# MAGIC - **Cloned the repo** as a Databricks Git folder → the CSV is already beside these
# MAGIC   notebooks and this notebook will find it automatically.
# MAGIC - **Downloaded the notebooks** and uploaded them → you'll upload the CSV to a
# MAGIC   Unity Catalog **Volume** (cell below shows you how).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Choose your catalog & schema
# MAGIC
# MAGIC On a fresh trial your default catalog is often `workspace` (or `main`). Pick any
# MAGIC catalog you can **CREATE SCHEMA** in. Everything the lab creates lands in one schema
# MAGIC so it's easy to clean up afterwards.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace", "Catalog")
dbutils.widgets.text("schema", "htg_metric_views_lab", "Schema")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
FQ = f"{CATALOG}.{SCHEMA}"

print(f"Target schema: {FQ}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")
print(f"Using {FQ}")
print("Databricks Runtime:", spark.conf.get("spark.databricks.clusterUsageTags.sparkVersion", "serverless / unknown"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Make the raw bookings CSV available
# MAGIC
# MAGIC We ship a synthetic, denormalised HTG bookings file: `data/htg_bookings_raw.csv`
# MAGIC (30,000 bookings, Jan 2024 – Sep 2026, including a free-text `customer_comments`
# MAGIC column we'll mine with AI later).
# MAGIC
# MAGIC The next cell tries, in order:
# MAGIC 1. **Repo path** — if you cloned the repo as a Git folder, the CSV is right here.
# MAGIC 2. **UC Volume** — otherwise we create a Volume and you upload the CSV to it.

# COMMAND ----------

import os

# A UC Volume to hold raw files (works whether or not you cloned the repo).
VOLUME = "raw_files"
spark.sql(f"CREATE VOLUME IF NOT EXISTS {FQ}.{VOLUME}")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
print("Volume path:", VOLUME_PATH)

# Candidate locations for the CSV, in priority order.
candidates = [
    # When cloned as a Git folder, the notebook runs under /Workspace/... and the
    # repo's data/ dir sits one level up from notebooks/.
    os.path.abspath(os.path.join(os.getcwd(), "..", "data", "htg_bookings_raw.csv")),
    "../data/htg_bookings_raw.csv",
    f"{VOLUME_PATH}/htg_bookings_raw.csv",
]

CSV_PATH = None
for c in candidates:
    try:
        if c.startswith("/Volumes") or c.startswith("dbfs:"):
            # check via dbutils
            exists = any(f.name == "htg_bookings_raw.csv" for f in dbutils.fs.ls(VOLUME_PATH))
            if exists:
                CSV_PATH = c
                break
        elif os.path.exists(c):
            CSV_PATH = c
            break
    except Exception:
        continue

if CSV_PATH:
    print("Found raw CSV at:", CSV_PATH)
else:
    print("CSV not found yet.")
    print("Upload data/htg_bookings_raw.csv to this Volume, then re-run this cell:")
    print("  Catalog Explorer →", f"{CATALOG} / {SCHEMA} / Volumes / {VOLUME}", "→ Upload to this volume")
    print("Expected final path:", f"{VOLUME_PATH}/htg_bookings_raw.csv")

# COMMAND ----------

# Stash config for the other notebooks via the Spark conf (simple cross-notebook state).
spark.conf.set("htg.catalog", CATALOG)
spark.conf.set("htg.schema", SCHEMA)
if CSV_PATH:
    spark.conf.set("htg.csv_path", CSV_PATH)

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Setup done.** Continue to **`01_ingest_bronze_silver`**.
# MAGIC
# MAGIC > Everything you create lives in `{catalog}.{schema}`. To clean up after the session:
# MAGIC > `DROP SCHEMA {catalog}.{schema} CASCADE;`
