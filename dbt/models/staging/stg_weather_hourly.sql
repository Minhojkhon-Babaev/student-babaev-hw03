{{
  config(alias="stg_weather_hourly")
}}

-- ODS: типы, дедуп по ключу наблюдения. При повторе строки оставляем последнюю в файле.
with src as (
    select
        city_id,
        observed_at::timestamp as observed_at,
        observed_date::date as observed_date,
        temperature_2m_c::double precision as temperature_2m_c,
        precipitation_mm::double precision as precipitation_mm,
        relative_humidity_2m_pct::double precision as relative_humidity_2m_pct,
        wind_speed_10m_kmh::double precision as wind_speed_10m_kmh,
        coalesce(is_synthetic, false) as is_synthetic,
        row_number() over (
            partition by city_id, observed_at
            order by observed_at
        ) as rn
    from {{ source('raw', 'weather_hourly') }}
)

select
    city_id,
    observed_at,
    observed_date,
    temperature_2m_c,
    precipitation_mm,
    relative_humidity_2m_pct,
    wind_speed_10m_kmh,
    is_synthetic
from src
where rn = 1
