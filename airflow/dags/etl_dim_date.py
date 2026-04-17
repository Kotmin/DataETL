from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

CALENDAR_START = date(2022, 1, 1)
CALENDAR_END   = date(2026, 12, 31)

_MONTH_NAMES = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
_DAY_NAMES   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def _pg_conn():
    return psycopg2.connect(
        host=os.environ["PG_HOST"], port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DB"], user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )


def generate_and_load(**_):
    rows = []
    current = CALENDAR_START
    while current <= CALENDAR_END:
        rows.append({
            "date_key":     int(current.strftime("%Y%m%d")),
            "full_date":    current,
            "year":         current.year,
            "quarter":      (current.month - 1) // 3 + 1,
            "month":        current.month,
            "month_name":   _MONTH_NAMES[current.month - 1],
            "week_of_year": int(current.strftime("%W")),
            "day_of_month": current.day,
            "day_of_week":  current.weekday() + 1,
            "day_name":     _DAY_NAMES[current.weekday()],
            "is_weekend":   current.weekday() >= 5,
        })
        current += timedelta(days=1)

    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_date")
            cur.executemany(
                """INSERT INTO dim.dim_date VALUES
                   (%(date_key)s,%(full_date)s,%(year)s,%(quarter)s,%(month)s,
                    %(month_name)s,%(week_of_year)s,%(day_of_month)s,%(day_of_week)s,
                    %(day_name)s,%(is_weekend)s)""",
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_date")
            count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    print(f"Loaded {count} rows into dim.dim_date")


with DAG(
    dag_id="etl_dim_date",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "date"],
) as dag:
    PythonOperator(task_id="load_dim_date", python_callable=generate_and_load)
