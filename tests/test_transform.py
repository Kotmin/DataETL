import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "airflow" / "dags"))

from etl_dim_product import transform as _transform_fn


def _make_raw_rows(overrides=None):
    base = [
        {
            "ProductID": 1,
            "ProductNumber": " BK-R93R-44 ",
            "ProductName": " Road-150 Red, 44 ",
            "ProductSubcategoryID": 2,
            "SubcategoryName": "Road Bikes",
            "ProductCategoryID": 1,
            "CategoryName": "Bikes",
        },
        {
            "ProductID": 2,
            "ProductNumber": "AR-5381",
            "ProductName": "Adjustable Race",
            "ProductSubcategoryID": None,
            "SubcategoryName": None,
            "ProductCategoryID": None,
            "CategoryName": None,
        },
    ]
    if overrides:
        base.extend(overrides)
    return base


class _FakeXCom:
    def __init__(self, raw_rows):
        self._rows = raw_rows

    def xcom_pull(self, task_ids, key):
        return self._rows

    def xcom_push(self, key, value):
        self._pushed = (key, value)


def _run_transform(raw_rows):
    ti = _FakeXCom(raw_rows)
    context = {"ti": ti}
    _transform_fn(**context)
    assert ti._pushed[0] == "transformed_rows"
    return ti._pushed[1]


def test_transform_renames_columns():
    result = _run_transform(_make_raw_rows())
    for row in result:
        assert "product_key" in row
        assert "product_code" in row
        assert "product_name" in row
        assert "subcategory_key" in row
        assert "subcategory_name" in row
        assert "category_key" in row
        assert "category_name" in row


def test_transform_trims_whitespace():
    result = _run_transform(_make_raw_rows())
    bike_row = next(r for r in result if r["product_key"] == 1)
    assert bike_row["product_code"] == "BK-R93R-44"
    assert bike_row["product_name"] == "Road-150 Red, 44"


def test_transform_preserves_nulls_for_no_subcategory():
    result = _run_transform(_make_raw_rows())
    no_sub = next(r for r in result if r["product_key"] == 2)
    assert no_sub["subcategory_key"] is None
    assert no_sub["subcategory_name"] is None
    assert no_sub["category_key"] is None
    assert no_sub["category_name"] is None


def test_transform_product_key_maps_from_product_id():
    result = _run_transform(_make_raw_rows())
    assert result[0]["product_key"] == 1
    assert result[1]["product_key"] == 2


def test_transform_row_count_preserved():
    raw = _make_raw_rows()
    result = _run_transform(raw)
    assert len(result) == len(raw)
