{{ config(alias="dim_city") }}

-- SCD2: одна версия атрибутов на интервал [valid_from, valid_to).
-- На контрольном срезе у каждого города одна вечная версия.
select
    md5(city_id || '|' || valid_from::text) as city_sk,
    city_id,
    city_name,
    country_code,
    federal_district,
    utc_offset_hours,
    valid_from,
    valid_to,
    (valid_to = date '9999-12-31') as is_current,
    is_synthetic
from {{ ref('stg_city') }}
