-- На одну календарную дату у города не больше одной версии измерения.
select
    city_id,
    valid_from,
    count(*) as versions
from {{ ref('dim_city') }}
group by city_id, valid_from
having count(*) > 1
