import os
import pytest
import pyodbc
import psycopg2


def _mssql_dsn():
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.environ.get('MSSQL_HOST', 'localhost')},"
        f"{os.environ.get('MSSQL_PORT', '1433')};"
        f"DATABASE={os.environ.get('MSSQL_DB', 'AdventureWorks2025')};"
        f"UID=sa;PWD={os.environ.get('MSSQL_SA_PASSWORD', '')};"
        "TrustServerCertificate=yes;"
    )


@pytest.fixture(scope="session")
def mssql_conn():
    if not os.environ.get("MSSQL_SA_PASSWORD"):
        pytest.skip("MSSQL_SA_PASSWORD not set — skipping MSSQL tests")
    try:
        conn = pyodbc.connect(_mssql_dsn(), timeout=5)
    except Exception as exc:
        pytest.skip(f"Cannot connect to SQL Server: {exc}")
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def pg_conn():
    required = ("PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD")
    if not all(os.environ.get(k) for k in required):
        pytest.skip("PostgreSQL env vars not set — skipping PG tests")
    try:
        conn = psycopg2.connect(
            host=os.environ["PG_HOST"],
            port=os.environ["PG_PORT"],
            dbname=os.environ["PG_DB"],
            user=os.environ["PG_USER"],
            password=os.environ["PG_PASSWORD"],
            connect_timeout=5,
        )
    except Exception as exc:
        pytest.skip(f"Cannot connect to PostgreSQL: {exc}")
    yield conn
    conn.close()
