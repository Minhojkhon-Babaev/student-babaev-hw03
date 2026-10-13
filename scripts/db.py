"""Общие команды psql к текущему лидеру учебного кластера."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = """
SET timezone = 'UTC';
SET max_parallel_workers_per_gather = 0;
SET work_mem = '16MB';
SET jit = off;
"""


def command(database: str = "warehouse", node: str | None = None) -> list[str]:
    return [
        "docker", "compose", "exec", "-T", node or "node1",
        "env", "PGPASSWORD=postgres", "PGCONNECT_TIMEOUT=5", "psql", "-X",
        "-h", "localhost" if node else "haproxy",
        "-p", "5432" if node else "5000",
        "-U", "postgres", "-d", database, "-v", "ON_ERROR_STOP=1",
    ]


def psql(sql: str, database: str = "warehouse", node: str | None = None) -> str:
    result = subprocess.run(
        command(database, node) + ["-qAt"], cwd=ROOT,
        input=sql, text=True, check=True, capture_output=True,
    )
    return result.stdout


def rows(query: str, database: str = "warehouse") -> list[dict]:
    query = query.strip().rstrip(";")
    result = psql(
        SETTINGS + f"SELECT coalesce(json_agg(q), '[]'::json) FROM ({query}) q;",
        database,
    )
    return json.loads(result.strip())


def run_file(path: Path) -> None:
    psql(path.read_text(encoding="utf-8"))


def save(path: str, text: str) -> None:
    target = ROOT / "evidence" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
