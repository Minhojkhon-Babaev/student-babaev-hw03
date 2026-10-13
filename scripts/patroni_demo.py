#!/usr/bin/env python3
"""Реальные роли, передача маркеров, явный switchover и отклонение записи."""

from __future__ import annotations

import json
import subprocess
import uuid

from db import ROOT, command, psql, rows, save
from wait_cluster import members, ready, roles, wait_for


def snapshot(title: str) -> str:
    lines = [title, json.dumps(members(), indent=2)]
    for node in ["node1", "node2"]:
        lines.append(node + ": " + psql(
            "SELECT pg_is_in_recovery(), current_setting('transaction_read_only'), "
            "inet_server_addr(), pg_last_wal_replay_lsn();", node=node,
        ).strip())
    lines.append("haproxy:5000: " + psql(
        "SELECT pg_is_in_recovery(), current_setting('transaction_read_only'), inet_server_addr();"
    ).strip())
    return "\n".join(lines) + "\n"


def main() -> None:
    leader, replica = wait_for(ready)
    save("patroni_roles_before.txt", snapshot("Before switchover"))
    marker1 = "before-" + uuid.uuid4().hex
    marker2 = "after-" + uuid.uuid4().hex
    rejected = "rejected-" + uuid.uuid4().hex
    psql("""
        CREATE TABLE IF NOT EXISTS published.repl_marker (
            id text PRIMARY KEY,
            note text NOT NULL,
            inserted_at timestamptz NOT NULL DEFAULT now()
        );
    """)
    psql(f"INSERT INTO published.repl_marker(id, note) VALUES ('{marker1}', 'via haproxy:5000 before switchover');")

    def received(node, ids):
        names = ", ".join(f"'{marker}'" for marker in ids)
        return psql(
            f"SELECT count(*) FROM published.repl_marker WHERE id IN ({names});", node=node,
        ).strip() == str(len(ids))

    wait_for(lambda: received(replica, [marker1]))
    assert psql("SELECT count(*) FROM published.weather_daily;", node=replica).strip() == "109590"
    save("patroni_marker_replica.txt", snapshot("Marker replicated before switchover") +
         psql("SELECT id, note, pg_is_in_recovery() FROM published.repl_marker ORDER BY id;", node=replica))
    result = subprocess.run(
        command(node=replica) + ["-c", f"INSERT INTO published.repl_marker(id, note) VALUES ('{rejected}', 'must fail');"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode != 0 and "read-only transaction" in result.stderr, result.stderr
    for node in [leader, replica]:
        assert psql(f"SELECT count(*) FROM published.repl_marker WHERE id='{rejected}';", node=node).strip() == "0"
    save("patroni_replica_write.txt",
         result.stdout + result.stderr + f"PASS exit_code={result.returncode}; rejected marker absent on both nodes\n")

    switch = subprocess.run(
        ["docker", "compose", "exec", "-T", "node1", "patronictl", "-c", "/tmp/patroni.yml",
         "switchover", "--leader", leader, "--candidate", replica, "--force"],
        cwd=ROOT, text=True, check=True, capture_output=True,
    )
    save("patroni_switchover.txt", switch.stdout + switch.stderr)

    def switched():
        new_leader, new_replica = ready()
        assert new_leader == replica and new_replica == leader
        return new_leader, new_replica

    new_leader, new_replica = wait_for(switched)
    assert received(new_leader, [marker1])
    psql(f"INSERT INTO published.repl_marker(id, note) VALUES ('{marker2}', 'via haproxy:5000 after switchover');")
    wait_for(lambda: received(new_replica, [marker1, marker2]))
    save("patroni_roles_after.txt", snapshot("After switchover") +
         f"PASS old_leader={leader}; new_leader={new_leader}; new_replica={new_replica}\n")
    names = f"'{marker1}', '{marker2}'"
    text = "After switchover: old and new markers on BOTH nodes\n"
    for node in [new_leader, new_replica]:
        text += node + "\n" + psql(
            f"SELECT id, note, pg_is_in_recovery() FROM published.repl_marker WHERE id IN ({names}) ORDER BY id;",
            node=node,
        )
    save("patroni_markers_after.txt", text)
    for name in ["narrow", "wide"]:
        query = (ROOT / f"sql/{name}.sql").read_text()
        baseline = json.loads((ROOT / f"evidence/bench/heap_{name}.json").read_text())["result"]
        assert rows(query) == baseline
        assert psql("SELECT count(*) FROM published.weather_daily;", node=new_replica).strip() == "109590"
    save("patroni_control_after_switch.txt", "PASS both analytic results equal baseline after switchover; replica has 109590 mart rows\n")
    print(text)


if __name__ == "__main__":
    main()
