"""Carga de tablas a SQLite."""
import sqlite3
from pathlib import Path

import pandas as pd


def connect(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def save_table(df, table, db_path, mode="replace"):
    with connect(db_path) as conn:
        df.to_sql(table, conn, if_exists=mode, index=False)


def read_table(table, db_path):
    with connect(db_path) as conn:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            return pd.DataFrame()
        return pd.read_sql(f"SELECT * FROM {table}", conn)


def query(sql, db_path, params=()):
    with connect(db_path) as conn:
        return pd.read_sql(sql, conn, params=params)
