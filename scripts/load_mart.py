#!/usr/bin/env python3
"""Создать новую базу и загрузить контрольный срез с явно помеченной синтетикой."""

from __future__ import annotations

import subprocess
import sys

from db import ROOT, command, psql, run_file, save


def main() -> None:
    if psql("SELECT count(*) FROM pg_database WHERE datname = 'warehouse';", "postgres").strip() != "0":
        raise SystemExit("База warehouse уже существует. Загрузка остановлена без удаления данных.")
    synth = ROOT / "data" / "synth" / "weather_daily.csv"
    if not synth.exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_synth.py")], check=True)
    psql("CREATE DATABASE warehouse;", "postgres")
    run_file(ROOT / "sql" / "01_heap.sql")
    for path in [ROOT / "data" / "control" / "weather_daily.csv", synth]:
        with path.open("rb") as source:
            subprocess.run(
                command() + ["-c", "COPY published.weather_daily FROM STDIN WITH (FORMAT csv, HEADER true)"],
                cwd=ROOT, stdin=source, check=True,
            )
    psql("VACUUM (ANALYZE) published.weather_daily;")
    result = psql((ROOT / "sql" / "stats.sql").read_text())
    save("data_stats.txt", result)
    print(result)


if __name__ == "__main__":
    main()
