# oCFO Agent Platform — CI/CD with Declarative Automation Bundles

Companion notes for the **CI/CD** tab. The full project lives in its own repo:
**https://github.com/VNSHANPR/ocfo-agent-platform**

## What it is

One Declarative Automation Bundle (DABs) that ships the whole agentic stack for the
Office-of-the-CFO demo as Infrastructure-as-Code and promotes it across
**dev → preprod → prod**:

- **Data layer** — governed Unity Catalog function tools + certified metric views
- **Genie layer** — 4 curated Genie spaces declared as **native `genie_spaces` resources**
- **Supervisor** — a managed Agent Bricks Multi-Agent Supervisor wiring the Genie spaces,
  the Knowledge Assistant (as a direct subagent) and the UC-function tools

## How the bundle is wired

| Piece | Where | How it deploys |
|-------|-------|----------------|
| Genie spaces | `resources.genie_spaces` in `databricks.yml` (engine: `direct`) | Declaratively on `bundle deploy` — each backed by a versioned `genie/*.geniespace.json` |
| UC tools + metric views | `src/deploy_data_layer.py` | Job task (idempotent, catalog-parameterized) |
| Supervisor + instructions | `config/supervisor_instructions.yml` + `src/create_supervisor.py` | Job task — reads the config and the Genie ids via `${resources.genie_spaces.<key>.id}` |

Everything is **catalog-parameterized**, so each environment sets its own `catalog` (and
`ka_tile_id`) and the same code promotes unchanged.

## Genie space resource (excerpt)

```yaml
bundle:
  name: ocfo_agent_platform
  engine: direct           # required for the genie_spaces resource

resources:
  genie_spaces:
    travel_expense:
      title: "Travel & Expense Spend — Concur"
      description: "Employee travel and expense spend, out-of-policy spend, merchants."
      warehouse_id: ${var.warehouse_id}
      file_path: ./genie/travel_expense.geniespace.json
      permissions:
        - level: CAN_RUN
          group_name: users
```

## Supervisor config (excerpt)

```yaml
# config/supervisor_instructions.yml — versioned routing policy + subagents
instructions: |
  Route each question to the single most appropriate specialist agent...
agents:
  - name: office_of_cfo         # Genie subagent
    kind: genie
    key: ocfo
  - name: financial_results_docs # Knowledge Assistant subagent
    kind: knowledge_assistant
    key: ka
uc_function_tools:
  - name: agent_tools.fx_convert
```

## Requirements

- **Databricks CLI ≥ 1.16.x** (older CLIs don't recognize `genie_spaces`).
- A SQL warehouse, the source schemas in the target catalog, and — for the docs subagent —
  a Knowledge Assistant whose `tile_id` you set via the `ka_tile_id` variable.

## Deploy

```bash
databricks bundle validate --target dev
databricks bundle deploy   --target dev
databricks bundle run ocfo_agent_platform_deploy --target dev

# promote unchanged
databricks bundle deploy --target preprod && databricks bundle run ocfo_agent_platform_deploy --target preprod
databricks bundle deploy --target prod    && databricks bundle run ocfo_agent_platform_deploy --target prod
```

No credentials are stored in the bundle — auth comes from your Databricks CLI profile, and
the deploy path is scoped per-user via `${workspace.current_user.userName}`.
