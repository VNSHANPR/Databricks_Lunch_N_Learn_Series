-- ============================================================================
-- STAGE 2 · SILVER (clean, typed, quality-enforced)
-- Reads a STREAM from Bronze and applies casts + cleaning per new row, so it stays
-- in sync with no full recompute. Data-quality EXPECTATIONS are the point of this
-- stage: the first two DROP bad rows, the rest are tracked (warn) in the pipeline's
-- data-quality metrics so you can see violations without failing the run.
--   ON VIOLATION DROP ROW   → row is quarantined out of Silver
--   (no clause)             → row is kept, violation counted in the DQ dashboard
--   ON VIOLATION FAIL UPDATE→ would stop the pipeline (use for hard invariants)
-- ============================================================================
CREATE OR REFRESH STREAMING TABLE bookings_silver
  (CONSTRAINT valid_booking_id     EXPECT (booking_id IS NOT NULL)                 ON VIOLATION DROP ROW,
   CONSTRAINT non_negative_value   EXPECT (gross_booking_value >= 0)               ON VIOLATION DROP ROW,
   CONSTRAINT positive_pax         EXPECT (pax_count > 0),
   CONSTRAINT known_status         EXPECT (booking_status IN ('Confirmed','Completed','Cancelled','Amended')),
   CONSTRAINT travel_after_booking EXPECT (travel_date >= booking_date),
   CONSTRAINT refund_within_value  EXPECT (refund_amount <= gross_booking_value))
  COMMENT 'Cleaned, typed bookings with data-quality expectations applied.'
  TBLPROPERTIES ('quality' = 'silver')
AS SELECT
     booking_id,
     to_date(booking_date) AS booking_date,
     to_date(travel_date)  AS travel_date,
     lead_time_days,
     customer_id, customer_name, customer_segment, loyalty_tier, home_city, home_country,
     destination_id, destination_city, destination_country, destination_region,
     product_id, product_type, brand,
     channel, consultant_id, booking_status, pax_count,
     CAST(gross_booking_value AS DECIMAL(12,2)) AS gross_booking_value,
     CAST(commission_amount   AS DECIMAL(12,2)) AS commission_amount,
     CAST(refund_amount       AS DECIMAL(12,2)) AS refund_amount,
     NULLIF(TRIM(customer_comments), '')        AS customer_comments
FROM STREAM(bookings_bronze);
