INSERT INTO dim.dim_product (
    product_key,
    product_code,
    product_name,
    subcategory_key,
    subcategory_name,
    category_key,
    category_name
)
SELECT
    p.ProductID              AS product_key,
    TRIM(p.ProductNumber)    AS product_code,
    TRIM(p.Name)             AS product_name,
    ps.ProductSubcategoryID  AS subcategory_key,
    ps.Name                  AS subcategory_name,
    pc.ProductCategoryID     AS category_key,
    pc.Name                  AS category_name
FROM Production.Product AS p
LEFT JOIN Production.ProductSubcategory AS ps
    ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production.ProductCategory AS pc
    ON ps.ProductCategoryID = pc.ProductCategoryID
