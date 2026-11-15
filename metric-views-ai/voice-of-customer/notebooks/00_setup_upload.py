# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — land the call recordings in a Volume
# MAGIC
# MAGIC The **Brickstage recorder** captures a live call and drops a WAV into a Unity Catalog
# MAGIC **Volume**. This notebook recreates that: it creates the catalog/schema/Volume and copies
# MAGIC the six simulated WAVs (from `voice-of-customer/data/recordings/`) into a `landing/` folder
# MAGIC that Auto Loader will watch. It also loads the call **metadata** into a Delta table.
# MAGIC
# MAGIC **Prereqs:** a UC-enabled workspace (**Free Edition is fine**) and this repo cloned as a
# MAGIC Databricks **Git folder** (so the WAVs are reachable at `/Workspace/...`). If the auto-copy
# MAGIC can't find them, the cell prints manual upload instructions.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace", "Catalog")
dbutils.widgets.text("schema", "htg_voc_lab", "Schema")
dbutils.widgets.text("volume", "call_recordings", "Volume")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA  = dbutils.widgets.get("schema").strip()
VOLUME  = dbutils.widgets.get("volume").strip()
FQ = f"{CATALOG}.{SCHEMA}"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {FQ}.{VOLUME}")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
LANDING     = f"{VOLUME_PATH}/landing"
dbutils.fs.mkdirs(LANDING)
print("Volume path:", VOLUME_PATH)
print("Landing    :", LANDING)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Copy the recordings + metadata into the Volume
# MAGIC We locate `voice-of-customer/data/` relative to this notebook (two levels up from
# MAGIC `notebooks/`) and copy from the `/Workspace` Git-folder path into the Volume.

# COMMAND ----------

import os

def repo_data_dir():
    """Find voice-of-customer/data next to this notebook in the Git folder."""
    try:
        nb = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        # nb = /Repos/.../voice-of-customer/notebooks/00_setup_upload  → data is ../data
        voc_root = os.path.dirname(os.path.dirname(nb))  # .../voice-of-customer
        return f"/Workspace{voc_root}/data"
    except Exception as e:
        print("Could not resolve notebook path:", e)
        return None

DATA_DIR = repo_data_dir()
copied = False
if DATA_DIR:
    rec_src = f"file:{DATA_DIR}/recordings"
    try:
        if any(f.name.endswith(".wav") for f in dbutils.fs.ls(rec_src)):
            dbutils.fs.cp(rec_src, LANDING, recurse=True)
            dbutils.fs.cp(f"file:{DATA_DIR}/conversations.csv", f"{VOLUME_PATH}/conversations.csv")
            dbutils.fs.cp(f"file:{DATA_DIR}/ground_truth.csv",  f"{VOLUME_PATH}/ground_truth.csv")
            copied = True
    except Exception as e:
        print("Auto-copy skipped:", e)

if copied:
    print("Copied recordings + metadata into the Volume.")
    display(dbutils.fs.ls(LANDING))
else:
    print("Could not auto-copy. Upload manually in Catalog Explorer:")
    print(f"  {CATALOG} / {SCHEMA} / Volumes / {VOLUME}  → create folder 'landing' → upload the 6 WAVs")
    print(f"  and upload conversations.csv + ground_truth.csv to {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load the call metadata into a Delta table
# MAGIC This is the `conversations` table the Gold layer joins transcripts to.

# COMMAND ----------

conv = (spark.read.option("header", True).option("inferSchema", True)
        .csv(f"{VOLUME_PATH}/conversations.csv"))
conv.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"{FQ}.conversations")
print(f"Wrote {conv.count()} rows to {FQ}.conversations")
display(spark.table(f"{FQ}.conversations"))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Recordings are in `landing/` and metadata is in `conversations`.
# MAGIC - Try a single-file transcription interactively in **`01_try_ai_transcribe`**.
# MAGIC - Then run the end-to-end **`pipelines/voc_sdp`** pipeline (Bronze → Silver → Gold).
