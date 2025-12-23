#!/usr/bin/env python3
"""
Subdomain Takeover Scanner - Clean CLI Interface

Simple, professional command-line interface for subdomain vulnerability scanning.
Supports automatic resume on restart (for Kaggle/long-running scans).

Usage:
    python scan.py <domain> [options]
    python scan.py -l domains.txt [options]

Examples:
    python scan.py example.com
    python scan.py example.com --output results/
    python scan.py example.com --json
    python scan.py -l domains.txt --workers 10

Resume functionality:
    - Progress is saved to scan_progress.json after each domain
    - Results are saved to all_results.json incrementally
    - On restart, already-scanned domains are automatically skipped
"""
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file from current directory
except ImportError:
    pass  # python-dotenv not installed, skip

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.orchestrator_v2 import OrchestratorV2


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )


def load_existing_results(filepath: Path) -> list:
    """Load existing results from JSON file"""
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


# =============================================================================
# RESUME FUNCTIONALITY
# =============================================================================

PROGRESS_FILE = Path("scan_progress.json")
RESULTS_FILE = Path("all_results.json")


def load_progress() -> dict:
    """
    Load scan progress from file.

    Returns:
        dict with 'last_row' (0-indexed row to resume FROM) and 'scanned_domains' set
    """
    progress = {
        'scanned_domains': set(),
        'last_row': 0,
        'total_scanned': 0
    }

    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                data = json.load(f)
                progress['last_row'] = data.get('last_row', 0)
                progress['total_scanned'] = data.get('total_scanned', 0)
                # Load scanned domains list if available
                progress['scanned_domains'] = set(data.get('scanned_domains', []))
        except (json.JSONDecodeError, IOError):
            pass

    return progress


def save_progress(scanned_domains: set, last_row: int):
    """
    Save scan progress to file.

    Args:
        scanned_domains: Set of domains that have been scanned
        last_row: Last row index processed
    """
    # Only save domain count to keep file small (domains can be inferred from results)
    data = {
        'last_row': last_row,
        'total_scanned': len(scanned_domains),
        'updated': datetime.now().isoformat(),
        # Save list of scanned domains for accurate resume
        'scanned_domains': list(scanned_domains)
    }

    with open(PROGRESS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def calculate_risk_and_confidence(http_status: int, provider: str, cname: str) -> tuple:
    """
    Calculate risk level and confidence score based on HTTP status, provider, and CNAME.
    """
    is_shopify = provider == "Shopify" or (cname and "shopify" in cname.lower())

    if http_status in (404, 500):
        if is_shopify:
            return "high", 90
        return "medium", 60

    if http_status == 403:
        if is_shopify:
            return "high", 85
        return "low", 40

    if http_status == 409:
        if is_shopify:
            return "high", 85
        return "medium", 60

    if http_status in (301, 302, 307, 308):
        if is_shopify:
            return "medium", 70
        return "low", 40

    return "low", 30


def save_result_to_all_results(subdomain_data: dict, results_file: Path = RESULTS_FILE):
    """
    Append a single result to all_results.json (incremental save).

    Args:
        subdomain_data: Dict with subdomain scan result
        results_file: Path to results JSON file
    """
    # Load existing results
    existing = []
    existing_subdomains = set()

    if results_file.exists():
        try:
            with open(results_file, 'r') as f:
                existing = json.load(f)
                existing_subdomains = {r.get('subdomain') for r in existing}
        except (json.JSONDecodeError, IOError):
            pass

    # Only add if not duplicate
    if subdomain_data.get('subdomain') not in existing_subdomains:
        existing.append(subdomain_data)

        # Save back
        with open(results_file, 'w') as f:
            json.dump(existing, f, indent=2)

        return True
    return False


def save_results_incremental(new_results: list, filepath: Path):
    """
    Save results incrementally - merge with existing results avoiding duplicates
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results
    existing = load_existing_results(filepath)
    existing_subdomains = {r.get('subdomain') for r in existing}

    # Add only new results (avoid duplicates)
    added = 0
    for result in new_results:
        if result.get('subdomain') not in existing_subdomains:
            existing.append(result)
            existing_subdomains.add(result.get('subdomain'))
            added += 1

    # Save merged results
    with open(filepath, 'w') as f:
        json.dump(existing, f, indent=2)

    return len(existing), added


def parse_status_code_patterns(pattern_str: str) -> list:
    """
    Parse status code patterns with wildcard support

    Args:
        pattern_str: Comma-separated status codes or patterns (e.g., "403,404,4*,5*")

    Returns:
        List of integer status codes

    Examples:
        "403,404,409" -> [403, 404, 409]
        "4*" -> [400, 401, 402, 403, ..., 499]
        "4*,500" -> [400-499, 500]
        "40*" -> [400, 401, 402, ..., 409]
    """
    status_codes = set()

    for pattern in pattern_str.split(','):
        pattern = pattern.strip()

        if not pattern:
            continue

        # Check for wildcard pattern
        if '*' in pattern:
            # Extract the prefix (everything before *)
            prefix = pattern.replace('*', '')

            if not prefix:
                # Just "*" - invalid
                continue

            # Validate prefix is numeric
            if not prefix.isdigit():
                continue

            # Generate range based on prefix length
            prefix_len = len(prefix)

            if prefix_len == 1:
                # Single digit prefix (e.g., "4*" -> 400-499)
                start = int(prefix) * 100
                end = start + 100
            elif prefix_len == 2:
                # Two digit prefix (e.g., "40*" -> 400-409)
                start = int(prefix) * 10
                end = start + 10
            else:
                # Three digit prefix (e.g., "40*" is actually just 400-409)
                # For safety, just add the specific code
                try:
                    status_codes.add(int(prefix))
                except ValueError:
                    pass
                continue

            # Add all codes in range
            for code in range(start, end):
                # Only add valid HTTP status codes (100-599)
                if 100 <= code <= 599:
                    status_codes.add(code)
        else:
            # Specific status code
            try:
                code = int(pattern)
                if 100 <= code <= 599:
                    status_codes.add(code)
            except ValueError:
                # Invalid pattern, skip
                pass

    return sorted(list(status_codes))


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Subdomain Takeover Scanner - Professional vulnerability detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python scan.py example.com
  python scan.py example.com --output results/
  python scan.py -l domains.txt --workers 10
  python scan.py example.com --only-vulnerable
  python scan.py example.com --json --quiet

  # Quick single domain scan:
  python scan.py --scan-single gymshark.com --provider Shopify

  # Domain collection examples:
  python scan.py --collect-domains bug_bounty --provider Shopify
  python scan.py --collect-domains tranco --tranco-top 5000 --min-authority 70
  python scan.py --collect-domains shopify --workers 10
  python scan.py --collect-domains myleadfox --provider Shopify
  python scan.py --collect-domains myleadfox --provider Shopify --limit 100

For more information, visit: https://github.com/yourusername/subdomain-scanner
        '''
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        'domain',
        nargs='?',
        help='Target domain to scan'
    )
    input_group.add_argument(
        '-l', '--list',
        dest='domain_list',
        help='File containing list of domains (one per line)'
    )
    input_group.add_argument(
        '--collect-domains',
        choices=['bug_bounty', 'tranco', 'shopify', 'myleadfox'],
        help='Auto-collect domains from source before scanning'
    )
    input_group.add_argument(
        '--scan-single',
        metavar='DOMAIN',
        help='Scan a single domain directly (e.g., gymshark.com)'
    )
    input_group.add_argument(
        '--google-sheet',
        metavar='URL',
        help='Read domains from a public Google Sheet URL'
    )

    # Google Sheets options (used with --google-sheet)
    parser.add_argument(
        '--sheet-name',
        default='domains',
        help='Name of the Google Sheet tab to read from (default: domains)'
    )
    parser.add_argument(
        '--sheet-column',
        default='Website',
        help='Column name containing domains (default: Website)'
    )

    # Output options
    parser.add_argument(
        '-o', '--output',
        default='data/scans',
        help='Output directory (default: data/scans)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='JSON output only (no human-readable summary)'
    )
    parser.add_argument(
        '--only-vulnerable',
        action='store_true',
        help='Only output vulnerable findings'
    )

    # Scan options
    parser.add_argument(
        '--mode',
        choices=['quick', 'full'],
        default='quick',
        help='Scan mode: quick (passive only, fast) or full (complete, slower) (default: quick)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of concurrent workers for multi-domain scans (default: 5)'
    )
    parser.add_argument(
        '--provider',
        help='Filter results by specific cloud provider (e.g., Shopify, AWS, Azure)'
    )
    parser.add_argument(
        '--filter-status',
        help='Only show subdomains with specific HTTP status codes. Supports wildcards: "403,404" or "4*" (all 4xx) or "40*" (400-409)'
    )
    parser.add_argument(
        '--require-cname',
        action='store_true',
        help='Only show subdomains with CNAME records (filters out direct A records)'
    )
    parser.add_argument(
        '--require-cname-contains',
        type=str,
        metavar='PATTERN',
        help='Only show subdomains where CNAME chain contains pattern (e.g., "shopify", "myshopify.com"). Checks entire CNAME chain, case-insensitive.'
    )
    parser.add_argument(
        '--shopify-takeover-only',
        action='store_true',
        help='Only show high-priority Shopify takeover candidates (CNAME to myshopify.com + 403/404)'
    )

    # Domain collection options
    parser.add_argument(
        '--tranco-top',
        type=int,
        default=10000,
        help='Number of top Tranco domains to collect (default: 10000)'
    )
    parser.add_argument(
        '--min-authority',
        type=int,
        default=60,
        help='Minimum authority score for Tranco domains (default: 60)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of domains to scan (e.g., --limit 100 for first 100 domains)'
    )

    # Resume options
    parser.add_argument(
        '--resume',
        action='store_true',
        default=True,
        help='Resume from last scan position (default: enabled)'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh, ignore previous progress'
    )
    parser.add_argument(
        '--progress-file',
        default='scan_progress.json',
        help='Path to progress file (default: scan_progress.json)'
    )
    parser.add_argument(
        '--results-file',
        default='all_results.json',
        help='Path to results file (default: all_results.json)'
    )

    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output (debug mode)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimal output (only results)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.domain_list:
        domain_list_path = Path(args.domain_list)
        if not domain_list_path.exists():
            parser.error(f"Domain list file not found: {args.domain_list}")

    # Validate Tranco options
    if args.tranco_top < 1 or args.tranco_top > 1000000:
        parser.error("--tranco-top must be between 1 and 1000000")

    if args.min_authority < 1 or args.min_authority > 100:
        parser.error("--min-authority must be between 1 and 100")

    return args


def save_results(results: dict, output_dir: Path, domain: str, args):
    """
    Save scan results to files

    Args:
        results: Scan results dictionary
        output_dir: Output directory
        domain: Target domain
        args: Command-line arguments
    """
    # Create timestamped directory
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    scan_dir = output_dir / f"{domain}_{timestamp}"
    scan_dir.mkdir(parents=True, exist_ok=True)

    # Save complete results
    all_file = scan_dir / 'all_findings.json'
    with open(all_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Save vulnerable-only results
    vulnerable_results = {
        'domain': results['domain'],
        'scan_time': timestamp,
        'vulnerable_count': results['statistics'].get('vulnerable', 0),
        'findings': results['vulnerable']
    }

    vulnerable_file = scan_dir / 'vulnerable.json'
    with open(vulnerable_file, 'w') as f:
        json.dump(vulnerable_results, f, indent=2)

    # Save by severity
    if results['vulnerable']:
        for severity in ['critical', 'high', 'medium', 'low']:
            severity_findings = [
                f for f in results['vulnerable']
                if f.get('risk_level') == severity
            ]

            if severity_findings:
                severity_file = scan_dir / f'{severity}.json'
                with open(severity_file, 'w') as f:
                    json.dump({
                        'domain': results['domain'],
                        'severity': severity,
                        'count': len(severity_findings),
                        'findings': severity_findings
                    }, f, indent=2)

    # Generate human-readable summary (unless --json)
    if not args.json:
        summary_file = scan_dir / 'summary.txt'
        generate_summary(results, summary_file)

    return scan_dir


def generate_summary(results: dict, output_file: Path):
    """Generate human-readable summary"""
    with open(output_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("SUBDOMAIN TAKEOVER SCAN REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Domain: {results['domain']}\n")
        f.write(f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        stats = results['statistics']
        f.write(f"Total Subdomains Found:     {stats.get('total_found', 0):,}\n")
        f.write(f"DNS Validated:              {stats.get('dns_validated', 0):,}\n")
        f.write(f"Wildcards Filtered:         {stats.get('wildcards_filtered', 0):,}\n")
        f.write(f"Cloud-Hosted:               {stats.get('cloud_hosted', 0):,}\n")
        f.write(f"Vulnerable:                 {stats.get('vulnerable', 0):,}\n\n")

        f.write("By Severity:\n")
        f.write(f"  CRITICAL:  {stats.get('critical', 0)}\n")
        f.write(f"  HIGH:      {stats.get('high', 0)}\n")
        f.write(f"  MEDIUM:    {stats.get('medium', 0)}\n")
        f.write(f"  LOW:       {stats.get('low', 0)}\n\n")

        # Provider breakdown
        if 'provider_identification' in results.get('phase_results', {}):
            providers = results['phase_results']['provider_identification'].get('providers', {})
            if providers:
                f.write("By Cloud Provider:\n")
                for provider, pstats in providers.items():
                    f.write(f"  {provider}: {pstats['count']} (IP confirmed: {pstats['ip_confirmed']})\n")
                f.write("\n")

        # Vulnerable findings
        if results['vulnerable']:
            f.write("=" * 80 + "\n")
            f.write("VULNERABLE FINDINGS\n")
            f.write("=" * 80 + "\n\n")

            for i, finding in enumerate(results['vulnerable'], 1):
                f.write(f"[{i}] {finding['subdomain']}\n")
                f.write(f"    Provider: {finding.get('provider', 'Unknown')}\n")
                if finding.get('cname'):
                    f.write(f"    CNAME: {finding['cname']}\n")
                if finding.get('http_status'):
                    f.write(f"    HTTP Status: {finding['http_status']}\n")
                if finding.get('ip_confirmed'):
                    f.write(f"    IP Confirmed: Yes\n")
                f.write(f"    Risk Level: {finding.get('risk_level', 'unknown').upper()}\n")
                if finding.get('fingerprint_matched'):
                    f.write(f"    Fingerprint: {finding['fingerprint_matched']}\n")
                f.write("\n")


def print_results_summary(results: dict, args):
    """Print results summary to console"""
    if args.quiet:
        # Only print vulnerable count
        print(results['statistics'].get('vulnerable', 0))
        return

    if args.json:
        # Only print JSON
        if args.only_vulnerable:
            print(json.dumps(results['vulnerable'], indent=2))
        else:
            print(json.dumps(results, indent=2))
        return

    # Human-readable summary
    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)

    stats = results['statistics']
    print(f"Total subdomains found: {stats.get('total_found', 0):,}")
    print(f"Cloud-hosted: {stats.get('cloud_hosted', 0):,}")
    print(f"Vulnerable: {stats.get('vulnerable', 0):,}")

    if stats.get('vulnerable', 0) > 0:
        print(f"\nBy Severity:")
        print(f"  CRITICAL: {stats.get('critical', 0)}")
        print(f"  HIGH: {stats.get('high', 0)}")
        print(f"  MEDIUM: {stats.get('medium', 0)}")
        print(f"  LOW: {stats.get('low', 0)}")


def main():
    """Main entry point"""
    args = parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose and not args.quiet)

    # Load configuration
    try:
        config = Config()
    except Exception as e:
        print(f"Error loading configuration: {str(e)}", file=sys.stderr)
        return 1

    # Initialize orchestrator
    orchestrator = OrchestratorV2(config)

    # Collect domains from source if requested
    if args.collect_domains:
        from src.collection.domain_collector import DomainCollector

        if not args.quiet:
            print(f"\nCollecting domains from source: {args.collect_domains}")

        collector = DomainCollector()

        try:
            if args.collect_domains == 'bug_bounty':
                domains = collector.collect_bug_bounty_domains()

            elif args.collect_domains == 'tranco':
                if not args.quiet:
                    print(f"Downloading top {args.tranco_top} Tranco domains...")
                domains_with_scores = collector.collect_tranco_domains(top_n=args.tranco_top)

                if not args.quiet:
                    print(f"Filtering by minimum authority score: {args.min_authority}")
                domains = collector.filter_by_authority(
                    domains_with_scores,
                    min_score=args.min_authority
                )

            elif args.collect_domains == 'shopify':
                domains = collector.collect_shopify_brands()

            elif args.collect_domains == 'myleadfox':
                domains = collector.collect_myleadfox_domains()

            # Apply limit if specified
            if args.limit and len(domains) > args.limit:
                domains = domains[:args.limit]

        except Exception as e:
            print(f"Error collecting domains: {str(e)}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    # Get domains to scan
    elif args.google_sheet:
        # Read domains from Google Sheet
        from src.collection.google_sheets import GoogleSheetsReader

        if not args.quiet:
            print(f"\n📊 Reading domains from Google Sheet...")
            print(f"Sheet name: {args.sheet_name}")
            print(f"Column: {args.sheet_column}")

        try:
            sheets_reader = GoogleSheetsReader()
            domains = sheets_reader.read_domains_from_sheet(
                sheet_url=args.google_sheet,
                sheet_name=args.sheet_name,
                column_name=args.sheet_column
            )

            if not args.quiet:
                print(f"✓ Loaded {len(domains)} domains from Google Sheet")
                if domains:
                    print(f"\nFirst 5 domains:")
                    for domain in domains[:5]:
                        print(f"  - {domain}")
                    if len(domains) > 5:
                        print(f"  ... and {len(domains) - 5} more")

            # Apply limit if specified
            if args.limit and len(domains) > args.limit:
                domains = domains[:args.limit]
                if not args.quiet:
                    print(f"\n⚠️  Limited to first {args.limit} domains")

        except Exception as e:
            print(f"Error reading Google Sheet: {str(e)}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    elif args.scan_single:
        # Direct single domain scan (no collection needed)
        domains = [args.scan_single]
        if not args.quiet:
            print(f"\nScanning domain: {args.scan_single}")
    elif args.domain:
        domains = [args.domain]
    else:
        with open(args.domain_list) as f:
            domains = [line.strip() for line in f if line.strip()]

        # Apply limit to file-based lists too
        if args.limit and len(domains) > args.limit:
            domains = domains[:args.limit]

    # ==========================================================================
    # RESUME FUNCTIONALITY - Row-based resume for accurate continuation
    # ==========================================================================
    global PROGRESS_FILE, RESULTS_FILE
    PROGRESS_FILE = Path(args.progress_file)
    RESULTS_FILE = Path(args.results_file)

    scanned_domains = set()
    original_count = len(domains)
    start_row = 0  # 0-indexed starting position

    if args.resume and not args.no_resume:
        # Load previous progress
        progress = load_progress()
        last_row = progress['last_row']
        scanned_domains = progress['scanned_domains']

        if last_row > 0:
            # Resume from the row AFTER last_row (last_row is the last completed row)
            start_row = last_row
            skipped = min(start_row, len(domains))

            if not args.quiet:
                print(f"\n🔄 RESUME MODE ACTIVE")
                print(f"   Last completed row: {last_row}")
                print(f"   Total domains in list: {original_count}")
                print(f"   Skipping first {skipped} domains (already scanned)")
                print(f"   Resuming from row: {start_row + 1}")
                print(f"   Remaining: {max(0, original_count - start_row)} domains to scan")

            if start_row >= len(domains):
                print(f"\n✅ All {original_count} domains already scanned! Nothing to do.")
                print(f"   Use --no-resume to start fresh.\n")
                return 0

            # Slice domains to start from resume point
            domains = domains[start_row:]

    elif args.no_resume and not args.quiet:
        print(f"\n🆕 Starting fresh scan (--no-resume)")
        # Clear progress files if starting fresh
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
        # Note: We don't clear RESULTS_FILE - user should do that manually if needed

    # Parse filter parameters with wildcard support
    filter_status_codes = None
    if args.filter_status:
        filter_status_codes = parse_status_code_patterns(args.filter_status)

    # Scan domains
    try:
        if len(domains) == 1:
            # Pass provider filter for early optimization
            results = orchestrator.scan_domain(domains[0], provider_filter=args.provider, mode=args.mode)
            all_results = [results]
        else:
            all_results = orchestrator.scan_domains(
                domains,
                workers=args.workers,
                provider_filter=args.provider,
                mode=args.mode,
                filter_status=filter_status_codes,
                require_cname=args.require_cname,
                require_cname_contains=args.require_cname_contains,
                shopify_takeover_only=args.shopify_takeover_only
            )

        # Save and print results
        output_dir = Path(args.output)
        takeover_file = output_dir / 'shopify_takeover_candidates.json'

        # Batch for incremental saving (save every N domains)
        SAVE_BATCH_SIZE = 10
        batch_candidates = []
        domains_processed = 0

        for results in all_results:
            domains_processed += 1
            current_domain = results.get('domain', '')

            # Provider filter already applied during scan (no need to filter again)

            # Save results silently
            scan_dir = save_results(results, output_dir, results['domain'], args)

            # Extract Shopify takeover candidates for summary file with enhanced DNS info
            if results.get('all_subdomains'):
                for sub in results['all_subdomains']:
                    cname = sub.get('cname', '')
                    status = sub.get('http_status')
                    # Save ALL results with Shopify CNAME and 3xx/4xx/5xx status
                    if cname and ('myshopify.com' in cname.lower() or 'shopify' in cname.lower()) and status and (300 <= status < 600):
                        # Calculate risk and confidence
                        risk_level, confidence_score = calculate_risk_and_confidence(
                            status, sub.get('provider', ''), cname
                        )

                        result_data = {
                            'subdomain': sub.get('subdomain'),
                            'http_status': status,
                            'provider': sub.get('provider', '-'),
                            'cname': cname,
                            'risk_level': sub.get('risk_level') or risk_level,
                            'confidence_score': sub.get('confidence_score') or confidence_score
                        }

                        # Save to all_results.json immediately (for resume)
                        save_result_to_all_results(result_data, RESULTS_FILE)

                        # Also collect for batch save to takeover file
                        batch_candidates.append({
                            'subdomain': sub.get('subdomain'),
                            'cname': cname,
                            'cname_chain': sub.get('cname_chain', []),
                            'cname_chain_count': sub.get('cname_chain_count', 0),
                            'final_cname_target': sub.get('final_cname_target'),
                            'dangling_cname': sub.get('dangling_cname', False),
                            'vulnerable_cname_hop': sub.get('vulnerable_cname_hop'),
                            'takeover_risk': sub.get('takeover_risk'),
                            'a_records': sub.get('a_records', []),
                            'aaaa_records': sub.get('aaaa_records', []),
                            'ns_records': sub.get('ns_records', []),
                            'dns_response_code': sub.get('dns_response_code'),
                            'dns_ttl': sub.get('dns_ttl'),
                            'http_status': status,
                            'http_title': sub.get('http_title'),
                            'provider': sub.get('provider'),
                            'provider_detection_method': sub.get('provider_detection_method'),
                            'ip_confirmed': sub.get('ip_confirmed', False),
                            'confidence_score': sub.get('confidence_score', 0),
                            'risk_level': sub.get('risk_level'),
                            'domain': results['domain']
                        })

            # Track this domain as scanned
            if current_domain:
                scanned_domains.add(current_domain)

            # Save progress after each domain (for resume)
            # Use absolute row number: start_row + domains_processed
            absolute_row = start_row + domains_processed
            save_progress(scanned_domains, absolute_row)

            # Save incrementally every SAVE_BATCH_SIZE domains
            if domains_processed % SAVE_BATCH_SIZE == 0 and batch_candidates:
                save_results_incremental(batch_candidates, takeover_file)
                batch_candidates = []  # Clear batch after saving

        # Save any remaining candidates
        if batch_candidates:
            save_results_incremental(batch_candidates, takeover_file)

        # Print final summary
        final_results = load_existing_results(takeover_file)
        if final_results:
            print(f"\n🎯 Found {len(final_results)} Shopify takeover candidates")
            print(f"📄 Saved to: {takeover_file}\n")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user", file=sys.stderr)
        # Save progress before exiting
        # Calculate absolute row: start_row + domains_processed
        absolute_row = start_row + domains_processed
        if absolute_row > 0:
            save_progress(scanned_domains, absolute_row)
            print(f"💾 Progress saved at row {absolute_row} ({domains_processed} scanned this session)", file=sys.stderr)
            print(f"   Run again to resume from row {absolute_row + 1}.\n", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ Error during scan: {str(e)}", file=sys.stderr)
        # Save progress before exiting on error
        absolute_row = start_row + domains_processed
        if absolute_row > 0:
            save_progress(scanned_domains, absolute_row)
            print(f"💾 Progress saved at row {absolute_row} ({domains_processed} scanned this session)", file=sys.stderr)
            print(f"   Run again to resume from row {absolute_row + 1}.\n", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
