#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch Public Holidays (2025–2027) from Google Calendar Public Holiday calendars.

Usage examples:
  export GCAL_API_KEY="YOUR_API_KEY"
  python holidays_gcal_fetch.py --countries JP,US,GB --out holidays.csv
  python holidays_gcal_fetch.py --calendar-id ja.japanese.official#holiday@group.v.calendar.google.com --out jp.csv
  python holidays_gcal_fetch.py --countries JP --format json --out jp.json

Notes:
- Requires only an API KEY (no OAuth) because these calendars are public.
- Calendar IDs differ by locale. This script ships with a small default map; you can pass --calendar-id to override.
- Time window is inclusive of 2025-01-01 and exclusive of 2028-01-01.
"""

import csv
import json
import os
import sys
import time
import argparse
from typing import Dict, List, Iterable, Tuple
from urllib.parse import urlencode
import urllib.request
import urllib.error

API_BASE = "https://www.googleapis.com/calendar/v3/events"

# Minimal built-in mapping (edit/extend as needed).
# Keys are "country hint" (ISO-3166 alpha-2 where possible), values are default calendarId strings.
# You can swap "en." for "ja." etc. depending on the language of event names you prefer.
DEFAULT_CAL_IDS: Dict[str, str] = {
    # Japan (public holidays only). "ja." yields Japanese names; "en." yields English names.
    "JP_ja": "ja.japanese.official#holiday@group.v.calendar.google.com",
    "JP_en": "en.japanese.official#holiday@group.v.calendar.google.com",
    # United States
    "US": "en.usa.official#holiday@group.v.calendar.google.com",
    # United Kingdom
    "GB": "en.uk.official#holiday@group.v.calendar.google.com",
    # South Korea
    "KR_en": "en.south_korea.official#holiday@group.v.calendar.google.com",
    "KR_ko": "ko.south_korea.official#holiday@group.v.calendar.google.com",
    # Taiwan
    "TW_en": "en.taiwan.official#holiday@group.v.calendar.google.com",
    "TW_zh": "zh.taiwan.official#holiday@group.v.calendar.google.com",
}

def build_url(calendar_id: str, api_key: str, time_min: str, time_max: str, page_token: str = None) -> str:
    params = {
        "key": api_key,
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "maxResults": "2500",
        "orderBy": "startTime",
    }
    if page_token:
        params["pageToken"] = page_token
    return f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events?{urlencode(params)}"

def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "holidays-fetch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        data = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} fetching {url}\n{data}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching {url}: {e}") from e

def fetch_calendar_holidays(calendar_id: str, api_key: str, years=(2025, 2026, 2027)) -> List[Dict]:
    """Return list of {date, name, country_hint, calendarId, id} items."""
    time_min = f"{min(years)}-01-01T00:00:00Z"
    time_max = f"{max(years)+1}-01-01T00:00:00Z"

    results = []
    page_token = None
    while True:
        url = build_url(calendar_id, api_key, time_min, time_max, page_token)
        data = http_get(url)

        for item in data.get("items", []):
            # All-day public holidays usually have start.date
            date = item.get("start", {}).get("date") or item.get("start", {}).get("dateTime", "")[:10]
            name = item.get("summary", "")
            results.append({
                "date": date,
                "name": name,
                "calendarId": calendar_id,
                "gcal_event_id": item.get("id", ""),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        # be polite if someone uses many calendars
        time.sleep(0.1)

    # Keep only requested years (safety in case Google returns boundary events)
    years_set = set(years)
    results = [r for r in results if r["date"] and int(r["date"][:4]) in years_set]
    return results

def write_csv(rows: List[Dict], out_path: str):
    fieldnames = ["date", "name", "calendarId", "gcal_event_id"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def write_json(rows: List[Dict], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def parse_countries_arg(arg: str) -> List[str]:
    # Accept comma-separated items like "JP,US,GB,KR_ko,TW_zh"
    return [x.strip() for x in arg.split(",") if x.strip()]

def main():
    parser = argparse.ArgumentParser(description="Fetch public holidays (2025–2027) from Google public holiday calendars.")
    parser.add_argument("--api-key", default=os.getenv("GCAL_API_KEY"), help="Google API key (or set GCAL_API_KEY env var).")
    parser.add_argument("--countries", help="Comma-separated keys to DEFAULT_CAL_IDS (e.g., JP_ja,JP_en,US,GB).")
    parser.add_argument("--calendar-id", help="Override: fetch using a specific calendarId (ignores --countries).")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format.")
    parser.add_argument("--out", default="holidays.csv", help="Output file path.")
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: Provide --api-key or set GCAL_API_KEY.", file=sys.stderr)
        sys.exit(2)

    targets: List[Tuple[str, str]] = []  # (label, calendar_id)

    if args.calendar_id:
        targets.append(("custom", args.calendar_id))
    elif args.countries:
        keys = parse_countries_arg(args.countries)
        for k in keys:
            cal_id = DEFAULT_CAL_IDS.get(k)
            if not cal_id:
                print(f"WARNING: '{k}' not found in DEFAULT_CAL_IDS. Skip or pass --calendar-id.", file=sys.stderr)
                continue
            targets.append((k, cal_id))
    else:
        print("ERROR: Provide --countries or --calendar-id.", file=sys.stderr)
        print("Example: --countries JP_ja,US,GB  OR  --calendar-id ja.japanese.official#holiday@group.v.calendar.google.com", file=sys.stderr)
        sys.exit(2)

    all_rows: List[Dict] = []
    for label, cal_id in targets:
        print(f"Fetching: {label} [{cal_id}] ...", file=sys.stderr)
        rows = fetch_calendar_holidays(cal_id, args.api_key)
        for r in rows:
            r["calendarKey"] = label
        all_rows.extend(rows)

    # Sort by date then calendarKey for a stable output
    all_rows.sort(key=lambda r: (r["date"], r.get("calendarKey","")))

    if args.format == "csv":
        write_csv(all_rows, args.out)
    else:
        write_json(all_rows, args.out)

    print(f"OK: wrote {len(all_rows)} rows to {args.out}")
    if args.format == "csv":
        print("Columns: date,name,calendarId,gcal_event_id", file=sys.stderr)

if __name__ == "__main__":
    main()
