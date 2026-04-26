#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REPO_ROOT}/.venv"

echo "=== AdventureWorks ETL Lab — Bootstrap ==="

# ── 1. System dependencies ─────────────────────────────────────────────────
echo "[1/6] Checking system dependencies..."

if ! dpkg -s msodbcsql18 > /dev/null 2>&1; then
    echo "  Installing Microsoft ODBC Driver 18 for SQL Server..."
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
https://packages.microsoft.com/ubuntu/24.04/prod noble main" \
        | sudo tee /etc/apt/sources.list.d/mssql-release.list > /dev/null

    sudo apt-get update -q
    sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
fi

if ! dpkg -s python3-venv > /dev/null 2>&1; then
    sudo apt-get install -y python3-venv python3-pip
fi

# ── 2. Python venv ─────────────────────────────────────────────────────────
echo "[2/6] Setting up Python venv at ${VENV}..."
if [ ! -d "${VENV}" ]; then
    python3 -m venv "${VENV}"
fi
"${VENV}/bin/pip" install --quiet --upgrade pip
"${VENV}/bin/pip" install --quiet -r "${REPO_ROOT}/requirements.txt"

# ── 3. Environment file ─────────────────────────────────────────────────────
echo "[3/6] Preparing .env..."
if [ ! -f "${REPO_ROOT}/.env" ]; then
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    echo "  Created .env from .env.example — review and update passwords if needed."
fi

set -a
source "${REPO_ROOT}/.env"
set +a

# ── 4. Docker containers ────────────────────────────────────────────────────
COMPOSE="docker compose -f ${REPO_ROOT}/docker/docker-compose.yml --env-file ${REPO_ROOT}/.env"

echo "[4/6] Starting Docker containers..."
${COMPOSE} up -d

echo "  Waiting for containers to be healthy (SQL Server restore may take ~120s)..."
for i in $(seq 1 36); do
    PG_STATUS=$(docker inspect docker-postgres-1  --format '{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    SQL_STATUS=$(docker inspect docker-sqlserver-1 --format '{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    if [ "${PG_STATUS}" = "healthy" ] && [ "${SQL_STATUS}" = "healthy" ]; then
        echo "  Both containers healthy."
        break
    fi
    echo "  [${i}/36] postgres=${PG_STATUS}  sqlserver=${SQL_STATUS} — retrying in 10s..."
    sleep 10
done

# ── 5. Airflow initialisation ───────────────────────────────────────────────
echo "[5/6] Initialising Airflow..."
export AIRFLOW_HOME="${REPO_ROOT}/airflow"
export AIRFLOW__CORE__DAGS_FOLDER="${REPO_ROOT}/airflow/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:////${REPO_ROOT}/airflow/airflow.db"
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True

"${VENV}/bin/airflow" db migrate 2>&1 | tail -5

# ── 6. Verify connections ───────────────────────────────────────────────────
echo "[6/6] Verifying database connections..."

PG_OK=$("${VENV}/bin/python" -c "
import psycopg2, os
try:
    c = psycopg2.connect(host=os.environ['PG_HOST'], port=os.environ['PG_PORT'],
        dbname=os.environ['PG_DB'], user=os.environ['PG_USER'], password=os.environ['PG_PASSWORD'])
    c.close(); print('OK')
except Exception as e: print(f'FAIL: {e}')
")
echo "  PostgreSQL: ${PG_OK}"

MSSQL_OK=$("${VENV}/bin/python" -c "
import pyodbc, os
try:
    dsn = (f\"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.environ['MSSQL_HOST']},{os.environ['MSSQL_PORT']};\"
           f\"DATABASE={os.environ['MSSQL_DB']};UID=sa;PWD={os.environ['MSSQL_SA_PASSWORD']};TrustServerCertificate=yes;\")
    c = pyodbc.connect(dsn); c.close(); print('OK')
except Exception as e: print(f'FAIL: {e}')
")
echo "  SQL Server:  ${MSSQL_OK}"

echo ""
echo "=== Bootstrap complete ==="
echo "  Start Airflow: ./scripts/start_airflow.sh"
echo "  UI:            http://localhost:8080  (admin / admin)"
echo "  Trigger DAG:   etl_dim_product"
echo "  Reset env:     ./scripts/reset_env.sh"
