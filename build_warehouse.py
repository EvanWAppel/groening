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

import datetime
import io
import json
import logging
import math
import socket
import ssl
import urllib.parse
import urllib.request
import zipfile
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


def _webmerc_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """EPSG:3857 (Web Mercator) meters -> (lon, lat) in WGS84 degrees.

    PortlandMaps' short-term-rental report ships web_merc_x/web_merc_y rather
    than ArcGIS geometry with an outSR option, so we reproject in the ELT.
    """
    lon = x / 20037508.34 * 180.0
    lat = y / 20037508.34 * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return (lon, lat)


def _parse_usgs_dv(payload: dict) -> pd.DataFrame:
    """USGS NWIS daily-values JSON -> DataFrame(date, discharge_cfs, provisional).

    Drops the -999999 no-data sentinel; a day is provisional if its qualifiers
    include ``P``. Raises if the response carries no time series (bad site/param).
    """
    series = payload.get("value", {}).get("timeSeries", [])
    if not series:
        raise ValueError("USGS dv: response contained no timeSeries")
    rows: list[dict] = []
    for point in series[0]["values"][0]["value"]:
        value = float(point["value"])
        if value == -999999:
            continue
        rows.append(
            {
                "date": point["dateTime"][:10],
                "discharge_cfs": value,
                "provisional": "P" in point.get("qualifiers", []),
            }
        )
    if not rows:
        raise ValueError("USGS dv: every value was the no-data sentinel")
    return pd.DataFrame(rows)


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


def fetch_parks() -> pd.DataFrame:
    """PortlandMaps park boundaries (polygons); attach a WGS84 centroid per park.

    Portland publishes no park-level water-feature attribute, so — unlike Elvis —
    there is no has_water flag; the drop is logged below.
    """
    log.info("Fetching parks from %s ...", cfg.PARKS_LAYER_URL)
    log.warning("parks: Portland has no water-feature attribute — dropping has_water flag")
    feats = fetch_features(cfg.PARKS_LAYER_URL, geometry=True, out_sr=4326)
    rows: list[dict] = []
    for attrs, geom in feats:
        lon, lat = _centroid(geom)
        row = dict(attrs)
        row["longitude"] = lon
        row["latitude"] = lat
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_weather() -> pd.DataFrame:
    """NOAA GHCN-Daily for PDX. Keep the core elements; units handled in staging.

    TMAX/TMIN are tenths of °C, PRCP/SNOW/SNWD are mm (PRCP tenths of mm); the
    access-format CSV uses empty strings for missing, which pandas reads as NaN.
    """
    keep = {"STATION", "DATE", "PRCP", "SNOW", "SNWD", "TMAX", "TMIN"}
    log.info("Fetching weather from %s ...", cfg.WEATHER_URL)
    with _urlopen(cfg.WEATHER_URL, headers=cfg.USER_AGENT) as resp:
        df = pd.read_csv(resp, usecols=lambda c: c in keep, low_memory=False)
    log.info("  weather: %d daily rows", len(df))
    return df


def fetch_willamette() -> pd.DataFrame:
    """USGS NWIS daily discharge for the downtown Willamette gauge (cfs)."""
    end = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    url = cfg.USGS_DV_URL.format(end=end)
    log.info("Fetching willamette discharge from %s ...", url)
    payload = _get_json(url)
    df = _parse_usgs_dv(payload)
    log.info("  willamette: %d daily discharge points", len(df))
    return df


def fetch_str() -> pd.DataFrame:
    """Portland Accessory Short-Term Rental permits (paginated report CSV).

    Reprojects the report's web_merc_x/web_merc_y (EPSG:3857) to WGS84 and
    dedupes on (application_number, ivr_number).
    """
    frames: list[pd.DataFrame] = []
    page = 1
    while True:
        url = f"{cfg.STR_REPORT_URL}&format=csv&page={page}"
        with _urlopen(url, headers=cfg.USER_AGENT) as resp:
            page_df = pd.read_csv(io.BytesIO(resp.read()))
        if page_df.empty:
            break
        frames.append(page_df)
        log.info("  short_term_rentals: page %d (%d rows)", page, len(page_df))
        if len(page_df) < cfg.STR_PAGE_SIZE:
            break
        page += 1
    df = pd.concat(frames, ignore_index=True)
    # The CSV export ships UPPERCASE headers; normalize so downstream is stable.
    df.columns = [c.lower() for c in df.columns]
    df = df.drop_duplicates(subset=["application_number", "ivr_number"]).reset_index(drop=True)
    lonlat = [_webmerc_to_wgs84(x, y) for x, y in zip(df["web_merc_x"], df["web_merc_y"])]
    df["longitude"] = [p[0] for p in lonlat]
    df["latitude"] = [p[1] for p in lonlat]
    return df


def fetch_crime() -> pd.DataFrame:
    """PPB reported crime — concat the three crime-against ArcGIS point layers.

    Rolling trailing-12-month window; REPORTED_DATETIME (esri date) is
    normalized to a string by fetch_layer.
    """
    frames: list[pd.DataFrame] = []
    for label, url in cfg.CRIME_LAYER_URLS.items():
        log.info("Fetching crime layer %s ...", label)
        frames.append(fetch_layer(url, geometry=True))
    return pd.concat(frames, ignore_index=True)


def fetch_air_quality() -> pd.DataFrame:
    """EPA AQS keyless daily bulk files, filtered to the OR tri-county metro.

    Downloads one national zip per (pollutant, year), keeps only the tri-county
    rows and the sample duration that carries a daily value + AQI, and stacks
    them. The force-IPv4 monkeypatch at module load keeps aqs.epa.gov from
    hanging over IPv6.
    """
    keep_cols = [
        "State Code", "County Code", "Site Num", "Date Local", "Arithmetic Mean",
        "AQI", "Parameter Name", "Units of Measure", "Sample Duration",
        "Latitude", "Longitude", "Local Site Name", "County Name",
    ]
    counties = set(cfg.AQS_COUNTIES)
    frames: list[pd.DataFrame] = []
    for param, label in cfg.AQS_PARAMS.items():
        durations = cfg.AQS_DURATIONS[param]
        for year in range(cfg.AQS_START_YEAR, cfg.AQS_END_YEAR + 1):
            url = cfg.AQS_FILE_URL.format(param=param, year=year)
            log.info("Fetching air_quality %s %d from %s ...", label, year, url)
            with _urlopen(url, headers=cfg.USER_AGENT) as resp:
                blob = resp.read()
            zf = zipfile.ZipFile(io.BytesIO(blob))
            with zf.open(zf.namelist()[0]) as member:
                df = pd.read_csv(member, usecols=keep_cols, dtype={"State Code": str, "County Code": str, "Site Num": str})
            df = df[(df["State Code"] == cfg.AQS_STATE) & (df["County Code"].isin(counties))]
            df = df[df["Sample Duration"].isin(durations)]
            if not df.empty:
                frames.append(df)
                log.info("  air_quality %s %d: %d tri-county rows", label, year, len(df))
    if not frames:
        raise ValueError("air_quality: no tri-county rows across any pollutant/year")
    out = pd.concat(frames, ignore_index=True)
    # Collapse duplicate (site, date, pollutant) rows to one daily observation.
    out = (
        out.sort_values("AQI")
        .drop_duplicates(subset=["State Code", "County Code", "Site Num", "Date Local", "Parameter Name"], keep="last")
        .reset_index(drop=True)
    )
    return out


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    try:
        log.info("Fetching building_permits (PortlandMaps ArcGIS) ...")
        load_raw(con, "building_permits", fetch_building_permits())

        log.info("Fetching parks (PortlandMaps ArcGIS) ...")
        load_raw(con, "parks", fetch_parks())

        log.info("Fetching weather (NOAA GHCN-Daily, PDX) ...")
        load_raw(con, "weather", fetch_weather())

        log.info("Fetching willamette discharge (USGS NWIS) ...")
        load_raw(con, "willamette", fetch_willamette())

        log.info("Fetching short_term_rentals (PortlandMaps report) ...")
        load_raw(con, "short_term_rentals", fetch_str())

        log.info("Fetching crime (PortlandMaps ArcGIS) ...")
        load_raw(con, "crime", fetch_crime())

        log.info("Fetching air_quality (EPA AQS bulk, tri-county) ...")
        load_raw(con, "air_quality", fetch_air_quality())
    finally:
        con.close()
    log.info("Warehouse build complete: %s", DB_PATH)


if __name__ == "__main__":
    main()
