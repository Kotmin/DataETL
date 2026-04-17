from pathlib import Path

EXTRACT_SQL = (Path(__file__).parents[1] / "sql" / "source" / "extract_dim_product.sql").read_text()

EXPECTED_COLUMNS = {
    "ProductID", "ProductNumber", "ProductName",
    "ProductSubcategoryID", "SubcategoryName",
    "ProductCategoryID", "CategoryName",
}


def test_extract_returns_rows(mssql_conn):
    cursor = mssql_conn.cursor()
    cursor.execute(EXTRACT_SQL)
    rows = cursor.fetchall()
    assert len(rows) > 0


def test_extract_column_names(mssql_conn):
    cursor = mssql_conn.cursor()
    cursor.execute(EXTRACT_SQL)
    columns = {d[0] for d in cursor.description}
    assert EXPECTED_COLUMNS == columns


def test_extract_no_null_product_id(mssql_conn):
    cursor = mssql_conn.cursor()
    cursor.execute(EXTRACT_SQL)
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    null_ids = [r for r in rows if r["ProductID"] is None]
    assert len(null_ids) == 0


def test_extract_no_null_product_name(mssql_conn):
    cursor = mssql_conn.cursor()
    cursor.execute(EXTRACT_SQL)
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    null_names = [r for r in rows if not r["ProductName"]]
    assert len(null_names) == 0


def test_extract_row_count_reasonable(mssql_conn):
    cursor = mssql_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Production.Product")
    source_count = cursor.fetchone()[0]
    assert source_count > 0

    cursor.execute(EXTRACT_SQL)
    extract_count = len(cursor.fetchall())
    assert extract_count == source_count
