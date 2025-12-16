"""
Google Sheets domain collection module
"""
import csv
import urllib.request
import urllib.error
from typing import List, Dict, Optional
import logging


class GoogleSheetsReader:
    """Read domains from public Google Sheets"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_sheet_id(self, url: str) -> Optional[str]:
        """
        Extract sheet ID from Google Sheets URL

        Args:
            url: Full Google Sheets URL

        Returns:
            Sheet ID or None if extraction fails
        """
        # Format: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit...
        try:
            if '/spreadsheets/d/' in url:
                parts = url.split('/spreadsheets/d/')[1]
                sheet_id = parts.split('/')[0]
                return sheet_id
        except Exception as e:
            self.logger.error(f"Failed to extract sheet ID: {e}")
        return None

    def read_domains_from_sheet(
        self,
        sheet_url: str,
        sheet_name: str = "domains",
        column_name: str = "Website"
    ) -> List[str]:
        """
        Read domains from a public Google Sheet

        Args:
            sheet_url: Full Google Sheets URL
            sheet_name: Name of the sheet/tab (default: "domains")
            column_name: Column containing domains (default: "Website")

        Returns:
            List of domain strings
        """
        sheet_id = self.extract_sheet_id(sheet_url)
        if not sheet_id:
            raise ValueError(f"Could not extract sheet ID from URL: {sheet_url}")

        # Construct CSV export URL
        # Format: https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

        self.logger.info(f"Fetching Google Sheet: {sheet_id}")
        self.logger.info(f"Sheet name: {sheet_name}")
        self.logger.info(f"Looking for column: {column_name}")

        try:
            # Fetch CSV data
            with urllib.request.urlopen(csv_url, timeout=30) as response:
                csv_data = response.read().decode('utf-8')

            # Parse CSV
            domains = []
            reader = csv.DictReader(csv_data.splitlines())

            # Check if column exists
            if column_name not in reader.fieldnames:
                available_columns = ', '.join(reader.fieldnames)
                raise ValueError(
                    f"Column '{column_name}' not found in sheet. "
                    f"Available columns: {available_columns}"
                )

            # Extract domains from specified column
            for row in reader:
                domain = row.get(column_name, '').strip()
                if domain and domain != '-':
                    # Clean domain (remove http://, https://, www., etc.)
                    domain = self._clean_domain(domain)
                    if domain:
                        domains.append(domain)

            self.logger.info(f"✓ Loaded {len(domains)} domains from Google Sheet")
            return domains

        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise ValueError(
                    f"Sheet '{sheet_name}' not found or sheet is not public. "
                    f"Make sure the sheet is shared as 'Anyone with the link can view'"
                )
            else:
                raise Exception(f"HTTP error fetching sheet: {e}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error fetching sheet: {e}")
        except Exception as e:
            raise Exception(f"Error reading Google Sheet: {e}")

    def _clean_domain(self, domain: str) -> str:
        """
        Clean domain name by removing protocol, www, paths, etc.

        Args:
            domain: Raw domain string

        Returns:
            Cleaned domain name
        """
        # Remove protocol
        domain = domain.replace('http://', '').replace('https://', '')

        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        # Remove path (everything after first /)
        if '/' in domain:
            domain = domain.split('/')[0]

        # Remove port
        if ':' in domain:
            domain = domain.split(':')[0]

        # Remove trailing dot
        domain = domain.rstrip('.')

        # Basic validation - must have at least one dot
        if '.' not in domain:
            return ''

        return domain.lower().strip()

    def get_sheet_info(self, sheet_url: str, sheet_name: str = "domains") -> Dict:
        """
        Get information about a Google Sheet (columns, row count)

        Args:
            sheet_url: Full Google Sheets URL
            sheet_name: Name of the sheet/tab

        Returns:
            Dictionary with sheet information
        """
        sheet_id = self.extract_sheet_id(sheet_url)
        if not sheet_id:
            raise ValueError(f"Could not extract sheet ID from URL: {sheet_url}")

        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

        try:
            with urllib.request.urlopen(csv_url, timeout=30) as response:
                csv_data = response.read().decode('utf-8')

            lines = csv_data.splitlines()
            reader = csv.DictReader(lines)

            rows = list(reader)

            return {
                'sheet_id': sheet_id,
                'sheet_name': sheet_name,
                'columns': reader.fieldnames,
                'row_count': len(rows),
                'sample_data': rows[:5] if rows else []
            }

        except Exception as e:
            raise Exception(f"Error getting sheet info: {e}")
