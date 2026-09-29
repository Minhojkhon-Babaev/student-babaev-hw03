{{
  config(alias="stg_city")
}}

select
    city_id,
    city_name,
    country_code,
    federal_district,
    utc_offset_hours::integer as utc_offset_hours,
    valid_from::date as valid_from,
    valid_to::date as valid_to,
    coalesce(is_synthetic, false) as is_synthetic
from {{ source('raw', 'city_reference') }}
