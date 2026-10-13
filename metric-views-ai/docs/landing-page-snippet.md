# Landing-page snippet (paste into the series index)

Drop-in content to add this session to the Lunch & Learn landing page, matching the existing
format (session row with a `Latest` badge + a numbered deep-dive module). Move the previous
"Latest" badge to this one.

## 1) Session list row (top of page)

| Date | Title | Status |
|------|-------|--------|
| **15 Oct 2026** | **Governed Metrics with UC Metric Views — & AI to build them fast** | `Latest` |

(Change the previous session — *17 Sep 2026* — from `Latest` to no badge.)

## 2) New numbered deep-dive module

> Renumber to follow the last module on the page (shown here as `09`).

### 09 — Governed Metrics with UC Metric Views (+ AI acceleration)

Build a single source of truth for business metrics with **Unity Catalog Metric Views**, and
use **Genie / AI tooling** to get there fast over your existing silver & gold layers — the
answer to "stop circling the drain trying to get alignment."

- **Acceleration:** Genie Code `/importBI` converts a Power BI model → Metric Views
  (presenter demo); system-table crawl finds candidates (hands-on).
- **Build:** filtered measures, ratios, star-schema joins, window / YoY-offset measures, and
  **agentic metadata** (synonyms, comments, formats) that make Genie answer well.
- **AI over text:** `ai_classify` turns customer comments into sentiment/issue dimensions → a
  Voice-of-Customer metric view → Genie Q&A.

[Read the deep-dive →](metric-views-ai-semantics.md) ·
[View on GitHub →](https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series/tree/main/metric-views-ai)

## 3) Suggested repo layout for this session

Place the staged folder under the repo as `metric-views-ai/` so the links above resolve:

```
Databricks_Lunch_N_Learn_Series/
└── metric-views-ai/
    ├── README.md
    ├── notebooks/   00..05 + 99
    ├── data/        htg_bookings_raw.csv  (+ generator)
    ├── demo/        importBI_demo_runbook.md
    └── docs/        metric-views-ai-semantics.md, prerequisites.md, facilitator-guide.md
```
