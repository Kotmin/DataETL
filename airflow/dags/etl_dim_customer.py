from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_customer.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_customer", key="raw_rows")

    pg = pg_conn(PGParams.from_env())
    try:
        with pg.cursor() as cur:
            cur.execute("""
                SELECT city_name, country_code, geography_key
                FROM dim.dim_geography
            """)
            geog_lookup = {
                (row[0].strip().lower(), row[1].strip().lower()): row[2]
                for row in cur.fetchall()
            }
    finally:
        pg.close()

    transformed = []
    for row in raw_rows:
        city = (row.get("City") or "").strip().lower()
        cc   = (row.get("CountryRegionCode") or "").strip().lower()
        geography_key = geog_lookup.get((city, cc)) if city else None
        transformed.append(
            {
                "customer_key":  int(row["CustomerID"]),
                "first_name":    row["FirstName"],
                "last_name":     row["LastName"],
                "geography_key": geography_key,
            }
        )
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_customer", key="transformed_rows")
    conn = pg_conn(PGParams.from_env())
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_customer CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_customer
                    (customer_key, first_name, last_name, geography_key)
                VALUES
                    (%(customer_key)s, %(first_name)s, %(last_name)s, %(geography_key)s)
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
    schedule="0 4 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "customer"],
) as dag:

    extract_task = PythonOperator(task_id="extract_dim_customer", python_callable=extract)
    transform_task = PythonOperator(task_id="transform_dim_customer", python_callable=transform)
    load_task = PythonOperator(task_id="load_dim_customer", python_callable=load)

    extract_task >> transform_task >> load_task
