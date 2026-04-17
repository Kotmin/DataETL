SELECT
    p.ProductID,
    p.ProductNumber,
    p.Name              AS ProductName,
    ps.ProductSubcategoryID,
    ps.Name             AS SubcategoryName,
    pc.ProductCategoryID,
    pc.Name             AS CategoryName
FROM Production.Product AS p
LEFT JOIN Production.ProductSubcategory AS ps
    ON p.ProductSubcategoryID = ps.ProductSubcategoryID
LEFT JOIN Production.ProductCategory AS pc
    ON ps.ProductCategoryID = pc.ProductCategoryID
