"""Независимый контроль витрины: те же агрегаты считаются по CSV, без dbt."""

import csv
import pathlib
import sys
from collections import defaultdict


def from_csv(path):
    buckets = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["city_id"], row["observed_date"])
            buckets[key].append(float(row["temperature_2m_c"]))
    result = {}
    for key, values in buckets.items():
        result[key] = {
            "n_hours": len(values),
            "avg_temp_c": round(sum(values) / len(values), 3),
            "min_temp_c": round(min(values), 1),
            "max_temp_c": round(max(values), 1),
            "amplitude_c": round(max(values) - min(values), 1),
        }
    return result


def main():
    weather = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/control/weather.csv")
    out = from_csv(weather)
    for (city, day), metrics in sorted(out.items()):
        print(f"{city}\t{day}\t{metrics}")
    print(f"city_days={len(out)}")


if __name__ == "__main__":
    main()
