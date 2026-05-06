from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_dim_geography.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_dim_geography", key="raw_rows")
    transformed = [
        {
            "geography_key":       int(row["GeographyKey"]),
            "country_key":         int(row["CountryKey"]),
            "country_name":        (row["CountryName"] or "").strip(),
            "country_code":        (row["CountryCode"] or "").strip(),
            "city_key":            int(row["CityKey"]),
            "city_name":           (row["CityName"] or "").strip(),
            "sales_territory_key": int(row["SalesTerritoryKey"]) if row["SalesTerritoryKey"] is not None else None,
        }
        for row in raw_rows
    ]
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_dim_geography", key="transformed_rows")
    conn = pg_conn(PGParams.from_env())
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_geography CASCADE")
            cur.executemany(
                """
                INSERT INTO dim.dim_geography
                    (geography_key, country_key, country_name, country_code,
                     city_key, city_name, sales_territory_key)
                VALUES
                    (%(geography_key)s, %(country_key)s, %(country_name)s,
                     %(country_code)s, %(city_key)s, %(city_name)s,
                     %(sales_territory_key)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_geography")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in dim.dim_geography")
    print(f"Loaded {count} rows into dim.dim_geography")


with DAG(
    dag_id="etl_dim_geography",
    schedule="0 3 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "geography"],
) as dag:

    extract_task = PythonOperator(task_id="extract_dim_geography", python_callable=extract)
    transform_task = PythonOperator(task_id="transform_dim_geography", python_callable=transform)
    load_task = PythonOperator(task_id="load_dim_geography", python_callable=load)

    extract_task >> transform_task >> load_task
