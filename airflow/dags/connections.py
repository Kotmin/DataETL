from __future__ import annotations

import os

import psycopg2
import psycopg2.extensions
import pyodbc


def mssql_conn() -> pyodbc.Connection:
    dsn = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.environ['MSSQL_HOST']},{os.environ['MSSQL_PORT']};"
        f"DATABASE={os.environ['MSSQL_DB']};"
        f"UID=sa;PWD={os.environ['MSSQL_SA_PASSWORD']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(dsn)


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
    )
