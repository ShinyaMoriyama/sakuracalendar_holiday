#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for update_holidays.py

This test verifies that existing holiday entries remain unchanged when
new holidays are added. It compares the state before and after running
update_holidays.py to ensure data integrity.

Usage:
  export GCAL_API_KEY="YOUR_API_KEY"
  python test_update_holidays.py --start-year 2025 --end-year 2027
"""

import json
import os
import sys
import argparse
import subprocess
import tempfile
import shutil
from typing import Dict, List, Set


def load_json_file(file_path: str) -> List[Dict]:
    """Load JSON file and return as list of dictionaries."""
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_holiday_key(holiday: Dict) -> str:
    """Create unique key for a holiday entry."""
    return f"{holiday['date']}:{holiday['name']}"


def backup_json_files(json_dir: str, backup_dir: str) -> Dict[str, List[Dict]]:
    """
    Backup all JSON files and return their contents.

    Args:
        json_dir: Directory containing JSON files
        backup_dir: Directory to store backups

    Returns:
        Dictionary mapping country code to list of holiday entries
    """
    os.makedirs(backup_dir, exist_ok=True)
    snapshot = {}

    for filename in os.listdir(json_dir):
        if not filename.endswith('.json'):
            continue

        country_code = os.path.splitext(filename)[0]
        if len(country_code) != 2 or not country_code.isupper():
            continue

        src_path = os.path.join(json_dir, filename)
        dst_path = os.path.join(backup_dir, filename)

        # Backup file
        shutil.copy2(src_path, dst_path)

        # Load and store contents
        snapshot[country_code] = load_json_file(src_path)

    return snapshot


def compare_snapshots(before: Dict[str, List[Dict]], after: Dict[str, List[Dict]]) -> Dict:
    """
    Compare before and after snapshots to detect changes in existing entries.

    Args:
        before: Snapshot before update
        after: Snapshot after update

    Returns:
        Dictionary containing test results:
        - 'passed': bool
        - 'errors': list of error messages
        - 'stats': statistics about changes
    """
    errors = []
    stats = {
        'countries_checked': 0,
        'total_entries_before': 0,
        'total_entries_after': 0,
        'unchanged_entries': 0,
        'new_entries': 0,
        'modified_entries': 0,
        'deleted_entries': 0,
    }

    # Check all countries that existed before
    for country_code, before_holidays in before.items():
        stats['countries_checked'] += 1
        stats['total_entries_before'] += len(before_holidays)

        if country_code not in after:
            errors.append(f"ERROR: Country {country_code} missing after update")
            continue

        after_holidays = after[country_code]
        stats['total_entries_after'] += len(after_holidays)

        # Create sets of holiday keys
        before_keys = {create_holiday_key(h) for h in before_holidays}
        after_keys = {create_holiday_key(h) for h in after_holidays}

        # Check for deleted entries (should not happen in append mode)
        deleted = before_keys - after_keys
        if deleted:
            stats['deleted_entries'] += len(deleted)
            for key in deleted:
                errors.append(f"ERROR: {country_code} - Entry deleted: {key}")

        # Check that all existing entries remain unchanged
        for before_holiday in before_holidays:
            key = create_holiday_key(before_holiday)

            # Find matching entry in after snapshot
            after_match = None
            for after_holiday in after_holidays:
                if create_holiday_key(after_holiday) == key:
                    after_match = after_holiday
                    break

            if after_match is None:
                # Already counted in deleted entries
                continue

            # Verify the entry is identical
            if before_holiday == after_match:
                stats['unchanged_entries'] += 1
            else:
                stats['modified_entries'] += 1
                errors.append(
                    f"ERROR: {country_code} - Entry modified:\n"
                    f"  Before: {before_holiday}\n"
                    f"  After:  {after_match}"
                )

        # Count new entries (this is expected)
        new_entries = after_keys - before_keys
        stats['new_entries'] += len(new_entries)

    return {
        'passed': len(errors) == 0,
        'errors': errors,
        'stats': stats,
    }


def run_update_script(args: argparse.Namespace) -> bool:
    """
    Run update_holidays.py with specified arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if script succeeded, False otherwise
    """
    cmd = [
        sys.executable,
        'update_holidays.py',
        '--start-year', str(args.start_year),
        '--end-year', str(args.end_year),
        '--json-dir', args.json_dir,
    ]

    if args.api_key:
        cmd.extend(['--api-key', args.api_key])

    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def print_results(result: Dict):
    """Print test results in a readable format."""
    print("\n" + "=" * 70)
    print("REGRESSION TEST RESULTS")
    print("=" * 70)

    stats = result['stats']
    print(f"\nCountries checked: {stats['countries_checked']}")
    print(f"Entries before:    {stats['total_entries_before']}")
    print(f"Entries after:     {stats['total_entries_after']}")
    print(f"  - Unchanged:     {stats['unchanged_entries']}")
    print(f"  - New:           {stats['new_entries']}")
    print(f"  - Modified:      {stats['modified_entries']}")
    print(f"  - Deleted:       {stats['deleted_entries']}")

    if result['passed']:
        print("\n✓ TEST PASSED: All existing entries remain unchanged")
    else:
        print("\n✗ TEST FAILED: Some existing entries were modified or deleted")
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors']:
            print(error)

    print("=" * 70)


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description="Regression test for update_holidays.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This test ensures that existing holiday entries remain unchanged when
running update_holidays.py. It creates a backup, runs the update script,
and compares the results.

Example:
  export GCAL_API_KEY="YOUR_API_KEY"
  python test_update_holidays.py --start-year 2025 --end-year 2027
        """
    )

    parser.add_argument(
        '--start-year',
        type=int,
        required=True,
        help='Start year (YYYY, e.g., 2025)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        required=True,
        help='End year (YYYY, e.g., 2027)'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('GCAL_API_KEY'),
        help='Google API key (or set GCAL_API_KEY environment variable)'
    )
    parser.add_argument(
        '--json-dir',
        default='json',
        help='Directory containing country JSON files (default: json)'
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

    # Create temporary backup directory
    with tempfile.TemporaryDirectory() as backup_dir:
        print("=" * 70)
        print("REGRESSION TEST FOR update_holidays.py")
        print("=" * 70)
        print(f"\nStep 1: Creating backup in {backup_dir}")

        # Create snapshot of current state
        before_snapshot = backup_json_files(args.json_dir, backup_dir)
        print(f"  Backed up {len(before_snapshot)} countries")

        # Run update script
        print(f"\nStep 2: Running update_holidays.py")
        if not run_update_script(args):
            print("\nERROR: update_holidays.py failed", file=sys.stderr)
            sys.exit(1)

        # Create snapshot of after state
        print(f"\nStep 3: Comparing results")
        after_snapshot = {}
        for country_code in before_snapshot.keys():
            file_path = os.path.join(args.json_dir, f"{country_code}.json")
            after_snapshot[country_code] = load_json_file(file_path)

        # Compare snapshots
        result = compare_snapshots(before_snapshot, after_snapshot)

        # Print results
        print_results(result)

        # Exit with appropriate code
        sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
