# Google Maps Scraper Test Report
**Date:** February 5, 2026  
**Test Query:** "gyms in New York"  
**Mode:** TRIAL (limited to 3 results)  
**Status:** ✅ SUCCESSFUL

---

## Test Configuration

- **TESTING:** `False` (real scraping enabled)
- **TRIAL:** `True` (limited to 3 results)
- **HEADLESS_MODE:** `False` (browser visible)
- **Test Script:** `test_scraper.py`
- **Log File:** `logs/app_2026-02-05_20-48-30.log`
- **Output File:** `output/gyms_in_New_York.xlsx`

---

## Test Results Summary

### ✅ Successful Components

1. **ChromeDriver Initialization**
   - ChromeDriver 144.0.7559.133 installed and cached successfully
   - Driver initialized without errors
   - Browser launched in non-headless mode

2. **Google Maps Navigation**
   - Successfully navigated to Google Maps
   - Search box found using alternative selector (`name: q`)
   - Search query entered and submitted successfully

3. **Result Scrolling & Collection**
   - Scrollable feed located
   - Collected 12 results total
   - Correctly limited to 3 results (TRIAL mode working)
   - Scroll logic working as expected

4. **Business Data Extraction**
   - Successfully scraped 3 businesses:
     1. Studio 16 Personal Training
     2. The Fort NYC
     3. GYM NYC
   - All core fields extracted (Name, Address, Phone, Website, Rating)

5. **Website Scraping**
   - All 3 businesses had websites
   - Successfully attempted to scrape social media from all websites
   - Extracted Instagram link from The Fort NYC
   - No errors during website scraping

6. **Data Processing**
   - Data normalization pipeline executed successfully
   - Deduplication logic ran (no duplicates found)
   - Excel file saved successfully

---

## Data Completeness Analysis

| Field | Completeness | Notes |
|-------|-------------|-------|
| **Name** | 3/3 (100%) | ✅ All extracted |
| **Google Maps Link** | 3/3 (100%) | ✅ Full URLs captured |
| **Address** | 3/3 (100%) | ✅ Complete addresses |
| **Phone** | 3/3 (100%) | ✅ All extracted |
| **WhatsApp** | 3/3 (100%) | ✅ Generated from phone numbers |
| **Website** | 3/3 (100%) | ✅ All extracted |
| **Rating** | 3/3 (100%) | ✅ All extracted (5.0, 5.0, 4.5) |
| **Review Count** | 0/3 (0%) | ❌ All showing NaN |
| **Facebook** | 0/3 (0%) | ⚠️ None extracted |
| **Instagram** | 1/3 (33%) | ⚠️ Only 1 extracted (The Fort NYC) |
| **Twitter** | 0/3 (0%) | ⚠️ None extracted |
| **LinkedIn** | 0/3 (0%) | ⚠️ None extracted |
| **YouTube** | 1/3 (33%) | ⚠️ 1 extracted (The Fort NYC) |
| **Pinterest** | 0/3 (0%) | ⚠️ None extracted |
| **TikTok** | 0/3 (0%) | ⚠️ None extracted |
| **Threads** | 0/3 (0%) | ⚠️ None extracted |
| **Snapchat** | 0/3 (0%) | ⚠️ None extracted |
| **Emails** | 0/3 (0%) | ❌ None extracted |
| **Scraped Time** | 3/3 (100%) | ✅ All timestamped |

---

## Issues Identified

### 🐛 Critical Issues

1. **Review Count Extraction Failing** (Priority: P1)
   - All 3 businesses show `NaN` for review count
   - XPath selector may be outdated or incorrect
   - Location: `scraper/scrape.py:119-127`

2. **Email Extraction Not Working** (Priority: P1)
   - No emails extracted from any of the 3 websites
   - All websites were successfully scraped (HTTP 200)
   - Regex pattern may need review or sites have obfuscated emails
   - Location: `scraper/scrape.py:75-76`

### ⚠️ Medium Priority Issues

3. **Social Media Extraction Low Success Rate** (Priority: P2)
   - Only 2/27 social media fields populated (7.4%)
   - Instagram: 1/3 (33%)
   - YouTube: 1/3 (33%)
   - All others: 0/3 (0%)
   - Regex patterns may need updating for modern social media URLs
   - Location: `scraper/scrape.py:52-62`

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Total Execution Time** | ~66 seconds |
| **ChromeDriver Init Time** | ~4 seconds |
| **Page Load Time** | ~7 seconds |
| **Search & Scroll Time** | ~18 seconds |
| **Scraping Time (3 businesses)** | ~26 seconds |
| **Average Time Per Business** | ~8.7 seconds |
| **Data Processing Time** | <1 second |

---

## Code Changes Made During Testing

### 1. Configuration Updates
- **File:** `input/config.py`
- **Changes:**
  - Set `TESTING = False` (enable real scraping)
  - Kept `TRIAL = True` (limit to 3 results)
  - Added clarifying comments

### 2. Search Box Selector Improvements
- **File:** `scraper/search.py`
- **Changes:**
  - Added cookie consent dialog handling
  - Implemented fallback selectors for search box:
    - `By.ID: searchboxinput`
    - `By.NAME: q` ✅ (this worked)
    - `By.CSS_SELECTOR: input[aria-label*="Search"]`
    - `By.CSS_SELECTOR: input[placeholder*="Search"]`
    - `By.XPATH: //input[@id="searchboxinput"]`
  - Added detailed debug logging
  - Added current URL and page title logging on failure

### 3. Logger Namespace Fixes
- **Files:** `scraper/search.py`, `scraper/driver.py`
- **Changes:**
  - Changed from `logging.getLogger(__name__)` to `logging.getLogger("leads_gen")`
  - Ensures all logs go to the same file

---

## Recommendations

### Immediate Actions (P1)
1. **Fix Review Count Extraction**
   - Investigate current Google Maps HTML structure
   - Update XPath selector in `scraper/scrape.py`
   - Add fallback selectors

2. **Fix Email Extraction**
   - Verify regex pattern works with test HTML
   - Check if emails are in contact forms or require JavaScript
   - Consider using BeautifulSoup for better HTML parsing

### Short-Term Improvements (P2)
3. **Enhance Social Media Extraction**
   - Update regex patterns for modern social media URLs
   - Add patterns for short URLs (bit.ly, shortened Instagram/Facebook links)
   - Test against known social media pages

4. **Add Retry Logic for Website Scraping**
   - Some sites may timeout or return errors
   - Current retry logic may need tuning

### Long-Term Enhancements (P3)
5. **Add Screenshot Capability**
   - Save screenshots when elements aren't found
   - Helps debugging selector issues

6. **Implement Rate Limiting**
   - Add configurable delays between requests
   - Respect robots.txt and site policies

---

## Test Data Sample

### Business 1: Studio 16 Personal Training
```
Name: Studio 16 Personal Training
Address: 630 9th Ave #411, New York, NY 10036, United States
Phone: 19732107262
Website: https://studio16nyc.com/free-consultation-call
Rating: 5.0
Review Count: NaN ❌
Social Media: None extracted
Emails: None extracted
```

### Business 2: The Fort NYC
```
Name: The Fort NYC
Address: 57 W 21st St, New York, NY 10010, United States
Phone: 19175813309
Website: https://thefortnyc.com/
Rating: 5.0
Review Count: NaN ❌
Social Media: Instagram ✅, YouTube ✅
Emails: None extracted
```

### Business 3: GYM NYC
```
Name: GYM NYC
Address: 227 Mulberry St, New York, NY 10012, United States
Phone: 16466784723
Website: http://thegym.nyc/
Rating: 4.5
Review Count: NaN ❌
Social Media: None extracted
Emails: None extracted
```

---

## Conclusion

The Google Maps scraping engine is **functional and operational** for core business data extraction. The TRIAL mode works correctly, limiting results to 3 as expected. However, **two critical issues** need immediate attention:

1. Review Count extraction is completely broken
2. Email extraction is not working

Social media extraction has low success rates but is partially working. These issues should be prioritized for fixing to ensure comprehensive lead data collection.

**Overall Status:** ✅ **PASS** (with issues to fix)

---

## Next Steps

1. Create bug tickets for Review Count and Email extraction
2. Fix the identified issues
3. Run another test with the same query to validate fixes
4. Run tests with different queries (restaurants, plumbers, etc.)
5. Test with higher result counts (10, 20, 50)
6. Validate data normalization and deduplication with larger datasets
