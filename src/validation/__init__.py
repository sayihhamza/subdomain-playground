"""
DNS and subdomain validation modules
"""
from .dns_validator import DNSValidator
from .wildcard_detector import WildcardDetector

__all__ = ['DNSValidator', 'WildcardDetector']
