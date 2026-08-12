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

# --------------------------------------------------------------------------- #
# Building Permits (vertical-slice topic) — VERIFIED live 2026-08-11           #
# --------------------------------------------------------------------------- #
# Layer 89 = "Residential Building Permits", point geometry (WGS84 via outSR),
# ~36k rows. Fields include ISSUEDATE/INDATE (esri date), STATUS, YEAR_,
# NEWCLASS, NEWTYPE, NBRHOOD, VALUATION, NEW_UNITS, SQFT, WORKDESC, PROP_ADDRE.
PERMITS_LAYER_URL = f"{COP_PLANNING}/89"

# --------------------------------------------------------------------------- #
# Parks — VERIFIED live 2026-08-11                                             #
# --------------------------------------------------------------------------- #
# Layer 35 = "Parks", 316 boundary polygons. Fields: NAME, ACRES, PROPERTYID.
# Native SR is Web Mercator; pass outSR=4326. Compute centroids for PyDeck.
# Portland publishes no park-level water-feature attribute — that Elvis flag is
# dropped (and logged). A wetlands/stream spatial intersect could revive it later.
PARKS_LAYER_URL = f"{COP_ENVIRONMENT}/35"

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
# Shared fetch tuning                                                          #
# --------------------------------------------------------------------------- #
PAGE_SIZE = 2000
USER_AGENT = {"User-Agent": "Mozilla/5.0 (compatible; groening-data/1.0)"}

# Municipal / clerk / health bulk files are frequently Windows-1252, not UTF-8.
BULK_ENCODING = "cp1252"
