#!/usr/bin/env python3
"""Дождаться двух рабочих ролей, SQL и маршрутизации записи."""

from __future__ import annotations

import json
import subprocess
import time

from db import ROOT, psql


def members() -> list[dict]:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "node1", "patronictl",
         "-c", "/tmp/patroni.yml", "list", "--format", "json"],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    return json.loads(result.stdout)


def roles() -> tuple[str, str]:
    nodes = members()
    leaders = [n for n in nodes if n["Role"] == "Leader" and n["State"] == "running"]
    replicas = [n for n in nodes if n["Role"] == "Replica" and n["State"] in ["running", "streaming"]]
    assert len(leaders) == len(replicas) == 1, nodes
    return leaders[0]["Member"], replicas[0]["Member"]


def wait_for(check, timeout: int = 180):
    deadline = time.monotonic() + timeout
    last = None
    last_log = time.monotonic()
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (AssertionError, subprocess.CalledProcessError, KeyError) as exc:
            last = exc
        if time.monotonic() - last_log >= 30:
            print(f"Waiting for readiness: {last}", flush=True)
            last_log = time.monotonic()
        time.sleep(2)
    raise RuntimeError(f"Readiness timed out: {last}")


def ready():
    leader, replica = roles()
    assert psql("SELECT pg_is_in_recovery();", "postgres", leader).strip() == "f"
    assert psql("SELECT pg_is_in_recovery();", "postgres", replica).strip() == "t"
    assert psql("SELECT pg_is_in_recovery();", "postgres").strip() == "f"
    return leader, replica


if __name__ == "__main__":
    print("Ready:", wait_for(ready))
