"""
IP-based Cloud Provider Detection

This is what the user asked for: "can you check with IP ?"
Much more accurate than CNAME-only matching.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
import ipaddress


class IPMatcher:
    """
    Matches IP addresses against cloud provider ranges

    This provides accurate provider detection beyond just CNAME patterns.
    """

    def __init__(self, config_dir: Path):
        """
        Initialize IP matcher

        Args:
            config_dir: Path to config directory with ip_ranges/
        """
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        self.ip_ranges = self._load_ip_ranges()

    def _load_ip_ranges(self) -> Dict:
        """
        Load cloud provider IP ranges from JSON files

        Returns:
            Dictionary of provider -> IP ranges
        """
        ip_ranges = {}
        ip_ranges_dir = self.config_dir / 'ip_ranges'

        if not ip_ranges_dir.exists():
            self.logger.warning(f"IP ranges directory not found: {ip_ranges_dir}")
            return {}

        # Load AWS ranges
        aws_file = ip_ranges_dir / 'aws.json'
        if aws_file.exists():
            try:
                with open(aws_file) as f:
                    data = json.load(f)
                    ip_ranges['AWS'] = self._parse_aws_ranges(data)
                    self.logger.debug(f"Loaded {len(ip_ranges['AWS'])} AWS IP ranges")
            except Exception as e:
                self.logger.error(f"Failed to load AWS ranges: {str(e)}")

        # Load GCP ranges
        gcp_file = ip_ranges_dir / 'gcp.json'
        if gcp_file.exists():
            try:
                with open(gcp_file) as f:
                    data = json.load(f)
                    ip_ranges['GCP'] = self._parse_gcp_ranges(data)
                    self.logger.debug(f"Loaded {len(ip_ranges['GCP'])} GCP IP ranges")
            except Exception as e:
                self.logger.error(f"Failed to load GCP ranges: {str(e)}")

        # Load Azure ranges (if available)
        azure_file = ip_ranges_dir / 'azure.json'
        if azure_file.exists():
            try:
                with open(azure_file) as f:
                    data = json.load(f)
                    ip_ranges['Azure'] = self._parse_azure_ranges(data)
                    if ip_ranges['Azure']:
                        self.logger.debug(f"Loaded {len(ip_ranges['Azure'])} Azure IP ranges")
            except Exception as e:
                self.logger.error(f"Failed to load Azure ranges: {str(e)}")

        # Load Shopify ranges (Cloudflare IPs)
        shopify_file = ip_ranges_dir / 'shopify.json'
        if shopify_file.exists():
            try:
                with open(shopify_file) as f:
                    data = json.load(f)
                    ip_ranges['Shopify'] = self._parse_shopify_ranges(data)
                    if ip_ranges['Shopify']:
                        self.logger.debug(f"Loaded {len(ip_ranges['Shopify'])} Shopify IP ranges")
            except Exception as e:
                self.logger.error(f"Failed to load Shopify ranges: {str(e)}")

        return ip_ranges

    def _parse_aws_ranges(self, data: Dict) -> List[Dict]:
        """Parse AWS IP ranges JSON"""
        ranges = []

        for prefix in data.get('ipv4_ranges', []):
            try:
                ranges.append({
                    'network': ipaddress.ip_network(prefix['ip_prefix']),
                    'service': prefix.get('service'),
                    'region': prefix.get('region')
                })
            except:
                pass

        return ranges

    def _parse_gcp_ranges(self, data: Dict) -> List[Dict]:
        """Parse GCP IP ranges JSON"""
        ranges = []

        for prefix in data.get('ipv4_ranges', []):
            try:
                ranges.append({
                    'network': ipaddress.ip_network(prefix['ip_prefix']),
                    'service': prefix.get('service'),
                    'scope': prefix.get('scope')
                })
            except:
                pass

        return ranges

    def _parse_azure_ranges(self, data: Dict) -> List[Dict]:
        """Parse Azure IP ranges JSON"""
        ranges = []

        for prefix in data.get('ipv4_ranges', []):
            try:
                ranges.append({
                    'network': ipaddress.ip_network(prefix['ip_prefix']),
                    'service': prefix.get('service'),
                    'region': prefix.get('region')
                })
            except:
                pass

        return ranges

    def _parse_shopify_ranges(self, data: Dict) -> List[Dict]:
        """Parse Shopify (Cloudflare) IP ranges JSON"""
        ranges = []

        # Parse IPv4 ranges
        for cidr in data.get('ipv4_ranges', []):
            try:
                ranges.append({
                    'network': ipaddress.ip_network(cidr),
                    'service': 'Shopify',
                    'cdn': 'Cloudflare'
                })
            except:
                pass

        # Parse IPv6 ranges
        for cidr in data.get('ipv6_ranges', []):
            try:
                ranges.append({
                    'network': ipaddress.ip_network(cidr),
                    'service': 'Shopify',
                    'cdn': 'Cloudflare'
                })
            except:
                pass

        return ranges

    def match_ip(self, ip_address: str) -> Optional[Dict]:
        """
        Match IP address against cloud provider ranges

        Args:
            ip_address: IP address to check

        Returns:
            Dict with provider info if matched, None otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return None

        # Check each provider
        for provider, ranges in self.ip_ranges.items():
            for range_info in ranges:
                if ip in range_info['network']:
                    return {
                        'provider': provider,
                        'service': range_info.get('service'),
                        'region': range_info.get('region') or range_info.get('scope'),
                        'detection_method': 'ip_range',
                        'ip_confirmed': True
                    }

        return None

    def match_ip_list(self, ip_addresses: List[str]) -> Optional[Dict]:
        """
        Match list of IP addresses against cloud provider ranges

        Args:
            ip_addresses: List of IP addresses

        Returns:
            Dict with provider info if any match, None otherwise
        """
        for ip in ip_addresses:
            result = self.match_ip(ip)
            if result:
                return result

        return None
