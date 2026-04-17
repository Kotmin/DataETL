#!/usr/bin/env python3
import json
import os
from typing import Literal

import pyodbc
import psycopg2
import psycopg2.extras
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sql-query")

_CONNECTIONS = {
    "mssql": lambda: pyodbc.connect(os.environ["MSSQL_CONN"]),
    "postgres": lambda: psycopg2.connect(os.environ["PG_CONN"]),
}


def _fetch(conn_factory, sql: str) -> str:
    try:
        conn = conn_factory()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            if cursor.description is None:
                conn.commit()
                return json.dumps({"affected": cursor.rowcount})
            columns = [d[0] for d in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return json.dumps(rows, default=str)
        finally:
            conn.close()
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
def query_sql(connection: Literal["mssql", "postgres"], sql: str) -> str:
    """Execute SQL against the named connection and return JSON results.

    connection: "mssql" for SQL Server source, "postgres" for PostgreSQL warehouse.
    sql: any valid SQL statement.
    Returns a JSON array of row objects, or {"error": "..."} on failure.
    """
    factory = _CONNECTIONS.get(connection)
    if factory is None:
        return json.dumps({"error": f"Unknown connection '{connection}'. Use 'mssql' or 'postgres'."})
    return _fetch(factory, sql)


if __name__ == "__main__":
    mcp.run(transport="stdio")
