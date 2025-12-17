# Fast Scan Issue - Root Domains vs Subdomains

## 🔍 Why Your Scan Finished Faster Than Expected

### Issue Discovered

**Your scan finished fast because 90% of your input contains ROOT DOMAINS, not SUBDOMAINS.**

---

## 📊 Current Situation

### Input File Analysis
```
File: data/all_sources.txt
Total domains: 9,900

Breakdown:
  - Subdomains (3+ parts): 1,023 (10%) ✓
  - Root domains (2 parts): 8,877 (90%) ✗

Examples of what's in the file:
  ✗ 101.art                    (root domain)
  ✗ 10buying.com               (root domain)
  ✗ 1commerce.store            (root domain)
  ✓ 0b9abc-3.myshopify.com     (subdomain)
  ✓ shop.example.com           (subdomain - if any)
```

---

## 🎯 Why Root Domains Get Filtered Out

### Your Scan Configuration
```bash
--mode full
--require-cname-contains 'shopify'
--filter-status '3*,4*,5*'
```

### What Happens to Root Domains

**Root Domain Example:** `101.art`

```
Step 1: DNS Lookup
  101.art → A record: 192.0.2.1 (direct IP)

Step 2: CNAME Check
  --require-cname-contains 'shopify'
  Result: NO CNAME RECORD

Step 3: Filter Decision
  Action: ✗ FILTERED OUT (no Shopify CNAME)
```

**Subdomain Example:** `shop.example.com`

```
Step 1: DNS Lookup
  shop.example.com → CNAME: shops.myshopify.com

Step 2: CNAME Check
  --require-cname-contains 'shopify'
  Result: ✓ CONTAINS 'shopify'

Step 3: Filter Decision
  Action: ✓ CONTINUE SCANNING
```

---

## 📉 Performance Impact

### Expected (if all subdomains)
```
Input: 9,900 subdomains
After CNAME filter: ~500-1,000 with Shopify CNAME
Scan time: 7-9 hours
```

### Actual (90% root domains)
```
Input: 9,900 domains (8,877 root + 1,023 subdomains)
After CNAME filter: ~100-200 with Shopify CNAME
Scan time: 1-2 hours ✓ (explains fast completion)
```

---

## 🔎 Root Cause: Dataset Column Issue

### Your Dataset Structure

Your CSV likely has these columns:
```
Website, Subdomain, Is_Shopify, CNAME_Record, HTTP_Status
```

### Problem

The `Subdomain` column in your dataset contains:
- **Root domains** (e.g., `example.com`, `shop.com`)
- NOT actual subdomains (e.g., `store.example.com`, `wholesale.shop.com`)

### Why This Happens

Most Shopify datasets use "Subdomain" to mean:
```
Subdomain column = The main website domain
  ✗ example.com
  ✗ mystore.com
  ✗ brandshop.com
```

Not the technical definition of subdomain:
```
Subdomain = Hostname with 3+ parts
  ✓ shop.example.com
  ✓ store.mystore.com
  ✓ checkout.brandshop.com
```

---

## 💡 Solutions

### Option 1: Use Root Domains (Current Behavior)

**When to use:**
- You want to scan the main Shopify stores
- Looking for abandoned stores (root domains)
- Quick reconnaissance

**Pros:**
- Fast (1-2 hours for 10k domains)
- Finds abandoned Shopify stores

**Cons:**
- Most root domains won't have Shopify CNAMEs
- Lower takeover probability
- Misses custom subdomains

### Option 2: Filter for Actual Subdomains Only

**Update Cell 6/7 to filter:**
```python
# After loading df_selected, filter for subdomains only
def is_subdomain(domain):
    return len(domain.split('.')) > 2

df_subdomains = df_selected[df_selected['Subdomain'].apply(is_subdomain)].copy()

# Save subdomain-only list
df_subdomains['Subdomain'].to_csv(targets_file, index=False, header=False)
```

**Pros:**
- Only scans actual subdomains
- Higher takeover probability
- Matches automatic subdomain detection

**Cons:**
- Smaller dataset (~10% of rows)
- May need to adjust START_ROW/END_ROW

### Option 3: Remove CNAME Filter (Scan All)

**Update scan command:**
```python
# Remove --require-cname-contains
process = subprocess.Popen([
    sys.executable, '-u', 'scan.py',
    '-l', 'data/all_sources.txt',
    '--mode', 'full',
    # '--require-cname-contains', 'shopify',  # ← Remove this
    '--filter-status', '3*,4*,5*',
    '--workers', '2'
])
```

**Pros:**
- Scans all domains (root + subdomains)
- Finds non-Shopify takeovers too

**Cons:**
- Much slower (7-9 hours for 10k)
- More false positives
- Not Shopify-focused

---

## 🎯 Recommended Solution

### For Shopify Takeover Detection:

**Use Option 2: Filter for Actual Subdomains**

This is what Cell 7 in the notebook already does:
```python
# Cell 7: Preview Full Dataset
def is_subdomain(domain):
    return len(domain.split('.')) > 2

subdomain_mask = df_selected['Subdomain'].apply(is_subdomain)
df_subdomains_only = df_selected[subdomain_mask].copy()
```

**Then in Cell 8, scan these filtered subdomains.**

---

## 📊 Expected Results After Fix

### Before Fix
```
Input: 9,900 domains
  - Root: 8,877 (filtered by CNAME check)
  - Subdomains: 1,023
After CNAME filter: ~200 domains
Scan time: 1-2 hours
```

### After Fix (Option 2)
```
Input: 1,023 subdomains (root domains excluded)
After CNAME filter: ~200-300 domains
Scan time: 2-3 hours (longer, but correct)
```

---

## 🔧 Quick Check

Run this to verify your dataset:
```python
import pandas as pd

df = pd.read_csv('/path/to/results.csv')

# Check what's in Subdomain column
print("Sample Subdomain values:")
print(df['Subdomain'].head(20))

# Count root vs subdomains
df['is_subdomain'] = df['Subdomain'].apply(lambda x: len(str(x).split('.')) > 2)
print(f"\nRoot domains: {(~df['is_subdomain']).sum()}")
print(f"Subdomains: {df['is_subdomain'].sum()}")
```

---

## ✅ Summary

**Why scan was fast:**
1. 90% of input file contains root domains
2. Root domains don't have Shopify CNAMEs
3. `--require-cname-contains shopify` filters them out immediately
4. Only ~1,000 subdomains actually scanned

**Solution:**
- Use Cell 7's subdomain filtering (already implemented)
- This ensures only actual subdomains are scanned
- Expected scan time: 2-3 hours for 1,000 subdomains

**Your notebook already has this fix in Cell 7!** ✓
