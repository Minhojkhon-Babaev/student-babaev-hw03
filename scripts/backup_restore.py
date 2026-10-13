#!/usr/bin/env python3
"""Custom pg_dump, новая база, каталоги и точные потоковые сравнения данных."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import tempfile

from db import ROOT, command, psql, rows, save
from independent_check import check_database

CATALOG_QUERIES = {
    "schemas": "SELECT nspname FROM pg_namespace WHERE nspname IN ('published', 'demo') ORDER BY 1",
    "tables": """
        SELECT n.nspname, c.relname, c.relkind, pg_get_partkeydef(c.oid) AS partition_key,
               pg_get_expr(c.relpartbound, c.oid) AS partition_bound
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('published', 'demo') AND c.relkind IN ('r', 'p')
        ORDER BY 1, 2
    """,
    "columns": """
        SELECT table_schema, table_name, column_name, ordinal_position,
               data_type, udt_name, is_nullable, column_default,
               numeric_precision, numeric_scale
        FROM information_schema.columns WHERE table_schema IN ('published', 'demo')
        ORDER BY table_schema, table_name, ordinal_position
    """,
    "indexes": """
        SELECT schemaname, tablename, indexname, indexdef FROM pg_indexes
        WHERE schemaname IN ('published', 'demo') ORDER BY 1, 2, 3
    """,
    "constraints": """
        SELECT n.nspname, c.relname, k.conname, k.contype,
               pg_get_constraintdef(k.oid) AS definition, k.convalidated
        FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('published', 'demo') ORDER BY 1, 2, 3
    """,
}


def digest_table(database: str, schema: str, table: str) -> dict:
    n_columns = int(psql(
        f"SELECT count(*) FROM information_schema.columns "
        f"WHERE table_schema='{schema}' AND table_name='{table}';", database
    ).strip())
    order = ", ".join(str(position) for position in range(1, n_columns + 1))
    sql = f'COPY (SELECT * FROM "{schema}"."{table}" ORDER BY {order}) TO STDOUT WITH (FORMAT csv);'
    # Бинарный поток: никаких текстовых преобразований dump или CSV.
    with tempfile.TemporaryFile("w+b") as stream:
        result = subprocess.run(
            command(database) + ["-qAt", "-c", sql], cwd=ROOT,
            stdout=stream, stderr=subprocess.PIPE, check=True,
        )
        stream.seek(0)
        digest = hashlib.sha256()
        size = 0
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    count = int(psql(f'SELECT count(*) FROM "{schema}"."{table}";', database).strip())
    return {"rows": count, "csv_bytes": size, "sha256": digest.hexdigest()}


def main() -> None:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    database = "warehouse_restored_" + stamp.lower()
    path = ROOT / "backups" / f"warehouse_{stamp}.dump"
    path.parent.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(
        ["docker", "compose", "exec", "-T", "node1", "pg_dump", "--version"],
        cwd=ROOT, check=True, text=True, capture_output=True,
    ).stdout.strip()
    dump_cmd = [
        "docker", "compose", "exec", "-T", "node1", "env", "PGPASSWORD=postgres",
        "pg_dump", "-h", "haproxy", "-p", "5000", "-U", "postgres",
        "-d", "warehouse", "-Fc", "-f", f"/tmp/warehouse_{stamp}.dump",
    ]
    subprocess.run(dump_cmd, cwd=ROOT, check=True)
    subprocess.run(
        ["docker", "compose", "cp", f"node1:/tmp/warehouse_{stamp}.dump", str(path)],
        cwd=ROOT, check=True, capture_output=True,
    )
    with path.open("rb") as stream:
        assert stream.read(5) == b"PGDMP", "Custom archive header missing"
    psql(f"CREATE DATABASE {database};", "postgres")
    restore_cmd = [
        "docker", "compose", "exec", "-T", "node1", "env", "PGPASSWORD=postgres",
        "pg_restore", "-h", "haproxy", "-p", "5000", "-U", "postgres",
        "-d", database, "--no-owner", "--exit-on-error", f"/tmp/warehouse_{stamp}.dump",
    ]
    restored = subprocess.run(restore_cmd, cwd=ROOT, text=True, check=True, capture_output=True)
    lines = [
        f"pg_dump version: {version}", "format: custom (-Fc)",
        "dump command: " + " ".join(dump_cmd),
        "restore command: " + " ".join(restore_cmd),
        f"dump file: {path.name}; bytes={path.stat().st_size}",
        f"restored database: {database}", "PASS pg_restore exit_code=0",
    ]
    catalogs = {}
    for label, query in CATALOG_QUERIES.items():
        original = rows(query)
        restored_rows = rows(query, database)
        assert original == restored_rows, f"Catalog mismatch: {label}"
        catalogs[label] = original
        lines.append(f"PASS catalog {label}: {len(original)} objects equal")
    assert [s["nspname"] for s in catalogs["schemas"]] == ["demo", "published"]
    table_digests = {}
    for table in catalogs["tables"]:
        schema, name = table["nspname"], table["relname"]
        original = digest_table("warehouse", schema, name)
        copy = digest_table(database, schema, name)
        assert original == copy, f"Data mismatch: {schema}.{name}"
        table_digests[f"{schema}.{name}"] = original
        lines.append(f"PASS exact rows {schema}.{name}: n={original['rows']} sha256={original['sha256']}")
    for table in ["weather_daily", "weather_daily_part"]:
        query = f"""
            SELECT count(*) AS n,
                   count(*) FILTER (WHERE city_id IS NULL OR observed_date IS NULL) AS null_keys,
                   count(*) - count(DISTINCT (city_id, observed_date)) AS duplicates,
                   count(*) FILTER (WHERE NOT is_synthetic) AS control_rows
            FROM published.{table}
        """
        for db in ["warehouse", database]:
            assert rows(query, db) == [{"n": 109590, "null_keys": 0, "duplicates": 0, "control_rows": 9}]
        lines.append(f"PASS keys {table}: 109590 rows; null=0; duplicate=0; real=9")
    for name in ["narrow", "wide"]:
        baseline = json.loads((ROOT / f"evidence/bench/heap_{name}.json").read_text())["result"]
        for suffix in ["", "_part"]:
            query = (ROOT / f"sql/{name}{suffix}.sql").read_text()
            assert rows(query) == rows(query, database) == baseline
            lines.append(f"PASS restored {name}{suffix}: all keys and measures equal ({len(baseline)} rows)")
    lines.append(check_database(database).strip())
    save("restore_catalog.json", json.dumps(catalogs, ensure_ascii=False, indent=2) + "\n")
    metadata = {
        "database": database, "dump": str(path.relative_to(ROOT)), "format": "custom",
        "version": version, "dump_bytes": path.stat().st_size, "tables": table_digests,
        "restore_exit_code": restored.returncode,
    }
    save("restore_metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    save("restore_check.txt", "\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
