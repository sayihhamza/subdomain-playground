#!/usr/bin/env python3
"""
Subdomain Takeover Scanner - Clean CLI Interface

Simple, professional command-line interface for subdomain vulnerability scanning.

Usage:
    python scan.py <domain> [options]
    python scan.py -l domains.txt [options]

Examples:
    python scan.py example.com
    python scan.py example.com --output results/
    python scan.py example.com --json
    python scan.py -l domains.txt --workers 10
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
        help='Only show subdomains with specific HTTP status codes (comma-separated, e.g., 403,404)'
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

    # Parse filter parameters
    filter_status_codes = None
    if args.filter_status:
        filter_status_codes = [int(code.strip()) for code in args.filter_status.split(',')]

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

        # Collect all takeover candidates
        all_takeover_candidates = []

        for results in all_results:
            # Provider filter already applied during scan (no need to filter again)

            # Save results silently
            scan_dir = save_results(results, output_dir, results['domain'], args)

            # Extract Shopify takeover candidates for summary file with enhanced DNS info
            if results.get('all_subdomains'):
                for sub in results['all_subdomains']:
                    cname = sub.get('cname', '')
                    status = sub.get('http_status')
                    if cname and ('myshopify.com' in cname.lower() or 'shopify' in cname.lower()) and status in [403, 404]:
                        all_takeover_candidates.append({
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

        # Save takeover candidates to summary file
        if all_takeover_candidates:
            takeover_file = output_dir / 'shopify_takeover_candidates.json'
            takeover_file.parent.mkdir(parents=True, exist_ok=True)
            with open(takeover_file, 'w') as f:
                json.dump(all_takeover_candidates, f, indent=2)
            print(f"\n🎯 Found {len(all_takeover_candidates)} Shopify takeover candidates")
            print(f"📄 Saved to: {takeover_file}\n")

        return 0

    except KeyboardInterrupt:
        print("\n\nScan interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError during scan: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
