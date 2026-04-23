import pytest


@pytest.mark.integration
def test_load_row_count_matches_source(mssql_conn, pg_conn):
    mssql_cur = mssql_conn.cursor()
    mssql_cur.execute("SELECT COUNT(*) FROM Production.Product")
    source_count = mssql_cur.fetchone()[0]

    pg_cur = pg_conn.cursor()
    pg_cur.execute("SELECT COUNT(*) FROM dim.dim_product")
    load_count = pg_cur.fetchone()[0]

    assert load_count > 0, "dim.dim_product is empty — run the etl_dim_product DAG first"
    assert load_count == source_count, (
        f"Row count mismatch: source={source_count}, warehouse={load_count}"
    )


@pytest.mark.integration
def test_load_product_key_is_unique(pg_conn):
    cur = pg_conn.cursor()
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT product_key) FROM dim.dim_product")
    total, distinct = cur.fetchone()
    assert total == distinct, f"Duplicate product_key detected: total={total}, distinct={distinct}"


@pytest.mark.integration
def test_load_no_null_product_keys(pg_conn):
    cur = pg_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dim.dim_product WHERE product_key IS NULL")
    null_count = cur.fetchone()[0]
    assert null_count == 0, f"{null_count} rows with NULL product_key"


@pytest.mark.integration
def test_load_no_null_product_codes(pg_conn):
    cur = pg_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dim.dim_product WHERE product_code IS NULL OR TRIM(product_code) = ''")
    bad = cur.fetchone()[0]
    assert bad == 0, f"{bad} rows with empty or NULL product_code"


@pytest.mark.integration
def test_load_no_null_product_names(pg_conn):
    cur = pg_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dim.dim_product WHERE product_name IS NULL OR TRIM(product_name) = ''")
    bad = cur.fetchone()[0]
    assert bad == 0, f"{bad} rows with empty or NULL product_name"
