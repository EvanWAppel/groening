"""Portland-metro configuration — the one file that encodes *which city*.

Every city-specific value (ArcGIS service roots, EPA AQS FIPS codes, NOAA station,
USGS gauge, year ranges, source URLs) lives here. ``build_warehouse.py`` imports
from this module; swapping the whole app to another metro is a single-file edit.

Interview outcomes (2026-08-11):
  - Metro breadth : full tri-county — Multnomah (051) + Washington (067)
                    + Clackamas (005).
  - Water body    : Willamette River (USGS NWIS).
  - Drop list     : drop Marriage & Fire if no easy machine-readable feed.
  - Deploy        : standalone Railway.

Each endpoint below is a *full* ArcGIS layer base URL (FeatureServer *or*
MapServer — Portland mixes both), because ``fetch_layer`` takes the base URL
directly rather than composing org/service/layer the way the Elvis original did.
"""

# --------------------------------------------------------------------------- #
# ArcGIS org / service roots                                                   #
# --------------------------------------------------------------------------- #
# PortlandMaps Open Data services (City of Portland). Note these are MapServer
# endpoints served from portlandmaps.com, not the arcgis.com FeatureServer org.
PORTLANDMAPS_OD = "https://www.portlandmaps.com/od/rest/services"

# Planning & Development open-data service (permits, land-use, etc.).
COP_PLANNING = f"{PORTLANDMAPS_OD}/COP_OpenData_PlanningDevelopment/MapServer"

# Environment open-data service (parks, wetlands, streams, watersheds, etc.).
COP_ENVIRONMENT = f"{PORTLANDMAPS_OD}/COP_OpenData_Environment/MapServer"

# Transportation open-data service (bike network, streets, etc.).
COP_TRANSPORTATION = f"{PORTLANDMAPS_OD}/COP_OpenData_Transportation/MapServer"

# --------------------------------------------------------------------------- #
# Building Permits (vertical-slice topic) — VERIFIED live 2026-08-11           #
# --------------------------------------------------------------------------- #
# Layer 89 = "Residential Building Permits", point geometry (WGS84 via outSR),
# ~36k rows. Fields include ISSUEDATE/INDATE (esri date), STATUS, YEAR_,
# NEWCLASS, NEWTYPE, NBRHOOD, VALUATION, NEW_UNITS, SQFT, WORKDESC, PROP_ADDRE.
PERMITS_LAYER_URL = f"{COP_PLANNING}/89"

# --------------------------------------------------------------------------- #
# Affordable Housing — Portland Housing Bureau "Rental Portfolio" — VERIFIED   #
# live 2026-09-26                                                              #
# --------------------------------------------------------------------------- #
# Layer 221 = "Rental Portfolio", ~380 point rows: the Housing Bureau's portfolio
# of financed/regulated affordable rental projects. Total_Unit / Regulated_Units,
# Year_Complet, Building_Type, Analysis_Area, and bond/TIF flags. Point geometry
# reprojected to WGS84 via outSR.
HOUSING_LAYER_URL = f"{COP_PLANNING}/221"

# --------------------------------------------------------------------------- #
# Parks — VERIFIED live 2026-08-11                                             #
# --------------------------------------------------------------------------- #
# Layer 35 = "Parks", 316 boundary polygons. Fields: NAME, ACRES, PROPERTYID.
# Native SR is Web Mercator; pass outSR=4326. Compute centroids for PyDeck.
# Portland publishes no park-level water-feature attribute — that Elvis flag is
# dropped (and logged). A wetlands/stream spatial intersect could revive it later.
PARKS_LAYER_URL = f"{COP_ENVIRONMENT}/35"

# Layer 220 = "Parks Tree Inventory", 25,734 points with taxonomy (Common_name,
# Genus, Genus_species), size (DBH, TreeHeight, Condition), and ecosystem-benefit
# metrics (carbon storage/sequestration, stormwater, pollution removal). WGS84.
TREES_LAYER_URL = f"{COP_ENVIRONMENT}/220"

# --------------------------------------------------------------------------- #
# EPA AQS — keyless bulk daily files, filtered by state/county FIPS            #
# --------------------------------------------------------------------------- #
# Oregon = 41; tri-county = Multnomah 051, Washington 067, Clackamas 005.
AQS_STATE = "41"
AQS_COUNTIES = ["051", "067", "005"]
AQS_FILE_URL = "https://aqs.epa.gov/aqsweb/airdata/daily_{param}_{year}.zip"
AQS_PARAMS = {"88101": "PM2.5", "44201": "Ozone"}  # param code -> label
# Each national file is ~200-300 MB and is filtered down to a few hundred
# tri-county rows, so keep the window modest to bound build time/bandwidth.
# 2024 is the last authoritative year (verified 2026-08-11).
AQS_START_YEAR = 2019
AQS_END_YEAR = 2024
# EPA ships multiple rows per site-day; keep only the duration that carries a
# daily value + AQI. Ozone is published as an 8-hour running average.
AQS_DURATIONS = {
    "88101": {"24 HOUR", "24-HR BLK AVG"},
    "44201": {"8-HR RUN AVG BEGIN HOUR"},
}
# Note: no EPA regulatory PM2.5 monitor in Clackamas (005); only Ozone. Logged.

# --------------------------------------------------------------------------- #
# NOAA GHCN-Daily — Portland International Airport (PDX)                        #
# --------------------------------------------------------------------------- #
NOAA_STATION = "USW00024229"  # PDX
WEATHER_URL = (
    "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/"
    f"access/{NOAA_STATION}.csv"
)

# --------------------------------------------------------------------------- #
# Signature water body — Willamette River (USGS NWIS) — VERIFIED 2026-08-11    #
# --------------------------------------------------------------------------- #
# Site 14211720 = "Willamette River at Portland, OR" (downtown, tidal). Use
# DISCHARGE (00060, cfs) — gage height (00065) has NO daily series here. Daily
# record 1972-10-01 -> present. Classic waterservices.usgs.gov is still live.
USGS_WILLAMETTE_SITE = "14211720"
USGS_DISCHARGE_PARAM = "00060"
USGS_DV_URL = (
    "https://waterservices.usgs.gov/nwis/dv/?format=json"
    f"&sites={USGS_WILLAMETTE_SITE}"
    "&startDT=1972-10-01&endDT={end}"
    f"&parameterCd={USGS_DISCHARGE_PARAM}&siteStatus=all"
)

# --------------------------------------------------------------------------- #
# Police / crime — PortlandMaps ArcGIS "Public/Crime" — VERIFIED 2026-08-11    #
# --------------------------------------------------------------------------- #
# Rolling trailing-12-month window (not full history), WGS84 points, block-level
# offset. REPORTED_DATETIME is esri date (epoch ms). Three crime-against layers.
CRIME_MAPSERVER = "https://www.portlandmaps.com/arcgis/rest/services/Public/Crime/MapServer"
CRIME_LAYER_URLS = {
    "Property": f"{CRIME_MAPSERVER}/1",
    "Person": f"{CRIME_MAPSERVER}/40",
    "Society": f"{CRIME_MAPSERVER}/59",
}

# --------------------------------------------------------------------------- #
# Short-Term Rentals — PortlandMaps report API — VERIFIED 2026-08-11           #
# --------------------------------------------------------------------------- #
# NOT ArcGIS: a ColdFusion report with JSON/CSV export, paginated at 100/page.
# Coordinates are web_merc_x/web_merc_y in EPSG:3857 — reproject to WGS84 in ELT.
STR_REPORT_URL = "https://www.portlandmaps.com/reports/index.cfm?action=short-term-rental"
STR_PAGE_SIZE = 100

# --------------------------------------------------------------------------- #
# Bike network — PortlandMaps Transportation MapServer — VERIFIED 2026-08-11   #
# --------------------------------------------------------------------------- #
# Layer 75 = "Bicycle Network" polylines, ~40k segments. YearBuilt drives a
# "miles built per year" + cumulative-network-growth story. Attributes only
# (no geometry) are needed for the charts. Facility = facility-type code.
BIKE_NETWORK_URL = f"{COP_TRANSPORTATION}/75"

# --------------------------------------------------------------------------- #
# Urban Growth Boundary — Metro DRC (ArcGIS Online) — VERIFIED 2026-08-11      #
# --------------------------------------------------------------------------- #
# Single dissolved polygon (~408 sq mi), no amendment history. Native SR is
# Oregon StatePlane (wkid 2913, feet) — pass outSR=4326. AREA_ is square feet.
UGB_URL = (
    "https://services1.arcgis.com/d9Fl2w84c4Vbf9kI/arcgis/rest/services/"
    "Urban_Growth_Boundary/FeatureServer/0"
)

# --------------------------------------------------------------------------- #
# Marriage — Oregon Health Authority vital stats (aggregate) — VERIFIED        #
# --------------------------------------------------------------------------- #
# No record-level feed (privacy). OHA publishes county x month marriage COUNTS
# with a same-sex breakout, 1995-present, one sheet per year, in a single XLSX.
MARRIAGE_XLSX_URL = (
    "https://www.oregon.gov/oha/PH/BIRTHDEATHCERTIFICATES/"
    "AllStatisticsMarriageData/MarriagesCountyByMonth1995-now.xlsx"
)
MARRIAGE_COUNTY = "Multnomah"

# --------------------------------------------------------------------------- #
# Air travel — BTS international passenger API (Socrata) — VERIFIED 2026-08-11  #
# --------------------------------------------------------------------------- #
# No gaming analog for Portland (Elvis's tourism page was gaming-heavy), so this
# is reframed as air travel. BTS International_Report_Passengers (dataset
# xgub-n9bw), monthly 1990-2025, keyless. International only; PDX is usg_apt.
# Server-side aggregate: one row per (year, month) with summed passengers.
BTS_PDX_INTL_URL = (
    "https://data.transportation.gov/resource/xgub-n9bw.csv"
    "?usg_apt=PDX&$select=year,month,sum(total)&$group=year,month"
    "&$order=year,month&$limit=50000"
)

# --------------------------------------------------------------------------- #
# Restaurant inspections — Multnomah County (MyHealthDepartment) — VERIFIED    #
# --------------------------------------------------------------------------- #
# Multnomah County Environmental Health publishes food/pool/lodging inspections
# on the MyHealthDepartment platform. The browse list POSTs a `searchInspections`
# task to the SITE ROOT (not an ArcGIS/REST path); it returns JSON rows with the
# establishment name, address, sanitation score (0-100 for food), inspection
# type, purpose, and date — but NO coordinates (address only, so no map).
# Gotchas (verified 2026-08-12):
#   - The host 403s clients without a browser-ish User-Agent; USER_AGENT below
#     already passes, so no per-host TLS/UA special-casing is required.
#   - A single query is hard-capped at ~225 rows (resultOffset >= 225 => "bad
#     request") and pages 25 at a time, so build_warehouse tiles the rolling
#     window into date ranges and splits any that overflow the cap.
#   - The searchable database only retains ~1 year of inspections.
INSPECTIONS_URL = "https://inspections.myhealthdepartment.com/"
INSPECTIONS_PATH = "multco-eh"  # Multnomah County Environmental Health jurisdiction
INSPECTIONS_MONTHS = 6  # rolling history to pull (bounded by ~225-row/query cap)
# Base date-window size. All-facility volume is ~20-80/day, so a 3-day window
# stays well under the 225-row cap and rarely needs splitting — fewer total
# requests (and no wasted re-fetch) than a wide window that keeps overflowing.
INSPECTIONS_WINDOW_DAYS = 3
INSPECTIONS_PAGE_SIZE = 25  # server caps a page at 25 regardless of requested count
INSPECTIONS_CAP = 225  # server refuses resultOffset >= this within one window
# Date windows are independent, so fetch them concurrently — the pull is entirely
# I/O-bound on a ~2s/request server. Tuned to 3: the county endpoint throttles
# (403s + connection timeouts) at 6-way load but tolerates 3 cleanly, roughly
# halving wall-clock (~22min -> ~11min) without triggering anti-abuse limits.
INSPECTIONS_CONCURRENCY = 3
# Hundreds of requests over a rate-limited county endpoint => a transient
# timeout/reset is likely at least once; retry with exponential backoff before
# aborting the whole build.
INSPECTIONS_RETRIES = 4

# --------------------------------------------------------------------------- #
# Transit — TriMet GTFS static feed — VERIFIED live 2026-09-26                 #
# --------------------------------------------------------------------------- #
# The regional transit agency publishes a standard GTFS zip (keyless, public):
# routes.txt (81 routes, route_type = mode), stops.txt (6,027 stops, WGS84
# lat/lon), and much more. We keep routes + stops; the 67k-row trips.txt is
# skipped for now (a service-frequency view could add it later). route_type is a
# GTFS-standard enum mapped to a mode label in staging, not here.
TRIMET_GTFS_URL = "https://developer.trimet.org/schedule/gtfs.zip"
# table_name -> (zip member, columns to keep). Columns are read as strings and
# cast/normalized in staging, matching every other topic.
GTFS_MEMBERS = {
    "transit_routes": (
        "routes.txt",
        ["route_id", "route_short_name", "route_long_name", "route_type", "route_color"],
    ),
    "transit_stops": (
        "stops.txt",
        ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"],
    ),
}

# --------------------------------------------------------------------------- #
# Shared fetch tuning                                                          #
# --------------------------------------------------------------------------- #
PAGE_SIZE = 2000
USER_AGENT = {"User-Agent": "Mozilla/5.0 (compatible; groening-data/1.0)"}

# Municipal / clerk / health bulk files are frequently Windows-1252, not UTF-8.
BULK_ENCODING = "cp1252"

# --------------------------------------------------------------------------- #
# Source catalog — provenance for the Sources & Methodology page               #
# --------------------------------------------------------------------------- #
# One entry per raw table (key == the raw.* table name, which also keys
# mart_build_metadata's row counts). This is city-specific provenance, so it
# lives in the one "which city" file: swapping metros re-points these too. The
# Sources page joins this catalog with the build-provenance mart's row counts.
#
# `page`     : views/<page>.py slug the row links to (all == key except bike).
# `publisher`: the agency that publishes the data.
# `url`      : the exact endpoint we fetch (the config constant above), so the
#              page cites where the data literally comes from, not a landing page.
# `coverage` : temporal/extent coverage (verified 2026-08-11; see comments above).
# `grain`    : one-line description of a row + the key raw->mart transform.
# `license`  : accurate for U.S. federal works (public domain); municipal/state
#              entries use descriptive attribution — TIGHTEN before public use.
SOURCES = {
    "building_permits": {
        "title": "Building Permits", "page": "building_permits",
        "publisher": "City of Portland — PortlandMaps Open Data",
        "url": PERMITS_LAYER_URL, "coverage": "~1995 – present",
        "grain": "One row per residential permit; geocoded to WGS84 points.",
        "license": "City of Portland open data",
    },
    "parks": {
        "title": "Parks", "page": "parks",
        "publisher": "Portland Parks & Recreation — PortlandMaps",
        "url": PARKS_LAYER_URL, "coverage": "Current inventory",
        "grain": "One row per park; boundary polygon reduced to a centroid.",
        "license": "City of Portland open data",
    },
    "trees": {
        "title": "Trees", "page": "trees",
        "publisher": "Portland Parks & Recreation — PortlandMaps",
        "url": TREES_LAYER_URL, "coverage": "Current inventory",
        "grain": "One row per inventoried street/park tree (taxonomy + benefits).",
        "license": "City of Portland open data",
    },
    "crime": {
        "title": "Reported Crime", "page": "crime",
        "publisher": "Portland Police Bureau — PortlandMaps",
        "url": CRIME_MAPSERVER, "coverage": "Rolling trailing 12 months",
        "grain": "One row per reported offense; three crime-against layers unioned.",
        "license": "City of Portland open data",
    },
    "short_term_rentals": {
        "title": "Short-Term Rentals", "page": "short_term_rentals",
        "publisher": "City of Portland — PortlandMaps report API",
        "url": STR_REPORT_URL, "coverage": "Current registry",
        "grain": "One row per ASTR permit; Web Mercator coords reprojected to WGS84.",
        "license": "City of Portland open data",
    },
    "bike_network": {
        "title": "Bike Network", "page": "bike",
        "publisher": "Portland Bureau of Transportation — PortlandMaps",
        "url": BIKE_NETWORK_URL, "coverage": "Segments with a recorded build year",
        "grain": "One row per bikeway segment; aggregated to miles built per year.",
        "license": "City of Portland open data",
    },
    "ugb": {
        "title": "Urban Growth Boundary", "page": "ugb",
        "publisher": "Metro (regional government)",
        "url": UGB_URL, "coverage": "Current boundary (no amendment history)",
        "grain": "Single dissolved polygon; area + outer ring for the map.",
        "license": "Metro RLIS open data",
    },
    "air_quality": {
        "title": "Air Quality", "page": "air_quality",
        "publisher": "U.S. EPA — Air Quality System (AQS)",
        "url": "https://aqs.epa.gov/aqsweb/airdata/", "coverage": "2019 – 2024",
        "grain": "One row per site-day; PM2.5 + Ozone, tri-county filtered.",
        "license": "U.S. public domain",
    },
    "weather": {
        "title": "Rain & Records", "page": "weather",
        "publisher": "NOAA — GHCN-Daily (station USW00024229, PDX)",
        "url": WEATHER_URL, "coverage": "1938 – present",
        "grain": "One row per day at PDX; units normalized to °F / inches.",
        "license": "U.S. public domain",
    },
    "willamette": {
        "title": "Willamette River", "page": "willamette",
        "publisher": "U.S. Geological Survey — NWIS (site 14211720)",
        "url": "https://waterservices.usgs.gov/nwis/dv/", "coverage": "1972 – present",
        "grain": "One row per day; mean discharge (cfs) with a provisional flag.",
        "license": "U.S. public domain",
    },
    "tourism": {
        "title": "Air Travel", "page": "tourism",
        "publisher": "U.S. Bureau of Transportation Statistics (BTS)",
        "url": "https://data.transportation.gov/resource/xgub-n9bw",
        "coverage": "1990 – 2025", "grain": "One row per month; PDX international passengers.",
        "license": "U.S. public domain",
    },
    "marriage": {
        "title": "Marriages", "page": "marriage",
        "publisher": "Oregon Health Authority — vital statistics",
        "url": MARRIAGE_XLSX_URL, "coverage": "1995 – present",
        "grain": "One row per year (Multnomah); aggregate counts + same-sex breakout.",
        "license": "Oregon OHA public statistics",
    },
    "restaurant_inspections": {
        "title": "Restaurant Inspections", "page": "restaurant_inspections",
        "publisher": "Multnomah County Environmental Health (MyHealthDepartment)",
        "url": INSPECTIONS_URL, "coverage": "Rolling ~6 months",
        "grain": "One row per inspection; 0–100 sanitation score (no coordinates).",
        "license": "Multnomah County public records",
    },
    "transit_routes": {
        "title": "Transit — Routes", "page": "transit",
        "publisher": "TriMet — GTFS static feed",
        "url": TRIMET_GTFS_URL, "coverage": "Current published schedule",
        "grain": "One row per route; GTFS route_type mapped to a mode label.",
        "license": "TriMet open data (GTFS)",
    },
    "transit_stops": {
        "title": "Transit — Stops", "page": "transit",
        "publisher": "TriMet — GTFS static feed",
        "url": TRIMET_GTFS_URL, "coverage": "Current published schedule",
        "grain": "One row per stop; WGS84 lat/lon for the map.",
        "license": "TriMet open data (GTFS)",
    },
    "housing": {
        "title": "Affordable Housing", "page": "housing",
        "publisher": "Portland Housing Bureau — PortlandMaps",
        "url": HOUSING_LAYER_URL, "coverage": "Regulated portfolio to date",
        "grain": "One row per regulated affordable-housing project (WGS84 point).",
        "license": "City of Portland open data",
    },
}


# Topics from the Elvis blueprint that Portland does not publish as a clean,
# machine-readable open feed (verified 2026-08-11). build_warehouse logs these at
# build time; the Sources page lists them so a dropped topic never reads as "done".
DROPPED_TOPICS = {
    "fire_inspections": "Portland Fire & Rescue publishes only station/district "
    "polygons — no inspection or incident records feed.",
    "business_licenses": "Portland's business license is a Revenue tax, not an open "
    "registry; the legacy CivicApps dataset is decommissioned.",
    "public_art": "Only a 42-point unofficial downtown scrape (~2012) exists; RACC "
    "publishes no machine-readable geo feed of its full collection.",
    "tree_canopy": "Portland's Urban Forestry canopy assessment is published as "
    "raster/land-cover snapshots, not a clean tabular canopy-over-time feed — no "
    "machine-readable time series to chart. (The Trees page covers the street-tree "
    "inventory instead.)",
}


def source_catalog_rows(row_counts: dict[str, int]) -> list[dict]:
    """Merge the SOURCES catalog with a table_name -> row_count mapping.

    Returns one display dict per catalogued source, in catalog order, with the
    row count attached. Raises if a counted table has no catalog entry — that
    means a new raw source shipped undocumented, which should surface loudly
    rather than silently miss the Sources page.
    """
    undocumented = set(row_counts) - set(SOURCES)
    if undocumented:
        raise KeyError(
            f"raw tables missing from SOURCES catalog: {sorted(undocumented)}"
        )
    return [
        {**meta, "table": table, "row_count": row_counts.get(table)}
        for table, meta in SOURCES.items()
    ]
