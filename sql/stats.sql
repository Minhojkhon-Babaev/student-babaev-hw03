SELECT count(*) AS n_rows,
       count(*) FILTER (WHERE NOT is_synthetic) AS real_rows,
       count(*) FILTER (WHERE is_synthetic) AS synth_rows,
       min(observed_date) AS dmin,
       max(observed_date) AS dmax
FROM published.weather_daily;

SELECT
    count(*) FILTER (
        WHERE city_id IN ('moscow', 'sochi', 'yakutsk')
          AND observed_date >= DATE '2024-06-01'
          AND observed_date <  DATE '2024-06-04'
    ) AS narrow_rows,
    count(*) FILTER (
        WHERE observed_date >= DATE '2020-01-01'
          AND observed_date <  DATE '2025-01-01'
    ) AS wide_rows,
    round(100.0 * count(*) FILTER (
        WHERE city_id IN ('moscow', 'sochi', 'yakutsk')
          AND observed_date >= DATE '2024-06-01'
          AND observed_date <  DATE '2024-06-04'
    ) / count(*), 6) AS narrow_pct,
    round(100.0 * count(*) FILTER (
        WHERE observed_date >= DATE '2020-01-01'
          AND observed_date <  DATE '2025-01-01'
    ) / count(*), 6) AS wide_pct
FROM published.weather_daily;
