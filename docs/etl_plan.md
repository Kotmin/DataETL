# ETL Execution Plan — AdventureWorks Teaching Lab

## Overview

AdventureWorks OLTP (SQL Server) → Airflow ETL → Star schema data mart (PostgreSQL).
9 DAGs, 8 dimensions + 1 fact table, ~83k rows total.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Host (Ubuntu / WSL2)                                │
│                                                      │
│  Apache Airflow 3.2.0 (local .venv, standalone)      │
│    DAGs:                                             │
│      etl_dim_date          (daily  03:00)            │
│      etl_dim_order_channel (weekly Mon 02:00)        │
│      etl_dim_sales_territory (weekly Mon 02:00)      │
│      etl_dim_delivery_method (weekly Mon 02:00)      │
│      etl_dim_payment_method  (weekly Mon 02:00)      │
│      etl_dim_geography     (daily  03:00)            │
│      etl_dim_product       (daily  03:00)            │
│      etl_dim_customer      (daily  04:00)            │
│      etl_fact_online_sales (hourly)                  │
│                                                      │
│  Operations CLI: app/main.py                         │
│  Claude Code MCP: tools/sql_query/server.py          │
└──────────────────┬───────────────────────────────────┘
                   │ pyodbc / psycopg2
          ┌────────┴─────────┐
          ▼                  ▼
   ┌─────────────┐   ┌───────────────┐
   │ SQL Server  │   │  PostgreSQL   │
   │  (Docker)   │   │   (Docker)    │
   │  port 1433  │   │   port 5432   │
   │ AW2025 OLTP │   │ dim + fact    │
   └─────────────┘   └───────────────┘
```

## Quickstart

```bash
# 1 — Start databases
cd docker && docker compose up -d

# 2 — Start Airflow
./scripts/start_airflow.sh        # UI at http://localhost:8080

# 3 — Check warehouse state
.venv/bin/python app/main.py status

# 4 — Run all ETL (direct, no scheduler)
.venv/bin/python app/main.py run --all

# 4b — OR trigger via Airflow scheduler
.venv/bin/python app/main.py airflow-trigger --all

# 5 — Export to CSV
.venv/bin/python app/main.py export --out exports/

# 6 — Run tests
.venv/bin/pytest tests/ -v
```

## DAG Execution Order and Schedules

Dependencies must be respected when triggering manually:

```
1. etl_dim_date             daily 03:00      (MSSQL — date range from OrderDate/ShipDate)
2. etl_dim_order_channel    weekly Mon 02:00 (MSSQL — DISTINCT OnlineOrderFlag)
3. etl_dim_sales_territory  weekly Mon 02:00 (MSSQL — SalesTerritory + CountryRegion)
4. etl_dim_delivery_method  weekly Mon 02:00 (MSSQL — Purchasing.ShipMethod)
5. etl_dim_payment_method   weekly Mon 02:00 (MSSQL — DISTINCT CardType)  ← before fact
6. etl_dim_geography        daily 03:00      (MSSQL — city-grain surrogate)  ← before customer
7. etl_dim_product          daily 03:00      (MSSQL — Product + subcategory + category)
8. etl_dim_customer         daily 04:00      (MSSQL + PG lookup for geography_key)
9. etl_fact_online_sales    hourly           (MSSQL + PG lookup for payment_method_key)
```

**On scheduling intervals:** all DAGs use full reload (TRUNCATE + INSERT). Hourly for fact
is appropriate for this pattern. A 5-minute interval requires an incremental/CDC approach
— only new or changed rows would be written each run instead of re-loading the whole table.

## Blocking Dependency Graph

```
LAYER 0 — Prerequisites
  [P1] apt: msodbcsql18, python3-venv, unixodbc-dev
  [P2] .env.example → .env
  [P3] requirements.txt → .venv/bin/pip install

LAYER 1 — Infrastructure                      (needs P2)
  [I1] docker/docker-compose.yml
  [I2] docker/sqlserver/init/restore.sh
  [I3] docker/postgres/init/01_warehouse_schema.sql
  ↓ docker compose up → DBs live

LAYER 2 — Mapping + SQL                       (validate after Docker up)
  [S1] docs/source_to_target_mapping.md        ← canonical column mapping
  [S2] sql/source/extract_*.sql               (9 files)
  [S3] sql/warehouse/ddl_*.sql               (9 files)

LAYER 3 — MCP Tool                            (needs P3 venv)
  [M1] tools/sql_query/server.py
  [M2] .claude/settings.json  ← MCP registration

LAYER 4 — ETL Pipeline                        (needs S2+S3 + Docker up)
  [E1] airflow/dags/connections.py            ← shared MSSQLParams / PGParams
  [E2] airflow/dags/etl_*.py                 (9 DAGs)
  [E3] scripts/start_airflow.sh
  [E4] app/main.py                            ← ops CLI

LAYER 5 — Tests
  [T1] tests/test_transform.py               pure Python, no DB
  [T2] tests/test_transform_phase2.py        pure Python, no DB

CRITICAL PATH: P1→P2→I1→I2→I3→(DBs up)→S2+S3→E2→(Airflow run)→verify
```

## Warehouse Tables

| Table | Rows | Schedule | Source |
|---|---|---|---|
| `dim.dim_date` | 2,191 | daily 03:00 | Generated from MSSQL date range |
| `dim.dim_order_channel` | 2 | weekly Mon | MSSQL `OnlineOrderFlag` |
| `dim.dim_sales_territory` | 10 | weekly Mon | MSSQL `SalesTerritory` |
| `dim.dim_delivery_method` | 5 | weekly Mon | MSSQL `ShipMethod` |
| `dim.dim_payment_method` | 5 | weekly Mon | MSSQL `CreditCard` |
| `dim.dim_geography` | 613 | daily 03:00 | MSSQL city-grain surrogate |
| `dim.dim_product` | 504 | daily 03:00 | MSSQL `Product` hierarchy |
| `dim.dim_customer` | 19,820 | daily 04:00 | MSSQL + PG geography FK |
| `fact.fact_online_sales` | 60,398 | hourly | MSSQL + PG payment FK |

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Full reload (TRUNCATE + INSERT) | Simplest for a teaching lab; incremental needs CDC/watermark |
| Surrogate keys via ROW_NUMBER() | No dependency on source auto-increment; stable across reloads |
| `OUTER APPLY TOP 1` for customer address | Deterministic single-address selection per customer |
| `DENSE_RANK()` for CountryKey | Conformed key shared between dim_geography and dim_sales_territory |
| Proportional freight allocation | `delivery_cost = Freight × LineTotal / OrderSubTotal` per line |
| `MSSQLParams` / `PGParams` dataclasses | Typed connection contracts; second DB = new params object, no env changes |

## Components

### `airflow/dags/connections.py`
Shared connection module. `MSSQLParams` and `PGParams` dataclasses hold typed connection parameters. `.from_env()` classmethods read the standard `.env` variables. Pass a different params object to connect to a second database instance.

### `app/main.py`
Operations CLI. Commands: `status` (row counts), `run --all` (direct ETL execution), `export --out DIR` (CSV dump), `airflow-trigger --all` (Airflow scheduler trigger).

### `tools/sql_query/server.py`
Universal MCP server (stdio transport). Exposes `query_sql(connection, sql)` — accepts `"mssql"` or `"postgres"`, returns JSON `list[dict]`. Registered in `.claude/settings.json`.

### `docker/sqlserver/init/restore.sh`
Starts `sqlservr` in background, polls until ready, auto-detects logical file names via `RESTORE FILELISTONLY`, then restores the AdventureWorks database. Idempotent.

## Milestones

| Milestone | Status |
|---|---|
| M1 — Architecture lock | Done — SQL Server + PostgreSQL + Airflow 3.2 standalone |
| M2 — Environment bootstrap | Done — docker-compose, start_airflow.sh |
| M3 — Mapping spec | Done — docs/source_to_target_mapping.md (all 9 tables) |
| M4 — PoC (dim_product) | Done |
| M5 — Phase 2 (all 9 DAGs) | Done — 60k fact rows, 8 dims, schedules set |
| M6 — Modular connections | Done — MSSQLParams/PGParams, ops CLI |
