# DAG Reference

This document is the canonical catalog of all Airflow DAGs in this project.
**Keep it updated** when adding, removing, or changing a DAG.

---

## Execution Order

Run dimensions before the fact. Suggested sequence:

```
1. etl_dim_date            (no source DB — safe to run anytime)
2. etl_dim_order_channel   (no source DB — seeded)
3. etl_dim_territory       (MSSQL)
4. etl_dim_delivery_method (MSSQL)
5. etl_dim_payment_method  (MSSQL) ← must run before etl_fact_online_sales
6. etl_dim_geography       (MSSQL) ← must run before etl_fact_online_sales
7. etl_dim_product         (MSSQL)
8. etl_dim_customer        (MSSQL)
9. etl_fact_online_sales   (MSSQL + PG lookup for payment_method_key)
```

DAGs 1–8 are independent of each other. DAG 9 (fact) requires DAG 5 (payment method)
to be loaded in PostgreSQL so that `transform` can resolve card type → surrogate key.

---

## DAG Catalogue

### `etl_dim_date`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_date.py` |
| Target | `dim.dim_date` |
| Source | Generated (no DB) |
| Pattern | Single task — generate + TRUNCATE + INSERT |
| Range | 2022-01-01 to 2026-12-31 (1,827 rows) |

---

### `etl_dim_order_channel`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_order_channel.py` |
| Target | `dim.dim_order_channel` |
| Source | Seeded (hardcoded 2 rows) |
| Pattern | Single task — TRUNCATE + INSERT |
| Rows | 2 — key 1 = Online, key 2 = In-Store |

Fact rows always have `order_channel_key = 1` because the extract filters `OnlineOrderFlag = 1`.

---

### `etl_dim_territory`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_territory.py` |
| Target | `dim.dim_territory` |
| Source | `Sales.SalesTerritory` |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |

---

### `etl_dim_delivery_method`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_delivery_method.py` |
| Target | `dim.dim_delivery_method` |
| Source | `Purchasing.ShipMethod` |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |
| Key | `ShipMethodID` used as natural key — no surrogate |

---

### `etl_dim_payment_method`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_payment_method.py` |
| Target | `dim.dim_payment_method` |
| Source | `Sales.CreditCard` (distinct `CardType`) + synthetic key 0 = 'None' |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |
| Key | `ROW_NUMBER() OVER (ORDER BY CardType)` — key 0 reserved for orders with no card |

**Dependency:** Must be loaded before `etl_fact_online_sales` runs. The fact transform
queries `dim.dim_payment_method` in PostgreSQL to resolve card type to surrogate key.

---

### `etl_dim_geography`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_geography.py` |
| Target | `dim.dim_geography` |
| Source | `Person.Address` JOIN `Person.StateProvince` JOIN `Person.CountryRegion` |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |
| Key | `AddressID` used as natural key — no surrogate |

Maps to `fact.fact_online_sales.geography_key` via `SalesOrderHeader.ShipToAddressID`.

---

### `etl_dim_product`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_product.py` |
| Target | `dim.dim_product` |
| Source | `Production.Product` LEFT JOIN `Production.ProductSubcategory` LEFT JOIN `Production.ProductCategory` |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |
| Teaching note | LEFT JOIN intentional — products without subcategory load with NULL hierarchy |

---

### `etl_dim_customer`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_customer.py` |
| Target | `dim.dim_customer` |
| Source | `Sales.Customer` LEFT JOIN `Person.Person` LEFT JOIN `Sales.SalesTerritory` |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |

---

### `etl_fact_online_sales`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_fact_online_sales.py` |
| Target | `fact.fact_online_sales` |
| Source | `Sales.SalesOrderHeader` JOIN `Sales.SalesOrderDetail` LEFT JOIN `Sales.CreditCard` |
| Filter | `OnlineOrderFlag = 1` |
| Pattern | Extract → Transform → Load (TRUNCATE + INSERT) |

**FK resolution in transform:**
- `order_date_key` — derived from `OrderDate` as `YYYYMMDD` integer
- `order_channel_key` — hardcoded `1` (Online) because of the `OnlineOrderFlag = 1` filter
- `payment_method_key` — resolved via live PG query to `dim.dim_payment_method` on `CardType`
- `geography_key` — maps directly from `ShipToAddressID` = `dim.dim_geography.geography_key`
- `delivery_method_key` — maps directly from `ShipMethodID` = `dim.dim_delivery_method.delivery_method_key`

---

## Adding a New DAG

1. Create `airflow/dags/etl_<name>.py` following the Extract → Transform → Load pattern.
2. Add extract SQL to `sql/source/extract_<name>.sql`.
3. Add warehouse DDL to `sql/warehouse/ddl_<name>.sql`.
4. Add `CREATE TABLE IF NOT EXISTS` to `docker/postgres/init/01_warehouse_schema.sql`.
5. Apply DDL to the running Postgres instance manually or by restarting the container.
6. Add the new DAG to the **Execution Order** and **DAG Catalogue** sections above.
7. Add column mapping to `docs/source_to_target_mapping.md`.
8. Write transform tests in `tests/test_transform_<name>.py` or extend `test_transform_phase2.py`.
