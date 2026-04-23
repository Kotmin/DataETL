SELECT
    ShipMethodID    AS DeliveryMethodKey,
    Name            AS DeliveryMethodName,
    ShipBase,
    ShipRate
FROM Purchasing.ShipMethod
