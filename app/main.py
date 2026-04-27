"""
AdventureWorks ETL — operations CLI.

Usage:
  python app/main.py status
  python app/main.py run --all
  python app/main.py run --dag etl_dim_product
  python app/main.py export [--out scripts/]
  python app/main.py airflow-trigger --all
  python app/main.py airflow-trigger --dag etl_fact_online_sales
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "airflow" / "dags"))

DAG_EXECUTION_ORDER = [
    "etl_dim_date",
    "etl_dim_order_channel",
    "etl_dim_sales_territory",
    "etl_dim_delivery_method",
    "etl_dim_payment_method",
    "etl_dim_geography",
    "etl_dim_product",
    "etl_dim_customer",
    "etl_fact_online_sales",
]

WAREHOUSE_TABLES = [
    ("dim", "dim_date"),
    ("dim", "dim_order_channel"),
    ("dim", "dim_sales_territory"),
    ("dim", "dim_delivery_method"),
    ("dim", "dim_payment_method"),
    ("dim", "dim_geography"),
    ("dim", "dim_product"),
    ("dim", "dim_customer"),
    ("fact", "fact_online_sales"),
]


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        print(f"ERROR: {env_path} not found — copy .env.example and fill in values", file=sys.stderr)
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _pg():
    import psycopg2
    from connections import PGParams, pg_conn
    return pg_conn(PGParams.from_env())


def cmd_status(_args: argparse.Namespace) -> None:
    _load_env()
    conn = _pg()
    try:
        with conn.cursor() as cur:
            print(f"\n{'Table':<30} {'Rows':>8}")
            print("-" * 40)
            for schema, table in WAREHOUSE_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
                count = cur.fetchone()[0]
                print(f"  {schema}.{table:<27} {count:>8,}")
    finally:
        conn.close()
    print()


def cmd_run(args: argparse.Namespace) -> None:
    _load_env()

    dag_ids = DAG_EXECUTION_ORDER if args.all else [args.dag]

    if not args.all and args.dag not in DAG_EXECUTION_ORDER:
        print(f"ERROR: unknown dag '{args.dag}'. Available:", file=sys.stderr)
        for d in DAG_EXECUTION_ORDER:
            print(f"  {d}", file=sys.stderr)
        sys.exit(1)

    for dag_id in dag_ids:
        print(f"\n>>> Running {dag_id} ...")
        mod = __import__(dag_id)
        from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

        class _XCom:
            def __init__(self):
                self._store: dict = {}
            def xcom_push(self, key, value):
                self._store[key] = value
            def xcom_pull(self, task_ids, key):
                return self._store.get(key)

        ti = _XCom()

        if dag_id == "etl_dim_date":
            mod.generate_and_load(ti=ti)
        else:
            mod.extract(ti=ti)
            mod.transform(ti=ti)
            mod.load(ti=ti)

        print(f"    done.")


def cmd_export(args: argparse.Namespace) -> None:
    _load_env()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = _pg()
    try:
        with conn.cursor() as cur:
            for schema, table in WAREHOUSE_TABLES:
                cur.execute(f"SELECT * FROM {schema}.{table} ORDER BY 1")
                path = out_dir / f"{table}.csv"
                with open(path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([d[0] for d in cur.description])
                    writer.writerows(cur.fetchall())
                print(f"  {cur.rowcount:>7,} rows  →  {path}")
    finally:
        conn.close()


def cmd_airflow_trigger(args: argparse.Namespace) -> None:
    print(
        "WARNING: triggers are asynchronous — Airflow may run DAGs in parallel.\n"
        "         For guaranteed sequential execution use: python app/main.py run --all"
    )
    airflow_bin = REPO_ROOT / ".venv" / "bin" / "airflow"
    env = {**os.environ, "AIRFLOW_HOME": str(REPO_ROOT / "airflow")}

    dag_ids = DAG_EXECUTION_ORDER if args.all else [args.dag]
    for dag_id in dag_ids:
        print(f"Triggering {dag_id} ...")
        subprocess.run(
            [str(airflow_bin), "dags", "trigger", dag_id],
            env=env,
            check=True,
            capture_output=True,
        )
        print(f"  queued.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="etl",
        description="AdventureWorks ETL operations CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show row counts for all warehouse tables")

    p_run = sub.add_parser("run", help="Execute ETL DAG(s) directly (no Airflow scheduler)")
    g_run = p_run.add_mutually_exclusive_group(required=True)
    g_run.add_argument("--all", action="store_true", help="Run all DAGs in execution order")
    g_run.add_argument("--dag", metavar="DAG_ID", help="Run a single DAG by ID")

    p_export = sub.add_parser("export", help="Export all warehouse tables to CSV")
    p_export.add_argument("--out", default="scripts/", metavar="DIR", help="Output directory (default: scripts/)")

    p_trigger = sub.add_parser("airflow-trigger", help="Trigger DAG run(s) via the Airflow scheduler")
    g_trigger = p_trigger.add_mutually_exclusive_group(required=True)
    g_trigger.add_argument("--all", action="store_true", help="Trigger all DAGs in execution order")
    g_trigger.add_argument("--dag", metavar="DAG_ID", help="Trigger a single DAG by ID")

    args = parser.parse_args()
    {
        "status":          cmd_status,
        "run":             cmd_run,
        "export":          cmd_export,
        "airflow-trigger": cmd_airflow_trigger,
    }[args.command](args)


if __name__ == "__main__":
    main()
