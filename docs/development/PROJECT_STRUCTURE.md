# Project Structure and Module Boundaries

This document defines the organization and responsibilities of each module in the Google Maps Lead Generator application.

## Directory Structure

```
leads_gen/
├── app.py                 # Streamlit UI entry point
├── main.py                # CLI entry point
├── version.py             # Application metadata (name, version)
├── data_types.py          # Shared data types and enums
├── input/                 # Configuration and user input handling
│   ├── __init__.py
│   └── config.py          # Configuration constants and user input functions
├── scraper/               # Google Maps scraping engine (business logic)
│   ├── __init__.py
│   ├── driver.py          # WebDriver initialization and management
│   ├── search.py          # Google Maps search functionality
│   ├── scroll.py          # Results scrolling logic
│   ├── scrape.py          # Business data extraction (including social media/emails)
│   └── zooming.py         # Map zooming utilities
└── utils/                 # Shared utilities (pure functions, no UI dependencies)
    ├── __init__.py
    ├── data_normalization.py  # Data model, normalization, and deduplication
    ├── demo_data.py           # Test/demo data generation
    ├── email_utils.py         # Email extraction and validation
    ├── files_and_dir_utils.py # File system operations
    ├── logging_utils.py       # Centralized logging configuration
    ├── paths.py               # EXE-safe path resolution
    ├── printing_and_logging.py # Legacy logging helper
    ├── selenium_utils.py      # Selenium helper functions
    └── webservices.py         # HTTP request utilities
```

## Module Responsibilities

### 1. UI Layer (`app.py`)

**Purpose**: Streamlit-based user interface for the application.

**Responsibilities**:
- User input collection (query, max results, output directory, file upload)
- Workflow management (new vs. append mode)
- Progress display and user feedback
- Result visualization
- File download and folder opening
- **MUST NOT**: Contain business logic, directly scrape data, or perform data transformations

**Dependencies**: Can import from `scraper/`, `utils/`, and `input/`

### 2. CLI Layer (`main.py`)

**Purpose**: Command-line interface for the application.

**Responsibilities**:
- Parse command-line arguments
- Orchestrate scraping workflow
- File I/O for results
- **MUST NOT**: Import any Streamlit code or UI components

**Dependencies**: Can import from `scraper/`, `utils/`, and `input/`

### 3. Configuration (`input/`)

**Purpose**: Centralized configuration and user input handling.

**Key Files**:
- `config.py`: Configuration constants (`HEADLESS_MODE`, `TRIAL`, `TESTING`), user input functions

**Responsibilities**:
- Define application-wide configuration constants
- Provide functions for CLI user input
- **MUST NOT**: Import UI code or perform scraping

**Dependencies**: None (pure configuration)

### 4. Scraping Engine (`scraper/`)

**Purpose**: Core business logic for scraping Google Maps and external websites.

**Key Files**:
- `driver.py`: WebDriver initialization (headless/non-headless mode)
- `search.py`: Google Maps search navigation
- `scroll.py`: Infinite scroll handling for results
- `scrape.py`: Business data extraction (name, address, phone, website, rating, reviews, social media links, emails)
- `zooming.py`: Map zoom controls

**Responsibilities**:
- All Google Maps scraping logic
- Website navigation and data extraction (social media, emails)
- Return raw data dictionaries/lists
- **MUST NOT**: Import any UI code (Streamlit), handle file I/O, or perform data normalization
- **MUST**: Be importable in both development and frozen (PyInstaller) modes

**Dependencies**: Can import from `utils/` and `input/`

### 5. Utilities (`utils/`)

**Purpose**: Shared utility functions and helpers (pure functions with no UI dependencies).

**Key Files**:
- `data_normalization.py`: Canonical data model, data cleaning, deduplication, Excel sanitization
- `demo_data.py`: Generate test/demo data for offline testing
- `email_utils.py`: Email extraction and validation
- `files_and_dir_utils.py`: File system operations
- `logging_utils.py`: Centralized logging configuration (file-based, rotating logs)
- `paths.py`: EXE-safe path resolution for logs, output, and resources
- `printing_and_logging.py`: Legacy logging helper
- `selenium_utils.py`: Selenium helper functions
- `webservices.py`: HTTP request utilities

**Responsibilities**:
- Provide reusable, pure functions
- Data transformation and validation
- Logging infrastructure
- File system utilities
- **MUST NOT**: Import UI code (Streamlit) or contain scraping logic
- **MUST**: Be importable in both development and frozen modes

**Dependencies**: Minimal (can import from `input/` if needed, but not from `scraper/` or UI layers)

### 6. Application Metadata (`version.py`)

**Purpose**: Store application version and name.

**Responsibilities**:
- Define `__version__` and `__app_name__`
- Used for logging and about information

**Dependencies**: None

### 7. Shared Types (`data_types.py`)

**Purpose**: Shared data types, enums, and type definitions.

**Responsibilities**:
- Define enums (e.g., `LoggingTypes`)
- Type aliases
- Dataclasses for structured data

**Dependencies**: None

## Design Principles

### 1. Separation of Concerns

- **UI Layer** (app.py, main.py): Thin orchestration layer that delegates to business logic
- **Business Logic** (scraper/): Core functionality, independent of UI
- **Utilities** (utils/): Reusable helpers, no UI or business logic dependencies

### 2. No Circular Dependencies

- `scraper/` and `utils/` MUST NOT import from UI layers
- `utils/` MUST NOT import from `scraper/`
- UI layers can import from any lower layer

### 3. EXE Compatibility

- All modules MUST be importable in frozen mode (PyInstaller)
- Use `utils/paths.py` for all file path resolution
- Avoid hard-coded paths or assumptions about file locations

### 4. Testability

- Business logic (scraper/) should be testable without UI
- Use `TESTING` flag and `demo_data.py` for offline testing
- Pure functions in `utils/` are easily unit-testable

### 5. Logging Strategy

- All modules use the `leads_gen` logger namespace
- Configure logging via `utils/logging_utils.py`
- Logs are written to `logs/app.log` (rotating file handler)

## Data Flow

```
User Input (UI/CLI)
    ↓
Scraping Engine (scraper/)
    ↓
Raw Data (list of dicts)
    ↓
Data Normalization (utils/data_normalization.py)
    ↓
Clean DataFrame
    ↓
Deduplication (utils/data_normalization.py)
    ↓
Final DataFrame
    ↓
Excel Output (UI/CLI)
```

## Module Import Rules

### ✅ Allowed Imports

- `app.py` → `scraper/`, `utils/`, `input/`, `version.py`, `data_types.py`
- `main.py` → `scraper/`, `utils/`, `input/`, `version.py`, `data_types.py`
- `scraper/` → `utils/`, `input/`, `data_types.py`
- `utils/` → `input/`, `data_types.py` (only if necessary)
- `input/` → `data_types.py`

### ❌ Forbidden Imports

- `scraper/` → `app.py`, `main.py`, or any Streamlit code
- `utils/` → `app.py`, `main.py`, `scraper/`, or any Streamlit code
- `input/` → `app.py`, `main.py`, `scraper/`, `utils/`, or any Streamlit code

## Frozen Mode Considerations

When packaging with PyInstaller:

1. **Entry Point**: `app.py` is the main entry point
2. **Data Includes**: All project modules (`scraper/`, `utils/`, `input/`) are included as data in the `.spec` file
3. **Path Resolution**: Use `utils/paths.py` functions (`get_base_dir()`, `get_logs_dir()`, etc.) for all file paths
4. **Hidden Imports**: All necessary dependencies are specified in `leads_gen.spec`

## Adding New Modules

When adding new functionality:

1. **Determine Layer**: UI, Business Logic, or Utility?
2. **Check Dependencies**: Does it need to import from UI layers? (If yes, it belongs in UI layer)
3. **Update .spec**: Add new modules to `datas` in `leads_gen.spec`
4. **Document**: Update this file with module responsibilities
5. **Test Frozen Mode**: Verify the module works in PyInstaller build

## Module Health Checklist

Use this checklist to verify module boundaries:

- [ ] No `scraper/` modules import Streamlit
- [ ] No `utils/` modules import Streamlit or `scraper/`
- [ ] All `__init__.py` files exist
- [ ] All modules use `utils/paths.py` for file paths
- [ ] All modules use `utils/logging_utils.py` for logging
- [ ] Business logic is testable without UI
- [ ] `.spec` file includes all project modules
- [ ] Frozen mode works (test with PyInstaller)
