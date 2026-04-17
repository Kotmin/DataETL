# ETL Execution Plan — AdventureWorks Teaching Lab

## Overview

This document describes the execution plan, blocking dependency graph, and component responsibilities for the AdventureWorks ETL Teaching Lab PoC.

## Architecture

```
┌─────────────────────────────────────────┐
│  Host (Ubuntu / WSL2)                   │
│                                         │
│  Apache Airflow (local .venv)           │
│    └── DAG: etl_dim_product             │
│         extract → transform → load      │
│                                         │
│  Claude Code MCP: sql-query             │
│    └── tools/sql_query/server.py        │
└─────────────────┬───────────────────────┘
                  │ pyodbc / psycopg2
         ┌────────┴─────────┐
         ▼                  ▼
  ┌─────────────┐   ┌───────────────┐
  │ SQL Server  │   │  PostgreSQL   │
  │  (Docker)   │   │   (Docker)    │
  │  port 1433  │   │   port 5432   │
  │             │   │               │
  │ AdventureW. │   │ dim schema    │
  │    OLTP     │   │ dim_product   │
  └─────────────┘   └───────────────┘
```

## Blocking Dependency Graph

```
LAYER 0 — Prerequisites
  [P1] apt: msodbcsql18, python3-venv, unixodbc-dev
  [P2] .env.example → .env
  [P3] requirements.txt

LAYER 1 — Infrastructure                    (needs P2)
  [I1] docker/docker-compose.yml
  [I2] docker/sqlserver/init/restore.sh
  [I3] docker/postgres/init/01_warehouse_schema.sql
  ↓ docker compose up → DBs live

LAYER 2 — Mapping + SQL                     (can write before Docker; validate after)
  [S1] docs/source_to_target_mapping.md
  [S2] sql/source/extract_dim_product.sql   (needs S1)
  [S3] sql/warehouse/ddl_dim_product.sql    (needs S1)
  [S4] sql/transforms/transform_dim_product.sql

LAYER 3 — MCP Tool                          (needs P1 venv)
  [M1] tools/sql_query/server.py
  [M2] .claude/settings.json  ← MCP registration

LAYER 4 — ETL Pipeline                      (needs S2+S3+S4 + Docker up)
  [E1] airflow/dags/etl_dim_product.py
  [E2] scripts/start_airflow.sh
  [E3] scripts/bootstrap.sh
  [E4] scripts/reset_env.sh

LAYER 5 — Tests                             (needs I1-I3 up; T4 needs completed DAG)
  [T1] tests/conftest.py
  [T2] tests/test_extract.py    — requires live MSSQL
  [T3] tests/test_transform.py  — pure Python, no DB needed
  [T4] tests/test_load.py       — @pytest.mark.integration, needs DAG run

LAYER 6 — Ralph Agents
  [R1] .claude/agents/branch-master.md
  [R2] .claude/agents/hypervisor.md

LAYER 7 — Cron Jobs                         (after env verified working)
  [C1] Workflow state monitor  */30 9-18 * * 1-5
  [C2] Restore-if-failed cron  0 7 * * 1-5

CRITICAL PATH: P1→P2→I1→I2→I3→(DBs up)→S2+S3→E1→(Airflow run)→T4
```

## Components

### docker/docker-compose.yml
Spins up SQL Server 2022 (port 1433) and PostgreSQL 16 (port 5432) with persistent named volumes. SQL Server uses a custom entrypoint that restores the AdventureWorks `.bak` on first start. PostgreSQL auto-runs `01_warehouse_schema.sql` via `docker-entrypoint-initdb.d`.

### docker/sqlserver/init/restore.sh
Starts `sqlservr` in background, polls until ready, auto-detects logical file names via `RESTORE FILELISTONLY`, then restores the database. Idempotent — skips restore if database already exists.

### tools/sql_query/server.py
Universal MCP server (stdio transport). Exposes `query_sql(connection, sql)` — accepts `"mssql"` or `"postgres"`, returns JSON `list[dict]`. Registered in `.claude/settings.json` so Claude Code can query both databases directly during development.

### airflow/dags/etl_dim_product.py
3-task linear DAG (manual trigger only for PoC):
- `extract_dim_product` — reads `sql/source/extract_dim_product.sql`, queries MSSQL, pushes rows via XCom
- `transform_dim_product` — remaps column names, trims strings, pulls/pushes XCom
- `load_dim_product` — TRUNCATE + INSERT into `dim.dim_product` via psycopg2

### Ralph Agents
- **branch-master** — invoked via `/ralph-loop $(cat .claude/agents/branch-master.md) --completion-promise 'BRANCH CLEAN AND COMMITTED'`. Groups staged changes into atomic conventional commits.
- **hypervisor** — invoked via `/ralph-loop $(cat .claude/agents/hypervisor.md) --completion-promise 'ENVIRONMENT HEALTHY'`. Checks Docker + Airflow + stale ralph state.

### Cron Jobs (set up via `schedule` skill after first successful DAG run)
```bash
# Workflow state monitor
schedule: */30 9-18 * * 1-5
# Pre-lab container restore
schedule: 0 7 * * 1-5
```

## Milestones vs Plan Alignment

| PRD Milestone | Status |
|---|---|
| M1 — Architecture lock | Done (SQL Server + PostgreSQL + local Airflow) |
| M2 — Environment bootstrap | Done (bootstrap.sh + docker-compose.yml) |
| M3 — Mapping spec | Done (docs/source_to_target_mapping.md) |
| M4 — PoC implementation | Ready to verify (requires `./scripts/bootstrap.sh` run) |
| M5 — Phase 2 planning | Deferred |
