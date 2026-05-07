# DAG Reference

This document is the canonical catalog of all Airflow DAGs in this project.
**Keep it updated** when adding, removing, or changing a DAG.

---

## Execution Order

All dims must run before the fact. Dependencies:
- `etl_dim_geography` must complete before `etl_dim_customer` (customer transform queries geog dim)
- `etl_dim_payment_method` must complete before `etl_fact_online_sales` (fact transform queries payment dim)

```
1. etl_dim_date             (MSSQL — date range from OrderDate/ShipDate)
2. etl_dim_order_channel    (MSSQL — derive from OnlineOrderFlag)
3. etl_dim_sales_territory  (MSSQL)
4. etl_dim_delivery_method  (MSSQL)
5. etl_dim_payment_method   (MSSQL) ← must run before fact
6. etl_dim_geography        (MSSQL) ← must run before customer
7. etl_dim_product          (MSSQL)
8. etl_dim_customer         (MSSQL + PG lookup for geography_key)
9. etl_fact_online_sales    (MSSQL + PG lookup for payment_method_key)
```

---

## Cross-DAG Dependency Enforcement

Two DAGs perform a live PostgreSQL lookup during their `transform` task against a dimension table that must already be fully loaded. To prevent a race condition where the transform hits an empty or mid-reload dim, an `ExternalTaskSensor` is inserted as the first task in each dependent DAG.

| Dependent DAG | Sensor task | Waits for | Why |
|---|---|---|---|
| `etl_dim_customer` | `wait_for_dim_geography` | `etl_dim_geography.load_dim_geography` | `transform` queries `dim.dim_geography` for `geography_key` lookup |
| `etl_fact_online_sales` | `wait_for_dim_payment_method` | `etl_dim_payment_method.load_dim_payment_method` | `transform` queries `dim.dim_payment_method` for `payment_method_key` lookup |

### Sensor configuration

Both sensors use `mode="reschedule"` so worker slots are released between polls.

All DAGs now run at `0 4 * * *`. Each sensor maps its execution date to the same
day's 4am run of the upstream DAG.

**`etl_dim_customer`** uses an inline lambda (geography runs at the same hour):
```python
execution_date_fn=lambda dt: dt.replace(hour=4, minute=0, second=0, microsecond=0)
```

**`etl_fact_online_sales`** uses a named function for explicitness:
```python
def _payment_method_run_dt(dt):
    return dt.replace(hour=4, minute=0, second=0, microsecond=0)
```

### Direct-run mode

`python app/main.py run --all` calls DAG functions directly in Python — sensors are not activated. Execution order is enforced by the `DAG_EXECUTION_ORDER` list in `app/main.py`.

---

## Type Mapping

Oracle NUMBER types → PostgreSQL: `NUMBER(1-3)=SMALLINT`, `NUMBER(5)=INTEGER`, `NUMBER(8)=INTEGER`, `NUMBER(10)=BIGINT`, `NUMBER(n,d)=NUMERIC(n,d)`, `VARCHAR2(n)=VARCHAR(n)`, `CHAR(n)=CHAR(n)`.

---

## DAG Catalogue

### `etl_dim_date`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_date.py` |
| Target | `dim.dim_date` |
| Source | MSSQL — range from `MIN(OrderDate)` to `MAX(ShipDate)` in SalesOrderHeader ±1 year buffer |
| Pattern | Single task — query range, generate dates, TRUNCATE + INSERT |
| Key columns | `day_number_of_year` (new), column names aligned to spec |

---

### `etl_dim_order_channel`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_order_channel.py` |
| Target | `dim.dim_order_channel` |
| Source | MSSQL — `DISTINCT OnlineOrderFlag` from SalesOrderHeader |
| Pattern | Extract → Transform → Load |
| Rows | key 1 = Online (flag=1), key 2 = In-Store (flag=0) |

---

### `etl_dim_sales_territory`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_sales_territory.py` |
| Target | `dim.dim_sales_territory` (replaces `dim_territory`) |
| Source | `Sales.SalesTerritory` JOIN `Person.CountryRegion` |
| Pattern | Extract → Transform → Load |
| Key columns | `sales_territory_key`, `country_key` (DENSE_RANK), `country_name`, `country_code` |

---

### `etl_dim_delivery_method`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_delivery_method.py` |
| Target | `dim.dim_delivery_method` |
| Source | `Purchasing.ShipMethod` |
| Key | `ShipMethodID` as natural key |

---

### `etl_dim_payment_method`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_payment_method.py` |
| Target | `dim.dim_payment_method` |
| Source | `DISTINCT CardType` from `Sales.CreditCard` + key 0 = 'None' |
| Key | `ROW_NUMBER() OVER (ORDER BY CardType)` |

**Dependency:** Must load before `etl_fact_online_sales`.

---

### `etl_dim_geography`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_geography.py` |
| Target | `dim.dim_geography` |
| Source | `Person.Address` (distinct City+StateProvinceID) JOIN `Person.StateProvince` JOIN `Person.CountryRegion` |
| Grain | Distinct `(City, CountryRegionCode)` |
| Key | `ROW_NUMBER()` surrogate; `CountryKey` = DENSE_RANK on country |
| Key columns | `geography_key`, `country_key`, `city_key`, `sales_territory_key` FK |

**Dependency:** Must load before `etl_dim_customer`.

---

### `etl_dim_product`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_product.py` |
| Target | `dim.dim_product` |
| Source | `Production.Product` LEFT JOIN subcategory LEFT JOIN category |
| Key columns | Types aligned to spec: `product_code VARCHAR(12)`, `product_name VARCHAR(40)` |

---

### `etl_dim_customer`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_dim_customer.py` |
| Target | `dim.dim_customer` |
| Source | `Sales.Customer` LEFT JOIN `Person.Person` OUTER APPLY address → StateProvince |
| Key columns | `geography_key` FK (resolved via PG lookup); no `account_number`, no `full_name` |

**FK resolution:** Transform queries `dim.dim_geography` in PG on `(city_name, country_code)`.

---

### `etl_fact_online_sales`

| Attribute | Value |
|---|---|
| File | `airflow/dags/etl_fact_online_sales.py` |
| Target | `fact.fact_online_sales` |
| Source | `SalesOrderHeader` JOIN `SalesOrderDetail` LEFT JOIN `CreditCard` LEFT JOIN `ProductCostHistory` (OUTER APPLY) |
| Filter | `OnlineOrderFlag = 1` |
| PK | Composite: `(order_key=SalesOrderNumber, order_line_number=ROW_NUMBER())` |

**Computed measures in transform:**
- `discount_amount` = `UnitPrice × UnitPriceDiscount`
- `discount_pctg` = `round(UnitPriceDiscount × 100)` as integer %
- `transaction_price` = `UnitPrice × (1 - UnitPriceDiscount)`
- `delivery_cost` = Freight allocated proportionally: `Freight × LineTotal / OrderSubTotal`
- `product_cost` = from `ProductCostHistory` by effective date; fallback `Product.StandardCost`
- `ship_date_key` = YYYYMMDD from ShipDate; NULL if ShipDate is null

---

## Adding a New DAG

1. Create `airflow/dags/etl_<name>.py` (Extract → Transform → Load pattern).
2. Add extract SQL to `sql/source/extract_<name>.sql`.
3. Add warehouse DDL to `sql/warehouse/ddl_<name>.sql`.
4. Add `CREATE TABLE IF NOT EXISTS` to `docker/postgres/init/01_warehouse_schema.sql`.
5. Apply DDL to running Postgres manually (`ALTER TABLE` or container restart).
6. Update **Execution Order** and **DAG Catalogue** above.
7. Update `docs/source_to_target_mapping.md` with column mapping.
8. Add transform tests in `tests/test_transform_<name>.py`.
