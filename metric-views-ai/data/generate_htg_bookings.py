#!/usr/bin/env python3
"""
Generate a synthetic, denormalised HTG (Horizon Travel Group) bookings
dataset for the Metric Views Lunch & Learn.

- Deterministic (fixed seed) so every participant gets identical numbers.
- Spans ~3 years of daily bookings so trailing-window and YoY/offset measures
  have enough history.
- Includes a free-text `customer_comments` column (correlated with booking
  status) for the AI-functions / sentiment step.
- Standard library only -> runs anywhere, no pip installs.

Output: htg_bookings_raw.csv  (one denormalised row per booking)
The lab notebooks split this into a gold star schema (fact + dimensions).
"""

import csv
import random
from datetime import date, timedelta

SEED = 42
N_ROWS = 30_000
START = date(2024, 1, 1)
END = date(2026, 9, 30)
OUT = "htg_bookings_raw.csv"

random.seed(SEED)

# --- Reference / dimension pools (brand & terminology are HTG-flavoured) ----

# HTG trades under several brands across leisure, corporate and SMB.
BRANDS = [
    ("Horizon Travel", "Leisure"),
    ("Corporate Voyager", "SMB"),
    ("Meridian Travel", "Corporate"),
    ("CampusTrips", "Leisure"),
    ("Journey Partners", "Leisure"),
]

PRODUCT_TYPES = ["Flight", "Hotel", "Package", "Cruise", "Tour", "Car Hire", "Travel Insurance"]

CHANNELS = ["Store", "Online", "Call Centre", "Mobile App", "Corporate Portal"]

LOYALTY_TIERS = ["None", "Silver", "Gold", "Platinum"]

# destination_id -> (city, country, region)
DESTINATIONS = [
    ("Sydney", "Australia", "APAC"),
    ("Melbourne", "Australia", "APAC"),
    ("Brisbane", "Australia", "APAC"),
    ("Auckland", "New Zealand", "APAC"),
    ("Bali", "Indonesia", "APAC"),
    ("Singapore", "Singapore", "APAC"),
    ("Tokyo", "Japan", "APAC"),
    ("Bangkok", "Thailand", "APAC"),
    ("London", "United Kingdom", "EMEA"),
    ("Paris", "France", "EMEA"),
    ("Dubai", "UAE", "EMEA"),
    ("Rome", "Italy", "EMEA"),
    ("New York", "United States", "Americas"),
    ("Los Angeles", "United States", "Americas"),
    ("Honolulu", "United States", "Americas"),
    ("Vancouver", "Canada", "Americas"),
    ("Fiji", "Fiji", "APAC"),
    ("Queenstown", "New Zealand", "APAC"),
]

HOME_CITIES = [
    ("Sydney", "Australia"), ("Melbourne", "Australia"), ("Brisbane", "Australia"),
    ("Perth", "Australia"), ("Adelaide", "Australia"), ("Auckland", "New Zealand"),
    ("London", "United Kingdom"), ("Toronto", "Canada"),
]

STATUSES = ["Confirmed", "Completed", "Cancelled", "Amended"]
# rough target mix
STATUS_WEIGHTS = [0.46, 0.40, 0.09, 0.05]

# Comment banks keyed by sentiment, so ai_classify has a real signal to find.
POSITIVE_COMMENTS = [
    "Fantastic service, our consultant went above and beyond.",
    "Really easy booking experience, would use again.",
    "Great value package and the hotel was exactly as described.",
    "Consultant found us a cheaper fare than we expected. Very happy.",
    "Smooth check-in and the itinerary was perfectly organised.",
    "Loved the trip, everything was seamless from start to finish.",
    "Quick responses and helpful advice on visas. Five stars.",
    "Best travel agent we've dealt with, highly recommend.",
]
NEUTRAL_COMMENTS = [
    "Booking was fine, nothing special but no issues.",
    "All as expected. Standard experience.",
    "Got what we paid for. Average service.",
    "Itinerary came through on time. No complaints.",
    "Okay overall, a couple of minor delays in email replies.",
]
NEGATIVE_COMMENTS = [
    "Flight was cancelled and the refund took weeks to process.",
    "Very disappointed, we were charged twice and had to chase it up.",
    "Long wait on the phone and the consultant seemed rushed.",
    "Hotel was not as advertised, felt misled by the package.",
    "Refund still not received after multiple follow ups. Frustrating.",
    "Had to cancel due to a schedule change and the fees were steep.",
    "Communication was poor, nobody told us the itinerary changed.",
]
NO_COMMENT_RATE = 0.35  # many bookings have no comment at all


def pick_status():
    r = random.random()
    cum = 0.0
    for s, w in zip(STATUSES, STATUS_WEIGHTS):
        cum += w
        if r <= cum:
            return s
    return STATUSES[-1]


def pick_comment(status):
    if random.random() < NO_COMMENT_RATE:
        return ""
    # Correlate sentiment with status so the AI step shows a real pattern.
    if status in ("Cancelled",):
        bank = random.choices(
            [NEGATIVE_COMMENTS, NEUTRAL_COMMENTS, POSITIVE_COMMENTS],
            weights=[0.70, 0.22, 0.08])[0]
    elif status in ("Amended",):
        bank = random.choices(
            [NEGATIVE_COMMENTS, NEUTRAL_COMMENTS, POSITIVE_COMMENTS],
            weights=[0.45, 0.35, 0.20])[0]
    elif status in ("Completed",):
        bank = random.choices(
            [POSITIVE_COMMENTS, NEUTRAL_COMMENTS, NEGATIVE_COMMENTS],
            weights=[0.62, 0.28, 0.10])[0]
    else:  # Confirmed (trip not taken yet)
        bank = random.choices(
            [POSITIVE_COMMENTS, NEUTRAL_COMMENTS, NEGATIVE_COMMENTS],
            weights=[0.45, 0.45, 0.10])[0]
    return random.choice(bank)


def seasonal_weight(d: date) -> float:
    """Mild seasonality + gentle year-on-year growth so trend charts look real."""
    # Southern-hemisphere peaks: Dec/Jan (summer) and Jun/Jul (ski/northern summer)
    month_factor = {
        1: 1.3, 2: 1.0, 3: 0.9, 4: 1.0, 5: 0.85, 6: 1.15,
        7: 1.2, 8: 0.95, 9: 0.9, 10: 1.05, 11: 1.1, 12: 1.35,
    }[d.month]
    years_in = (d - START).days / 365.0
    growth = 1.0 + 0.12 * years_in  # ~12% YoY growth
    return month_factor * growth


# Pre-build a date-weighted sampling list.
span_days = (END - START).days
day_weights = []
for i in range(span_days + 1):
    d = START + timedelta(days=i)
    day_weights.append(seasonal_weight(d))


def gross_value(product_type, pax):
    base = {
        "Flight": 650, "Hotel": 220, "Package": 1800, "Cruise": 2400,
        "Tour": 1500, "Car Hire": 90, "Travel Insurance": 85,
    }[product_type]
    noise = random.uniform(0.6, 1.8)
    return round(base * pax * noise, 2)


# --- Generate rows ----------------------------------------------------------

n_customers = 6000
n_consultants = 120

rows = []
for i in range(N_ROWS):
    booking_id = 1_000_000 + i

    day_offset = random.choices(range(span_days + 1), weights=day_weights, k=1)[0]
    booking_date = START + timedelta(days=day_offset)
    lead_time = int(abs(random.gauss(45, 35))) + 1
    travel_date = booking_date + timedelta(days=lead_time)

    brand, segment = random.choice(BRANDS)
    product_type = random.choice(PRODUCT_TYPES)
    channel = random.choice(CHANNELS)

    cust_id = random.randint(1, n_customers)
    cust_home_city, cust_home_country = random.choice(HOME_CITIES)
    loyalty = random.choices(LOYALTY_TIERS, weights=[0.5, 0.25, 0.17, 0.08])[0]

    dest_city, dest_country, dest_region = random.choice(DESTINATIONS)
    dest_id = DESTINATIONS.index((dest_city, dest_country, dest_region)) + 1

    consultant_id = random.randint(1, n_consultants)

    status = pick_status()
    pax = random.choices([1, 2, 3, 4, 5, 6], weights=[0.35, 0.34, 0.12, 0.11, 0.05, 0.03])[0]

    ttv = gross_value(product_type, pax)
    # Commission ~ 8-14% of TTV depending on product
    comm_rate = {
        "Flight": 0.07, "Hotel": 0.12, "Package": 0.13, "Cruise": 0.14,
        "Tour": 0.13, "Car Hire": 0.10, "Travel Insurance": 0.30,
    }[product_type]
    commission = round(ttv * comm_rate * random.uniform(0.85, 1.15), 2)

    refund = 0.0
    if status == "Cancelled":
        refund = round(ttv * random.uniform(0.4, 1.0), 2)
    elif status == "Amended" and random.random() < 0.3:
        refund = round(ttv * random.uniform(0.05, 0.25), 2)

    comment = pick_comment(status)

    rows.append([
        booking_id,
        booking_date.isoformat(),
        travel_date.isoformat(),
        lead_time,
        cust_id,
        f"Customer {cust_id:05d}",
        segment,
        loyalty,
        cust_home_city,
        cust_home_country,
        dest_id,
        dest_city,
        dest_country,
        dest_region,
        f"PRD-{product_type[:3].upper()}-{PRODUCT_TYPES.index(product_type)+1:02d}",
        product_type,
        brand,
        channel,
        consultant_id,
        status,
        pax,
        ttv,
        commission,
        refund,
        comment,
    ])

# Sort by booking_date for a natural-looking file.
rows.sort(key=lambda r: r[1])

HEADER = [
    "booking_id", "booking_date", "travel_date", "lead_time_days",
    "customer_id", "customer_name", "customer_segment", "loyalty_tier",
    "home_city", "home_country",
    "destination_id", "destination_city", "destination_country", "destination_region",
    "product_id", "product_type", "brand", "channel", "consultant_id",
    "booking_status", "pax_count",
    "gross_booking_value", "commission_amount", "refund_amount",
    "customer_comments",
]

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    w.writerows(rows)

print(f"Wrote {len(rows):,} rows to {OUT}")
print(f"Date range: {rows[0][1]} .. {rows[-1][1]}")
