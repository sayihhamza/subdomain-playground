# Kaggle Deployment Guide

## Pre-Deployment Checklist ✅

### 1. Dataset Configuration
- ✅ Dataset path: `/kaggle/input/all-leads-merged/results.csv`
- ✅ Default sorting: `Est Monthly Page Views` (highest first)
- ✅ Verification filtering: Enabled by default
- ✅ Output path: `/kaggle/working/filtered_targets.csv`

### 2. Column Validation
Your dataset has these columns:
```
- Est. Monthly Sales
- Est. Products Sold
- Platform
- Plan
- Theme
- Installed Apps
- Technology Used
- Est Monthly Page Views  ← DEFAULT SORT
- Est Monthly Visits
- Shipping Partners
- Facebook, Instagram, Twitter, LinkedIn, YouTube, Pinterest, Tiktok
- Twitter Followers, Twitter Posts
- YouTube Followers
- Pinterest Followers, Pinterest Posts
- Tiktok Followers
- Keywords
- Lang
- Subdomain  ← REQUIRED
- Is_Subdomain
- Is_Shopify  ← REQUIRED
- CNAME_Record
- HTTP_Status  ← REQUIRED
- Error_Message
- Timestamp
```

**Required Columns:**
- ✅ `Is_Shopify` - Filter for Shopify stores
- ✅ `Subdomain` - Target domains to scan
- ✅ `HTTP_Status` - Prioritization and filtering
- ✅ `Est Monthly Page Views` - Default sorting metric

---

## Bug Fixes Applied

### 1. CSV Loading
**Problem:** Large CSV files cause memory issues
**Fix:** Added `low_memory=False` parameter
```python
df = pd.read_csv(csv_path, low_memory=False)
```

### 2. Missing Column Detection
**Problem:** Script crashes if columns are missing
**Fix:** Validate required columns before processing
```python
required_cols = ['Is_Shopify', 'Subdomain', 'HTTP_Status']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    print(f"❌ Error: Missing columns: {', '.join(missing_cols)}")
    return DataFrame()
```

### 3. Data Type Handling
**Problem:** Mixed data types (200 vs "200") cause comparison issues
**Fix:** Normalize all values to strings before comparison
```python
is_shopify = df['Is_Shopify'].astype(str).str.strip().str.lower() == 'yes'
is_interesting_status = ~df['HTTP_Status'].astype(str).str.strip().isin([str(s) for s in excluded_statuses])
```

### 4. NaN Value Handling
**Problem:** NaN values cause sorting errors
**Fix:** Fill NaN with 0 before sorting
```python
filtered_df['PageViews_Numeric'].fillna(0, inplace=True)
```

### 5. Graceful Degradation
**Problem:** Script fails if page views column missing
**Fix:** Fall back to HTTP status prioritization
```python
if 'Est Monthly Page Views' not in filtered_df.columns:
    print("Falling back to HTTP status prioritization")
    # Use status-based sorting instead
```

---

## Performance Optimizations

### 1. Efficient CSV Loading
```python
# Low memory mode for large files
df = pd.read_csv(csv_path, low_memory=False)
```

### 2. Chunked DNS Validation
```python
# Process 1000 domains at a time
if len(subdomains) > 1000:
    process_in_chunks(subdomains, chunk_size=1000)
```

### 3. Parallel DNS Resolution
```python
# 100 threads for DNS queries
dnsx -threads 100 -r 8.8.8.8,1.1.1.1,208.67.222.222
```

### 4. Fast Pandas Filtering
```python
# Boolean indexing (vectorized operations)
is_shopify = df['Is_Shopify'] == 'Yes'
is_custom_domain = ~df['Subdomain'].str.contains('myshopify.com')
filtered = df[is_shopify & is_custom_domain & is_interesting_status]
```

---

## Files to Upload to Kaggle

### 1. Core Scanner Files
```
src/
├── __init__.py
├── config.py
├── orchestrator_v2.py
├── models/
│   ├── __init__.py
│   └── subdomain.py
├── validation/
│   ├── __init__.py
│   ├── dns_validator.py
│   ├── wildcard_detector.py
│   └── cname_blacklist.py
├── identification/
│   ├── __init__.py
│   ├── provider_detector.py
│   └── ip_matcher.py
├── parsers/
│   ├── __init__.py
│   └── httpx_parser.py
├── pipeline/
│   ├── __init__.py
│   ├── subdomain_enum_v2.py
│   ├── http_validator.py
│   └── takeover_detector.py
└── utils/
    ├── __init__.py
    └── logging_utils.py
```

### 2. Configuration Files
```
config/
├── settings.yaml
├── providers.yaml
├── cname_blacklist.yaml
└── ip_ranges/
    ├── aws.json
    ├── azure.json
    ├── gcp.json
    └── shopify.json
```

### 3. Main Scripts
```
scan.py                 ← Main scanner
hybrid_scan.py          ← Hybrid scanner (fast filter + deep scan)
kaggle_scan.py          ← Kaggle-optimized wrapper
run.sh                  ← Shell wrapper
```

### 4. Data Files
```
data/
└── wordlists/
    └── best-dns-wordlist.txt  (1,775 entries)
```

---

## Kaggle Notebook Setup

### Cell 1: Install Tools
```python
%%bash
# Build tools
mkdir -p ~/go/bin

# Build dnsx
echo "Building dnsx..."
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest

# Build httpx
echo "Building httpx..."
go install github.com/projectdiscovery/httpx/cmd/httpx@latest

# Build subzy
echo "Building subzy..."
go install github.com/LukaSikic/subzy@latest

# Verify builds
ls -lh ~/go/bin/
```

### Cell 2: Set Environment Variables
```python
import os

# Set tool paths
os.environ['DNSX_PATH'] = '/root/go/bin/dnsx'
os.environ['HTTPX_PATH'] = '/root/go/bin/httpx'
os.environ['SUBZY_PATH'] = '/root/go/bin/subzy'

# Verify
print(f"DNSX: {os.environ['DNSX_PATH']}")
print(f"HTTPX: {os.environ['HTTPX_PATH']}")
print(f"SUBZY: {os.environ['SUBZY_PATH']}")
```

### Cell 3: Run Hybrid Scanner
```python
%%bash
# Quick filter + deep scan top 100 by page views
python kaggle_scan.py

# This will:
# 1. Load /kaggle/input/all-leads-merged/results.csv
# 2. Filter for Shopify stores (not *.myshopify.com, not 200/429)
# 3. Exclude verification subdomains
# 4. Sort by Est Monthly Page Views (highest first)
# 5. Export top 100 to /kaggle/working/deep_scan_targets.txt
```

### Cell 4: Run Deep Scanner
```python
%%bash
# Deep scan the prioritized targets
./run.sh \
  --domain-list /kaggle/working/deep_scan_targets.txt \
  --mode quick \
  --provider Shopify \
  --json \
  --output /kaggle/working/takeover_results.json
```

### Cell 5: View Results
```python
import pandas as pd
import json

# Load results
with open('/kaggle/working/takeover_results.json') as f:
    results = json.load(f)

# Show vulnerabilities
vulnerable = [r for r in results if r.get('evidence', '').startswith('DEFINITE')]
print(f"Found {len(vulnerable)} definite takeovers")

# Display
df = pd.DataFrame(vulnerable)
df[['subdomain', 'status', 'evidence', 'confidence', 'message']].head(20)
```

---

## Expected Timeline

### Kaggle Execution Time

| Phase | Time | Output |
|-------|------|--------|
| **Cell 1: Build Tools** | 5-8 min | Tools installed |
| **Cell 2: Set Env Vars** | 1 sec | Environment ready |
| **Cell 3: Quick Filter** | 2-5 sec | 100 targets exported |
| **Cell 4: Deep Scan** | 10-15 min | Vulnerabilities found |
| **Cell 5: View Results** | 1 sec | Results displayed |
| **TOTAL** | **15-25 min** | Complete scan ✅ |

**Well within Kaggle's 12-hour limit** ✅

---

## Command Reference

### Basic Usage (Default: Page Views)
```bash
python kaggle_scan.py
```

### Custom Sorting Options
```bash
# Sort by sales
python hybrid_scan.py \
  --csv /kaggle/input/all-leads-merged/results.csv \
  --deep-scan \
  --limit 100 \
  --prioritize sales

# Sort by HTTP status (403/404 first)
python hybrid_scan.py \
  --csv /kaggle/input/all-leads-merged/results.csv \
  --deep-scan \
  --limit 100 \
  --prioritize status

# Sort by custom column
python hybrid_scan.py \
  --csv /kaggle/input/all-leads-merged/results.csv \
  --deep-scan \
  --limit 100 \
  --prioritize column \
  --sort-column "Twitter Followers" \
  --sort-order desc
```

---

## Troubleshooting

### Issue 1: CSV Not Found
```
❌ Error: CSV file not found: /kaggle/input/all-leads-merged/results.csv
```

**Fix:** Verify dataset is attached to notebook:
1. Go to "Add Data" in Kaggle
2. Search for your dataset
3. Click "Add"

### Issue 2: Missing Columns
```
❌ Error: Missing required columns: Est Monthly Page Views
Available columns: [list of columns]
```

**Fix:** Use a different prioritization:
```bash
python kaggle_scan.py --prioritize status
```

### Issue 3: Tools Not Found
```
❌ Error: dnsx binary not found
```

**Fix:** Rebuild tools in Cell 1:
```bash
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
```

### Issue 4: Memory Issues
```
MemoryError: Unable to allocate array
```

**Fix:** Reduce limit:
```bash
python kaggle_scan.py --limit 50
```

---

## Testing Before Deployment

### Local Test (Dry Run)
```bash
# Test with sample data
python hybrid_scan.py \
  --csv sample_data.csv \
  --quick-filter \
  --deep-scan \
  --limit 10 \
  --prioritize pageviews
```

**Expected Output:**
```
🔍 TIER 1: Fast Pre-Filter (Pandas)
============================================================
Loading CSV: sample_data.csv
Total rows: 1,000
✅ Shopify stores: 520
✅ Custom domains (not *.myshopify.com): 480
✅ Interesting status codes (not 200/429): 50

🔬 TIER 2: Deep Validation (Your Scanner)
============================================================
Prioritizing by: Estimated Monthly Page Views (top 10)

✅ Exported 10 targets to: deep_scan_targets.txt
```

---

## Validation Checklist

Before pushing to Kaggle, verify:

- [ ] `kaggle_scan.py` uses correct dataset path
- [ ] Default sorting is page views
- [ ] Verification filtering is enabled
- [ ] Error handling for missing columns
- [ ] NaN values handled properly
- [ ] Memory-efficient CSV loading
- [ ] Output paths use `/kaggle/working/`
- [ ] Tools are in `~/go/bin/`
- [ ] All dependencies uploaded
- [ ] Configuration files included

---

## Quick Start Command

**For Kaggle, run this single command:**
```python
!python kaggle_scan.py
```

That's it! The script will:
1. Load your dataset
2. Filter for Shopify targets
3. Sort by page views
4. Export top 100
5. Ready for deep scan

---

## Summary

✅ **Dataset path:** `/kaggle/input/all-leads-merged/results.csv`
✅ **Default sorting:** `Est Monthly Page Views` (highest first)
✅ **Verification filtering:** Enabled
✅ **Error handling:** Comprehensive
✅ **Performance:** Optimized for large CSV
✅ **Timeline:** 15-25 minutes total
✅ **Kaggle timeout:** Well within 12-hour limit

**Ready to deploy!** 🚀
