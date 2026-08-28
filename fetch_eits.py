#!/usr/bin/env python3
"""Fetch all modules and measures from the E-ITS public API."""

import csv
import html
import json
import re
import sys
import time
import argparse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

_BLOCK_TAGS = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6"}


class _Stripper(HTMLParser):
    """Flatten HTML to text, one line per block element."""

    def __init__(self):
        super().__init__()
        self._lines = [[]]

    def _break(self):
        if self._lines[-1]:
            self._lines.append([])

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._break()

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self._break()

    def handle_data(self, data):
        text = data.replace("\xa0", " ").strip()
        if text:
            self._lines[-1].append(text)

    def get_text(self):
        return "\n".join(" ".join(parts) for parts in self._lines if parts)


def strip_html(raw):
    s = _Stripper()
    s.feed(html.unescape(raw or ""))
    return s.get_text()


# The measure body starts with a block of "<p><b>Label:</b> value</p>" paragraphs
# that repeat metadata rather than requirements; these are lifted into own columns.
_META_PARA = re.compile(r"\s*<p>\s*<b>\s*([^<]+?)\s*:?\s*</b>\s*(.*?)\s*</p>", re.S | re.I)
_META_FIELDS = {
    "vastutaja": "responsible",
    "responsible": "responsible",
    "elutsükli etapp": "lifecycle_stage",
    "life cycle phase": "lifecycle_stage",
    "lifecycle phase": "lifecycle_stage",
    "turvakomponent": "security_component",
    "security component": "security_component",
}


def split_body_meta(raw):
    """Return (metadata dict, remaining body HTML) for a measure body."""
    body = raw or ""
    meta = {}
    while True:
        m = _META_PARA.match(body)
        if not m:
            break
        field = _META_FIELDS.get(strip_html(m.group(1)).lower())
        if not field:
            # Unknown label: leave it in the body rather than dropping it.
            break
        meta[field] = strip_html(m.group(2))
        body = body[m.end():]
    return meta, body


# Requirements inside a measure body are lettered paragraphs ("a. ...", "b. ...");
# any following lines (list bullets, continuations) belong to the preceding letter.
_SUBMEASURE = re.compile(r"^([a-z])\.\s+(.*)$")


def split_submeasures(text):
    """Return [(letter, text)] for a stripped measure body.

    Text before the first lettered paragraph — rare, but possible — is returned
    under an empty letter so nothing is dropped.
    """
    items = []
    for line in text.split("\n"):
        m = _SUBMEASURE.match(line)
        # Letters always run forward; a "b." inside a bullet list is continuation text.
        if m and (not items or m.group(1) > items[-1][0]):
            items.append([m.group(1), [m.group(2)]])
        elif items:
            items[-1][1].append(line)
        elif line.strip():
            items.append(["", [line]])
    return [(letter, "\n".join(parts)) for letter, parts in items]

BASE_URL = "https://eits.ria.ee/api/2"
DEFAULT_VERSION = "2026"


def get(path, params=None):
    url = BASE_URL + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; fetch-eits/1.0)",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_versions():
    return [v["version"] for v in get("/catalog")["versions"]]


def fetch_modules(version, lang):
    return get(f"/catalog/{version}/modules", {"lang": lang})["modules"]


def fetch_module_detail(version, module_id, lang):
    return get(f"/catalog/{version}/{module_id}", {"lang": lang})


def fetch_all(version, lang, workers, delay):
    print(f"Fetching modules for version {version} [{lang}]...", file=sys.stderr)
    modules = fetch_modules(version, lang)
    print(f"  Found {len(modules)} modules. Fetching details...", file=sys.stderr)

    results = {}
    failed = []

    def fetch_one(module):
        time.sleep(delay)
        try:
            return module["moduleId"], fetch_module_detail(version, module["moduleId"], lang)
        except Exception as e:
            return module["moduleId"], {"error": str(e), **module}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one, m): m for m in modules}
        done = 0
        for future in as_completed(futures):
            mid, detail = future.result()
            results[mid] = detail
            done += 1
            if "error" in detail:
                failed.append(mid)
            print(f"  {done}/{len(modules)}", end="\r", file=sys.stderr)

    print(file=sys.stderr)
    if failed:
        print(f"  Failed IDs: {failed}", file=sys.stderr)

    return {"version": version, "lang": lang, "modules": results}


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON saved to {path}")


def strip_code_prefix(title, code):
    """Drop a leading measure/module code (and its separator) from a title."""
    if code and title.startswith(code):
        return title[len(code):].lstrip(": ").strip()
    return title


def save_csv(data, path, per_submeasure=True):
    rows = []
    for mod in data["modules"].values():
        if "error" in mod:
            continue
        module_code = mod.get("moduleCode", "")
        module_title = strip_code_prefix(mod.get("moduleTitle", ""), module_code)
        for group in mod.get("measureDetails", []):
            group_code = group.get("groupCode", "")
            group_title = group.get("groupTitle", "")
            for measure in group.get("measures", []):
                meta, body = split_body_meta(measure.get("body", ""))
                text = strip_html(body)
                measure_code = measure.get("measureCode", "")
                row = {
                    "module_code": module_code,
                    "module_title": module_title,
                    "group_code": group_code,
                    "group_title": group_title,
                    "measure_code": measure_code,
                    "measure_title": strip_code_prefix(
                        measure.get("measureTitle", ""), measure_code),
                    "responsible": meta.get("responsible", ""),
                    "lifecycle_stage": meta.get("lifecycle_stage", ""),
                    "security_component": meta.get("security_component", ""),
                    "assignees": "; ".join(measure.get("assignees", [])),
                }
                if not per_submeasure:
                    rows.append({**row, "measure_body": text})
                    continue
                for letter, sub_text in split_submeasures(text) or [("", "")]:
                    rows.append({
                        **row,
                        "submeasure_code": f"{measure_code}.{letter}" if letter else measure_code,
                        "submeasure_body": sub_text,
                    })

    body_fields = (["submeasure_code", "submeasure_body"]
                   if per_submeasure else ["measure_body"])
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, delimiter=";", fieldnames=[
            "module_code", "module_title",
            "group_code", "group_title",
            "measure_code", "measure_title",
            "responsible", "lifecycle_stage", "security_component",
            *body_fields,
            "assignees",
        ])
        writer.writeheader()
        writer.writerows(rows)
    unit = "submeasures" if per_submeasure else "measures"
    print(f"CSV saved to {path} ({len(rows)} {unit})")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch E-ITS modules and measures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s                          # fetch 2026\n"
               "  %(prog)s --version 2024           # fetch 2024\n"
               "  %(prog)s --version 2023 2024 2026 # fetch multiple versions\n"
               "  %(prog)s --all-versions           # fetch all available versions\n",
    )
    parser.add_argument(
        "--version", nargs="+", default=[DEFAULT_VERSION], metavar="VERSION",
        help=f"One or more catalog versions to fetch (default: {DEFAULT_VERSION})",
    )
    parser.add_argument("--all-versions", action="store_true", help="Fetch all available versions")
    parser.add_argument("--lang", default="et", choices=["et", "en"], help="Language (default: et)")
    parser.add_argument("--json", dest="json_output", metavar="FILE",
                        help="Save full data as JSON (only valid for a single version)")
    parser.add_argument("--csv", dest="csv_output", metavar="FILE",
                        help="Save measures as CSV (only valid for a single version)")
    parser.add_argument("--csv-rows", choices=["submeasure", "measure"], default="submeasure",
                        help="CSV granularity: one row per lettered submeasure (default) or per measure")
    parser.add_argument("--list-versions", action="store_true", help="List available versions and exit")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent requests (default: 8)")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between requests in seconds (default: 0.05)")
    args = parser.parse_args()

    available = fetch_versions()

    if args.list_versions:
        print("Available versions:", ", ".join(available))
        return

    versions = available if args.all_versions else args.version

    invalid = [v for v in versions if v not in available]
    if invalid:
        print(f"Unknown version(s): {', '.join(invalid)}. Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    multi = len(versions) > 1
    if multi and (args.json_output or args.csv_output):
        print("--json and --csv cannot be used with multiple versions; per-version files will be created.", file=sys.stderr)
        args.json_output = args.csv_output = None

    for version in versions:
        data = fetch_all(version, args.lang, args.workers, args.delay)

        total_measures = sum(
            len(g.get("measures", []))
            for mod in data["modules"].values() if "error" not in mod
            for g in mod.get("measureDetails", [])
        )
        print(f"Version: {version} | Language: {args.lang} | Modules: {len(data['modules'])} | Measures: {total_measures}")

        json_path = args.json_output if not multi else None
        csv_path = args.csv_output if not multi else None

        if not json_path and not csv_path:
            json_path = f"eits_{version}_{args.lang}.json"
            csv_path = f"eits_{version}_{args.lang}.csv"

        if json_path:
            save_json(data, json_path)
        if csv_path:
            save_csv(data, csv_path, per_submeasure=args.csv_rows == "submeasure")


if __name__ == "__main__":
    main()
