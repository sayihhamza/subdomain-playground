#!/usr/bin/env python3
"""
Download cloud provider IP ranges for accurate provider detection

This enables IP-based provider detection instead of just CNAME matching.
"""
import json
import sys
from pathlib import Path
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def download_aws_ranges():
    """Download AWS IP ranges from official source"""
    logger.info("Downloading AWS IP ranges...")
    url = "https://ip-ranges.amazonaws.com/ip-ranges.json"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        # Extract IPv4 ranges
        ipv4_ranges = []
        for prefix in data.get('prefixes', []):
            ipv4_ranges.append({
                'ip_prefix': prefix.get('ip_prefix'),
                'region': prefix.get('region'),
                'service': prefix.get('service'),
                'network_border_group': prefix.get('network_border_group')
            })

        # Extract IPv6 ranges
        ipv6_ranges = []
        for prefix in data.get('ipv6_prefixes', []):
            ipv6_ranges.append({
                'ipv6_prefix': prefix.get('ipv6_prefix'),
                'region': prefix.get('region'),
                'service': prefix.get('service'),
                'network_border_group': prefix.get('network_border_group')
            })

        output = {
            'provider': 'AWS',
            'download_date': data.get('createDate'),
            'ipv4_count': len(ipv4_ranges),
            'ipv6_count': len(ipv6_ranges),
            'ipv4_ranges': ipv4_ranges,
            'ipv6_ranges': ipv6_ranges
        }

        logger.info(f"  Downloaded {len(ipv4_ranges)} IPv4 ranges and {len(ipv6_ranges)} IPv6 ranges")
        return output

    except Exception as e:
        logger.error(f"  Failed to download AWS ranges: {str(e)}")
        return None


def download_azure_ranges():
    """Download Azure IP ranges"""
    logger.info("Downloading Azure IP ranges...")
    logger.info("  Note: Azure IP ranges require manual download from Microsoft")
    logger.info("  Visit: https://www.microsoft.com/en-us/download/details.aspx?id=56519")
    logger.info("  For now, creating placeholder with common Azure ranges")

    # Placeholder with some known Azure ranges
    output = {
        'provider': 'Azure',
        'download_date': 'manual',
        'note': 'Azure requires manual download - this is a placeholder',
        'ipv4_count': 0,
        'ipv6_count': 0,
        'ipv4_ranges': [],
        'ipv6_ranges': [],
        'known_domains': [
            '.cloudapp.net',
            '.cloudapp.azure.com',
            '.azurewebsites.net',
            '.blob.core.windows.net',
            '.azure-api.net'
        ]
    }

    return output


def download_gcp_ranges():
    """Download Google Cloud Platform IP ranges"""
    logger.info("Downloading GCP IP ranges...")
    url = "https://www.gstatic.com/ipranges/cloud.json"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        # Extract IPv4 ranges
        ipv4_ranges = []
        ipv6_ranges = []

        for prefix in data.get('prefixes', []):
            if 'ipv4Prefix' in prefix:
                ipv4_ranges.append({
                    'ip_prefix': prefix.get('ipv4Prefix'),
                    'service': prefix.get('service', 'Google Cloud'),
                    'scope': prefix.get('scope', 'unknown')
                })
            elif 'ipv6Prefix' in prefix:
                ipv6_ranges.append({
                    'ipv6_prefix': prefix.get('ipv6Prefix'),
                    'service': prefix.get('service', 'Google Cloud'),
                    'scope': prefix.get('scope', 'unknown')
                })

        output = {
            'provider': 'GCP',
            'download_date': data.get('creationTime'),
            'ipv4_count': len(ipv4_ranges),
            'ipv6_count': len(ipv6_ranges),
            'ipv4_ranges': ipv4_ranges,
            'ipv6_ranges': ipv6_ranges
        }

        logger.info(f"  Downloaded {len(ipv4_ranges)} IPv4 ranges and {len(ipv6_ranges)} IPv6 ranges")
        return output

    except Exception as e:
        logger.error(f"  Failed to download GCP ranges: {str(e)}")
        return None


def main():
    project_root = Path(__file__).parent.parent
    ip_ranges_dir = project_root / 'config' / 'ip_ranges'
    ip_ranges_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Cloud Provider IP Range Downloader")
    logger.info("=" * 60)
    logger.info("")

    # Download AWS ranges
    aws_data = download_aws_ranges()
    if aws_data:
        aws_file = ip_ranges_dir / 'aws.json'
        with open(aws_file, 'w') as f:
            json.dump(aws_data, f, indent=2)
        logger.info(f"  Saved to: {aws_file}")
    logger.info("")

    # Download Azure ranges
    azure_data = download_azure_ranges()
    if azure_data:
        azure_file = ip_ranges_dir / 'azure.json'
        with open(azure_file, 'w') as f:
            json.dump(azure_data, f, indent=2)
        logger.info(f"  Saved to: {azure_file}")
    logger.info("")

    # Download GCP ranges
    gcp_data = download_gcp_ranges()
    if gcp_data:
        gcp_file = ip_ranges_dir / 'gcp.json'
        with open(gcp_file, 'w') as f:
            json.dump(gcp_data, f, indent=2)
        logger.info(f"  Saved to: {gcp_file}")
    logger.info("")

    logger.info("=" * 60)
    logger.info("Download Complete")
    logger.info("=" * 60)
    logger.info("")
    logger.info("IP ranges saved to: config/ip_ranges/")
    logger.info("")
    logger.info("Note: Azure requires manual download. Visit:")
    logger.info("https://www.microsoft.com/en-us/download/details.aspx?id=56519")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
