SELECT
    a.AddressID             AS GeographyKey,
    a.AddressLine1,
    a.City,
    sp.StateProvinceCode,
    sp.Name                 AS StateProvinceName,
    sp.CountryRegionCode,
    cr.Name                 AS CountryName,
    a.PostalCode
FROM Person.Address AS a
JOIN Person.StateProvince  AS sp ON a.StateProvinceID   = sp.StateProvinceID
JOIN Person.CountryRegion  AS cr ON sp.CountryRegionCode = cr.CountryRegionCode
