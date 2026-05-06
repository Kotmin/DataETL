from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

REPO_ROOT = Path(__file__).parents[2]
EXTRACT_SQL = (REPO_ROOT / "sql" / "source" / "extract_fact_online_sales.sql").read_text()


def _payment_method_run_dt(dt):
    return dt.replace(hour=4, minute=0, second=0, microsecond=0)


def _to_date_key(val):
    if val is None:
        return None
    if isinstance(val, str):
        val = datetime.strptime(val[:10], "%Y-%m-%d").date()
    elif hasattr(val, "date"):
        val = val.date()
    return int(val.strftime("%Y%m%d"))


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
    raw_rows = context["ti"].xcom_pull(task_ids="extract_fact_online_sales", key="raw_rows")

    pg = pg_conn(PGParams.from_env())
    try:
        with pg.cursor() as cur:
            cur.execute("SELECT payment_method_name, payment_method_key FROM dim.dim_payment_method")
            pm_lookup = {name: key for name, key in cur.fetchall()}
    finally:
        pg.close()

    order_subtotal: dict[str, float] = defaultdict(float)
    for row in raw_rows:
        order_subtotal[row["OrderKey"]] += float(row["LineTotal"] or 0)

    transformed = []
    for row in raw_rows:
        unit_price     = float(row["UnitPrice"] or 0)
        discount_frac  = float(row["UnitPriceDiscount"] or 0)
        line_total     = float(row["LineTotal"] or 0)
        freight        = float(row["Freight"] or 0)
        sub_total      = order_subtotal[row["OrderKey"]]

        discount_amount   = round(unit_price * discount_frac, 2)
        discount_pctg     = round(discount_frac * 100)
        transaction_price = round(unit_price * (1 - discount_frac), 2)
        delivery_cost     = round(freight * line_total / sub_total, 2) if sub_total > 0 else round(freight, 2)

        card_type = row.get("CardType") or "None"
        transformed.append(
            {
                "order_key":           str(row["OrderKey"]),
                "order_line_number":   int(row["OrderLineNumber"]),
                "customer_key":        int(row["CustomerID"]) if row["CustomerID"] is not None else None,
                "product_key":         int(row["ProductID"]),
                "sales_territory_key": int(row["TerritoryID"]) if row["TerritoryID"] is not None else None,
                "channel_key":         1,
                "payment_method_key":  pm_lookup.get(card_type),
                "delivery_method_key": int(row["ShipMethodID"]) if row["ShipMethodID"] is not None else None,
                "order_date_key":      _to_date_key(row["OrderDate"]),
                "ship_date_key":       _to_date_key(row["ShipDate"]),
                "quantity":            int(row["OrderQty"]),
                "catalog_price":       round(unit_price, 2),
                "discount_amount":     discount_amount,
                "discount_pctg":       discount_pctg,
                "transaction_price":   transaction_price,
                "delivery_cost":       delivery_cost,
                "product_cost":        round(float(row["ProductCost"] or 0), 2),
            }
        )
    context["ti"].xcom_push(key="transformed_rows", value=transformed)


def load(**context):
    rows = context["ti"].xcom_pull(task_ids="transform_fact_online_sales", key="transformed_rows")
    conn = pg_conn(PGParams.from_env())
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE fact.fact_online_sales")
            cur.executemany(
                """
                INSERT INTO fact.fact_online_sales
                    (order_key, order_line_number, customer_key, product_key,
                     sales_territory_key, channel_key, payment_method_key,
                     delivery_method_key, order_date_key, ship_date_key,
                     quantity, catalog_price, discount_amount, discount_pctg,
                     transaction_price, delivery_cost, product_cost)
                VALUES
                    (%(order_key)s, %(order_line_number)s, %(customer_key)s,
                     %(product_key)s, %(sales_territory_key)s, %(channel_key)s,
                     %(payment_method_key)s, %(delivery_method_key)s,
                     %(order_date_key)s, %(ship_date_key)s,
                     %(quantity)s, %(catalog_price)s, %(discount_amount)s,
                     %(discount_pctg)s, %(transaction_price)s,
                     %(delivery_cost)s, %(product_cost)s)
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
    schedule="0 4 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["fact", "sales"],
) as dag:

    wait_for_payment_method = ExternalTaskSensor(
        task_id="wait_for_dim_payment_method",
        external_dag_id="etl_dim_payment_method",
        external_task_id="load_dim_payment_method",
        execution_date_fn=_payment_method_run_dt,
        mode="reschedule",
        poke_interval=60,
        timeout=3600,
    )

    extract_task = PythonOperator(task_id="extract_fact_online_sales", python_callable=extract)
    transform_task = PythonOperator(task_id="transform_fact_online_sales", python_callable=transform)
    load_task = PythonOperator(task_id="load_fact_online_sales", python_callable=load)

    wait_for_payment_method >> extract_task >> transform_task >> load_task
