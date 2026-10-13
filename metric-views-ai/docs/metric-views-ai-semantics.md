# Governed Metrics with Unity Catalog Metric Views — & AI to build them fast

**Lunch & Learn · 15 Oct 2026 · `Latest`**

Your metrics already exist — scattered across gold tables and a Power BI semantic model.
The problem was never *computing* them; it was **agreeing** on them and then **governing** a
single definition. This session shows how to collapse that: let AI surface and convert what
you have, land it as a governed **Unity Catalog Metric View**, and let **Genie** answer over
it in plain English.

> **The brief:** *"…not only on metric views but also around the idea of leveraging genie / AI
> tooling to run over the top of our existing silver and gold layers in order to build these
> metrics views in a much faster fashion compared to us circling the drain trying to get
> alignment."*

[View the hands-on repo on GitHub →](https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series)

---

## 01 — Why Metric Views

A **Metric View** is a Unity Catalog object that defines **dimensions** and **measures** in
YAML, separately from how they're aggregated. One governed definition, consumed identically by
SQL, AI/BI dashboards, Alerts and **Genie**.

- Aggregation is **flexible at query time** — group by anything, ratios re-aggregate safely.
- Joins (star/snowflake) are **declared once** in the view, not re-written per query.
- It's **AI-native**: Genie reads the metric view's metadata to answer business questions.

**The point:** stop shipping three subtly different definitions of "TTV." Ship one.

---

## 02 — The acceleration: AI over what you already have

Two honest moves — neither is "AI magically invents your metrics":

**a) Convert the Power BI model you already aligned on.**
Genie Code's **`/importBI`** skill ingests a Power BI `.pbit`, extracts measures /
relationships / dimensions, and emits Metric View YAML + an AI/BI dashboard. It auto-converts
~**40–75%**; complex DAX (iterators, calc groups, bidirectional) needs human review. *That
review is the alignment — just far smaller.*

**b) Discover candidates from your gold tables.**
Genie Code won't scan gold and propose metrics on its own, so we do it with your **system
tables**: the most-**queried** and most-**joined** tables are your highest-confidence
candidates, and the joins people already run are the joins your metric view should declare.

[Read the Power BI → Metric Views demo runbook →](https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series/blob/main/metric-views-ai/demo/importBI_demo_runbook.md)

> ⚠️ `/importBI` needs AI/BI access + "Partner-powered AI" enabled (that toggle is removed
> **1 Nov 2026** — after which it's account-team-gated). We run it as a **presenter demo**;
> everyone does the candidate-discovery + build hands-on.

---

## 03 — Find the candidates (hands-on)

Notebook `03` crawls `system.access.table_lineage` and `system.query.history` to rank
most-referenced tables and most-joined pairs, then classifies columns into measures vs.
dimensions and emits a **suggested metric-view skeleton**. A deterministic
`information_schema` fallback works even on a brand-new trial.

[View notebook 03 →](https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series/blob/main/metric-views-ai/notebooks/03_candidate_discovery_system_tables.py)

---

## 04 — Build the Metric View (hands-on)

We layer up on an HTG bookings star schema:

- **Filtered measures** — `Cancellation Rate`, `Refund Exposure` via `FILTER (WHERE …)`.
- **Ratios** — `Average Booking Value`, `Commission Rate` (re-aggregate safely).
- **Joins** — customer / destination / product dimensions declared once.
- **Window & period-over-period** — trailing 30-day TTV; **YoY via `offset: -12 month`**.
- **Agentic metadata** — `comment`, `synonyms` ("TTV", "turnover"), `format` (AUD, %). This
  is what makes Genie answer *well*, not just *at all*.

```yaml
measures:
  - name: Total TTV
    expr: SUM(source.gross_booking_value)
    comment: "Total Transaction Value — gross value of all bookings"
    synonyms: [TTV, total transaction value, turnover]
    format: { type: currency, currency_code: AUD, decimal_places: 0 }
  - name: Monthly TTV LY
    expr: SUM(source.gross_booking_value)
    window:
      - order: Booking Month
        range: current
        semiadditive: last
        offset: -12 month
```

[View notebook 04 →](https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series/blob/main/metric-views-ai/notebooks/04_build_metric_views.py)

---

## 05 — AI over the text, then Genie over the metrics (hands-on)

`ai_classify` turns the free-text `customer_comments` into **sentiment** and **issue
category** dimensions (classify the *distinct* comments, join back — cheap at scale). That
feeds a Voice-of-Customer metric view (`Negative Comment Rate`, `TTV at Risk`). Then point
**Genie** at all three views and ask:

- *"Total **TTV** by region last quarter?"* · *"**Cancellation rate** by brand?"*
- *"**Year on year growth** in TTV for 2026?"* · *"**TTV at risk** by issue?"*

Every answer is consistent with the dashboards and SQL using the same views. That's the
antidote to circling the drain.

[View notebook 05 →](https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series/blob/main/metric-views-ai/notebooks/05_ai_enrichment_and_genie.py)

---

## 📎 Resources & Hands-On

- **Repo / all notebooks:** <https://github.com/VNSHANPR/Databricks_Lunch_N_Learn_Series>
- **Prerequisites:** [`docs/prerequisites.md`](prerequisites.md)
- **Facilitator run-of-show:** [`docs/facilitator-guide.md`](facilitator-guide.md)
- **Metric Views docs:** <https://docs.databricks.com/aws/en/metric-views/>
- **Window measures:** <https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures>
- **Genie Code `/importBI`:** <https://docs.databricks.com/aws/en/dashboards/manage/import-bi>
