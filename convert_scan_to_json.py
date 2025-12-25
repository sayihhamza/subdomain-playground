#!/usr/bin/env python3
"""
Convert previous_scanned.txt to all_results.json format
"""
import json
import re

def calculate_risk_and_confidence(http_status: int, provider: str, cname: str) -> tuple:
    """
    Calculate risk level and confidence score based on HTTP status, provider, and CNAME.

    Risk levels:
    - high: 403/404/500 with Shopify provider (potential takeover)
    - medium: 301/302/308 redirects with Shopify (might be configured)
    - low: non-Shopify or unclear cases
    """
    is_shopify = provider == "Shopify" or "shopify" in cname.lower()

    if http_status in (404, 500):
        # 404/500 with Shopify = high risk
        if is_shopify:
            return "high", 90
        return "medium", 60

    if http_status == 403:
        # 403 with Shopify = high risk
        if is_shopify:
            return "high", 85
        return "low", 40

    if http_status == 409:
        # 409 Conflict
        if is_shopify:
            return "high", 85
        return "medium", 60

    if http_status in (301, 302, 307, 308):
        # Redirects - medium risk
        if is_shopify:
            return "medium", 70
        return "low", 40

    # Default
    return "low", 30


def parse_scan_line(line: str) -> dict | None:
    """
    Parse a single scan result line from the text file.
    Format: SUBDOMAIN  STATUS  PROVIDER  CNAME  EVIDENCE  MESSAGE

    Also handles Kaggle notebook log format with timestamp prefix:
    Example: "381.3s	1318	account.womensbest.com    403    Shopify    ..."
    """
    # Skip non-data lines
    if not line.strip():
        return None
    if 'complete |' in line or 'Rate:' in line:
        return None
    if 'go: downloading' in line or 'github.com/' in line:
        return None

    # Strip Kaggle timestamp prefix if present (format: "123.4s\t1234\t")
    kaggle_prefix_match = re.match(r'^\d+\.\d+s\s+\d+\s+', line)
    if kaggle_prefix_match:
        line = line[kaggle_prefix_match.end():]

    # Skip header/separator lines (after stripping prefix)
    if line.startswith('=') or line.startswith('[') or line.startswith('SUBDOMAIN'):
        return None

    # Split by multiple spaces (table format)
    parts = re.split(r'\s{2,}', line.strip())

    if len(parts) < 4:
        return None

    subdomain = parts[0].strip()

    # Validate subdomain looks like a domain
    if '.' not in subdomain:
        return None

    # Try to parse status as integer
    try:
        http_status = int(parts[1].strip())
    except (ValueError, IndexError):
        return None

    provider = parts[2].strip() if len(parts) > 2 else "-"

    # Handle CNAME - might be truncated with ".." or have "(X hops)"
    cname_raw = parts[3].strip() if len(parts) > 3 else ""

    # Clean up truncated CNAMEs (ending with "..")
    cname = cname_raw.replace("..", "")

    # Extract hops info and clean CNAME
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
    }


def convert_scan_file(input_file: str, output_file: str, merge: bool = True):
    """
    Convert the scan text file to JSON format.
    If merge=True, merge with existing results in output_file.
    """
    results = []
    seen_subdomains = set()

    # Load existing results if merging
    if merge:
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                print(f"Loaded {len(existing)} existing entries from {output_file}")
                for entry in existing:
                    seen_subdomains.add(entry['subdomain'])
                    results.append(entry)
        except FileNotFoundError:
            print(f"No existing {output_file} found, creating new file")

    print(f"Reading {input_file}...")

    new_count = 0
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            result = parse_scan_line(line)
            if result and result['subdomain'] not in seen_subdomains:
                results.append(result)
                seen_subdomains.add(result['subdomain'])
                new_count += 1

            if line_num % 10000 == 0:
                print(f"  Processed {line_num} lines...")

    print(f"\nAdded {new_count} new entries (total: {len(results)})")

    # Sort by authority_score (if present) then confidence_score (highest first)
    results.sort(key=lambda x: (-x.get('authority_score', 0), -x['confidence_score'], x['subdomain']))

    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Done! Wrote {len(results)} entries to {output_file}")

    # Print summary
    risk_counts = {}
    for r in results:
        risk_counts[r['risk_level']] = risk_counts.get(r['risk_level'], 0) + 1

    print("\nRisk level summary:")
    for level in ['high', 'medium', 'low']:
        count = risk_counts.get(level, 0)
        print(f"  {level}: {count}")


if __name__ == "__main__":
    convert_scan_file("previous_scanned.txt", "all_results.json")
