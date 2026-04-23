# AdventureWorks ETL Teaching Lab

A reproducible ETL lab that demonstrates OLTP → dimensional modeling using AdventureWorks, Apache Airflow, and PostgreSQL.

## Prerequisites

- Ubuntu 22.04+ or Windows WSL2
- Docker Engine ≥ 24
- Python 3.12
- ~4 GB RAM for containers

## Quickstart

```bash
# 1. Clone and enter
git clone <repo-url>
cd DataETL

# 2. Bootstrap (installs ODBC driver, creates venv, starts containers)
./scripts/bootstrap.sh

# 3. Start Airflow
./scripts/start_airflow.sh

# 4. Open UI and trigger the DAG
#    http://localhost:8080  (admin / admin)
#    → Trigger: etl_dim_product

# 5. Verify
source .env
.venv/bin/pytest tests/test_transform.py tests/test_extract.py -v
.venv/bin/pytest tests/test_load.py -v -m integration
```

## Architecture

| Component | Technology | Location |
|---|---|---|
| Source DB | SQL Server 2022 (Docker, port 1433) | AdventureWorks2025 |
| Warehouse | PostgreSQL 16 (Docker, port 5432) | `dim` schema |
| Orchestrator | Apache Airflow 2.9.3 (local) | http://localhost:8080 |
| SQL MCP Tool | Python stdio MCP server | `tools/sql_query/` |

## Repository Structure

```
DataETL/
  docker/               Docker Compose + SQL Server restore script
  airflow/dags/         Airflow DAG definitions
  sql/                  Extract SQL, warehouse DDL, transform reference SQL
  tools/sql_query/      Universal SQL MCP server (pyodbc + psycopg2)
  tests/                pytest suite — unit and integration
  scripts/              bootstrap.sh / start_airflow.sh / reset_env.sh
  docs/                 Mapping spec, execution plan, restore guide
  ralph/                Ralph autonomous agent runner
  .claude/agents/       Ralph agent prompts (branch-master, hypervisor)
```

## Tests

```bash
# Unit tests (no DB required)
.venv/bin/pytest tests/test_transform.py -v

# DB tests (requires containers up)
source .env
.venv/bin/pytest tests/test_extract.py -v

# Integration tests (requires completed DAG run)
.venv/bin/pytest tests/test_load.py -v -m integration
```

## Reset

```bash
./scripts/reset_env.sh   # tears down volumes + Airflow state
./scripts/bootstrap.sh   # full rebuild
```

## Ralph Agents

```bash
# Git hygiene — groups changes into atomic conventional commits
/ralph-loop $(cat .claude/agents/branch-master.md) --completion-promise 'BRANCH CLEAN AND COMMITTED' --max-iterations 15

# Environment health check
/ralph-loop $(cat .claude/agents/hypervisor.md) --completion-promise 'ENVIRONMENT HEALTHY' --max-iterations 10
```

## Docs

- `docs/source_to_target_mapping.md` — column-level mapping for DimProduct
- `docs/etl_plan.md` — execution plan and blocking dependency graph
- `docs/workflow_restore.md` — restore guide for machine restarts and failures
- `PRD.md` — full product requirements