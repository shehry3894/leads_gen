# Production Directory Structure
**Date:** February 5, 2026  
**Status:** ✅ Implemented

---

## New Structure

```
leads_gen/                          # Project root
│
├── leads_gen/                      # ✅ Main application package
│   ├── __init__.py
│   ├── version.py                  # App version metadata
│   │
│   ├── config/                     # ✅ Configuration module
│   │   ├── __init__.py
│   │   └── settings.py             # App settings (from input/config.py)
│   │
│   ├── core/                       # ✅ Core business logic
│   │   ├── __init__.py
│   │   ├── data_types.py           # Data models and types
│   │   ├── data_normalization.py  # Data cleaning & deduplication
│   │   └── demo_data.py            # Demo/test data generator
│   │
│   ├── scraper/                    # ✅ Google Maps scraping engine
│   │   ├── __init__.py
│   │   ├── driver.py               # WebDriver management
│   │   ├── search.py               # Search & navigation
│   │   ├── scroll.py               # Result scrolling
│   │   ├── scrape.py               # Data extraction
│   │   └── zooming.py              # Map zoom controls
│   │
│   ├── licensing/                  # ✅ Licensing system
│   │   ├── __init__.py
│   │   ├── fingerprint.py          # Machine fingerprint generation
│   │   ├── license_model.py        # License data structures
│   │   └── license_manager.py      # License validation & enforcement
│   │
│   └── utils/                      # ✅ Utilities
│       ├── __init__.py
│       ├── logging_utils.py        # Logging configuration
│       ├── paths.py                # Path management
│       ├── selenium_utils.py       # Selenium helpers (legacy)
│       └── webservices.py          # Email & social media extraction
│
├── tools/                          # ✅ Developer tools (NOT distributed)
│   ├── __init__.py
│   ├── generate_license.py         # License key generator
│   └── README.md                   # Tools documentation
│
├── tests/                          # ✅ Test files
│   ├── __init__.py
│   └── test_scraper.py             # Scraper tests
│
├── docs/                           # ✅ Documentation
│   ├── agent/                      # Agent-specific documentation
│   │   ├── AGENT_INSTRUCTIONS.md
│   │   └── AGENT_SUMMARY.md
│   ├── development/                # Development documentation
│   │   ├── IMPLEMENTATION_PLAN.md
│   │   ├── PROJECT_STRUCTURE.md
│   │   ├── CROSS_PLATFORM_VALIDATION.md
│   │   ├── REFACTORING_PLAN.md
│   │   └── DIRECTORY_STRUCTURE.md  # This file
│   ├── licensing/                  # Licensing documentation
│   │   └── LICENSING_GUIDE.md
│   └── reports/                    # Test & change reports
│       ├── CHANGELOG_2026-02-05.md
│       └── SCRAPER_TEST_REPORT_2026-02-05.md
│
├── logs/                           # Runtime logs (gitignored)
├── output/                         # CLI output files (gitignored)
├── leads_gen_output/               # UI output files (gitignored)
│
├── main.py                         # ✅ CLI entry point
├── app.py                          # ✅ Streamlit UI entry point
├── README.md                       # Main project README
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project metadata (uv, PEP 621)
├── environment.yml                 # Conda environment definition
├── Dockerfile                      # Container definition
├── leads_gen.spec                  # PyInstaller build specification
├── license.key                     # User license file (gitignored)
├── .gitignore                      # Git ignore rules
└── .gitattributes                  # Git attributes

```

---

## What Changed

### Files Moved

#### From Root → `leads_gen/`
- `version.py` → `leads_gen/version.py`
- `data_types.py` → `leads_gen/core/data_types.py`

#### From `input/` → `leads_gen/config/`
- `input/config.py` → `leads_gen/config/settings.py`
- `input/` directory removed

#### From `scraper/` → `leads_gen/scraper/`
- All scraper modules moved into package
- Imports updated

#### From `utils/` → Multiple Destinations
- `utils/data_normalization.py` → `leads_gen/core/`
- `utils/demo_data.py` → `leads_gen/core/`
- `utils/fingerprint.py` → `leads_gen/licensing/`
- `utils/license_model.py` → `leads_gen/licensing/`
- `utils/license_manager.py` → `leads_gen/licensing/`
- `utils/*.py` (remaining) → `leads_gen/utils/`
- `utils/` directory removed

#### From Root → `tools/`
- `generate_license.py` → `tools/generate_license.py`

#### From Root → `tests/`
- `test_scraper.py` → `tests/test_scraper.py`
- `test_run*.log` files deleted

#### From Root → `docs/`
- All `.md` files except `README.md`
- Organized into subdirectories by category

---

## Import Path Changes

### Before Refactoring
```python
from utils.data_normalization import process_scraped_data
from utils.license_manager import LicenseManager
from scraper.driver import start_driver
from input.config import get_user_inputs
from version import __version__
```

### After Refactoring
```python
from leads_gen.core.data_normalization import process_scraped_data
from leads_gen.licensing.license_manager import LicenseManager
from leads_gen.scraper.driver import start_driver
from leads_gen.config.settings import get_user_inputs
from leads_gen.version import __version__
```

---

## Benefits Achieved

### 1. ✅ Clean Root Directory
**Before:** 20+ files at root  
**After:** 8 essential files at root

Root now contains only:
- Entry points (`main.py`, `app.py`)
- Configuration (`requirements.txt`, `pyproject.toml`, etc.)
- Essential docs (`README.md`)

### 2. ✅ Standard Python Package Structure
- Proper package hierarchy with `__init__.py`
- Better IDE support and autocomplete
- Easier to understand for new developers

### 3. ✅ Organized Documentation
- No more doc sprawl at root
- Categorized by purpose
- Easy to find relevant documentation

### 4. ✅ Clear Separation of Concerns
- **Application code** in `leads_gen/`
- **Developer tools** in `tools/`
- **Tests** in `tests/`
- **Documentation** in `docs/`

### 5. ✅ Better Scalability
- Clear where new modules belong
- Easier to add features without clutter
- Professional project structure

---

## How to Use

### Running the Application

**CLI Mode:**
```bash
python main.py
```

**Streamlit UI:**
```bash
streamlit run app.py
```

**With UV:**
```bash
uv run python main.py
uv run streamlit run app.py
```

### Development

**Generate License:**
```bash
python tools/generate_license.py --help
```

**Run Tests:**
```bash
pytest tests/
# or
python tests/test_scraper.py
```

**Import in Code:**
```python
from leads_gen.scraper import search_maps
from leads_gen.core import data_normalization
from leads_gen.licensing import LicenseManager
```

---

## Files Updated

Total files with updated imports: **30+ files**

### Entry Points
- ✅ `main.py`
- ✅ `app.py`

### Application Package (`leads_gen/`)
- ✅ All scraper modules (5 files)
- ✅ All core modules (3 files)
- ✅ All licensing modules (3 files)
- ✅ All utility modules (4 files)
- ✅ Configuration module (1 file)

### Tools
- ✅ `tools/generate_license.py`

---

## Verification

To verify the refactoring worked:

```bash
# Test basic imports
python3 -c "from leads_gen.version import __version__; print(__version__)"

# Test with UV (full environment)
uv run python -c "from leads_gen.scraper.driver import start_driver; print('✓')"

# Run CLI (will check license)
echo -e "test query\n10" | uv run python main.py

# Run UI
uv run streamlit run app.py
```

---

## Migration Notes for Developers

If you have existing code using old imports:

1. **Find and replace** in your codebase:
   - `from utils.` → `from leads_gen.utils.`
   - `from scraper.` → `from leads_gen.scraper.`
   - `from input.config` → `from leads_gen.config.settings`
   - `from version import` → `from leads_gen.version import`

2. **Update paths** in configuration files:
   - PyInstaller spec files
   - Dockerfile COPY commands
   - CI/CD scripts

3. **Update documentation** references to file paths

---

## Next Steps

### Recommended Follow-ups

1. **Update PyInstaller Spec** (`leads_gen.spec`)
   - Verify all modules are included
   - Update hidden imports if needed
   - Test executable build

2. **Add Package Metadata** to `leads_gen/__init__.py`
   - Export version
   - Export main entry points
   - Add package docstring

3. **Consider Setup.py** or **setup.cfg**
   - For pip installable package
   - Enable: `pip install -e .`
   - Better for development

4. **Update CI/CD**
   - If using GitHub Actions, update paths
   - Update test commands
   - Update build scripts

---

## Rollback Procedure

If issues arise and you need to rollback:

```bash
# This refactoring was done in a single commit
git log --oneline | head -1  # Get commit hash
git revert <commit-hash>

# Or restore from backup
git stash
git checkout <previous-commit>
```

---

**Refactoring completed successfully! ✅**

All imports updated, structure reorganized, functionality preserved.
