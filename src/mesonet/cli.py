"""Command-line interface for pulling live Purdue Mesonet station data.

Default (no VARIABLE arg): prints total precipitation for the past 24 hours,
7 days, and 30 days for the station.

Data source: the public Purdue Mesonet Data Hub, an embedded Tableau Server
dashboard. We read its underlying data as CSV:
  * 24-hour total -> "Map View" with the "Map Variable" parameter = Precip
                     (the dashboard's published rolling 24 hr precip figure)
  * 7- & 30-day   -> "Table View (Dly)" daily "Precipitation (in)" totals,
                     summed over the most recent 7 and 30 calendar days
                     (data runs through yesterday).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import urllib.parse
import urllib.request

from . import __version__

BASE = "https://tableau.it.purdue.edu/t/public/views/IndianaMesonetDashboard"

DEFAULT_STATION = "MARTELL"

# key -> human label, for the Map View "Map Variable" parameter (single-value mode)
VARIABLES: list[tuple[str, str]] = [
    ("Precip", "24 hr Total Precipitation (in)"),
    ("Air Temp", "Air Temp (°F)"),
    ("AirTemp050cmAvg", "0.5 m Air Temp (°F)"),
    ("AirTemp150cmAvg", "1.5 m Air Temp (°F)"),
    ("AirTemp300cmAvg", "3 m Air Temp (°F)"),
    ("Inversion Strength", "Inversion Strength (°F)"),
    ("RH", "Relative Humidity (%)"),
    ("Solar", "Solar Radiation (W/m²)"),
    ("W Spd", "Wind Speed (mph)"),
    ("Wdir", "Wind Direction (°)"),
    ("Wgust", "Wind Gust (mph)"),
    ("Heat Index", "Heat Index (°F)"),
    ("Wind Chill", "Wind Chill (°F)"),
    ("Dew Point (Formatted) (F)", "Dew Point (°F)"),
    ("WBGT (F)", "Wet Bulb Globe Temperature (°F)"),
    ("Barometric Pressure", "Barometric Pressure (inHg)"),
]

# Fallback station list if a live lookup isn't possible (e.g. offline).
STATIONS_FALLBACK = [
    "ACRE", "ASEL", "CCCS", "DFINC", "DPAC", "DUNLAP", "FPAC", "MARTELL",
    "NEPAC", "PPAC", "SEPAC", "SHFPRS", "SIPAC", "SWPAC", "TPAC",
]


def fetch_csv(view: str, params: dict[str, str]) -> list[list[str]]:
    """Fetch a dashboard view as CSV and return it as a list of rows."""
    q = {":embed": "y", ":showVizHome": "no", **params}
    url = f"{BASE}/{view}.csv?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"mesonet/{__version__}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8-sig"))))


def map_value(station: str, variable: str) -> dict[str, str]:
    """Return the current value of ``variable`` for ``station`` from the Map View."""
    rows = fetch_csv("MapView", {"Map Variable": variable})
    # cols: 2=Station Id, 4=obs time, 6=value, 9=Station Name, 10=variable label
    for r in rows[1:]:
        if len(r) >= 11 and r[2].strip().upper() == station:
            return {"name": r[9], "label": r[10], "value": r[6], "as_of": r[4]}
    valid = sorted({r[2] for r in rows[1:] if len(r) > 2 and r[2]})
    raise SystemExit(
        f"Station '{station}' not found. Reporting: {', '.join(valid)}\n"
        f"Run 'mesonet --help' for stations and variables."
    )


def daily_precip(station: str) -> list[tuple[datetime.date, float]]:
    """Return (date, inches) daily precip totals for ``station``, oldest first."""
    rows = fetch_csv("TableViewDly", {"Selected Station": station})
    # cols: 0=Date, 1=Measure Names, 2=Station Id, 3=Measure Values
    out: list[tuple[datetime.date, float]] = []
    for r in rows[1:]:
        if len(r) >= 4 and r[1] == "Precipitation (in)" and r[3] not in ("", "null"):
            try:
                d = datetime.datetime.strptime(r[0], "%m/%d/%Y %I:%M:%S %p").date()
                out.append((d, float(r[3])))
            except ValueError:
                pass
    out.sort()
    return out


def live_stations() -> list[tuple[str, str]]:
    """Return station IDs + names currently reporting; empty list on failure."""
    try:
        rows = fetch_csv("MapView", {"Map Variable": "Air Temp"})
        seen: dict[str, str] = {}
        for r in rows[1:]:
            if len(r) >= 10 and r[2].strip():
                seen.setdefault(r[2].strip(), r[9])
        return sorted(seen.items())
    except Exception:
        return []


def print_help() -> None:
    """Print rich help text, including a live station lookup when possible."""
    print(
        "mesonet — live data from a Purdue Mesonet station (no API key needed)\n\n"
        "USAGE\n"
        "  mesonet [STATION]                Precip summary: past 24h / 7d / 30d\n"
        "  mesonet [STATION] [VARIABLE]     Current value of one variable\n"
        "  mesonet [STATION] --json         Precip summary as JSON\n"
        "  mesonet [STATION] VARIABLE --raw Bare number only (for piping)\n"
        "  mesonet -h | --help              This help\n\n"
        "  STATION defaults to MARTELL. VARIABLE is one of the keys below.\n\n"
        "VARIABLES (key  ->  meaning)"
    )
    for k, lab in VARIABLES:
        print(f"  {k:<27} {lab}")
    stns = live_stations()
    print("\nSTATIONS" + ("" if stns else "  (fallback list — live lookup unavailable)"))
    if stns:
        for sid, name in stns:
            print(f"  {sid:<10} {name}")
    else:
        print("  " + "  ".join(STATIONS_FALLBACK))
    print(
        "\nEXAMPLES\n"
        "  mesonet                     # MARTELL precip summary\n"
        "  mesonet TPAC                # TPAC precip summary\n"
        "  mesonet MARTELL --json      # summary as JSON\n"
        '  mesonet ACRE "W Spd"        # current wind speed at ACRE'
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mesonet",
        add_help=False,  # custom help includes a live station lookup
        description="Pull live data from a Purdue Mesonet station (no API key / login).",
    )
    parser.add_argument("station", nargs="?", default=DEFAULT_STATION,
                        help="station ID (default: MARTELL)")
    parser.add_argument("variable", nargs="?",
                        help="optional VARIABLE key for a single current value")
    parser.add_argument("--json", action="store_true",
                        help="print the precip summary as JSON")
    parser.add_argument("--raw", action="store_true",
                        help="with VARIABLE, print the bare value only")
    parser.add_argument("-h", "--help", action="store_true",
                        help="show this help message and exit")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser


def report_variable(station: str, variable: str, raw: bool) -> None:
    """Print a single current value for ``variable`` at ``station``."""
    v = map_value(station, variable)
    if raw:
        print(v["value"])
    else:
        print(f"{v['name']} ({station})")
        print(f"{v['label']}: {v['value']}")
        print(f"as of {v['as_of']}")


def report_precip(station: str, as_json: bool) -> None:
    """Print the 24h / 7d / 30d precipitation summary for ``station``."""
    mv = map_value(station, "Precip")  # rolling 24-hr total + station name + time
    daily = daily_precip(station)
    last7 = round(sum(v for _, v in daily[-7:]), 2)
    last30 = round(sum(v for _, v in daily[-30:]), 2)
    p24 = float(mv["value"])
    asof = mv["as_of"]
    name = mv["name"]
    span_lo = daily[0][0].isoformat() if daily else None
    span_hi = daily[-1][0].isoformat() if daily else None

    if as_json:
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.help:
        print_help()
        return 0

    station = args.station.upper()

    if args.variable is not None:
        report_variable(station, args.variable, args.raw)
    else:
        report_precip(station, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
