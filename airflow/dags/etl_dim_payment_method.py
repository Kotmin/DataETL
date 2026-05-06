from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_payment_method.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_payment_method", key="raw_rows")
    transformed = [
        {
            "payment_method_key":  int(row["PaymentMethodKey"]),
            "payment_method_name": (row["PaymentMethodName"] or "").strip(),
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_payment_method", key="transformed_rows")
    conn = pg_conn(PGParams.from_env())
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_payment_method CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_payment_method
                    (payment_method_key, payment_method_name)
                VALUES
                    (%(payment_method_key)s, %(payment_method_name)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_payment_method")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_payment_method")
    print(f"Loaded {count} rows into dim.dim_payment_method")


with DAG(
    dag_id="etl_dim_payment_method",
    schedule="0 4 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "payment"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_dim_payment_method",
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id="transform_dim_payment_method",
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id="load_dim_payment_method",
        python_callable=load,
    )

    extract_task >> transform_task >> load_task
