-- ============================================================================
-- STAGE 3 · PROD / GOLD (business-ready Kimball star schema)
-- The fact is an append-only STREAMING TABLE from Silver. The dimensions are
-- MATERIALIZED VIEWS (dedup is an aggregation over the whole table — an MV job,
-- not a streaming one). This is the Gold your Metric Views (notebook 04) point at.
--
-- If bookings can be amended/cancelled after the fact, swap fact_bookings for an
-- AUTO CDC flow keyed on booking_id (upsert), and SCD Type 2 dimensions if you need
-- "segment as-of booking date". Kept append-only here for a clean teaching example.
-- ============================================================================

CREATE OR REFRESH STREAMING TABLE fact_bookings
  COMMENT 'Gold fact — one row per booking event.'
  TBLPROPERTIES ('quality' = 'gold')
AS SELECT
     booking_id, booking_date, travel_date, lead_time_days,
     customer_id, destination_id, product_id, consultant_id, channel,
     booking_status, pax_count,
     gross_booking_value, commission_amount, refund_amount,
     customer_comments
FROM STREAM(bookings_silver);

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW dim_customer
  COMMENT 'Latest attributes per customer (Type 1).'
AS SELECT customer_id, customer_name, customer_segment, loyalty_tier, home_city, home_country
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY booking_date DESC) AS rn
  FROM bookings_silver
) WHERE rn = 1;

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW dim_destination
AS SELECT destination_id, destination_city, destination_country, destination_region
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY destination_id ORDER BY booking_date DESC) AS rn
  FROM bookings_silver
) WHERE rn = 1;

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW dim_product
AS SELECT product_id, product_type, brand
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY booking_date DESC) AS rn
  FROM bookings_silver
) WHERE rn = 1;

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW dim_date
  COMMENT 'Distinct booking + travel dates with calendar attributes.'
AS SELECT DISTINCT
     d                         AS date_key,
     YEAR(d)                   AS year,
     CONCAT('Q', QUARTER(d))   AS quarter,
     DATE_FORMAT(d, 'yyyy-MM') AS month,
     DATE_FORMAT(d, 'MMMM')    AS month_name,
     DATE_FORMAT(d, 'EEEE')    AS day_of_week
FROM (
  SELECT booking_date AS d FROM bookings_silver WHERE booking_date IS NOT NULL
  UNION
  SELECT travel_date  AS d FROM bookings_silver WHERE travel_date  IS NOT NULL
);
