SELECT
    c.CustomerID,
    c.AccountNumber,
    p.FirstName,
    p.LastName,
    TRIM(COALESCE(p.FirstName + ' ', '') + COALESCE(p.LastName, '')) AS FullName,
    c.TerritoryID,
    st.Name AS TerritoryName
FROM Sales.Customer AS c
LEFT JOIN Person.Person AS p
    ON c.PersonID = p.BusinessEntityID
LEFT JOIN Sales.SalesTerritory AS st
    ON c.TerritoryID = st.TerritoryID
