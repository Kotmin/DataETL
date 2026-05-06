# Source-to-Target Mapping

Type convention: `NUMBER(1-3)→SMALLINT`, `NUMBER(5)→INTEGER`, `NUMBER(8)→INTEGER`, `NUMBER(10)→BIGINT`, `NUMBER(n,d)→NUMERIC(n,d)`, `VARCHAR2(n)→VARCHAR(n)`, `CHAR(n)→CHAR(n)`.

---

## dim.dim_date

| Attribute | Value |
|---|---|
| Target table | `dim.dim_date` |
| Source system | MSSQL — `Sales.SalesOrderHeader` (date range, `OnlineOrderFlag = 1`) + Python generation |
| Load pattern | Full reload (TRUNCATE + INSERT) |
| Range | `MIN(OrderDate) − 1 year` to `MAX(ShipDate) + 1 year` |

### Column Mapping

| Target Column | Type | Source | Transform |
|---|---|---|---|
| `date_key` | INTEGER NOT NULL PK | Computed | `YYYYMMDD` integer from `full_date` |
| `full_date` | DATE NOT NULL | Generated | Sequential calendar day |
| `calendar_year` | SMALLINT NOT NULL | Generated | `date.year` |
| `calendar_quarter` | SMALLINT NOT NULL | Generated | `(month - 1) // 3 + 1` |
| `month_number_of_year` | SMALLINT NOT NULL | Generated | `date.month` |
| `month_name` | VARCHAR(12) NOT NULL | Generated | Locale month name |
| `week_number_of_year` | SMALLINT NOT NULL | Generated | `strftime("%V")` ISO 8601 week (1–53, Monday-based; no week 0) |
| `day_number_of_year` | SMALLINT NOT NULL | Generated | `date.timetuple().tm_yday` |
| `day_number_of_month` | SMALLINT NOT NULL | Generated | `date.day` |
| `day_number_of_week` | SMALLINT NOT NULL | Generated | `weekday() + 1` (1=Mon, 7=Sun) |
| `day_name_of_week` | VARCHAR(12) NOT NULL | Generated | Locale weekday name |
| `is_weekend` | BOOLEAN NOT NULL | Generated | `weekday() >= 5` |

---

## dim.dim_order_channel

| Attribute | Value |
|---|---|
| Target table | `dim.dim_order_channel` |
| Source system | MSSQL — `Sales.SalesOrderHeader.OnlineOrderFlag` |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `order_channel_key` | SMALLINT NOT NULL PK | `Sales.SalesOrderHeader` | `OnlineOrderFlag` | `1→1 (Online)`, `0→2 (In-Store)` |
| `channel_name` | VARCHAR(20) NOT NULL | Derived | `OnlineOrderFlag` | `1→'Online'`, `0→'In-Store'` |

---

## dim.dim_sales_territory

| Attribute | Value |
|---|---|
| Target table | `dim.dim_sales_territory` |
| Source system | MSSQL — `Sales.SalesTerritory` JOIN `Person.CountryRegion` |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `sales_territory_key` | SMALLINT NOT NULL PK | `Sales.SalesTerritory` | `TerritoryID` | Direct cast |
| `sales_territory_name` | VARCHAR(50) NOT NULL | `Sales.SalesTerritory` | `Name` | TRIM |
| `country_key` | SMALLINT NOT NULL | Computed | `CountryRegionCode` | `DENSE_RANK() OVER (ORDER BY CountryRegionCode)` |
| `country_name` | VARCHAR(50) NOT NULL | `Person.CountryRegion` | `Name` | TRIM |
| `country_code` | CHAR(2) NOT NULL | `Sales.SalesTerritory` | `CountryRegionCode` | TRIM |

### Join Strategy

```sql
Sales.SalesTerritory AS st
JOIN Person.CountryRegion AS cr ON st.CountryRegionCode = cr.CountryRegionCode
```

---

## dim.dim_delivery_method

| Attribute | Value |
|---|---|
| Target table | `dim.dim_delivery_method` |
| Source system | MSSQL — `Purchasing.ShipMethod` |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `delivery_method_key` | SMALLINT NOT NULL PK | `Purchasing.ShipMethod` | `ShipMethodID` | Natural key |
| `delivery_method_name` | VARCHAR(20) NOT NULL | `Purchasing.ShipMethod` | `Name` | TRIM |

---

## dim.dim_payment_method

| Attribute | Value |
|---|---|
| Target table | `dim.dim_payment_method` |
| Source system | MSSQL — `Sales.CreditCard` |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `payment_method_key` | SMALLINT NOT NULL PK | `Sales.CreditCard` | `CardType` | `ROW_NUMBER() OVER (ORDER BY CardType)`; key 0 reserved for `'None'` |
| `payment_method_name` | VARCHAR(20) NOT NULL | `Sales.CreditCard` | `CardType` | DISTINCT values + `'None'` for orders without a card |

**FK resolution in fact:** `etl_fact_online_sales.transform` queries `dim.dim_payment_method` at runtime. `etl_dim_payment_method` must run before `etl_fact_online_sales`.

---

## dim.dim_geography

| Attribute | Value |
|---|---|
| Target table | `dim.dim_geography` |
| Source system | MSSQL — `Person.Address` JOIN `Person.StateProvince` JOIN `Person.CountryRegion` |
| Grain | Distinct `(City, CountryRegionCode)` |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `geography_key` | SMALLINT NOT NULL PK | Computed | `(City, CountryRegionCode)` DISTINCT | `ROW_NUMBER() OVER (ORDER BY CountryCode, City)` |
| `country_key` | SMALLINT NOT NULL | Computed | `CountryRegionCode` | `DENSE_RANK() OVER (ORDER BY CountryRegionCode)` |
| `country_name` | VARCHAR(50) NOT NULL | `Person.CountryRegion` | `Name` | TRIM |
| `country_code` | CHAR(2) NOT NULL | `Person.StateProvince` | `CountryRegionCode` | TRIM |
| `city_key` | SMALLINT NOT NULL | Computed | same as `geography_key` | Equals `geography_key` (grain is city-scoped) |
| `city_name` | VARCHAR(30) NOT NULL | `Person.Address` | `City` | TRIM |
| `sales_territory_key` | SMALLINT FK | `Person.StateProvince` | `TerritoryID` | FK → `dim.dim_sales_territory` |

### Join Strategy

```sql
(SELECT DISTINCT City, StateProvinceID FROM Person.Address) AS a
JOIN Person.StateProvince AS sp ON a.StateProvinceID = sp.StateProvinceID
JOIN Person.CountryRegion AS cr ON sp.CountryRegionCode = cr.CountryRegionCode
```

**FK resolution in customer:** `etl_dim_customer.transform` queries `dim.dim_geography` at runtime on `(city_name, country_code)`. `etl_dim_geography` must run before `etl_dim_customer`.

---

## dim.dim_product

| Attribute | Value |
|---|---|
| Target table | `dim.dim_product` |
| Source system | MSSQL — `Production.Product` JOIN subcategory JOIN category |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `product_key` | INTEGER NOT NULL PK | `Production.Product` | `ProductID` | Direct cast |
| `product_code` | VARCHAR(12) NOT NULL | `Production.Product` | `ProductNumber` | TRIM |
| `product_name` | VARCHAR(40) NOT NULL | `Production.Product` | `Name` | TRIM |
| `subcategory_key` | SMALLINT NULLABLE | `Production.ProductSubcategory` | `ProductSubcategoryID` | NULL if no subcategory |
| `subcategory_name` | VARCHAR(40) NULLABLE | `Production.ProductSubcategory` | `Name` | NULL if no subcategory |
| `category_key` | SMALLINT NULLABLE | `Production.ProductCategory` | `ProductCategoryID` | NULL if no subcategory |
| `category_name` | VARCHAR(30) NULLABLE | `Production.ProductCategory` | `Name` | NULL if no subcategory |

### Join Strategy

```sql
Production.Product AS p
LEFT JOIN Production.ProductSubcategory AS ps ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production.ProductCategory    AS pc ON ps.ProductCategoryID    = pc.ProductCategoryID
```

---

## dim.dim_customer

| Attribute | Value |
|---|---|
| Target table | `dim.dim_customer` |
| Source system | MSSQL — `Sales.Customer` JOIN `Person.Person` OUTER APPLY address |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `customer_key` | BIGINT NOT NULL PK | `Sales.Customer` | `CustomerID` | Direct cast |
| `first_name` | VARCHAR(25) NULLABLE | `Person.Person` | `FirstName` | NULL if no Person row |
| `last_name` | VARCHAR(45) NULLABLE | `Person.Person` | `LastName` | NULL if no Person row |
| `geography_key` | SMALLINT FK NULLABLE | PG lookup | `dim.dim_geography` | Resolved at transform time via `(city_name, country_code)`; NULL if no address |

### Address Resolution

```sql
OUTER APPLY (
    SELECT TOP 1 a.AddressID, a.StateProvinceID
    FROM Person.BusinessEntityAddress AS bea
    JOIN Person.Address AS a ON bea.AddressID = a.AddressID
    WHERE bea.BusinessEntityID = c.PersonID
    ORDER BY bea.AddressTypeID
) AS addr
LEFT JOIN Person.StateProvince AS sp ON addr.StateProvinceID = sp.StateProvinceID
```

TOP 1 by `AddressTypeID` selects a deterministic primary address per customer.

---

## fact.fact_online_sales

| Attribute | Value |
|---|---|
| Target table | `fact.fact_online_sales` |
| Source system | MSSQL — `SalesOrderHeader` JOIN `SalesOrderDetail` LEFT JOIN `CreditCard` OUTER APPLY `ProductCostHistory` |
| Filter | `OnlineOrderFlag = 1` |
| PK | Composite: `(order_key, order_line_number)` |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `order_key` | VARCHAR(10) NOT NULL PK1 | `Sales.SalesOrderHeader` | `SalesOrderNumber` | Direct (`"SO43659"` format) |
| `order_line_number` | SMALLINT NOT NULL PK2 | Computed | `SalesOrderDetailID` | `ROW_NUMBER() OVER (PARTITION BY SalesOrderID ORDER BY SalesOrderDetailID)` |
| `customer_key` | BIGINT NULLABLE | `Sales.SalesOrderHeader` | `CustomerID` | FK → `dim.dim_customer` |
| `product_key` | INTEGER NOT NULL | `Sales.SalesOrderDetail` | `ProductID` | FK → `dim.dim_product` |
| `sales_territory_key` | SMALLINT NULLABLE | `Sales.SalesOrderHeader` | `TerritoryID` | FK → `dim.dim_sales_territory` |
| `channel_key` | SMALLINT NOT NULL | Hardcoded | — | Always `1` (Online); fact is filtered to online orders |
| `payment_method_key` | SMALLINT NULLABLE | PG lookup | `dim.dim_payment_method` | Resolved at transform time via `CardType`; `COALESCE(cc.CardType, 'None')` |
| `delivery_method_key` | SMALLINT NULLABLE | `Sales.SalesOrderHeader` | `ShipMethodID` | FK → `dim.dim_delivery_method` |
| `order_date_key` | INTEGER NOT NULL | `Sales.SalesOrderHeader` | `OrderDate` | `YYYYMMDD` integer; FK → `dim.dim_date` |
| `ship_date_key` | INTEGER NULLABLE | `Sales.SalesOrderHeader` | `ShipDate` | `YYYYMMDD` integer; NULL if `ShipDate IS NULL` |
| `quantity` | SMALLINT NOT NULL | `Sales.SalesOrderDetail` | `OrderQty` | Direct cast |
| `catalog_price` | NUMERIC(7,2) NOT NULL | `Sales.SalesOrderDetail` | `UnitPrice` | `round(UnitPrice, 2)` — **non-additive**; use AVG or as a filter, not SUM |
| `discount_amount` | NUMERIC(7,2) NOT NULL | Computed | `UnitPrice`, `UnitPriceDiscount` | `round(UnitPrice × UnitPriceDiscount, 2)` |
| `discount_pctg` | SMALLINT NOT NULL | Computed | `UnitPriceDiscount` | `round(UnitPriceDiscount × 100)` as integer % — **non-additive**; rounded to nearest %, use AVG not SUM |
| `transaction_price` | NUMERIC(7,2) NOT NULL | Computed | `UnitPrice`, `UnitPriceDiscount` | `round(UnitPrice × (1 − UnitPriceDiscount), 2)` — **non-additive**; multiply by `quantity` first to get line revenue |
| `delivery_cost` | NUMERIC(7,2) NOT NULL | Computed | `Freight`, `LineTotal`, `SubTotal` | `round(Freight × LineTotal / OrderSubTotal, 2)`; proportional per line |
| `product_cost` | NUMERIC(8,2) NOT NULL | OUTER APPLY | `ProductCostHistory.StandardCost` | Effective-date lookup; fallback `Production.Product.StandardCost`; widened from spec NUMBER(5,2) — AW bikes exceed 999.99 |

### FK Constraints

| Constraint | Fact Column | References |
|---|---|---|
| `fk_fact_customer` | `customer_key` | `dim.dim_customer(customer_key)` — NULLABLE |
| `fk_fact_product` | `product_key` | `dim.dim_product(product_key)` — NOT NULL |
| `fk_fact_sales_territory` | `sales_territory_key` | `dim.dim_sales_territory(sales_territory_key)` — NULLABLE |
| `fk_fact_channel` | `channel_key` | `dim.dim_order_channel(order_channel_key)` — NOT NULL |
| `fk_fact_payment_method` | `payment_method_key` | `dim.dim_payment_method(payment_method_key)` — NULLABLE |
| `fk_fact_delivery_method` | `delivery_method_key` | `dim.dim_delivery_method(delivery_method_key)` — NULLABLE |
| `fk_fact_order_date` | `order_date_key` | `dim.dim_date(date_key)` — NOT NULL |
| `fk_fact_ship_date` | `ship_date_key` | `dim.dim_date(date_key)` — NULLABLE |

All dims must be loaded before the fact. Dim TRUNCATEs use `CASCADE` which propagates to this table.

### Join Strategy

```sql
Sales.SalesOrderHeader AS h
JOIN  Sales.SalesOrderDetail AS d   ON h.SalesOrderID  = d.SalesOrderID
LEFT JOIN Sales.CreditCard   AS cc  ON h.CreditCardID  = cc.CreditCardID
LEFT JOIN Production.Product AS pp  ON d.ProductID     = pp.ProductID
OUTER APPLY (
    SELECT TOP 1 StandardCost
    FROM Production.ProductCostHistory
    WHERE ProductID = d.ProductID
      AND h.OrderDate BETWEEN StartDate AND ISNULL(EndDate, '9999-12-31')
    ORDER BY StartDate DESC
) AS pch
WHERE h.OnlineOrderFlag = 1
```

### Delivery Cost Allocation

`Freight` is a header-level field shared across all lines of an order. It is allocated proportionally:

```
delivery_cost_line = Freight × (LineTotal / SUM(LineTotal) per OrderKey)
```

`SubTotal` from the extract is used as the denominator (equals `SUM(LineTotal)` for online orders). If `SubTotal = 0`, freight is applied in full to the single line.
