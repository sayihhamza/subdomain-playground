"""
Parser for subzy JSON output
"""
from typing import List, Dict, Any
from ..models.subdomain import Subdomain


class SubzyParser:
    """Parser for subzy JSON output"""

    def parse(self, json_data: List[Dict[str, Any]], subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Parse subzy JSON output and update subdomain objects

        Args:
            json_data: List of JSON objects from subzy
            subdomains: Existing subdomain objects to update

        Returns:
            Updated list of Subdomain objects with vulnerability info
        """
        # Create lookup map
        subdomain_map = {s.subdomain: s for s in subdomains}

        for entry in json_data:
            try:
                host = entry.get('subdomain', '')
                if host not in subdomain_map:
                    continue

                subdomain = subdomain_map[host]

                # Check if vulnerable
                if entry.get('vulnerable', False):
                    subdomain.is_vulnerable = True
                    subdomain.vulnerability_type = 'subdomain_takeover'
                    subdomain.provider = entry.get('service', entry.get('engine'))
                    subdomain.fingerprint_matched = entry.get('fingerprint')

                    # Add verification source
                    if 'subzy' not in subdomain.verified_by:
                        subdomain.verified_by.append('subzy')

            except Exception:
                continue

        return list(subdomain_map.values())
