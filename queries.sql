-- Запросы к опубликованной витрине. Потребитель — аналитик климата.
-- Срез: Москва, Сочи, Якутск, 2024-06-01..2024-06-03 UTC.

-- 1. В каком городе в какой день суточная амплитуда температуры наибольшая?
select city_id, observed_date, amplitude_c, min_temp_c, max_temp_c
from published.weather_daily
order by amplitude_c desc, city_id, observed_date
limit 5;

-- 2. Средняя температура по городам за срез.
select city_id, round(avg(avg_temp_c), 3) as mean_of_daily_avg_c, count(*) as days
from published.weather_daily
group by city_id
order by city_id;

-- 3. Сравнение округов: средняя амплитуда.
select federal_district, round(avg(amplitude_c), 2) as mean_amplitude_c, count(*) as city_days
from published.weather_daily
group by federal_district
order by mean_amplitude_c desc;
