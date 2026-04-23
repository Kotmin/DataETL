from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_delivery_method.sql").read_text()


def extract(**context):
    conn = mssql_conn(MSSQLParams.from_env())
    try:
        cursor = conn.cursor()
        cursor.execute(EXTRACT_SQL)
        columns = [d[0] for d in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()
    context["ti"].xcom_push(key="raw_rows", value=rows)


def transform(**context):
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_delivery_method", key="raw_rows")
    transformed = [
        {
            "delivery_method_key":  row["DeliveryMethodKey"],
            "delivery_method_name": (row["DeliveryMethodName"] or "").strip(),
            "ship_base":            float(row["ShipBase"]) if row["ShipBase"] is not None else None,
            "ship_rate":            float(row["ShipRate"]) if row["ShipRate"] is not None else None,
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_delivery_method", key="transformed_rows")
    conn = pg_conn(PGParams.from_env())
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_delivery_method CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_delivery_method
                    (delivery_method_key, delivery_method_name, ship_base, ship_rate)
                VALUES
                    (%(delivery_method_key)s, %(delivery_method_name)s,
                     %(ship_base)s, %(ship_rate)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_delivery_method")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_delivery_method")
    print(f"Loaded {count} rows into dim.dim_delivery_method")


with DAG(
    dag_id="etl_dim_delivery_method",
    schedule="0 2 * * 1",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "delivery"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_dim_delivery_method",
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id="transform_dim_delivery_method",
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id="load_dim_delivery_method",
        python_callable=load,
    )

    extract_task >> transform_task >> load_task
