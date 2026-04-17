SELECT
    d.SalesOrderDetailID                    AS SalesOrderKey,
    h.OrderDate,
    h.CustomerID,
    d.ProductID,
    h.TerritoryID,
    h.ShipToAddressID,
    h.ShipMethodID,
    COALESCE(cc.CardType, 'None')           AS CardType,
    d.OrderQty,
    d.UnitPrice,
    d.UnitPriceDiscount,
    d.LineTotal,
    h.SubTotal,
    h.TaxAmt,
    h.Freight,
    h.TotalDue
FROM Sales.SalesOrderHeader AS h
JOIN Sales.SalesOrderDetail  AS d  ON h.SalesOrderID   = d.SalesOrderID
LEFT JOIN Sales.CreditCard   AS cc ON h.CreditCardID   = cc.CreditCardID
WHERE h.OnlineOrderFlag = 1
