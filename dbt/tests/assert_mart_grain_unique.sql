select city_id, observed_date, count(*) as n
from {{ ref('weather_daily_candidate') }}
group by city_id, observed_date
having count(*) > 1
