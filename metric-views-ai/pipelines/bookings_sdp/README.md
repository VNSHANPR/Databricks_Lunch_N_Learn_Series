# Bookings medallion — production Spark Declarative Pipeline (SDP)

The batch notebooks `00`–`02` build Bronze → Silver → Gold **by hand**. This is the same
medallion expressed as **one declarative pipeline** that keeps every layer incrementally in
sync (real Streaming Tables + Auto Loader), with data-quality **expectations** and split into
the three stages you'd have in production.

```
transformations/
  01_ingestion/  bronze_bookings.sql   -- Auto Loader (read_files json) → bookings_bronze
  02_silver/     silver_bookings.sql   -- clean/type + 6 EXPECT constraints → bookings_silver
  03_prod/       gold_bookings.sql     -- fact_bookings (streaming) + dim_* (materialized views)
```

## Prerequisite
Run **`notebooks/00_setup` sections 1–3** once so the Volume and `landing/` JSON files exist.
Point this pipeline at a **fresh schema** (default `htg_metric_views_lab_prod`) so it doesn't
collide with the batch tables from `00`–`02`.

## Deploy & run (CLI / Asset Bundle)
```bash
databricks auth profiles                       # pick your workspace profile
databricks bundle validate --profile <PROFILE>
databricks bundle deploy   --profile <PROFILE> # dev target (default)
databricks bundle run bookings_sdp --profile <PROFILE>
```
Override the defaults per workspace if needed:
```bash
databricks bundle deploy --profile <PROFILE> \
  --var="catalog=workspace" \
  --var="target_schema=htg_metric_views_lab_prod" \
  --var="landing_path=/Volumes/workspace/htg_metric_views_lab/raw_files/landing"
```

## Or create it in the UI
**Jobs & Pipelines → Create → ETL pipeline** → Serverless → add all files under
`transformations/` as source → Destination = your catalog + a fresh schema → add
configuration key `landing_path` → **Start**. Run **triggered** (scheduled) or **continuous**.

## Then point the Metric Views at this Gold
`notebooks/04_build_metric_views` is unchanged — set its `catalog`/`schema` widgets to this
pipeline's target so `source: <schema>.fact_bookings` resolves to the pipeline's Gold. The
metric view stays virtual and reads whatever the pipeline has published, live.

## Expectations in this pipeline (Silver)
| Constraint | Rule | On violation |
|---|---|---|
| `valid_booking_id` | `booking_id IS NOT NULL` | DROP ROW |
| `non_negative_value` | `gross_booking_value >= 0` | DROP ROW |
| `positive_pax` | `pax_count > 0` | warn (tracked) |
| `known_status` | status in Confirmed/Completed/Cancelled/Amended | warn |
| `travel_after_booking` | `travel_date >= booking_date` | warn |
| `refund_within_value` | `refund_amount <= gross_booking_value` | warn |

Violations show up in the pipeline's **data quality** tab per run.

## Production extras worth adding
- **RELY PK/FK** on the Gold tables (as notebook `02` does via `ALTER TABLE`) — helps the
  metric-view join optimiser. Run the ALTERs after the first pipeline update.
- **AUTO CDC** on `fact_bookings` keyed on `booking_id` if bookings get amended/cancelled.
- **Managed file events** instead of directory listing once file volumes grow large.
