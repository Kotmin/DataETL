import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

EXPECTED_SOURCE_TABLES = [
    ("Sales", "Customer"),
    ("Person", "Person"),
    ("Person", "Address"),
    ("Person", "StateProvince"),
    ("Person", "CountryRegion"),
    ("Production", "Product"),
    ("Production", "ProductSubcategory"),
    ("Production", "ProductCategory"),
    ("Sales", "SalesOrderHeader"),
    ("Sales", "SalesOrderDetail"),
    ("Sales", "CreditCard"),
    ("Purchasing", "ShipMethod"),
    ("Production", "ProductCostHistory"),
]

EXPECTED_WAREHOUSE_TABLES = [
    ("dim", "dim_date"),
    ("dim", "dim_order_channel"),
    ("dim", "dim_sales_territory"),
    ("dim", "dim_delivery_method"),
    ("dim", "dim_payment_method"),
    ("dim", "dim_geography"),
    ("dim", "dim_product"),
    ("dim", "dim_customer"),
    ("fact", "fact_online_sales"),
]

_TEST_PRODUCT_NUMBER = "TEST-QA-001"


def _run_etl(*args):
    result = subprocess.run(
        [str(REPO / ".venv/bin/python"), str(REPO / "app/main.py"), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert result.returncode == 0, f"ETL run failed:\n{result.stderr}"


def _warehouse_row_counts(pg_conn):
    pg_conn.rollback()
    cursor = pg_conn.cursor()
    counts = {}
    for schema, table in EXPECTED_WAREHOUSE_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
        counts[(schema, table)] = cursor.fetchone()[0]
    return counts


@pytest.mark.qa
def test_all_expected_source_tables_exist_in_adventureworks(mssql_conn):
    cursor = mssql_conn.cursor()
    for schema, table in EXPECTED_SOURCE_TABLES:
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
            schema,
            table,
        )
        count = cursor.fetchone()[0]
        assert count == 1, f"Source table not found: {schema}.{table}"


@pytest.mark.qa
def test_key_columns_present_in_source_tables(mssql_conn):
    required = {
        ("Production", "Product"): ["ProductID", "ProductNumber", "Name"],
        ("Sales", "SalesOrderHeader"): ["SalesOrderID", "SalesOrderNumber", "CustomerID", "OnlineOrderFlag"],
        ("Sales", "SalesOrderDetail"): ["SalesOrderDetailID", "SalesOrderID", "ProductID", "OrderQty"],
        ("Sales", "Customer"): ["CustomerID", "PersonID"],
    }
    cursor = mssql_conn.cursor()
    for (schema, table), columns in required.items():
        for column in columns:
            cursor.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?",
                schema,
                table,
                column,
            )
            assert cursor.fetchone()[0] == 1, f"Missing column: {schema}.{table}.{column}"


@pytest.mark.qa
def test_all_expected_warehouse_tables_exist_in_postgres(pg_conn):
    cursor = pg_conn.cursor()
    for schema, table in EXPECTED_WAREHOUSE_TABLES:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (schema, table),
        )
        count = cursor.fetchone()[0]
        assert count == 1, f"Warehouse table not found: {schema}.{table}"


@pytest.mark.qa
def test_every_source_product_is_present_in_warehouse(mssql_conn, pg_conn):
    mssql_cursor = mssql_conn.cursor()
    mssql_cursor.execute("SELECT ProductID FROM Production.Product")
    source_ids = {row[0] for row in mssql_cursor.fetchall()}

    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT product_key FROM dim.dim_product")
    warehouse_ids = {row[0] for row in pg_cursor.fetchall()}

    missing = source_ids - warehouse_ids
    assert not missing, (
        f"{len(missing)} source products are absent from the warehouse. "
        f"Sample missing IDs: {sorted(missing)[:10]}"
    )


@pytest.mark.qa
def test_running_full_pipeline_twice_produces_identical_row_counts(pg_conn):
    _run_etl("run", "--all")
    counts_first_run = _warehouse_row_counts(pg_conn)

    _run_etl("run", "--all")
    counts_second_run = _warehouse_row_counts(pg_conn)

    for schema, table in EXPECTED_WAREHOUSE_TABLES:
        key = (schema, table)
        assert counts_first_run[key] == counts_second_run[key], (
            f"{schema}.{table}: first run produced {counts_first_run[key]} rows, "
            f"second run produced {counts_second_run[key]} rows — "
            f"TRUNCATE+INSERT should yield identical counts on each run"
        )


@pytest.mark.qa
def test_new_source_product_syncs_to_warehouse_without_duplicating_existing_rows(mssql_conn, pg_conn):
    pg_cursor = pg_conn.cursor()
    mssql_cursor = mssql_conn.cursor()

    pg_cursor.execute("SELECT COUNT(*) FROM dim.dim_product")
    warehouse_count_before_new_product = pg_cursor.fetchone()[0]

    mssql_cursor.execute(
        "INSERT INTO Production.Product "
        "(Name, ProductNumber, SafetyStockLevel, ReorderPoint, "
        "StandardCost, ListPrice, DaysToManufacture, SellStartDate) "
        "VALUES (?, ?, 0, 0, 0.00, 0.00, 0, GETDATE())",
        "QA Test Product",
        _TEST_PRODUCT_NUMBER,
    )
    mssql_conn.commit()

    try:
        _run_etl("run", "--dag", "etl_dim_product")

        pg_conn.rollback()
        pg_cursor.execute("SELECT COUNT(*) FROM dim.dim_product")
        warehouse_count_after_sync = pg_cursor.fetchone()[0]

        pg_cursor.execute(
            "SELECT COUNT(*) FROM dim.dim_product WHERE product_code = %s",
            (_TEST_PRODUCT_NUMBER,),
        )
        occurrences_of_new_product = pg_cursor.fetchone()[0]

        assert warehouse_count_after_sync == warehouse_count_before_new_product + 1, (
            f"Expected {warehouse_count_before_new_product + 1} rows after one new product was added to the source, "
            f"but warehouse has {warehouse_count_after_sync} rows. "
            f"If higher than expected: the ETL duplicated existing rows instead of replacing them."
        )
        assert occurrences_of_new_product == 1, (
            f"New product {_TEST_PRODUCT_NUMBER!r} should appear exactly once in the warehouse, "
            f"found {occurrences_of_new_product} occurrences."
        )
    finally:
        mssql_cursor.execute(
            "DELETE FROM Production.Product WHERE ProductNumber = ?",
            _TEST_PRODUCT_NUMBER,
        )
        mssql_conn.commit()
        _run_etl("run", "--dag", "etl_dim_product")
