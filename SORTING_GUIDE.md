# Hybrid Scanner - Sorting & Prioritization Guide

## Overview

You can now sort your CSV data by **any column** before deep scanning. This helps you target the most valuable or interesting subdomains first.

---

## Quick Examples

### 1. Sort by Page Views (Highest First)
```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize pageviews
```

### 2. Sort by Custom Column
```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize column \
  --sort-column "Est Monthly Page Views" \
  --sort-order desc
```

### 3. Sort by Multiple Criteria
```bash
# First filter by page views, then prioritize by HTTP status
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize column \
  --sort-column "Est Monthly Page Views" \
  --sort-order desc
```

---

## Built-in Prioritization Options

### 1. `--prioritize status` (Default)

Prioritizes by HTTP status code - most likely to be vulnerable first:

```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize status
```

**Priority Order:**
1. **403 Forbidden** (most likely takeover/verification)
2. **404 Not Found** (unclaimed stores)
3. **409 Conflict** (configuration issues)
4. Others

**Use When:** You want to find vulnerabilities fast

---

### 2. `--prioritize sales`

Prioritizes by estimated monthly sales - highest value targets first:

```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize sales
```

**Sorts By:** `Est. Monthly Sales` column (highest first)

**Use When:** You want to target high-revenue stores

---

### 3. `--prioritize pageviews`

Prioritizes by estimated monthly page views - most traffic first:

```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize pageviews
```

**Sorts By:** `Est Monthly Page Views` column (highest first)

**Use When:** You want to target high-traffic sites

---

### 4. `--prioritize random`

Random sampling - good for statistical analysis:

```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize random
```

**Use When:** You want an unbiased sample

---

### 5. `--prioritize column` (Custom Sorting)

Sort by **any column** in your CSV:

```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 100 \
  --prioritize column \
  --sort-column "Your Column Name" \
  --sort-order desc
```

**Options:**
- `--sort-column`: Exact column name from CSV (case-sensitive)
- `--sort-order`: `desc` (high to low) or `asc` (low to high)

**Use When:** You want custom sorting logic

---

## Common Use Cases

### Use Case 1: Target High-Traffic Sites
```bash
python hybrid_scan.py \
  --csv /kaggle/input/shopify-data/results.csv \
  --quick-filter \
  --exclude-verification \
  --deep-scan \
  --limit 100 \
  --prioritize pageviews
```

**Output:**
```
Prioritizing by: Estimated Monthly Page Views (top 100)
✅ Exported 100 targets to: deep_scan_targets.txt

📋 Sample targets (first 10):
  403    shop.hightraffic.com                     450,000 views
  404    store.popular.com                        380,000 views
  403    wholesale.trending.com                   320,000 views
  ...
```

---

### Use Case 2: Target by Specific Metric

If your CSV has a custom metric like "Domain Authority" or "Alexa Rank":

```bash
python hybrid_scan.py \
  --csv your_data.csv \
  --deep-scan \
  --limit 50 \
  --prioritize column \
  --sort-column "Domain Authority" \
  --sort-order desc
```

---

### Use Case 3: Combine Multiple Filters

```bash
# Step 1: Quick filter + sort by page views
python hybrid_scan.py \
  --csv /kaggle/input/data.csv \
  --quick-filter \
  --exclude-verification \
  --output high_traffic.csv

# Step 2: Deep scan top 100 by HTTP status (from high traffic sites)
python hybrid_scan.py \
  --csv high_traffic.csv \
  --deep-scan \
  --limit 100 \
  --prioritize status
```

---

## Available Columns in Your Dataset

Your enriched CSV has **42 columns**. Here are the key sortable ones:

### Traffic Metrics
- `Est Monthly Page Views` - Page views per month
- `Est Monthly Unique Visitors` - Unique visitors per month

### Business Metrics
- `Est. Monthly Sales` - Estimated monthly revenue
- `Product Count` - Number of products

### Technical Metrics
- `HTTP_Status` - HTTP status code
- `Response_Time` - Server response time
- `SSL_Status` - SSL certificate status

### Domain Metrics
- `Domain_Age` - Age of domain
- `Domain_Authority` - SEO authority score
- `Backlinks_Count` - Number of backlinks

### Geographic
- `Country` - Country location
- `Region` - Region/state

To see all columns in your CSV:
```bash
python -c "import pandas as pd; df = pd.read_csv('your_data.csv'); print(df.columns.tolist())"
```

---

## Sorting Order

### Descending (Default) - High to Low
```bash
--sort-order desc
```

Use for:
- Page views (want highest traffic)
- Sales (want highest revenue)
- Domain authority (want most authoritative)

### Ascending - Low to High
```bash
--sort-order asc
```

Use for:
- Response time (want fastest sites)
- Domain age (want newest domains)
- Product count (want smaller stores)

---

## Examples with Real Data

### Example 1: Target Top 50 High-Traffic + 403 Errors

```bash
# First, get high-traffic sites
python hybrid_scan.py \
  --csv results.csv \
  --quick-filter \
  --exclude-verification \
  --prioritize pageviews \
  --output high_traffic.csv

# Filter for 403 errors only
python -c "
import pandas as pd
df = pd.read_csv('high_traffic.csv')
df_403 = df[df['HTTP_Status'] == 403]
df_403.to_csv('high_traffic_403.csv', index=False)
"

# Deep scan those specific targets
python hybrid_scan.py \
  --csv high_traffic_403.csv \
  --deep-scan \
  --limit 50 \
  --prioritize pageviews
```

---

### Example 2: Target by Multiple Metrics

```bash
# Get top 200 by page views
python hybrid_scan.py \
  --csv results.csv \
  --quick-filter \
  --deep-scan \
  --limit 200 \
  --prioritize pageviews \
  --output top_200_traffic.csv

# From those 200, get top 50 by sales
python hybrid_scan.py \
  --csv top_200_traffic.csv \
  --deep-scan \
  --limit 50 \
  --prioritize sales
```

---

### Example 3: Geographic Targeting

```bash
# Target US-based sites with high traffic
python -c "
import pandas as pd
df = pd.read_csv('results.csv')
df_us = df[df['Country'] == 'US']
df_us.to_csv('us_sites.csv', index=False)
"

python hybrid_scan.py \
  --csv us_sites.csv \
  --quick-filter \
  --deep-scan \
  --limit 100 \
  --prioritize pageviews
```

---

## Performance Tips

### 1. Filter Before Sorting

Always use `--quick-filter` first to reduce dataset size:

```bash
# Good: Filter then sort
python hybrid_scan.py \
  --csv large_file.csv \
  --quick-filter \
  --exclude-verification \
  --output filtered.csv

python hybrid_scan.py \
  --csv filtered.csv \
  --deep-scan \
  --limit 100 \
  --prioritize pageviews
```

### 2. Use Appropriate Limits

- **Testing**: `--limit 10` (very fast)
- **Quick scan**: `--limit 50` (5-10 minutes)
- **Standard**: `--limit 100` (10-15 minutes)
- **Thorough**: `--limit 200` (20-30 minutes)

### 3. Combine with Verification Filtering

```bash
python hybrid_scan.py \
  --csv data.csv \
  --quick-filter \
  --exclude-verification \  # Removes false positives upfront
  --deep-scan \
  --limit 100 \
  --prioritize pageviews
```

---

## Error Handling

### Error: Column not found

```
❌ Error: Column 'Page Views' not found in CSV
Available columns: Subdomain, HTTP_Status, Est Monthly Page Views, ...
```

**Fix:** Use exact column name (case-sensitive):
```bash
--sort-column "Est Monthly Page Views"  # Correct
# NOT: --sort-column "Page Views"       # Wrong
```

### Error: Non-numeric column

If the column contains text (not numbers), the scanner will:
1. Try to extract numbers (e.g., "USD $12,000" → 12000)
2. Fall back to string sorting if extraction fails

---

## Complete Workflow Example

### Goal: Find high-traffic Shopify stores with takeover vulnerabilities

```bash
# Step 1: Quick filter for Shopify stores (2 seconds)
python hybrid_scan.py \
  --csv /kaggle/input/data.csv \
  --quick-filter \
  --exclude-verification \
  --output shopify_filtered.csv

# Output: Found 464 Shopify stores

# Step 2: Sort by page views, prioritize top 100 (instant)
python hybrid_scan.py \
  --csv shopify_filtered.csv \
  --deep-scan \
  --limit 100 \
  --prioritize pageviews

# Output: Exported 100 targets to deep_scan_targets.txt

# Step 3: Deep scan with your accurate scanner (15 minutes)
./run.sh \
  --domain-list deep_scan_targets.txt \
  --mode quick \
  --provider Shopify \
  --json \
  --output takeover_results.json

# Output: Found 25-30 potential takeovers
```

**Result:** Found high-traffic vulnerable stores in 15 minutes vs 4 hours for full scan

---

## Summary

### Quick Reference

| Option | Description | Example |
|--------|-------------|---------|
| `--prioritize status` | HTTP status (403/404 first) | Default |
| `--prioritize sales` | Highest sales first | `--prioritize sales` |
| `--prioritize pageviews` | Most traffic first | `--prioritize pageviews` |
| `--prioritize random` | Random sample | `--prioritize random` |
| `--prioritize column` | Custom column | `--prioritize column --sort-column "Name"` |
| `--sort-order desc` | High to low (default) | `--sort-order desc` |
| `--sort-order asc` | Low to high | `--sort-order asc` |
| `--limit N` | Limit to top N results | `--limit 100` |

### Best Practices

1. ✅ Always use `--quick-filter` first
2. ✅ Use `--exclude-verification` to reduce false positives
3. ✅ Start with `--limit 50` for testing
4. ✅ Sort by metrics that matter to you (traffic, sales, status)
5. ✅ Combine filters for targeted scanning

You can now prioritize your scans by any metric in your dataset!
