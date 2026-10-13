# Metric Views + AI — HTG Lunch & Learn

**Session date:** 15 Oct 2026 · **Series:** Databricks Lunch & Learn
**Theme:** Build a *governed* semantic layer with Unity Catalog **Metric Views**, and use
**Genie / AI tooling** to get there fast — over your existing silver & gold layers.

> *The brief from HTG:* "target this section not only on metric views but also around the
> idea of leveraging genie / AI tooling to run over the top of our existing silver and gold
> layers in order to build these metrics views in a much faster fashion compared to us
> circling the drain trying to get alignment."

This lab answers that directly: **let AI surface the metric candidates and convert what you
already have, land them as governed Metric Views, and let Genie answer over them.**

---

## What you'll build (hands-on)

```
CSV (bookings + comments)
      │  01  ingest → bronze → silver        (or Lakeflow Designer, no-code)
      ▼
  Gold star schema                           02  fact_bookings + dims + PK/FK
      │
      ├─ 03  find metric-view candidates from your SYSTEM TABLES
      │        (most-queried / most-joined) → auto-suggested view
      │
      ├─ 04  build the metric views
      │        basic → filtered → ratios → joins → window/offset → agentic metadata
      │
      └─ 05  AI over the text (ai_classify) → VoC metric view → Genie Q&A
```

Plus **`99`** — a zero-setup fallback on `samples.tpch` if any workspace blocks the data step,
and a **presenter demo** of Genie Code `/importBI` converting a Power BI model → Metric Views.

---

## Prerequisites (2 minutes)

- A Databricks workspace with **Unity Catalog** — a **free trial is fine**.
- **Serverless** SQL warehouse / notebook compute recommended.
- Metric Views: **DBR 16.4+** (we use v1.1 YAML; best on **17.2+**).
  The **window/offset** measures in notebook `04` need **DBR 18.0+** — there's a clearly
  marked fallback if your compute is older.
- Ability to **CREATE SCHEMA** in some catalog (on a trial, `workspace` usually works).

Full detail: [`docs/prerequisites.md`](docs/prerequisites.md).

---

## Get the assets — two ways

### Option A — Clone the repo as a Databricks Git folder (recommended)
1. In your workspace: **Workspace → Create → Git folder**.
2. Repo URL: `https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series`
3. Open the `.../metric-views-ai/notebooks/` folder — the data CSV is right beside it, so
   notebook `00` finds it automatically.

### Option B — Download & upload the notebooks
1. Download the files in [`notebooks/`](notebooks/) (they're Databricks source `.py` files).
2. In your workspace: **Workspace → Import** → drop the `.py` files in.
3. Download [`data/htg_bookings_raw.csv`](data/htg_bookings_raw.csv) and, when notebook `00`
   prompts, **upload it to the Unity Catalog Volume** it creates for you.

Then run **`00_setup`** → `01` → `02` → `03` → `04` → `05` in order.

---

## Repo contents

| Path | What it is |
|------|------------|
| `notebooks/00_setup.py` | Catalog/schema + data location |
| `notebooks/01_ingest_bronze_silver.py` | CSV → bronze → silver (Lakeflow Designer note) |
| `notebooks/02_build_gold_star_schema.py` | Fact + dimensions + PK/FK constraints |
| `notebooks/03_candidate_discovery_system_tables.py` | Find candidates from system tables |
| `notebooks/04_build_metric_views.py` | Progressive metric views + window/offset |
| `notebooks/05_ai_enrichment_and_genie.py` | AI Functions over comments + Genie |
| `notebooks/99_appendix_tpch_fallback.py` | Zero-setup fallback on `samples.tpch` |
| `data/htg_bookings_raw.csv` | Synthetic HTG bookings (30k rows, 2024–2026) |
| `data/generate_htg_bookings.py` | The generator (deterministic, stdlib only) |
| `demo/importBI_demo_runbook.md` | Presenter script: Power BI → Metric Views |
| `docs/metric-views-ai-semantics.md` | The written deep-dive (session page) |
| `docs/prerequisites.md` · `docs/facilitator-guide.md` | Setup + run-of-show |

---

## Clean up

```sql
DROP SCHEMA <catalog>.htg_metric_views_lab CASCADE;
```
