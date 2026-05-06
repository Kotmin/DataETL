#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REPO_ROOT}/.venv/bin"
LOG="${REPO_ROOT}/airflow/logs/standalone.log"

if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo "ERROR: .env not found. Run: cp ${REPO_ROOT}/.env.example ${REPO_ROOT}/.env"
    exit 1
fi

set -a
source "${REPO_ROOT}/.env"
set +a

export PATH="${VENV}:${PATH}"

export AIRFLOW_HOME="${REPO_ROOT}/airflow"
export AIRFLOW__CORE__DAGS_FOLDER="${REPO_ROOT}/airflow/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:////${REPO_ROOT}/airflow/airflow.db"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True

"${VENV}/airflow" db migrate

mkdir -p "${REPO_ROOT}/airflow/logs"

echo "Starting Airflow standalone (api-server + scheduler + triggerer)..."
nohup "${VENV}/airflow" standalone > "${LOG}" 2>&1 &
AIRFLOW_PID=$!
echo "${AIRFLOW_PID}" > "${REPO_ROOT}/airflow/airflow.pid"

echo "Waiting for API server to be ready..."
HEALTHY=0
for i in $(seq 1 30); do
    curl -s http://localhost:8080/api/v2/monitor/health > /dev/null 2>&1 && { HEALTHY=1; break; }
    sleep 2
done
if [ "${HEALTHY}" -eq 0 ]; then
    echo "ERROR: Airflow did not become healthy after 60s. Check logs: ${LOG}"
    exit 1
fi

echo ""
echo "Airflow running  (PID ${AIRFLOW_PID})"
echo "  UI:   http://localhost:8080"
echo "  Logs: ${LOG}"
echo "  Stop: kill \$(cat ${REPO_ROOT}/airflow/airflow.pid)"
