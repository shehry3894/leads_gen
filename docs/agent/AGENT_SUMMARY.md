# Agent Summary - Google Maps Lead Generator

**Last Updated:** February 5, 2026  
**Project Status:** ~80% Complete  
**Current Branch:** `streamlit-app-functionality-added`

---

## Project Overview

This is a Google Maps Lead Generator application that scrapes business information from Google Maps and exports it to Excel. The application supports two deployment modes:
- **Streamlit Web UI** - Interactive web interface for end users
- **CLI Mode** - Command-line interface for automation and scripting

The application is designed to be packaged as a standalone executable using PyInstaller for distribution to end users.

---

## Recent Major Changes

### 1. Logging System Overhaul
- **Per-Session Timestamped Log Files**: Each app session creates a unique log file with format `app_YYYY-MM-DD_HH-MM-SS.log`
- **Fixed Duplication Issues**: Resolved multiple log duplication bugs in Streamlit's rerun model
- **Session-Persistent Logging**: Log file is created once per browser session, not on every user action
- **Implementation**: 
  - `utils/logging_utils.py` - Centralized logging configuration
  - `app.py` - Uses `st.session_state` to persist log file path across reruns

### 2. Data Normalization & Quality
- **New Module**: `utils/data_normalization.py`
- **Canonical Data Model**: Enforces consistent column schema across all outputs
- **Data Cleaning**: Normalizes phone numbers, empty values, and sanitizes Excel-incompatible characters
- **Deduplication**: Intelligent deduplication using website (primary) and name+address (fallback) as keys
- **Integration**: Applied in both Streamlit UI (`app.py`) and CLI (`main.py`)

### 3. UI/UX Improvements
- **Workflow Locking**: Once user selects "Start Fresh" or "Append to Existing", the choice is locked until browser refresh
- **File Path Display**: Uploaded files now display their absolute path in the local file path input field
- **Progress Feedback**: Clear indication of scraping progress and file save locations
- **File Persistence**: In append mode, files are saved directly to output directory (not temp), and overwritten in place

### 4. Bug Fixes
- **Bug `leads_gen-kqd`**: Fixed `AttributeError` in `render_clickable_links` when handling mixed data types
- **Log File Creation**: Fixed issue where new log file was created on every user action
- **Handler Deduplication**: Improved path resolution logic in `configure_file_logging`

### 5. Documentation
- **`PROJECT_STRUCTURE.md`**: Comprehensive module organization and design principles
- **`CROSS_PLATFORM_VALIDATION.md`**: Validation checklist for Windows, macOS, Linux
- **`CHANGELOG_2026-02-05.md`**: Detailed changelog of all work in this session
- **`.gitignore`**: Updated to ignore logs, build artifacts, IDE settings, and OS files

---

## Technical Architecture

### Module Structure
```
leads_gen/
├── app.py                    # Streamlit UI entry point
├── main.py                   # CLI entry point
├── data_types.py            # Shared type definitions
├── input/
│   └── config.py            # User configuration
├── scraper/
│   ├── driver.py            # WebDriver management
│   ├── search.py            # Google Maps search logic
│   ├── scroll.py            # Result scrolling
│   ├── scrape.py            # Data extraction
│   └── zooming.py           # Map zoom controls
└── utils/
    ├── data_normalization.py  # Data cleaning & deduplication
    ├── email_utils.py         # Email extraction
    ├── files_and_dir_utils.py # Path management
    ├── logging_utils.py       # Logging configuration
    ├── paths.py               # Cross-platform path handling
    ├── printing_and_logging.py # Logging helpers
    ├── selenium_utils.py      # Selenium utilities
    └── webservices.py         # Social media link extraction
```

### Key Design Principles
1. **Separation of Concerns**: UI (`app.py`) is decoupled from business logic (`scraper/`, `utils/`)
2. **No Circular Dependencies**: Modules have clear dependency hierarchy
3. **EXE Compatibility**: All modules are importable in PyInstaller-packaged executables
4. **Cross-Platform**: Uses `pathlib.Path` and `sys.frozen` for robust path handling
5. **Testability**: Business logic is isolated and unit testable

### Canonical Data Model
```python
CANONICAL_COLUMNS = [
    'Name', 'Google Maps Link', 'Address', 'Phone', 'WhatsApp', 'Website',
    'Rating', 'Review Count', 'Facebook', 'Instagram', 'Twitter', 'LinkedIn',
    'YouTube', 'Pinterest', 'TikTok', 'Threads', 'Snapchat', 'Emails', 
    'Scraped Time'
]
```

---

## Key Files & Their Purpose

### Core Application
- **`app.py`**: Streamlit web UI, handles user interactions, file uploads, and progress display
- **`main.py`**: CLI entry point, processes command-line arguments and runs scraper

### Scraping Engine
- **`scraper/search.py`**: Initiates Google Maps search and handles search results
- **`scraper/scroll.py`**: Scrolls through paginated results
- **`scraper/scrape.py`**: Extracts business data from individual listings
- **`scraper/driver.py`**: Manages Selenium WebDriver lifecycle

### Utilities
- **`utils/data_normalization.py`**: Data cleaning, normalization, and deduplication
- **`utils/logging_utils.py`**: Centralized logging configuration with per-session files
- **`utils/paths.py`**: Cross-platform path resolution for regular and frozen (EXE) modes
- **`utils/email_utils.py`**: Email extraction from web pages
- **`utils/webservices.py`**: Social media link extraction and validation

### Configuration & Build
- **`input/config.py`**: User-configurable settings (search queries, result limits)
- **`leads_gen.spec`**: PyInstaller build specification
- **`requirements.txt`**: Python dependencies
- **`Dockerfile`**: Container configuration (uses `uv` for fast installs)

### Documentation
- **`PROJECT_STRUCTURE.md`**: Module organization and design principles
- **`CROSS_PLATFORM_VALIDATION.md`**: Testing checklist for packaged executables
- **`CHANGELOG_2026-02-05.md`**: Detailed changelog of recent work
- **`AGENTS.md`**: Beads issue tracker workflow and mandatory session completion steps

---

## Issue Tracking (Beads)

### Completed Epics & Stories
- ✅ **EPIC 1**: Configuration & Bootstrap (`leads_gen-brp`)
- ✅ **EPIC 2**: Logging Infrastructure (`leads_gen-bfb`)
- ✅ **EPIC 3**: Data Management & Deduplication (`leads_gen-d7o`)
- ✅ **EPIC 4**: Streamlit UI (`leads_gen-vkt`)
- ✅ **EPIC 5**: Google Maps Scraping Engine (`leads_gen-2mj`)
- ✅ **Bug Fix**: `AttributeError` in `render_clickable_links` (`leads_gen-kqd`)

### Open Tasks (Backlog - P4)
- **EPIC 7**: Licensing & Enforcement System (`leads_gen-w1v`) - All stories set to P4 per user request
  - Story 7.1 – Machine Fingerprint Generation
  - Story 7.2 – License Data Model
  - Story 7.3 – License Key Encoding (Offline)
  - Story 7.4 – License Key Storage
  - Story 7.5 – License Validation Logic
  - Story 7.6 – Enforcement Rules

### Documentation Tasks (P3)
- **EPIC 10**: Documentation & Handoff (`leads_gen-sle`)
  - Story 10.1 – Internal Engineering Docs (`leads_gen-sle.1`)
  - Story 10.2 – User-Facing Instructions (`leads_gen-sle.2`)

---

## Known Issues & Limitations

### Fixed Issues
1. ✅ Log file duplication in Streamlit UI
2. ✅ New log file created on every user action
3. ✅ `AttributeError` when rendering clickable links with mixed data types
4. ✅ Workflow selection not locked after starting scrape

### Current Limitations
1. **Licensing System**: Not yet implemented (P4 backlog)
2. **Rate Limiting**: No built-in rate limiting for Google Maps scraping
3. **Captcha Handling**: May encounter captchas on high-volume scraping

---

## Development Workflow

### Using Beads Issue Tracker
```bash
bd ready                      # Find available work
bd show <id>                  # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>                 # Complete work
bd sync                       # Sync with git
```

### Running the Application

**Streamlit UI:**
```bash
streamlit run app.py
```

**CLI Mode:**
```bash
python main.py
```

**Building Executable:**
```bash
pyinstaller leads_gen.spec
```

### Testing Strategy
- **Unit Tests**: Created for isolated components (logging, data normalization, link rendering)
- **Integration Tests**: Manual testing of UI workflows and CLI operations
- **Validation**: Cross-platform testing checklist in `CROSS_PLATFORM_VALIDATION.md`

---

## Session Completion Checklist (MANDATORY)

Before ending any work session, ALL steps must be completed:

1. **File issues** for remaining work
2. **Run quality gates** (tests, linters, builds) if code changed
3. **Update issue status** (close finished, update in-progress)
4. **PUSH TO REMOTE** (MANDATORY):
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** (stashes, remote branches)
6. **Verify** (all changes committed AND pushed)
7. **Hand off** (context for next session)

**CRITICAL**: Work is NOT complete until `git push` succeeds.

---

## Next Steps

### Immediate (Current Session)
1. Commit and push all recent changes (see `CHANGELOG_2026-02-05.md`)
2. Update beads issues to reflect completed work

### Short Term (P3)
1. Complete internal engineering documentation (Story 10.1)
2. Create user-facing instructions (Story 10.2)
3. Perform cross-platform validation using checklist

### Long Term (P4 - Backlog)
1. Implement licensing system (EPIC 7)
2. Add rate limiting for scraping
3. Implement captcha detection and handling

---

## Important Notes for Future Agents

1. **Logging**: All logging should use `logging.getLogger("leads_gen")` namespace
2. **Paths**: Always use `pathlib.Path` and check `sys.frozen` for EXE compatibility
3. **Data Flow**: All scraped data must go through `process_scraped_data()` for normalization
4. **Session State**: Streamlit UI relies heavily on `st.session_state` - be careful with state management
5. **Deduplication**: Uses website as primary key, falls back to name+address combination
6. **Workflow Locking**: Once locked, requires browser refresh to unlock (by design)
7. **Log Files**: One per session, timestamped filename format `app_YYYY-MM-DD_HH-MM-SS.log`

---

## Contact & Handoff

**Previous Session Transcript**: `/Users/shehryarali/.cursor/projects/Volumes-data-Work-Google-Leads-leads-gen/agent-transcripts/99a283d4-1b51-4451-955c-6bc7e4276867.txt`

**Key Decisions Made**:
- Licensing features moved to P4 backlog (not urgent)
- Focus on core scraping functionality and data quality
- Per-session log files instead of rotating logs
- Direct file overwriting in append mode (no temp directory)

**Changelog**: See `CHANGELOG_2026-02-05.md` for detailed changelog of latest session.

---

**End of Summary**
