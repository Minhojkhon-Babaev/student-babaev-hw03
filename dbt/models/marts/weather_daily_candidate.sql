{{ config(alias="weather_daily_candidate") }}

-- Кандидат витрины. Потребитель его не читает: публикация копирует снимок в published.weather_daily.
select
    f.city_id,
    max(c.city_name) as city_name,
    max(c.federal_district) as federal_district,
    f.observed_date,
    count(*) as n_hours,
    round(avg(f.temperature_2m_c)::numeric, 3) as avg_temp_c,
    round(min(f.temperature_2m_c)::numeric, 1) as min_temp_c,
    round(max(f.temperature_2m_c)::numeric, 1) as max_temp_c,
    round((max(f.temperature_2m_c) - min(f.temperature_2m_c))::numeric, 1) as amplitude_c,
    round(sum(f.precipitation_mm)::numeric, 2) as precip_sum_mm
from {{ ref('fact_weather_hourly') }} f
inner join {{ ref('dim_city') }} c
    on f.city_sk = c.city_sk
group by f.city_id, f.observed_date
