select city_id, observed_at, count(*) as n
from {{ ref('fact_weather_hourly') }}
group by city_id, observed_at
having count(*) > 1
