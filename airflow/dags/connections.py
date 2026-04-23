from __future__ import annotations

import os
from dataclasses import dataclass, field

import psycopg2
import psycopg2.extensions
import pyodbc


@dataclass
class MSSQLParams:
    host: str
    port: str
    database: str
    password: str
    username: str = "sa"
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_server_certificate: bool = True

    @classmethod
    def from_env(cls) -> MSSQLParams:
        return cls(
            host=os.environ["MSSQL_HOST"],
            port=os.environ["MSSQL_PORT"],
            database=os.environ["MSSQL_DB"],
            password=os.environ["MSSQL_SA_PASSWORD"],
        )


@dataclass
class PGParams:
    host: str
    port: str
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> PGParams:
        return cls(
            host=os.environ["PG_HOST"],
            port=os.environ["PG_PORT"],
            dbname=os.environ["PG_DB"],
            user=os.environ["PG_USER"],
            password=os.environ["PG_PASSWORD"],
        )


def mssql_conn(params: MSSQLParams) -> pyodbc.Connection:
    dsn = (
        f"DRIVER={{{params.driver}}};"
        f"SERVER={params.host},{params.port};"
        f"DATABASE={params.database};"
        f"UID={params.username};PWD={params.password};"
        f"TrustServerCertificate={'yes' if params.trust_server_certificate else 'no'};"
    )
    return pyodbc.connect(dsn)


def pg_conn(params: PGParams) -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=params.host,
        port=params.port,
        dbname=params.dbname,
        user=params.user,
        password=params.password,
    )
