"""
Multi-Method Cloud Provider Detection

Combines IP range matching, CNAME patterns, and HTTP headers
for accurate provider identification.
"""
import re
import logging
from typing import Optional, Dict, List
from pathlib import Path

from ..models.subdomain import Subdomain
from .ip_matcher import IPMatcher


class ProviderDetector:
    """
    Detects cloud providers using multiple methods:
    1. IP range matching (most accurate)
    2. CNAME pattern matching
    3. HTTP header analysis
    """

    def __init__(self, config_dir: Path, providers_config: Dict):
        """
        Initialize provider detector

        Args:
            config_dir: Path to config directory
            providers_config: Loaded providers.yaml configuration
        """
        self.config_dir = config_dir
        self.providers_config = providers_config
        self.ip_matcher = IPMatcher(config_dir)
        self.logger = logging.getLogger(__name__)

    def detect_provider(self, subdomain: Subdomain) -> Optional[str]:
        """
        Detect cloud provider using multiple methods

        Args:
            subdomain: Subdomain object with DNS and HTTP data

        Returns:
            Provider name if detected, None otherwise
        """
        # Method 1: IP range matching (most accurate)
        if subdomain.a_records:
            ip_match = self.ip_matcher.match_ip_list(subdomain.a_records)
            if ip_match:
                subdomain.provider = ip_match['provider']
                subdomain.provider_detection_method = 'ip_range'
                subdomain.provider_service = ip_match.get('service')
                subdomain.provider_region = ip_match.get('region')
                subdomain.ip_confirmed = True
                self.logger.debug(f"{subdomain.subdomain}: Detected {ip_match['provider']} via IP")
                return ip_match['provider']

        # Method 2: CNAME pattern matching
        if subdomain.cname:
            cname_match = self._match_cname_patterns(subdomain.cname)
            if cname_match:
                subdomain.provider = cname_match['provider']
                subdomain.provider_detection_method = 'cname_pattern'
                subdomain.ip_confirmed = False
                self.logger.debug(f"{subdomain.subdomain}: Detected {cname_match['provider']} via CNAME")
                return cname_match['provider']

        # Method 3: HTTP header analysis (future enhancement)
        # Can be added to analyze Server, Via, X-* headers

        return None

    def _match_cname_patterns(self, cname: str) -> Optional[Dict]:
        """
        Match CNAME against provider patterns from config

        Args:
            cname: CNAME record

        Returns:
            Dict with provider info if matched
        """
        providers = self.providers_config.get('providers', {})

        for provider_key, provider_config in providers.items():
            patterns = provider_config.get('patterns', {}).get('cname', [])

            for pattern in patterns:
                try:
                    if re.search(pattern, cname, re.IGNORECASE):
                        return {
                            'provider': provider_config.get('name', provider_key),
                            'provider_key': provider_key
                        }
                except re.error:
                    self.logger.warning(f"Invalid regex pattern: {pattern}")
                    continue

        return None

    def detect_batch(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Detect providers for batch of subdomains

        Args:
            subdomains: List of Subdomain objects

        Returns:
            List of Subdomain objects with provider info populated
        """
        detected_count = 0

        for subdomain in subdomains:
            provider = self.detect_provider(subdomain)
            if provider:
                detected_count += 1

        self.logger.info(f"Detected cloud providers for {detected_count}/{len(subdomains)} subdomains")

        return subdomains
