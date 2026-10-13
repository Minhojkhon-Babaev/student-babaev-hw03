#!/usr/bin/env python3
"""Независимый расчёт всех мер контрольного среза из hourly CSV."""

from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from db import ROOT, rows, save


def expected_control() -> list[dict]:
    buckets = defaultdict(list)
    with (ROOT / "data/control/weather.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["is_synthetic"] != "false":
                raise AssertionError("Контрольный hourly CSV должен быть реальным срезом ДЗ 2")
            buckets[(row["city_id"], row["observed_date"])].append(row)
    with (ROOT / "data/control/city.csv").open(encoding="utf-8", newline="") as source:
        cities = {row["city_id"]: row for row in csv.DictReader(source)}
    result = []
    for (city, day), hours in sorted(buckets.items()):
        assert len(hours) == len({h["observed_at"] for h in hours}) == 24
        temps = [Decimal(h["temperature_2m_c"]) for h in hours]
        result.append({
            "city_id": city, "city_name": cities[city]["city_name"],
            "federal_district": cities[city]["federal_district"], "observed_date": day,
            "n_hours": 24,
            "avg_temp_c": float((sum(temps) / 24).quantize(Decimal(".001"), rounding=ROUND_HALF_UP)),
            "min_temp_c": float(min(temps)), "max_temp_c": float(max(temps)),
            "amplitude_c": float(max(temps) - min(temps)),
            "precip_sum_mm": float(sum(Decimal(h["precipitation_mm"]) for h in hours)),
            "is_synthetic": False,
        })
    assert len(result) == 9
    return result


def check_database(database: str = "warehouse") -> str:
    expected = expected_control()
    actual = rows(
        "SELECT * FROM published.weather_daily WHERE NOT is_synthetic ORDER BY city_id, observed_date",
        database,
    )
    assert actual == expected, (database, actual, expected)
    amplitudes = defaultdict(list)
    for row in expected:
        amplitudes[row["city_id"]].append(Decimal(str(row["amplitude_c"])))
    lines = [f"PASS {database}: 216 hourly rows -> 9 city-days; all columns equal"]
    for row in expected:
        lines.append(str(row))
    for city, values in sorted(amplitudes.items()):
        lines.append(f"{city}: mean amplitude = {sum(values) / len(values):.3f} C")
    top = max(expected, key=lambda row: row["amplitude_c"])
    lines.append(f"Independent maximum: {top['city_id']} {top['observed_date']} {top['amplitude_c']} C")
    return "\n".join(lines) + "\n"


def main() -> None:
    text = check_database()
    save("independent_control.txt", text)
    print(text)


if __name__ == "__main__":
    main()
