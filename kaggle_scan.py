#!/usr/bin/env python3
"""
Kaggle-Optimized Subdomain Takeover Scanner

This script is optimized for Kaggle's environment:
- Uses the dataset at /kaggle/input/all-leads-merged/results.csv
- Defaults to sorting by Est Monthly Page Views
- Handles large CSV files efficiently
- Works within Kaggle's 12-hour timeout
"""
import sys
from pathlib import Path

# Import the hybrid scanner
sys.path.insert(0, str(Path(__file__).parent))
from hybrid_scan import main as hybrid_main, parse_args

# Override default arguments for Kaggle
import argparse

def kaggle_parse_args():
    """Parse arguments with Kaggle-specific defaults"""
    parser = argparse.ArgumentParser(
        description='Kaggle-Optimized Hybrid Scanner: Fast filter + Deep validation'
    )

    parser.add_argument(
        '--csv',
        default='/kaggle/input/all-leads-merged/results.csv',
        help='Path to CSV file (default: Kaggle dataset path)'
    )

    parser.add_argument(
        '--quick-filter',
        action='store_true',
        default=False,
        help='Quick filter only (instant results)'
    )

    parser.add_argument(
        '--deep-scan',
        action='store_true',
        default=True,  # Default to deep scan in Kaggle
        help='Deep scan filtered results (default: True)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Limit deep scan to top N results (default: 100)'
    )

    parser.add_argument(
        '--prioritize',
        choices=['status', 'sales', 'pageviews', 'random', 'column'],
        default='pageviews',  # Default to page views
        help='How to prioritize (default: pageviews)'
    )

    parser.add_argument(
        '--sort-column',
        type=str,
        default=None,
        help='Custom column name to sort by'
    )

    parser.add_argument(
        '--sort-order',
        choices=['asc', 'desc'],
        default='desc',
        help='Sort order (default: desc)'
    )

    parser.add_argument(
        '--output',
        default='/kaggle/working/filtered_targets.csv',
        help='Output CSV file (default: /kaggle/working/filtered_targets.csv)'
    )

    parser.add_argument(
        '--exclude-verification',
        action='store_true',
        default=True,  # Default to excluding verification
        help='Pre-filter verification subdomains (default: True)'
    )

    return parser.parse_args()


if __name__ == '__main__':
    print("=" * 60)
    print("Kaggle-Optimized Subdomain Takeover Scanner")
    print("=" * 60)
    print()
    print("Dataset: /kaggle/input/all-leads-merged/results.csv")
    print("Sorting: Est Monthly Page Views (highest first)")
    print("Verification Filtering: Enabled")
    print()

    # Use Kaggle-optimized defaults
    sys.argv[0] = 'kaggle_scan.py'

    # If no arguments provided, use smart defaults
    if len(sys.argv) == 1:
        print("Using Kaggle defaults:")
        print("  --csv /kaggle/input/all-leads-merged/results.csv")
        print("  --deep-scan")
        print("  --limit 100")
        print("  --prioritize pageviews")
        print("  --exclude-verification")
        print()

        sys.argv.extend([
            '--csv', '/kaggle/input/all-leads-merged/results.csv',
            '--quick-filter',
            '--deep-scan',
            '--limit', '100',
            '--prioritize', 'pageviews',
            '--exclude-verification',
            '--output', '/kaggle/working/filtered_targets.csv'
        ])

    # Run the hybrid scanner
    sys.exit(hybrid_main())
