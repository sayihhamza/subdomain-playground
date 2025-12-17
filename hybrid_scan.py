#!/usr/bin/env python3
"""
Hybrid Scanner: Fast Pandas filtering + Deep validation

Combines:
1. Pandas fast filtering (instant results like your friend's code)
2. Your scanner's deep validation (accurate CNAME/DNS/takeover detection)

Usage:
    python hybrid_scan.py --csv results.csv --quick-filter
    python hybrid_scan.py --csv results.csv --deep-scan --limit 50
"""
import pandas as pd
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from src.validation.cname_blacklist import CNAMEBlacklist


def parse_args():
    parser = argparse.ArgumentParser(
        description='Hybrid scanner: Fast Pandas filter + Deep validation'
    )

    parser.add_argument(
        '--csv',
        required=True,
        help='Path to enriched CSV file (e.g., results.csv)'
    )

    parser.add_argument(
        '--quick-filter',
        action='store_true',
        help='Quick filter only (instant, like your friend\'s code)'
    )

    parser.add_argument(
        '--deep-scan',
        action='store_true',
        help='Deep scan filtered results (accurate, slower)'
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
        default='pageviews',
        help='How to prioritize for deep scan (default: pageviews)'
    )

    parser.add_argument(
        '--sort-column',
        type=str,
        default=None,
        help='Custom column name to sort by (use with --prioritize column)'
    )

    parser.add_argument(
        '--sort-order',
        choices=['asc', 'desc'],
        default='desc',
        help='Sort order: asc (ascending) or desc (descending, default)'
    )

    parser.add_argument(
        '--output',
        default='filtered_targets.csv',
        help='Output CSV file (default: filtered_targets.csv)'
    )

    parser.add_argument(
        '--exclude-verification',
        action='store_true',
        help='Pre-filter verification subdomains before deep scan'
    )

    return parser.parse_args()


def quick_filter(csv_path: str, exclude_verification: bool = False) -> pd.DataFrame:
    """
    Fast Pandas filtering (your friend's approach)

    Args:
        csv_path: Path to CSV file
        exclude_verification: Apply CNAME blacklist pre-filter

    Returns:
        Filtered DataFrame
    """
    print("🔍 TIER 1: Fast Pre-Filter (Pandas)")
    print("=" * 60)

    # Load CSV
    print(f"Loading CSV: {csv_path}")
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return pd.DataFrame()

    print(f"Total rows: {len(df):,}")

    # Validate required columns
    required_cols = ['Is_Shopify', 'Subdomain', 'HTTP_Status']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Error: Missing required columns: {', '.join(missing_cols)}")
        print(f"Available columns: {', '.join(df.columns.tolist())}")
        return pd.DataFrame()

    # Filter A: Must be Shopify store
    is_shopify = df['Is_Shopify'].astype(str).str.strip().str.lower() == 'yes'
    shopify_count = is_shopify.sum()
    print(f"✅ Shopify stores: {shopify_count:,}")

    # Filter B: Exclude raw myshopify.com domains
    is_custom_domain = ~df['Subdomain'].astype(str).str.contains('myshopify.com', case=False, na=False)
    custom_count = (is_shopify & is_custom_domain).sum()
    print(f"✅ Custom domains (not *.myshopify.com): {custom_count:,}")

    # Filter C: Exclude HTTP 200 and 429 (working sites)
    # Handle both numeric and string status codes
    excluded_statuses = [200, 429, '200', '429', 200.0, 429.0, '200.0', '429.0']
    is_interesting_status = ~df['HTTP_Status'].astype(str).str.strip().isin([str(s) for s in excluded_statuses])

    # Apply all filters
    filtered = df[is_shopify & is_custom_domain & is_interesting_status].copy()
    print(f"✅ Interesting status codes (not 200/429): {len(filtered):,}")

    # Filter D: Exclude verification subdomains (optional)
    if exclude_verification:
        print("\n🔒 Applying CNAME Blacklist Pre-Filter...")
        blacklist = CNAMEBlacklist()

        # Check subdomain names for verification patterns
        verification_patterns = [
            'verification',
            'verify',
            '_acme',
            '_dnsauth',
            'ssl-validation',
        ]

        mask = ~filtered['Subdomain'].str.contains(
            '|'.join(verification_patterns),
            case=False,
            na=False
        )

        before = len(filtered)
        filtered = filtered[mask]
        removed = before - len(filtered)
        print(f"✅ Filtered verification subdomains: {removed:,}")
        print(f"✅ Remaining: {len(filtered):,}")

    print()
    print("📊 Status Code Breakdown:")
    print(filtered['HTTP_Status'].value_counts().head(10))
    print()

    return filtered


def deep_scan(filtered_df: pd.DataFrame, limit: int, prioritize: str = 'status',
              sort_column: str = None, sort_order: str = 'desc'):
    """
    Deep scan with your accurate scanner

    Args:
        filtered_df: Pre-filtered DataFrame
        limit: Max number to scan
        prioritize: How to prioritize ('status', 'sales', 'pageviews', 'random', 'column')
        sort_column: Custom column name for sorting (when prioritize='column')
        sort_order: Sort order ('asc' or 'desc')
    """
    print("🔬 TIER 2: Deep Validation (Your Scanner)")
    print("=" * 60)

    # Prioritize targets
    if prioritize == 'sales':
        print(f"Prioritizing by: Estimated Monthly Sales (top {limit})")

        # Check if column exists
        if 'Est. Monthly Sales' not in filtered_df.columns:
            print(f"❌ Error: Column 'Est. Monthly Sales' not found in CSV")
            print(f"Available columns: {', '.join(filtered_df.columns.tolist())}")
            return None

        # Convert sales to numeric (remove currency symbols), handling NaN
        try:
            filtered_df['Sales_Numeric'] = pd.to_numeric(
                filtered_df['Est. Monthly Sales'].astype(str).str.replace(r'[^\d.]', '', regex=True),
                errors='coerce'
            )
            filtered_df['Sales_Numeric'].fillna(0, inplace=True)
            targets = filtered_df.nlargest(limit, 'Sales_Numeric')
        except Exception as e:
            print(f"❌ Error processing sales data: {e}")
            print(f"Falling back to HTTP status prioritization")
            priority_order = {403: 0, 404: 1, 409: 2}
            filtered_df['Priority'] = filtered_df['HTTP_Status'].map(lambda x: priority_order.get(x, 99))
            targets = filtered_df.nsmallest(limit, 'Priority')

    elif prioritize == 'pageviews':
        print(f"Prioritizing by: Estimated Monthly Page Views (top {limit})")

        # Check if column exists
        if 'Est Monthly Page Views' not in filtered_df.columns:
            print(f"❌ Error: Column 'Est Monthly Page Views' not found in CSV")
            print(f"Available columns: {', '.join(filtered_df.columns.tolist())}")
            return None

        # Convert page views to numeric, handling NaN values
        try:
            filtered_df['PageViews_Numeric'] = pd.to_numeric(
                filtered_df['Est Monthly Page Views'].astype(str).str.replace(r'[^\d.]', '', regex=True),
                errors='coerce'
            )
            # Replace NaN with 0 for sorting
            filtered_df['PageViews_Numeric'].fillna(0, inplace=True)
            targets = filtered_df.nlargest(limit, 'PageViews_Numeric')
        except Exception as e:
            print(f"❌ Error processing page views: {e}")
            print(f"Falling back to HTTP status prioritization")
            priority_order = {403: 0, 404: 1, 409: 2}
            filtered_df['Priority'] = filtered_df['HTTP_Status'].map(lambda x: priority_order.get(x, 99))
            targets = filtered_df.nsmallest(limit, 'Priority')

    elif prioritize == 'column':
        if not sort_column:
            print("❌ Error: --sort-column required when using --prioritize column")
            return None

        if sort_column not in filtered_df.columns:
            print(f"❌ Error: Column '{sort_column}' not found in CSV")
            print(f"Available columns: {', '.join(filtered_df.columns)}")
            return None

        print(f"Prioritizing by: {sort_column} ({sort_order}ending, top {limit})")

        # Try to convert to numeric if possible
        try:
            filtered_df['Sort_Numeric'] = pd.to_numeric(
                filtered_df[sort_column].astype(str).str.replace(r'[^\d.]', '', regex=True),
                errors='coerce'
            )
            if sort_order == 'desc':
                targets = filtered_df.nlargest(limit, 'Sort_Numeric')
            else:
                targets = filtered_df.nsmallest(limit, 'Sort_Numeric')
        except:
            # Fall back to string sorting
            targets = filtered_df.sort_values(
                by=sort_column,
                ascending=(sort_order == 'asc')
            ).head(limit)

    elif prioritize == 'random':
        print(f"Prioritizing by: Random sample ({limit})")
        targets = filtered_df.sample(n=min(limit, len(filtered_df)))

    else:  # status
        print(f"Prioritizing by: HTTP Status (403/404 first, then others)")
        # Prioritize: 403 > 404 > 409 > others
        priority_order = {403: 0, 404: 1, 409: 2}
        filtered_df['Priority'] = filtered_df['HTTP_Status'].map(
            lambda x: priority_order.get(x, 99)
        )
        targets = filtered_df.nsmallest(limit, 'Priority')

    # Export for scanning
    scan_list_path = 'deep_scan_targets.txt'
    targets['Subdomain'].to_csv(scan_list_path, index=False, header=False)

    print(f"\n✅ Exported {len(targets)} targets to: {scan_list_path}")
    print()
    print("🚀 Run deep scan with:")
    print(f"   ./run.sh --domain-list {scan_list_path} --mode quick --provider Shopify --json")
    print()
    print("This will:")
    print("  1. Skip enumeration (subdomains detected) ✅")
    print("  2. Validate DNS with full CNAME chains ✅")
    print("  3. Filter blacklisted CNAMEs ✅")
    print("  4. Check HTTP with body analysis ✅")
    print("  5. Detect takeover evidence ✅")
    print()

    # Show sample targets with relevant metric
    print("📋 Sample targets (first 10):")
    print("-" * 90)

    # Determine which metric to show based on prioritization
    metric_col = None
    if prioritize == 'sales' and 'Est. Monthly Sales' in targets.columns:
        metric_col = 'Est. Monthly Sales'
    elif prioritize == 'pageviews' and 'Est Monthly Page Views' in targets.columns:
        metric_col = 'Est Monthly Page Views'

    for idx, row in targets.head(10).iterrows():
        subdomain = row['Subdomain'] if 'Subdomain' in row else 'N/A'
        status = row['HTTP_Status'] if 'HTTP_Status' in row else 'N/A'
        metric_value = row.get(metric_col, 'N/A') if metric_col else 'N/A'

        # Format output
        print(f"  {str(status):<6} {str(subdomain):<50} {str(metric_value)}")

    if len(targets) > 10:
        print(f"  ... and {len(targets) - 10} more")

    return targets


def main():
    args = parse_args()

    # Validate inputs
    if not Path(args.csv).exists():
        print(f"❌ Error: CSV file not found: {args.csv}")
        return 1

    if not args.quick_filter and not args.deep_scan:
        print("❌ Error: Specify --quick-filter and/or --deep-scan")
        return 1

    # TIER 1: Quick filter
    filtered_df = quick_filter(args.csv, exclude_verification=args.exclude_verification)

    if len(filtered_df) == 0:
        print("❌ No results after filtering")
        return 1

    # Save filtered results
    filtered_df.to_csv(args.output, index=False)
    print(f"💾 Saved filtered results to: {args.output}")
    print()

    # Show quick results (like your friend's code)
    if args.quick_filter:
        print("📊 QUICK RESULTS (Instant - Pre-Filtered)")
        print("=" * 60)
        print(f"Found {len(filtered_df)} potential targets")
        print()

        # Show top results
        display_cols = ['Subdomain', 'HTTP_Status']
        if 'Est. Monthly Sales' in filtered_df.columns:
            display_cols.append('Est. Monthly Sales')

        print(filtered_df[display_cols].head(20).to_string(index=False))

        if len(filtered_df) > 20:
            print(f"\n... and {len(filtered_df) - 20} more")
        print()

    # TIER 2: Deep scan (optional)
    if args.deep_scan:
        if len(filtered_df) > args.limit:
            print(f"⚠️  Found {len(filtered_df)} targets, limiting deep scan to {args.limit}")
            print(f"   (Adjust with --limit)")
            print()

        deep_scan(filtered_df, args.limit, args.prioritize, args.sort_column, args.sort_order)
    else:
        print("💡 TIP: Run with --deep-scan to validate these results with your scanner")
        print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
