"""
Wildcard DNS Detection Module - Critical for filtering false positives

Detects wildcard DNS configurations that create massive false positives.
This was completely missing from the original implementation.
"""
import logging
import random
import string
from typing import List, Set, Dict
from collections import defaultdict

from ..models.subdomain import Subdomain


class WildcardDetector:
    """
    Detects and filters wildcard DNS responses

    Wildcard DNS is a major source of false positives - can create 70%+ false positive rate.
    This module is CRITICAL for accurate subdomain takeover detection.
    """

    def __init__(self, num_tests: int = 15):
        """
        Initialize wildcard detector

        Args:
            num_tests: Number of random subdomains to test per domain (default: 15 for better accuracy)
        """
        self.num_tests = num_tests
        self.logger = logging.getLogger(__name__)
        self.wildcard_cache: Dict[str, Set[str]] = {}  # domain -> set of wildcard IPs

    def filter_wildcards(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Filter out wildcard DNS matches from subdomain list

        Args:
            subdomains: List of validated Subdomain objects

        Returns:
            List of non-wildcard Subdomain objects
        """
        if not subdomains:
            return []

        self.logger.info(f"Filtering wildcards from {len(subdomains)} subdomains")

        # Group subdomains by parent domain
        by_domain = defaultdict(list)
        for subdomain in subdomains:
            by_domain[subdomain.parent_domain].append(subdomain)

        # Detect wildcards for each parent domain
        filtered = []
        for parent_domain, subs in by_domain.items():
            wildcard_ips = self._detect_wildcard(parent_domain)

            if wildcard_ips:
                self.logger.info(f"Detected wildcard DNS for {parent_domain}: {wildcard_ips}")
                # Filter out subdomains that match wildcard IPs
                for sub in subs:
                    if not self._is_wildcard_match(sub, wildcard_ips):
                        filtered.append(sub)
                    else:
                        self.logger.debug(f"Filtered wildcard match: {sub.subdomain}")
            else:
                # No wildcards detected, keep all
                filtered.extend(subs)

        removed = len(subdomains) - len(filtered)
        if removed > 0:
            self.logger.info(f"Filtered {removed} wildcard matches ({removed/len(subdomains)*100:.1f}%)")

        return filtered

    def _detect_wildcard(self, domain: str) -> Set[str]:
        """
        Detect if domain has wildcard DNS by querying random non-existent subdomains

        Args:
            domain: Parent domain to check

        Returns:
            Set of IP addresses that wildcard DNS resolves to (empty if no wildcard)
        """
        # Check cache first
        if domain in self.wildcard_cache:
            return self.wildcard_cache[domain]

        wildcard_ips = set()

        # Generate random non-existent subdomains
        for _ in range(self.num_tests):
            random_subdomain = self._generate_random_subdomain(domain)

            # Try to resolve it
            try:
                import dns.resolver
                answers = dns.resolver.resolve(random_subdomain, 'A')
                ips = [str(rdata) for rdata in answers]
                wildcard_ips.update(ips)
            except dns.resolver.NXDOMAIN:
                # Good - non-existent subdomain returns NXDOMAIN
                pass
            except:
                # Other DNS errors, ignore
                pass

        # If multiple random subdomains resolve to the same IPs, it's a wildcard
        if len(wildcard_ips) > 0:
            self.wildcard_cache[domain] = wildcard_ips
            return wildcard_ips

        # No wildcard detected
        self.wildcard_cache[domain] = set()
        return set()

    def _generate_random_subdomain(self, domain: str) -> str:
        """
        Generate random non-existent subdomain for testing

        Args:
            domain: Parent domain

        Returns:
            Random subdomain like "xkqp7z2m.example.com"
        """
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{random_str}.{domain}"

    def _is_wildcard_match(self, subdomain: Subdomain, wildcard_ips: Set[str]) -> bool:
        """
        Check if subdomain's IPs match wildcard IPs

        Args:
            subdomain: Subdomain object
            wildcard_ips: Set of known wildcard IPs

        Returns:
            True if subdomain matches wildcard pattern
        """
        if not subdomain.a_records:
            return False

        # Check if any of the subdomain's IPs match wildcard IPs
        subdomain_ips = set(subdomain.a_records)
        return len(subdomain_ips.intersection(wildcard_ips)) > 0

    def clear_cache(self):
        """Clear wildcard detection cache"""
        self.wildcard_cache.clear()
