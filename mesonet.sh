#!/usr/bin/env bash
#
# mesonet.sh — pull live data from a Purdue Mesonet station (no API key / login).
#
# Default (no VARIABLE arg): prints total precipitation for the past
#   24 hours, 7 days, and 30 days for the station.
#
# Data source: the public Purdue Mesonet Data Hub, an embedded Tableau Server
# dashboard. We read its underlying data as CSV:
#   * 24-hour total  -> "Map View" with the "Map Variable" parameter = Precip
#                       (the dashboard's published rolling 24 hr precip figure)
#   * 7- & 30-day     -> "Table View (Dly)" daily "Precipitation (in)" totals,
#                       summed over the most recent 7 and 30 calendar days
#                       (data runs through yesterday).
#
# Usage:
#   ./mesonet.sh [STATION]                 # precip summary (24h / 7d / 30d)
#   ./mesonet.sh [STATION] [VARIABLE]      # single current value of any variable
#   ./mesonet.sh [STATION] --json          # precip summary as JSON
#
#   STATION   Station ID (default: MARTELL). ACRE, TPAC, DPAC, PPAC, SEPAC,
#             SWPAC, SIPAC, FPAC, NEPAC, DUNLAP, ASEL, CCCS, DFINC, SHFPRS.
#
# Single-value VARIABLE keys (current reading):
#   Precip  Air Temp  AirTemp050cmAvg  AirTemp150cmAvg  AirTemp300cmAvg
#   Inversion Strength  RH  Solar  W Spd  Wdir  Wgust  Heat Index  Wind Chill
#   Dew Point (Formatted) (F)  WBGT (F)  Barometric Pressure
#
# Examples:
#   ./mesonet.sh                       # MARTELL precip summary
#   ./mesonet.sh TPAC                  # TPAC precip summary
#   ./mesonet.sh MARTELL --json        # summary as JSON
#   ./mesonet.sh TPAC "Air Temp"       # current air temp at Throckmorton

exec python3 - "$@" <<'PY'
import csv, io, sys, urllib.parse, urllib.request, json

BASE = "https://tableau.it.purdue.edu/t/public/views/IndianaMesonetDashboard"

def fetch_csv(view, params):
    q = {":embed": "y", ":showVizHome": "no", **params}
    url = f"{BASE}/{view}.csv?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": "mesonet.sh/2.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8-sig"))))

def map_value(station, variable):
    """Current value of `variable` for `station` from the Map View."""
    rows = fetch_csv("MapView", {"Map Variable": variable})
    # cols: 2=Station Id, 4=obs time, 6=value, 9=Station Name, 10=variable label
    for r in rows[1:]:
        if len(r) >= 11 and r[2].strip().upper() == station:
            return {"name": r[9], "label": r[10], "value": r[6], "as_of": r[4]}
    valid = sorted({r[2] for r in rows[1:] if len(r) > 2 and r[2]})
    sys.exit(f"Station '{station}' not found. Reporting: {', '.join(valid)}\n"
             f"Run 'mesonet.sh --help' for stations and variables.")

def daily_precip(station):
    """List of (date, inches) daily precip totals for `station`, oldest first."""
    rows = fetch_csv("TableViewDly", {"Selected Station": station})
    # cols: 0=Date, 1=Measure Names, 2=Station Id, 3=Measure Values
    import datetime
    out = []
    for r in rows[1:]:
        if len(r) >= 4 and r[1] == "Precipitation (in)" and r[3] not in ("", "null"):
            try:
                d = datetime.datetime.strptime(r[0], "%m/%d/%Y %I:%M:%S %p").date()
                out.append((d, float(r[3])))
            except ValueError:
                pass
    out.sort()
    return out

# key -> human label, for the Map View "Map Variable" parameter (single-value mode)
VARIABLES = [
    ("Precip",                    "24 hr Total Precipitation (in)"),
    ("Air Temp",                  "Air Temp (°F)"),
    ("AirTemp050cmAvg",           "0.5 m Air Temp (°F)"),
    ("AirTemp150cmAvg",           "1.5 m Air Temp (°F)"),
    ("AirTemp300cmAvg",           "3 m Air Temp (°F)"),
    ("Inversion Strength",        "Inversion Strength (°F)"),
    ("RH",                        "Relative Humidity (%)"),
    ("Solar",                     "Solar Radiation (W/m²)"),
    ("W Spd",                     "Wind Speed (mph)"),
    ("Wdir",                      "Wind Direction (°)"),
    ("Wgust",                     "Wind Gust (mph)"),
    ("Heat Index",                "Heat Index (°F)"),
    ("Wind Chill",                "Wind Chill (°F)"),
    ("Dew Point (Formatted) (F)", "Dew Point (°F)"),
    ("WBGT (F)",                  "Wet Bulb Globe Temperature (°F)"),
    ("Barometric Pressure",       "Barometric Pressure (inHg)"),
]

# Fallback station list if a live lookup isn't possible (e.g. offline).
STATIONS_FALLBACK = ["ACRE", "ASEL", "CCCS", "DFINC", "DPAC", "DUNLAP", "FPAC",
                     "MARTELL", "NEPAC", "PPAC", "SEPAC", "SHFPRS", "SIPAC",
                     "SWPAC", "TPAC"]

def live_stations():
    """Station IDs + names currently reporting on the Map View; () on failure."""
    try:
        rows = fetch_csv("MapView", {"Map Variable": "Air Temp"})
        seen = {}
        for r in rows[1:]:
            if len(r) >= 10 and r[2].strip():
                seen.setdefault(r[2].strip(), r[9])
        return sorted(seen.items())
    except Exception:
        return ()

def print_help():
    print(f"""mesonet.sh — live data from a Purdue Mesonet station (no API key needed)

USAGE
  mesonet.sh [STATION]                Precip summary: past 24h / 7d / 30d
  mesonet.sh [STATION] [VARIABLE]     Current value of one variable
  mesonet.sh [STATION] --json         Precip summary as JSON
  mesonet.sh [STATION] VARIABLE --raw Bare number only (for piping)
  mesonet.sh -h | --help              This help

  STATION defaults to MARTELL. VARIABLE is one of the keys below.

VARIABLES (key  ->  meaning)""")
    for k, lab in VARIABLES:
        print(f"  {k:<27} {lab}")
    stns = live_stations()
    print("\nSTATIONS" + ("" if stns else "  (fallback list — live lookup unavailable)"))
    if stns:
        for sid, name in stns:
            print(f"  {sid:<10} {name}")
    else:
        print("  " + "  ".join(STATIONS_FALLBACK))
    print("""
EXAMPLES
  mesonet.sh                     # MARTELL precip summary
  mesonet.sh TPAC                # TPAC precip summary
  mesonet.sh MARTELL --json      # summary as JSON
  mesonet.sh ACRE \"W Spd\"        # current wind speed at ACRE""")

if {"-h", "--help"} & set(sys.argv[1:]):
    print_help()
    sys.exit(0)

args = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = {a for a in sys.argv[1:] if a.startswith("--")}
station = (args[0] if len(args) > 0 else "MARTELL").upper()

# Single-variable mode: a VARIABLE was supplied as the 2nd positional arg.
if len(args) > 1:
    variable = args[1]
    v = map_value(station, variable)
    if "--raw" in flags:
        print(v["value"])
    else:
        print(f"{v['name']} ({station})")
        print(f"{v['label']}: {v['value']}")
        print(f"as of {v['as_of']}")
    sys.exit(0)

# Default mode: precipitation summary (24h / 7d / 30d).
mv = map_value(station, "Precip")          # rolling 24-hr total + station name + time
daily = daily_precip(station)
last7  = round(sum(v for _, v in daily[-7:]), 2)
last30 = round(sum(v for _, v in daily[-30:]), 2)
p24    = float(mv["value"])
asof   = mv["as_of"]
name   = mv["name"]
span_lo = daily[0][0].isoformat() if daily else None
span_hi = daily[-1][0].isoformat() if daily else None

if "--json" in flags:
    print(json.dumps({
        "station": station, "name": name, "units": "inches",
        "precip_24h": p24, "precip_7d": last7, "precip_30d": last30,
        "precip_24h_as_of": asof,
        "daily_window": {"from": span_lo, "to": span_hi, "days": len(daily)},
    }, indent=2))
else:
    print(f"{name} ({station}) — total precipitation")
    print(f"  Past 24 hours : {p24:>6.2f} in   (rolling, as of {asof})")
    print(f"  Past 7 days   : {last7:>6.2f} in")
    print(f"  Past 30 days  : {last30:>6.2f} in")
    if daily:
        print(f"  (7/30-day are sums of daily totals, {span_lo} → {span_hi})")
PY
