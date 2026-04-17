# BI Export Guide — AdventureWorks Warehouse

How to connect the `dim` schema in the PostgreSQL warehouse to common BI and data tools.

## Connection Details

| Parameter | Value (default from `.env`) |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `warehouse` |
| User | `warehouse` |
| Password | `warehouse` |
| Target table | `dim.dim_product` |

---

## Power BI Desktop

**Prerequisites:** Power BI Desktop ships with a built-in Npgsql driver (December 2019+). No separate driver install needed.

**Steps:**
1. Get Data → Database → **PostgreSQL database**
2. Server: `localhost`, Database: `warehouse`
3. Enter credentials: user `warehouse`, password `warehouse`
4. Select `dim` → `dim_product` → Load
5. Build visuals directly or use Power Query for transforms

**Note:** For Power BI Service (cloud), you need an on-premises data gateway to reach `localhost`.

---

## Tableau Desktop / Tableau Public

**Prerequisites:** Download the PostgreSQL driver from `tableau.com/support/drivers`.

**Steps:**
1. Connect → To a Server → **PostgreSQL**
2. Server: `localhost`, Port: `5432`
3. Database: `warehouse`, Authentication: Username + Password
4. Username: `warehouse`, Password: `warehouse`
5. Drag `dim_product` (under schema `dim`) to the canvas

---

## Databricks

**Use case:** reading the warehouse into a Spark DataFrame for further processing or comparison labs.

**Python / PySpark (JDBC):**
```python
df = (
    spark.read
    .format("jdbc")
    .option("url", "jdbc:postgresql://localhost:5432/warehouse")
    .option("dbtable", "dim.dim_product")
    .option("user", "warehouse")
    .option("password", "warehouse")
    .option("driver", "org.postgresql.Driver")
    .load()
)
df.show()
```

**Databricks named connector (Runtime 11.3+):**
```python
df = spark.read.postgresql(
    host="localhost", port=5432,
    database="warehouse", table="dim.dim_product",
    user="warehouse", password="warehouse"
)
```

**Note:** `localhost` only works when Databricks and PostgreSQL are on the same network. For remote Databricks, expose the warehouse via a tunnel or use a cloud-hosted PostgreSQL.

---

## Raw CSV Export

**Option A — psql client (no superuser needed):**
```bash
psql -h localhost -U warehouse -d warehouse \
  -c "\copy (SELECT * FROM dim.dim_product) TO 'dim_product.csv' CSV HEADER"
```

**Option B — Python (use inside the venv):**
```python
import psycopg2, csv

conn = psycopg2.connect("postgresql://warehouse:warehouse@localhost:5432/warehouse")
cur = conn.cursor()
cur.execute("SELECT * FROM dim.dim_product ORDER BY product_key")
with open("dim_product.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([d[0] for d in cur.description])
    writer.writerows(cur.fetchall())
conn.close()
```

**Option C — server-side COPY (requires superuser or pg_write_server_files):**
```sql
COPY dim.dim_product TO '/tmp/dim_product.csv' DELIMITER ',' CSV HEADER;
```

---

## Metabase (Docker)

**Run Metabase alongside the warehouse:**
```bash
docker run -d --name metabase \
  --network docker_default \
  -p 3000:3000 \
  metabase/metabase
```

**Connect to the warehouse (in Metabase UI → Settings → Databases → Add):**
- Database type: **PostgreSQL**
- Host: `postgres` (Docker service name if on same network) or `localhost` if on host
- Port: `5432`
- Database name: `warehouse`
- Username: `warehouse`, Password: `warehouse`

Access Metabase at `http://localhost:3000`.

---

## Apache Superset (Docker)

**SQLAlchemy connection string:**
```
postgresql+psycopg2://warehouse:warehouse@localhost:5432/warehouse
```

**Add in Superset UI:** Settings → Database Connections → + Database → PostgreSQL → paste string → Test Connection → Save.

**Quick Docker run:**
```bash
docker run -d --name superset -p 8088:8088 apache/superset
# then follow Superset quickstart to configure admin and add the connection
```

---

## DBeaver

**New connection:**
1. File → New → Database Connection → **PostgreSQL**
2. Host: `localhost`, Port: `5432`, Database: `warehouse`
3. Username: `warehouse`, Password: `warehouse`
4. Test Connection → Finish

**Export to CSV:**
Right-click `dim_product` → Export Data → Format: CSV → configure header and delimiter → Finish.

---

## pgAdmin

**Add server:** Right-click Servers → Register → Server
- General: Name = `Warehouse`
- Connection: Host `localhost`, Port `5432`, Database `warehouse`, Username `warehouse`

**Export table to CSV:**
Right-click `dim_product` → Import/Export Data → toggle to **Export** → Format: CSV → Header: Yes → choose output path → OK.

---

## Summary

| Tool | Setup effort | Auth needed | Notes |
|---|---|---|---|
| Power BI | Low | UI login | No driver install needed |
| Tableau | Low | UI login | PostgreSQL driver download required |
| Databricks | Medium | Notebook config | JDBC; `localhost` requires network access |
| Raw CSV | None | CLI | Fastest for one-off exports |
| Metabase | Docker + UI | Browser setup | Full BI browser UI, free |
| Superset | Docker + UI | Browser setup | SQLAlchemy connection string |
| DBeaver | GUI wizard | DB credentials | Best for ad-hoc SQL + export |
| pgAdmin | GUI | DB credentials | Built into most PostgreSQL setups |
