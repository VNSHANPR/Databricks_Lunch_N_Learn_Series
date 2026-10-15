# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Build the Metric Views
# MAGIC
# MAGIC We build up from a simple view to a **production, AI-ready** metric view, layering in:
# MAGIC filtered measures → ratios → star-schema joins → **agentic metadata** (synonyms,
# MAGIC comments, format). Then a separate **trends** view adds **window & period-over-period
# MAGIC (offset)** measures.
# MAGIC
# MAGIC All measures are queried with the `MEASURE()` function. `SELECT *` is **not** supported.

# COMMAND ----------

# Catalog & schema are chosen ONCE in notebook 00 (its widgets) and recorded in a small
# JSON config on the lab Volume. Downstream notebooks READ that config — they define no
# catalog/schema of their own, so there's nothing to keep in sync. We locate the config by
# scanning the catalogs you can see for the lab schema's config file.
import json

LAB_SCHEMA = "htg_metric_views_lab"   # lab's fixed schema name — used only to locate 00's config

def _read_lab_cfg():
    cats = []
    try:
        cats.append(spark.sql("SELECT current_catalog()").first()[0])
    except Exception:
        pass
    try:
        cats += [r[0] for r in spark.sql("SHOW CATALOGS").collect()]
    except Exception:
        pass
    for cat in dict.fromkeys(cats):
        try:
            return json.loads(dbutils.fs.head(
                f"/Volumes/{cat}/{LAB_SCHEMA}/raw_files/_htg_config.json"))
        except Exception:
            continue
    return None

_cfg = _read_lab_cfg()
assert _cfg, ("Lab config not found — run 00_setup first. It picks the catalog/schema and "
              "writes _htg_config.json on the lab Volume, which every downstream notebook reads.")
CATALOG, SCHEMA = _cfg["htg.catalog"], _cfg["htg.schema"]
FQ = f"{CATALOG}.{SCHEMA}"
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")
print(f"Using {FQ} (from 00_setup config)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — The AI-ready metric view
# MAGIC
# MAGIC Note the **agentic metadata** on every field and measure:
# MAGIC - `comment` — plain-English definition (what Genie reads to understand intent).
# MAGIC - `synonyms` — alternative names so Genie matches business language
# MAGIC   (e.g. *"TTV"*, *"total transaction value"* → the TTV measure).
# MAGIC - `format` — currency/number formatting so results render correctly everywhere.
# MAGIC
# MAGIC This is what makes the difference between a metric view Genie *can* use and one it
# MAGIC uses *well*.

# COMMAND ----------

mv_bookings = f"""
CREATE OR REPLACE VIEW {FQ}.mv_bookings
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "HTG bookings — governed KPIs for leisure, corporate and SMB travel. Single source of truth for TTV, commission and booking volumes."
source: {FQ}.fact_bookings

joins:
  - name: customer
    source: {FQ}.dim_customer
    on: source.customer_id = customer.customer_id
  - name: destination
    source: {FQ}.dim_destination
    on: source.destination_id = destination.destination_id
  - name: product
    source: {FQ}.dim_product
    on: source.product_id = product.product_id

dimensions:
  - name: Booking Date
    expr: source.booking_date
    comment: "Date the booking was made"
    synonyms: [date, booking day, transaction date]
  - name: Booking Month
    expr: DATE_TRUNC('MONTH', source.booking_date)
    comment: "Month the booking was made"
    synonyms: [month]
  - name: Booking Status
    expr: source.booking_status
    comment: "Confirmed, Completed, Cancelled or Amended"
    synonyms: [status]
  - name: Channel
    expr: source.channel
    comment: "Sales channel: Store, Online, Call Centre, Mobile App, Corporate Portal"
    synonyms: [sales channel, booking channel]
  - name: Brand
    expr: product.brand
    comment: "HTG trading brand"
    synonyms: [trading brand, business]
  - name: Product Type
    expr: product.product_type
    comment: "Flight, Hotel, Package, Cruise, Tour, Car Hire or Travel Insurance"
    synonyms: [product, product category]
  - name: Customer Segment
    expr: customer.customer_segment
    comment: "Leisure, Corporate or SMB"
    synonyms: [segment]
  - name: Loyalty Tier
    expr: customer.loyalty_tier
    synonyms: [tier, membership]
  - name: Destination Region
    expr: destination.destination_region
    comment: "APAC, EMEA or Americas"
    synonyms: [region, geography]
  - name: Destination Country
    expr: destination.destination_country
    synonyms: [country]

measures:
  - name: Booking Count
    expr: COUNT(1)
    comment: "Number of bookings"
    synonyms: [bookings, number of bookings, volume]
    format:
      type: number
      decimal_places:
        type: exact
        places: 0

  - name: Total TTV
    expr: SUM(source.gross_booking_value)
    comment: "Total Transaction Value — gross value of all bookings"
    synonyms: [TTV, total transaction value, gross booking value, sales, turnover]
    format:
      type: currency
      currency_code: AUD
      decimal_places:
        type: exact
        places: 0

  - name: Total Commission
    expr: SUM(source.commission_amount)
    comment: "Commission / margin earned by HTG"
    synonyms: [commission, margin, revenue]
    format:
      type: currency
      currency_code: AUD
      decimal_places:
        type: exact
        places: 0

  # --- Filtered measures ---
  - name: Cancelled Bookings
    expr: COUNT(1) FILTER (WHERE source.booking_status = 'Cancelled')
    comment: "Bookings that were cancelled"
    synonyms: [cancellations]
    format:
      type: number
      decimal_places:
        type: exact
        places: 0

  - name: Cancellation Rate
    expr: COUNT(1) FILTER (WHERE source.booking_status = 'Cancelled') * 1.0 / COUNT(1)
    comment: "Share of bookings cancelled"
    synonyms: [cancel rate, cancellation %]
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1

  - name: Refund Exposure
    expr: SUM(source.refund_amount)
    comment: "Total value refunded — money at risk / returned to customers"
    synonyms: [refunds, refund value, money refunded]
    format:
      type: currency
      currency_code: AUD
      decimal_places:
        type: exact
        places: 0

  # --- Ratio measures (re-aggregate safely) ---
  - name: Average Booking Value
    expr: SUM(source.gross_booking_value) / COUNT(1)
    comment: "Average TTV per booking"
    synonyms: [ABV, avg booking value, average TTV]
    format:
      type: currency
      currency_code: AUD
      decimal_places:
        type: exact
        places: 0

  - name: Commission Rate
    expr: SUM(source.commission_amount) / NULLIF(SUM(source.gross_booking_value), 0)
    comment: "Commission as a percentage of TTV — HTG's effective margin"
    synonyms: [margin rate, take rate, commission %]
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1

  - name: Active Customers
    expr: COUNT(DISTINCT source.customer_id)
    comment: "Distinct customers who booked"
    synonyms: [unique customers, customer count]
    format:
      type: number
      decimal_places:
        type: exact
        places: 0
$$
"""
try:
    spark.sql(mv_bookings)
    print("Created metric view:", f"{FQ}.mv_bookings")
except Exception as e:
    msg = str(e)
    print("⚠️  Could not create the metric view.")
    if "Failed to parse YAML" in msg or "INVALID_VIEW_DEFINITION" in msg:
        print("   The YAML failed validation. The usual culprits are in a `format` block:")
        print("   • decimal_places must be an OBJECT, not a bare integer —")
        print("     decimal_places: {type: exact, places: N}")
        print("   • the percent format type is spelled `percentage`, not `percent`")
    if "PARSE_SYNTAX_ERROR" in msg or "Unsupported" in msg:
        print("   If instead it's a syntax/unsupported error, your compute may be below")
        print("   DBR 16.4 — metric views need 16.4+ (17.2+ recommended). Use serverless")
        print("   notebook compute (current runtime), or a SQL warehouse on Current/Preview.")
    print("   Detail:", msg[:300])
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ### Query it — flexible aggregation at query time
# MAGIC All measures via `MEASURE()`; group by any dimension(s).

# COMMAND ----------

display(spark.sql(f"""
  SELECT
    `Destination Region`,
    `Product Type`,
    MEASURE(`Total TTV`)             AS ttv,
    MEASURE(`Total Commission`)      AS commission,
    MEASURE(`Commission Rate`)       AS commission_rate,
    MEASURE(`Cancellation Rate`)     AS cancel_rate,
    MEASURE(`Average Booking Value`) AS abv
  FROM {FQ}.mv_bookings
  GROUP BY ALL
  ORDER BY ttv DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Trends view: window & period-over-period (offset) measures
# MAGIC
# MAGIC Window measures (trailing/rolling windows) and `offset` (period-over-period) are
# MAGIC **GA**, but need **DBR 18.0+** (18.1+ for the `inclusive/exclusive` modifier). If your
# MAGIC compute is older, this cell prints guidance instead of failing — the rest of the lab
# MAGIC still works.

# COMMAND ----------

mv_trends = f"""
CREATE OR REPLACE VIEW {FQ}.mv_bookings_trends
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "HTG booking trends — trailing windows and year-over-year growth"
source: {FQ}.fact_bookings

dimensions:
  - name: Booking Date
    expr: source.booking_date
  - name: Booking Month
    expr: DATE_TRUNC('MONTH', source.booking_date)

measures:
  - name: Daily TTV
    expr: SUM(source.gross_booking_value)
    format:
      type: currency
      currency_code: AUD

  # Rolling 30-day TTV (trailing window, excludes the current day by default)
  - name: TTV 30d Rolling
    expr: SUM(source.gross_booking_value)
    comment: "Trailing 30-day TTV"
    synonyms: [rolling 30 day TTV, 30d TTV]
    window:
      - order: Booking Date
        range: trailing 30 day
        semiadditive: last
    format:
      type: currency
      currency_code: AUD

  # Monthly TTV and the same month a year earlier (offset), then YoY growth %
  - name: Monthly TTV
    expr: SUM(source.gross_booking_value)
    window:
      - order: Booking Month
        range: current
        semiadditive: last
    format:
      type: currency
      currency_code: AUD

  - name: Monthly TTV LY
    expr: SUM(source.gross_booking_value)
    comment: "Monthly TTV for the same month last year"
    synonyms: [TTV last year, prior year TTV]
    window:
      - order: Booking Month
        range: current
        semiadditive: last
        offset: -12 month
    format:
      type: currency
      currency_code: AUD

  - name: TTV YoY Growth
    expr: (MEASURE(`Monthly TTV`) - MEASURE(`Monthly TTV LY`)) / NULLIF(MEASURE(`Monthly TTV LY`), 0)
    comment: "Year-over-year TTV growth"
    synonyms: [YoY growth, year on year growth]
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1
$$
"""
try:
    spark.sql(mv_trends)
    print("Created trends metric view:", f"{FQ}.mv_bookings_trends")
except Exception as e:
    print("⚠️  Could not create window/offset view — your compute is likely below DBR 18.0.")
    print("   Window & offset measures are GA on DBR 18.0+ (18.1+ for inclusive/exclusive).")
    print("   Fix: attach a serverless warehouse/compute on the current channel, then re-run.")
    print("   Detail:", str(e)[:200])

# COMMAND ----------

# Year-over-year TTV by month (only runs if the trends view was created above).
# Note: spark.catalog.tableExists() isn't available on serverless (Spark Connect),
# so we just try the query and fall back to a message if the view isn't there.
try:
    display(spark.sql(f"""
      SELECT
        `Booking Month`,
        MEASURE(`Monthly TTV`)    AS ttv,
        MEASURE(`Monthly TTV LY`) AS ttv_last_year,
        MEASURE(`TTV YoY Growth`) AS yoy_growth
      FROM {FQ}.mv_bookings_trends
      WHERE `Booking Month` >= '2025-01-01'
      GROUP BY ALL
      ORDER BY `Booking Month`
    """))
except Exception:
    print("Trends view not available (needs DBR 18.0+). Skipping YoY query.")

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ Metric views built. Continue to **`05_ai_enrichment_and_genie`** to mine the free-text
# MAGIC comments with AI and let Genie answer questions over these governed metrics.
