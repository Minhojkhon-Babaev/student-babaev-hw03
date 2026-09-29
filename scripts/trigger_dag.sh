#!/usr/bin/env bash
# Триггер DAG из контейнера Airflow.
set -euo pipefail
SLICE="${1:-control}"
cd "$(dirname "$0")/.."
docker compose exec -T airflow bash -lc \
  "export PATH=/home/airflow/.local/bin:\$PATH; airflow dags trigger weather_elt --conf '{\"slice\": \"${SLICE}\"}'"
echo "triggered slice=${SLICE}"
