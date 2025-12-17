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

                # Extract and analyze response body for takeover indicators
                body = entry.get('body', '')
                if body:
                    subdomain.http_body_snippet = self._extract_error_message(body)
                    subdomain.takeover_evidence = self._detect_takeover_patterns(body, subdomain.http_status)

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

    def _extract_error_message(self, body: str) -> str:
        """
        Extract relevant error message snippet from HTML body

        Args:
            body: Full HTML response body

        Returns:
            Extracted error message (max 200 chars)
        """
        # Common Shopify error patterns to extract
        shopify_patterns = [
            # Shopify-specific messages
            ("Only one step left", 150),
            ("This shop is currently unavailable", 150),
            ("Sorry, this shop is currently unavailable", 150),
            ("This store doesn't exist", 150),
            ("No shop configured at this domain", 150),
            ("This domain is not connected to a Shopify store", 150),

            # Generic error indicators
            ("<h1>", 200),  # Often contains error title
            ("<title>", 100),  # Page title
        ]

        body_lower = body.lower()

        # Try to find Shopify-specific messages first
        for pattern, max_len in shopify_patterns[:6]:  # Shopify messages
            pattern_lower = pattern.lower()
            if pattern_lower in body_lower:
                # Find the pattern and extract surrounding context
                idx = body_lower.index(pattern_lower)
                # Extract from pattern start to +max_len chars
                snippet = body[idx:idx+max_len].strip()
                # Clean HTML tags
                snippet = snippet.replace('<', ' <').replace('>', '> ')
                import re
                snippet = re.sub(r'<[^>]+>', '', snippet)  # Remove HTML tags
                snippet = re.sub(r'\s+', ' ', snippet)  # Normalize whitespace
                return snippet[:200].strip()

        # Fallback: try to extract h1 or title
        import re
        for tag in ['h1', 'title']:
            match = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', body, re.IGNORECASE | re.DOTALL)
            if match:
                text = match.group(1).strip()
                text = re.sub(r'<[^>]+>', '', text)  # Remove inner HTML tags
                text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                if text:
                    return text[:200].strip()

        # Last resort: return first 200 chars of body (cleaned)
        cleaned = re.sub(r'<[^>]+>', '', body)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:200] if cleaned else "[No error message found]"

    def _detect_takeover_patterns(self, body: str, status_code: int) -> str:
        """
        Detect specific takeover vulnerability patterns in response body

        Args:
            body: HTTP response body
            status_code: HTTP status code

        Returns:
            Evidence description if takeover pattern detected, empty string otherwise
        """
        body_lower = body.lower()

        # Definitive Shopify takeover indicators
        definitive_patterns = {
            "only one step left": "DEFINITE TAKEOVER - Shopify unclaimed store page",
            "this shop is currently unavailable": "HIGH PROBABILITY - Shop unavailable message",
            "sorry, this shop is currently unavailable": "HIGH PROBABILITY - Shop unavailable message",
            "no shop configured at this domain": "DEFINITE TAKEOVER - Domain not connected to any store",
            "this domain is not connected to a shopify store": "DEFINITE TAKEOVER - Unclaimed domain",
        }

        for pattern, evidence in definitive_patterns.items():
            if pattern in body_lower:
                return evidence

        # Suspicious patterns (needs manual verification)
        suspicious_patterns = {
            "404": "SUSPICIOUS - 404 error (verify manually)",
            "not found": "SUSPICIOUS - Not found message",
            "doesn't exist": "SUSPICIOUS - Entity doesn't exist",
        }

        # Only flag suspicious if status is 404/403
        if status_code in [403, 404]:
            for pattern, evidence in suspicious_patterns.items():
                if pattern in body_lower:
                    return evidence

        # Verification/setup page indicators (requires DNS/provider access)
        # These look like "Needs setup" pages but cannot be taken over without DNS access
        verification_patterns = [
            "checking dns records",
            "add these new dns records",
            "shopify_verification_",
            "needs setup",
            "domain verification",
            "verify your domain",
            "txt record",
            "dns management",
            "cloudflare dns",
            "update dns",
            "log in to cloudflare",
            "add dns record",
            "domain setup",
        ]

        for verify_pattern in verification_patterns:
            if verify_pattern in body_lower:
                return "FALSE POSITIVE - Verification page (requires DNS/Cloudflare access)"

        # False positive indicators (login pages, active sites)
        false_positive_patterns = [
            "login",
            "password",
            "sign in",
            "log in",
            "enter your email",
            "username",
            "forgot password",
            "create account",
            "register",
        ]

        for fp_pattern in false_positive_patterns:
            if fp_pattern in body_lower:
                return "FALSE POSITIVE - Active site with login/signup"

        return ""  # No clear evidence
