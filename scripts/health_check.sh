#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
ISSUES=()

if [ -f "${REPO_ROOT}/.env" ]; then
    set -a
    source "${REPO_ROOT}/.env"
    set +a
fi

PG_STATUS=$(docker inspect --format='{{.State.Health.Status}}' \
    "$(docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" ps -q postgres 2>/dev/null)" 2>/dev/null || echo "missing")

MSSQL_STATUS=$(docker inspect --format='{{.State.Health.Status}}' \
    "$(docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" ps -q sqlserver 2>/dev/null)" 2>/dev/null || echo "missing")

[ "${PG_STATUS}" != "healthy" ] && ISSUES+=("postgres: ${PG_STATUS}")
[ "${MSSQL_STATUS}" != "healthy" ] && ISSUES+=("sqlserver: ${MSSQL_STATUS}")

curl -s http://localhost:8080/api/v2/monitor/health > /dev/null 2>&1 || ISSUES+=("airflow api-server: DOWN")
pgrep -E -f "airflow (scheduler|standalone)" > /dev/null 2>&1 || ISSUES+=("airflow scheduler: DOWN")

if [ ${#ISSUES[@]} -eq 0 ]; then
    echo "${TIMESTAMP} [OK] All services healthy"
else
    echo "${TIMESTAMP} [WARN] Issues detected:"
    for issue in "${ISSUES[@]}"; do
        echo "  - ${issue}"
    done
fi
