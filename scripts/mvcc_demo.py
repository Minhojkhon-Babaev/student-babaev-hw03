#!/usr/bin/env python3
"""Две рабочие сессии READ COMMITTED и отдельное соединение для наблюдения блокировок."""

from __future__ import annotations

import subprocess

from db import ROOT, psql, save

EXPERIMENT = r"""
import threading
import time
import psycopg2

def connect():
    return psycopg2.connect(host="haproxy", port=5000, user="postgres", password="postgres", dbname="warehouse")

a, b, observer = connect(), connect(), connect()
observer.autocommit = True
try:
    a.set_session(isolation_level="READ COMMITTED")
    b.set_session(isolation_level="READ COMMITTED")
    ca, cb, co = a.cursor(), b.cursor(), observer.cursor()
    for name, cur in [("A", ca), ("B", cb)]:
        cur.execute("SHOW transaction_isolation")
        print(name, "isolation =", cur.fetchone()[0], flush=True)
    ca.execute("UPDATE demo.mvcc_value SET value=20 WHERE id=1")
    ca.execute("SELECT value FROM demo.mvcc_value WHERE id=1")
    assert ca.fetchone()[0] == 20
    cb.execute("SELECT value FROM demo.mvcc_value WHERE id=1")
    before = cb.fetchone()[0]
    assert before == 10
    print("A updated 10 -> 20, uncommitted; B sees", before, flush=True)
    a.commit()
    cb.execute("SELECT value FROM demo.mvcc_value WHERE id=1")
    after = cb.fetchone()[0]
    assert after == 20
    print("A COMMIT; B next SELECT sees", after, flush=True)
    b.commit()
    ca.execute("UPDATE demo.mvcc_value SET value=30 WHERE id=1")
    errors = []
    def competing_update():
        try:
            cb.execute("SET LOCAL statement_timeout = '10s'")
            cb.execute("UPDATE demo.mvcc_value SET value=40 WHERE id=1")
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=competing_update)
    thread.start()
    deadline = time.monotonic() + 5
    waiting = None
    while time.monotonic() < deadline:
        co.execute(
            "SELECT pid, wait_event_type, wait_event, pg_blocking_pids(pid) "
            "FROM pg_stat_activity WHERE pid=%s", (b.get_backend_pid(),)
        )
        waiting = co.fetchone()
        if waiting and a.get_backend_pid() in waiting[3]:
            break
        time.sleep(.1)
    assert waiting and waiting[1] == "Lock" and a.get_backend_pid() in waiting[3], waiting
    print("B UPDATE waits:", waiting, "; blocker A pid =", a.get_backend_pid(), flush=True)
    a.rollback()
    thread.join(8)
    assert not thread.is_alive() and not errors, errors
    b.rollback()
    co.execute("SELECT value FROM demo.mvcc_value WHERE id=1")
    assert co.fetchone()[0] == 20
    print("A ROLLBACK releases lock; B UPDATE completes then B ROLLBACK; final value=20", flush=True)
    print("PASS: all transactions ended; mart data untouched", flush=True)
finally:
    a.rollback()
    b.rollback()
    a.close()
    b.close()
    observer.close()
"""


def main() -> None:
    psql("""
        CREATE SCHEMA IF NOT EXISTS demo;
        CREATE TABLE IF NOT EXISTS demo.mvcc_value (id integer PRIMARY KEY, value integer NOT NULL);
        INSERT INTO demo.mvcc_value VALUES (1, 10) ON CONFLICT (id) DO UPDATE SET value=10;
    """)
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "node1", "python3", "-c", EXPERIMENT],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    save("mvcc_two_sessions.txt", result.stdout + result.stderr)
    print(result.stdout)


if __name__ == "__main__":
    main()
