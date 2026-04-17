import sys
from datetime import datetime, date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "airflow" / "dags"))

from etl_dim_territory import transform as _transform_territory
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


def _run(fn, raw_rows):
    ti = _FakeXCom(raw_rows)
    fn(**{"ti": ti})
    assert ti._pushed[0] == "transformed_rows"
    return ti._pushed[1]


def _run_fact(raw_rows):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = list(_PM_LOOKUP.items())
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    ti = _FakeXCom(raw_rows)
    with patch.object(_fact_module, "_pg_conn", return_value=mock_conn):
        _fact_module.transform(**{"ti": ti})
    assert ti._pushed[0] == "transformed_rows"
    return ti._pushed[1]


_TERRITORY_RAW = [
    {"TerritoryID": 1, "TerritoryName": " Northwest ", "CountryRegionCode": "US", "RegionGroup": "North America"},
    {"TerritoryID": 6, "TerritoryName": "France", "CountryRegionCode": "FR", "RegionGroup": "Europe"},
]

_CUSTOMER_RAW = [
    {
        "CustomerID": 11000,
        "AccountNumber": "AW00011000",
        "FirstName": "Jon",
        "LastName": "Yang",
        "FullName": "Jon Yang",
        "TerritoryID": 1,
        "TerritoryName": "Northwest",
    },
    {
        "CustomerID": 11001,
        "AccountNumber": "AW00011001",
        "FirstName": None,
        "LastName": None,
        "FullName": None,
        "TerritoryID": None,
        "TerritoryName": None,
    },
]

_FACT_RAW = [
    {
        "SalesOrderKey": 1,
        "OrderDate": datetime(2022, 5, 15, 0, 0),
        "CustomerID": 11000,
        "ProductID": 776,
        "TerritoryID": 1,
        "ShipToAddressID": 1001,
        "ShipMethodID": 2,
        "CardType": "Vista",
        "OrderQty": 1,
        "UnitPrice": 2024.994,
        "UnitPriceDiscount": 0.0,
        "LineTotal": 2024.994,
        "SubTotal": 2024.994,
        "TaxAmt": 162.0,
        "Freight": 50.0,
        "TotalDue": 2236.994,
    },
    {
        "SalesOrderKey": 2,
        "OrderDate": "2023-11-01 00:00:00",
        "CustomerID": None,
        "ProductID": 777,
        "TerritoryID": None,
        "ShipToAddressID": None,
        "ShipMethodID": 1,
        "CardType": "None",
        "OrderQty": 2,
        "UnitPrice": 100.0,
        "UnitPriceDiscount": 0.0,
        "LineTotal": 200.0,
        "SubTotal": None,
        "TaxAmt": None,
        "Freight": None,
        "TotalDue": None,
    },
]


def test_territory_renames_columns():
    result = _run(_transform_territory, _TERRITORY_RAW)
    for row in result:
        assert "territory_key" in row
        assert "territory_name" in row
        assert "country_region_code" in row
        assert "region_group" in row


def test_territory_trims_whitespace():
    result = _run(_transform_territory, _TERRITORY_RAW)
    row = next(r for r in result if r["territory_key"] == 1)
    assert row["territory_name"] == "Northwest"


def test_territory_row_count_preserved():
    result = _run(_transform_territory, _TERRITORY_RAW)
    assert len(result) == len(_TERRITORY_RAW)


def test_customer_renames_columns():
    result = _run(_transform_customer, _CUSTOMER_RAW)
    for row in result:
        assert "customer_key" in row
        assert "account_number" in row
        assert "first_name" in row
        assert "last_name" in row
        assert "full_name" in row
        assert "territory_key" in row
        assert "territory_name" in row


def test_customer_preserves_nulls():
    result = _run(_transform_customer, _CUSTOMER_RAW)
    anon = next(r for r in result if r["customer_key"] == 11001)
    assert anon["first_name"] is None
    assert anon["last_name"] is None
    assert anon["territory_key"] is None


def test_customer_strips_account_number():
    result = _run(_transform_customer, _CUSTOMER_RAW)
    row = next(r for r in result if r["customer_key"] == 11000)
    assert row["account_number"] == "AW00011000"


def test_fact_computes_date_key_from_datetime():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["sales_order_key"] == 1)
    assert row["order_date_key"] == 20220515


def test_fact_computes_date_key_from_string():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["sales_order_key"] == 2)
    assert row["order_date_key"] == 20231101


def test_fact_preserves_nulls_for_header_fields():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["sales_order_key"] == 2)
    assert row["sub_total"] is None
    assert row["tax_amt"] is None
    assert row["freight"] is None
    assert row["total_due"] is None


def test_fact_row_count_preserved():
    result = _run_fact(_FACT_RAW)
    assert len(result) == len(_FACT_RAW)


def test_fact_resolves_payment_method_key():
    result = _run_fact(_FACT_RAW)
    vista_row = next(r for r in result if r["sales_order_key"] == 1)
    assert vista_row["payment_method_key"] == 4

    none_row = next(r for r in result if r["sales_order_key"] == 2)
    assert none_row["payment_method_key"] == 0


def test_fact_maps_geography_and_delivery_keys():
    result = _run_fact(_FACT_RAW)
    row = next(r for r in result if r["sales_order_key"] == 1)
    assert row["geography_key"] == 1001
    assert row["delivery_method_key"] == 2


def test_fact_order_channel_always_online():
    result = _run_fact(_FACT_RAW)
    assert all(r["order_channel_key"] == 1 for r in result)
