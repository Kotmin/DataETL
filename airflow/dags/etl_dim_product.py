from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pyodbc
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_product.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_product", key="raw_rows")
    transformed = [
        {
            "product_key": row["ProductID"],
            "product_code": (row["ProductNumber"] or "").strip(),
            "product_name": (row["ProductName"] or "").strip(),
            "subcategory_key": row["ProductSubcategoryID"],
            "subcategory_name": row["SubcategoryName"],
            "category_key": row["ProductCategoryID"],
            "category_name": row["CategoryName"],
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_product", key="transformed_rows")
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_product")
            cur.executemany(
                """
                INSERT INTO dim.dim_product
                    (product_key, product_code, product_name,
                     subcategory_key, subcategory_name, category_key, category_name)
                VALUES
                    (%(product_key)s, %(product_code)s, %(product_name)s,
                     %(subcategory_key)s, %(subcategory_name)s, %(category_key)s, %(category_name)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_product")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_product")
    print(f"Loaded {count} rows into dim.dim_product")


with DAG(
    dag_id="etl_dim_product",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "product", "poc"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_dim_product",
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id="transform_dim_product",
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id="load_dim_product",
        python_callable=load,
    )

    extract_task >> transform_task >> load_task
