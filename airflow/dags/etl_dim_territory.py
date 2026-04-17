from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pyodbc
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_territory.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_territory", key="raw_rows")
    transformed = [
        {
            "territory_key": row["TerritoryID"],
            "territory_name": (row["TerritoryName"] or "").strip(),
            "country_region_code": (row["CountryRegionCode"] or "").strip(),
            "region_group": (row["RegionGroup"] or "").strip(),
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_territory", key="transformed_rows")
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_territory CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_territory
                    (territory_key, territory_name, country_region_code, region_group)
                VALUES
                    (%(territory_key)s, %(territory_name)s,
                     %(country_region_code)s, %(region_group)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_territory")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_territory")
    print(f"Loaded {count} rows into dim.dim_territory")


with DAG(
    dag_id="etl_dim_territory",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "territory"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_dim_territory",
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id="transform_dim_territory",
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id="load_dim_territory",
        python_callable=load,
    )

    extract_task >> transform_task >> load_task
