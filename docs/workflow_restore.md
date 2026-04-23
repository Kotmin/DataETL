# Workflow Restore Guide

How to restore this lab to a working state after a machine restart, crash, or partial execution failure.

## Quick Reference

| Symptom | Fix |
|---|---|
| Containers stopped after reboot | [Step A](#a-restart-docker-containers) |
| Airflow not running | [Step B](#b-restart-airflow) |
| SQL Server restore never finished | [Step C](#c-force-full-reseed) |
| MCP sql-query tool not responding | [Step D](#d-mcp-tool-issues) |
| ralph-loop stuck / session orphaned | [Step E](#e-stuck-ralph-loop) |
| Complete wipe and rebuild | [Step F](#f-full-rebuild) |

---

## A. Restart Docker Containers

```bash
cd /home/kotmin/Coding/DataETL
source .env
docker compose -f docker/docker-compose.yml up -d
```

Wait ~90 seconds for SQL Server to come healthy (first start restores the `.bak`; subsequent starts are fast).

Check status:
```bash
docker compose -f docker/docker-compose.yml ps
```

Both `sqlserver` and `postgres` should show `healthy`.

---

## B. Restart Airflow

```bash
cd /home/kotmin/Coding/DataETL
./scripts/start_airflow.sh
```

Access UI at http://localhost:8080 (admin / admin).

If Airflow fails to start, check if a stale PID file exists:
```bash
rm -f airflow/airflow-webserver.pid airflow/airflow-scheduler.pid
./scripts/start_airflow.sh
```

---

## C. Force Full Reseed (SQL Server)

Use this when the SQL Server container started but the restore never completed (e.g., power cut mid-restore).

```bash
cd /home/kotmin/Coding/DataETL
docker compose -f docker/docker-compose.yml stop sqlserver
docker compose -f docker/docker-compose.yml rm -f sqlserver
docker volume rm datametl_sqlserver-data 2>/dev/null || \
    docker volume rm $(docker volume ls -q | grep sqlserver-data)
docker compose -f docker/docker-compose.yml up -d sqlserver
```

The volume removal forces `restore.sh` to re-run the full `RESTORE DATABASE` on next start.

---

## D. MCP Tool Issues

The `sql-query` MCP server runs as a subprocess of Claude Code. It requires:
1. `.venv/` exists with `mcp`, `pyodbc`, and `psycopg2-binary` installed
2. Both Docker containers are healthy
3. `.env` is sourced (MCP server reads env vars from `settings.json`)

If Claude Code can't reach the tool:
```bash
# Verify venv
/home/kotmin/Coding/DataETL/.venv/bin/python -c "import mcp, pyodbc, psycopg2; print('OK')"

# Test manually (should return JSON)
source /home/kotmin/Coding/DataETL/.env
MSSQL_CONN="DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost,1433;DATABASE=AdventureWorks2025;UID=sa;PWD=${MSSQL_SA_PASSWORD};TrustServerCertificate=yes;" \
PG_CONN="postgresql://${PG_USER}:${PG_PASSWORD}@${PG_HOST}:${PG_PORT}/${PG_DB}" \
/home/kotmin/Coding/DataETL/.venv/bin/python /home/kotmin/Coding/DataETL/tools/sql_query/server.py
```

Restart Claude Code after fixing — MCP servers are started at session open time.

---

## E. Stuck Ralph Loop

If a ralph-loop session is orphaned (Claude Code session closed without completing):

```bash
# Find and inspect the state file
cat /home/kotmin/Coding/DataETL/.claude/ralph-loop.local.md

# If stale (no matching live Claude session), remove it
rm /home/kotmin/Coding/DataETL/.claude/ralph-loop.local.md
```

In worktrees:
```bash
find /home/kotmin/Coding/DataETL -name "ralph-loop.local.md" -print
# Review each, remove stale ones
```

---

## F. Full Rebuild

Wipes everything and starts from scratch. Use when all else fails.

```bash
cd /home/kotmin/Coding/DataETL

# 1. Tear down
./scripts/reset_env.sh

# 2. Rebuild (re-runs all setup steps)
./scripts/bootstrap.sh

# 3. Start Airflow
./scripts/start_airflow.sh

# 4. Trigger DimProduct DAG in UI
open http://localhost:8080
# → Trigger etl_dim_product manually

# 5. Verify
source .env
.venv/bin/pytest tests/test_transform.py tests/test_extract.py -v
.venv/bin/pytest tests/test_load.py -v -m integration
```

---

## Restore from Plan File

If the entire execution state is lost and you need to resume work from the plan:

```bash
# The plan is saved at:
cat /home/kotmin/.claude/plans/we-want-to-work-glimmering-kahn.md

# Check git log to see what was completed
git log --oneline

# Resume the next uncommitted step from the plan
```

The plan file at `/home/kotmin/.claude/plans/we-want-to-work-glimmering-kahn.md` contains the full blocking dependency graph and implementation order. Match the last git commit to the implementation order table to find the next step.

---

## Environment Health Check (one-liner)

```bash
cd /home/kotmin/Coding/DataETL && \
  source .env && \
  docker compose -f docker/docker-compose.yml ps && \
  pgrep -f "airflow webserver" > /dev/null && echo "Airflow:UP" || echo "Airflow:DOWN" && \
  .venv/bin/pytest tests/test_transform.py -q
```
