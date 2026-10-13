CREATE SCHEMA IF NOT EXISTS published;

-- Только создание в новой учебной базе; существующие данные не удаляются.
CREATE TABLE published.weather_daily (
    city_id            text          NOT NULL,
    city_name          text          NOT NULL,
    federal_district   text          NOT NULL,
    observed_date      date          NOT NULL,
    n_hours            integer       NOT NULL CHECK (n_hours = 24),
    avg_temp_c         numeric(8,3)  NOT NULL,
    min_temp_c         numeric(8,1)  NOT NULL,
    max_temp_c         numeric(8,1)  NOT NULL,
    amplitude_c        numeric(8,1)  NOT NULL,
    precip_sum_mm      numeric(10,2) NOT NULL CHECK (precip_sum_mm >= 0),
    is_synthetic       boolean       NOT NULL,
    PRIMARY KEY (city_id, observed_date),
    CHECK (min_temp_c <= avg_temp_c AND avg_temp_c <= max_temp_c),
    CHECK (amplitude_c = max_temp_c - min_temp_c)
);

COMMENT ON TABLE published.weather_daily IS
    'Витрина город×день UTC. Контрольные 9 строк из ДЗ 2 — Open-Meteo; остальное явно синтетика.';
