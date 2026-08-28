# fetch-eits

A command-line tool that fetches all modules and security measures from the public E-ITS (Eesti Infoturbestandard / Estonian Information Security Standard) API and exports them as JSON or CSV.

## Features

- Fetches module and measure data from `https://eits.ria.ee/api/2`
- Supports multiple catalog versions (e.g. 2024, 2026) and languages (Estonian, English)
- Concurrent fetching with configurable worker count and request delay
- Strips HTML markup from measure body text
- Splits each measure body into its lettered submeasures (`a.`, `b.`, …), one CSV row each
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
# Fetch the default version (2026, Estonian)
python fetch_eits.py

# Fetch a specific version
python fetch_eits.py --version 2024

# Fetch multiple versions
python fetch_eits.py --version 2023 2024 2026

# Fetch all available versions
python fetch_eits.py --all-versions

# Fetch in English
python fetch_eits.py --lang en

# Save to custom output files (single version only)
python fetch_eits.py --json out.json --csv out.csv

# One CSV row per measure instead of per submeasure
python fetch_eits.py --csv-rows measure

# List available catalog versions
python fetch_eits.py --list-versions
```

### All Options

| Flag | Default | Description |
|---|---|---|
| `--version VERSION [...]` | `2026` | One or more catalog versions to fetch |
| `--all-versions` | — | Fetch all available versions |
| `--lang {et,en}` | `et` | Language for labels and descriptions |
| `--json FILE` | auto | Save full data as JSON (single version only) |
| `--csv FILE` | auto | Save measures as CSV (single version only) |
| `--csv-rows {submeasure,measure}` | `submeasure` | CSV granularity: one row per lettered submeasure or per measure |
| `--list-versions` | — | Print available versions and exit |
| `--workers N` | `8` | Number of concurrent HTTP workers |
| `--delay SECONDS` | `0.05` | Delay between requests per worker |

When neither `--json` nor `--csv` is specified, both files are created automatically with names in the form `eits_{version}_{lang}.json` / `.csv`.

## Output Format

**JSON** — full hierarchical data: version, language, and a map of modules each containing `measureDetails` groups and individual measures.

**CSV** — semicolon-delimited (`;`), one row per submeasure with columns:

`module_code`, `module_title`, `group_code`, `group_title`, `measure_code`, `measure_title`, `responsible`, `lifecycle_stage`, `security_component`, `submeasure_code`, `submeasure_body`, `assignees`

`module_title` and `measure_title` hold only the title text — the code prefix the API includes there (e.g. `GRC.7: `, `GRC.7.M1 `) is stripped, since it is already in `module_code` / `measure_code`.

A measure body is a sequence of lettered requirement paragraphs (`a.`, `b.`, `c.` …); each becomes its own row, with the measure-level columns repeated. `submeasure_code` is the measure code plus the letter (e.g. `GRC.6.M1.a`), giving every requirement a stable identifier. Bullet lists belonging to a lettered paragraph stay with it as extra lines inside `submeasure_body`. Letters are not always contiguous — a measure may go `a.`, `b.`, `d.` — and the letters used are preserved as published.

With `--csv-rows measure` the two `submeasure_*` columns are replaced by a single `measure_body` column holding the whole body, one row per measure.

Each measure body from the API begins with a metadata block (`Vastutaja`, `Elutsükli etapp`, and optionally `Turvakomponent`). These are parsed out into the `responsible`, `lifecycle_stage` and `security_component` columns, so `measure_body` holds only the requirement text. Note that `responsible` (per measure, from the body) does not always match the API's `assignees` field, which is broader; both are kept.

The CSV is written with UTF-8 BOM (`utf-8-sig`) and a semicolon delimiter for compatibility with Excel in European locales. Multi-value fields (`assignees`) use `; ` internally and are quoted, so they parse correctly.

## Architecture & Security

See [Architecture.md](Architecture.md), [Security.md](Security.md), and [SBOM.md](SBOM.md).

## Known Limitations & Assumptions

- `--json` and `--csv` flags are silently ignored when fetching multiple versions; per-version auto-named files are produced instead.
- No retry logic for failed module fetches — failures are recorded in the JSON output under an `"error"` key and reported to stderr.
- No test suite or CI/CD configuration is present in the repository.
- The `.gitignore` uses a wildcard pattern; the data files (`*.json`, `*.csv`) are tracked by explicit `git add`.
