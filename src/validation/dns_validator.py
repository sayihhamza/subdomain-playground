"""
DNS Validation Module - Critical missing component

Properly resolves DNS records, tracks CNAME chains, and detects NXDOMAIN.
This is the step that was missing between enumeration and HTTP probing.
"""
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import subprocess
import json
import tempfile

from ..models.subdomain import Subdomain


class DNSValidator:
    """
    Validates DNS records for subdomains using dnsx

    This is the CRITICAL missing step in the original workflow.
    Properly validates which subdomains actually resolve before HTTP probing.
    """

    def __init__(self, dnsx_path: Path, use_dnspython_fallback: bool = True):
        """
        Initialize DNS validator

        Args:
            dnsx_path: Path to dnsx binary
            use_dnspython_fallback: Use dnspython if dnsx fails
        """
        self.dnsx_path = dnsx_path
        self.use_dnspython_fallback = use_dnspython_fallback
        self.logger = logging.getLogger(__name__)

    def validate_batch(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Validate DNS resolution for batch of subdomains

        Args:
            subdomains: List of Subdomain objects

        Returns:
            List of Subdomain objects with DNS data populated
        """
        if not subdomains:
            return []

        self.logger.info(f"Validating DNS for {len(subdomains)} subdomains")

        # Create temporary file with subdomain list
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for subdomain in subdomains:
                f.write(f"{subdomain.subdomain}\n")
            temp_file = f.name

        try:
            # Run dnsx to resolve DNS records with custom resolvers
            # Using comprehensive flags for detailed DNS information
            cmd = [
                str(self.dnsx_path),
                '-l', temp_file,
                '-json',
                '-cname',        # CNAME records
                '-a',            # A records
                '-aaaa',         # AAAA records
                '-ns',           # NS records
                '-mx',           # MX records
                '-txt',          # TXT records
                '-soa',          # SOA records
                '-resp',         # Include full DNS response
                '-trace',        # Trace CNAME chain
                '-rc',           # Response code
                '-cdn',          # CDN detection
                '-rcode',        # Response code details
                '-retry', '2',
                '-timeout', '5',
                '-r', '8.8.8.8,1.1.1.1,208.67.222.222,9.9.9.9',  # Google, Cloudflare, OpenDNS, Quad9
                '-silent'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0 and result.stdout:
                # Parse dnsx JSON output
                validated = self._parse_dnsx_output(result.stdout, subdomains)
                self.logger.info(f"Successfully validated {len(validated)} subdomains")
                return validated
            else:
                self.logger.warning("dnsx validation failed, using fallback")
                if self.use_dnspython_fallback:
                    return self._fallback_validation(subdomains)
                return []

        except subprocess.TimeoutExpired:
            self.logger.error("DNS validation timed out")
            if self.use_dnspython_fallback:
                return self._fallback_validation(subdomains)
            return []
        except Exception as e:
            self.logger.error(f"DNS validation error: {str(e)}")
            if self.use_dnspython_fallback:
                return self._fallback_validation(subdomains)
            return []
        finally:
            # Clean up temp file
            try:
                Path(temp_file).unlink()
            except:
                pass

    def _parse_dnsx_output(self, output: str, original_subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Parse dnsx JSON output and populate Subdomain objects

        Args:
            output: dnsx JSON output
            original_subdomains: Original subdomain list

        Returns:
            List of validated Subdomain objects
        """
        validated = []
        subdomain_map = {s.subdomain: s for s in original_subdomains}

        for line in output.strip().split('\n'):
            if not line:
                continue

            try:
                data = json.loads(line)
                hostname = data.get('host', '')

                if hostname in subdomain_map:
                    subdomain = subdomain_map[hostname]

                    # Extract CNAME (track full chain)
                    # CRITICAL: For takeover detection, we need to know what the subdomain POINTS TO
                    # dnsx returns CNAME chain in resolution order: [first_hop, second_hop, ..., final]
                    cname_records = data.get('cname', [])
                    if cname_records:
                        if isinstance(cname_records, list):
                            # Full CNAME chain - dnsx returns in order of resolution
                            subdomain.cname_chain = cname_records
                            subdomain.cname = cname_records[0] if cname_records else None  # FIRST hop (what subdomain points to)
                            subdomain.final_cname_target = cname_records[-1]  # FINAL destination
                            subdomain.cname_chain_count = len(cname_records)

                            # For takeover detection: Check if ANY hop in chain points to vulnerable service
                            # Example: subdomain.com -> cdn.cloudflare.net -> shop.myshopify.com
                            # We need to check ALL hops, not just first or last
                            for cname_hop in cname_records:
                                # Normalize: remove trailing dots, lowercase
                                cname_hop_normalized = cname_hop.rstrip('.').lower()
                                # Check if this hop points to a potentially vulnerable service
                                if any(pattern in cname_hop_normalized for pattern in [
                                    'myshopify.com', 'shopify.com',
                                    'azurewebsites.net', 'cloudapp.net',
                                    'herokuapp.com', 'herokudns.com',
                                    'amazonaws.com', 's3.amazonaws.com',
                                    'github.io', 'netlify.app',
                                    'pantheonsite.io', 'readme.io',
                                    'zendesk.com', 'helpscoutdocs.com',
                                    'fastly.net', 'cloudfront.net'
                                ]):
                                    # Store the vulnerable hop for verification
                                    if not hasattr(subdomain, 'vulnerable_cname_hop'):
                                        subdomain.vulnerable_cname_hop = cname_hop_normalized

                        else:
                            subdomain.cname = cname_records
                            subdomain.final_cname_target = cname_records
                            subdomain.cname_chain = [cname_records]
                            subdomain.cname_chain_count = 1

                    # CRITICAL: Check if CNAME target resolves
                    # If subdomain has CNAME but NO A/AAAA records, the target might not exist (TAKEOVER!)
                    # This is a STRONG indicator of subdomain takeover vulnerability
                    if subdomain.cname and not data.get('a') and not data.get('aaaa'):
                        # CNAME exists but doesn't resolve to IP - potential dangling CNAME
                        subdomain.dangling_cname = True
                        subdomain.takeover_risk = 'high'
                    else:
                        subdomain.dangling_cname = False

                    # Extract A records
                    a_records = data.get('a', [])
                    if a_records:
                        subdomain.a_records = a_records if isinstance(a_records, list) else [a_records]
                        # Use first IP as primary
                        if subdomain.a_records and not hasattr(subdomain, 'ip_address'):
                            subdomain.ip_address = subdomain.a_records[0]

                    # Extract AAAA records
                    aaaa_records = data.get('aaaa', [])
                    if aaaa_records:
                        subdomain.aaaa_records = aaaa_records if isinstance(aaaa_records, list) else [aaaa_records]

                    # Extract NS records
                    ns_records = data.get('ns', [])
                    if ns_records:
                        subdomain.ns_records = ns_records if isinstance(ns_records, list) else [ns_records]
                        # First NS as authoritative
                        if subdomain.ns_records:
                            subdomain.authoritative_ns = subdomain.ns_records[0]

                    # Extract MX records
                    mx_records = data.get('mx', [])
                    if mx_records:
                        subdomain.mx_records = mx_records if isinstance(mx_records, list) else [mx_records]

                    # Extract TXT records
                    txt_records = data.get('txt', [])
                    if txt_records:
                        subdomain.txt_records = txt_records if isinstance(txt_records, list) else [txt_records]

                    # Extract SOA record
                    soa = data.get('soa', '')
                    if soa:
                        subdomain.soa_record = soa

                    # Extract TTL
                    ttl = data.get('ttl', None)
                    if ttl:
                        subdomain.dns_ttl = int(ttl)

                    # Extract response code
                    rcode = data.get('rcode', data.get('status_code', ''))
                    if rcode:
                        subdomain.dns_response_code = str(rcode)

                    # Mark as resolved
                    subdomain.dns_resolved = True

                    # Check for NXDOMAIN in response
                    if 'NXDOMAIN' in str(rcode) or 'NXDOMAIN' in str(data.get('status_code', '')):
                        subdomain.nxdomain = True

                    validated.append(subdomain)

            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse dnsx output line: {line[:100]}")
                continue

        return validated

    def _fallback_validation(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Fallback DNS validation using dnspython

        Args:
            subdomains: List of Subdomain objects

        Returns:
            List of validated Subdomain objects
        """
        try:
            import dns.resolver
        except ImportError:
            self.logger.error("dnspython not available for fallback")
            return []

        self.logger.info(f"Using dnspython fallback for {len(subdomains)} subdomains")
        validated = []

        for subdomain in subdomains:
            try:
                # Try to resolve A records
                try:
                    answers = dns.resolver.resolve(subdomain.subdomain, 'A')
                    subdomain.a_records = [str(rdata) for rdata in answers]
                    subdomain.dns_resolved = True
                    # Extract TTL from first answer
                    if answers.rrset:
                        subdomain.dns_ttl = answers.rrset.ttl
                except dns.resolver.NXDOMAIN:
                    subdomain.nxdomain = True
                    subdomain.dns_resolved = False
                    subdomain.dns_response_code = 'NXDOMAIN'
                except:
                    pass

                # Try to resolve CNAME (track full chain)
                try:
                    # Manually resolve CNAME chain
                    current_name = subdomain.subdomain
                    cname_chain = []
                    max_chain_length = 10  # Prevent infinite loops

                    for _ in range(max_chain_length):
                        try:
                            answers = dns.resolver.resolve(current_name, 'CNAME')
                            if answers:
                                cname_target = str(answers[0].target).rstrip('.')
                                cname_chain.append(cname_target)
                                current_name = cname_target
                            else:
                                break
                        except dns.resolver.NoAnswer:
                            break
                        except dns.resolver.NXDOMAIN:
                            subdomain.nxdomain = True
                            break

                    if cname_chain:
                        subdomain.cname = cname_chain[0]  # First CNAME
                        subdomain.final_cname_target = cname_chain[-1]  # Final target
                        subdomain.cname_chain = cname_chain
                        subdomain.cname_chain_count = len(cname_chain)
                except:
                    pass

                # Try to resolve AAAA
                try:
                    answers = dns.resolver.resolve(subdomain.subdomain, 'AAAA')
                    subdomain.aaaa_records = [str(rdata) for rdata in answers]
                except:
                    pass

                # Try to resolve NS
                try:
                    answers = dns.resolver.resolve(subdomain.subdomain, 'NS')
                    subdomain.ns_records = [str(rdata).rstrip('.') for rdata in answers]
                    if subdomain.ns_records:
                        subdomain.authoritative_ns = subdomain.ns_records[0]
                except:
                    pass

                # Try to resolve MX
                try:
                    answers = dns.resolver.resolve(subdomain.subdomain, 'MX')
                    subdomain.mx_records = [str(rdata.exchange).rstrip('.') for rdata in answers]
                except:
                    pass

                # Try to resolve TXT
                try:
                    answers = dns.resolver.resolve(subdomain.subdomain, 'TXT')
                    subdomain.txt_records = [str(rdata) for rdata in answers]
                except:
                    pass

                # Try to resolve SOA
                try:
                    answers = dns.resolver.resolve(subdomain.subdomain, 'SOA')
                    if answers:
                        subdomain.soa_record = str(answers[0])
                except:
                    pass

                if subdomain.dns_resolved or subdomain.cname:
                    validated.append(subdomain)

            except Exception as e:
                self.logger.debug(f"Fallback validation failed for {subdomain.subdomain}: {str(e)}")
                continue

        self.logger.info(f"Fallback validated {len(validated)} subdomains")
        return validated

    def check_nxdomain(self, hostname: str) -> bool:
        """
        Check if a hostname returns NXDOMAIN

        Args:
            hostname: Hostname to check

        Returns:
            True if NXDOMAIN, False otherwise
        """
        try:
            import dns.resolver
            dns.resolver.resolve(hostname, 'A')
            return False
        except dns.resolver.NXDOMAIN:
            return True
        except:
            return False

    def verify_cname_target(self, subdomain) -> dict:
        """
        Deep verification of CNAME target for takeover detection

        Args:
            subdomain: Subdomain object with CNAME data

        Returns:
            Dictionary with verification results
        """
        results = {
            'cname_exists': False,
            'target_resolves': False,
            'is_dangling': False,
            'vulnerable_pattern': None,
            'takeover_confidence': 0,
            'verification_details': []
        }

        if not subdomain.cname:
            return results

        results['cname_exists'] = True

        try:
            import dns.resolver

            # Check if final CNAME target resolves
            target = subdomain.final_cname_target or subdomain.cname
            try:
                answers = dns.resolver.resolve(target, 'A')
                results['target_resolves'] = True
                results['verification_details'].append(f"Target {target} resolves to {len(answers)} IPs")
            except dns.resolver.NXDOMAIN:
                results['is_dangling'] = True
                results['takeover_confidence'] += 50
                results['verification_details'].append(f"CRITICAL: Target {target} returns NXDOMAIN")
            except dns.resolver.NoAnswer:
                results['is_dangling'] = True
                results['takeover_confidence'] += 40
                results['verification_details'].append(f"WARNING: Target {target} has no A records")
            except Exception as e:
                results['verification_details'].append(f"DNS error for {target}: {str(e)}")

            # Check each hop in CNAME chain for vulnerable patterns
            for hop in subdomain.cname_chain:
                hop_normalized = hop.rstrip('.').lower()

                # Vulnerable service patterns
                vulnerable_patterns = {
                    'shopify': ['myshopify.com', 'shopify.com'],
                    'azure': ['azurewebsites.net', 'cloudapp.azure.com', 'cloudapp.net'],
                    'heroku': ['herokuapp.com', 'herokudns.com'],
                    'aws': ['amazonaws.com', 's3.amazonaws.com', 'elasticbeanstalk.com'],
                    'github': ['github.io'],
                    'netlify': ['netlify.app', 'netlify.com'],
                    'pantheon': ['pantheonsite.io'],
                    'readme': ['readme.io'],
                    'zendesk': ['zendesk.com'],
                    'helpscout': ['helpscoutdocs.com'],
                    'fastly': ['fastly.net'],
                    'cloudfront': ['cloudfront.net'],
                    'bitbucket': ['bitbucket.io'],
                    'surge': ['surge.sh'],
                    'tumblr': ['tumblr.com'],
                    'wordpress': ['wordpress.com'],
                    'ghost': ['ghost.io'],
                    'smugmug': ['smugmug.com'],
                    'cargo': ['cargocollective.com'],
                    'statuspage': ['statuspage.io'],
                    'uservoice': ['uservoice.com'],
                    'getresponse': ['getresponse.com'],
                    'vend': ['vendhq.com'],
                    'jetbrains': ['myjetbrains.com'],
                    'brightcove': ['bcvp0rtal.com', 'brightcovegallery.com'],
                    'bigcartel': ['bigcartel.com'],
                    'campaignmonitor': ['createsend.com'],
                    'acquia': ['acquia.com']
                }

                for service, patterns in vulnerable_patterns.items():
                    if any(pattern in hop_normalized for pattern in patterns):
                        results['vulnerable_pattern'] = service
                        results['takeover_confidence'] += 30
                        results['verification_details'].append(f"VULNERABLE: Found {service} pattern in {hop}")
                        break

        except ImportError:
            results['verification_details'].append("dnspython not available for deep verification")
        except Exception as e:
            results['verification_details'].append(f"Verification error: {str(e)}")

        return results
