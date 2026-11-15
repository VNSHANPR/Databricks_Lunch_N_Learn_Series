-- ============================================================================
-- STAGE 1 · INGESTION (Bronze) — Auto Loader over audio
-- Incrementally pick up new call WAVs from the Volume as binary files. One row per
-- recording; the `content` column holds the raw bytes ai_transcribe will read.
-- `${recordings_path}` is a pipeline configuration value.
-- ============================================================================
CREATE OR REFRESH STREAMING TABLE loaded_audio_files
  (CONSTRAINT has_audio EXPECT (content IS NOT NULL) ON VIOLATION DROP ROW)
  COMMENT 'Raw call recordings ingested from the Volume by Auto Loader (binaryFile).'
  TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
     path,
     regexp_extract(path, '([^/]+)$', 1) AS audio_file,
     length,
     modificationTime,
     content,
     current_timestamp() AS _ingested_at
FROM STREAM read_files('${recordings_path}', format => 'binaryFile');
