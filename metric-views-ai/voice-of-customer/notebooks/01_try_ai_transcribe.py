# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Try `ai_transcribe` on one recording
# MAGIC
# MAGIC Before building the pipeline, let's *see* the transcription work on a single file and
# MAGIC inspect the **shape** `ai_transcribe` returns (it's Beta — a diarized, time-stamped
# MAGIC result). The Gold layer reads text out of this, so knowing the exact field names helps.
# MAGIC
# MAGIC > **Free Edition note:** `ai_transcribe` runs on **serverless** SQL/compute and is **Beta**,
# MAGIC > so availability can vary by region. The first cell checks it and, if unavailable, points
# MAGIC > you to the ground-truth fallback so the rest of the lab (classify/summarize) still works.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace", "Catalog")
dbutils.widgets.text("schema", "htg_voc_lab", "Schema")
dbutils.widgets.text("volume", "call_recordings", "Volume")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA  = dbutils.widgets.get("schema").strip()
VOLUME  = dbutils.widgets.get("volume").strip()
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/landing"
ONE_FILE = f"{LANDING}/call_0003.wav"   # the "delayed flight" complaint
print("Transcribing:", ONE_FILE)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Availability check + raw result
# MAGIC `ai_transcribe(content)` takes the binary audio. We read the file with
# MAGIC `read_files(... format => 'binaryFile')` and show the result as JSON so you can read its
# MAGIC structure (look for a top-level `text`/`transcription` and a `segments` array).

# COMMAND ----------

try:
    raw = spark.sql(f"""
        SELECT to_json(ai_transcribe(content)) AS result
        FROM read_files('{ONE_FILE}', format => 'binaryFile')
    """).collect()[0]["result"]
    print("ai_transcribe is available. Raw JSON result:\n")
    import json
    print(json.dumps(json.loads(raw), indent=2)[:2000])
except Exception as e:
    print("ai_transcribe not available in this workspace/region (Beta). Error:\n", str(e)[:400])
    print("\nFallback: use voice-of-customer/data/ground_truth.csv as the 'transcript' column and")
    print("skip the Silver transcription step — the classify/summarize Gold logic is identical.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Pull just the transcript text (schema-tolerant)
# MAGIC We parse the JSON to VARIANT and try the likely fields in order, falling back to the
# MAGIC whole value as a string. This is exactly the expression the Gold layer uses.

# COMMAND ----------

spark.sql(f"""
    WITH t AS (
      SELECT parse_json(to_json(ai_transcribe(content))) AS v
      FROM read_files('{ONE_FILE}', format => 'binaryFile')
    )
    SELECT COALESCE(
             v:text::string,
             v:transcription::string,
             array_join(transform(try_cast(v:segments AS ARRAY<VARIANT>), s -> s:text::string), ' '),
             v::string
           ) AS transcript_text
    FROM t
""").display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. One-shot preview of the enrichment
# MAGIC Sentiment + call-reason + a one-line summary on this single transcript — the Gold layer
# MAGIC applies the same three AI functions to every call.

# COMMAND ----------

spark.sql(f"""
    WITH t AS (
      SELECT COALESCE(
               parse_json(to_json(ai_transcribe(content))):text::string,
               parse_json(to_json(ai_transcribe(content))):transcription::string
             ) AS transcript_text
      FROM read_files('{ONE_FILE}', format => 'binaryFile')
    )
    SELECT
      transcript_text,
      ai_analyze_sentiment(transcript_text) AS sentiment,
      ai_classify(transcript_text,
        ARRAY('new_booking_enquiry','booking_change','cancellation','refund_request',
              'payment_issue','delay_or_disruption','loyalty_points','complaint',
              'compliment','other')):response[0]::string AS call_reason,
      ai_summarize(transcript_text, 25) AS summary
    FROM t
""").display()
