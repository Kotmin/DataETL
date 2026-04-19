from __future__ import annotations

import os
from datetime import datetime

import pyodbc
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

_CHANNEL_MAP = {
    1: {"order_channel_key": 1, "channel_name": "Online",   "online_flag": True},
    0: {"order_channel_key": 2, "channel_name": "In-Store", "online_flag": False},
}


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
        host=os.environ["PG_HOST"], port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DB"], user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def extract(**context):
    conn = _mssql_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT OnlineOrderFlag FROM Sales.SalesOrderHeader")
        flags = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
    context["ti"].xcom_push(key="flags", value=flags)


def transform(**context):
    flags = context["ti"].xcom_pull(task_ids="extract_dim_order_channel", key="flags")
    rows = [_CHANNEL_MAP[int(f)] for f in flags if int(f) in _CHANNEL_MAP]
    context["ti"].xcom_push(key="transformed_rows", value=rows)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_order_channel", key="transformed_rows")
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_order_channel CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_order_channel
                    (order_channel_key, channel_name, online_flag)
                VALUES
                    (%(order_channel_key)s, %(channel_name)s, %(online_flag)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_order_channel")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    print(f"Loaded {count} rows into dim.dim_order_channel")


with DAG(
    dag_id="etl_dim_order_channel",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "channel"],
) as dag:

    extract_task = PythonOperator(task_id="extract_dim_order_channel", python_callable=extract)
    transform_task = PythonOperator(task_id="transform_dim_order_channel", python_callable=transform)
    load_task = PythonOperator(task_id="load_dim_order_channel", python_callable=load)

    extract_task >> transform_task >> load_task
