#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update holiday definitions in JSON files using Google Calendar API.

This script fetches public holidays from Google Calendar API and updates
the country-specific JSON files in the json directory.

Usage:
  export GCAL_API_KEY="YOUR_API_KEY"
  python update_holidays.py --start-year 2025 --end-year 2027 --recreate
  python update_holidays.py --start-year 2025 --end-year 2027
"""

import json
import os
import sys
import glob
import argparse
import ssl
import certifi
from typing import List, Dict, Set
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
from urllib.parse import urlencode, quote

API_BASE_URL = "https://www.googleapis.com/calendar/v3/calendars"

# Mapping of country codes to Google Calendar IDs and language preferences
# JP uses Japanese locale (ja), all others use English (en)
CALENDAR_MAPPING = {
    "JP": {"calendar_id": "ja.japanese.official#holiday@group.v.calendar.google.com", "lang": "ja"},
    "US": {"calendar_id": "en.usa.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "GB": {"calendar_id": "en.uk.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "UK": {"calendar_id": "en.uk.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Alias for GB
    "KR": {"calendar_id": "en.south_korea.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CA": {"calendar_id": "en.canadian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "AU": {"calendar_id": "en.australian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "NZ": {"calendar_id": "en.new_zealand.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "DE": {"calendar_id": "en.german.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "FR": {"calendar_id": "en.french.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "IT": {"calendar_id": "en.italian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "ES": {"calendar_id": "en.spain.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "BR": {"calendar_id": "en.brazilian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "MX": {"calendar_id": "en.mexican.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "IN": {"calendar_id": "en.indian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CN": {"calendar_id": "en.china.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "HK": {"calendar_id": "en.hong_kong.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "SG": {"calendar_id": "en.singapore.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "MY": {"calendar_id": "en.malaysia.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "TH": {"calendar_id": "en.thai.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "VN": {"calendar_id": "en.vietnamese.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "PH": {"calendar_id": "en.philippines.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "ID": {"calendar_id": "en.indonesian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "TR": {"calendar_id": "en.turkish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "SA": {"calendar_id": "en.sa.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "AE": {"calendar_id": "en.ae.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "IL": {"calendar_id": "en.jewish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "ZA": {"calendar_id": "en.sa.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "RU": {"calendar_id": "en.russian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "PL": {"calendar_id": "en.polish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "NL": {"calendar_id": "en.dutch.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "BE": {"calendar_id": "en.be.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "AT": {"calendar_id": "en.austrian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CH": {"calendar_id": "en.ch.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "SE": {"calendar_id": "en.swedish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "NO": {"calendar_id": "en.norwegian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "DK": {"calendar_id": "en.danish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "FI": {"calendar_id": "en.finnish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "PT": {"calendar_id": "en.portuguese.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "GR": {"calendar_id": "en.greek.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "IE": {"calendar_id": "en.irish.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CZ": {"calendar_id": "en.czech.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "HU": {"calendar_id": "en.hungarian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "RO": {"calendar_id": "en.romanian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "BG": {"calendar_id": "en.bulgarian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "HR": {"calendar_id": "en.croatian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "RS": {"calendar_id": "en.rs.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "SI": {"calendar_id": "en.slovenian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "SK": {"calendar_id": "en.slovak.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "LT": {"calendar_id": "en.lithuanian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "LV": {"calendar_id": "en.latvian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "EE": {"calendar_id": "en.ee.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "UA": {"calendar_id": "en.ukrainian.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "BY": {"calendar_id": "en.by.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "AR": {"calendar_id": "en.ar.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CL": {"calendar_id": "en.cl.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CO": {"calendar_id": "en.co.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "PE": {"calendar_id": "en.pe.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "VE": {"calendar_id": "en.ve.official#holiday@group.v.calendar.google.com", "lang": "en"},
    "CR": {"calendar_id": "en.cr.official#holiday@group.v.calendar.google.com", "lang": "en"},
    # Additional countries
    "AO": {"calendar_id": "en.ao.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Angola
    "AW": {"calendar_id": "en.aw.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Aruba
    "BD": {"calendar_id": "en.bd.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Bangladesh
    "BI": {"calendar_id": "en.bi.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Burundi
    "BW": {"calendar_id": "en.bw.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Botswana
    "CW": {"calendar_id": "en.cw.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Curaçao
    "DJ": {"calendar_id": "en.dj.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Djibouti
    "DO": {"calendar_id": "en.do.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Dominican Republic
    "EG": {"calendar_id": "en.eg.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Egypt
    "GE": {"calendar_id": "en.ge.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Georgia
    "HN": {"calendar_id": "en.hn.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Honduras
    "IS": {"calendar_id": "en.is.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Iceland
    "JM": {"calendar_id": "en.jm.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Jamaica
    "KE": {"calendar_id": "en.ke.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Kenya
    "LU": {"calendar_id": "en.lu.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Luxembourg
    "MA": {"calendar_id": "en.ma.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Morocco
    "MW": {"calendar_id": "en.mw.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Malawi
    "MZ": {"calendar_id": "en.mz.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Mozambique
    "NG": {"calendar_id": "en.ng.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Nigeria
    "NI": {"calendar_id": "en.ni.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Nicaragua
    "PY": {"calendar_id": "en.py.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Paraguay
    "YV": {"calendar_id": "en.ve.official#holiday@group.v.calendar.google.com", "lang": "en"},  # Venezuela (YV alias)
}


def get_country_codes_from_json_dir(json_dir: str) -> List[str]:
    """
    Extract country codes from JSON filenames in the specified directory.

    Args:
        json_dir: Path to the directory containing country JSON files

    Returns:
        List of 2-letter country codes (e.g., ['JP', 'US', 'GB'])
    """
    country_codes = []
    json_files = glob.glob(os.path.join(json_dir, "*.json"))

    for file_path in json_files:
        filename = os.path.basename(file_path)
        # Extract country code from filename (e.g., "JP.json" -> "JP")
        country_code = os.path.splitext(filename)[0]
        # Only include 2-letter uppercase codes
        if len(country_code) == 2 and country_code.isupper():
            country_codes.append(country_code)

    return sorted(country_codes)


def build_calendar_url(calendar_id: str, api_key: str, time_min: str, time_max: str, page_token: str = None) -> str:
    """
    Build Google Calendar API URL for fetching events.

    Args:
        calendar_id: Google Calendar ID
        api_key: Google API key
        time_min: ISO format start time (e.g., "2025-01-01T00:00:00Z")
        time_max: ISO format end time (e.g., "2028-01-01T00:00:00Z")
        page_token: Optional pagination token

    Returns:
        Complete API URL
    """
    # URL encode the calendar ID (contains # and @ characters)
    encoded_calendar_id = quote(calendar_id, safe='')

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

    return f"{API_BASE_URL}/{encoded_calendar_id}/events?{urlencode(params)}"


def http_get(url: str) -> dict:
    """
    Perform HTTP GET request and return JSON response.

    Args:
        url: URL to fetch

    Returns:
        Parsed JSON response as dictionary

    Raises:
        RuntimeError: If HTTP request fails
    """
    req = urllib.request.Request(url, headers={"User-Agent": "holiday-updater/1.0"})

    # Create SSL context with certifi's CA bundle
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except NameError:
        # If certifi is not available, fall back to default SSL context
        ssl_context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        data = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} fetching {url}\n{data}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching {url}: {e}") from e


def fetch_holidays_from_gcal(calendar_id: str, api_key: str, start_year: int, end_year: int) -> List[Dict]:
    """
    Fetch holidays from Google Calendar API for the specified year range.

    Args:
        calendar_id: Google Calendar ID
        api_key: Google API key
        start_year: Start year (inclusive)
        end_year: End year (inclusive)

    Returns:
        List of holiday dictionaries with 'date' and 'name' fields
        (duplicates by date are resolved - later entries overwrite earlier ones)
    """
    time_min = f"{start_year}-01-01T00:00:00Z"
    time_max = f"{end_year + 1}-01-01T00:00:00Z"

    holidays = []
    page_token = None

    while True:
        url = build_calendar_url(calendar_id, api_key, time_min, time_max, page_token)
        data = http_get(url)

        for item in data.get("items", []):
            # Extract date from all-day event (start.date) or datetime event
            start = item.get("start", {})
            date_str = start.get("date") or start.get("dateTime", "")[:10]

            if date_str:
                # Convert YYYY-MM-DD to ISO format with time: YYYY-MM-DDTHH:MM:SS.sssZ
                iso_date = f"{date_str}T00:00:00.000Z"
                name = item.get("summary", "")

                holidays.append({
                    "date": iso_date,
                    "name": name
                })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    # Filter to only include years in the requested range
    year_set = set(range(start_year, end_year + 1))
    filtered_holidays = [
        h for h in holidays
        if h["date"] and int(h["date"][:4]) in year_set
    ]

    # Remove duplicates by date - keep last occurrence (usually English)
    # Use dict to preserve order while removing duplicates by date
    unique_holidays = {}
    for holiday in filtered_holidays:
        # Later entries with same date will overwrite earlier ones
        unique_holidays[holiday["date"]] = holiday

    return list(unique_holidays.values())


def load_existing_holidays(file_path: str) -> List[Dict]:
    """
    Load existing holidays from JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        List of holiday dictionaries, or empty list if file doesn't exist
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure it's a list
            if isinstance(data, list):
                return data
            else:
                print(f"WARNING: {file_path} does not contain a list. Treating as empty.", file=sys.stderr)
                return []
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse {file_path}: {e}. Treating as empty.", file=sys.stderr)
        return []


def save_holidays_to_json(file_path: str, holidays: List[Dict]):
    """
    Save holidays to JSON file in compact format (no indentation).

    Args:
        file_path: Path to JSON file
        holidays: List of holiday dictionaries
    """
    with open(file_path, "w", encoding="utf-8") as f:
        # Write in compact format without indentation, matching existing files
        json.dump(holidays, f, ensure_ascii=False, separators=(',', ':'))


def merge_holidays(existing: List[Dict], new_holidays: List[Dict]) -> List[Dict]:
    """
    Merge new holidays with existing ones, avoiding duplicates.

    Args:
        existing: List of existing holiday dictionaries
        new_holidays: List of new holiday dictionaries to add

    Returns:
        Merged and sorted list of holidays
    """
    # Create set of existing holiday keys (date + name) for duplicate detection
    existing_keys = {(h["date"], h["name"]) for h in existing}

    # Add only new holidays that don't already exist
    merged = existing.copy()
    for holiday in new_holidays:
        key = (holiday["date"], holiday["name"])
        if key not in existing_keys:
            merged.append(holiday)
            existing_keys.add(key)

    # Sort by date
    merged.sort(key=lambda h: h["date"])

    return merged


def update_country_holidays(
    country_code: str,
    json_dir: str,
    api_key: str,
    start_year: int,
    end_year: int,
    recreate: bool
) -> bool:
    """
    Update holidays for a specific country.

    Args:
        country_code: 2-letter country code
        json_dir: Directory containing JSON files
        api_key: Google API key
        start_year: Start year
        end_year: End year
        recreate: If True, recreate file; if False, append to existing

    Returns:
        True if successful, False otherwise
    """
    file_path = os.path.join(json_dir, f"{country_code}.json")

    # Check if country is supported
    if country_code not in CALENDAR_MAPPING:
        print(f"WARNING: Country code '{country_code}' not supported in CALENDAR_MAPPING. Skipping.", file=sys.stderr)
        return False

    calendar_info = CALENDAR_MAPPING[country_code]
    calendar_id = calendar_info["calendar_id"]

    # Check file existence for recreate mode
    if recreate and os.path.exists(file_path):
        raise FileExistsError(f"ERROR: File {file_path} already exists. Cannot recreate (use --force to overwrite or remove --recreate flag).")

    print(f"Processing {country_code}: {calendar_id}")

    try:
        # Fetch new holidays from Google Calendar
        new_holidays = fetch_holidays_from_gcal(calendar_id, api_key, start_year, end_year)

        if not new_holidays:
            print(f"  No holidays found for {country_code} ({start_year}-{end_year})")
            return True

        if recreate:
            # Create new file with only new holidays
            final_holidays = new_holidays
            print(f"  Creating new file with {len(final_holidays)} holidays")
        else:
            # Load existing and merge
            existing_holidays = load_existing_holidays(file_path)
            final_holidays = merge_holidays(existing_holidays, new_holidays)
            added_count = len(final_holidays) - len(existing_holidays)
            print(f"  Added {added_count} new holidays (total: {len(final_holidays)})")

        # Save to file
        save_holidays_to_json(file_path, final_holidays)

        return True

    except Exception as e:
        print(f"ERROR processing {country_code}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Update holiday definitions in JSON files using Google Calendar API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Append holidays for 2025-2027 to existing files
  python update_holidays.py --start-year 2025 --end-year 2027

  # Create new files (error if files exist)
  python update_holidays.py --start-year 2025 --end-year 2027 --recreate

  # Force recreate (overwrite existing files)
  python update_holidays.py --start-year 2025 --end-year 2027 --recreate --force
        """
    )

    parser.add_argument(
        "--start-year",
        type=int,
        required=True,
        help="Start year (YYYY, e.g., 2025)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        required=True,
        help="End year (YYYY, e.g., 2027)"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate JSON files (error if files exist, unless --force is used)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite when using --recreate"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("GCAL_API_KEY"),
        help="Google API key (or set GCAL_API_KEY environment variable)"
    )
    parser.add_argument(
        "--json-dir",
        default="json",
        help="Directory containing country JSON files (default: json)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.api_key:
        print("ERROR: API key required. Set GCAL_API_KEY environment variable or use --api-key.", file=sys.stderr)
        sys.exit(1)

    if args.start_year > args.end_year:
        print("ERROR: start-year must be <= end-year", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.json_dir):
        print(f"ERROR: JSON directory '{args.json_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Get country codes from JSON directory
    country_codes = get_country_codes_from_json_dir(args.json_dir)

    if not country_codes:
        print(f"ERROR: No country JSON files found in '{args.json_dir}'", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(country_codes)} countries: {', '.join(country_codes)}")
    print(f"Year range: {args.start_year}-{args.end_year}")
    print(f"Mode: {'RECREATE' if args.recreate else 'APPEND'}")
    if args.recreate and args.force:
        print("WARNING: --force is set. Existing files will be overwritten!")
    print()

    # Process each country
    success_count = 0
    error_count = 0

    for country_code in country_codes:
        try:
            # Handle force flag for recreate mode
            if args.recreate and args.force:
                file_path = os.path.join(args.json_dir, f"{country_code}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)

            if update_country_holidays(
                country_code,
                args.json_dir,
                args.api_key,
                args.start_year,
                args.end_year,
                args.recreate
            ):
                success_count += 1
            else:
                error_count += 1

        except FileExistsError as e:
            print(str(e), file=sys.stderr)
            error_count += 1
        except Exception as e:
            print(f"ERROR: Unexpected error processing {country_code}: {e}", file=sys.stderr)
            error_count += 1

    print()
    print(f"Completed: {success_count} successful, {error_count} errors")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
