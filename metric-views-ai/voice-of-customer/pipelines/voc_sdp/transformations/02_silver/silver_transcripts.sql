-- ============================================================================
-- STAGE 2 · SILVER — transcription with ai_transcribe (Beta)
-- Streams each new recording through ai_transcribe and pulls out the plain transcript.
-- ai_transcribe returns a diarized, time-stamped STRUCT; we store it as VARIANT
-- (`transcription`) AND extract `transcript_text` defensively so the demo works whether
-- the text sits at `:text`, `:transcription`, inside a `segments[]` array, or is a bare
-- string. Confirm the real field names once in notebook 01 and simplify if you like.
-- Because this is a STREAMING TABLE, ai_transcribe runs ONCE per recording (not re-run).
-- ============================================================================
CREATE OR REFRESH STREAMING TABLE call_transcripts
  (CONSTRAINT has_transcript EXPECT (transcript_text IS NOT NULL AND length(transcript_text) > 0))
  COMMENT 'One transcript per recording. transcript_text is the cleaned plain text for enrichment.'
  TBLPROPERTIES ('quality' = 'silver')
AS SELECT
     audio_file,
     path,
     _ingested_at,
     transcription,
     COALESCE(
       transcription:text::string,
       transcription:transcription::string,
       array_join(transform(try_cast(transcription:segments AS ARRAY<VARIANT>), s -> s:text::string), ' '),
       transcription::string
     ) AS transcript_text
FROM (
  SELECT
    audio_file, path, _ingested_at,
    parse_json(to_json(ai_transcribe(content))) AS transcription
  FROM STREAM(loaded_audio_files)
);
