"""Скачать контрольный срез Open-Meteo и собрать CSV.

Контрольный срез: Москва, Сочи, Якутск; часы UTC 2024-06-01 .. 2024-06-03.
Для случая 2 дополнительно качается 2024-06-04 только по Москве.

Запуск из корня сдачи:
    python3 scripts/fetch_source.py
"""

import csv
import json
import pathlib
import sys
import urllib.parse
import urllib.request
from datetime import datetime

API_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "relative_humidity_2m",
    "wind_speed_10m",
]

CITIES = [
    {
        "city_id": "moscow",
        "city_name": "Москва",
        "country_code": "RU",
        "federal_district": "Центральный",
        "utc_offset_hours": 3,
        "latitude": 55.7558,
        "longitude": 37.6173,
    },
    {
        "city_id": "sochi",
        "city_name": "Сочи",
        "country_code": "RU",
        "federal_district": "Южный",
        "utc_offset_hours": 3,
        "latitude": 43.5855,
        "longitude": 39.7231,
    },
    {
        "city_id": "yakutsk",
        "city_name": "Якутск",
        "country_code": "RU",
        "federal_district": "Дальневосточный",
        "utc_offset_hours": 9,
        "latitude": 62.0355,
        "longitude": 129.6755,
    },
]

WEATHER_COLUMNS = [
    "city_id",
    "observed_at",
    "observed_date",
    "temperature_2m_c",
    "precipitation_mm",
    "relative_humidity_2m_pct",
    "wind_speed_10m_kmh",
    "is_synthetic",
]

CITY_COLUMNS = [
    "city_id",
    "city_name",
    "country_code",
    "federal_district",
    "utc_offset_hours",
    "valid_from",
    "valid_to",
    "is_synthetic",
]


def download(lat, lon, start, end):
    query = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
    })
    url = f"{API_URL}?{query}"
    print(f"GET {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def hourly_rows(city, payload, start, end):
    hourly = payload["hourly"]
    rows = []
    for i, moment in enumerate(hourly["time"]):
        observed_at = datetime.strptime(moment, "%Y-%m-%dT%H:%M")
        observed_date = observed_at.strftime("%Y-%m-%d")
        if observed_date < start or observed_date > end:
            continue
        rows.append({
            "city_id": city["city_id"],
            "observed_at": observed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "observed_date": observed_date,
            "temperature_2m_c": hourly["temperature_2m"][i],
            "precipitation_mm": hourly["precipitation"][i],
            "relative_humidity_2m_pct": hourly["relative_humidity_2m"][i],
            "wind_speed_10m_kmh": hourly["wind_speed_10m"][i],
            "is_synthetic": "false",
        })
    return rows


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"{path}: {len(rows)} строк")


def city_versions():
    rows = []
    for city in CITIES:
        rows.append({
            "city_id": city["city_id"],
            "city_name": city["city_name"],
            "country_code": city["country_code"],
            "federal_district": city["federal_district"],
            "utc_offset_hours": city["utc_offset_hours"],
            "valid_from": "2024-01-01",
            "valid_to": "9999-12-31",
            "is_synthetic": "false",
        })
    return rows


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    data = root / "data"
    if not pathlib.Path("docker-compose.yml").exists() and not (root / "docker-compose.yml").exists():
        # allow running from anywhere as long as we write next to this repo
        pass

    control_weather = []
    moscow_extra = []
    for city in CITIES:
        payload = download(city["latitude"], city["longitude"], "2024-06-01", "2024-06-04")
        control_weather.extend(hourly_rows(city, payload, "2024-06-01", "2024-06-03"))
        if city["city_id"] == "moscow":
            moscow_extra = hourly_rows(city, payload, "2024-06-04", "2024-06-04")

    write_csv(data / "control" / "weather.csv", WEATHER_COLUMNS, control_weather)
    write_csv(data / "control" / "city.csv", CITY_COLUMNS, city_versions())

    # Случай 2: те же факты + реальный следующий день Москвы из того же API.
    write_csv(
        data / "cases" / "case2_new_day" / "weather.csv",
        WEATHER_COLUMNS,
        control_weather + moscow_extra,
    )
    write_csv(data / "cases" / "case2_new_day" / "city.csv", CITY_COLUMNS, city_versions())

    # Случай 3: синтетическая смена округа Москвы со 2 июня. Не данные Open-Meteo.
    history = []
    for row in city_versions():
        if row["city_id"] != "moscow":
            history.append(row)
            continue
        old = dict(row)
        old["valid_to"] = "2024-06-02"
        history.append(old)
        new = dict(row)
        new["federal_district"] = "ТЕСТОВЫЙ_ОКРУГ"
        new["valid_from"] = "2024-06-02"
        new["is_synthetic"] = "true"
        history.append(new)
    write_csv(data / "cases" / "case3_city_history" / "weather.csv", WEATHER_COLUMNS, control_weather)
    write_csv(data / "cases" / "case3_city_history" / "city.csv", CITY_COLUMNS, history)

    # Случай 4: невозможная температура у Якутска.
    bad = [dict(row) for row in control_weather]
    for row in bad:
        if row["city_id"] == "yakutsk" and row["observed_at"] == "2024-06-02 12:00:00":
            row["temperature_2m_c"] = 999
            row["is_synthetic"] = "true"
            break
    write_csv(data / "cases" / "case4_bad_temperature" / "weather.csv", WEATHER_COLUMNS, bad)
    write_csv(data / "cases" / "case4_bad_temperature" / "city.csv", CITY_COLUMNS, city_versions())

    print("Контрольный срез и входы четырёх случаев готовы.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
