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

# --------------------------------------------------------------------------- #
# Building Permits (vertical-slice topic) — VERIFIED live 2026-08-11           #
# --------------------------------------------------------------------------- #
# Layer 89 = "Residential Building Permits", point geometry (WGS84 via outSR),
# ~36k rows. Fields include ISSUEDATE/INDATE (esri date), STATUS, YEAR_,
# NEWCLASS, NEWTYPE, NBRHOOD, VALUATION, NEW_UNITS, SQFT, WORKDESC, PROP_ADDRE.
PERMITS_LAYER_URL = f"{COP_PLANNING}/89"

# --------------------------------------------------------------------------- #
# EPA AQS — keyless bulk daily files, filtered by state/county FIPS            #
# --------------------------------------------------------------------------- #
# Oregon = 41; tri-county = Multnomah 051, Washington 067, Clackamas 005.
AQS_STATE = "41"
AQS_COUNTIES = ["051", "067", "005"]
AQS_FILE_URL = "https://aqs.epa.gov/aqsweb/airdata/daily_{param}_{year}.zip"
AQS_PARAMS = {"88101": "PM2.5", "44201": "Ozone"}  # param code -> label
AQS_START_YEAR = 2015

# --------------------------------------------------------------------------- #
# NOAA GHCN-Daily — Portland International Airport (PDX)                        #
# --------------------------------------------------------------------------- #
NOAA_STATION = "USW00024229"  # PDX
WEATHER_URL = (
    "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/"
    f"access/{NOAA_STATION}.csv"
)

# --------------------------------------------------------------------------- #
# Signature water body — Willamette River (USGS NWIS)                          #
# --------------------------------------------------------------------------- #
# Site id to be confirmed under CONFIG-06 before wiring TOPIC-water. USGS
# 14211720 = "Willamette River at Portland, OR" is the standard downtown gauge.
USGS_WILLAMETTE_SITE = "14211720"

# --------------------------------------------------------------------------- #
# Shared fetch tuning                                                          #
# --------------------------------------------------------------------------- #
PAGE_SIZE = 2000
USER_AGENT = {"User-Agent": "Mozilla/5.0 (compatible; groening-data/1.0)"}

# Municipal / clerk / health bulk files are frequently Windows-1252, not UTF-8.
BULK_ENCODING = "cp1252"
