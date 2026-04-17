#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="${REPO_ROOT}/airflow/logs/prelab_restore.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$(dirname "${LOG}")"

log() { echo "${TIMESTAMP} $*" | tee -a "${LOG}"; }

if [ -f "${REPO_ROOT}/.env" ]; then
    set -a
    source "${REPO_ROOT}/.env"
    set +a
fi

PG_STATUS=$(docker inspect --format='{{.State.Health.Status}}' \
    "$(docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" ps -q postgres 2>/dev/null)" 2>/dev/null || echo "missing")

MSSQL_STATUS=$(docker inspect --format='{{.State.Health.Status}}' \
    "$(docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" ps -q sqlserver 2>/dev/null)" 2>/dev/null || echo "missing")

if [ "${PG_STATUS}" = "healthy" ] && [ "${MSSQL_STATUS}" = "healthy" ]; then
    log "[OK] Containers already healthy (pg:${PG_STATUS} mssql:${MSSQL_STATUS})"
    exit 0
fi

log "[RESTORE] Starting containers (pg:${PG_STATUS} mssql:${MSSQL_STATUS})"
docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" up -d

log "[RESTORE] Waiting for health checks (up to 120s)..."
for i in $(seq 1 24); do
    sleep 5
    PG_S=$(docker inspect --format='{{.State.Health.Status}}' \
        "$(docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" ps -q postgres 2>/dev/null)" 2>/dev/null || echo "missing")
    MSSQL_S=$(docker inspect --format='{{.State.Health.Status}}' \
        "$(docker compose -f "${REPO_ROOT}/docker/docker-compose.yml" --env-file "${REPO_ROOT}/.env" ps -q sqlserver 2>/dev/null)" 2>/dev/null || echo "missing")
    if [ "${PG_S}" = "healthy" ] && [ "${MSSQL_S}" = "healthy" ]; then
        log "[OK] Containers restored successfully"
        exit 0
    fi
done

log "[ERROR] Containers did not reach healthy state after 120s"
exit 1
