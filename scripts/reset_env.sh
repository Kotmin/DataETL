#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Stopping Airflow processes..."
PID_FILE="${REPO_ROOT}/airflow/airflow.pid"
if [ -f "${PID_FILE}" ]; then
    kill "$(cat "${PID_FILE}")" 2>/dev/null || true
    rm -f "${PID_FILE}"
fi
pkill -f "airflow standalone" 2>/dev/null || true
pkill -f "airflow scheduler"  2>/dev/null || true

echo "Tearing down Docker containers and volumes..."
docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" down -v 2>/dev/null || \
    docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" down -v

echo "Removing Airflow state..."
rm -f "${REPO_ROOT}/airflow/airflow.db"
rm -rf "${REPO_ROOT}/airflow/logs"

echo "Done. Run ./scripts/bootstrap.sh to rebuild the environment."
