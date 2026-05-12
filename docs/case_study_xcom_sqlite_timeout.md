# Case Study: Airflow 3.x XCom ReadTimeout with SQLite

**Environment:** Airflow 3.2.0 · standalone mode · LocalExecutor · SQLite metadata DB  
**DAG affected:** `etl_fact_online_sales`

---

## Case

`extract_fact_online_sales` failed consistently after ~73 seconds. The task showed as
**failed** in the UI with no visible application error — no MSSQL connection refused, no
SQL syntax error, no Python traceback inside the task code. All other DAGs ran normally.
The Airflow scheduler, triggerer, and dag_processor were healthy (after unrelated port-
conflict fixes applied earlier in the project).

The failure was reproducible on every manual trigger and on every scheduled run.

---

## How to Diagnose

### 1. Read the scheduler error in `standalone.log`

```bash
grep -i "extract_fact_online_sales\|ReadTimeout\|httpcore" airflow/logs/standalone.log | tail -30
```

Key signal found:

```
httpcore.ReadTimeout: timed out
  ...
  airflow/sdk/execution_time/supervisor.py, line 1868, in cb
  ...
  airflow/executors/local_executor.py, line 144, in _execute_work
      supervise(
```

The timeout fires inside `supervisor.py`, **not** inside task code. That is the
first critical clue — it rules out application bugs in the extract function.

### 2. Read the task log

```bash
find airflow/logs -name "attempt=1.log" -path "*extract_fact*" | sort -r | head -3
```

The task log shows the task started, the SQL query completed, and then the process was
terminated externally — no exception was raised inside the task itself.

### 3. Correlate timing

```
Task start   → ~70s → task terminated externally
              ↑
     where does the time go?
```

SQL execution (measured separately via MSSQL query stats): ~15–20 s.  
Remaining ~50 s: data serialisation + XCom push attempting to write to SQLite.

### 4. Estimate XCom payload size

Add a temporary log before the push to confirm:

```python
import sys
print(f"XCom payload: {sys.getsizeof(rows) / 1024 / 1024:.1f} MB (in-process)")
```

For this project's fact extract — ~60 k rows × 17 columns — the in-process list is
~120 MB. Serialised to JSON it grows further.

---

## Cause

### Airflow 3.x task communication architecture

In Airflow 3.x, tasks run in subprocesses managed by a **supervisor** process inside the
LocalExecutor worker. The supervisor proxies all calls between the task and the Airflow
API server.

```
Task subprocess
      │  UNIX socket
      ▼
Supervisor  (inside LocalExecutor worker)
      │  HTTP  (httpx / httpcore)
      ▼
Airflow API server  (port 8080)
      │  SQLAlchemy
      ▼
SQLite metadata database
```

When the task calls `context["ti"].xcom_push(key="raw_rows", value=rows)`:

1. Task subprocess serialises `rows` to JSON — ~120 MB for this dataset
2. Sends the blob to the supervisor over a UNIX socket
3. Supervisor makes an HTTP `POST /execution/xcoms/…` to the API server
4. API server writes the blob to the `xcom` table in SQLite
5. API server returns HTTP 201 to the supervisor
6. **Timeout fires here** — supervisor's `httpcore` client was waiting for the 201
   response while the API server was still writing the large blob to SQLite

SQLite is single-writer. A large sequential blob write can take 30–60 s on a typical
developer SSD. That exceeds `httpcore`'s default read timeout. The supervisor throws
`ReadTimeout`, the executor marks the task as failed, and the scheduler logs a
state-mismatch error.

**The task code never raises an exception.** The failure is entirely at the
infrastructure layer.

### Why Airflow 2.x didn't surface this

In Airflow 2.x, `xcom_push` wrote directly to the database via SQLAlchemy inside the
task process. The only timeout involved was SQLAlchemy's pool timeout and SQLite's
busy timeout — both configurable and lenient by default. Airflow 3.x's HTTP-mediated
architecture introduced a new, harder timeout surface that makes the XCom-as-data-bus
antipattern fail loudly instead of silently degrading.

### Contributing factors in this project

| Factor | Impact |
|--------|--------|
| SQLite — single-writer, no WAL mode | Any write locks the DB exclusively |
| LocalExecutor default parallelism = 32 | Many concurrent writes amplify lock contention |
| Hourly fact schedule (`0 * * * *`) | Frequent runs kept the DB under constant write pressure |
| Full-table extract, no pagination | Single XCom payload = entire fact dataset |

---

## Solutions

### Solution 1 — Temp-file transport *(implemented)*

Replace large XCom values with **file paths**. Each task writes its output to a
`NamedTemporaryFile` on the local filesystem and pushes only the path (a ~50-character
string) via XCom. The next task reads the file, processes it, and deletes it.

```python
import json, os, tempfile

# ── extract ──────────────────────────────────────────────────────────────────
def extract(**context):
    conn = mssql_conn(MSSQLParams.from_env())
    try:
        cursor = conn.cursor()
        cursor.execute(EXTRACT_SQL)
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="fact_raw_"
    )
    json.dump(rows, tmp, default=str)   # default=str handles Decimal + datetime
    tmp.close()
    context["ti"].xcom_push(key="raw_rows_path", value=tmp.name)

# ── transform ────────────────────────────────────────────────────────────────
def transform(**context):
    raw_path = context["ti"].xcom_pull(
        task_ids="extract_fact_online_sales", key="raw_rows_path"
    )
    with open(raw_path) as f:
        raw_rows = json.load(f)
    os.unlink(raw_path)                 # clean up as soon as data is in memory

    # ... transform logic ...

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="fact_transformed_"
    )
    json.dump(transformed, tmp)
    tmp.close()
    context["ti"].xcom_push(key="transformed_rows_path", value=tmp.name)

# ── load ─────────────────────────────────────────────────────────────────────
def load(**context):
    path = context["ti"].xcom_pull(
        task_ids="transform_fact_online_sales", key="transformed_rows_path"
    )
    with open(path) as f:
        rows = json.load(f)
    os.unlink(path)

    # ... insert into PostgreSQL ...
```

**Serialisation note:** `default=str` converts SQL Server `Decimal` and `datetime`
objects to strings. Downstream code must accept strings — in this project `float(val)`
and `datetime.strptime(val[:10], "%Y-%m-%d")` already handle that.

| | |
|---|---|
| ✓ | E→T→L task graph unchanged — full Airflow UI visibility |
| ✓ | XCom payload is now a 50-char string — no timeout possible |
| ✓ | Works regardless of Airflow database backend |
| ✗ | Files orphaned on disk if a task crashes before `os.unlink` (OS temp cleanup handles these eventually; for production, add a cleanup step or use `try/finally`) |
| ✗ | JSON roundtrip: type fidelity requires `default=str` + lenient parsers downstream |

---

### Solution 2 — PostgreSQL as Airflow metadata database *(proper production fix)*

The root cause is SQLite's write performance. Switching Airflow's metadata DB to
PostgreSQL eliminates the XCom bottleneck — Postgres handles large blobs and concurrent
writes efficiently.

```bash
# 1. Create the database once (Postgres container already running in this project)
docker exec <postgres_container> psql -U warehouse -c "CREATE DATABASE airflow;"

# 2. Replace in both start_airflow.sh and bootstrap.sh
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=\
  "postgresql+psycopg2://${PG_USER}:${PG_PASSWORD}@${PG_HOST}:${PG_PORT}/airflow"
```

| | |
|---|---|
| ✓ | Eliminates the XCom timeout at the root — no workaround needed |
| ✓ | Enables true concurrent writes; scheduler/triggerer never lock each other |
| ✓ | Production-grade; matches real deployment topology |
| ✗ | Requires a dedicated database for Airflow metadata |
| ✗ | More complex bootstrap; credential management for two PG databases |

---

### Solution 3 — Merge E+T+L into a single task

Eliminate XCom entirely. One `PythonOperator` handles extract, transform, and load in
sequence. No data leaves the process boundary.

```python
def etl(**context):
    # ── extract
    conn = mssql_conn(MSSQLParams.from_env())
    try:
        cursor = conn.cursor()
        cursor.execute(EXTRACT_SQL)
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

    # ── transform (in-process, no XCom)
    transformed = [...]

    # ── load
    pg = pg_conn(PGParams.from_env())
    ...
```

| | |
|---|---|
| ✓ | Zero XCom — timeout is structurally impossible |
| ✓ | Simplest implementation |
| ✗ | One task = one failure point; UI doesn't show which stage failed |
| ✗ | Individual stages harder to unit-test in isolation |
| ✗ | Breaks E→T→L convention documented in this project's DAG reference |

---

### Solution 4 — SQLite hardening *(mitigating, not fixing)*

Applied as defence-in-depth alongside Solution 1. These settings do not fix the XCom
HTTP timeout, but they eliminate most other SQLite contention that causes scheduler and
triggerer to go unhealthy under load.

```bash
# Retry for 30 s instead of immediately raising on lock
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///...airflow.db?timeout=30"

# WAL mode: readers never block writers — applied after db migrate
"${VENV}/python" -c "
import sqlite3
c = sqlite3.connect('${REPO_ROOT}/airflow/airflow.db')
c.execute('PRAGMA journal_mode=WAL')
c.close()
"

# Cap parallel task slots to reduce concurrent DB write pressure
export AIRFLOW__CORE__PARALLELISM=8
export AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG=4
```

---

## Thoughts

### XCom is not a data bus

XCom was designed for **small metadata**: row counts, file paths, status flags, run IDs.
The Airflow documentation states its intended use clearly, but nothing in the API
prevents misuse. The practical rule: if the XCom value wouldn't fit comfortably in a
URL, use a different transport (file, object store, shared DB table).

### Airflow 3.x makes the antipattern fail loudly

In Airflow 2.x, the same large XCom would silently degrade — slow writes, occasional
lock errors that retried and mostly succeeded. In Airflow 3.x, the HTTP supervisor layer
adds a hard timeout surface. The failure is now deterministic and reproducible rather
than flaky. In a counterintuitive sense, Airflow 3.x's stricter architecture is more
honest: it surfaces the antipattern as a hard error rather than letting it limp along.

### SQLite is a valid choice for a dev lab

With WAL mode, a 30 s busy timeout, and bounded parallelism, SQLite handles Airflow's
metadata workload comfortably — as long as XCom payloads are small. The combination
"SQLite + temp-file XCom" is practical and durable for a single-machine lab. The real
cost of SQLite is not correctness but throughput: you cannot run more than one writer at
a time, which limits how many tasks can heartbeat simultaneously.

### When to move to PostgreSQL

Upgrade the metadata database when:

- Tasks run on more than one machine (CeleryExecutor / KubernetesExecutor)
- Fact tables exceed ~500 k rows and DAG scheduling latency matters
- You want native large XCom without workarounds
- The project is moving toward a production deployment
