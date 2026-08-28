# fetch-eits

A command-line tool that fetches all modules and security measures from the public E-ITS (Eesti Infoturbestandard / Estonian Information Security Standard) API and exports them as JSON or CSV.

## Features

- Fetches module and measure data from `https://eits.ria.ee/api/2`
- Supports multiple catalog versions (e.g. 2024, 2025) and languages (Estonian, English)
- Concurrent fetching with configurable worker count and request delay
- Strips HTML markup from measure body text
- Exports full structured data as JSON and flattened measures as CSV

## Requirements

- Python 3.x (developed and tested with 3.13)
- No external packages — standard library only

## Setup & Installation

```bash
git clone <repository-url>
cd eits
python fetch_eits.py --help
```

## Running the Application

```bash
# Fetch the default version (2025, Estonian)
python fetch_eits.py

# Fetch a specific version
python fetch_eits.py --version 2024

# Fetch multiple versions
python fetch_eits.py --version 2023 2024 2025

# Fetch all available versions
python fetch_eits.py --all-versions

# Fetch in English
python fetch_eits.py --lang en

# Save to custom output files (single version only)
python fetch_eits.py --json out.json --csv out.csv

# List available catalog versions
python fetch_eits.py --list-versions
```

### All Options

| Flag | Default | Description |
|---|---|---|
| `--version VERSION [...]` | `2025` | One or more catalog versions to fetch |
| `--all-versions` | — | Fetch all available versions |
| `--lang {et,en}` | `et` | Language for labels and descriptions |
| `--json FILE` | auto | Save full data as JSON (single version only) |
| `--csv FILE` | auto | Save measures as CSV (single version only) |
| `--list-versions` | — | Print available versions and exit |
| `--workers N` | `8` | Number of concurrent HTTP workers |
| `--delay SECONDS` | `0.05` | Delay between requests per worker |

When neither `--json` nor `--csv` is specified, both files are created automatically with names in the form `eits_{version}_{lang}.json` / `.csv`.

## Output Format

**JSON** — full hierarchical data: version, language, and a map of modules each containing `measureDetails` groups and individual measures.

**CSV** — one row per measure with columns:

`module_id`, `module_code`, `module_title`, `group_code`, `group_title`, `measure_id`, `measure_code`, `measure_title`, `measure_body`, `assignees`, `security_codes`

The CSV is written with UTF-8 BOM (`utf-8-sig`) for compatibility with Excel.

## Known Limitations & Assumptions

- `--json` and `--csv` flags are silently ignored when fetching multiple versions; per-version auto-named files are produced instead.
- No retry logic for failed module fetches — failures are recorded in the JSON output under an `"error"` key and reported to stderr.
- No test suite or CI/CD configuration is present in the repository.
- The `.gitignore` uses a wildcard pattern; the data files (`*.json`, `*.csv`) are tracked by explicit `git add`.
