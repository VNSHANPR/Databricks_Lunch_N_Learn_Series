-- ============================================================================
-- STAGE 1 · INGESTION (Bronze)
-- Auto Loader incrementally ingests booking JSON from the landing Volume into a
-- streaming table. A checkpoint (managed by the pipeline) means each file is read
-- exactly once — re-runs only pick up new files.
-- `${landing_path}` is a pipeline configuration value (see resources/bookings.pipeline.yml).
-- ============================================================================
CREATE OR REFRESH STREAMING TABLE bookings_bronze
  (CONSTRAINT valid_booking_id EXPECT (booking_id IS NOT NULL))
  COMMENT 'Raw bookings landed as-is by Auto Loader (schema inferred). One row per source record.'
  TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
     *,
     _metadata.file_path  AS _source_file,
     current_timestamp()  AS _ingested_at
FROM STREAM read_files(
  '${landing_path}',
  format           => 'json',
  inferColumnTypes => true
);
