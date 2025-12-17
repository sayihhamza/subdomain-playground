"""
CNAME Blacklist Filter - Exclude untakeable CNAME patterns
"""
import logging
import yaml
from pathlib import Path
from typing import List, Set, Optional


class CNAMEBlacklist:
    """Filter out CNAMEs that cannot be taken over"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize CNAME blacklist filter

        Args:
            config_path: Path to cname_blacklist.yaml config file
        """
        self.logger = logging.getLogger(__name__)

        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'cname_blacklist.yaml'

        self.blacklist_patterns: Set[str] = set()
        self._load_blacklist(config_path)

    def _load_blacklist(self, config_path: Path):
        """
        Load blacklist patterns from YAML config

        Args:
            config_path: Path to cname_blacklist.yaml
        """
        try:
            if not config_path.exists():
                self.logger.warning(f"CNAME blacklist config not found: {config_path}")
                self._load_default_blacklist()
                return

            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Flatten all categories into a single set
            for category, patterns in config.items():
                if isinstance(patterns, list):
                    for pattern in patterns:
                        self.blacklist_patterns.add(pattern.lower())

            self.logger.info(f"Loaded {len(self.blacklist_patterns)} CNAME blacklist patterns")

        except Exception as e:
            self.logger.error(f"Error loading CNAME blacklist: {e}")
            self._load_default_blacklist()

    def _load_default_blacklist(self):
        """Load minimal default blacklist if config fails"""
        self.blacklist_patterns = {
            # Shopify
            'myshopify.verification',
            'verification.shopify.com',

            # Cloudflare
            'verify.cloudflare.com',
            '_cf-custom-hostname',

            # AWS
            'acm-validation',
            'amazonses.com',

            # Google
            'google-site-verification',
            'ghs.googlehosted.com',

            # Email
            '_domainkey',
            'mail.protection.outlook.com',
            'mailgun.org',
            'sendgrid.net',
        }
        self.logger.info(f"Loaded {len(self.blacklist_patterns)} default CNAME blacklist patterns")

    def is_blacklisted(self, cname: str) -> bool:
        """
        Check if a CNAME matches blacklist patterns

        Args:
            cname: CNAME record to check

        Returns:
            True if CNAME is blacklisted (untakeable)
        """
        if not cname:
            return False

        cname_lower = cname.lower().strip().rstrip('.')

        # Exact match
        if cname_lower in self.blacklist_patterns:
            return True

        # Substring match (e.g., "x.myshopify.verification" matches "myshopify.verification")
        for pattern in self.blacklist_patterns:
            if pattern in cname_lower:
                return True

        return False

    def filter_subdomains(self, subdomains: List, verbose: bool = False) -> List:
        """
        Filter out subdomains with blacklisted CNAMEs

        Args:
            subdomains: List of Subdomain objects
            verbose: Log each filtered subdomain

        Returns:
            Filtered list of subdomains (blacklisted CNAMEs removed)
        """
        filtered = []
        blacklisted_count = 0

        for subdomain in subdomains:
            # Check primary CNAME
            if subdomain.cname and self.is_blacklisted(subdomain.cname):
                blacklisted_count += 1
                if verbose:
                    self.logger.debug(f"Blacklisted CNAME: {subdomain.subdomain} → {subdomain.cname}")
                continue

            # Check CNAME chain (if present)
            is_chain_blacklisted = False
            if subdomain.cname_chain:
                for cname_hop in subdomain.cname_chain:
                    if self.is_blacklisted(cname_hop):
                        blacklisted_count += 1
                        is_chain_blacklisted = True
                        if verbose:
                            self.logger.debug(f"Blacklisted CNAME in chain: {subdomain.subdomain} → {cname_hop}")
                        break

            if is_chain_blacklisted:
                continue

            # Not blacklisted, keep it
            filtered.append(subdomain)

        # if blacklisted_count > 0:
        #     self.logger.info(f"Filtered {blacklisted_count} subdomains with blacklisted CNAMEs")

        return filtered

    def add_pattern(self, pattern: str):
        """
        Add a custom blacklist pattern at runtime

        Args:
            pattern: CNAME pattern to blacklist
        """
        self.blacklist_patterns.add(pattern.lower().strip())
        self.logger.info(f"Added CNAME blacklist pattern: {pattern}")

    def remove_pattern(self, pattern: str):
        """
        Remove a blacklist pattern

        Args:
            pattern: CNAME pattern to remove
        """
        pattern_lower = pattern.lower().strip()
        if pattern_lower in self.blacklist_patterns:
            self.blacklist_patterns.remove(pattern_lower)
            self.logger.info(f"Removed CNAME blacklist pattern: {pattern}")

    def get_patterns(self) -> List[str]:
        """Get all blacklist patterns"""
        return sorted(list(self.blacklist_patterns))
