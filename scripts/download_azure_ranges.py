#!/usr/bin/env python3
"""
Download Azure IP ranges from Microsoft's Service Tag API
"""
import json
import sys
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def download_azure_ranges():
    """
    Download Azure IP ranges from Microsoft's Service Tag API

    The URL changes weekly, so we'll fetch a reasonable subset of known ranges
    or use the documented API endpoint
    """
    logger.info("Downloading Azure IP ranges...")

    # Microsoft's Service Tags discovery URL
    # This returns the latest download link for Azure IP ranges
    discovery_url = "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519"

    # For now, we'll create a comprehensive list based on known Azure ranges
    # In production, you would scrape the discovery page or use Microsoft's API

    # Common Azure IP ranges (sample - not exhaustive)
    azure_data = {
        'provider': 'Azure',
        'download_date': '2025-12-17',
        'note': 'Azure IP ranges - partial list from known ranges',
        'ipv4_count': 0,
        'ipv6_count': 0,
        'ipv4_ranges': [],
        'ipv6_ranges': [],
        'known_domains': [
            '.cloudapp.net',
            '.cloudapp.azure.com',
            '.azurewebsites.net',
            '.blob.core.windows.net',
            '.azure-api.net',
            '.trafficmanager.net',
            '.azureedge.net',
            '.azure.com',
            '.windows.net',
            '.database.windows.net',
            '.vault.azure.net',
            '.azurecr.io'
        ]
    }

    # Try to fetch from a known working URL
    # Microsoft publishes weekly service tags at predictable locations
    try:
        # This is the JSON API endpoint for Azure Service Tags
        url = "https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_20231204.json"

        logger.info(f"  Attempting to download from: {url}")
        logger.info("  Note: This URL may be outdated. For production, use Microsoft's weekly updated link.")

        with urllib.request.urlopen(url, timeout=60) as response:
            data = json.loads(response.read().decode())

        # Extract IP ranges from Azure services
        ipv4_ranges = []
        ipv6_ranges = []

        for service in data.get('values', []):
            service_name = service.get('name', '')
            properties = service.get('properties', {})

            for prefix in properties.get('addressPrefixes', []):
                if ':' in prefix:  # IPv6
                    ipv6_ranges.append({
                        'ipv6_prefix': prefix,
                        'service': service_name,
                        'region': properties.get('region', 'unknown'),
                        'platform': properties.get('platform', 'Azure')
                    })
                else:  # IPv4
                    ipv4_ranges.append({
                        'ip_prefix': prefix,
                        'service': service_name,
                        'region': properties.get('region', 'unknown'),
                        'platform': properties.get('platform', 'Azure')
                    })

        azure_data['ipv4_ranges'] = ipv4_ranges
        azure_data['ipv6_ranges'] = ipv6_ranges
        azure_data['ipv4_count'] = len(ipv4_ranges)
        azure_data['ipv6_count'] = len(ipv6_ranges)
        azure_data['note'] = 'Azure IP ranges downloaded from Microsoft Service Tags'

        logger.info(f"  ✓ Downloaded {len(ipv4_ranges)} IPv4 ranges")
        logger.info(f"  ✓ Downloaded {len(ipv6_ranges)} IPv6 ranges")

    except Exception as e:
        logger.warning(f"  ✗ Failed to download Azure ranges: {str(e)}")
        logger.info("  ℹ Using domain-based detection only")
        # Return the domain-based fallback

    return azure_data


def main():
    project_root = Path(__file__).parent.parent
    ip_ranges_dir = project_root / 'config' / 'ip_ranges'
    ip_ranges_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Azure IP Range Downloader")
    logger.info("=" * 60)
    logger.info("")

    azure_data = download_azure_ranges()

    if azure_data:
        azure_file = ip_ranges_dir / 'azure.json'
        with open(azure_file, 'w') as f:
            json.dump(azure_data, f, indent=2)

        logger.info("")
        logger.info(f"✓ Saved to: {azure_file}")
        logger.info(f"✓ IPv4 ranges: {azure_data['ipv4_count']}")
        logger.info(f"✓ IPv6 ranges: {azure_data['ipv6_count']}")
        logger.info(f"✓ Known domains: {len(azure_data['known_domains'])}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("Note: For the latest Azure IP ranges, visit:")
    logger.info("https://www.microsoft.com/en-us/download/details.aspx?id=56519")
    logger.info("=" * 60)
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
