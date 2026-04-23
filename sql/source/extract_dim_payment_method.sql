SELECT 0 AS PaymentMethodKey, 'None' AS PaymentMethodName
UNION ALL
SELECT
    ROW_NUMBER() OVER (ORDER BY CardType) AS PaymentMethodKey,
    CardType                              AS PaymentMethodName
FROM (SELECT DISTINCT CardType FROM Sales.CreditCard) AS t
