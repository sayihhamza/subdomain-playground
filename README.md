# Shopify Subdomain Takeover Scanner

Automated scanner for detecting Shopify subdomain takeover vulnerabilities.

## Quick Start (Kaggle)

### Option 1: Upload Notebook (Recommended)
1. Download `KAGGLE_NOTEBOOK.ipynb`
2. Upload to Kaggle: File → Upload Notebook
3. Run all cells (takes 5-6 hours for ~10k domains)

### Option 2: Clone from GitHub
```bash
# In Kaggle notebook
!git clone https://github.com/sayihhamza/subdomain-playground.git
cd subdomain-playground
```
Then copy cells from `KAGGLE_NOTEBOOK.ipynb`

## What It Does

Scans domains to find:
- Domains with CNAME pointing to `*.myshopify.com`
- HTTP status 403/404 (indicates potential takeover)
- Potential subdomain takeover vulnerabilities

## Notebook Structure

1. **Setup** (Cells 1-4): Install Go, build tools, configure environment
2. **Data Prep** (Cell 5): Extract domains from CSV
3. **Test** (Cell 6): Quick test with 5 domains
4. **Full Scan** (Cell 7): Scan all domains (5-6 hours)
5. **Results** (Cells 8-11): View, export, download results

## Output Files

- `shopify_results.csv` - All findings
- `shopify_high_risk.csv` - Critical/high risk only
- `data/scans/shopify_takeover_candidates.json` - Full JSON results

## Requirements

Automatically installed by notebook:
- Go 1.22+
- httpx, dnsx, subzy (compiled from source)
- Python 3.8+

## Data

Domain lists should be in `data/domain_sources/myleadfox/*.csv`

The notebook will automatically extract domains from CSV files.

## Local Testing

```bash
python scan.py -l data/all_sources.txt --shopify-takeover-only --workers 4 --mode quick
```

## Legal

⚠️ Only scan domains you own or have authorization to test. Unauthorized testing is illegal.

## Features

- Real-time progress display
- Multi-threaded scanning (4 workers)
- CNAME chain tracking
- HTTP status validation
- Risk classification (low/medium/high/critical)
- Confidence scoring (0-100)

## Timeline

- Setup: 3-5 minutes
- Testing: 30 seconds
- Full scan: 5-6 hours for ~10k domains
- Results export: 1 minute

## Support

See `START_HERE.txt` for detailed instructions.
