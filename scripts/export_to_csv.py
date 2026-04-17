import psycopg2
import csv

conn = psycopg2.connect("postgresql://warehouse:warehouse@localhost:5432/warehouse")
cur = conn.cursor()
cur.execute("SELECT * FROM dim.dim_product ORDER BY product_key")
with open("dim_product.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([d[0] for d in cur.description])
    writer.writerows(cur.fetchall())
conn.close()