# Deploy guide — run these pipelines on a fresh Databricks workspace

End-to-end instructions to deploy both pipelines yourself on a brand-new **Databricks Free
Edition** workspace using a **local CLI profile** + **Asset Bundles**.

- **Part 1 — `pipelines/bookings_sdp/`**: Auto Loader → Bronze → Silver → Gold (bookings), with expectations.
- **Part 2 — `voice-of-customer/`**: call recordings → `ai_transcribe` → `ai_classify`/sentiment/summarize.

Everything is serverless and uses the `workspace` catalog by default (the Free Edition default).

---

## 0. Prerequisites (one-time)

### a. Create a Free Edition workspace
Sign up at **https://www.databricks.com/learn/free-edition** and note your workspace URL, e.g.
`https://dbc-xxxxxxxx-xxxx.cloud.databricks.com`. Free Edition is serverless with Unity Catalog
enabled (default catalog is `workspace`).

### b. Install the Databricks CLI (v0.292.0+)
```bash
# macOS (Homebrew)
brew tap databricks/tap && brew install databricks
# or the universal installer
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks --version        # must be >= 0.292.0
```

### c. Create a local profile (OAuth browser login)
```bash
databricks auth login \
  --host https://dbc-xxxxxxxx-xxxx.cloud.databricks.com \
  --profile free-edition
# A browser opens — approve. Then verify:
databricks auth profiles
databricks current-user me --profile free-edition
```

### d. Get the repo in two places
```bash
# 1) Local clone — the CLI deploys the bundles FROM here
git clone https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series.git
cd Databricks_Lunch_N_Learn_Series/metric-views-ai
```
```text
# 2) Workspace Git folder — so the NOTEBOOKS can see the committed WAVs/CSVs.
#    In the workspace UI: Workspace → (your home) → Create → Git folder →
#    URL: https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series.git → Create.
```

> Everywhere below, replace `<PROFILE>` with `free-edition`.

---

## Part 1 — Bookings medallion pipeline

### 1. Land the raw files (once)
In the workspace Git folder, open **`metric-views-ai/notebooks/00_setup`** and run
**sections 1–3** (serverless). This creates the `raw_files` Volume and fills
`/Volumes/workspace/htg_metric_views_lab/raw_files/landing/` with JSON — the folder the
pipeline watches.

### 2. Deploy & run the pipeline
```bash
cd metric-views-ai/pipelines/bookings_sdp
databricks bundle validate --profile <PROFILE>
databricks bundle deploy   --profile <PROFILE>        # creates the pipeline (dev target)
databricks bundle run bookings_sdp --profile <PROFILE>
```
Override defaults if your catalog/schema/landing path differ:
```bash
databricks bundle deploy --profile <PROFILE> \
  --var="catalog=workspace" \
  --var="target_schema=htg_metric_views_lab_prod" \
  --var="landing_path=/Volumes/workspace/htg_metric_views_lab/raw_files/landing"
```

### 3. Verify
- **Jobs & Pipelines** → open `htg-bookings-medallion` → the graph shows
  `bookings_bronze → bookings_silver → fact_bookings` + `dim_*`.
- Open the **Data quality** tab to see the Silver expectations (kept/dropped counts).
- Point `notebooks/04_build_metric_views` at `target_schema` to read the pipeline's Gold.

---

## Part 2 — Voice-of-Customer pipeline

### 1. Land the recordings + metadata (once)
In the workspace Git folder, run **`metric-views-ai/voice-of-customer/notebooks/00_setup_upload`**
(serverless). It creates the `call_recordings` Volume, copies the 6 WAVs into `landing/`, and
builds the `conversations` table. Then run **`01_try_ai_transcribe`** to confirm `ai_transcribe`
is enabled in your region (it's Beta) and to see the transcript shape.

> If `ai_transcribe` is NOT available, use `voice-of-customer/data/ground_truth.csv` as the
> transcript source — only the Silver step changes; classify/summarize are identical.

### 2. Deploy & run the pipeline
```bash
cd metric-views-ai/voice-of-customer/pipelines/voc_sdp
databricks bundle validate --profile <PROFILE>
databricks bundle deploy   --profile <PROFILE>
databricks bundle run voc_sdp --profile <PROFILE>
```
Override defaults if needed:
```bash
databricks bundle deploy --profile <PROFILE> \
  --var="catalog=workspace" \
  --var="target_schema=htg_voc_lab" \
  --var="recordings_path=/Volumes/workspace/htg_voc_lab/call_recordings/landing" \
  --var="metadata_table=workspace.htg_voc_lab.conversations"
```

### 3. Verify
- Pipeline graph: `loaded_audio_files → call_transcripts → call_insights`.
- `SELECT call_reason, sentiment, summary, transcript_text FROM workspace.htg_voc_lab.call_insights`.
- Point a **Genie space** or **AI/BI dashboard** at `call_insights`.

---

## Test checklist
- [ ] `databricks current-user me --profile free-edition` returns your user.
- [ ] Notebook `00_setup` sections 1–3 ran; `landing/` has JSON files.
- [ ] `bundle validate` passes for `bookings_sdp`; `bundle run` completes; graph is green.
- [ ] `00_setup_upload` ran; `call_recordings/landing/` has 6 WAVs; `conversations` has 6 rows.
- [ ] `01_try_ai_transcribe` prints a transcript (or you switch to the ground-truth fallback).
- [ ] `bundle validate` passes for `voc_sdp`; `bundle run` completes; `call_insights` has 6 rows.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `bundle validate` can't resolve host | Pass `--profile <PROFILE>`; or add `workspace: {host: https://...}` under the `dev` target. |
| CLI too old / command missing | Upgrade to >= 0.292.0 (step 0b). |
| `ai_transcribe` not found / errors | Beta + region-gated — use the `ground_truth.csv` fallback (notebook 01 explains). |
| Notebook 00 can't find the WAVs | Make sure you cloned the repo as a **Git folder** in the workspace (step 0d-2), not just locally. |
| Pipeline stuck INITIALIZING | Normal cold start for serverless — wait a few minutes. |
