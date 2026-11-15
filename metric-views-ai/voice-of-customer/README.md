# Voice of Customer — call recordings → `ai_transcribe` → `ai_classify`

A small, Free-Edition-friendly lab that mirrors the **Genesys "batch, post-call speech
analytics"** flow (*ingest → transcribe → enrich → serve*). Call recordings land in a Unity
Catalog Volume (as the **Brickstage recorder** does live), Auto Loader ingests them, and the
built-in AI functions turn audio into governed, queryable insight — **no GPU Whisper endpoint
required** (we use `ai_transcribe` instead of the deck's `ai_query` on a Whisper endpoint).

```
voice-of-customer/
  scripts/generate_recordings.py     # make 6 simulated WAV calls (macOS say + ffmpeg)
  data/
    recordings/*.wav                 # 6 calls, 16 kHz mono PCM (pre-generated)
    conversations.csv                # call metadata (agent, queue, duration, ...)
    ground_truth.csv                 # true transcript + reason (fallback + accuracy ref)
    labels.json                      # the call-reason taxonomy
  notebooks/
    00_setup_upload.py               # create Volume, land WAVs, build `conversations`
    01_try_ai_transcribe.py          # transcribe ONE file; inspect the result shape
  pipelines/voc_sdp/                  # the end-to-end SDP (Bronze → Silver → Gold)
```

## Flow
| Stage | Table | What happens |
|---|---|---|
| Ingest (Bronze) | `loaded_audio_files` | Auto Loader `read_files(... binaryFile)` picks up new WAVs |
| Transcribe (Silver) | `call_transcripts` | `ai_transcribe(content)` → `transcript_text` (once per call) |
| Enrich + serve (Gold) | `call_insights` | `ai_analyze_sentiment` + `ai_classify` (call reason) + `ai_summarize`, joined to `conversations` |

**Call-reason labels:** `new_booking_enquiry, booking_change, cancellation, refund_request,
payment_issue, delay_or_disruption, loyalty_points, complaint, compliment, other`.

## Run it
1. **(optional) Regenerate audio** locally on a Mac: `python3 scripts/generate_recordings.py`
   — the 6 WAVs are already committed, so you can skip this.
2. **Clone this repo as a Databricks Git folder**, then run **`notebooks/00_setup_upload`**
   (creates the Volume, copies the WAVs to `landing/`, builds the `conversations` table).
3. **`notebooks/01_try_ai_transcribe`** — see one call transcribed + a one-shot sentiment/
   classify/summarize preview. This also prints the real `ai_transcribe` result schema.
4. **Deploy & run the pipeline:**
   ```bash
   cd pipelines/voc_sdp
   databricks bundle validate --profile <PROFILE>
   databricks bundle deploy   --profile <PROFILE>
   databricks bundle run voc_sdp --profile <PROFILE>
   ```
   (or build it in the UI: **Jobs & Pipelines → Create → ETL pipeline**, serverless, point at
   `transformations/`, set `recordings_path` + `metadata_table` config.)
5. **Explore `call_insights`** — point a **Genie space** or an **AI/BI dashboard** at it
   (sentiment by queue, top call reasons, calls needing follow-up).

## Free Edition notes
- `ai_transcribe` is **Beta** and runs on **serverless** — availability can vary by region.
  Notebook `01` checks it; if it's unavailable, use `data/ground_truth.csv` as the transcript
  source and the Silver step is the only thing you skip (classify/summarize are unchanged).
- `ai_classify`, `ai_analyze_sentiment`, `ai_summarize` are standard serverless AI functions.
- AI functions are an LLM call per row — fine here (6 calls). At scale, persist once (as the
  streaming tables do) and never re-invoke on every query.

## How this reflects the Genesys deck
Same four-stage batch shape and the same `transcripts` → `transcripts_with_sentiment`
streaming-table idea. We deliberately swapped the deck's `ai_query`-on-Whisper-GPU endpoint
for `ai_transcribe` so the whole thing runs on Free Edition with zero endpoint setup. The
deck's real-time AudioHook path (Model Serving on GPU + Lakebase fan-out) is out of scope for
this lab.
