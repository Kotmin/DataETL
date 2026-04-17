from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pyodbc
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_fact_online_sales.sql").read_text()


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_fact_online_sales", key="raw_rows")

    pg = _pg_conn()
    try:
        with pg.cursor() as cur:
            cur.execute("SELECT payment_method_name, payment_method_key FROM dim.dim_payment_method")
            pm_lookup = {name: key for name, key in cur.fetchall()}
    finally:
        pg.close()

    transformed = []
    for row in raw_rows:
        order_date = row["OrderDate"]
        if isinstance(order_date, str):
            order_date = datetime.strptime(order_date[:10], "%Y-%m-%d").date()
        elif hasattr(order_date, "date"):
            order_date = order_date.date()
        date_key = int(order_date.strftime("%Y%m%d"))

        card_type = row.get("CardType") or "None"
        transformed.append(
            {
                "sales_order_key":     row["SalesOrderKey"],
                "order_date_key":      date_key,
                "customer_key":        row["CustomerID"],
                "product_key":         row["ProductID"],
                "territory_key":       row["TerritoryID"],
                "order_channel_key":   1,
                "payment_method_key":  pm_lookup.get(card_type),
                "geography_key":       row["ShipToAddressID"],
                "delivery_method_key": row["ShipMethodID"],
                "order_qty":           row["OrderQty"],
                "unit_price":          row["UnitPrice"],
                "unit_price_discount": row["UnitPriceDiscount"],
                "line_total":          float(row["LineTotal"]),
                "sub_total":           float(row["SubTotal"]) if row["SubTotal"] is not None else None,
                "tax_amt":             float(row["TaxAmt"]) if row["TaxAmt"] is not None else None,
                "freight":             float(row["Freight"]) if row["Freight"] is not None else None,
                "total_due":           float(row["TotalDue"]) if row["TotalDue"] is not None else None,
            }
        )
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_fact_online_sales", key="transformed_rows")
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE fact.fact_online_sales")
            cur.executemany(
                """
                INSERT INTO fact.fact_online_sales
                    (sales_order_key, order_date_key, customer_key, product_key,
                     territory_key, order_channel_key, payment_method_key,
                     geography_key, delivery_method_key,
                     order_qty, unit_price, unit_price_discount, line_total,
                     sub_total, tax_amt, freight, total_due)
                VALUES
                    (%(sales_order_key)s, %(order_date_key)s, %(customer_key)s,
                     %(product_key)s, %(territory_key)s, %(order_channel_key)s,
                     %(payment_method_key)s, %(geography_key)s, %(delivery_method_key)s,
                     %(order_qty)s, %(unit_price)s, %(unit_price_discount)s,
                     %(line_total)s, %(sub_total)s, %(tax_amt)s,
                     %(freight)s, %(total_due)s)
                """,
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM fact.fact_online_sales")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if count == 0:
        raise ValueError("Load produced 0 rows in fact.fact_online_sales")
    print(f"Loaded {count} rows into fact.fact_online_sales")


with DAG(
    dag_id="etl_fact_online_sales",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["fact", "sales"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_fact_online_sales",
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id="transform_fact_online_sales",
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id="load_fact_online_sales",
        python_callable=load,
    )

    extract_task >> transform_task >> load_task
