import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")

conn = psycopg2.connect(
    host=os.environ["PG_HOST"],
    port=os.environ["PG_PORT"],
    dbname=os.environ["PG_DB"],
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
)
try:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM dim.dim_product ORDER BY product_key")
        path = Path(__file__).parent / "dim_product.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([d[0] for d in cur.description])
            writer.writerows(cur.fetchall())
        print(f"Exported {cur.rowcount} rows → {path.name}")
finally:
    conn.close()
