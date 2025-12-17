# Cloudflare Verification Detection Guide

## Overview

The scanner now intelligently detects subdomains that show "Needs setup" or verification pages requiring **Cloudflare DNS management access**. These cannot be taken over without:

1. Access to the domain's Cloudflare account
2. Permission to add/modify DNS records (TXT, CNAME, A)
3. The specific verification token/value

**Example:** `club.gruntstyle.com` shows:
```
"Hey My Store, need help with your domain?"
"Checking DNS records"
"Log in to Cloudflare and open DNS management"
"Add these new DNS records"
Type: TXT, Name: shopify_verification_club, Value: UR4E7G77
```

This is **NOT a takeover opportunity** - it's a verification requirement.

---

## How Detection Works

### 1. **CNAME Blacklist Filter** (Phase 3.5)

Filters subdomains/CNAMEs containing verification patterns:

```yaml
# config/cname_blacklist.yaml
cloudflare_verification:
  - "shopify_verification_"  # TXT record verification
  - "_acme-challenge"        # SSL certificate validation
  - "_dnsauth"               # DNS authentication
  - "verify.cloudflare.com"  # Cloudflare verification endpoint
  - "ssl-validation"
  - "domain-verification"
```

**Example:**
```
shop.example.com → shopify_verification_shop ❌ FILTERED
store.example.com → shops.myshopify.com ✅ KEPT (potentially vulnerable)
```

### 2. **HTTP Body Pattern Detection** (Phase 5)

Analyzes the HTTP response body for verification page indicators:

```python
# src/parsers/httpx_parser.py
verification_patterns = [
    "checking dns records",
    "add these new dns records",
    "shopify_verification_",
    "needs setup",
    "domain verification",
    "verify your domain",
    "txt record",
    "dns management",
    "cloudflare dns",
    "update dns",
    "log in to cloudflare",
    "add dns record",
    "domain setup",
]
```

**Result:** Marked as `FALSE POSITIVE - Verification page (requires DNS/Cloudflare access)`

---

## Detection Examples

### Example 1: Shopify Verification via Cloudflare

**Subdomain:** `club.gruntstyle.com`

**HTTP Response:**
```html
<h1>Hey My Store, need help with your domain?</h1>
<p>Checking DNS records</p>
<ol>
  <li>Log in to Cloudflare and open DNS management for club.gruntstyle.com</li>
  <li>Add these new DNS records</li>
</ol>
<table>
  <tr>
    <td>Type</td><td>Name</td><td>Value</td>
  </tr>
  <tr>
    <td>TXT</td><td>shopify_verification_club</td><td>UR4E7G77</td>
  </tr>
</table>
```

**Scanner Detection:**
1. ✅ HTTP 200 status (page loads)
2. ✅ Body contains "checking dns records"
3. ✅ Body contains "log in to cloudflare"
4. ✅ Body contains "shopify_verification_"
5. **Result:** `FALSE POSITIVE - Verification page (requires DNS/Cloudflare access)`

**Evidence Column:** `❌ FALSE POSITIVE`
**Message Column:** `Hey My Store, need help with your domain? Checking DNS records...`

---

### Example 2: SSL Certificate Validation

**Subdomain:** `_acme-challenge.example.com`

**CNAME:** `_acme-challenge.example.com.verify.cloudflare.com`

**Scanner Detection:**
1. ✅ CNAME contains `_acme-challenge`
2. ✅ CNAME contains `verify.cloudflare.com`
3. **Result:** Filtered by CNAME blacklist
4. **Phase:** Never reaches HTTP validation (filtered in Phase 3.5)

**Log Output:**
```
[PHASE 3.5] CNAME Blacklist Filtering
Filtered 1 subdomains with blacklisted CNAMEs
Blacklisted CNAME: _acme-challenge.example.com → verify.cloudflare.com
```

---

### Example 3: Genuinely Vulnerable Subdomain

**Subdomain:** `shop.example.com`

**CNAME:** `shops.myshopify.com`

**HTTP Response:**
```html
<h1>Only one step left before your store is ready!</h1>
<p>This shop is currently unavailable.</p>
```

**Scanner Detection:**
1. ✅ CNAME points to `shops.myshopify.com` (NOT blacklisted)
2. ✅ Body contains "only one step left"
3. ✅ Body contains "this shop is currently unavailable"
4. **Result:** `DEFINITE TAKEOVER - Shopify unclaimed store page`

**Evidence Column:** `🔴 DEFINITE TAKEOVER`
**Message Column:** `Only one step left before your store is ready!`

---

## Comparison: Verification vs. Takeover

| Indicator | Verification Page | Takeover Page |
|-----------|------------------|---------------|
| **Title** | "Need help with your domain?" | "Only one step left!" |
| **Message** | "Checking DNS records" | "This shop is currently unavailable" |
| **Action Required** | "Log in to Cloudflare" | "Claim this shop" |
| **DNS Record** | TXT record needed | No DNS change needed |
| **CNAME** | Often `shopify_verification_*` | `shops.myshopify.com` |
| **Takeover Risk** | ❌ FALSE POSITIVE | ✅ VULNERABLE |

---

## Configuration

### Add Custom Verification Patterns

Edit `config/cname_blacklist.yaml`:

```yaml
cloudflare_verification:
  - "verify.cloudflare.com"
  - "shopify_verification_"
  - "_acme-challenge"
  - "_dnsauth"
  - "ssl-validation"
  - "domain-verification"
  # Add your custom patterns:
  - "my-custom-verification"
  - "internal-dns-auth"
```

### Add Custom HTTP Body Patterns

Edit `src/parsers/httpx_parser.py`:

```python
verification_patterns = [
    "checking dns records",
    "add these new dns records",
    # Add your custom patterns:
    "custom verification message",
    "requires dns configuration",
]
```

---

## Testing

### Test 1: Blacklist Detection

```python
from src.validation.cname_blacklist import CNAMEBlacklist

bl = CNAMEBlacklist()

# Test Cloudflare verification patterns
print(bl.is_blacklisted("shopify_verification_club"))  # True
print(bl.is_blacklisted("_acme-challenge.example.com"))  # True
print(bl.is_blacklisted("verify.cloudflare.com"))  # True
print(bl.is_blacklisted("shops.myshopify.com"))  # False (vulnerable!)
```

### Test 2: HTTP Pattern Detection

```python
from src.parsers.httpx_parser import HTTPXParser

parser = HTTPXParser()

# Test verification page body
body = """
<h1>Hey My Store, need help with your domain?</h1>
<p>Checking DNS records</p>
<p>Log in to Cloudflare and add these new DNS records</p>
"""

evidence = parser._detect_takeover_patterns(body, 200)
print(evidence)
# Output: "FALSE POSITIVE - Verification page (requires DNS/Cloudflare access)"
```

### Test 3: Full Scan

```bash
# Scan a verification subdomain
./run.sh --scan-single club.gruntstyle.com --mode quick

# Expected output:
# [PHASE 5] HTTP Validation
# Evidence: ❌ FALSE POSITIVE - Verification page (requires DNS/Cloudflare access)
# Message: Hey My Store, need help with your domain? Checking DNS records...
```

---

## Output Examples

### Verification Page (False Positive)

```
SUBDOMAIN                     STATUS   PROVIDER   CNAME                   EVIDENCE                MESSAGE
club.gruntstyle.com           200      Shopify    shops.myshopify.com     ❌ FALSE POSITIVE       Hey My Store, need help...
```

### Takeover Page (Vulnerable)

```
SUBDOMAIN                     STATUS   PROVIDER   CNAME                   EVIDENCE                MESSAGE
shop.abandoned.com            404      Shopify    shops.myshopify.com     🔴 DEFINITE TAKEOVER    Only one step left befor...
```

---

## Cloudflare-Specific Indicators

### Common Cloudflare Verification Requirements:

1. **TXT Record Verification**
   - Pattern: `shopify_verification_*`
   - Example: `shopify_verification_club`
   - Required: Add TXT record with specific token

2. **CNAME Verification**
   - Pattern: `_cf-custom-hostname.*`
   - Example: `_cf-custom-hostname.example.com`
   - Required: Add CNAME pointing to Cloudflare

3. **SSL Certificate Validation**
   - Pattern: `_acme-challenge.*`
   - Example: `_acme-challenge.example.com`
   - Required: Add TXT record with ACME challenge

4. **Custom Hostname Verification**
   - Pattern: `verify.cloudflare.com`
   - Required: Cloudflare account access

---

## Integration with CSV Workflow

When scanning from your enriched CSV dataset:

```python
import pandas as pd

# Load CSV
df = pd.read_csv("enriched_shopify_data.csv")

# Filter for potential targets (before scanning)
candidates = df[
    (df['Is_Shopify'] == 'Yes') &
    (df['HTTP_Status'].isin([403, 404])) &
    (df['CNAME_Record'].notna()) &
    # Exclude verification subdomains
    (~df['Subdomain'].str.contains('verification', case=False, na=False)) &
    (~df['Subdomain'].str.contains('verify', case=False, na=False)) &
    (~df['Subdomain'].str.contains('_acme', case=False, na=False))
]

# Export for scanning
candidates['Subdomain'].to_csv('scan_targets.txt', index=False, header=False)
```

```bash
# Scan with automatic verification detection
./run.sh --domain-list scan_targets.txt --mode quick --json

# Scanner will:
# 1. Skip enumeration (subdomains detected) ✅
# 2. Filter blacklisted CNAMEs ✅
# 3. Detect verification pages in HTTP body ✅
# 4. Mark as FALSE POSITIVE ✅
```

---

## Troubleshooting

### Q: Why is my subdomain marked as FALSE POSITIVE?

**Check the HTTP response:**
```bash
curl -L https://subdomain.example.com

# Look for:
# - "checking dns records"
# - "log in to cloudflare"
# - "add these new dns records"
# - "shopify_verification_"
```

If any of these appear, it's a verification page, not a takeover.

### Q: Can I override the false positive detection?

**Yes, edit the patterns:**

1. Remove from `config/cname_blacklist.yaml` (CNAME filter)
2. Remove from `src/parsers/httpx_parser.py` (HTTP body filter)

**Or manually verify:**
- Visit the subdomain
- Check if you can claim it without DNS access
- If not, it's correctly marked as false positive

### Q: How do I distinguish between verification and takeover?

**Verification page indicators:**
- Asks for DNS record changes
- Requires Cloudflare/provider login
- Shows specific TXT record values
- Says "needs setup" or "verify your domain"

**Takeover page indicators:**
- Says "only one step left"
- Says "this shop is currently unavailable"
- Shows Shopify signup/claim button
- NO mention of DNS records

---

## Best Practices

1. **Always check Evidence column** - Distinguishes verification vs. takeover
2. **Review Message column** - Shows actual page content
3. **Verify manually** - For high-value targets, visit the page
4. **Update blacklist regularly** - Add new verification patterns as discovered
5. **Monitor logs** - Check what's being filtered and why

---

## Summary

The scanner now intelligently filters Cloudflare verification requirements:

✅ **Detects** verification pages by HTTP body content
✅ **Filters** verification CNAMEs via blacklist
✅ **Labels** false positives clearly
✅ **Preserves** genuine takeover opportunities

**Result:** Fewer false positives, more accurate vulnerability detection.
