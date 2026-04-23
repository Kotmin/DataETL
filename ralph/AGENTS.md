# AGENTS.md — AdventureWorks ETL Teaching Lab

Operational guide for autonomous agents. Keep concise. Update Learnings as you discover things.

## Project Layout

```
DataETL/
  docker/           Docker Compose + init scripts
  airflow/dags/     Airflow DAG definitions
  sql/              Source extract, warehouse DDL, transform SQL
  tools/sql_query/  Universal SQL MCP server (pyodbc + psycopg2)
  tests/            pytest suite (unit + integration)
  scripts/          bootstrap.sh, start_airflow.sh, reset_env.sh
  docs/             Mapping specs, execution plan, restore guide
  ralph/            This tool
  .venv/            Python 3.12 venv (gitignored)
```

## Build & Validate

- **test**: `.venv/bin/pytest tests/ -v`
- **unit only**: `.venv/bin/pytest tests/test_transform.py -v`
- **integration**: `.venv/bin/pytest tests/ -v -m integration`
- **build check**: `docker compose -f docker/docker-compose.yml ps`
- **dev**: `./scripts/start_airflow.sh`

## Environment

- Python venv at `.venv/` — always use `.venv/bin/python` and `.venv/bin/pip`
- Docker containers: `sqlserver` (port 1433) and `postgres` (port 5432)
- Airflow: local install in venv, SQLite backend, webserver at http://localhost:8080
- Env vars sourced from `.env` (copy of `.env.example`)
- ODBC driver required: `ODBC Driver 18 for SQL Server` via `msodbcsql18` apt package

## Commit Format

Conventional commits only:
```
feat(scope): description
fix(scope): description
chore(scope): description
docs: description
test: description
refactor(scope): description
```

Scopes: `docker`, `airflow`, `sql`, `mcp`, `tests`, `scripts`, `docs`, `agents`

Rules:
- No AI/Claude mentions in commits or trailers
- One commit = one atomic, logically coherent change
- Branch: always work on `dev`, never push directly to `main`

## Tracking Files (inside worktree at `.ralph_tracking/`)

- `PRD.md` — checkbox source of truth. Mark `[x]` when done.
- `progress.txt` — append-only log: what changed, what's next, blockers.
- `state.json` — machine state. Set `status = "NEEDS_CLARIFICATION"` + write to `questions.md` if blocked.

## Agent Roles

**branch-master**: Manages git hygiene on `dev` branch. Groups uncommitted changes into atomic conventional commits. Never pushes to `main`.

**hypervisor**: Checks environment health — Docker container status, Airflow process status, stale ralph-loop state files. Reports only, no auto-restart.

## Learnings

- SQL Server .bak uses logical file names `AdventureWorks2017` and `AdventureWorks2017_log` — verify with RESTORE FILELISTONLY before hardcoding
- DimProduct extract returns ~504 rows from AdventureWorks OLTP
- XCom approach is safe for this row count (well under 48KB default limit)
- test_load.py tests require a completed Airflow DAG run before they pass
