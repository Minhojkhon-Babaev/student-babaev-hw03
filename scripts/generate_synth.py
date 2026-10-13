#!/usr/bin/env python3
"""Синтетическая витрина того же домена. Не выдаёт себя за Open-Meteo.

Контрольные 9 строк (Москва/Сочи/Якутск, 1–3 июня 2024) не генерируются:
их кладёт load_mart.py из data/control/weather_daily.csv.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synth" / "weather_daily.csv"

REAL_CITIES = [
    ("moscow", "Москва", "Центральный"),
    ("sochi", "Сочи", "Южный"),
    ("yakutsk", "Якутск", "Дальневосточный"),
]
SYN_CITIES = [
    (f"syn_{i:02d}", f"SYN-город-{i:02d}", "ТЕСТОВЫЙ_ОКРУГ")
    for i in range(1, 28)
]
CITIES = REAL_CITIES + SYN_CITIES

START = dt.date(2015, 1, 1)
END = dt.date(2024, 12, 31)  # inclusive
CONTROL_KEYS = {
    ("moscow", dt.date(2024, 6, 1)),
    ("moscow", dt.date(2024, 6, 2)),
    ("moscow", dt.date(2024, 6, 3)),
    ("sochi", dt.date(2024, 6, 1)),
    ("sochi", dt.date(2024, 6, 2)),
    ("sochi", dt.date(2024, 6, 3)),
    ("yakutsk", dt.date(2024, 6, 1)),
    ("yakutsk", dt.date(2024, 6, 2)),
    ("yakutsk", dt.date(2024, 6, 3)),
}

# Климат: Сочи ровный, Якутск большая амплитуда. Остальное — детерминированный хэш.
BASE = {
    "moscow": (10.0, 12.0),
    "sochi": (16.0, 6.0),
    "yakutsk": (-5.0, 18.0),
}


def u01(city: str, day: dt.date, salt: str) -> float:
    digest = hashlib.md5(f"{city}|{day.isoformat()}|{salt}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2**32


def climate(city: str) -> tuple[float, float]:
    if city in BASE:
        return BASE[city]
    idx = int(city.split("_")[1])
    return (-8.0 + idx, 8.0 + (idx % 7))


def row(city_id: str, city_name: str, district: str, day: dt.date) -> dict:
    mean0, amp0 = climate(city_id)
    doy = day.timetuple().tm_yday
    seasonal = 12.0 * (1 if city_id != "yakutsk" else 1.6) * math.sin(
        2 * 3.14159265 * (doy - 80) / 365
    )
    mean = mean0 + seasonal + (u01(city_id, day, "mean") - 0.5) * 4
    amp = max(1.5, amp0 + (u01(city_id, day, "amp") - 0.5) * 6)
    min_t = round(mean - amp / 2, 1)
    max_t = round(mean + amp / 2, 1)
    avg = round((min_t + max_t) / 2 + (u01(city_id, day, "avg") - 0.5) * 0.8, 3)
    precip = round(u01(city_id, day, "pr") * 8, 2)
    return {
        "city_id": city_id,
        "city_name": city_name,
        "federal_district": district,
        "observed_date": day.isoformat(),
        "n_hours": 24,
        "avg_temp_c": f"{avg:.3f}",
        "min_temp_c": f"{min_t:.1f}",
        "max_temp_c": f"{max_t:.1f}",
        "amplitude_c": f"{round(max_t - min_t, 1):.1f}",
        "precip_sum_mm": f"{precip:.2f}",
        "is_synthetic": "true",
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "city_id",
                "city_name",
                "federal_district",
                "observed_date",
                "n_hours",
                "avg_temp_c",
                "min_temp_c",
                "max_temp_c",
                "amplitude_c",
                "precip_sum_mm",
                "is_synthetic",
            ],
        )
        writer.writeheader()
        day = START
        while day <= END:
            for city_id, city_name, district in CITIES:
                if (city_id, day) in CONTROL_KEYS:
                    continue
                writer.writerow(row(city_id, city_name, district, day))
                n += 1
            day += dt.timedelta(days=1)
    print(f"wrote {n} synthetic rows to {OUT}")


if __name__ == "__main__":
    main()
