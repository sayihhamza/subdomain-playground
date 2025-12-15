"""
Confidence scoring system for vulnerability assessment
"""
from typing import Dict, Any, List


class ConfidenceScorer:
    """Calculate confidence scores for subdomain takeover vulnerabilities"""

    # Scoring weights
    WEIGHTS = {
        'nxdomain': 40,           # NXDOMAIN is strong indicator
        'http_404': 30,           # 404 status code
        'http_403': 10,           # 403 might indicate unclaimed (generic)
        'http_403_shopify': 35,   # 403 on Shopify is STRONG indicator of unclaimed store
        'fingerprint_high': 25,   # High confidence fingerprint
        'fingerprint_medium': 15, # Medium confidence fingerprint
        'fingerprint_low': 5,     # Low confidence fingerprint
        'cname_pattern': 5,       # CNAME matches pattern
    }

    def __init__(self):
        self.evidence = []

    def calculate_score(self, finding: Dict[str, Any]) -> int:
        """
        Calculate confidence score (0-100)

        Args:
            finding: Dictionary with vulnerability data

        Returns:
            Score from 0 to 100
        """
        score = 0
        self.evidence = []

        # DNS factors
        if finding.get('nxdomain'):
            score += self.WEIGHTS['nxdomain']
            self.evidence.append("NXDOMAIN - DNS record does not exist")

        # HTTP status code factors
        http_status = finding.get('http_status') or finding.get('status')
        provider = finding.get('provider', '').lower()

        if http_status == 404:
            score += self.WEIGHTS['http_404']
            self.evidence.append("HTTP 404 - Not Found")
        elif http_status == 403:
            # Shopify 403 is a STRONG indicator of unclaimed store
            if provider == 'shopify':
                score += self.WEIGHTS['http_403_shopify']
                self.evidence.append("HTTP 403 - Shopify unclaimed store (HIGH RISK)")
            else:
                score += self.WEIGHTS['http_403']
                self.evidence.append("HTTP 403 - Forbidden")

        # Fingerprint factors
        fingerprint = finding.get('fingerprint_matched')
        if fingerprint:
            confidence_level = finding.get('fingerprint_confidence', 'medium')
            if confidence_level == 'high':
                score += self.WEIGHTS['fingerprint_high']
                self.evidence.append(f"High-confidence fingerprint matched: '{fingerprint[:50]}'")
            elif confidence_level == 'medium':
                score += self.WEIGHTS['fingerprint_medium']
                self.evidence.append(f"Medium-confidence fingerprint matched: '{fingerprint[:50]}'")
            else:
                score += self.WEIGHTS['fingerprint_low']
                self.evidence.append(f"Fingerprint matched: '{fingerprint[:50]}'")

        # CNAME pattern match
        if finding.get('cname') and finding.get('provider'):
            score += self.WEIGHTS['cname_pattern']
            self.evidence.append(f"CNAME points to {finding['provider']} ({finding['cname']})")

        return min(score, 100)  # Cap at 100

    def classify_risk(self, score: int) -> str:
        """
        Classify risk level based on score

        Args:
            score: Confidence score (0-100)

        Returns:
            Risk level string
        """
        if score >= 80:
            return "critical"  # Definitely vulnerable
        elif score >= 60:
            return "high"      # Very likely vulnerable
        elif score >= 40:
            return "medium"    # Possibly vulnerable
        elif score >= 20:
            return "low"       # Unlikely vulnerable
        else:
            return "info"      # Informational only

    def get_evidence(self) -> List[str]:
        """Get evidence list from last scoring"""
        return self.evidence.copy()

    def assess(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete assessment with score, risk, and evidence

        Args:
            finding: Vulnerability finding data

        Returns:
            Assessment result with score, risk, evidence
        """
        score = self.calculate_score(finding)
        risk = self.classify_risk(score)
        evidence = self.get_evidence()

        return {
            'confidence_score': score,
            'risk_level': risk,
            'evidence': evidence,
            'vulnerable': score >= 60  # High/Critical = vulnerable
        }
