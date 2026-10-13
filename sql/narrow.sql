-- Узкий отчёт: тот же бизнес-вопрос ДЗ 2.
-- Москва, Сочи, Якутск; 2024-06-01 .. 2024-06-03 UTC; мера amplitude_c = max-min °C.
SELECT city_id, observed_date, amplitude_c, min_temp_c, max_temp_c, avg_temp_c
FROM published.weather_daily
WHERE city_id IN ('moscow', 'sochi', 'yakutsk')
  AND observed_date >= DATE '2024-06-01'
  AND observed_date <  DATE '2024-06-04'
ORDER BY amplitude_c DESC, city_id, observed_date;
