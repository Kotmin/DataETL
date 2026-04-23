SELECT
    c.CustomerID,
    p.FirstName,
    p.LastName,
    addr.City,
    sp.StateProvinceCode,
    sp.CountryRegionCode
FROM Sales.Customer AS c
LEFT JOIN Person.Person AS p
    ON c.PersonID = p.BusinessEntityID
OUTER APPLY (
    SELECT TOP 1 a.AddressID, a.StateProvinceID, a.City
    FROM Person.BusinessEntityAddress AS bea
    JOIN Person.Address               AS a ON bea.AddressID = a.AddressID
    WHERE bea.BusinessEntityID = c.PersonID
    ORDER BY bea.AddressTypeID
) AS addr
LEFT JOIN Person.StateProvince AS sp
    ON addr.StateProvinceID = sp.StateProvinceID
