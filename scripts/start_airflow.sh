#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REPO_ROOT}/.venv/bin"

if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo "ERROR: .env not found. Run: cp ${REPO_ROOT}/.env.example ${REPO_ROOT}/.env"
    exit 1
fi

set -a
source "${REPO_ROOT}/.env"
set +a

export AIRFLOW_HOME="${REPO_ROOT}/airflow"
export AIRFLOW__CORE__DAGS_FOLDER="${REPO_ROOT}/airflow/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:////${REPO_ROOT}/airflow/airflow.db"

"${VENV}/airflow" db migrate

"${VENV}/airflow" users create \
    --username admin --password admin --role Admin \
    --firstname Lab --lastname Admin --email lab@local 2>/dev/null || true

echo "Starting Airflow webserver on http://localhost:8080 ..."
"${VENV}/airflow" webserver --port 8080 --daemon

echo "Starting Airflow scheduler ..."
"${VENV}/airflow" scheduler --daemon

echo "Airflow running. Logs: ${REPO_ROOT}/airflow/logs/"
echo "Stop with: pkill -f 'airflow webserver' && pkill -f 'airflow scheduler'"
