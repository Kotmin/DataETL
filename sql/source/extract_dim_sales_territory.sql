SELECT
    st.TerritoryID                                         AS SalesTerritoryKey,
    st.Name                                                AS SalesTerritoryName,
    DENSE_RANK() OVER (ORDER BY st.CountryRegionCode)      AS CountryKey,
    cr.Name                                                AS CountryName,
    st.CountryRegionCode                                   AS CountryCode
FROM Sales.SalesTerritory  AS st
JOIN Person.CountryRegion  AS cr ON st.CountryRegionCode = cr.CountryRegionCode
