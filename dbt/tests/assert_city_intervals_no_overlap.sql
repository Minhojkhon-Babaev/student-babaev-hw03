-- У одной версии города интервалы SCD2 не пересекаются.
select
    a.city_id,
    a.valid_from as a_from,
    a.valid_to as a_to,
    b.valid_from as b_from,
    b.valid_to as b_to
from {{ ref('dim_city') }} a
join {{ ref('dim_city') }} b
  on a.city_id = b.city_id
 and a.city_sk < b.city_sk
where a.valid_from < b.valid_to
  and b.valid_from < a.valid_to
