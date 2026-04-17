from __future__ import annotations

import os
from datetime import datetime

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

_ROWS = [
    {"order_channel_key": 1, "channel_name": "Online",   "online_flag": True},
    {"order_channel_key": 2, "channel_name": "In-Store",  "online_flag": False},
]


def _pg_conn():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def load_and_seed(**_):
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
                _ROWS,
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
    PythonOperator(task_id="load_dim_order_channel", python_callable=load_and_seed)
