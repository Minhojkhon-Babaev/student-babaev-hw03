"""Загрузка CSV среза в schema raw. Полная перезапись: срез маленький и задаётся явно."""

import csv
import os
import pathlib
import sys

import psycopg2
from psycopg2 import sql

WEATHER_DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.weather_hourly (
    city_id                   text,
    observed_at               timestamp,
    observed_date             date,
    temperature_2m_c          double precision,
    precipitation_mm          double precision,
    relative_humidity_2m_pct  double precision,
    wind_speed_10m_kmh        double precision,
    is_synthetic              boolean
);
CREATE TABLE IF NOT EXISTS raw.city_reference (
    city_id            text,
    city_name          text,
    country_code       text,
    federal_district   text,
    utc_offset_hours   integer,
    valid_from         date,
    valid_to           date,
    is_synthetic       boolean
);
TRUNCATE raw.weather_hourly;
TRUNCATE raw.city_reference;
"""


def connect():
    return psycopg2.connect(
        host=os.environ.get("WAREHOUSE_HOST", "localhost"),
        port=os.environ.get("WAREHOUSE_PORT", "5433"),
        dbname=os.environ.get("WAREHOUSE_DB", "warehouse"),
        user=os.environ.get("WAREHOUSE_USER", "warehouse"),
        password=os.environ.get("WAREHOUSE_PASSWORD", "warehouse"),
    )


def copy_csv(cursor, table, path):
    with path.open("r", encoding="utf-8") as handle:
        cursor.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH CSV HEADER").format(sql.Identifier(*table.split("."))),
            handle,
        )


def copy_csv_qualified(cursor, schema, table, path):
    with path.open("r", encoding="utf-8") as handle:
        cursor.copy_expert(
            f"COPY {schema}.{table} FROM STDIN WITH CSV HEADER",
            handle,
        )


def load_slice(slice_dir: pathlib.Path):
    weather = slice_dir / "weather.csv"
    city = slice_dir / "city.csv"
    if not weather.exists() or not city.exists():
        sys.exit(f"В {slice_dir} нет weather.csv или city.csv")

    conn = connect()
    try:
        with conn, conn.cursor() as cursor:
            cursor.execute(WEATHER_DDL)
            copy_csv_qualified(cursor, "raw", "weather_hourly", weather)
            copy_csv_qualified(cursor, "raw", "city_reference", city)
            cursor.execute("SELECT count(*) FROM raw.weather_hourly")
            weather_n = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM raw.city_reference")
            city_n = cursor.fetchone()[0]
        print(f"raw.weather_hourly = {weather_n}; raw.city_reference = {city_n}; slice = {slice_dir}")
    finally:
        conn.close()


def main():
    project = pathlib.Path(os.environ.get("PROJECT_DIR", pathlib.Path(__file__).resolve().parents[1]))
    slice_name = sys.argv[1] if len(sys.argv) > 1 else "control"
    slice_dir = project / "data" / slice_name if slice_name == "control" else project / "data" / slice_name
    if slice_name == "control":
        slice_dir = project / "data" / "control"
    elif not slice_name.startswith("data/"):
        # cases/case2_new_day
        slice_dir = project / "data" / slice_name
    load_slice(slice_dir)


if __name__ == "__main__":
    main()
