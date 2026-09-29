{{ config(alias="dim_date") }}

-- Календарь из фактических дат среза. Отдельный генератор дат не нужен: потребитель смотрит только дни с наблюдениями.
select
    observed_date as date_key,
    observed_date,
    extract(year from observed_date)::int as year,
    extract(month from observed_date)::int as month,
    extract(day from observed_date)::int as day,
    extract(isodow from observed_date)::int as iso_dow,
    (extract(isodow from observed_date) in (6, 7)) as is_weekend
from (
    select distinct observed_date
    from {{ ref('stg_weather_hourly') }}
) d
