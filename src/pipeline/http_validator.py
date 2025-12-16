"""
HTTP validation using httpx
"""
from typing import List
from pathlib import Path
import tempfile

from .base import PipelineStage
from ..models.subdomain import Subdomain
from ..parsers.httpx_parser import HTTPXParser


class HTTPValidator(PipelineStage):
    """HTTP validation pipeline stage"""

    def __init__(self, binary_path: Path, threads: int = 100, timeout: int = 10):
        """
        Initialize HTTP validator

        Args:
            binary_path: Path to httpx binary
            threads: Number of threads for validation
            timeout: HTTP request timeout in seconds
        """
        super().__init__(binary_path)
        self.threads = threads
        self.timeout = timeout
        self.parser = HTTPXParser()

    def validate_batch(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Validate HTTP/HTTPS for a batch of subdomains

        Args:
            subdomains: List of Subdomain objects

        Returns:
            Updated list of Subdomain objects with HTTP info
        """
        if not subdomains:
            return []

        self.logger.info(f"Validating HTTP for {len(subdomains)} subdomains")

        # Create temporary file with subdomain list
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for subdomain in subdomains:
                f.write(f"{subdomain.subdomain}\n")
            temp_file = f.name

        try:
            # Build httpx command with body extraction for takeover detection
            args = [
                '-l', temp_file,
                '-json',            # JSON output
                '-status-code',     # Include status codes
                '-tech-detect',     # Detect technologies
                '-cdn',             # Detect CDN
                '-title',           # Get page title
                '-server',          # Get server header
                '-body',            # Extract response body (for error message detection)
                '-follow-redirects',
                '-silent',
                '-t', str(self.threads),
                '-timeout', str(self.timeout)
            ]

            result = self.run_command(args, timeout=600)

            if result.stdout:
                # Parse JSON output
                json_data = self.parse_json_lines(result.stdout)
                subdomains = self.parser.parse(json_data, subdomains)

                validated_count = sum(1 for s in subdomains if s.http_status)
                self.logger.info(f"Validated HTTP for {validated_count} subdomains")

            return subdomains

        except Exception as e:
            self.logger.error(f"Error validating HTTP: {str(e)}")
            return subdomains
        finally:
            # Clean up temp file
            try:
                Path(temp_file).unlink()
            except:
                pass

    def execute(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Execute HTTP validation

        Args:
            subdomains: List of Subdomain objects

        Returns:
            Updated list of Subdomain objects
        """
        return self.validate_batch(subdomains)
