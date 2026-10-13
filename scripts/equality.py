#!/usr/bin/env python3
"""Два запроса и полные таблицы: точное равенство после каждого изменения."""

from __future__ import annotations

import argparse
import json

from db import ROOT, psql, rows, save
from independent_check import check_database


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["index", "partition", "final"], required=True)
    args = parser.parse_args()
    lines = []
    for name in ["narrow", "wide"]:
        baseline = json.loads((ROOT / f"evidence/bench/heap_{name}.json").read_text())["result"]
        actual = rows((ROOT / f"sql/{name}.sql").read_text())
        assert actual == baseline, f"{args.stage}: heap {name} differs"
        lines.append(f"PASS {args.stage}: {name} heap result equals baseline ({len(actual)} rows)")
        if args.stage in ["partition", "final"]:
            part = rows((ROOT / f"sql/{name}_part.sql").read_text())
            assert part == baseline, f"{args.stage}: partition {name} differs"
            query = (ROOT / f"sql/{name}.sql").read_text().strip().rstrip(";")
            part_query = (ROOT / f"sql/{name}_part.sql").read_text().strip().rstrip(";")
            for left, right, direction in [
                (query, part_query, "heap_minus_part"),
                (part_query, query, "part_minus_heap"),
            ]:
                count = psql(f"SELECT count(*) FROM (({left}) EXCEPT ALL ({right})) q;").strip()
                assert count == "0", (name, direction, count)
                lines.append(f"PASS {name} {direction}: EXCEPT ALL = 0")
    if args.stage in ["partition", "final"]:
        for left, right in [
            ("weather_daily", "weather_daily_part"),
            ("weather_daily_part", "weather_daily"),
        ]:
            count = psql(
                f"SELECT count(*) FROM (SELECT * FROM published.{left} "
                f"EXCEPT ALL SELECT * FROM published.{right}) q;"
            ).strip()
            assert count == "0", (left, right, count)
            lines.append(f"PASS full table {left} minus {right}: EXCEPT ALL = 0")
    lines.append(check_database().strip())
    text = "\n".join(lines) + "\n"
    save(f"equality_{args.stage}.txt", text)
    print(text)


if __name__ == "__main__":
    main()
