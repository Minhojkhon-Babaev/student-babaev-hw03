CREATE TABLE published.weather_daily_part (
    LIKE published.weather_daily INCLUDING CONSTRAINTS INCLUDING COMMENTS,
    PRIMARY KEY (city_id, observed_date)
) PARTITION BY RANGE (observed_date);

-- Десять годовых секций: начало включено, конец исключён [from, to).
DO $$
DECLARE
    y integer;
BEGIN
    FOR y IN 2015..2024 LOOP
        EXECUTE format(
            'CREATE TABLE published.weather_daily_p%s PARTITION OF published.weather_daily_part
             FOR VALUES FROM (%L) TO (%L)',
            y, make_date(y, 1, 1), make_date(y + 1, 1, 1)
        );
    END LOOP;
END $$;

-- Те же ключи и INCLUDE, что в индексированном варианте, без смешения эффектов.
CREATE INDEX weather_daily_part_date_city_cover_idx
    ON published.weather_daily_part (observed_date, city_id)
    INCLUDE (amplitude_c, min_temp_c, max_temp_c, avg_temp_c);

INSERT INTO published.weather_daily_part
SELECT * FROM published.weather_daily;

VACUUM (ANALYZE) published.weather_daily_part;
