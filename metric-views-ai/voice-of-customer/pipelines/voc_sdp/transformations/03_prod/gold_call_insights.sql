-- ============================================================================
-- STAGE 3 · PROD / GOLD — enrich every call, join to metadata
-- The three AI functions (sentiment, call-reason classification, summary) run ONCE
-- per transcript (streaming table) and the result is joined to the call metadata
-- table built by notebook 00 (`${metadata_table}`). This is the business-ready table
-- to point a Genie space or an AI/BI dashboard at.
--   ai_classify returns VARIANT → read the chosen label with :response[0].
-- ============================================================================
CREATE OR REFRESH STREAMING TABLE call_insights
  COMMENT 'Gold — one row per call: transcript + sentiment + call reason + summary + metadata.'
  TBLPROPERTIES ('quality' = 'gold')
AS SELECT
     t.audio_file,
     c.call_id,
     c.agent_name,
     c.queue,
     c.channel,
     c.call_start_ts,
     c.duration_seconds,
     c.customer_id,
     t.transcript_text,
     ai_analyze_sentiment(t.transcript_text) AS sentiment,
     ai_classify(
       t.transcript_text,
       ARRAY('new_booking_enquiry','booking_change','cancellation','refund_request',
             'payment_issue','delay_or_disruption','loyalty_points','complaint',
             'compliment','other')
     ):response[0]::string AS call_reason,
     ai_summarize(t.transcript_text, 25) AS summary
FROM STREAM(call_transcripts) t
LEFT JOIN ${metadata_table} c
  ON lower(c.audio_file) = lower(t.audio_file);
