"""
Analyses the hotel bookings database and produces:
  - output/report.md        a short report with the key numbers
  - output/*.png            charts for occupancy and revenue

Key hotel metrics used:
  Occupancy = rooms sold / rooms available
  ADR       = Average Daily Rate = room revenue / rooms sold
  RevPAR    = Revenue Per Available Room = room revenue / rooms available
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw charts to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "hotel.db"
SQL_PATH = ROOT / "sql" / "queries.sql"
OUTPUT = ROOT / "output"


def load_queries(path: Path = SQL_PATH) -> dict[str, str]:
    """Split queries.sql into a {name: sql} dictionary using the '-- name:' markers."""
    queries, name, lines = {}, None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            if name:
                queries[name] = "\n".join(lines).strip()
            name, lines = line.split(":", 1)[1].strip(), []
        elif name and not line.startswith("--"):  # skip comment lines
            lines.append(line)
    if name:
        queries[name] = "\n".join(lines).strip()
    return queries


def daily_occupancy(bookings: pd.DataFrame, total_rooms: int) -> pd.DataFrame:
    """
    Turns bookings into one row per night.
    A guest who checks in on the 1st and out on the 4th occupies the room
    on the nights of the 1st, 2nd and 3rd (the check-out day is not counted).
    """
    nights = []
    for row in bookings.itertuples():
        for night in pd.date_range(row.check_in, row.check_out, inclusive="left"):
            nights.append((night, row.price_per_night))

    per_night = pd.DataFrame(nights, columns=["date", "price"])
    daily = per_night.groupby("date").agg(rooms_sold=("price", "size"), revenue=("price", "sum"))
    daily["occupancy_pct"] = 100 * daily["rooms_sold"] / total_rooms
    return daily


def monthly_kpis(daily: pd.DataFrame, total_rooms: int) -> pd.DataFrame:
    monthly = daily.resample("MS").agg({"rooms_sold": "sum", "revenue": "sum"})
    monthly["revenue"] = monthly["revenue"].round(0)
    monthly["rooms_available"] = daily.resample("MS").size() * total_rooms
    monthly["occupancy_pct"] = (100 * monthly["rooms_sold"] / monthly["rooms_available"]).round(1)
    monthly["ADR"] = (monthly["revenue"] / monthly["rooms_sold"]).round(2)
    monthly["RevPAR"] = (monthly["revenue"] / monthly["rooms_available"]).round(2)
    monthly.index = monthly.index.strftime("%b %Y")
    return monthly


def save_charts(daily: pd.DataFrame, monthly: pd.DataFrame, by_channel: pd.DataFrame) -> None:
    OUTPUT.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(daily.index, daily["occupancy_pct"], linewidth=1)
    ax.plot(daily.index, daily["occupancy_pct"].rolling(7).mean(), linewidth=2, label="7-day average")
    ax.set_title("Daily occupancy (%)")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT / "daily_occupancy.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(monthly.index, monthly["occupancy_pct"])
    ax.set_title("Monthly occupancy (%)")
    ax.set_ylim(0, 100)
    fig.tight_layout()
    fig.savefig(OUTPUT / "monthly_occupancy.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(by_channel["channel"], by_channel["revenue"])
    ax.invert_yaxis()
    ax.set_title("Room revenue by booking channel (EUR)")
    fig.tight_layout()
    fig.savefig(OUTPUT / "revenue_by_channel.png", dpi=120)
    plt.close(fig)


def write_report(monthly, by_channel, cancellations, countries, room_types) -> None:
    season = monthly[["rooms_sold", "revenue", "rooms_available"]].sum()
    lines = [
        "# Season report",
        "",
        f"- Season occupancy: **{100 * season.rooms_sold / season.rooms_available:.1f}%**",
        f"- Room revenue: **EUR {season.revenue:,.0f}**",
        f"- ADR: **EUR {season.revenue / season.rooms_sold:.2f}**",
        f"- RevPAR: **EUR {season.revenue / season.rooms_available:.2f}**",
        "",
        "## Monthly KPIs", monthly.to_markdown(), "",
        "## Revenue by channel", by_channel.to_markdown(index=False), "",
        "## Cancellation rate by channel", cancellations.to_markdown(index=False), "",
        "## Room types", room_types.to_markdown(index=False), "",
        "## Top guest countries", countries.head(5).to_markdown(index=False), "",
    ]
    (OUTPUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run `python src/generate_data.py` first.")

    queries = load_queries()
    with sqlite3.connect(DB_PATH) as conn:
        run = lambda name: pd.read_sql_query(queries[name], conn)
        total_rooms = int(run("total_rooms").iloc[0, 0])
        bookings = run("active_bookings")
        by_channel = run("revenue_by_channel")
        cancellations = run("cancellation_rate_by_channel")
        countries = run("guests_by_country")
        room_types = run("room_type_performance")

    daily = daily_occupancy(bookings, total_rooms)
    monthly = monthly_kpis(daily, total_rooms)

    OUTPUT.mkdir(exist_ok=True)
    save_charts(daily, monthly, by_channel)
    write_report(monthly, by_channel, cancellations, countries, room_types)

    print(monthly.to_string())
    print(f"\nReport and charts saved in {OUTPUT}")


if __name__ == "__main__":
    main()
