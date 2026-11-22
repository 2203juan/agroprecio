"""Carga de tablas a SQLite."""
import sqlite3
from pathlib import Path

import pandas as pd


def connect(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def table_exists(conn, table):
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def add_missing_columns(conn, table, df):
    """Si la tabla ya existe y el DataFrame trae columnas nuevas, las agrega vacías
    para poder seguir acumulando el historial."""
    existing = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
    for col in df.columns:
        if col not in existing:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}"')


def save_table(df, table, db_path, mode="replace"):
    with connect(db_path) as conn:
        if mode == "append" and table_exists(conn, table):
            add_missing_columns(conn, table, df)
        df.to_sql(table, conn, if_exists=mode, index=False)


def read_table(table, db_path):
    with connect(db_path) as conn:
        if not table_exists(conn, table):
            return pd.DataFrame()
        return pd.read_sql(f"SELECT * FROM {table}", conn)


def query(sql, db_path, params=()):
    with connect(db_path) as conn:
        return pd.read_sql(sql, conn, params=params)
