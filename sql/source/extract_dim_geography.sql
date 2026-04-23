SELECT
    ROW_NUMBER() OVER (ORDER BY sp.CountryRegionCode, a.City) AS GeographyKey,
    DENSE_RANK()  OVER (ORDER BY sp.CountryRegionCode)        AS CountryKey,
    cr.Name                 AS CountryName,
    sp.CountryRegionCode    AS CountryCode,
    ROW_NUMBER() OVER (ORDER BY sp.CountryRegionCode, a.City) AS CityKey,
    a.City                  AS CityName,
    sp.TerritoryID          AS SalesTerritoryKey
FROM (SELECT DISTINCT City, StateProvinceID FROM Person.Address) AS a
JOIN Person.StateProvince  AS sp ON a.StateProvinceID   = sp.StateProvinceID
JOIN Person.CountryRegion  AS cr ON sp.CountryRegionCode = cr.CountryRegionCode
