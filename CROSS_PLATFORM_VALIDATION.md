# Cross-Platform Validation Checklist

This document provides a checklist for validating the Google Maps Lead Generator on different platforms (Windows, macOS, Linux).

## Platforms to Test

- ✅ macOS (development platform)
- ⚠️ Windows 10/11 (primary deployment target)
- ⚠️ Linux (optional)

## Pre-Validation Setup

### 1. Build the Executable

```bash
# On the target platform
cd /path/to/leads_gen
pyinstaller leads_gen.spec

# Executable will be in dist/ folder
# - macOS: dist/leads_gen (Unix executable)
# - Windows: dist/leads_gen.exe (Windows executable)
# - Linux: dist/leads_gen (Unix executable)
```

### 2. Verify Dependencies

Ensure the following are installed on the target platform:
- Google Chrome browser (for Selenium)
- Write permissions in the executable's directory (for logs/ and output/)

## Validation Test Cases

### Test 1: First Launch

**Steps**:
1. Run the executable for the first time
2. Verify the Streamlit UI launches successfully
3. Check that the following directories are created:
   - `logs/` (for app.log)
   - `leads_gen_output/` (default output directory)

**Expected Results**:
- ✅ Application starts without errors
- ✅ Browser opens to http://localhost:8501
- ✅ Log file `logs/app.log` is created
- ✅ No permission errors

**Platform-Specific Notes**:
- **Windows**: May show Windows Defender/firewall prompt (allow access)
- **macOS**: May show Gatekeeper warning (right-click > Open to bypass)
- **Linux**: Ensure executable has execute permissions (`chmod +x dist/leads_gen`)

---

### Test 2: Google Maps Scraping (New Mode)

**Steps**:
1. In the UI, select "Start fresh (new Excel file)"
2. Enter a search query (e.g., "gyms in New York")
3. Set max results to 3
4. Click "Start Scraping"

**Expected Results**:
- ✅ ChromeDriver launches successfully
- ✅ Google Maps search completes
- ✅ Progress bar updates during scraping
- ✅ Data is saved to `leads_gen_output/gyms_in_New_York.xlsx`
- ✅ Excel file is valid and opens correctly
- ✅ All columns are populated (Name, Address, Phone, Website, etc.)

**Platform-Specific Notes**:
- **Windows**: ChromeDriver may download automatically via `webdriver_manager`
- **macOS**: Same as Windows
- **Linux**: May require `xvfb` for headless mode

---

### Test 3: Append Mode

**Steps**:
1. Select "Append to existing Excel file"
2. Upload the Excel file created in Test 2
3. Enter the same query and set max results to 2
4. Click "Start Scraping"

**Expected Results**:
- ✅ Existing file is loaded correctly
- ✅ New data is appended to existing data
- ✅ Deduplication works (no duplicate businesses)
- ✅ File is saved successfully

---

### Test 4: Path Handling

**Steps**:
1. Check that all file paths work correctly on the platform
2. Verify custom output directory works

**Expected Results**:
- ✅ `logs/app.log` is created relative to executable location
- ✅ `leads_gen_output/` is created relative to executable location
- ✅ Custom output paths work (test with spaces in path names)

**Platform-Specific Notes**:
- **Windows**: Test with paths like `C:\Users\John Doe\Documents\Leads`
- **macOS**: Test with paths like `/Users/john/Documents/Leads`
- **Linux**: Test with paths like `/home/john/Documents/Leads`

---

### Test 5: Logging Verification

**Steps**:
1. Perform a scraping operation
2. Close the application
3. Open `logs/app.log`

**Expected Results**:
- ✅ Log file contains:
  - Application version and start timestamp
  - User inputs (query, max results)
  - Scraping phases (search, scroll, scrape)
  - Number of businesses scraped
  - File save location and row count
- ✅ No duplicate log entries
- ✅ Log file is readable and properly formatted

---

### Test 6: ChromeDriver & Selenium

**Steps**:
1. Run a scraping operation with both headless and non-headless modes (toggle `HEADLESS_MODE` in `input/config.py`)

**Expected Results**:
- ✅ ChromeDriver downloads automatically (if not present)
- ✅ Chrome browser launches correctly
- ✅ Google Maps loads successfully
- ✅ No Selenium exceptions

**Platform-Specific Notes**:
- **Windows**: ChromeDriver may be blocked by antivirus (whitelist if needed)
- **macOS**: May require Gatekeeper approval for ChromeDriver
- **Linux**: May require `chromium-browser` or `google-chrome` package

---

### Test 7: Restart & Persistence

**Steps**:
1. Run the application and scrape data
2. Close the application completely
3. Relaunch the application
4. Verify logs and output are still accessible

**Expected Results**:
- ✅ Previous logs are preserved (new logs appended)
- ✅ Previous output files are accessible
- ✅ No data loss

---

### Test 8: Error Handling

**Steps**:
1. Test with invalid queries (empty string, special characters)
2. Test with no internet connection
3. Test with ChromeDriver unavailable

**Expected Results**:
- ✅ Graceful error messages displayed to user
- ✅ Errors logged to `logs/app.log`
- ✅ Application does not crash

---

### Test 9: Open Output Folder

**Steps**:
1. After scraping, click "📂 Open Output Folder"

**Expected Results**:
- ✅ File explorer/Finder opens to the output folder

**Platform-Specific Notes**:
- **Windows**: Opens File Explorer
- **macOS**: Opens Finder
- **Linux**: Opens file manager (xdg-open)

---

### Test 10: Demo Mode (TESTING=True)

**Steps**:
1. In `input/config.py`, set `TESTING = True`
2. Run the application
3. Perform a scraping operation

**Expected Results**:
- ✅ Demo data is used instead of live scraping
- ✅ No ChromeDriver is launched
- ✅ Excel file is created with demo data

---

## Known Platform-Specific Issues

### Windows
- **Issue**: Windows Defender may flag the executable as suspicious
  - **Solution**: Whitelist the executable or sign the .exe with a code signing certificate
- **Issue**: ChromeDriver may be blocked by antivirus
  - **Solution**: Whitelist ChromeDriver in antivirus settings

### macOS
- **Issue**: Gatekeeper may block the application
  - **Solution**: Right-click > Open to bypass Gatekeeper, or sign the app with Apple Developer certificate
- **Issue**: ChromeDriver may require approval
  - **Solution**: Approve in System Preferences > Security & Privacy

### Linux
- **Issue**: ChromeDriver may not work without display
  - **Solution**: Use `xvfb` for headless mode: `xvfb-run ./dist/leads_gen`

## Code Features for Cross-Platform Compatibility

The application has been designed with cross-platform compatibility in mind:

1. **Path Handling**:
   - Uses `pathlib.Path` for all file paths
   - `utils/paths.py` provides platform-agnostic path resolution
   - Detects frozen mode (`sys.frozen`) for PyInstaller builds

2. **Folder Opening**:
   - `app.py` has platform-specific logic for opening folders:
     - macOS: `open`
     - Windows: `os.startfile()`
     - Linux: `xdg-open`

3. **ChromeDriver**:
   - Uses `webdriver_manager` for automatic ChromeDriver download
   - No hard-coded paths or assumptions about ChromeDriver location

4. **Logging**:
   - Uses `logging.handlers.RotatingFileHandler` for log rotation
   - Logs are written relative to executable location
   - UTF-8 encoding for cross-platform compatibility

5. **Excel Files**:
   - Uses `pandas` and `openpyxl` for Excel I/O (cross-platform libraries)
   - No platform-specific Excel APIs

## Validation Sign-Off

Complete this checklist after validation on each platform:

### Windows
- [ ] Test 1: First Launch
- [ ] Test 2: Google Maps Scraping (New Mode)
- [ ] Test 3: Append Mode
- [ ] Test 4: Path Handling
- [ ] Test 5: Logging Verification
- [ ] Test 6: ChromeDriver & Selenium
- [ ] Test 7: Restart & Persistence
- [ ] Test 8: Error Handling
- [ ] Test 9: Open Output Folder
- [ ] Test 10: Demo Mode

### macOS
- [x] Test 1: First Launch (assumed working, development platform)
- [ ] Test 2: Google Maps Scraping (New Mode)
- [ ] Test 3: Append Mode
- [ ] Test 4: Path Handling
- [ ] Test 5: Logging Verification
- [ ] Test 6: ChromeDriver & Selenium
- [ ] Test 7: Restart & Persistence
- [ ] Test 8: Error Handling
- [ ] Test 9: Open Output Folder
- [ ] Test 10: Demo Mode

### Linux (Optional)
- [ ] Test 1: First Launch
- [ ] Test 2: Google Maps Scraping (New Mode)
- [ ] Test 3: Append Mode
- [ ] Test 4: Path Handling
- [ ] Test 5: Logging Verification
- [ ] Test 6: ChromeDriver & Selenium
- [ ] Test 7: Restart & Persistence
- [ ] Test 8: Error Handling
- [ ] Test 9: Open Output Folder
- [ ] Test 10: Demo Mode

## Post-Validation Actions

After successful validation on all target platforms:

1. Document any platform-specific issues encountered
2. Update user-facing documentation with platform-specific notes
3. Consider code signing for Windows/macOS executables (optional, for distribution)
4. Prepare deployment package with README and installation instructions
