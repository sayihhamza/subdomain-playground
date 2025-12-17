# Independent Range Control - Preview & Scan

## ✅ What Changed

You now have **independent control** over the row ranges for:
- **Cell 7 (Preview)** - Shows filtered dataset for manual review
- **Cell 8 (Scan)** - Runs the actual deep scan

---

## 📋 Configuration Variables

### Cell 6: Base Filter & Sort
```python
START_ROW = 1      # Not used anymore (kept for compatibility)
END_ROW = 100      # Not used anymore (kept for compatibility)
SORT_BY = 'Est Monthly Page Views'  # Sorting column
```

**Purpose:** Loads and filters the full dataset, creates `df_base_filtered`

---

### Cell 7: Preview Configuration
```python
PREVIEW_START_ROW = 1       # First row to PREVIEW (1-indexed)
PREVIEW_END_ROW = 100       # Last row to PREVIEW
```

**Purpose:** Controls what rows are **displayed** for manual review

**Example Usage:**
```python
# Preview first 100 rows
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 100

# Preview rows 101-200 (second batch)
PREVIEW_START_ROW = 101
PREVIEW_END_ROW = 200

# Preview rows 1-1000 (large preview)
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 1000
```

---

### Cell 8: Scan Configuration
```python
SCAN_START_ROW = 1       # First row to SCAN (1-indexed)
SCAN_END_ROW = 100       # Last row to SCAN
```

**Purpose:** Controls what rows are **scanned** by the deep scanner

**Example Usage:**
```python
# Scan first 100 rows
SCAN_START_ROW = 1
SCAN_END_ROW = 100

# Scan rows 101-200 (second batch)
SCAN_START_ROW = 101
SCAN_END_ROW = 200

# Scan rows 1-10000 (large scan - 7-9 hours)
SCAN_START_ROW = 1
SCAN_END_ROW = 10000
```

---

## 🎯 Use Cases

### Use Case 1: Preview More, Scan Less
**Scenario:** You want to see the top 1000 targets but only scan top 100

```python
# Cell 7: Preview
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 1000      # See 1000 rows

# Cell 8: Scan
SCAN_START_ROW = 1
SCAN_END_ROW = 100          # Only scan top 100
```

**Why:** Quickly check data quality for 1000 rows, but run fast scan on top 100

---

### Use Case 2: Preview Sample, Scan All
**Scenario:** Quick preview of top 50, but scan top 500

```python
# Cell 7: Preview
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 50        # Quick preview

# Cell 8: Scan
SCAN_START_ROW = 1
SCAN_END_ROW = 500          # Comprehensive scan
```

**Why:** Don't need to see all 500 rows, but want to scan them all

---

### Use Case 3: Different Ranges Entirely
**Scenario:** Preview middle range, scan top range

```python
# Cell 7: Preview
PREVIEW_START_ROW = 101
PREVIEW_END_ROW = 200       # Check rows 101-200

# Cell 8: Scan
SCAN_START_ROW = 1
SCAN_END_ROW = 100          # Scan top 100
```

**Why:** Already reviewed top 100, want to preview next batch before deciding

---

### Use Case 4: Batch Processing
**Scenario:** Process dataset in batches of 100

**Batch 1:**
```python
# Cell 7 & 8
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 100
SCAN_START_ROW = 1
SCAN_END_ROW = 100
```

**Batch 2:**
```python
# Cell 7 & 8
PREVIEW_START_ROW = 101
PREVIEW_END_ROW = 200
SCAN_START_ROW = 101
SCAN_END_ROW = 200
```

**Batch 3:**
```python
# Cell 7 & 8
PREVIEW_START_ROW = 201
PREVIEW_END_ROW = 300
SCAN_START_ROW = 201
SCAN_END_ROW = 300
```

**Why:** Process large dataset in manageable chunks within Kaggle's 12-hour limit

---

## 📊 Example Workflow

### Workflow 1: Conservative Approach
```
1. Cell 6: Load & filter full dataset
   ↓
2. Cell 7: Preview top 1000 (PREVIEW_END_ROW = 1000)
   ↓ (manually review)
3. Cell 8: Scan only top 100 (SCAN_END_ROW = 100)
   ↓ (15-20 min)
4. Cell 9: Review results
   ↓
5. If good results, increase SCAN_END_ROW to 500 and re-run Cell 8
```

### Workflow 2: Aggressive Approach
```
1. Cell 6: Load & filter full dataset
   ↓
2. Cell 7: Preview top 100 (PREVIEW_END_ROW = 100)
   ↓ (quick check)
3. Cell 8: Scan top 10000 (SCAN_END_ROW = 10000)
   ↓ (7-9 hours - let it run)
4. Cell 9: Review all results
```

### Workflow 3: Batch Processing
```
Run 1:
  Cell 7: Preview 1-100
  Cell 8: Scan 1-100 → Export results

Run 2:
  Cell 7: Preview 101-200
  Cell 8: Scan 101-200 → Export results

Run 3:
  Cell 7: Preview 201-300
  Cell 8: Scan 201-300 → Export results

Combine all results after
```

---

## 🔧 Configuration Examples

### Example 1: Quick Test
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 10        # See top 10

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 10           # Scan top 10 (fast test)
```
**Time:** ~1 minute

---

### Example 2: Standard Run
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 100       # See top 100

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 100          # Scan top 100
```
**Time:** ~15-20 minutes

---

### Example 3: Large Run
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 500       # See top 500

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 1000         # Scan top 1000
```
**Time:** ~2-3 hours

---

### Example 4: Maximum Coverage
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 1000      # See top 1000

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 10000        # Scan top 10000
```
**Time:** ~7-9 hours (near Kaggle limit)

---

## ⚠️ Important Notes

### 1. Row Numbers are 1-indexed
```python
PREVIEW_START_ROW = 1   # First row (not 0)
PREVIEW_END_ROW = 100   # Row 100 (not 99)
```

### 2. Ranges are Inclusive
```python
SCAN_START_ROW = 1
SCAN_END_ROW = 100
# Scans rows 1, 2, 3, ..., 99, 100 (100 rows total)
```

### 3. Root Domains Filtered Automatically
Both Cell 7 and Cell 8 automatically filter out root domains and keep only subdomains

```python
# Before filtering
example.com          ← Root domain (2 parts) ✗
shop.example.com     ← Subdomain (3 parts) ✓

# After filtering (automatic)
shop.example.com     ← Kept
```

### 4. Ranges are Independent
Changing `PREVIEW_START_ROW` doesn't affect `SCAN_START_ROW`

```python
# This is valid
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 1000

SCAN_START_ROW = 1
SCAN_END_ROW = 100
# Preview shows 1000, scan only processes 100
```

---

## 📈 Performance Guide

| Scan Range | Estimated Time | Use Case |
|------------|----------------|----------|
| 1-10 | 1 minute | Quick test |
| 1-50 | 5-10 minutes | Validation |
| 1-100 | 15-20 minutes | Standard scan |
| 1-500 | 1-2 hours | Medium coverage |
| 1-1000 | 2-3 hours | High coverage |
| 1-5000 | 4-5 hours | Very high coverage |
| 1-10000 | 7-9 hours | Maximum coverage |

**Kaggle Limit:** 12 hours total runtime

---

## 🎮 Quick Commands

### Preview First 100, Scan First 100
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 100

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 100
```

### Preview First 1000, Scan First 100
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 1000

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 100
```

### Preview All Available, Scan Top 500
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 99999  # Will cap at max available

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 500
```

### Second Batch (101-200)
```python
# Cell 7
PREVIEW_START_ROW = 101
PREVIEW_END_ROW = 200

# Cell 8
SCAN_START_ROW = 101
SCAN_END_ROW = 200
```

---

## ✅ Summary

**Before:** One range controlled both preview and scan
```python
START_ROW = 1
END_ROW = 100
# Both Cell 7 and Cell 8 used same range
```

**After:** Independent control for each
```python
# Cell 7
PREVIEW_START_ROW = 1
PREVIEW_END_ROW = 1000    # See 1000

# Cell 8
SCAN_START_ROW = 1
SCAN_END_ROW = 100        # Scan 100

# Total flexibility!
```

**Benefits:**
- ✅ Preview more data without scanning it all
- ✅ Batch processing with different ranges
- ✅ Validate data quality before long scan
- ✅ More control over Kaggle runtime
