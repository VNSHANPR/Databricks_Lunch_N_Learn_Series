# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · (Appendix) The production version — a Lakeflow Declarative Pipeline
# MAGIC
# MAGIC Notebooks `00`–`02` build the medallion **step by step, in batch** — great for *seeing*
# MAGIC each layer, but you run them by hand and Silver/Gold fully recompute each time. In
# MAGIC production you'd express the same Bronze → Silver → Gold as **one declarative pipeline**
# MAGIC that keeps every layer **incrementally in sync** and produces real **Streaming Tables**
# MAGIC (the ones with the streaming icon in Catalog Explorer).
# MAGIC
# MAGIC ⚠️ **This notebook is the *source* for a Lakeflow Declarative Pipeline — it is NOT run
# MAGIC cell-by-cell.** The `%sql` cells below *define* datasets; a pipeline executes them as a
# MAGIC dependency graph. Follow the "How to run" steps at the bottom.
# MAGIC
# MAGIC **Prerequisite:** run `00_setup` sections 1–3 first, so the Volume and the `landing/`
# MAGIC JSON files exist. Point the pipeline at a **fresh schema** (e.g. `htg_metric_views_lab_prod`)
# MAGIC so it doesn't collide with the batch tables from `00`–`02`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze — Auto Loader Streaming Table
# MAGIC
# MAGIC Incremental file ingestion straight from the landing folder. `${landing_path}` is a
# MAGIC pipeline **configuration** value you set when you create the pipeline.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH STREAMING TABLE bookings_bronze
# MAGIC   (CONSTRAINT valid_booking EXPECT (booking_id IS NOT NULL))
# MAGIC AS SELECT
# MAGIC      *,
# MAGIC      _metadata.file_path AS _source_file,
# MAGIC      current_timestamp() AS _ingested_at
# MAGIC FROM STREAM read_files(
# MAGIC   '${landing_path}',
# MAGIC   format => 'json',
# MAGIC   inferColumnTypes => true
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver — Streaming Table from Bronze (+ data-quality expectations)
# MAGIC
# MAGIC Reads a **stream** from Bronze and applies the same casts/cleaning per new row — so it
# MAGIC stays in sync automatically, no full recompute. Expectations drop bad rows (here) or can
# MAGIC fail the run; either way the violations are tracked in the pipeline's data-quality view.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH STREAMING TABLE bookings_silver
# MAGIC   (CONSTRAINT valid_booking    EXPECT (booking_id IS NOT NULL) ON VIOLATION DROP ROW,
# MAGIC    CONSTRAINT non_negative_ttv EXPECT (gross_booking_value >= 0))
# MAGIC AS SELECT
# MAGIC      booking_id,
# MAGIC      to_date(booking_date) AS booking_date,
# MAGIC      to_date(travel_date)  AS travel_date,
# MAGIC      lead_time_days,
# MAGIC      customer_id, customer_name, customer_segment, loyalty_tier, home_city, home_country,
# MAGIC      destination_id, destination_city, destination_country, destination_region,
# MAGIC      product_id, product_type, brand,
# MAGIC      channel, consultant_id, booking_status, pax_count,
# MAGIC      CAST(gross_booking_value AS DECIMAL(12,2)) AS gross_booking_value,
# MAGIC      CAST(commission_amount   AS DECIMAL(12,2)) AS commission_amount,
# MAGIC      CAST(refund_amount       AS DECIMAL(12,2)) AS refund_amount,
# MAGIC      NULLIF(TRIM(customer_comments), '') AS customer_comments
# MAGIC FROM STREAM(bookings_bronze);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold — fact Streaming Table + dimension Materialized Views
# MAGIC
# MAGIC The fact is append-only (streaming) from Silver. The dimensions are **materialized
# MAGIC views**: deduplication is an aggregation over the *whole* table, which is an MV job, not a
# MAGIC streaming one. *(If bookings can be amended/cancelled, swap the fact for an **Auto CDC**
# MAGIC flow keyed on `booking_id` so updates upsert instead of append.)*

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH STREAMING TABLE fact_bookings
# MAGIC AS SELECT
# MAGIC      booking_id, booking_date, travel_date, lead_time_days,
# MAGIC      customer_id, destination_id, product_id, consultant_id, channel,
# MAGIC      booking_status, pax_count,
# MAGIC      gross_booking_value, commission_amount, refund_amount,
# MAGIC      customer_comments
# MAGIC FROM STREAM(bookings_silver);

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH MATERIALIZED VIEW dim_customer AS
# MAGIC SELECT customer_id, customer_name, customer_segment, loyalty_tier, home_city, home_country
# MAGIC FROM (
# MAGIC   SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY booking_date DESC) AS rn
# MAGIC   FROM bookings_silver
# MAGIC ) WHERE rn = 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH MATERIALIZED VIEW dim_destination AS
# MAGIC SELECT destination_id, destination_city, destination_country, destination_region
# MAGIC FROM (
# MAGIC   SELECT *, ROW_NUMBER() OVER (PARTITION BY destination_id ORDER BY booking_date DESC) AS rn
# MAGIC   FROM bookings_silver
# MAGIC ) WHERE rn = 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH MATERIALIZED VIEW dim_product AS
# MAGIC SELECT product_id, product_type, brand
# MAGIC FROM (
# MAGIC   SELECT *, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY booking_date DESC) AS rn
# MAGIC   FROM bookings_silver
# MAGIC ) WHERE rn = 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH MATERIALIZED VIEW dim_date AS
# MAGIC SELECT DISTINCT
# MAGIC   d                          AS date_key,
# MAGIC   YEAR(d)                    AS year,
# MAGIC   CONCAT('Q', QUARTER(d))    AS quarter,
# MAGIC   DATE_FORMAT(d, 'yyyy-MM')  AS month,
# MAGIC   DATE_FORMAT(d, 'MMMM')     AS month_name,
# MAGIC   DATE_FORMAT(d, 'EEEE')     AS day_of_week
# MAGIC FROM (
# MAGIC   SELECT booking_date AS d FROM bookings_silver WHERE booking_date IS NOT NULL
# MAGIC   UNION
# MAGIC   SELECT travel_date  AS d FROM bookings_silver WHERE travel_date  IS NOT NULL
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC ## How to run this as a pipeline
# MAGIC
# MAGIC **UI**
# MAGIC 1. **Jobs & Pipelines → Create → ETL pipeline**.
# MAGIC 2. **Source code:** this notebook (`06_production_pipeline`).
# MAGIC 3. **Compute:** Serverless.
# MAGIC 4. **Destination:** Unity Catalog → your catalog + a **fresh schema**
# MAGIC    (e.g. `htg_metric_views_lab_prod`).
# MAGIC 5. **Configuration:** add key `landing_path` =
# MAGIC    `/Volumes/<catalog>/<schema>/raw_files/landing` (the folder notebook `00` filled).
# MAGIC 6. **Start.** The first run cold-starts the managed pipeline (a few minutes), then builds
# MAGIC    Bronze → Silver → Gold. Add a **schedule** (triggered) or run **continuous** for
# MAGIC    always-on ingestion.
# MAGIC
# MAGIC **CLI** (optional)
# MAGIC ```bash
# MAGIC databricks pipelines create --json '{
# MAGIC   "name": "htg-medallion",
# MAGIC   "serverless": true,
# MAGIC   "catalog": "<catalog>",
# MAGIC   "schema": "htg_metric_views_lab_prod",
# MAGIC   "configuration": {"landing_path": "/Volumes/<catalog>/<schema>/raw_files/landing"},
# MAGIC   "libraries": [{"notebook": {"path": "<path-to>/06_production_pipeline"}}]
# MAGIC }' --profile <PROFILE>
# MAGIC ```
# MAGIC
# MAGIC ## Then point the metric views at this Gold
# MAGIC
# MAGIC `04_build_metric_views` is **unchanged** — just set its `catalog` / `schema` widgets to the
# MAGIC pipeline's target so `source: <schema>.fact_bookings` resolves to the pipeline's Gold. The
# MAGIC metric view stays **virtual** and reads whatever the pipeline has published — live.
# MAGIC
# MAGIC **Production extras worth adding**
# MAGIC - **RELY PK/FK** on the Gold tables (as in `02`) — helps the metric-view join optimiser.
# MAGIC - **Auto CDC** on `fact_bookings` keyed on `booking_id` if bookings get amended/cancelled
# MAGIC   (upsert instead of append); **SCD Type 2** dimensions if you need "segment as-of booking date".
# MAGIC - **Managed file events** instead of directory listing once file volumes grow large.
# MAGIC - **Materialize** the metric view only if dashboards / Genie need sub-second reads at scale.
