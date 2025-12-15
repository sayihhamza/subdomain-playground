"""
Parser for httpx JSON output
"""
from typing import List, Dict, Any
from ..models.subdomain import Subdomain


class HTTPXParser:
    """Parser for httpx JSON output"""

    def parse(self, json_data: List[Dict[str, Any]], subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Parse httpx JSON output and update subdomain objects

        Args:
            json_data: List of JSON objects from httpx
            subdomains: Existing subdomain objects to update

        Returns:
            Updated list of Subdomain objects
        """
        # Create lookup map
        subdomain_map = {s.subdomain: s for s in subdomains}

        for entry in json_data:
            try:
                # Extract host from URL
                url = entry.get('url', '')
                host = entry.get('host', '')

                # Try to match subdomain
                if host not in subdomain_map:
                    # Try extracting from URL
                    if '://' in url:
                        host = url.split('://')[1].split('/')[0].split(':')[0]

                if host not in subdomain_map:
                    continue

                subdomain = subdomain_map[host]

                # Extract HTTP info
                subdomain.http_status = entry.get('status_code')
                subdomain.http_title = entry.get('title')
                subdomain.http_server = entry.get('webserver')

                # Extract CDN info
                if entry.get('cdn'):
                    subdomain.cdn = entry.get('cdn_name', 'Unknown CDN')

                # Extract technologies
                if 'tech' in entry:
                    tech = entry['tech']
                    if isinstance(tech, list):
                        subdomain.technologies = tech
                    elif isinstance(tech, str):
                        subdomain.technologies = [tech]

            except Exception:
                continue

        return list(subdomain_map.values())
