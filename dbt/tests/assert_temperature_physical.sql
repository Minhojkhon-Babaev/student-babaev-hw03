-- Бизнес-правило: температура должна быть физически возможной.
-- Тест возвращает нарушившие строки — так dbt показывает конкретный брак.
select
    city_id,
    observed_at,
    temperature_2m_c
from {{ ref('fact_weather_hourly') }}
where temperature_2m_c < -90
   or temperature_2m_c > 60
