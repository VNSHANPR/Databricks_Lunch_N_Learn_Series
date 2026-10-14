# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — HTG Metric Views Lunch & Learn
# MAGIC
# MAGIC **Session:** Governed Metrics with Unity Catalog Metric Views + AI acceleration
# MAGIC
# MAGIC ### The big picture
# MAGIC Booking data from HTG's retail outlets lands as JSON files; Auto Loader ingests it into a
# MAGIC Bronze streaming table; the medallion shapes Silver → Gold; `ai_classify` enriches the
# MAGIC free-text comments; and governed **Metric Views** serve Genie, dashboards and SQL.
# MAGIC
# MAGIC ![HTG booking data architecture — retail outlets to JSON files to Auto Loader to Bronze/Silver/Gold medallion to ai_classify enrichment to Unity Catalog Metric Views to Genie, dashboards and SQL](https://vnshanpr.github.io/Databricks_Lunch_N_Learn_Series/metric-views-ai/assets/architecture.png)
# MAGIC
# MAGIC This notebook sets up the catalog, schema and data location, then **lands the raw
# MAGIC bookings with Auto Loader into a streaming Bronze table** — including an incremental
# MAGIC load so you can watch Auto Loader pick up new files as they arrive. Run it once, top
# MAGIC to bottom.
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
# On serverless, cluster-tag confs aren't exposed and spark.conf.get() raises
# CONFIG_NOT_AVAILABLE (the default arg doesn't help) — so guard it.
try:
    _runtime = spark.conf.get("spark.databricks.clusterUsageTags.sparkVersion")
except Exception:
    _runtime = "serverless / current"
print("Databricks Runtime:", _runtime)

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

# Stash config for the other notebooks. On serverless compute, spark.conf.set()
# rejects custom keys (CONFIG_NOT_AVAILABLE), so it can't carry cross-notebook state.
# Instead we write a small JSON file to the lab Volume; the other notebooks read it
# back. (This also works on classic compute.)
import json

config = {"htg.catalog": CATALOG, "htg.schema": SCHEMA}
if CSV_PATH:
    config["htg.csv_path"] = CSV_PATH

CONFIG_PATH = f"{VOLUME_PATH}/_htg_config.json"
dbutils.fs.put(CONFIG_PATH, json.dumps(config), overwrite=True)
print("Wrote lab config to", CONFIG_PATH)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Split the raw file into a landing zone for Auto Loader
# MAGIC
# MAGIC Real pipelines ingest **many files that arrive over time**, not one big CSV. So we
# MAGIC split the raw file into several small **JSON** files in a `landing/` folder on the
# MAGIC Volume, and **hold back a little data** in `incoming_later/` to simulate new files
# MAGIC arriving after the first load.

# COMMAND ----------

import csv, math

LANDING  = f"{VOLUME_PATH}/landing"
INCOMING = f"{VOLUME_PATH}/incoming_later"
for d in (LANDING, INCOMING):
    dbutils.fs.mkdirs(d)        # idempotent; works on UC Volumes (open() below needs the dir)

if not CSV_PATH:
    raise Exception("No source CSV found — complete section 2 (make the CSV available) first.")

INT_COLS   = {"lead_time_days", "pax_count"}
FLOAT_COLS = {"gross_booking_value", "commission_amount", "refund_amount"}

def _coerce(row):
    """Give JSON sensible native types so Bronze isn't all-strings; dates stay strings."""
    out = {}
    for k, v in row.items():
        if v is None or v == "":
            out[k] = None
        elif k in INT_COLS:
            try: out[k] = int(float(v))
            except Exception: out[k] = None
        elif k in FLOAT_COLS:
            try: out[k] = float(v)
            except Exception: out[k] = None
        else:
            out[k] = v
    return out

def _write_jsonl(records, path):
    with open(path, "w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")

with open(CSV_PATH, newline="") as f:
    rows = [_coerce(r) for r in csv.DictReader(f)]

HOLDBACK = 100                                   # rows saved for the incremental demo
initial, later = rows[:len(rows) - HOLDBACK], rows[len(rows) - HOLDBACK:]

# Initial load: 8 small files in landing/
N_FILES = 8
step = math.ceil(len(initial) / N_FILES)
for i in range(N_FILES):
    _write_jsonl(initial[i * step:(i + 1) * step], f"{LANDING}/bookings_{i:03d}.json")

# Incremental: 2 files staged OUTSIDE landing/ — we add them after the first load.
half = math.ceil(len(later) / 2)
_write_jsonl(later[:half], f"{INCOMING}/bookings_new_001.json")
_write_jsonl(later[half:], f"{INCOMING}/bookings_new_002.json")

print(f"Wrote {N_FILES} initial files ({len(initial)} rows) to {LANDING}")
print(f"Staged 2 incremental files ({len(later)} rows) in {INCOMING}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Auto Loader → Bronze **streaming table**
# MAGIC
# MAGIC `cloudFiles` (Auto Loader) incrementally ingests files from the landing folder. We use
# MAGIC `trigger(availableNow=True)` so it processes everything available **and then stops** —
# MAGIC ideal for a lab. A **checkpoint** records which files it has already seen, so re-running
# MAGIC only picks up *new* files. The target Delta table is our **Bronze** layer.
# MAGIC
# MAGIC > Runs on serverless or any standard compute. No cloud notifications to configure —
# MAGIC > Auto Loader uses directory listing by default.

# COMMAND ----------

from pyspark.sql import functions as F

BRONZE     = f"{FQ}.bookings_bronze"
CKPT       = f"{VOLUME_PATH}/_autoloader/bookings_bronze/checkpoint"
SCHEMA_LOC = f"{VOLUME_PATH}/_autoloader/bookings_bronze/schema"

def run_autoloader():
    """Ingest any new files in LANDING into the Bronze table, then stop."""
    stream = (spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", SCHEMA_LOC)
        .option("cloudFiles.inferColumnTypes", "true")
        .load(LANDING)
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path")))
    (stream.writeStream
        .option("checkpointLocation", CKPT)
        .trigger(availableNow=True)
        .toTable(BRONZE)
        .awaitTermination())

run_autoloader()
print("Bronze rows after initial load:", spark.table(BRONZE).count())
display(spark.table(BRONZE).limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Simulate new files arriving — Auto Loader catches up
# MAGIC
# MAGIC We move the two staged files into `landing/` and run the **same** Auto Loader again.
# MAGIC Because the checkpoint remembers the first 8 files, only the **2 new files** are read,
# MAGIC and the Bronze row count goes up.

# COMMAND ----------

for fn in ("bookings_new_001.json", "bookings_new_002.json"):
    try:
        dbutils.fs.mv(f"{INCOMING}/{fn}", f"{LANDING}/{fn}")
    except Exception as e:
        print("skip (already moved?):", fn, "->", str(e)[:80])

run_autoloader()   # same checkpoint → only the 2 new files are ingested
print("Bronze rows after incremental load:", spark.table(BRONZE).count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. (Optional, serverless) The same ingest as a managed **Streaming Table**
# MAGIC
# MAGIC The `bookings_bronze` table above is a normal Delta table that a Structured Streaming job
# MAGIC *writes to* — correct and incremental, but Unity Catalog lists it as an **ordinary table**
# MAGIC (no streaming icon). A **Streaming Table (ST)** is a different, *declarative* object: you
# MAGIC describe the result and Databricks runs a **managed pipeline** to keep it current. That's
# MAGIC the object that shows the **streaming icon** in Catalog Explorer.
# MAGIC
# MAGIC Run the next cell to create one — named `bookings_bronze_st` so it doesn't clash with the
# MAGIC section-4 table. **Serverless only**, and the first run spins up a managed pipeline, so
# MAGIC give it a minute. *(This is optional — the rest of the lab runs on `bookings_bronze`.)*

# COMMAND ----------

# OPTIONAL — creates a managed Streaming Table (needs serverless). Safe to skip.
create_st = f"""
CREATE OR REFRESH STREAMING TABLE {FQ}.bookings_bronze_st AS
SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '{LANDING}',
  format => 'json',
  inferColumnTypes => true
)
"""
try:
    spark.sql(create_st)
    print("Created managed Streaming Table:", f"{FQ}.bookings_bronze_st")
    print("Rows:", spark.table(f"{FQ}.bookings_bronze_st").count())
    print("Open it in Catalog Explorer — it carries the streaming-table icon.")
    print("Ingest new files later: drop them in", LANDING, "then run")
    print(f"  REFRESH STREAMING TABLE {FQ}.bookings_bronze_st")
    print("  (or use the Refresh action in Catalog Explorer).")
except Exception as e:
    print("⚠️  Could not create the Streaming Table — this needs serverless compute")
    print("   (classic compute can't create a managed streaming table). The lab continues")
    print("   fine on the section-4 `bookings_bronze` table.")
    print("   Detail:", str(e)[:200])

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Setup done.** You now have a **Bronze table** (`bookings_bronze`), incrementally
# MAGIC loaded by Auto Loader — plus, optionally, a managed **Streaming Table**
# MAGIC (`bookings_bronze_st`) if you ran section 6. Continue to **`01_ingest_bronze_silver`**
# MAGIC to shape Silver, then Gold.
# MAGIC
# MAGIC > Everything you create lives in `{catalog}.{schema}`. To clean up after the session:
# MAGIC > `DROP SCHEMA {catalog}.{schema} CASCADE;` and delete the Volume's `landing/`,
# MAGIC > `incoming_later/` and `_autoloader/` folders.
# MAGIC >
# MAGIC > Re-running from scratch? Also `DROP TABLE {catalog}.{schema}.bookings_bronze` and
# MAGIC > delete `_autoloader/` so Auto Loader starts with a fresh checkpoint.
