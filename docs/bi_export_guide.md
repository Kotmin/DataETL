# BI Export Guide — AdventureWorks Warehouse

How to connect the warehouse (`dim` + `fact` schemas) in the local PostgreSQL instance to common BI and data tools.

## Connection Details

| Parameter | Value (from `.env`) |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `warehouse` |
| User | `warehouse` |
| Password | `warehouse` |

### Available Tables

| Schema | Table | Rows (approx.) |
|---|---|---|
| `dim` | `dim_date` | 2,191 |
| `dim` | `dim_order_channel` | 2 |
| `dim` | `dim_sales_territory` | 10 |
| `dim` | `dim_delivery_method` | 5 |
| `dim` | `dim_payment_method` | 5 |
| `dim` | `dim_geography` | 613 |
| `dim` | `dim_product` | 504 |
| `dim` | `dim_customer` | 19,820 |
| `fact` | `fact_online_sales` | 60,398 |

---

## Quickstart

**Check current row counts:**
```bash
.venv/bin/python app/main.py status
```

**Export all tables to CSV:**
```bash
.venv/bin/python app/main.py export --out exports/
```

**Run all ETL DAGs directly (no Airflow scheduler required):**
```bash
.venv/bin/python app/main.py run --all
```

---

## Power BI Desktop

**Prerequisites:** Power BI Desktop ships with a built-in Npgsql driver (December 2019+). No separate driver install needed.

**Steps:**
1. Get Data → Database → **PostgreSQL database**
2. Server: `localhost`, Database: `warehouse`
3. Enter credentials: user `warehouse`, password `warehouse`
4. Browse the `dim` and `fact` schemas → select tables → Load
5. Create relationships: all dim keys → `fact_online_sales` foreign keys
6. Build visuals or use Power Query for transforms

**Suggested star schema joins in Power BI:**

| Fact column | Dimension table | Key |
|---|---|---|
| `order_date_key` | `dim_date` | `date_key` |
| `customer_key` | `dim_customer` | `customer_key` |
| `product_key` | `dim_product` | `product_key` |
| `sales_territory_key` | `dim_sales_territory` | `sales_territory_key` |
| `channel_key` | `dim_order_channel` | `order_channel_key` |
| `payment_method_key` | `dim_payment_method` | `payment_method_key` |
| `delivery_method_key` | `dim_delivery_method` | `delivery_method_key` |

**Note:** For Power BI Service (cloud), you need an on-premises data gateway to reach `localhost`.

---

## Tableau Desktop / Tableau Public

**Prerequisites:** Download the PostgreSQL driver from `tableau.com/support/drivers`.

**Steps:**
1. Connect → To a Server → **PostgreSQL**
2. Server: `localhost`, Port: `5432`
3. Database: `warehouse`, Authentication: Username + Password
4. Username: `warehouse`, Password: `warehouse`
5. Drag tables from `dim` and `fact` schemas to the canvas
6. Define joins on matching key columns (see star schema table above)

---

## Databricks

**Use case:** reading the warehouse into a Spark DataFrame for further processing or comparison labs.

**Python / PySpark (JDBC):**
```python
def read_table(schema: str, table: str):
    return (
        spark.read
        .format("jdbc")
        .option("url", "jdbc:postgresql://localhost:5432/warehouse")
        .option("dbtable", f"{schema}.{table}")
        .option("user", "warehouse")
        .option("password", "warehouse")
        .option("driver", "org.postgresql.Driver")
        .load()
    )

fact   = read_table("fact", "fact_online_sales")
dim_dt = read_table("dim",  "dim_date")
dim_cu = read_table("dim",  "dim_customer")
```

**Note:** `localhost` only works when Databricks and PostgreSQL are on the same network. For remote Databricks, expose the warehouse via a tunnel or use a cloud-hosted PostgreSQL.

---

## Raw CSV Export

**Option A — CLI (all 9 tables at once):**
```bash
.venv/bin/python app/main.py export --out exports/
```

**Option B — psql client (single table):**
```bash
psql -h localhost -U warehouse -d warehouse \
  -c "\copy (SELECT * FROM fact.fact_online_sales) TO 'fact_online_sales.csv' CSV HEADER"
```

**Option C — server-side COPY (requires superuser or pg_write_server_files):**
```sql
COPY fact.fact_online_sales TO '/tmp/fact_online_sales.csv' DELIMITER ',' CSV HEADER;
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

**Connect (Metabase UI → Settings → Databases → Add):**
- Database type: **PostgreSQL**
- Host: `postgres` (Docker service name, same network) or `localhost` (host network)
- Port: `5432`, Database: `warehouse`
- Username: `warehouse`, Password: `warehouse`

Access at `http://localhost:3000`.

---

## Apache Superset (Docker)

**SQLAlchemy connection string:**
```
postgresql+psycopg2://warehouse:warehouse@localhost:5432/warehouse
```

**Add in Superset UI:** Settings → Database Connections → + Database → PostgreSQL → paste string → Test Connection → Save.

---

## DBeaver

1. File → New → Database Connection → **PostgreSQL**
2. Host: `localhost`, Port: `5432`, Database: `warehouse`
3. Username: `warehouse`, Password: `warehouse`
4. Test Connection → Finish

**Export to CSV:** Right-click any table → Export Data → Format: CSV → configure header and delimiter → Finish.

---

## pgAdmin

**Add server:** Right-click Servers → Register → Server
- General: Name = `Warehouse`
- Connection: Host `localhost`, Port `5432`, Database `warehouse`, Username `warehouse`

**Export to CSV:** Right-click table → Import/Export Data → Export → Format: CSV → Header: Yes → choose path → OK.

---

## Summary

| Tool | Setup effort | Notes |
|---|---|---|
| `app/main.py export` | None | Fastest — exports all 9 tables at once |
| Power BI | Low | No driver install; needs manual star schema joins |
| Tableau | Low | PostgreSQL driver download required |
| Databricks | Medium | JDBC; requires network access to `localhost` |
| Metabase | Docker + UI | Free BI browser UI, good for dashboards |
| Superset | Docker + UI | SQLAlchemy connection string |
| DBeaver | GUI wizard | Best for ad-hoc SQL exploration |
| pgAdmin | GUI | Built-in with most PostgreSQL setups |
