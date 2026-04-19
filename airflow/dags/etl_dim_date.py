from __future__ import annotations

from datetime import date, datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from connections import MSSQLParams, PGParams, mssql_conn, pg_conn

_MONTH_NAMES = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
_DAY_NAMES   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def generate_and_load(**_):
    conn = mssql_conn(MSSQLParams.from_env())
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(OrderDate), MAX(ISNULL(ShipDate, OrderDate))
            FROM Sales.SalesOrderHeader
            WHERE OnlineOrderFlag = 1
        """)
        min_date, max_date = cursor.fetchone()
    finally:
        conn.close()

    start = (min_date.date() if hasattr(min_date, "date") else min_date).replace(year=min_date.year - 1, month=1, day=1)
    end   = (max_date.date() if hasattr(max_date, "date") else max_date).replace(year=max_date.year + 1, month=12, day=31)

    rows = []
    current = start
    while current <= end:
        rows.append({
            "date_key":             int(current.strftime("%Y%m%d")),
            "full_date":            current,
            "calendar_year":        current.year,
            "calendar_quarter":     (current.month - 1) // 3 + 1,
            "month_number_of_year": current.month,
            "month_name":           _MONTH_NAMES[current.month - 1],
            "week_number_of_year":  int(current.strftime("%W")),
            "day_number_of_year":   current.timetuple().tm_yday,
            "day_number_of_month":  current.day,
            "day_number_of_week":   current.weekday() + 1,
            "day_name_of_week":     _DAY_NAMES[current.weekday()],
            "is_weekend":           current.weekday() >= 5,
        })
        current += timedelta(days=1)

    pg = pg_conn(PGParams.from_env())
    try:
        with pg.cursor() as cur:
            cur.execute("TRUNCATE TABLE dim.dim_date")
            cur.executemany(
                """INSERT INTO dim.dim_date VALUES
                   (%(date_key)s,%(full_date)s,%(calendar_year)s,%(calendar_quarter)s,
                    %(month_number_of_year)s,%(month_name)s,%(week_number_of_year)s,
                    %(day_number_of_year)s,%(day_number_of_month)s,%(day_number_of_week)s,
                    %(day_name_of_week)s,%(is_weekend)s)""",
                rows,
            )
            cur.execute("SELECT COUNT(*) FROM dim.dim_date")
            count = cur.fetchone()[0]
        pg.commit()
    finally:
        pg.close()
    print(f"Loaded {count} rows into dim.dim_date (range {start} to {end})")


with DAG(
    dag_id="etl_dim_date",
    schedule="0 3 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["dim", "date"],
) as dag:
    PythonOperator(task_id="load_dim_date", python_callable=generate_and_load)
