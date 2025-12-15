"""
Subdomain takeover detector using subzy and nuclei
"""
from typing import List
from pathlib import Path
import tempfile

from .base import PipelineStage
from ..models.subdomain import Subdomain
from ..parsers.subzy_parser import SubzyParser


class TakeoverDetector(PipelineStage):
    """Subdomain takeover detection pipeline stage"""

    def __init__(self, subzy_path: Path, nuclei_path: Path = None, use_nuclei_only: bool = False):
        """
        Initialize takeover detector

        Args:
            subzy_path: Path to subzy binary
            nuclei_path: Path to nuclei binary
            use_nuclei_only: Use only nuclei for verification
        """
        super().__init__(subzy_path)
        self.nuclei_path = nuclei_path
        self.use_nuclei_only = use_nuclei_only
        self.parser = SubzyParser()

    def verify_batch(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Verify subdomain takeover vulnerabilities

        Args:
            subdomains: List of Subdomain objects

        Returns:
            List of vulnerable Subdomain objects
        """
        if not subdomains:
            return []

        self.logger.info(f"Verifying takeover for {len(subdomains)} subdomains")

        # Create temporary file with subdomain list
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for subdomain in subdomains:
                f.write(f"{subdomain.subdomain}\n")
            temp_file = f.name

        try:
            # Run subzy
            args = [
                '--targets', temp_file,
                '--hide_fails',
                '--concurrency', '10'
            ]

            result = self.run_command(args, timeout=300)

            if result.stdout:
                # Try to parse as JSON
                try:
                    import json
                    json_data = json.loads(result.stdout)
                    if isinstance(json_data, dict):
                        json_data = [json_data]
                    subdomains = self.parser.parse(json_data, subdomains)
                except json.JSONDecodeError:
                    # Parse line by line
                    json_data = self.parse_json_lines(result.stdout)
                    subdomains = self.parser.parse(json_data, subdomains)

            # Filter only vulnerable subdomains
            vulnerable = [s for s in subdomains if s.is_vulnerable]

            self.logger.info(f"Found {len(vulnerable)} vulnerable subdomains")

            return vulnerable

        except Exception as e:
            self.logger.error(f"Error detecting takeover: {str(e)}")
            return []
        finally:
            # Clean up temp file
            try:
                Path(temp_file).unlink()
            except:
                pass

    def execute(self, subdomains: List[Subdomain]) -> List[Subdomain]:
        """
        Execute takeover detection

        Args:
            subdomains: List of Subdomain objects

        Returns:
            List of vulnerable Subdomain objects
        """
        return self.verify_batch(subdomains)
