SELECT
    h.SalesOrderNumber                                          AS OrderKey,
    ROW_NUMBER() OVER (
        PARTITION BY h.SalesOrderID
        ORDER BY d.SalesOrderDetailID
    )                                                           AS OrderLineNumber,
    h.CustomerID,
    d.ProductID,
    h.TerritoryID,
    h.ShipMethodID,
    COALESCE(cc.CardType, 'None')                              AS CardType,
    h.OrderDate,
    h.ShipDate,
    d.OrderQty,
    d.UnitPrice,
    d.UnitPriceDiscount,
    d.LineTotal,
    h.Freight,
    h.SubTotal,
    COALESCE(pch.StandardCost, pp.StandardCost, 0)             AS ProductCost
FROM Sales.SalesOrderHeader AS h
JOIN Sales.SalesOrderDetail  AS d  ON h.SalesOrderID  = d.SalesOrderID
LEFT JOIN Sales.CreditCard   AS cc ON h.CreditCardID  = cc.CreditCardID
LEFT JOIN Production.Product AS pp ON d.ProductID     = pp.ProductID
OUTER APPLY (
    SELECT TOP 1 pch_inner.StandardCost
    FROM Production.ProductCostHistory AS pch_inner
    WHERE pch_inner.ProductID = d.ProductID
      AND h.OrderDate BETWEEN pch_inner.StartDate
                          AND ISNULL(pch_inner.EndDate, '9999-12-31')
    ORDER BY pch_inner.StartDate DESC
) AS pch
WHERE h.OnlineOrderFlag = 1
