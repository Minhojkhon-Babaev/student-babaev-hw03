-- Учебные базы: склад данных и метаданные Airflow.
CREATE DATABASE airflow;

\connect warehouse

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS ods;
CREATE SCHEMA IF NOT EXISTS dds;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS published;

-- Потребитель читает только эту таблицу. Кандидат dbt сюда не пишет.
CREATE TABLE published.weather_daily (
    city_id            text        NOT NULL,
    city_name          text        NOT NULL,
    federal_district   text        NOT NULL,
    observed_date      date        NOT NULL,
    n_hours            integer     NOT NULL,
    avg_temp_c         numeric(8,3) NOT NULL,
    min_temp_c         numeric(8,1) NOT NULL,
    max_temp_c         numeric(8,1) NOT NULL,
    amplitude_c        numeric(8,1) NOT NULL,
    precip_sum_mm      numeric(10,2) NOT NULL,
    published_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (city_id, observed_date)
);

COMMENT ON TABLE published.weather_daily IS
    'Опубликованная витрина. Обновляется только после успешных тестов dbt.';
