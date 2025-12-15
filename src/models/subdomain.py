"""
Subdomain data model
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Subdomain:
    """Subdomain data model"""

    # Basic info
    subdomain: str
    parent_domain: str

    # DNS info
    cname: Optional[str] = None
    cname_chain: List[str] = field(default_factory=list)
    a_records: List[str] = field(default_factory=list)
    aaaa_records: List[str] = field(default_factory=list)
    ns_records: List[str] = field(default_factory=list)
    dns_resolved: bool = False
    nxdomain: bool = False

    # Enhanced DNS details
    dns_ttl: Optional[int] = None
    dns_response_code: Optional[str] = None
    authoritative_ns: Optional[str] = None
    soa_record: Optional[str] = None
    mx_records: List[str] = field(default_factory=list)
    txt_records: List[str] = field(default_factory=list)
    cname_chain_count: int = 0
    final_cname_target: Optional[str] = None

    # Takeover detection fields
    dangling_cname: bool = False  # CNAME points to non-existent target
    vulnerable_cname_hop: Optional[str] = None  # Which hop in chain is vulnerable
    takeover_risk: Optional[str] = None  # Risk level based on DNS analysis

    # HTTP info
    http_status: Optional[int] = None
    http_title: Optional[str] = None
    http_server: Optional[str] = None
    technologies: List[str] = field(default_factory=list)
    cdn: Optional[str] = None

    # Provider info
    provider: Optional[str] = None
    provider_pattern: Optional[str] = None
    provider_detection_method: Optional[str] = None
    provider_service: Optional[str] = None
    provider_region: Optional[str] = None
    ip_confirmed: bool = False

    # Vulnerability info
    is_vulnerable: bool = False
    vulnerability_type: Optional[str] = None
    fingerprint_matched: Optional[str] = None
    risk_level: Optional[str] = None
    verified_by: List[str] = field(default_factory=list)

    # Metadata
    discovered_at: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None

    def __post_init__(self):
        """Post-initialization validation"""
        if not self.subdomain:
            raise ValueError("Subdomain cannot be empty")

        # Normalize subdomain
        self.subdomain = self.subdomain.lower().strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime to ISO format
        data['discovered_at'] = self.discovered_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subdomain':
        """Create from dictionary"""
        # Convert ISO format to datetime
        if 'discovered_at' in data and isinstance(data['discovered_at'], str):
            data['discovered_at'] = datetime.fromisoformat(data['discovered_at'])
        return cls(**data)

    def matches_provider_pattern(self, pattern: str) -> bool:
        """Check if CNAME matches a provider pattern"""
        if not self.cname:
            return False

        import re
        try:
            return bool(re.search(pattern, self.cname, re.IGNORECASE))
        except re.error:
            return False

    def is_wildcard(self) -> bool:
        """Check if this appears to be a wildcard DNS entry"""
        if self.cname and '*' in self.cname:
            return True
        return False
