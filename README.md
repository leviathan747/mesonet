# mesonet

Pull live data from a Purdue Mesonet station — no API key or login required.

By default it prints total precipitation for the past **24 hours, 7 days, and
30 days** for a station. You can also request the current value of any single
variable (air temperature, wind speed, humidity, and more).

## Data source

Data comes from the public [Purdue Mesonet Data Hub][hub], an embedded Tableau
Server dashboard. We read its underlying data as CSV:

- **24-hour total** — the "Map View" with the `Map Variable` parameter set to
  `Precip` (the dashboard's published rolling 24 hr precip figure).
- **7- & 30-day totals** — the "Table View (Dly)" daily `Precipitation (in)`
  totals, summed over the most recent 7 and 30 calendar days (data runs through
  yesterday).

[hub]: https://ag.purdue.edu/indiana-state-climate/purdue-mesonet/purdue-mesonet-data-hub/

## Installation

Install directly from GitHub with pip:

```bash
pip install git+https://github.com/leviathan747/mesonet.git
```

This installs a `mesonet` command on your `PATH`. Requires Python 3.9+ and has
no third-party dependencies.

## Usage

```text
mesonet [STATION]                Precip summary: past 24h / 7d / 30d
mesonet [STATION] [VARIABLE]     Current value of one variable
mesonet [STATION] --json         Precip summary as JSON
mesonet [STATION] VARIABLE --raw Bare number only (for piping)
mesonet -h | --help              Help, including live station list
```

`STATION` defaults to `MARTELL`. `VARIABLE` is one of the keys listed below.

### Stations

`ACRE`, `ASEL`, `CCCS`, `DFINC`, `DPAC`, `DUNLAP`, `FPAC`, `MARTELL`, `NEPAC`,
`PPAC`, `SEPAC`, `SHFPRS`, `SIPAC`, `SWPAC`, `TPAC`.

Run `mesonet --help` for the live list of currently reporting stations.

### Variables (single-value mode)

| Key                           | Meaning                          |
| ----------------------------- | -------------------------------- |
| `Precip`                      | 24 hr Total Precipitation (in)   |
| `Air Temp`                    | Air Temp (°F)                    |
| `AirTemp050cmAvg`             | 0.5 m Air Temp (°F)              |
| `AirTemp150cmAvg`             | 1.5 m Air Temp (°F)              |
| `AirTemp300cmAvg`             | 3 m Air Temp (°F)                |
| `Inversion Strength`          | Inversion Strength (°F)          |
| `RH`                          | Relative Humidity (%)            |
| `Solar`                       | Solar Radiation (W/m²)           |
| `W Spd`                       | Wind Speed (mph)                 |
| `Wdir`                        | Wind Direction (°)               |
| `Wgust`                       | Wind Gust (mph)                  |
| `Heat Index`                  | Heat Index (°F)                  |
| `Wind Chill`                  | Wind Chill (°F)                  |
| `Dew Point (Formatted) (F)`   | Dew Point (°F)                   |
| `WBGT (F)`                    | Wet Bulb Globe Temperature (°F)  |
| `Barometric Pressure`         | Barometric Pressure (inHg)       |

### Examples

```bash
mesonet                       # MARTELL precip summary
mesonet TPAC                  # TPAC precip summary
mesonet MARTELL --json        # summary as JSON
mesonet ACRE "W Spd"          # current wind speed at ACRE
mesonet TPAC "Air Temp"       # current air temp at Throckmorton
mesonet MARTELL Precip --raw  # bare 24h precip value, for piping
```

You can also run it without installing the console script:

```bash
python -m mesonet TPAC
```

## License

MIT
