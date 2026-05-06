# AdventureWorks ETL Teaching Lab

A reproducible ETL lab that demonstrates OLTP → dimensional modeling using AdventureWorks, Apache Airflow, and PostgreSQL.

## Prerequisites

- Ubuntu 22.04+ or Windows WSL2
- Docker Engine ≥ 24
- Python 3.12
- ~4 GB RAM for containers

## Source Database

The AdventureWorks `.bak` file is **not included** in this repository (too large for Git). You must download it into `db-seed/` before running bootstrap.

> **Important:** download the **OLTP** edition (`AdventureWorks2025.bak`), not the Data Warehouse edition (`AdventureWorksDW2025.bak`). The lab depends on the normalized transactional schema.

Official install guide: https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure?view=sql-server-ver17&tabs=ssms

```bash
mkdir -p db-seed
curl -L -o db-seed/AdventureWorks2025.bak \
  https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks2025.bak
```

> **Note:** the direct download URL above targets a specific GitHub release tag and may change. If it fails, find the latest `.bak` on the releases page:
> https://github.com/Microsoft/sql-server-samples/releases/tag/adventureworks

## Quickstart

```bash
# 1. Clone and enter
git clone <repo-url>
cd DataETL

# 2. Download the AdventureWorks backup (see "Source Database" above)
mkdir -p db-seed && curl -L -o db-seed/AdventureWorks2025.bak \
  https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks2025.bak

# 3. Bootstrap — creates .env from .env.example, installs deps, starts containers
#    Afterwards review .env if you changed any passwords from the defaults
./scripts/bootstrap.sh

# 4. Start Airflow
./scripts/start_airflow.sh

# 5. Open UI and trigger the DAG
#    http://localhost:8080  (admin / admin)
#    → Trigger: etl_dim_product

# 6. Verify
source .env
.venv/bin/pytest tests/test_transform.py tests/test_extract.py -v
.venv/bin/pytest tests/test_load.py -v -m integration
```

## Airflow Configuration

`airflow/airflow.cfg` is committed to this repository intentionally — it is a teaching artifact that makes Airflow settings visible and editable without students having to locate generated files.

All machine-specific paths in the file use `${AIRFLOW_HOME}`, which Airflow expands at startup from the environment variable set by `start_airflow.sh`. No manual editing is needed after cloning.

> **Production note:** in real deployments `airflow.cfg` should be excluded from version control (add to `.gitignore`). It is a generated file that may contain secrets. Use `AIRFLOW__SECTION__KEY` environment variables or a secrets backend instead.

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