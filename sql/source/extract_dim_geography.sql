WITH ranked AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY sp.CountryRegionCode, a.City) AS rn,
        DENSE_RANK()  OVER (ORDER BY sp.CountryRegionCode)        AS CountryKey,
        cr.Name              AS CountryName,
        sp.CountryRegionCode AS CountryCode,
        a.City               AS CityName,
        sp.TerritoryID       AS SalesTerritoryKey
    FROM (SELECT DISTINCT City, StateProvinceID FROM Person.Address) AS a
    JOIN Person.StateProvince AS sp ON a.StateProvinceID   = sp.StateProvinceID
    JOIN Person.CountryRegion AS cr ON sp.CountryRegionCode = cr.CountryRegionCode
)
SELECT
    rn           AS GeographyKey,
    CountryKey,
    CountryName,
    CountryCode,
    rn           AS CityKey,
    CityName,
    SalesTerritoryKey
FROM ranked
