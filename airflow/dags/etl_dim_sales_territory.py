from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from connections import mssql_conn as _mssql_conn, pg_conn as _pg_conn

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_sales_territory.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_sales_territory", key="raw_rows")
    transformed = [
        {
            "sales_territory_key":  int(row["SalesTerritoryKey"]),
            "sales_territory_name": (row["SalesTerritoryName"] or "").strip(),
            "country_key":          int(row["CountryKey"]),
            "country_name":         (row["CountryName"] or "").strip(),
            "country_code":         (row["CountryCode"] or "").strip(),
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_sales_territory", key="transformed_rows")
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_sales_territory CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_sales_territory
                    (sales_territory_key, sales_territory_name,
                     country_key, country_name, country_code)
                VALUES
                    (%(sales_territory_key)s, %(sales_territory_name)s,
                     %(country_key)s, %(country_name)s, %(country_code)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_sales_territory")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_sales_territory")
    print(f"Loaded {count} rows into dim.dim_sales_territory")


with DAG(
    dag_id="etl_dim_sales_territory",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "territory"],
) as dag:

    extract_task = PythonOperator(task_id="extract_dim_sales_territory", python_callable=extract)
    transform_task = PythonOperator(task_id="transform_dim_sales_territory", python_callable=transform)
    load_task = PythonOperator(task_id="load_dim_sales_territory", python_callable=load)

    extract_task >> transform_task >> load_task
