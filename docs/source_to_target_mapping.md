# Source-to-Target Mapping

---

## DimProduct

## Overview

| Attribute | Value |
|---|---|
| Target table | `dim.dim_product` |
| Target system | PostgreSQL warehouse |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |
| Phase | PoC |

## Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `product_key` | INTEGER NOT NULL PK | `Production.Product` | `ProductID` | Direct cast |
| `product_code` | VARCHAR(25) NOT NULL | `Production.Product` | `ProductNumber` | TRIM |
| `product_name` | VARCHAR(50) NOT NULL | `Production.Product` | `Name` | TRIM |
| `subcategory_key` | INTEGER NULLABLE | `Production.ProductSubcategory` | `ProductSubcategoryID` | NULL if product has no subcategory |
| `subcategory_name` | VARCHAR(50) NULLABLE | `Production.ProductSubcategory` | `Name` | NULL if product has no subcategory |
| `category_key` | INTEGER NULLABLE | `Production.ProductCategory` | `ProductCategoryID` | NULL if product has no subcategory |
| `category_name` | VARCHAR(50) NULLABLE | `Production.ProductCategory` | `Name` | NULL if product has no subcategory |

## Source Tables

### `Production.Product`
Primary source. One row per product.

Key columns used:
- `ProductID` → product_key
- `ProductNumber` → product_code
- `Name` → product_name
- `ProductSubcategoryID` → join key (nullable — not all products have a subcategory)

### `Production.ProductSubcategory`
Joined via `Product.ProductSubcategoryID = ProductSubcategory.ProductSubcategoryID`.

Key columns used:
- `ProductSubcategoryID` → subcategory_key
- `Name` → subcategory_name
- `ProductCategoryID` → join key to ProductCategory

### `Production.ProductCategory`
Joined via `ProductSubcategory.ProductCategoryID = ProductCategory.ProductCategoryID`.

Key columns used:
- `ProductCategoryID` → category_key
- `Name` → category_name

## Join Strategy

```sql
Production.Product AS p
LEFT JOIN Production.ProductSubcategory AS ps
    ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production.ProductCategory AS pc
    ON ps.ProductCategoryID = pc.ProductCategoryID
```

**Teaching note:** LEFT JOIN is intentional. Products without a subcategory (e.g., components) are included in DimProduct with NULL hierarchy columns. An INNER JOIN would silently exclude these rows — a common ETL mistake.

## Null Handling Rules

| Column | Null allowed | Behaviour when source is null |
|---|---|---|
| product_key | No | Source ProductID is always populated — if null, row is an error |
| product_code | No | Source ProductNumber is always populated |
| product_name | No | Source Name is always populated |
| subcategory_key | Yes | NULL when Product.ProductSubcategoryID IS NULL |
| subcategory_name | Yes | NULL when no subcategory match |
| category_key | Yes | NULL when no subcategory match |
| category_name | Yes | NULL when no subcategory match |

## Validation Checks

| Check | Expected |
|---|---|
| Row count | > 0 |
| Row count vs source | `COUNT(dim_product)` = `COUNT(Production.Product)` |
| ProductKey uniqueness | No duplicates on `product_key` |
| ProductKey not null | 0 rows with `product_key IS NULL` |

## Data Type Normalisation

| SQL Server type | PostgreSQL type |
|---|---|
| `int` | `INTEGER` |
| `nvarchar(n)` | `VARCHAR(n)` |
| `NULL` (FK) | `NULL` |

---

## DimDate

| Attribute | Value |
|---|---|
| Target table | `dim.dim_date` |
| Source system | Generated (no DB source) |
| Load pattern | Full reload (TRUNCATE + INSERT) |
| Range | 2022-01-01 to 2026-12-31 |

### Column Mapping

| Target Column | Type | Source | Transform |
|---|---|---|---|
| `date_key` | INTEGER NOT NULL PK | Computed | `YYYYMMDD` integer from `full_date` |
| `full_date` | DATE NOT NULL | Generated | Sequential calendar day |
| `year` | SMALLINT NOT NULL | Generated | `date.year` |
| `quarter` | SMALLINT NOT NULL | Generated | `(month - 1) // 3 + 1` |
| `month` | SMALLINT NOT NULL | Generated | `date.month` |
| `month_name` | VARCHAR(9) NOT NULL | Generated | Lookup from month number |
| `week_of_year` | SMALLINT NOT NULL | Generated | `strftime("%W")` — Monday-based week 0 |
| `day_of_month` | SMALLINT NOT NULL | Generated | `date.day` |
| `day_of_week` | SMALLINT NOT NULL | Generated | `weekday() + 1` (1=Monday, 7=Sunday) |
| `day_name` | VARCHAR(9) NOT NULL | Generated | Lookup from weekday number |
| `is_weekend` | BOOLEAN NOT NULL | Generated | `weekday() >= 5` |

---

## DimTerritory

| Attribute | Value |
|---|---|
| Target table | `dim.dim_territory` |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `territory_key` | INTEGER NOT NULL PK | `Sales.SalesTerritory` | `TerritoryID` | Direct cast |
| `territory_name` | VARCHAR(50) NOT NULL | `Sales.SalesTerritory` | `Name` | TRIM |
| `country_region_code` | VARCHAR(3) NOT NULL | `Sales.SalesTerritory` | `CountryRegionCode` | TRIM |
| `region_group` | VARCHAR(50) NOT NULL | `Sales.SalesTerritory` | `[Group]` | TRIM |

---

## DimCustomer

| Attribute | Value |
|---|---|
| Target table | `dim.dim_customer` |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `customer_key` | INTEGER NOT NULL PK | `Sales.Customer` | `CustomerID` | Direct cast |
| `account_number` | VARCHAR(10) NOT NULL | `Sales.Customer` | `AccountNumber` | TRIM |
| `first_name` | VARCHAR(50) NULLABLE | `Person.Person` | `FirstName` | NULL if no Person row (store-only customers) |
| `last_name` | VARCHAR(50) NULLABLE | `Person.Person` | `LastName` | NULL if no Person row |
| `full_name` | VARCHAR(101) NULLABLE | Computed | `COALESCE(FirstName+' ','')+COALESCE(LastName,'')` | NULL if no Person row |
| `territory_key` | INTEGER NULLABLE | `Sales.Customer` | `TerritoryID` | NULL if unassigned |
| `territory_name` | VARCHAR(50) NULLABLE | `Sales.SalesTerritory` | `Name` | NULL if no territory match |

### Join Strategy

```sql
Sales.Customer AS c
LEFT JOIN Person.Person AS p ON c.PersonID = p.BusinessEntityID
LEFT JOIN Sales.SalesTerritory AS st ON c.TerritoryID = st.TerritoryID
```

---

## FactOnlineSales

| Attribute | Value |
|---|---|
| Target table | `fact.fact_online_sales` |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |
| Filter | `OnlineOrderFlag = 1` (excludes in-store orders) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `sales_order_key` | BIGINT NOT NULL PK | `Sales.SalesOrderDetail` | `SalesOrderDetailID` | Direct cast |
| `order_date_key` | INTEGER NOT NULL | `Sales.SalesOrderHeader` | `OrderDate` | `YYYYMMDD` integer — FK to dim.dim_date |
| `customer_key` | INTEGER NULLABLE | `Sales.SalesOrderHeader` | `CustomerID` | FK to dim.dim_customer, NULL for guest orders |
| `product_key` | INTEGER NOT NULL | `Sales.SalesOrderDetail` | `ProductID` | FK to dim.dim_product |
| `territory_key` | INTEGER NULLABLE | `Sales.SalesOrderHeader` | `TerritoryID` | FK to dim.dim_territory |
| `order_qty` | SMALLINT NOT NULL | `Sales.SalesOrderDetail` | `OrderQty` | Direct cast |
| `unit_price` | NUMERIC(19,4) NOT NULL | `Sales.SalesOrderDetail` | `UnitPrice` | Direct cast |
| `unit_price_discount` | NUMERIC(19,4) NOT NULL | `Sales.SalesOrderDetail` | `UnitPriceDiscount` | Direct cast, defaults to 0 |
| `line_total` | NUMERIC(19,4) NOT NULL | `Sales.SalesOrderDetail` | `LineTotal` | Direct cast |
| `sub_total` | NUMERIC(19,4) NULLABLE | `Sales.SalesOrderHeader` | `SubTotal` | Header-level, shared across detail rows |
| `tax_amt` | NUMERIC(19,4) NULLABLE | `Sales.SalesOrderHeader` | `TaxAmt` | Header-level |
| `freight` | NUMERIC(19,4) NULLABLE | `Sales.SalesOrderHeader` | `Freight` | Header-level |
| `total_due` | NUMERIC(19,4) NULLABLE | `Sales.SalesOrderHeader` | `TotalDue` | Header-level |

### Join Strategy

```sql
Sales.SalesOrderHeader AS h
JOIN Sales.SalesOrderDetail AS d ON h.SalesOrderID = d.SalesOrderID
WHERE h.OnlineOrderFlag = 1
```

**Note:** Header-level financial fields (SubTotal, TaxAmt, Freight, TotalDue) repeat across detail rows for the same order. This is intentional for teaching aggregation queries.

---

## DimOrderChannel

| Attribute | Value |
|---|---|
| Target table | `dim.dim_order_channel` |
| Source system | Seeded (no DB extract) |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source | Transform |
|---|---|---|---|
| `order_channel_key` | INTEGER NOT NULL PK | Seeded | 1 = Online, 2 = In-Store |
| `channel_name` | VARCHAR(20) NOT NULL | Seeded | "Online" or "In-Store" |
| `online_flag` | BOOLEAN NOT NULL | Seeded | True for Online, False for In-Store |

**Note:** All rows in `fact.fact_online_sales` have `order_channel_key = 1` because the extract filters `OnlineOrderFlag = 1`. The In-Store row exists for completeness.

---

## DimDeliveryMethod

| Attribute | Value |
|---|---|
| Target table | `dim.dim_delivery_method` |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `delivery_method_key` | INTEGER NOT NULL PK | `Purchasing.ShipMethod` | `ShipMethodID` | Natural key — no surrogate |
| `delivery_method_name` | VARCHAR(50) NOT NULL | `Purchasing.ShipMethod` | `Name` | TRIM |
| `ship_base` | NUMERIC(19,4) | `Purchasing.ShipMethod` | `ShipBase` | Direct cast |
| `ship_rate` | NUMERIC(19,4) | `Purchasing.ShipMethod` | `ShipRate` | Direct cast |

Maps to `fact.fact_online_sales.delivery_method_key` via `SalesOrderHeader.ShipMethodID`.

---

## DimPaymentMethod

| Attribute | Value |
|---|---|
| Target table | `dim.dim_payment_method` |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `payment_method_key` | INTEGER NOT NULL PK | `Sales.CreditCard` | `CardType` (DISTINCT) | `ROW_NUMBER() OVER (ORDER BY CardType)`; key 0 = 'None' for orders without a card |
| `payment_method_name` | VARCHAR(50) NOT NULL | `Sales.CreditCard` | `CardType` | Direct value; 'None' for missing |

**FK resolution in fact:** The `transform` step of `etl_fact_online_sales` queries `dim.dim_payment_method` in PostgreSQL at runtime to build a name→key lookup dict. This means `etl_dim_payment_method` must be run before `etl_fact_online_sales`.

---

## DimGeography

| Attribute | Value |
|---|---|
| Target table | `dim.dim_geography` |
| Source system | SQL Server — AdventureWorks2025 |
| Load pattern | Full reload (TRUNCATE + INSERT) |

### Column Mapping

| Target Column | Type | Source Table | Source Column | Transform |
|---|---|---|---|---|
| `geography_key` | INTEGER NOT NULL PK | `Person.Address` | `AddressID` | Natural key — no surrogate |
| `address_line1` | VARCHAR(60) | `Person.Address` | `AddressLine1` | Direct |
| `city` | VARCHAR(30) NOT NULL | `Person.Address` | `City` | TRIM |
| `state_province_code` | VARCHAR(3) | `Person.StateProvince` | `StateProvinceCode` | Direct |
| `state_province_name` | VARCHAR(50) | `Person.StateProvince` | `Name` | Direct |
| `country_region_code` | VARCHAR(3) NOT NULL | `Person.StateProvince` | `CountryRegionCode` | TRIM |
| `country_name` | VARCHAR(50) NOT NULL | `Person.CountryRegion` | `Name` | TRIM |
| `postal_code` | VARCHAR(15) | `Person.Address` | `PostalCode` | Direct |

### Join Strategy

```sql
Person.Address AS a
JOIN Person.StateProvince AS sp ON a.StateProvinceID   = sp.StateProvinceID
JOIN Person.CountryRegion AS cr ON sp.CountryRegionCode = cr.CountryRegionCode
```

Maps to `fact.fact_online_sales.geography_key` via `SalesOrderHeader.ShipToAddressID`.
