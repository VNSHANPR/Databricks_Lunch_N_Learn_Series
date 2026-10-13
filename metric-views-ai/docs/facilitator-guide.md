# Facilitator guide — run of show

**Format:** hands-on, ~75 min. Two presenters (e.g. Ben + Vinay). Attendees in their own
workspaces (trials fine). Keep one shared screen on the slides / your demo workspace.

## Timing

| Time | Segment | Who | Mode |
|------|---------|-----|------|
| 0:00–0:05 | **Framing** — the "circling the drain" problem; metric views as the single source of truth; AI to shortcut alignment | Presenter A | Slides |
| 0:05–0:15 | **Act 1 · Acceleration demo** — Genie Code `/importBI`: Power BI model → Metric Views. Narrate clean vs. flagged DAX. *(see `demo/importBI_demo_runbook.md`)* | Presenter A | Demo |
| 0:15–0:22 | **Candidate discovery** — notebook `03`: crawl system tables for most-queried / most-joined → auto-suggested view | Presenter B | Hands-on |
| 0:22–0:30 | **Data prep** — notebooks `00`–`02`: CSV → silver → gold star schema (mention Lakeflow Designer no-code path) | All | Hands-on |
| 0:30–0:55 | **Build the metric views** — notebook `04`: basic → filtered → ratios → joins → window/offset → agentic metadata | Presenter B | Hands-on |
| 0:55–1:05 | **AI + Genie** — notebook `05`: `ai_classify` over comments → VoC view → ask Genie in plain English | Presenter A | Hands-on |
| 1:05–1:15 | **Debrief & HTG next steps** — map to their Power BI estate; the ratify-don't-reinvent play | All | Discuss |

> Tight on time? Pre-run `00`–`02` live-coded is optional — tell attendees to just run those
> cells while you talk, and spend the saved minutes on `04` (the hero) and Genie.

## Facilitation tips
- **Run `03` before `00`–`02`?** On a brand-new trial, system tables are empty — so `03`
  Sections A/B won't show history. Either (a) demo A/B on *your* seasoned workspace on the
  shared screen, and have attendees run Section C (information_schema) themselves; or (b) run
  `00`–`02` first, do a few queries, then come back to `03`.
- **The hero moment** is the agentic metadata in `04` + the first Genie question in `05` that
  resolves "TTV" via a synonym. Land that beat clearly.
- **Honesty sells:** be explicit that `/importBI` is ~40–75% automatic. The remaining human
  review *is* the alignment — just dramatically smaller.

## Common issues
| Symptom | Fix |
|---|---|
| `CREATE SCHEMA` denied | Pick a catalog they own; on trials try `workspace`. |
| Window view in `04` errors | Compute < DBR 18.0 → it prints guidance; use serverless. |
| `ai_classify` errors in `05` | AI Functions/FM API not enabled → cell skips; Genie section still runs. |
| `03` Sections A/B empty | No system-table history/grants → use Section C. |
| CSV not found in `00` | Upload it to the Volume `00` created, re-run the cell. |

## Travel-domain talking points
- A travel business's semantic layer often lives in **Power BI** today → `/importBI` is the
  on-ramp, not a rebuild.
- **TTV** (Total Transaction Value) is modelled as a first-class measure with synonyms — use
  the business's own language.
- Tie governed metric views back to any existing **Genie adoption** — they make those Genie
  answers trustworthy and consistent.
