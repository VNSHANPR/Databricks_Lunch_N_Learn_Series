# Prerequisites & setup

## Workspace
- **Unity Catalog enabled.** A **free trial** works for the whole lab.
- Don't have one? Sign up at <https://www.databricks.com/try-databricks> (serverless, UC on
  by default). Allow ~10 min for first-time setup; do this **before** the session.

## Compute
- **Run the notebooks on serverless *notebook* compute.** It's on the current runtime, so
  every feature in the lab — including window/offset measures — is available. (Validated on
  DBR 18.2.)
- ⚠️ **Watch out for old SQL warehouses.** A SQL warehouse on an older channel can be below
  DBR 16.4 and will reject every metric view with a confusing
  `METRIC_VIEW_INVALID_VIEW_DEFINITION` / "Failed to parse YAML" error. If you see that, the
  YAML is fine — your *compute* is too old. Switch to serverless notebook compute, or move the
  warehouse to the **Current/Preview** channel.
- Runtime floors:

| Feature | Minimum |
|---|---|
| Metric Views (v1.1 YAML, joins, filters, ratios, agentic metadata) | DBR 16.4+ (best 17.2+) |
| **Window & offset measures** (notebook `04` trends view) | **DBR 18.0+** (18.1+ for inclusive/exclusive) |
| `ai_classify` / AI Functions (notebook `05`) | Serverless + Foundation Model API |
| System tables (notebook `03` Sections A/B) | Enabled by metastore admin + `SELECT` granted |

> Missing entitlements (AI Functions, system tables)? Those notebooks **degrade gracefully**
> and tell you the fallback. The one thing you must get right is the **runtime** — metric
> views simply won't create below DBR 16.4.

## Permissions
- `CREATE SCHEMA` in a catalog you can write to (trial: `workspace` usually works).
- `CREATE VOLUME`, `CREATE TABLE` in that schema.
- For notebook `03` system-table sections: `SELECT` on `system.query.history` and
  `system.access.table_lineage` (ask a metastore admin). Without it, use Section C
  (information_schema) — it always works.

## Pre-session checklist (facilitators send this out)
- [ ] Can log in to a UC-enabled workspace (trial OK).
- [ ] Can start a **serverless** warehouse / compute.
- [ ] Cloned the repo as a Git folder **or** downloaded the notebooks + CSV.
- [ ] Ran `00_setup` to the "✅ Setup done" cell.
