"""
Generates a synthetic bookings dataset for a 60-room seasonal hotel
and stores it in a SQLite database (data/hotel.db).

The data is fake but realistic: the season runs from April to October,
demand peaks in July-August, and bookings come from the channels a
Greek resort hotel typically uses (Booking.com, Expedia, direct website).
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "hotel.db"

SEASON_START = date(2024, 4, 15)
SEASON_END = date(2024, 10, 31)

# Room types: (name, number of rooms, base price per night in EUR)
ROOM_TYPES = [
    ("Standard Double", 30, 85),
    ("Superior Sea View", 20, 120),
    ("Family Suite", 10, 170),
]

# Booking channels and how often each one is used
CHANNELS = {"Booking.com": 0.50, "Expedia": 0.20, "Direct (website)": 0.20, "Travel Agent": 0.10}

COUNTRIES = {"United Kingdom": 0.30, "Germany": 0.20, "Greece": 0.15, "Italy": 0.10,
             "France": 0.08, "Netherlands": 0.07, "Poland": 0.05, "USA": 0.05}

# Chance (0-1) that a free room gets a new booking on a given day of each month.
# Higher in July-August, lower at the start and end of the season.
MONTH_DEMAND = {4: 0.06, 5: 0.12, 6: 0.25, 7: 0.55, 8: 0.60, 9: 0.22, 10: 0.07}

# Prices go up in high season
MONTH_PRICE_FACTOR = {4: 0.8, 5: 0.9, 6: 1.1, 7: 1.35, 8: 1.4, 9: 1.05, 10: 0.85}


def weighted_choice(options: dict) -> str:
    return random.choices(list(options), weights=list(options.values()))[0]


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS bookings;
        DROP TABLE IF EXISTS rooms;

        CREATE TABLE rooms (
            room_type   TEXT PRIMARY KEY,
            room_count  INTEGER NOT NULL,
            base_price  REAL NOT NULL
        );

        CREATE TABLE bookings (
            booking_id     INTEGER PRIMARY KEY,
            room_type      TEXT NOT NULL REFERENCES rooms(room_type),
            channel        TEXT NOT NULL,
            guest_country  TEXT NOT NULL,
            check_in       DATE NOT NULL,
            check_out      DATE NOT NULL,
            nights         INTEGER NOT NULL,
            price_per_night REAL NOT NULL,
            is_cancelled   INTEGER NOT NULL DEFAULT 0
        );
        """
    )


def generate_bookings(seed: int = 42) -> list[tuple]:
    """Fill each room night by night, so a room is never double-booked."""
    random.seed(seed)
    bookings = []

    for room_type, room_count, base_price in ROOM_TYPES:
        for _room in range(room_count):
            day = SEASON_START
            while day < SEASON_END:
                # Decide if this room gets a booking starting today
                if random.random() > MONTH_DEMAND[day.month]:
                    day += timedelta(days=1)
                    continue

                nights = random.choice([2, 3, 4, 5, 7, 7, 10, 14])
                check_out = min(day + timedelta(days=nights), SEASON_END)
                nights = (check_out - day).days

                channel = weighted_choice(CHANNELS)
                price = base_price * MONTH_PRICE_FACTOR[day.month] * random.uniform(0.9, 1.1)
                if channel == "Direct (website)":
                    price *= 0.95  # small discount for booking direct

                # Online travel agencies have more cancellations
                cancel_rate = 0.18 if channel in ("Booking.com", "Expedia") else 0.08
                is_cancelled = int(random.random() < cancel_rate)

                bookings.append((room_type, channel, weighted_choice(COUNTRIES),
                                 day.isoformat(), check_out.isoformat(), nights,
                                 round(price, 2), is_cancelled))

                # A cancelled booking leaves the room free again
                day = day + timedelta(days=1) if is_cancelled else check_out
    return bookings


def main() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)
        conn.executemany("INSERT INTO rooms VALUES (?, ?, ?)", ROOM_TYPES)
        rows = generate_bookings()
        conn.executemany(
            """INSERT INTO bookings (room_type, channel, guest_country, check_in,
               check_out, nights, price_per_night, is_cancelled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    print(f"Created {len(rows)} bookings in {DB_PATH}")


if __name__ == "__main__":
    main()
