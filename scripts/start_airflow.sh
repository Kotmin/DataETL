#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REPO_ROOT}/.venv/bin"
LOG="${REPO_ROOT}/airflow/logs/standalone.log"

if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo "ERROR: .env not found. Run: cp ${REPO_ROOT}/.env.example ${REPO_ROOT}/.env"
    exit 1
fi

sed -i 's/\r//' "${REPO_ROOT}/.env"
set -a
source "${REPO_ROOT}/.env"
set +a

export PATH="${VENV}:${PATH}"

export AIRFLOW_HOME="${REPO_ROOT}/airflow"
export AIRFLOW__CORE__DAGS_FOLDER="${REPO_ROOT}/airflow/dags"
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///${REPO_ROOT}/airflow/airflow.db?timeout=30"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS=admin:admin
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=False
export AIRFLOW__EXECUTION_API__JWT_EXPIRATION_TIME=86400
export AIRFLOW__CORE__PARALLELISM=8
export AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG=4

"${VENV}/airflow" db migrate
"${VENV}/python" -c "import sqlite3; c=sqlite3.connect('${REPO_ROOT}/airflow/airflow.db'); c.execute('PRAGMA journal_mode=WAL'); c.close()"

pkill -f "airflow (standalone|api_server|scheduler|triggerer|dag-processor|serve-logs)" 2>/dev/null || true
sleep 3
rm -f "${REPO_ROOT}/airflow/airflow.pid"

mkdir -p "${REPO_ROOT}/airflow/logs"

echo "Starting Airflow standalone (api-server + scheduler + triggerer)..."
nohup "${VENV}/airflow" standalone > "${LOG}" 2>&1 &
AIRFLOW_PID=$!
echo "${AIRFLOW_PID}" > "${REPO_ROOT}/airflow/airflow.pid"

echo "Waiting for all Airflow components to be healthy..."
HEALTHY=0
for i in $(seq 1 36); do
    HEALTH_JSON=$(curl -sf http://localhost:8080/api/v2/monitor/health 2>/dev/null || echo "")
    if [ -n "${HEALTH_JSON}" ]; then
        SCHED=$(echo "${HEALTH_JSON}" | "${VENV}/python" -c \
            "import sys,json; d=json.load(sys.stdin); print((d.get('scheduler') or {}).get('status','unknown'))" 2>/dev/null || echo "unknown")
        TRIG=$(echo "${HEALTH_JSON}" | "${VENV}/python" -c \
            "import sys,json; d=json.load(sys.stdin); print((d.get('triggerer') or {}).get('status','unknown'))" 2>/dev/null || echo "unknown")
        DAG=$(echo "${HEALTH_JSON}" | "${VENV}/python" -c \
            "import sys,json; d=json.load(sys.stdin); print((d.get('dag_processor') or {}).get('status','unknown'))" 2>/dev/null || echo "unknown")
        if [ "${SCHED}" = "healthy" ] && [ "${TRIG}" = "healthy" ] && [ "${DAG}" = "healthy" ]; then
            HEALTHY=1; break
        fi
        echo "  [${i}/36] scheduler=${SCHED}  triggerer=${TRIG}  dag_processor=${DAG} — retrying in 5s..."
    else
        echo "  [${i}/36] API not responding yet — retrying in 5s..."
    fi
    sleep 5
done
if [ "${HEALTHY}" -eq 0 ]; then
    echo "ERROR: Airflow components did not become healthy after 180s. Check: ${LOG}"
    exit 1
fi

echo ""
echo "Airflow running  (PID ${AIRFLOW_PID})"
echo "  UI:   http://localhost:8080"
echo "  Logs: ${LOG}"
echo "  Stop: kill \$(cat ${REPO_ROOT}/airflow/airflow.pid)"
