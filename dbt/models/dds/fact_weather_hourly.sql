{{ config(alias="fact_weather_hourly") }}

-- Одна строка факта — один час UTC в одном городе.
-- Город берём той версией измерения, которая действовала в момент наблюдения.
select
    c.city_sk,
    w.city_id,
    d.date_key,
    w.observed_at,
    w.observed_date,
    extract(hour from w.observed_at)::int as hour_utc,
    w.temperature_2m_c,
    w.precipitation_mm,
    w.relative_humidity_2m_pct,
    w.wind_speed_10m_kmh,
    w.is_synthetic
from {{ ref('stg_weather_hourly') }} w
inner join {{ ref('dim_date') }} d
    on w.observed_date = d.date_key
inner join {{ ref('dim_city') }} c
    on w.city_id = c.city_id
   and w.observed_date >= c.valid_from
   and w.observed_date < c.valid_to
