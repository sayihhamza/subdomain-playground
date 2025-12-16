"""
Subdomain Takeover Scanner Orchestrator V2

This is the CORRECT workflow based on industry standards and research.

CORRECT 6-PHASE WORKFLOW:
1. Enumeration (subfinder) - Find ALL subdomains
2. DNS Validation (dnsx) - Validate which actually resolve [CRITICAL MISSING STEP]
3. Wildcard Filtering - Remove wildcard DNS false positives [CRITICAL MISSING STEP]
4. Provider Identification - IP range + CNAME + HTTP headers
5. HTTP Validation (httpx) - Get HTTP status and content
6. Vulnerability Verification (subzy) - Confirm takeover possibilities

Old (WRONG) workflow: subfinder → DNS → HTTP → Verify
New (CORRECT) workflow: subfinder → DNS Validation → Wildcard Filter → HTTP → Provider ID → Verify
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models.subdomain import Subdomain
from .pipeline.subdomain_enum_v2 import MultiToolEnumerator
from .validation.dns_validator import DNSValidator
from .validation.wildcard_detector import WildcardDetector
from .identification.provider_detector import ProviderDetector
from .pipeline.http_validator import HTTPValidator
from .pipeline.takeover_detector import TakeoverDetector
from .detectors.confidence_scorer import ConfidenceScorer
from .config import Config
from .utils.progress_tracker import ProgressTracker, SubdomainProgressTracker


class OrchestratorV2:
    """
    Redesigned orchestrator with correct 6-phase workflow

    This addresses the user's concerns:
    - "poor job at scanning all subdomains" → Better enumeration
    - "clearly stating the cloud provider (can you check with IP?)" → IP-based detection
    - "don't filter by cloud provider yet by default" → Returns all findings
    """

    def __init__(self, config: Config):
        """
        Initialize orchestrator with correct workflow

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize pipeline stages
        # Use MultiToolEnumerator for maximum coverage
        self.enumerator = MultiToolEnumerator()

        self.dns_validator = DNSValidator(
            dnsx_path=config.tool_paths['dnsx']
        )

        self.wildcard_detector = WildcardDetector(
            num_tests=5
        )

        self.provider_detector = ProviderDetector(
            config_dir=config.config_dir,
            providers_config=config.providers
        )

        self.http_validator = HTTPValidator(
            binary_path=config.tool_paths['httpx']
        )

        self.takeover_detector = TakeoverDetector(
            subzy_path=config.tool_paths['subzy']
        )

        self.confidence_scorer = ConfidenceScorer()

    def _print_live_subdomain(self, subdomain: Subdomain):
        """
        Print a live subdomain result as it's discovered

        Args:
            subdomain: Subdomain object with scan results
        """
        # Status based on HTTP status code and vulnerability
        if subdomain.vulnerable:
            status = "🔴 VULN"
        elif subdomain.http_status:
            if subdomain.http_status < 300:
                status = f"✓ {subdomain.http_status}"  # 2xx Success
            elif subdomain.http_status < 400:
                status = f"→ {subdomain.http_status}"  # 3xx Redirect
            elif subdomain.http_status == 403:
                status = f"⚠ {subdomain.http_status}"  # 403 Forbidden (potential vuln)
            elif subdomain.http_status == 404:
                status = f"✗ {subdomain.http_status}"  # 404 Not Found
            elif subdomain.http_status < 500:
                status = f"⚠ {subdomain.http_status}"  # Other 4xx
            else:
                status = f"✗ {subdomain.http_status}"  # 5xx Server Error
        else:
            status = "- DNS"  # DNS only, no HTTP check

        # Truncate values for display
        sub_display = subdomain.subdomain[:43] + ".." if len(subdomain.subdomain) > 45 else subdomain.subdomain
        provider_display = subdomain.provider[:10] if subdomain.provider else "-"
        cname_display = subdomain.cname[:23] + ".." if subdomain.cname and len(subdomain.cname) > 25 else (subdomain.cname or "-")

        # Build info string
        info_parts = []
        if subdomain.ip_address:
            info_parts.append(f"IP:{subdomain.ip_address[:15]}")
        if subdomain.ip_confirmed:
            info_parts.append("✓CloudIP")
        if subdomain.vulnerable:
            info_parts.append("⚠️TAKEOVER")

        info_display = " ".join(info_parts) if info_parts else "-"

        print(f"  {status:<8} {sub_display:<45} {provider_display:<12} {cname_display:<25} {info_display}")

    def scan_domain(self, domain: str, provider_filter: Optional[str] = None, quiet_mode: bool = False, mode: str = 'quick') -> Dict:
        """
        Execute complete 6-phase scan for a single domain

        Args:
            domain: Target domain
            provider_filter: Optional provider to filter for (e.g., 'Shopify', 'AWS')
                           If set, only processes subdomains matching this provider (saves time)
            quiet_mode: If True, suppress verbose logging (for batch scans)
            mode: Enumeration mode - 'quick' (passive only) or 'full' (complete with bruteforce)

        Returns:
            Scan results dictionary
        """
        if not quiet_mode:
            self.logger.info("=" * 60)
            self.logger.info(f"Starting scan for: {domain}")
            if provider_filter:
                self.logger.info(f"Provider Filter: {provider_filter} (early filtering enabled)")
            self.logger.info("=" * 60)

        results = {
            'domain': domain,
            'phase_results': {},
            'all_subdomains': [],
            'cloud_hosted': [],
            'vulnerable': [],
            'statistics': {}
        }

        # PHASE 1: Subdomain Enumeration
        self.logger.info("")
        self.logger.info("[PHASE 1/6] Subdomain Enumeration")
        self.logger.info("-" * 60)

        # Using 'full' mode for maximum coverage (all tools enabled)
        # Available modes: 'passive' (faster, 90-95%) or 'full' (slower, 98-99%)
        enumerated = self.enumerator.enumerate(domain, mode=mode)
        results['phase_results']['enumeration'] = {
            'count': len(enumerated),
            'subdomains': [s.subdomain for s in enumerated]
        }
        self.logger.info(f"Found {len(enumerated)} subdomains")

        if not enumerated:
            self.logger.debug("No subdomains found, stopping scan")
            return results

        # PHASE 2: DNS Validation (CRITICAL MISSING STEP)
        self.logger.info("")
        self.logger.info("[PHASE 2/6] DNS Validation")
        self.logger.info("-" * 60)

        validated = self.dns_validator.validate_batch(enumerated)
        results['phase_results']['dns_validation'] = {
            'validated': len(validated),
            'nxdomain_count': sum(1 for s in validated if s.nxdomain)
        }
        self.logger.info(f"Validated {len(validated)}/{len(enumerated)} subdomains")
        self.logger.info(f"NXDOMAIN detected: {results['phase_results']['dns_validation']['nxdomain_count']}")

        if not validated:
            self.logger.warning("No valid DNS records found, stopping scan")
            return results

        # PHASE 3: Wildcard Filtering (CRITICAL MISSING STEP)
        self.logger.info("")
        self.logger.info("[PHASE 3/6] Wildcard Filtering")
        self.logger.info("-" * 60)

        filtered = self.wildcard_detector.filter_wildcards(validated)
        wildcards_removed = len(validated) - len(filtered)
        results['phase_results']['wildcard_filtering'] = {
            'wildcards_removed': wildcards_removed,
            'percentage_removed': wildcards_removed / len(validated) * 100 if validated else 0
        }
        self.logger.info(f"Filtered {wildcards_removed} wildcard matches")
        self.logger.info(f"Remaining: {len(filtered)} subdomains")

        if not filtered:
            self.logger.warning("All subdomains filtered as wildcards")
            return results

        # PHASE 4: Cloud Provider Identification (IP + CNAME + Headers)
        self.logger.info("")
        self.logger.info("[PHASE 4/6] Cloud Provider Identification")
        self.logger.info("-" * 60)

        identified = self.provider_detector.detect_batch(filtered)
        cloud_hosted = [s for s in identified if s.provider]

        # Apply provider filter early if specified (saves time on HTTP/verification)
        if provider_filter:
            cloud_hosted_before_filter = len(cloud_hosted)
            cloud_hosted = [
                s for s in cloud_hosted
                if s.provider and s.provider.lower() == provider_filter.lower()
            ]
            self.logger.info(f"Provider filter: kept {len(cloud_hosted)}/{cloud_hosted_before_filter} {provider_filter} subdomains")

            # Also filter the full list for HTTP validation
            identified = [
                s for s in identified
                if not s.provider or s.provider.lower() == provider_filter.lower()
            ]

        results['phase_results']['provider_identification'] = {
            'cloud_hosted': len(cloud_hosted),
            'ip_confirmed': sum(1 for s in cloud_hosted if s.ip_confirmed),
            'cname_only': sum(1 for s in cloud_hosted if not s.ip_confirmed),
            'providers': {},
            'filtered_by': provider_filter if provider_filter else None
        }

        # Count by provider
        for subdomain in cloud_hosted:
            provider = subdomain.provider
            if provider not in results['phase_results']['provider_identification']['providers']:
                results['phase_results']['provider_identification']['providers'][provider] = {
                    'count': 0,
                    'ip_confirmed': 0
                }
            results['phase_results']['provider_identification']['providers'][provider]['count'] += 1
            if subdomain.ip_confirmed:
                results['phase_results']['provider_identification']['providers'][provider]['ip_confirmed'] += 1

        self.logger.info(f"Identified {len(cloud_hosted)} cloud-hosted subdomains")
        for provider, stats in results['phase_results']['provider_identification']['providers'].items():
            self.logger.info(f"  {provider}: {stats['count']} (IP confirmed: {stats['ip_confirmed']})")

        # PHASE 5: HTTP Validation
        self.logger.info("")
        self.logger.info("[PHASE 5/6] HTTP Validation")
        self.logger.info("-" * 60)

        # HTTP validate all subdomains (not just cloud-hosted)
        http_validated = self.http_validator.validate_batch(identified)
        results['phase_results']['http_validation'] = {
            'validated': len(http_validated),
            'status_codes': {}
        }

        # Count status codes
        for subdomain in http_validated:
            status = subdomain.http_status or 'unknown'
            results['phase_results']['http_validation']['status_codes'][status] = \
                results['phase_results']['http_validation']['status_codes'].get(status, 0) + 1

        self.logger.info(f"HTTP validated {len(http_validated)} subdomains")

        # Print live results table (only if not in quiet mode)
        if http_validated and not quiet_mode:
            print("\n" + "=" * 110)
            print(f"{'STATUS':<8} {'SUBDOMAIN':<45} {'PROVIDER':<12} {'CNAME':<25} {'INFO':<18}")
            print("=" * 110)
            for subdomain in http_validated:
                self._print_live_subdomain(subdomain)

        # PHASE 6: Vulnerability Verification
        self.logger.info("")
        self.logger.info("[PHASE 6/6] Vulnerability Verification")
        self.logger.info("-" * 60)

        # Only verify cloud-hosted subdomains
        cloud_with_http = [s for s in http_validated if s.provider]
        if cloud_with_http:
            # ENHANCED: Deep CNAME verification for takeover detection
            self.logger.info("Performing deep CNAME verification...")
            for subdomain in cloud_with_http:
                if subdomain.cname:
                    verification = self.dns_validator.verify_cname_target(subdomain)
                    # Store verification results
                    if verification['is_dangling']:
                        subdomain.dangling_cname = True
                        subdomain.takeover_risk = 'critical' if verification['takeover_confidence'] > 70 else 'high'
                    if verification['vulnerable_pattern']:
                        subdomain.vulnerable_cname_hop = verification['vulnerable_pattern']

            vulnerable = self.takeover_detector.verify_batch(cloud_with_http)

            # Apply confidence scoring with enhanced CNAME data
            for subdomain in vulnerable:
                assessment = self.confidence_scorer.assess(subdomain.to_dict())
                subdomain.risk_level = assessment.get('risk_level')
                subdomain.vulnerability_type = 'subdomain_takeover'

                # Boost risk level if dangling CNAME detected
                if subdomain.dangling_cname:
                    if subdomain.risk_level == 'high':
                        subdomain.risk_level = 'critical'
                    elif subdomain.risk_level == 'medium':
                        subdomain.risk_level = 'high'

            results['phase_results']['verification'] = {
                'checked': len(cloud_with_http),
                'vulnerable': len(vulnerable),
                'by_risk': {}
            }

            # Count by risk level
            for subdomain in vulnerable:
                risk = subdomain.risk_level or 'unknown'
                results['phase_results']['verification']['by_risk'][risk] = \
                    results['phase_results']['verification']['by_risk'].get(risk, 0) + 1

            self.logger.info(f"Found {len(vulnerable)} vulnerable subdomains")
            for risk, count in results['phase_results']['verification']['by_risk'].items():
                self.logger.info(f"  {risk.upper()}: {count}")
        else:
            vulnerable = []
            self.logger.info("No cloud-hosted subdomains to verify")

        # Compile final results
        results['all_subdomains'] = [s.to_dict() for s in http_validated]
        results['cloud_hosted'] = [s.to_dict() for s in cloud_with_http]
        results['vulnerable'] = [s.to_dict() for s in vulnerable]

        # Statistics
        results['statistics'] = {
            'total_found': len(enumerated),
            'dns_validated': len(validated),
            'wildcards_filtered': wildcards_removed,
            'cloud_hosted': len(cloud_hosted),
            'vulnerable': len(vulnerable),
            'critical': sum(1 for s in vulnerable if s.risk_level == 'critical'),
            'high': sum(1 for s in vulnerable if s.risk_level == 'high'),
            'medium': sum(1 for s in vulnerable if s.risk_level == 'medium'),
            'low': sum(1 for s in vulnerable if s.risk_level == 'low')
        }

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("Scan Complete")
        self.logger.info("=" * 60)
        self.logger.info(f"Total subdomains found: {results['statistics']['total_found']}")
        self.logger.info(f"Cloud-hosted: {results['statistics']['cloud_hosted']}")
        self.logger.info(f"Vulnerable: {results['statistics']['vulnerable']}")

        return results

    def scan_domains(self, domains: List[str], workers: int = 5, provider_filter: Optional[str] = None, mode: str = 'quick',
                    filter_status: Optional[List[int]] = None, require_cname: bool = False, require_cname_contains: Optional[str] = None,
                    shopify_takeover_only: bool = False) -> List[Dict]:
        """
        Scan multiple domains concurrently

        Args:
            domains: List of domains to scan
            workers: Number of concurrent workers
            provider_filter: Optional provider to filter for (e.g., 'Shopify', 'AWS')
            filter_status: Only show subdomains with these HTTP status codes
            require_cname: Only show subdomains with CNAME records
            require_cname_contains: Only show subdomains where CNAME chain contains this pattern (case-insensitive)
            shopify_takeover_only: Only show Shopify takeover candidates

        Returns:
            List of scan results
        """
        # Initialize progress tracker with time estimation
        tracker = ProgressTracker(total_domains=len(domains), workers=workers)
        tracker.start()

        results = []

        # Suppress verbose logging during batch scans
        # Save original levels
        original_levels = {}
        loggers_to_quiet = [
            self.logger,
            self.enumerator.logger,
            self.dns_validator.logger,
            self.wildcard_detector.logger,
            self.provider_detector.logger,
            self.http_validator.logger,
            self.takeover_detector.logger
        ]

        for logger in loggers_to_quiet:
            original_levels[logger] = logger.level
            logger.setLevel(logging.WARNING)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.scan_domain, domain, provider_filter, quiet_mode=True, mode=mode): domain for domain in domains}

            for future in as_completed(futures):
                domain = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    # Update progress tracker - show each subdomain found (with filtering)
                    if result.get('all_subdomains'):
                        # Show each discovered subdomain (apply filters)
                        for sub in result['all_subdomains']:
                            # Apply filters
                            if shopify_takeover_only:
                                # Must have CNAME to myshopify.com AND 403/404 status
                                cname = sub.get('cname', '')
                                status = sub.get('http_status')
                                if not (cname and ('myshopify.com' in cname.lower() or 'shopify' in cname.lower())
                                       and status in [403, 404]):
                                    continue  # Skip this subdomain
                            elif filter_status:
                                # Filter by status codes
                                if sub.get('http_status') not in filter_status:
                                    continue

                            if require_cname:
                                # Must have CNAME record
                                if not sub.get('cname'):
                                    continue

                            if require_cname_contains:
                                # Check if ANY CNAME in the chain contains the pattern (case-insensitive)
                                cname_chain = sub.get('cname_chain', [])
                                pattern_lower = require_cname_contains.lower()

                                # Check all CNAMEs in the chain
                                found_pattern = False
                                if cname_chain:
                                    for cname_hop in cname_chain:
                                        if pattern_lower in cname_hop.lower():
                                            found_pattern = True
                                            break

                                # Also check the primary cname field as fallback
                                if not found_pattern and sub.get('cname'):
                                    if pattern_lower in sub.get('cname').lower():
                                        found_pattern = True

                                if not found_pattern:
                                    continue  # Skip this subdomain - doesn't contain pattern

                            # Passed all filters - show it with enhanced DNS info
                            tracker.update(
                                subdomain=sub.get('subdomain', domain),
                                provider=sub.get('provider'),
                                cname=sub.get('cname'),
                                http_status=sub.get('http_status'),
                                fingerprint=sub.get('fingerprint'),
                                vulnerable=sub.get('vulnerable', False),
                                cname_chain=sub.get('cname_chain', []),
                                cname_chain_count=sub.get('cname_chain_count', 0),
                                dns_response_code=sub.get('dns_response_code'),
                                a_records=sub.get('a_records', []),
                                final_cname_target=sub.get('final_cname_target')
                            )
                    else:
                        # No subdomains found - only show if no filters are active
                        # (Don't clutter output when using specific filters like --shopify-takeover-only)
                        if not (shopify_takeover_only or filter_status or require_cname or require_cname_contains):
                            tracker.update(
                                subdomain=domain,
                                provider=None,
                                cname=None,
                                http_status=None,
                                fingerprint="No subdomains",
                                vulnerable=False
                            )

                except Exception as e:
                    self.logger.error(f"Failed to scan {domain}: {str(e)}")
                    tracker.update(subdomain=domain, status="✗")

        # Restore original logging levels
        for logger, level in original_levels.items():
            logger.setLevel(level)

        tracker.finish()
        return results
