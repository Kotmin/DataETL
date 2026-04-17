# Source-to-Target Mapping — DimProduct

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
