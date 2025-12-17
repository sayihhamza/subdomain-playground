# Kaggle Notebook - Preview Cell Added ✅

## Summary

Added a new **Cell 7** to the Kaggle notebook that displays the complete filtered and sorted dataset **before** the deep scan starts. This allows you to manually review subdomains while the scanner runs.

---

## What Was Added

### New Cell 7: Preview Full Dataset (Manual Review)

**Location:** Between Cell 6 (Load and Filter Dataset) and Cell 8 (Deep Scan Execution)

**Purpose:**
- Display the complete filtered and sorted dataset before scanning
- Allow manual verification of subdomains while scan runs
- Show all entries from START_ROW to END_ROW

**Features:**
1. **Full Dataset Display** - Shows ALL selected rows (not just first 20)
2. **Subdomain Verification** - Filters out root domains, keeps only subdomains
3. **Row Numbers** - 1-based index for easy reference
4. **Sortable View** - Sorted by Est Monthly Page Views (descending)
5. **Key Columns** - Row, Subdomain, HTTP Status, Page Views, CNAME

---

## Cell Structure (Updated)

| Cell | Type | Title | Description |
|------|------|-------|-------------|
| 0 | Markdown | Title | Project overview |
| 1 | Markdown | Cell 1 | Clone project |
| 2 | Code | Cell 1 | Git clone from GitHub |
| 3 | Markdown | Cell 2 | Install dependencies |
| 4 | Code | Cell 2 | pip install requirements |
| 5 | Markdown | Cell 3 | Install Go |
| 6 | Code | Cell 3 | Download and install Go 1.24 |
| 7 | Markdown | Cell 4 | Build security tools |
| 8 | Code | Cell 4 | Build subfinder, findomain, etc. |
| 9 | Markdown | Cell 5 | Set environment |
| 10 | Code | Cell 5 | Set PATH variables |
| 11 | Markdown | Cell 6 | Load and filter dataset |
| 12 | Code | Cell 6 | Load CSV, apply filters, sort |
| **13** | **Markdown** | **Cell 7** | **Preview full dataset** ⭐ NEW |
| **14** | **Code** | **Cell 7** | **Display all filtered subdomains** ⭐ NEW |
| 15 | Markdown | Cell 8 | Deep scan execution |
| 16 | Code | Cell 8 | Run scan.py with full mode |
| 17 | Markdown | Cell 9 | View results |
| 18 | Code | Cell 9 | Display scan results |
| 19 | Markdown | Cell 10 | Export to CSV |
| 20 | Code | Cell 10 | Save results to CSV |

---

## Cell 7 Output Example

```
================================================================================
FULL FILTERED DATASET (Rows 1 to 100)
================================================================================

Total selected: 100 entries
Sorted by: Est Monthly Page Views (descending)

================================================================================
Displaying ALL 98 subdomains:
================================================================================

Row  Subdomain                    HTTP_Status  Est Monthly Page Views  CNAME_Record
  1  shop.example1.com                    403                 450000  shops.myshopify.com
  2  store.example2.com                   404                 380000  shops.myshopify.com
  3  wholesale.example3.com               403                 320000  shops.myshopify.com
  4  b2b.example4.com                     404                 290000  shops.myshopify.com
  5  shop.example5.com                    403                 265000  shops.myshopify.com
  ...
 98  checkout.example98.com               404                  12000  shops.myshopify.com

================================================================================

📋 Dataset Summary:
  • Total subdomains: 98
  • Range: Row 1 to 98
  • Sorted by: Est Monthly Page Views (highest first)
  • All entries verified as subdomains (not root domains)

💡 TIP: You can manually review these subdomains while Cell 8 runs the scan

================================================================================
Next: Run Cell 8 to start deep scan of these 98 subdomains
================================================================================

✓ Updated targets file with verified subdomains: /kaggle/working/subdomain-playground/data/all_sources.txt
```

---

## Key Features

### 1. Subdomain Verification ✅
```python
def is_subdomain(domain):
    """Check if domain is a subdomain (has more than 2 parts)"""
    if pd.isna(domain) or not isinstance(domain, str):
        return False
    parts = domain.split('.')
    return len(parts) > 2  # e.g., shop.example.com has 3 parts
```

**What it does:**
- Automatically filters out root domains (example.com)
- Keeps only subdomains (shop.example.com)
- Shows warning if any root domains were filtered out

### 2. Full Display (No Truncation) ✅
```python
pd.set_option('display.max_rows', None)  # Show ALL rows
```

**What it does:**
- Displays ALL rows in the selected range (1-10000)
- No truncation with "..."
- Complete dataset visibility

### 3. Row Numbers for Reference ✅
```python
display_df.insert(0, 'Row', range(START_ROW, START_ROW + len(display_df)))
```

**What it does:**
- Adds 1-based row numbers
- Easy to reference specific entries
- Matches START_ROW/END_ROW configuration

### 4. Updated Targets File ✅
```python
display_df['Subdomain'].to_csv(targets_file, index=False, header=False)
```

**What it does:**
- Updates all_sources.txt with verified subdomains only
- Removes any root domains from scan input
- Ensures clean input for scanner

---

## Use Cases

### While Scan Runs
1. **Manual Verification** - Check if high-traffic subdomains look legitimate
2. **Pattern Recognition** - Identify common subdomain patterns
3. **CNAME Review** - Verify CNAME records point to Shopify
4. **Status Code Analysis** - Understand HTTP status distribution

### Before Scan Starts
1. **Data Validation** - Confirm filters applied correctly
2. **Range Verification** - Check START_ROW/END_ROW is correct
3. **Subdomain Check** - Verify all entries are subdomains
4. **Sorting Confirmation** - Ensure sorted by desired column

---

## Configuration Options

### Change Range
```python
START_ROW = 1      # First row (1-indexed)
END_ROW = 100      # Last row
```

**Examples:**
- `START_ROW = 1, END_ROW = 100` - Top 100 by page views
- `START_ROW = 1, END_ROW = 1000` - Top 1000
- `START_ROW = 101, END_ROW = 200` - Rows 101-200 (second batch)
- `START_ROW = 1, END_ROW = 10000` - Top 10,000 (max for Kaggle 12-hour limit)

### Change Sorting
```python
SORT_BY = 'Est Monthly Page Views'  # Column to sort by
```

**Alternatives:**
- `'Est. Monthly Sales'` - Sort by revenue
- `'Twitter Followers'` - Sort by social reach
- `'HTTP_Status'` - Sort by status code

---

## Benefits

### 1. Manual Review During Scan ✅
- **Problem:** Scan takes 15-20 minutes for 100 domains, 7-9 hours for 10k
- **Solution:** Preview dataset immediately while scan runs in background
- **Benefit:** Productive use of time, can spot issues early

### 2. Data Quality Assurance ✅
- **Problem:** Can't verify filtered data before expensive scan
- **Solution:** Full dataset preview shows exactly what will be scanned
- **Benefit:** Catch configuration errors before wasting hours

### 3. Subdomain-Only Guarantee ✅
- **Problem:** Dataset may contain root domains (example.com)
- **Solution:** Automatic filtering keeps only subdomains
- **Benefit:** Scanner optimizations work correctly (skip enumeration)

### 4. Complete Visibility ✅
- **Problem:** Cell 6 only showed first 20 entries
- **Solution:** Cell 7 shows ALL entries in range
- **Benefit:** See entire dataset, not just preview

---

## Example Workflow

### Step 1: Configure Range (Cell 6)
```python
START_ROW = 1
END_ROW = 100
SORT_BY = 'Est Monthly Page Views'
```

### Step 2: Load and Filter (Cell 6)
```
✓ Loaded 1,700,000 total rows
✓ Filtered to 464 Shopify stores with interesting status codes
✓ Sorted by Est Monthly Page Views
✓ Selected 100 domains
```

### Step 3: Preview Full Dataset (Cell 7) ⭐ NEW
```
Displaying ALL 98 subdomains:
Row 1: shop.example1.com (403, 450000 views)
Row 2: store.example2.com (404, 380000 views)
...
Row 98: checkout.example98.com (404, 12000 views)
```

### Step 4: Start Scan (Cell 8)
While scan runs, you can:
- Scroll through Cell 7 output
- Check specific subdomains manually in browser
- Verify CNAME records with dig/nslookup
- Look for patterns or anomalies

### Step 5: View Results (Cell 9)
Compare Cell 7 preview with scan results

---

## Technical Details

### Pandas Display Options
```python
pd.set_option('display.max_rows', None)      # Show all rows
pd.set_option('display.max_colwidth', 50)    # Truncate long values
pd.set_option('display.width', 120)          # Terminal width
```

### Subdomain Validation Logic
```python
# Valid subdomains (3+ parts):
shop.example.com       → 3 parts → ✓ subdomain
api.staging.site.com   → 4 parts → ✓ subdomain

# Invalid (2 parts):
example.com            → 2 parts → ✗ root domain
site.com               → 2 parts → ✗ root domain
```

### File Output
```python
targets_file = '/kaggle/working/subdomain-playground/data/all_sources.txt'
display_df['Subdomain'].to_csv(targets_file, index=False, header=False)
```

**Format (one subdomain per line):**
```
shop.example1.com
store.example2.com
wholesale.example3.com
...
```

---

## Testing

### Quick Test (10 domains)
```python
START_ROW = 1
END_ROW = 10
```
**Expected:** Cell 7 shows 10 subdomains, Cell 8 scans in ~2 minutes

### Medium Test (100 domains)
```python
START_ROW = 1
END_ROW = 100
```
**Expected:** Cell 7 shows ~98 subdomains, Cell 8 scans in ~15-20 minutes

### Large Test (1000 domains)
```python
START_ROW = 1
END_ROW = 1000
```
**Expected:** Cell 7 shows ~980 subdomains, Cell 8 scans in ~2-3 hours

---

## Troubleshooting

### Q: Cell 7 shows fewer domains than END_ROW - START_ROW + 1?
**A:** Root domains were filtered out. This is expected and correct behavior.

### Q: Can I disable subdomain-only filtering?
**A:** Not recommended. The scanner's automatic subdomain detection (which saves hours) only works with actual subdomains.

### Q: How do I see more columns?
**A:** Modify `display_columns` list:
```python
display_columns = ['Row', 'Subdomain', 'HTTP_Status', SORT_BY, 'CNAME_Record', 'Website', 'Email']
```

### Q: Output is too wide for my screen?
**A:** Adjust display width:
```python
pd.set_option('display.width', 80)  # Narrower
pd.set_option('display.max_colwidth', 30)  # Shorter columns
```

---

## Comparison: Before vs After

### Before (Cell 6 only)
```
First 20 targets:
  shop.example1.com
  store.example2.com
  ...
  (20 entries shown)

... and 80 more

❓ What are the other 80 subdomains?
❓ Are they all subdomains or some root domains?
❓ Can I review them before scanning?
```

### After (Cell 6 + Cell 7)
```
Cell 6: Summary and first 20
Cell 7: FULL dataset (all 98 subdomains)
  Row 1-98 displayed
  All verified as subdomains
  Complete visibility

✅ Know exactly what will be scanned
✅ Can review while scan runs
✅ Data quality guaranteed
```

---

## Conclusion

The new **Cell 7** provides:

1. ✅ **Complete dataset visibility** - See all entries, not just preview
2. ✅ **Subdomain verification** - Automatic filtering of root domains
3. ✅ **Manual review capability** - Check subdomains while scan runs
4. ✅ **Data quality assurance** - Verify filters before expensive scan
5. ✅ **Row-based reference** - Easy to identify specific entries

**Perfect for:**
- Large scans (1000-10000 domains)
- Manual verification needs
- Data quality checks
- Pattern analysis
- Debugging filter issues

**Ready to use in Kaggle!** 🚀
