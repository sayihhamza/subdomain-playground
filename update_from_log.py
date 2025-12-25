#!/usr/bin/env python3
"""
Update all_results.json and scan_progress.json from Kaggle log output.

Usage:
    1. Copy Kaggle log output to clipboard or save to a file
    2. Run: python update_from_log.py < paste_log.txt
       Or:  python update_from_log.py --file kaggle_output.txt
       Or:  python update_from_log.py --paste  (reads from stdin until EOF)

The script will:
    - Parse scan results from the log (handles Kaggle timestamp format)
    - Merge new entries into all_results.json (avoiding duplicates)
    - Update scan_progress.json with the latest row number
"""
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime


RESULTS_FILE = Path("all_results.json")
PROGRESS_FILE = Path("scan_progress.json")


def calculate_risk_and_confidence(http_status: int, provider: str, cname: str) -> tuple:
    """Calculate risk level and confidence score."""
    is_shopify = provider == "Shopify" or (cname and "shopify" in cname.lower())

    if http_status in (404, 500):
        return ("high", 90) if is_shopify else ("medium", 60)
    if http_status == 403:
        return ("high", 85) if is_shopify else ("low", 40)
    if http_status == 409:
        return ("high", 85) if is_shopify else ("medium", 60)
    if http_status in (301, 302, 307, 308):
        return ("medium", 70) if is_shopify else ("low", 40)
    return "low", 30


def parse_log_line(line: str) -> tuple[dict | None, int | None]:
    """
    Parse a scan result line from Kaggle log output.

    Returns:
        tuple: (result_dict or None, row_number or None)
    """
    if not line.strip():
        return None, None

    # Skip non-data lines
    skip_patterns = [
        'complete |', 'Rate:', 'go: downloading', 'github.com/',
        'Cloning', 'Building', 'Installing', 'Downloading',
        'RESUME MODE', 'Skipping', 'Remaining:', 'Starting',
        'Progress saved', 'All domains', 'Found ', 'Saved to',
        'Error', 'Warning', 'Debugger', 'SUBDOMAIN', '====',
        'total ', 'drwx', '-rw-', 'Shopify takeover'
    ]
    for pattern in skip_patterns:
        if pattern in line:
            return None, None

    # Extract Kaggle timestamp and row number if present
    # Format: "381.3s	1318	subdomain.com    403    Shopify    ..."
    row_number = None
    kaggle_match = re.match(r'^(\d+\.\d+)s\s+(\d+)\s+', line)
    if kaggle_match:
        row_number = int(kaggle_match.group(2))
        line = line[kaggle_match.end():]

    # Skip header/separator lines
    if line.startswith('=') or line.startswith('[') or line.startswith('SUBDOMAIN'):
        return None, row_number

    # Split by multiple spaces (table format)
    parts = re.split(r'\s{2,}', line.strip())

    if len(parts) < 4:
        return None, row_number

    subdomain = parts[0].strip()

    # Validate subdomain
    if '.' not in subdomain or subdomain.startswith('-'):
        return None, row_number

    # Parse HTTP status
    try:
        http_status = int(parts[1].strip())
    except (ValueError, IndexError):
        return None, row_number

    provider = parts[2].strip() if len(parts) > 2 else "-"

    # Handle CNAME
    cname_raw = parts[3].strip() if len(parts) > 3 else ""
    cname = cname_raw.replace("..", "")

    # Extract hops info
    hops_match = re.search(r'\((\d+)\s*hops?\)', cname)
    if hops_match:
        hops = hops_match.group(0)
        cname_clean = re.sub(r'\s*\(\d+\s*hops?\)', '', cname).strip()
        cname = f"{cname_clean} {hops}"

    risk_level, confidence_score = calculate_risk_and_confidence(http_status, provider, cname)

    return {
        "subdomain": subdomain,
        "http_status": http_status,
        "provider": provider,
        "cname": cname,
        "risk_level": risk_level,
        "confidence_score": confidence_score
    }, row_number


def load_existing_results() -> tuple[list, set]:
    """Load existing results and return (results_list, subdomains_set)."""
    results = []
    subdomains = set()

    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE, 'r') as f:
                results = json.load(f)
                subdomains = {r['subdomain'] for r in results}
        except (json.JSONDecodeError, IOError):
            pass

    return results, subdomains


def load_progress() -> dict:
    """Load current progress."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'last_row': 0, 'total_scanned': 0}


def save_results(results: list):
    """Save results sorted by authority_score then confidence_score."""
    results.sort(key=lambda x: (
        -x.get('authority_score', 0),
        -x['confidence_score'],
        x['subdomain']
    ))

    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)


def save_progress(last_row: int, total_scanned: int, scanned_domains: list = None):
    """Save progress to file."""
    data = {
        'last_row': last_row,
        'total_scanned': total_scanned,
        'updated': datetime.now().isoformat()
    }
    if scanned_domains:
        data['scanned_domains'] = scanned_domains

    with open(PROGRESS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def process_log(lines: list[str]) -> dict:
    """
    Process log lines and update results/progress.

    Returns:
        dict with stats about what was updated
    """
    results, existing_subdomains = load_existing_results()
    progress = load_progress()

    new_entries = []
    max_row = progress.get('last_row', 0)
    parsed_count = 0

    for line in lines:
        result, row_number = parse_log_line(line)

        if row_number and row_number > max_row:
            max_row = row_number

        if result:
            parsed_count += 1
            if result['subdomain'] not in existing_subdomains:
                new_entries.append(result)
                existing_subdomains.add(result['subdomain'])

    # Merge new entries
    if new_entries:
        results.extend(new_entries)
        save_results(results)

    # Update progress if we found a higher row number
    if max_row > progress.get('last_row', 0):
        save_progress(max_row, len(existing_subdomains))

    return {
        'lines_processed': len(lines),
        'entries_parsed': parsed_count,
        'new_entries': len(new_entries),
        'total_results': len(results),
        'last_row': max_row,
        'previous_row': progress.get('last_row', 0)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Update results from Kaggle log output',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Paste log and press Ctrl+D (Mac/Linux) or Ctrl+Z (Windows) when done:
    python update_from_log.py --paste

    # From a file:
    python update_from_log.py --file kaggle_output.txt

    # Pipe from clipboard (Mac):
    pbpaste | python update_from_log.py

    # Redirect from file:
    python update_from_log.py < log.txt
"""
    )
    parser.add_argument(
        '--file', '-f',
        help='Read log from file instead of stdin'
    )
    parser.add_argument(
        '--paste', '-p',
        action='store_true',
        help='Interactive mode: paste log, then Ctrl+D to process'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Parse only, do not save changes'
    )

    args = parser.parse_args()

    # Read input
    if args.file:
        with open(args.file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f"Reading from file: {args.file}")
    elif args.paste or sys.stdin.isatty():
        print("Paste Kaggle log output below, then press Ctrl+D (Mac/Linux) or Ctrl+Z+Enter (Windows):")
        print("-" * 60)
        lines = sys.stdin.readlines()
        print("-" * 60)
    else:
        # Piped input
        lines = sys.stdin.readlines()

    if not lines:
        print("No input received.")
        return 1

    print(f"\nProcessing {len(lines)} lines...")

    if args.dry_run:
        # Dry run - just parse and show what would happen
        results, existing = load_existing_results()
        progress = load_progress()

        new_count = 0
        max_row = progress.get('last_row', 0)

        for line in lines:
            result, row_number = parse_log_line(line)
            if row_number and row_number > max_row:
                max_row = row_number
            if result and result['subdomain'] not in existing:
                new_count += 1
                existing.add(result['subdomain'])

        print(f"\n[DRY RUN] Would add {new_count} new entries")
        print(f"[DRY RUN] Would update last_row from {progress.get('last_row', 0)} to {max_row}")
        return 0

    # Process and save
    stats = process_log(lines)

    print(f"\n{'='*50}")
    print(f"RESULTS UPDATED")
    print(f"{'='*50}")
    print(f"  Lines processed:    {stats['lines_processed']}")
    print(f"  Entries parsed:     {stats['entries_parsed']}")
    print(f"  New entries added:  {stats['new_entries']}")
    print(f"  Total in results:   {stats['total_results']}")
    print(f"")
    print(f"  Progress updated:   row {stats['previous_row']} -> {stats['last_row']}")
    print(f"{'='*50}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
