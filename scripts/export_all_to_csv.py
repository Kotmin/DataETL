import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")

TABLES = [
    ("dim", "dim_date"),
    ("dim", "dim_order_channel"),
    ("dim", "dim_sales_territory"),
    ("dim", "dim_delivery_method"),
    ("dim", "dim_payment_method"),
    ("dim", "dim_geography"),
    ("dim", "dim_product"),
    ("dim", "dim_customer"),
    ("fact", "fact_online_sales"),
]

conn = psycopg2.connect(
    host=os.environ["PG_HOST"],
    port=os.environ["PG_PORT"],
    dbname=os.environ["PG_DB"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
)

out_dir = Path(__file__).parent
try:
    with conn.cursor() as cur:
        for schema, table in TABLES:
            cur.execute(f"SELECT * FROM {schema}.{table} ORDER BY 1")
            path = out_dir / f"{table}.csv"
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([d[0] for d in cur.description])
                writer.writerows(cur.fetchall())
            print(f"Exported {cur.rowcount} rows → {path.name}")
finally:
    conn.close()
