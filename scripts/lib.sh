#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5000}"
export PGUSER="${PGUSER:-postgres}"
export PGPASSWORD="${PGPASSWORD:-postgres}"
export PGDATABASE="${PGDATABASE:-warehouse}"

psqlw() {
  docker compose exec -T node1 env PGPASSWORD=postgres \
    psql -h haproxy -p 5000 -U postgres -d "${PGDATABASE:-postgres}" -v ON_ERROR_STOP=1 "$@"
}

psql_on() {
  local node="$1"
  shift
  docker compose exec -T "$node" env PGPASSWORD=postgres \
    psql -h localhost -p 5432 -U postgres -d "${PGDATABASE:-postgres}" -v ON_ERROR_STOP=1 "$@"
}

leader_name() {
  docker compose exec -T node1 patronictl -c /tmp/patroni.yml list --format json \
    | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(next(r["Member"] for r in rows if r.get("Role")=="Leader"))'
}

replica_name() {
  docker compose exec -T node1 patronictl -c /tmp/patroni.yml list --format json \
    | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(next(r["Member"] for r in rows if r.get("Role")!="Leader"))'
}
