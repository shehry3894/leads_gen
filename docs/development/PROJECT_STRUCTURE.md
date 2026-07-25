# Project structure

## Layout

```
app.py                       Streamlit UI entry point
main.py                      CLI entry point

leads_gen/
├── config/
│   └── settings.py          TRIAL, TESTING, HEADLESS_MODE, WAIT_CONFIG, get_user_inputs()
├── scraper/                 Selenium-based Google Maps scraping
│   ├── driver.py            start_driver(), DriverInitError, _diagnose_webdriver_error()
│   ├── search.py            search_maps() — navigate, dismiss cookies, run query
│   ├── scrape.py            scrape_business_data() — interleaved scroll+scrape
│   │                        + extract_social_and_email_links()
│   └── zooming.py           zoom/checkbox helpers used by search.py
├── core/
│   ├── data_normalization.py  process_scraped_data(), deduplicate_dataframe(), CANONICAL_COLUMNS
│   └── demo_data.py           get_demo_leads() — canned data for TESTING mode
├── licensing/
│   ├── fingerprint.py       generate_machine_fingerprint() — returns the OS hardware UUID (ioreg / wmic / DMI), canonical UPPERCASE
│   ├── license_model.py     LicenseData dataclass
│   ├── license_codec.py     encode_license() / decode_license() — XOR + base64
│   └── license_manager.py   LicenseManager — loads leads_gen/license.key, validates, enforces
├── utils/
│   ├── paths.py             get_base_dir(), get_output_dir(), get_logs_dir(), etc. — tempdir fallback
│   ├── logging_utils.py     configure_file_logging() — per-session log file, stderr fallback
│   └── wait_utils.py        SmartWait — WebDriverWait wrapper with retry/backoff
├── version.py               __app_name__, __version__
└── license.key              (created by the user at activation)

tools/
└── generate_license.py      Developer-only license key generator (holds SECRET_KEY)

tests/                       pytest suite; markers: live (real network), ui (real browser)
docs/development/            PROJECT_STRUCTURE (this file), EXECUTABLE_BUILD
docs/licensing/              LICENSING_GUIDE
```

## Pipeline

The scrape flow is linear; each stage can be swapped/debugged in isolation.

```
User input (UI or CLI)
        │
        ▼
scraper.driver.start_driver          Build Chrome WebDriver (headless controlled by HEADLESS_MODE)
        │
        ▼
scraper.search.search_maps           Navigate to Google Maps, dismiss cookies, run query
        │
        ▼
scraper.scrape.scrape_business_data  Interleaved scroll+scrape loop. Per iteration:
        │                              - scroll the feed if no card at position i
        │                              - click card, wait, extract fields, fetch site
        │                                for socials/emails via requests
        │                            Stops on: max_results reached | 5 consecutive
        │                            duplicates | 3 consecutive scroll stalls |
        │                            "end of list" marker visible.
        │                            ⚠ TRIAL=True caps max_results at 3.
        ▼
core.data_normalization              Normalize to CANONICAL_COLUMNS, dedupe by website (or name+addr).
        │
        ▼
Excel output                         CLI → output/  |  UI → leads_gen_output/
                                     If file exists, merge + dedupe rather than overwrite.
```

## Selector strategy

`search_maps` and `scrape_business_data` each keep an ordered list of `(By, selector)` tuples per field and iterate them via `SmartWait.wait_for_element` with short (2–3s) timeouts. Google Maps changes class names frequently, so when a field starts returning `"N/A"`, the fix is to add a new selector at the top of the relevant list.

## Module boundaries

- **`scraper/`** may import `utils/` and `config/`. Never Streamlit.
- **`core/`** is pure data — never imports Selenium.
- **`utils/`** never imports `scraper/` or Streamlit.
- **`licensing/`** is self-contained; `license_manager` imports `decode_license` from `tools/generate_license.py` (an intentional runtime coupling — the "dev tool" holds the shared secret).
- **`app.py` / `main.py`** are the only modules that may import from any layer.

All modules log to the `leads_gen` logger (never root). Configure it once per session via `utils.logging_utils.configure_file_logging`.

## Frozen (PyInstaller) mode

- `utils.paths.get_base_dir()` returns the executable directory when `sys.frozen` is set, so `output/`, `logs/`, and `license.key` live next to the binary.
- `app.py` monkey-patches `importlib.metadata` to fake a Streamlit distribution (PyInstaller strips package metadata).
- When adding or renaming imports, keep [leads_gen.spec](../../leads_gen.spec)'s `hiddenimports` / `datas` lists in sync.
