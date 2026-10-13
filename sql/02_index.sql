-- PK уже даёт B-tree (city_id, observed_date).
-- Проверяем дополнительный покрывающий индекс: дата ограничивает интервал,
-- city_id уточняет город, INCLUDE содержит все меры обоих отчётов.
CREATE INDEX weather_daily_date_city_cover_idx
    ON published.weather_daily (observed_date, city_id)
    INCLUDE (amplitude_c, min_temp_c, max_temp_c, avg_temp_c);
VACUUM (ANALYZE) published.weather_daily;
