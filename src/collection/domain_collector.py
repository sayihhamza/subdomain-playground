#!/usr/bin/env python3
"""
Domain Collector

Collects and ranks domains from public sources for subdomain takeover scanning.
NO database, NO scheduling - just simple data fetching and caching.
"""

import requests
import csv
import math
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DomainCollector:
    """
    Collect and rank domains from public sources.

    Supports three domain sources:
    1. Bug Bounty Programs - Legal, pre-vetted targets from bounty-targets-data
    2. Tranco Top Domains - High-authority domains with calculated authority scores
    3. Shopify Brands - Curated list of known Shopify-using brands
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize domain collector.

        Args:
            cache_dir: Directory for caching downloaded domain lists.
                      Defaults to 'data/domain_sources'
        """
        self.cache_dir = cache_dir or Path('data/domain_sources')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # URLs for domain sources
        self.bug_bounty_url = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/domains.txt"
        self.tranco_url = "https://tranco-list.eu/top-1m.csv.zip"

    def collect_bug_bounty_domains(self) -> List[str]:
        """
        Download domains from bounty-targets-data GitHub repository.

        These are domains from bug bounty programs (HackerOne, Bugcrowd, etc.)
        that have explicit permission for security testing.

        Returns:
            List of domain strings (e.g., ['example.com', 'test.com'])
        """
        logger.info("Downloading bug bounty domains from bounty-targets-data...")

        try:
            response = requests.get(self.bug_bounty_url, timeout=30)
            response.raise_for_status()

            domains = response.text.strip().split('\n')
            domains = [d.strip() for d in domains if d.strip()]

            # Cache to file
            cache_file = self.cache_dir / 'bug_bounty.txt'
            cache_file.write_text('\n'.join(domains))

            logger.info(f"✅ Downloaded {len(domains)} bug bounty domains")
            return domains

        except Exception as e:
            logger.error(f"Failed to download bug bounty domains: {e}")

            # Try to use cached version
            cache_file = self.cache_dir / 'bug_bounty.txt'
            if cache_file.exists():
                logger.info("Using cached bug bounty domains")
                domains = cache_file.read_text().strip().split('\n')
                return [d.strip() for d in domains if d.strip()]

            raise

    def collect_tranco_domains(self, top_n: int = 10000) -> List[Dict]:
        """
        Download Tranco top N domains with calculated authority scores.

        Tranco is a research-oriented ranking of top websites, designed to be
        manipulation-resistant and reproducible.

        Args:
            top_n: Number of top domains to retrieve (default: 10,000)

        Returns:
            List of dicts with rank, domain, and authority_score:
            [
                {'rank': 1, 'domain': 'google.com', 'authority_score': 100},
                {'rank': 2, 'domain': 'youtube.com', 'authority_score': 98},
                ...
            ]
        """
        logger.info(f"Downloading Tranco top {top_n} domains...")

        try:
            import zipfile
            import io

            # Download ZIP file
            response = requests.get(self.tranco_url, timeout=60)
            response.raise_for_status()

            # Extract CSV from ZIP
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))
            csv_data = zip_file.read('top-1m.csv').decode('utf-8')

            # Parse CSV and calculate authority scores
            domains_with_ranks = []
            reader = csv.reader(csv_data.split('\n'))

            for i, row in enumerate(reader):
                if i >= top_n:
                    break

                if len(row) == 2:
                    rank, domain = row

                    # Calculate authority score based on rank
                    # Logarithmic scale: rank 1 = 100, rank 10000 = ~60
                    authority_score = self._rank_to_authority(int(rank), top_n)

                    domains_with_ranks.append({
                        'rank': int(rank),
                        'domain': domain.strip(),
                        'authority_score': authority_score
                    })

            # Cache to file
            cache_file = self.cache_dir / f'tranco_top{top_n}.csv'
            with open(cache_file, 'w') as f:
                for d in domains_with_ranks:
                    f.write(f"{d['rank']},{d['domain']},{d['authority_score']}\n")

            logger.info(f"✅ Downloaded {len(domains_with_ranks)} Tranco domains")
            return domains_with_ranks

        except Exception as e:
            logger.error(f"Failed to download Tranco domains: {e}")

            # Try to use cached version
            cache_file = self.cache_dir / f'tranco_top{top_n}.csv'
            if cache_file.exists():
                logger.info("Using cached Tranco domains")
                domains_with_ranks = []

                with open(cache_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) == 3:
                            domains_with_ranks.append({
                                'rank': int(parts[0]),
                                'domain': parts[1],
                                'authority_score': int(parts[2])
                            })

                return domains_with_ranks

            raise

    def _rank_to_authority(self, rank: int, max_rank: int) -> int:
        """
        Convert Tranco rank to authority score (1-100) using logarithmic scale.

        This mimics SEMrush's Authority Score methodology:
        - Uses logarithmic scaling (harder to increase score at high levels)
        - Rank 1 gets maximum score (100)
        - Lower ranks get progressively lower scores

        Examples:
            - Rank 1:      Authority 100
            - Rank 10:     Authority 95
            - Rank 100:    Authority 85
            - Rank 1,000:  Authority 75
            - Rank 10,000: Authority 60

        Args:
            rank: Tranco rank position (1-based)
            max_rank: Maximum rank in dataset (used for normalization)

        Returns:
            Authority score (1-100)
        """
        max_score = 100
        min_score = 40  # Even rank 1M has some authority

        # Special case: rank 1 gets maximum score
        if rank == 1:
            return max_score

        # Logarithmic scaling
        # score = max - (log(rank) / log(max_rank)) * (max - min)
        log_factor = math.log(rank) / math.log(max_rank)
        score = max_score - (log_factor * (max_score - min_score))

        return max(min_score, min(max_score, int(score)))

    def collect_shopify_brands(self) -> List[str]:
        """
        Load curated list of known Shopify brands from data/shopify_brands.txt.

        This is a manually curated list of high-authority brands known to use
        Shopify for their e-commerce operations.

        Returns:
            List of domain strings
        """
        brands_file = Path('data/shopify_brands.txt')

        if not brands_file.exists():
            # Create default list if file doesn't exist
            default_brands = [
                'gymshark.com',
                'uniqlo.com',
                'aloyoga.com',
                'kyliecosmetics.com',
                'wearfigs.com',
                'ring.com',
                'sennheiser.com',
                'ColourPop.com',
                'allbirds.com',
                'hiutdenim.co.uk',
            ]

            brands_file.parent.mkdir(parents=True, exist_ok=True)
            brands_file.write_text('\n'.join(default_brands))

            logger.info(f"✅ Created default Shopify brands list ({len(default_brands)} domains)")
            return default_brands

        # Load from file
        brands = [line.strip() for line in brands_file.read_text().split('\n') if line.strip()]
        logger.info(f"✅ Loaded {len(brands)} curated Shopify brands")
        return brands

    def filter_by_authority(self, domains_with_scores: List[Dict], min_score: int = 60) -> List[str]:
        """
        Filter domains by minimum authority score.

        Args:
            domains_with_scores: List of domain dicts with 'authority_score' key
            min_score: Minimum authority score threshold (default: 60)

        Returns:
            List of domain strings that meet the threshold
        """
        filtered = [d['domain'] for d in domains_with_scores if d['authority_score'] >= min_score]
        logger.info(f"✅ Filtered to {len(filtered)} domains with authority >= {min_score}")
        return filtered

    def get_domain_with_score(self, domain: str, domains_with_scores: List[Dict]) -> Optional[Dict]:
        """
        Get authority score for a specific domain.

        Args:
            domain: Domain name to look up
            domains_with_scores: List of domain dicts

        Returns:
            Domain dict if found, None otherwise
        """
        for d in domains_with_scores:
            if d['domain'] == domain:
                return d
        return None

    def collect_myleadfox_domains(self) -> List[str]:
        """
        Load domains from MyLeadFox CSV files in data/domain_sources/myleadfox/

        Reads all CSV files in the myleadfox directory and extracts domains
        from the 'Website' column.

        Returns:
            List of domain strings
        """
        myleadfox_dir = Path('data/domain_sources/myleadfox')

        if not myleadfox_dir.exists():
            logger.warning(f"MyLeadFox directory not found: {myleadfox_dir}")
            return []

        # Find all CSV files
        csv_files = list(myleadfox_dir.glob('*.csv'))

        if not csv_files:
            logger.warning(f"No CSV files found in {myleadfox_dir}")
            return []

        domains = set()

        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)

                    for row in reader:
                        domain = row.get('Website', '').strip()
                        if domain:
                            # Remove quotes if present
                            domain = domain.strip('"')
                            domains.add(domain)

            except Exception as e:
                logger.error(f"Failed to read {csv_file.name}: {e}")
                continue

        domains_list = sorted(list(domains))
        logger.debug(f"Loaded {len(domains_list)} domains from {len(csv_files)} MyLeadFox CSV files")
        return domains_list
