"""
Parser for dnsx JSON output
"""
from typing import List, Dict, Any
from ..models.subdomain import Subdomain


class DNSXParser:
    """Parser for dnsx JSON output"""

    def parse(self, json_data: List[Dict[str, Any]], subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Parse dnsx JSON output and update subdomain objects

        Args:
            json_data: List of JSON objects from dnsx
            subdomains: Existing subdomain objects to update

        Returns:
            Updated list of Subdomain objects
        """
        # Create lookup map
        subdomain_map = {s.subdomain: s for s in subdomains}

        for entry in json_data:
            try:
                host = entry.get('host', '')
                if host not in subdomain_map:
                    continue

                subdomain = subdomain_map[host]

                # Extract CNAME
                if 'cname' in entry:
                    cnames = entry['cname']
                    if isinstance(cnames, list) and cnames:
                        subdomain.cname = cnames[0]  # Take first CNAME
                    elif isinstance(cnames, str):
                        subdomain.cname = cnames

                # Extract A records
                if 'a' in entry:
                    a_records = entry['a']
                    if isinstance(a_records, list):
                        subdomain.a_records = a_records
                    elif isinstance(a_records, str):
                        subdomain.a_records = [a_records]

                # Extract AAAA records
                if 'aaaa' in entry:
                    aaaa_records = entry['aaaa']
                    if isinstance(aaaa_records, list):
                        subdomain.aaaa_records = aaaa_records
                    elif isinstance(aaaa_records, str):
                        subdomain.aaaa_records = [aaaa_records]

            except Exception:
                continue

        return list(subdomain_map.values())
