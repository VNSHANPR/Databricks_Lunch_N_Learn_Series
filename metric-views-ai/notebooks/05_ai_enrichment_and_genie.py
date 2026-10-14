# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · AI enrichment + Genie
# MAGIC
# MAGIC Two payoffs here:
# MAGIC 1. **AI over silver/gold** — turn the free-text `customer_comments` into structured
# MAGIC    dimensions (sentiment, issue category) with **AI Functions**, then fold them into a
# MAGIC    metric view. This is the "AI tooling over the top of your existing layers" idea.
# MAGIC 2. **Genie over the metric view** — point AI/BI Genie at the governed metrics so the
# MAGIC    business asks questions in plain English and gets *consistent* answers.
# MAGIC
# MAGIC **Needs:** a **serverless SQL warehouse / serverless compute** with Foundation Model
# MAGIC APIs available (standard on most workspaces incl. trials). If AI Functions aren't
# MAGIC enabled, the enrichment cell degrades gracefully and the Genie section still applies.

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
# MAGIC ## Step 1 — Classify the *distinct* comments (cheap by design)
# MAGIC
# MAGIC There are only a handful of distinct comment strings, so we classify the **distinct
# MAGIC values** and join the labels back — not 30k rows. That's the pattern to use at scale:
# MAGIC classify the cardinality that matters, not every row.

# COMMAND ----------

AI_OK = True
try:
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FQ}.comment_labels AS
        WITH distinct_comments AS (
          SELECT DISTINCT customer_comments
          FROM {FQ}.fact_bookings
          WHERE customer_comments IS NOT NULL
        )
        SELECT
          customer_comments,
          ai_classify(customer_comments, ARRAY('Positive', 'Neutral', 'Negative')) AS sentiment,
          ai_classify(customer_comments, ARRAY(
            'Refund or Billing', 'Service Quality', 'Itinerary Change',
            'Pricing', 'Positive Experience', 'Other')) AS issue_category
        FROM distinct_comments
    """)
    display(spark.table(f"{FQ}.comment_labels"))
except Exception as e:
    AI_OK = False
    print("⚠️  AI Functions unavailable here — skipping enrichment, continuing to Genie.")
    print("   (ai_classify needs serverless + Foundation Model API access.)")
    print("   Detail:", str(e)[:200])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Enriched gold table + Voice-of-Customer metric view

# COMMAND ----------

if AI_OK:
    # Join labels back onto the fact to produce an enriched gold table.
    spark.sql(f"""
        CREATE OR REPLACE TABLE {FQ}.fact_bookings_enriched AS
        SELECT f.*,
               COALESCE(l.sentiment, 'No Comment')      AS comment_sentiment,
               COALESCE(l.issue_category, 'No Comment')  AS comment_issue_category
        FROM {FQ}.fact_bookings f
        LEFT JOIN {FQ}.comment_labels l
          ON f.customer_comments = l.customer_comments
    """)

    spark.sql(f"""
        CREATE OR REPLACE VIEW {FQ}.mv_bookings_voc
        WITH METRICS
        LANGUAGE YAML
        AS $$
        version: 1.1
        comment: "Voice of Customer — booking KPIs sliced by AI-derived sentiment and issue category"
        source: {FQ}.fact_bookings_enriched
        dimensions:
          - name: Booking Month
            expr: DATE_TRUNC('MONTH', booking_date)
            synonyms: [month]
          - name: Sentiment
            expr: comment_sentiment
            comment: "AI-derived sentiment of the customer comment: Positive, Neutral, Negative or No Comment"
            synonyms: [customer sentiment, feedback sentiment]
          - name: Issue Category
            expr: comment_issue_category
            comment: "AI-derived theme of the customer comment"
            synonyms: [issue, complaint type, feedback theme]
          - name: Channel
            expr: channel
          - name: Brand
            expr: brand
        measures:
          - name: Booking Count
            expr: COUNT(1)
            format: {{ type: number, decimal_places: {{ type: exact, places: 0 }} }}
          - name: Negative Comment Rate
            expr: COUNT(1) FILTER (WHERE comment_sentiment = 'Negative') * 1.0
                  / NULLIF(COUNT(1) FILTER (WHERE comment_sentiment <> 'No Comment'), 0)
            comment: "Share of commented bookings with negative sentiment"
            synonyms: [negative rate, detractor rate, complaint rate]
            format: {{ type: percentage, decimal_places: {{ type: exact, places: 1 }} }}
          - name: TTV at Risk
            expr: SUM(gross_booking_value) FILTER (WHERE comment_sentiment = 'Negative')
            comment: "TTV associated with negative-sentiment bookings"
            synonyms: [revenue at risk, TTV at risk]
            format: {{ type: currency, currency_code: AUD, decimal_places: {{ type: exact, places: 0 }} }}
        $$
    """)
    print("Created", f"{FQ}.mv_bookings_voc")

    display(spark.sql(f"""
      SELECT `Issue Category`,
             MEASURE(`Booking Count`)         AS bookings,
             MEASURE(`Negative Comment Rate`) AS neg_rate,
             MEASURE(`TTV at Risk`)           AS ttv_at_risk
      FROM {FQ}.mv_bookings_voc
      WHERE `Issue Category` <> 'No Comment'
      GROUP BY ALL
      ORDER BY ttv_at_risk DESC
    """))
else:
    print("Skipped enrichment view (AI Functions unavailable).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Let Genie answer over the governed metrics
# MAGIC
# MAGIC The metric views are now the **single source of truth**. Create a Genie space on top
# MAGIC so the business self-serves — and because every measure/dimension carries `comment`
# MAGIC and `synonyms`, Genie understands HTG language out of the box.
# MAGIC
# MAGIC ### Create the Genie space (UI, 1 minute)
# MAGIC 1. **Genie** (left nav) → **New** → name it *"HTG Bookings"*.
# MAGIC 2. **Add data** → select your metric views:
# MAGIC    `mv_bookings`, `mv_bookings_trends`, `mv_bookings_voc`.
# MAGIC 3. Pick your **serverless SQL warehouse** → **Save**.
# MAGIC
# MAGIC ### Questions to try (these exercise the synonyms you defined)
# MAGIC - *"What was total **TTV** by region last quarter?"* → maps "TTV" → `Total TTV`.
# MAGIC - *"Show me the **cancellation rate** by brand."*
# MAGIC - *"Which **product type** has the highest **commission rate**?"*
# MAGIC - *"**Year on year growth** in TTV for 2026."* → uses the offset measure.
# MAGIC - *"What's our **negative comment rate** and **TTV at risk** by issue?"*
# MAGIC
# MAGIC Because the metrics are governed, every answer is **consistent** with the dashboards and
# MAGIC SQL that use the same views — no more three definitions of "TTV". That is the antidote
# MAGIC to *"circling the drain trying to get alignment."*
# MAGIC
# MAGIC ### (Optional) AI/BI dashboard
# MAGIC In a new **AI/BI dashboard**, add a dataset `SELECT ... MEASURE(...) FROM {FQ}.mv_bookings`
# MAGIC and build charts — the formatting (`AUD`, `%`) carries through automatically.

# COMMAND ----------

# MAGIC %md
# MAGIC 🎉 **You've gone end-to-end:** CSV → silver → gold star schema → AI-derived dimensions
# MAGIC → governed, AI-ready metric views → Genie. See `99_appendix_tpch_fallback` for a
# MAGIC zero-setup version on the built-in `samples.tpch` data.
