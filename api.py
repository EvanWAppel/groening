"""Read-only JSON serving layer (E8) over the DuckDB marts.

A small FastAPI app that exposes the dbt-built ``mart_*`` tables in
``portland.duckdb`` as JSON — a data *product* alongside the Streamlit
dashboard, not a replacement for it.

Design guarantees:
- **Read-only.** The warehouse is opened ``read_only=True`` and callers can only
  read whole marts; there is no arbitrary-SQL endpoint.
- **Marts only.** Only ``main.mart_*`` base tables are reachable. The ``raw.*``
  tables and ``stg_*`` staging views are never served.
- **No injection surface.** A requested name is served only if it appears in the
  live catalog of marts; anything else is a 404, so the name is never trusted raw.

Run locally::

    uv run uvicorn api:app --reload

The Railway deploy still serves only Streamlit; wiring this endpoint into the
deploy is a separate, later decision (see DECISIONS.md).
"""

import logging
from pathlib import Path
from typing import Annotated

import duckdb
from fastapi import Depends, FastAPI, HTTPException, Query

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "portland.duckdb"
MART_SCHEMA = "main"
MART_PREFIX = "mart_"
MAX_LIMIT = 10_000
DEFAULT_LIMIT = 100

app = FastAPI(
    title="Groening — Portland open-data marts",
    description="Read-only JSON access to the dbt-built marts behind the Groening field guide.",
    version="1.0.0",
)

_shared_con: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """One shared read-only connection to the baked warehouse.

    Overridden in tests (``app.dependency_overrides``) to point at a throwaway
    DuckDB so the suite never touches the real warehouse or live data.
    """
    global _shared_con
    if _shared_con is None:
        _shared_con = duckdb.connect(str(DB_PATH), read_only=True)
    return _shared_con


def list_marts(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Sorted names of the served marts: ``main.mart_*`` base tables.

    Pinned to ``current_database()`` as well as the ``main`` schema so that, if a
    second catalog is ever ``ATTACH``ed, its own ``main.mart_*`` tables can never
    leak in — the "marts only, from *our* warehouse" guarantee holds regardless.
    The ``_`` in ``mart_`` is escaped so it matches a literal underscore, not the
    LIKE any-single-char wildcard (else a table named ``martXYZ`` would slip in).
    """
    rows = con.cursor().execute(
        r"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = current_database()
          AND table_schema = ?
          AND table_type = 'BASE TABLE'
          AND table_name LIKE ? ESCAPE '\'
        ORDER BY table_name
        """,
        [MART_SCHEMA, MART_PREFIX.replace("_", r"\_") + "%"],
    ).fetchall()
    return [r[0] for r in rows]


def _require_mart(con: duckdb.DuckDBPyConnection, name: str) -> str:
    """Return ``name`` iff it is a live mart, else raise 404.

    Validating against the live catalog is what makes it safe to interpolate the
    name into a query below — an unknown or crafted name never reaches SQL.
    """
    if name not in list_marts(con):
        raise HTTPException(status_code=404, detail=f"No such mart: {name!r}")
    return name


def _qualified(name: str) -> str:
    """Fully-qualified, quote-escaped identifier for a validated mart name."""
    return f'{MART_SCHEMA}."{name.replace(chr(34), chr(34) * 2)}"'


def _row_count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    row = con.cursor().execute(f"SELECT count(*) FROM {table}").fetchone()
    return int(row[0]) if row else 0


Con = Annotated[duckdb.DuckDBPyConnection, Depends(get_connection)]


@app.get("/health")
def health(con: Con) -> dict:
    return {"status": "ok", "marts": len(list_marts(con))}


@app.get("/marts")
def marts(con: Con) -> dict:
    names = list_marts(con)
    out = [{"name": name, "rows": _row_count(con, _qualified(name))} for name in names]
    return {"count": len(out), "marts": out}


@app.get("/marts/{name}")
def mart_rows(
    name: str,
    con: Con,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    _require_mart(con, name)
    table = _qualified(name)
    total = _row_count(con, table)
    cur = con.cursor().execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", [limit, offset])
    # DuckDB's fetchall returns native Python scalars (int stays int, NULL -> None,
    # DATE -> date, DECIMAL -> Decimal); FastAPI's encoder renders dates/Decimals to
    # JSON. This avoids the pandas roundtrip, which coerces a nullable-int column to
    # float (e.g. a year 2024 -> 2024.0), and keeps this endpoint pandas-free.
    columns = [d[0] for d in cur.description]
    rows = [dict(zip(columns, record)) for record in cur.fetchall()]
    return {"name": name, "total": total, "count": len(rows), "limit": limit, "offset": offset, "rows": rows}


@app.get("/marts/{name}/schema")
def mart_schema(name: str, con: Con) -> dict:
    _require_mart(con, name)
    rows = con.cursor().execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_catalog = current_database()
          AND table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [MART_SCHEMA, name],
    ).fetchall()
    return {"name": name, "columns": [{"name": c, "type": t} for c, t in rows]}
