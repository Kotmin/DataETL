from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pyodbc
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_customer.sql").read_text()


def _mssql_conn():
    dsn = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.environ['MSSQL_HOST']},{os.environ['MSSQL_PORT']};"
        f"DATABASE={os.environ['MSSQL_DB']};"
        f"UID=sa;PWD={os.environ['MSSQL_SA_PASSWORD']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(dsn)


def _pg_conn():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def extract(**context):
    conn = _mssql_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(EXTRACT_SQL)
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()
    context["ti"].xcom_push(key="raw_rows", value=rows)


def transform(**context):
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_customer", key="raw_rows")
    transformed = [
        {
            "customer_key": row["CustomerID"],
            "account_number": (row["AccountNumber"] or "").strip(),
            "first_name": row["FirstName"],
            "last_name": row["LastName"],
            "full_name": row["FullName"],
            "territory_key": row["TerritoryID"],
            "territory_name": row["TerritoryName"],
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_customer", key="transformed_rows")
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_customer CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_customer
                    (customer_key, account_number, first_name, last_name,
                     full_name, territory_key, territory_name)
                VALUES
                    (%(customer_key)s, %(account_number)s, %(first_name)s,
                     %(last_name)s, %(full_name)s, %(territory_key)s, %(territory_name)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_customer")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_customer")
    print(f"Loaded {count} rows into dim.dim_customer")


with DAG(
    dag_id="etl_dim_customer",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "customer"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_dim_customer",
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id="transform_dim_customer",
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id="load_dim_customer",
        python_callable=load,
    )

    extract_task >> transform_task >> load_task
