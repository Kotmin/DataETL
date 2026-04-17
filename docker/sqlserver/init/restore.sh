#!/bin/bash
set -euo pipefail

BACKUP_FILE="/backups/AdventureWorks2025.bak"
DB_NAME="AdventureWorks2025"
DATA_DIR="/var/opt/mssql/data"
SQLCMD="/opt/mssql-tools18/bin/sqlcmd"
SA_CONN="-S localhost -U sa -P ${MSSQL_SA_PASSWORD} -C"

/opt/mssql/bin/sqlservr &
MSSQL_PID=$!

echo "Waiting for SQL Server to accept connections..."
for i in $(seq 1 40); do
    "${SQLCMD}" ${SA_CONN} -Q "SELECT 1" -b > /dev/null 2>&1 && break
    echo "  attempt ${i}/40 — sleeping 3s"
    sleep 3
done

DB_EXISTS=$("${SQLCMD}" ${SA_CONN} \
    -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.databases WHERE name='${DB_NAME}'" \
    -h -1 | tr -d '[:space:]')

if [ "${DB_EXISTS}" = "0" ]; then
    echo "Detecting logical file names from backup..."
    FILELIST=$("${SQLCMD}" ${SA_CONN} \
        -Q "RESTORE FILELISTONLY FROM DISK='${BACKUP_FILE}'" \
        -h -1 2>/dev/null)

    DATA_LOGICAL=$(echo "${FILELIST}" | awk 'NR==1{print $1}')
    LOG_LOGICAL=$(echo "${FILELIST}"  | awk 'NR==2{print $1}')

    echo "  data logical: ${DATA_LOGICAL}"
    echo "  log  logical: ${LOG_LOGICAL}"

    echo "Restoring ${DB_NAME}..."
    "${SQLCMD}" ${SA_CONN} -Q "
        RESTORE DATABASE [${DB_NAME}]
        FROM DISK = '${BACKUP_FILE}'
        WITH MOVE '${DATA_LOGICAL}' TO '${DATA_DIR}/${DB_NAME}.mdf',
             MOVE '${LOG_LOGICAL}'  TO '${DATA_DIR}/${DB_NAME}_log.ldf',
             REPLACE, RECOVERY
    "
    echo "Restore complete."
else
    echo "${DB_NAME} already exists — skipping restore."
fi

wait "${MSSQL_PID}"
