"""
Parser for subfinder JSON output
"""
from typing import List, Dict, Any
from ..models.subdomain import Subdomain


class SubfinderParser:
    """Parser for subfinder JSON output"""

    def parse(self, json_data: List[Dict[str, Any]], parent_domain: str) -> List[Subdomain]:
        """
        Parse subfinder JSON output

        Args:
            json_data: List of JSON objects from subfinder
            parent_domain: Parent domain being scanned

        Returns:
            List of Subdomain objects
        """
        subdomains = []

        for entry in json_data:
            try:
                subdomain = Subdomain(
                    subdomain=entry.get('host', ''),
                    parent_domain=parent_domain,
                    source='subfinder'
                )
                subdomains.append(subdomain)
            except Exception as e:
                # Skip invalid entries
                continue

        return subdomains
