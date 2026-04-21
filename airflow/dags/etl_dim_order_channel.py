from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

_CHANNEL_MAP = {
    1: {"order_channel_key": 1, "channel_name": "Online",   "online_flag": True},
    0: {"order_channel_key": 2, "channel_name": "In-Store", "online_flag": False},
}


def extract(**context):
    conn = mssql_conn(MSSQLParams.from_env())
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
    conn = pg_conn(PGParams.from_env())
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
    schedule="0 2 * * 1",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "channel"],
) as dag:

    extract_task = PythonOperator(task_id="extract_dim_order_channel", python_callable=extract)
    transform_task = PythonOperator(task_id="transform_dim_order_channel", python_callable=transform)
    load_task = PythonOperator(task_id="load_dim_order_channel", python_callable=load)

    extract_task >> transform_task >> load_task
