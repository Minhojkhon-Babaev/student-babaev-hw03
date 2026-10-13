-- Широкий отчёт: все 30 городов за пять лет, включая явно синтетические.
-- Сравнение средней суточной амплитуды; синтетика не климатическое наблюдение.
SELECT city_id,
       round(avg(amplitude_c), 2) AS mean_amplitude_c,
       count(*) AS city_days
FROM published.weather_daily
WHERE observed_date >= DATE '2020-01-01'
  AND observed_date <  DATE '2025-01-01'
GROUP BY city_id
ORDER BY city_id;
