import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from analyze import daily_occupancy, load_queries, monthly_kpis  # noqa: E402


def test_checkout_day_is_not_counted():
    bookings = pd.DataFrame(
        {"check_in": ["2024-07-01"], "check_out": ["2024-07-04"], "price_per_night": [100.0]}
    )
    daily = daily_occupancy(bookings, total_rooms=10)
    assert len(daily) == 3                      # nights of 1st, 2nd and 3rd
    assert daily["rooms_sold"].sum() == 3
    assert daily["occupancy_pct"].iloc[0] == 10.0


def test_monthly_kpis():
    bookings = pd.DataFrame(
        {"check_in": ["2024-07-01", "2024-07-01"],
         "check_out": ["2024-07-03", "2024-07-02"],
         "price_per_night": [100.0, 200.0]}
    )
    daily = daily_occupancy(bookings, total_rooms=2)
    monthly = monthly_kpis(daily, total_rooms=2)
    row = monthly.iloc[0]
    assert row["rooms_sold"] == 3               # 2 nights + 1 night
    assert row["revenue"] == 400                # 2*100 + 1*200
    assert row["ADR"] == round(400 / 3, 2)
    assert row["occupancy_pct"] == 75.0         # 3 sold / (2 days * 2 rooms)


def test_all_queries_are_loaded():
    queries = load_queries()
    for name in ["total_rooms", "revenue_by_channel", "cancellation_rate_by_channel",
                 "guests_by_country", "room_type_performance", "active_bookings"]:
        assert name in queries and queries[name].upper().startswith("SELECT")
