import sys
from datetime import datetime, date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "airflow" / "dags"))

from etl_dim_sales_territory import transform as _transform_territory
from etl_dim_customer import transform as _transform_customer
import etl_fact_online_sales as _fact_module


class _FakeXCom:
    def __init__(self, raw_rows):
        self._rows = raw_rows

    def xcom_pull(self, task_ids, key):
        return self._rows

    def xcom_push(self, key, value):
        self._pushed = (key, value)


_PM_LOOKUP = {"None": 0, "ColonialVoice": 1, "Distinguish": 2, "SuperiorCard": 3, "Vista": 4}
_GEOG_LOOKUP = {("seattle", "wa", "us"): 42, ("paris", "75", "fr"): 7}


def _run(fn, raw_rows):
    ti = _FakeXCom(raw_rows)
    fn(**{"ti": ti})
    assert ti._pushed[0] == "transformed_rows"
    return ti._pushed[1]


def _run_customer(raw_rows):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("Seattle", "WA", "US", 42),
        ("Paris",   "75", "FR", 7),
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    ti = _FakeXCom(raw_rows)
    with patch.object(sys.modules["etl_dim_customer"], "pg_conn", return_value=mock_conn), \
         patch.object(sys.modules["etl_dim_customer"], "PGParams"):
        sys.modules["etl_dim_customer"].transform(**{"ti": ti})
    assert ti._pushed[0] == "transformed_rows"
    return ti._pushed[1]


def _run_fact(raw_rows):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = list(_PM_LOOKUP.items())
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    ti = _FakeXCom(raw_rows)
    with patch.object(_fact_module, "pg_conn", return_value=mock_conn), \
         patch.object(_fact_module, "PGParams"):
        _fact_module.transform(**{"ti": ti})
    assert ti._pushed[0] == "transformed_rows"
    return ti._pushed[1]


_TERRITORY_RAW = [
    {"SalesTerritoryKey": 1, "SalesTerritoryName": " Northwest ", "CountryKey": 2, "CountryName": "United States", "CountryCode": "US"},
    {"SalesTerritoryKey": 6, "SalesTerritoryName": "France", "CountryKey": 3, "CountryName": "France", "CountryCode": "FR"},
]

_CUSTOMER_RAW = [
    {"CustomerID": 11000, "FirstName": "Jon", "LastName": "Yang", "City": "Seattle", "StateProvinceCode": "WA", "CountryRegionCode": "US"},
    {"CustomerID": 11001, "FirstName": None, "LastName": None, "City": None, "StateProvinceCode": None, "CountryRegionCode": None},
]

_FACT_RAW = [
    {
        "OrderKey": "SO43659",
        "OrderLineNumber": 1,
        "CustomerID": 11000,
        "ProductID": 776,
        "TerritoryID": 1,
        "ShipMethodID": 2,
        "CardType": "Vista",
        "OrderDate": datetime(2022, 5, 15, 0, 0),
        "ShipDate": datetime(2022, 5, 20, 0, 0),
        "OrderQty": 1,
        "UnitPrice": 2024.994,
        "UnitPriceDiscount": 0.10,
        "LineTotal": 1822.4946,
        "Freight": 50.0,
        "SubTotal": 1822.4946,
        "ProductCost": 1200.0,
    },
    {
        "OrderKey": "SO43659",
        "OrderLineNumber": 2,
        "CustomerID": 11000,
        "ProductID": 777,
        "TerritoryID": 1,
        "ShipMethodID": 2,
        "CardType": "Vista",
        "OrderDate": datetime(2022, 5, 15, 0, 0),
        "ShipDate": None,
        "OrderQty": 2,
        "UnitPrice": 100.0,
        "UnitPriceDiscount": 0.0,
        "LineTotal": 200.0,
        "Freight": 50.0,
        "SubTotal": 2022.4946,
        "ProductCost": 60.0,
    },
]


def test_territory_renames_columns():
    result = _run(_transform_territory, _TERRITORY_RAW)
    for row in result:
        assert "sales_territory_key" in row
        assert "sales_territory_name" in row
        assert "country_key" in row
        assert "country_name" in row
        assert "country_code" in row


def test_territory_trims_whitespace():
    result = _run(_transform_territory, _TERRITORY_RAW)
    row = next(r for r in result if r["sales_territory_key"] == 1)
    assert row["sales_territory_name"] == "Northwest"


def test_territory_row_count_preserved():
    result = _run(_transform_territory, _TERRITORY_RAW)
    assert len(result) == len(_TERRITORY_RAW)


def test_customer_renames_columns():
    result = _run_customer(_CUSTOMER_RAW)
    for row in result:
        assert "customer_key" in row
        assert "first_name" in row
        assert "last_name" in row
        assert "geography_key" in row


def test_customer_no_account_number_or_full_name():
    result = _run_customer(_CUSTOMER_RAW)
    for row in result:
        assert "account_number" not in row
        assert "full_name" not in row
        assert "territory_key" not in row


def test_customer_resolves_geography_key():
    result = _run_customer(_CUSTOMER_RAW)
    row = next(r for r in result if r["customer_key"] == 11000)
    assert row["geography_key"] == 42


def test_customer_null_geography_when_no_address():
    result = _run_customer(_CUSTOMER_RAW)
    row = next(r for r in result if r["customer_key"] == 11001)
    assert row["geography_key"] is None


def test_fact_composite_pk_fields():
    result = _run_fact(_FACT_RAW)
    assert "order_key" in result[0]
    assert "order_line_number" in result[0]


def test_fact_computes_date_key_from_datetime():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["order_line_number"] == 1)
    assert row["order_date_key"] == 20220515


def test_fact_ship_date_key_null_when_no_shipdate():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["order_line_number"] == 2)
    assert row["ship_date_key"] is None


def test_fact_computes_discount_amount():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["order_line_number"] == 1)
    assert row["discount_amount"] == round(2024.994 * 0.10, 2)


def test_fact_computes_discount_pctg():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["order_line_number"] == 1)
    assert row["discount_pctg"] == 10


def test_fact_computes_transaction_price():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["order_line_number"] == 1)
    assert row["transaction_price"] == round(2024.994 * 0.90, 2)


def test_fact_computes_delivery_cost_proportional():
    result = _run_fact(_FACT_RAW)
    row1 = next(r for r in result if r["order_line_number"] == 1)
    assert row1["delivery_cost"] is not None
    assert row1["delivery_cost"] > 0


def test_fact_resolves_payment_method_key():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["order_line_number"] == 1)
    assert row["payment_method_key"] == 4


def test_fact_order_channel_always_online():
    result = _run_fact(_FACT_RAW)
    assert all(r["channel_key"] == 1 for r in result)


def test_fact_row_count_preserved():
    result = _run_fact(_FACT_RAW)
    assert len(result) == len(_FACT_RAW)


def test_fact_no_old_columns():
    result = _run_fact(_FACT_RAW)
    for row in result:
        assert "sales_order_key" not in row
        assert "order_qty" not in row
        assert "unit_price" not in row
        assert "sub_total" not in row
        assert "line_total" not in row
        assert "territory_key" not in row
