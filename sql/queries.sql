-- Each query starts with a "-- name: <query_name>" line so that
-- analyze.py can load them one by one.

-- name: total_rooms
SELECT SUM(room_count) AS total_rooms FROM rooms;

-- name: revenue_by_channel
-- Revenue and number of stays per booking channel (cancelled bookings excluded)
SELECT channel,
       COUNT(*)                                   AS bookings,
       SUM(nights)                                AS room_nights,
       ROUND(SUM(nights * price_per_night), 0)    AS revenue,
       ROUND(AVG(price_per_night), 2)             AS avg_daily_rate
FROM bookings
WHERE is_cancelled = 0
GROUP BY channel
ORDER BY revenue DESC;

-- name: cancellation_rate_by_channel
SELECT channel,
       COUNT(*)                                   AS total_bookings,
       SUM(is_cancelled)                          AS cancelled,
       ROUND(100.0 * SUM(is_cancelled) / COUNT(*), 1) AS cancellation_rate_pct
FROM bookings
GROUP BY channel
ORDER BY cancellation_rate_pct DESC;

-- name: guests_by_country
SELECT guest_country,
       COUNT(*)                                   AS bookings,
       ROUND(AVG(nights), 1)                      AS avg_length_of_stay
FROM bookings
WHERE is_cancelled = 0
GROUP BY guest_country
ORDER BY bookings DESC;

-- name: room_type_performance
SELECT b.room_type,
       r.room_count,
       SUM(b.nights)                              AS room_nights_sold,
       ROUND(SUM(b.nights * b.price_per_night), 0) AS revenue,
       ROUND(AVG(b.price_per_night), 2)           AS avg_daily_rate
FROM bookings b
JOIN rooms r ON r.room_type = b.room_type
WHERE b.is_cancelled = 0
GROUP BY b.room_type, r.room_count
ORDER BY revenue DESC;

-- name: active_bookings
-- Used by analyze.py to calculate occupancy day by day
SELECT check_in, check_out, price_per_night
FROM bookings
WHERE is_cancelled = 0;
