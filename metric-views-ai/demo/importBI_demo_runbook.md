# Presenter Demo Runbook — Genie Code `/importBI` (Power BI → Metric Views)

**Audience-facing goal:** show that the metric definitions HTG already fought to align on
— sitting inside their Power BI semantic model — can be **imported** into governed Unity
Catalog Metric Views in minutes, instead of being hand-rebuilt. Humans *ratify*, they don't
*reinvent*.

> **Run this as a presenter-led demo, not a hands-on step.** It depends on entitlements that
> trial workspaces usually don't have (see Caveats). The hands-on equivalent participants do
> themselves is the **candidate-discovery notebook (`03`)** + **building the views (`04`)**.

---

## The honest framing (say this out loud)

- Genie Code **does not** scan your gold tables and invent metrics for you. It needs an
  **input** — your Power BI model — or human guidance.
- `/importBI` auto-converts roughly **40–75%** of a model. Simple DAX (SUM, AVG,
  DISTINCTCOUNT, basic time-intelligence/YoY) converts cleanly. Complex DAX — iterators
  (`SUMX`/`AVERAGEX`), calculation groups, bidirectional relationships, multi-filter
  `CALCULATE` — needs human review.
- **That split is the message:** the tool kills the busywork; your experts spend their time
  on the genuinely ambiguous 25–60%, not re-litigating "what does TTV mean."

---

## Pre-flight (do this before the session)

1. **Workspace:** use *your* FE demo workspace, not a trial — confirm **AI/BI access** and
   **"Partner-powered AI features"** are enabled (Settings → account/workspace).
   - ⚠️ **The "Partner-powered AI" toggle is being removed on 1 Nov 2026.** After that,
     enablement is via your Databricks account team. Demo before then, or pre-arrange access.
2. **Sample model:** have a small `.pbit` (Power BI **template**) ready — ideally a sanitised
   HTG-style sales/bookings model, else any sales model. Keep it < 100 MB (larger → stage
   via a UC Volume).
3. **Dry-run it once** the day before. Note which measures convert clean vs. flagged, so you
   can narrate confidently.

---

## Live demo script (~8 min)

1. **Open Genie Code** (full-page command centre, or from a notebook / SQL editor).
2. **Invoke the skill** — drag the `.pbit` into the chat, or type:
   ```
   /importBI @/Volumes/<catalog>/<schema>/<volume>/htg_sales.pbit
   ```
3. **Walk the output as it generates:**
   - Extracted **measures** → metric-view `measures` (point out DAX → SQL aggregate).
   - Extracted **relationships** → metric-view `joins`.
   - Extracted **dimensions/columns** → `dimensions`.
   - A generated **AI/BI dashboard** scaffold.
4. **Show a clean conversion** (e.g. `Total Sales = SUM(...)`) and **a flagged one** (e.g. a
   `SUMX` iterator) — read the tool's review note. *This is the ratify step.*
5. **Review & accept** the YAML. Run the `CREATE ... WITH METRICS` it proposes.
6. **Punchline:** "Minutes, not weeks — and now it's governed, and Genie can query it." Hand
   back to the hands-on notebooks where everyone builds one themselves.

---

## If the demo can't run (fallback)

- Show the **DAX → Metric View mapping table** (below) on a slide and talk through it.
- Jump straight to notebook `03` → `04`: discover candidates from system tables and build the
  view by hand. Same destination, no entitlement dependency.

### DAX → Metric View quick map

| Power BI element | → Metric View |
|---|---|
| Fact table | `source` + primary `measures` |
| Dimension table | `joins` entry |
| Relationship | `joins … on:` |
| `SUM/AVG/COUNT/DISTINCTCOUNT` measure | `measures.expr` aggregate |
| `CALCULATE([m], Year=2025)` (simple filter) | `FILTER (WHERE …)` on the measure |
| YoY `CALCULATE([m], DATEADD(…,-1,YEAR))` | window measure with `offset: -12 month` |
| 7/30-day moving average | window measure, `range: trailing N day` |
| Calculation groups / `SUMX` / bidirectional | ⚠️ manual rewrite |
| Row-level security | UC row filter / policy |

---

## Sources / further reading
- Import BI (Genie Code) docs: https://docs.databricks.com/aws/en/dashboards/manage/import-bi
- Genie Code: https://docs.databricks.com/aws/en/genie-code/
- Partner-powered AI (entitlement + Nov 1 note): https://docs.databricks.com/aws/en/databricks-ai/partner-powered
- Metric Views: https://docs.databricks.com/aws/en/metric-views/
