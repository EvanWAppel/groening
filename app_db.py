"""Shared DuckDB access for the Streamlit app.

The app reads the dbt-built marts straight out of ``portland.duckdb`` (materialized
by ``build_warehouse.py`` + ``dbt build``). No external database, no CSV snapshot —
the dbt output *is* what the app queries.
"""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "portland.duckdb"


@st.cache_resource
def _connection() -> duckdb.DuckDBPyConnection:
    """One shared read-only connection to the warehouse file."""
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    """Run a query and return a DataFrame.

    A fresh cursor per call keeps concurrent Streamlit reruns thread-safe while
    still sharing the single underlying connection.
    """
    return _connection().cursor().execute(sql).df()
