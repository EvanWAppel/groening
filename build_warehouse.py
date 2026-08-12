"""Build the Groening DuckDB warehouse from Portland-metro open data.

A near-exact port of Elvis (Las Vegas). Upstream sources feed the ``raw`` schema
of ``portland.duckdb``, which dbt then transforms into staging + mart models.
All city-specific endpoints/FIPS/stations live in ``city_config.py``.

Vertical slice (first topic):
    building_permits   PortlandMaps "Residential Building Permits" (MapServer
                       layer 89), point geometry reprojected to WGS84, with
                       valuation, new-unit counts, and issue dates.

Usage:
    uv run python build_warehouse.py
"""

import json
import logging
import socket
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

import city_config as cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_warehouse")


# Some upstreams (notably aqs.epa.gov) advertise an AAAA record but have broken
# IPv6, so a default connect hangs in SYN_SENT until timeout. Prefer IPv4 for all
# fetches, falling back to whatever's available if a host is IPv4-less.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first(*args, **kwargs):
    results = _orig_getaddrinfo(*args, **kwargs)
    return [r for r in results if r[0] == socket.AF_INET] or results


# Deliberate monkeypatch: the signature intentionally differs from the stdlib
# stub, so the type checker can't reconcile it. See the EPA-AQS IPv6 gotcha above.
socket.getaddrinfo = _ipv4_first  # ty: ignore[invalid-assignment]

DB_PATH = Path(__file__).parent / "portland.duckdb"
PAGE_SIZE = cfg.PAGE_SIZE


# --------------------------------------------------------------------------- #
# Generic ArcGIS fetch (FeatureServer or MapServer, any org, optional TLS skip) #
# --------------------------------------------------------------------------- #
def _get_json(url: str, ctx: ssl.SSLContext | None = None) -> dict:
    with urllib.request.urlopen(url, timeout=180, context=ctx) as resp:
        return json.load(resp)


def _ssl_ctx(verify: bool) -> ssl.SSLContext | None:
    """None keeps default verification; a permissive ctx tolerates broken certs.

    Only pass ``verify=False`` for a specific host known to ship a bad cert, and
    log loudly when you do — never disable verification globally.
    """
    if verify:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_layer(
    base_url: str,
    geometry: bool = False,
    centroid: bool = False,
    out_sr: int = 4326,
    ssl_verify: bool = True,
    date_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch all attribute rows of an ArcGIS layer into a DataFrame, paginated.

    Unlike the Elvis original (which composed ``org/service/FeatureServer/layer``),
    this takes the *full* layer base URL so ``city_config`` can point at either
    FeatureServer or MapServer endpoints across orgs — Portland mixes both.

    Args:
        base_url: full ArcGIS layer URL, e.g. ``.../MapServer/89``.
        geometry: also pull point geometry into ``longitude``/``latitude`` columns.
        centroid: for polygon layers, pull the centroid into ``longitude``/``latitude``.
        out_sr: spatial reference to reproject geometry into (4326 = WGS84).
        ssl_verify: pass ``False`` only for a specific broken-TLS host (logged).
        date_columns: extra columns to force to ISO date strings beyond the
            esri date fields auto-detected from layer metadata.
    """
    ctx = _ssl_ctx(ssl_verify)
    if not ssl_verify:
        host = urllib.parse.urlparse(base_url).netloc
        log.warning("TLS verification DISABLED for %s (broken cert host)", host)

    meta = _get_json(f"{base_url}?f=json", ctx)
    page = min(meta.get("maxRecordCount") or PAGE_SIZE, PAGE_SIZE)
    esri_date_fields = {
        f["name"] for f in meta.get("fields", []) if f.get("type") == "esriFieldTypeDate"
    }
    date_cols = set(date_columns or []) | esri_date_fields

    rows: list[dict] = []
    offset = 0
    while True:
        query = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true" if geometry else "false",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": page,
        }
        if centroid:
            query["returnCentroid"] = "true"
        if geometry or centroid:
            query["outSR"] = out_sr
        params = urllib.parse.urlencode(query)
        data = _get_json(f"{base_url}/query?{params}", ctx)
        feats = data.get("features", [])
        if not feats:
            break
        for feat in feats:
            attrs = dict(feat["attributes"])
            point = feat.get("geometry") if geometry else feat.get("centroid")
            if point:
                attrs["longitude"] = point.get("x")
                attrs["latitude"] = point.get("y")
            rows.append(attrs)
        offset += len(feats)
        log.info("  %s: %d rows fetched", base_url.rsplit("/services/", 1)[-1], len(rows))
        if len(feats) < page:
            break

    df = pd.DataFrame(rows)
    for col in df.columns:
        if col in date_cols:
            s = df[col]
            if pd.api.types.is_numeric_dtype(s):
                dt = pd.to_datetime(s, unit="ms", errors="coerce")
            else:
                dt = pd.to_datetime(s, errors="coerce")
            df[col] = dt.dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def fetch_features(
    base_url: str,
    where: str = "1=1",
    out_fields: str = "*",
    geometry: bool = True,
    out_sr: int = 4326,
    ssl_verify: bool = True,
) -> list[tuple[dict, dict | None]]:
    """Paginate any ArcGIS layer URL, returning (attributes, geometry) per feature.

    The lower-level counterpart to :func:`fetch_layer`, for topics that need the
    raw geometry (e.g. polygon centroids or point-in-polygon joins).
    """
    ctx = _ssl_ctx(ssl_verify)
    if not ssl_verify:
        host = urllib.parse.urlparse(base_url).netloc
        log.warning("TLS verification DISABLED for %s (broken cert host)", host)

    meta = _get_json(f"{base_url}?f=json", ctx)
    page = min(meta.get("maxRecordCount") or PAGE_SIZE, PAGE_SIZE)
    out: list[tuple[dict, dict | None]] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode(
            {
                "where": where,
                "outFields": out_fields,
                "returnGeometry": "true" if geometry else "false",
                "outSR": out_sr,
                "f": "json",
                "resultOffset": offset,
                "resultRecordCount": page,
            }
        )
        feats = _get_json(f"{base_url}/query?{params}", ctx).get("features", [])
        if not feats:
            break
        out.extend((f.get("attributes", {}), f.get("geometry")) for f in feats)
        offset += len(feats)
        if len(feats) < page:
            break
    log.info("  %s: %d features", base_url.rsplit("/services/", 1)[-1], len(out))
    return out


def _centroid(geom: dict | None) -> tuple[float | None, float | None]:
    """(lon, lat) for a point, or the vertex-average of a polygon's outer ring."""
    if not geom:
        return (None, None)
    if "x" in geom:
        return (geom.get("x"), geom.get("y"))
    rings = geom.get("rings")
    if rings:
        ext = rings[0]
        pts = ext[:-1] if len(ext) > 1 and ext[0] == ext[-1] else ext
        if pts:
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return (None, None)


def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    """Ray-casting test: is (lon, lat) inside the polygon exterior ``ring``?"""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _epoch_to_date(ms) -> str | None:
    """ArcGIS epoch-millisecond timestamp -> ISO date string (None if missing)."""
    if ms is None or (isinstance(ms, float) and pd.isna(ms)):
        return None
    dt = pd.to_datetime(ms, unit="ms", errors="coerce")
    # AQS/ArcGIS use a 1900 sentinel for "no date"; treat pre-1990 as null.
    if pd.isna(dt) or dt.year < 1990:
        return None
    return dt.strftime("%Y-%m-%d")


def _urlopen(url: str, headers: dict | None = None, timeout: int = 300):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers or {}), timeout=timeout
    )


# --------------------------------------------------------------------------- #
# Warehouse materialization                                                    #
# --------------------------------------------------------------------------- #
def load_raw(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError(
            f"raw.{table}: fetch returned zero rows — refusing to ship an empty page"
        )
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.register("_df", df)
    con.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM _df")
    con.unregister("_df")
    log.info("Loaded raw.%s: %d rows, %d cols", table, len(df), len(df.columns))


# --------------------------------------------------------------------------- #
# Topic fetchers                                                               #
# --------------------------------------------------------------------------- #
def fetch_building_permits() -> pd.DataFrame:
    """PortlandMaps residential building permits (point geometry, WGS84)."""
    log.info("Fetching building_permits from %s ...", cfg.PERMITS_LAYER_URL)
    return fetch_layer(cfg.PERMITS_LAYER_URL, geometry=True)


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    try:
        log.info("Fetching building_permits (PortlandMaps ArcGIS) ...")
        load_raw(con, "building_permits", fetch_building_permits())
    finally:
        con.close()
    log.info("Warehouse build complete: %s", DB_PATH)


if __name__ == "__main__":
    main()
