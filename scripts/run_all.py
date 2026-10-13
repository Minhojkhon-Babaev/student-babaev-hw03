#!/usr/bin/env python3
"""Выполнить ДЗ с нуля; существующая warehouse не перезаписывается."""

from __future__ import annotations

import datetime as dt
import json
import platform
import subprocess
import sys
import time

from db import ROOT, SETTINGS, psql, rows, run_file, save
from wait_cluster import ready, wait_for


def run(*arguments: str) -> None:
    print("$ " + " ".join(arguments), flush=True)
    subprocess.run(list(arguments), cwd=ROOT, check=True)


def environment() -> None:
    lines = [f"Run UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}",
             f"Host: {platform.platform()}", f"Host Python: {platform.python_version()}"]
    commands = [
        ["docker", "version", "--format", "{{.Client.Version}} / {{.Server.Version}}"],
        ["docker", "compose", "version"],
        ["docker", "info", "--format", "VM CPUs={{.NCPU}}; memory bytes={{.MemTotal}}; arch={{.Architecture}}"],
        ["docker", "compose", "exec", "-T", "node1", "postgres", "--version"],
        ["docker", "compose", "exec", "-T", "node1", "patroni", "--version"],
        ["docker", "compose", "exec", "-T", "node1", "python3", "--version"],
        ["docker", "compose", "exec", "-T", "node1", "pip3", "freeze"],
        ["docker", "compose", "exec", "-T", "etcd", "etcd", "--version"],
        ["docker", "compose", "exec", "-T", "haproxy", "haproxy", "-v"],
        ["docker", "image", "inspect", "postgres:16.4-bookworm", "quay.io/coreos/etcd:v3.5.16",
         "haproxy:2.9.15-alpine", "--format", "{{.RepoTags}} {{.Id}} {{.RepoDigests}}"],
        ["docker", "compose", "ps"],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=ROOT, check=True, text=True, capture_output=True)
        lines += ["$ " + " ".join(cmd), result.stdout.strip()]
    lines.append(psql(SETTINGS + """
        SELECT name, setting, unit FROM pg_settings WHERE name IN (
            'server_version', 'shared_buffers', 'work_mem', 'max_parallel_workers_per_gather',
            'jit', 'enable_seqscan', 'enable_partition_pruning', 'random_page_cost',
            'seq_page_cost', 'effective_cache_size', 'TimeZone', 'default_transaction_isolation'
        ) ORDER BY name;
    """, "postgres"))
    save("environment.txt", "\n".join(lines) + "\n")


def main() -> None:
    wait_for(ready)
    if psql("SELECT count(*) FROM pg_database WHERE datname='warehouse';", "postgres").strip() != "0":
        raise SystemExit("warehouse уже существует: run_all не удаляет и не перезаписывает данные.")
    environment()
    started = time.perf_counter()
    run(sys.executable, "scripts/generate_synth.py")
    generated = time.perf_counter() - started
    started = time.perf_counter()
    run(sys.executable, "scripts/load_mart.py")
    loaded = time.perf_counter() - started
    run(sys.executable, "scripts/independent_check.py")
    for name in ["narrow", "wide"]:
        run(sys.executable, "scripts/bench.py", "--sql", f"sql/{name}.sql", "--label", f"heap_{name}")
    started = time.perf_counter()
    run_file(ROOT / "sql/02_index.sql")
    indexed = time.perf_counter() - started
    run(sys.executable, "scripts/equality.py", "--stage", "index")
    for name in ["narrow", "wide"]:
        run(sys.executable, "scripts/bench.py", "--sql", f"sql/{name}.sql", "--label", f"index_{name}")
    started = time.perf_counter()
    run_file(ROOT / "sql/03_partition.sql")
    partitioned = time.perf_counter() - started
    run(sys.executable, "scripts/equality.py", "--stage", "partition")
    for name in ["narrow", "wide"]:
        run(sys.executable, "scripts/bench.py", "--sql", f"sql/{name}_part.sql", "--label", f"part_{name}")
    sizes = rows("""
        SELECT c.relname, pg_relation_size(c.oid) AS table_bytes,
               pg_indexes_size(c.oid) AS index_bytes
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='published' AND c.relkind IN ('r', 'p') ORDER BY c.relname
    """)
    save("sizes.json", json.dumps(sizes, indent=2) + "\n")
    costs = {"synthetic_generation_client_s": generated, "load_vacuum_client_s": loaded,
             "index_build_vacuum_client_s": indexed, "partition_create_copy_vacuum_client_s": partitioned}
    save("setup_costs.json", json.dumps(costs, indent=2) + "\n")
    run(sys.executable, "scripts/patroni_demo.py")
    run(sys.executable, "scripts/mvcc_demo.py")
    run(sys.executable, "scripts/equality.py", "--stage", "final")
    run(sys.executable, "scripts/backup_restore.py")
    save("completed.txt", f"PASS all runtime checks completed at {dt.datetime.now(dt.timezone.utc).isoformat()}\n")
    print("PASS: all runtime checks completed", flush=True)


if __name__ == "__main__":
    main()
