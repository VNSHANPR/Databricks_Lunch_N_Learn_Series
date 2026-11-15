# Deploy guide — run these pipelines on any Databricks workspace

End-to-end instructions to deploy both pipelines yourself using a **local CLI profile** +
**Asset Bundles**. Works on **Free Edition** (catalog `workspace`) or any other workspace
(e.g. a shared workspace where your catalog is `main`, `de_cert_classic_catalog`, etc.) — you
just set two values once and every command below uses them.

- **Part 1 — `pipelines/bookings_sdp/`**: Auto Loader → Bronze → Silver → Gold (bookings), with expectations.
- **Part 2 — `voice-of-customer/`**: call recordings → `ai_transcribe` → `ai_classify`/sentiment/summarize.

Everything is serverless.

---

## 0. Prerequisites (one-time)

### a. Create / pick a workspace
- **Free Edition:** sign up at https://www.databricks.com/learn/free-edition and note the URL
  (serverless + Unity Catalog, default catalog `workspace`).
- **Any other workspace:** just note its URL and a Unity Catalog you can `CREATE` in.

### b. Install the Databricks CLI (v0.292.0+)
```bash
brew tap databricks/tap && brew install databricks      # macOS
# or: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
databricks --version        # must be >= 0.292.0
```

### c. Create a local profile (OAuth browser login)
Give the profile any name you like — that name IS how you select the workspace later.
```bash
databricks auth login \
  --host https://<your-workspace>.cloud.databricks.com \
  --profile <your-profile-name>
```

### d. ⭐ Set YOUR workspace + catalog (every command below reads these)
Run these two `export`s in your terminal. **This is where you "enter" the workspace and
catalog** — change them to match what you created/chose above:
```bash
export PROFILE=<your-profile-name>     # the workspace, e.g. free-edition  OR  fevm-de-cert-classic
export CATALOG=<your-catalog>          # Free Edition: workspace          OR  e.g. de_cert_classic_catalog
```
Verify they work:
```bash
databricks current-user me --profile "$PROFILE"
databricks catalogs list --profile "$PROFILE"     # confirm $CATALOG is in the list
```

### e. Get the repo in two places
```bash
git clone https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series.git   # local, for bundle deploy
cd Databricks_Lunch_N_Learn_Series/metric-views-ai
```
Also add the repo as a **Git folder in the workspace UI** (Workspace → Create → Git folder →
the repo URL) so the notebooks can see the committed WAVs.

---

## Part 1 — Bookings medallion pipeline

### 1. Land the raw files (once)
In the workspace, open **`metric-views-ai/notebooks/00_setup`**, set its **`catalog` widget to
your `$CATALOG`**, and run **sections 1–3**. That creates the `raw_files` Volume and fills
`/Volumes/$CATALOG/htg_metric_views_lab/raw_files/landing/` with JSON.

### 2. Deploy & run
```bash
cd metric-views-ai/pipelines/bookings_sdp

databricks bundle validate --profile "$PROFILE" --var="catalog=$CATALOG"

databricks bundle deploy --profile "$PROFILE" \
  --var="catalog=$CATALOG" \
  --var="target_schema=htg_metric_views_lab_prod" \
  --var="landing_path=/Volumes/$CATALOG/htg_metric_views_lab/raw_files/landing"

databricks bundle run bookings_sdp --profile "$PROFILE" \
  --var="catalog=$CATALOG" \
  --var="target_schema=htg_metric_views_lab_prod" \
  --var="landing_path=/Volumes/$CATALOG/htg_metric_views_lab/raw_files/landing"
```
> Pass the **same `--var`s** to `deploy` and `run`. (On Free Edition `$CATALOG=workspace` the
> defaults already match, so you can drop the flags there.)

### 3. Verify
- **Jobs & Pipelines → `htg-bookings-medallion`**: graph `bookings_bronze → bookings_silver →
  fact_bookings` + `dim_*`; check the **Data quality** tab for the Silver expectations.
- Point `notebooks/04_build_metric_views` at `$CATALOG` / `htg_metric_views_lab_prod`.

---

## Part 2 — Voice-of-Customer pipeline

### 1. Land the recordings + metadata (once)
In the workspace, run **`voice-of-customer/notebooks/00_setup_upload`** with its **`catalog`
widget set to `$CATALOG`** (creates the `call_recordings` Volume, copies the 6 WAVs to
`landing/`, builds `conversations`). Then run **`01_try_ai_transcribe`** to confirm
`ai_transcribe` is enabled (Beta) and see the transcript shape.
> If `ai_transcribe` is unavailable, use `voice-of-customer/data/ground_truth.csv` as the
> transcript source — only the Silver step changes.

### 2. Deploy & run
```bash
cd metric-views-ai/voice-of-customer/pipelines/voc_sdp

databricks bundle validate --profile "$PROFILE" --var="catalog=$CATALOG"

databricks bundle deploy --profile "$PROFILE" \
  --var="catalog=$CATALOG" \
  --var="target_schema=htg_voc_lab" \
  --var="recordings_path=/Volumes/$CATALOG/htg_voc_lab/call_recordings/landing" \
  --var="metadata_table=$CATALOG.htg_voc_lab.conversations"

databricks bundle run voc_sdp --profile "$PROFILE" \
  --var="catalog=$CATALOG" \
  --var="target_schema=htg_voc_lab" \
  --var="recordings_path=/Volumes/$CATALOG/htg_voc_lab/call_recordings/landing" \
  --var="metadata_table=$CATALOG.htg_voc_lab.conversations"
```

### 3. Verify
- Pipeline graph: `loaded_audio_files → call_transcripts → call_insights`.
- `SELECT call_reason, sentiment, summary, transcript_text FROM $CATALOG.htg_voc_lab.call_insights`.
- Point a **Genie space** / **AI-BI dashboard** at `call_insights`.

---

## Quick copy-paste (example: de-cert-classic)
```bash
export PROFILE=fevm-de-cert-classic
export CATALOG=de_cert_classic_catalog
# then run the Part 1 / Part 2 blocks above as-is
```

## Test checklist
- [ ] `databricks current-user me --profile "$PROFILE"` returns your user; `$CATALOG` is in `catalogs list`.
- [ ] Notebook `00_setup` (sections 1–3) ran with the `catalog` widget = `$CATALOG`; `landing/` has JSON.
- [ ] `bundle validate` passes for `bookings_sdp`; `bundle run` completes; graph is green.
- [ ] `00_setup_upload` ran (catalog widget = `$CATALOG`); 6 WAVs in `landing/`; `conversations` has 6 rows.
- [ ] `01_try_ai_transcribe` prints a transcript (or switch to the ground-truth fallback).
- [ ] `bundle validate` passes for `voc_sdp`; `bundle run` completes; `call_insights` has 6 rows.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `CATALOG_DOES_NOT_EXIST` on deploy | `$CATALOG` doesn't exist in that workspace. Run `databricks catalogs list --profile "$PROFILE"` and set `CATALOG` to a real one (Free Edition = `workspace`; de-cert-classic = `de_cert_classic_catalog`). |
| `bundle validate` can't resolve host | Make sure `--profile "$PROFILE"` is set; the profile supplies the host. |
| CLI too old / command missing | Upgrade to >= 0.292.0 (step 0b). |
| `ai_transcribe` not found / errors | Beta + region-gated — use the `ground_truth.csv` fallback (notebook 01 explains). |
| Notebook 00 can't find the WAVs | Clone the repo as a **Git folder** in the workspace (step 0e), not just locally. |
| Pipeline stuck INITIALIZING | Normal cold start for serverless — wait a few minutes. |
| Table/volume not found at `run` | Run the setup notebook first with its `catalog` widget set to `$CATALOG`. |
