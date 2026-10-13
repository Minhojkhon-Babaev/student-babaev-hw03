#!/usr/bin/env python3
"""Один прогрев + пять измерений серверного Execution Time в одинаковых условиях."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess

from db import ROOT, SETTINGS, command, psql, rows, save


def explain(query: str, format_name: str = "JSON") -> str:
    return psql(SETTINGS + f"EXPLAIN (ANALYZE, BUFFERS, FORMAT {format_name})\n" + query)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    query = (ROOT / args.sql).read_text(encoding="utf-8")
    warmup = json.loads(explain(query))[0]
    plans = [json.loads(explain(query))[0] for _ in range(5)]
    times = [plan["Execution Time"] for plan in plans]
    result = rows(query)
    payload = {
        "label": args.label, "sql": query, "settings": SETTINGS,
        "warmup_ms_discarded": warmup["Execution Time"],
        "repeats_ms": times, "median_ms": statistics.median(times),
        "rows_returned": len(result), "result": result, "plans": plans,
    }
    save(f"bench/{args.label}.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    table = subprocess.run(
        command(), cwd=ROOT, input=SETTINGS + query,
        text=True, check=True, capture_output=True,
    ).stdout
    text = (
        f"{args.label}\nmetric: server Execution Time, ms; warmup discarded\n"
        f"repeats_ms: {times}\nmedian_ms: {payload['median_ms']:.3f}\n"
        f"rows_returned: {len(result)}\n\n{table}\n"
        + explain(query, "TEXT")
    )
    save(f"bench/{args.label}.txt", text)
    print(f"{args.label}: median={payload['median_ms']:.3f} ms, repeats={times}, rows={len(result)}")


if __name__ == "__main__":
    main()
