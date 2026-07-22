# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

`pyproject.toml` is the single source of truth for dependencies (installed via `uv`). `streamlit-desktop-app` lives in the `[build]` optional-dependency group and is only needed when producing the standalone executable. Common workflows are wrapped in the [Makefile](Makefile):

```bash
# Install runtime dependencies (make install → uv pip install -e .)
make install

# Install runtime + build extras (needed only for `make build`)
make install-build

# Run the Streamlit web UI (http://localhost:8501)
make ui

# Run CLI (interactive prompts)
make cli

# Run CLI non-interactively (bypass make; --no-license skips licensing for local testing)
uv run python main.py --query "gyms in NYC" --max-results 10 --no-license
uv run python main.py --query "hotels in Miami" --max-results all

# Show the machine fingerprint (needed to generate a license)
make fingerprint

# Generate a license (developer-only tool; not bundled)
uv run python tools/generate_license.py --fingerprint <hash> --days 30 --max-results 500

# Activate a license
echo "YOUR_LICENSE_KEY" > leads_gen/license.key

# Run the scraper smoke test (subprocess-driven, ~2 min timeout, uses TRIAL cap of 3)
make test

# Build the standalone GUI executable
make build

# Run browser visibly (debugging)
HEADLESS_MODE=false make ui
```

There is no configured lint or unit-test runner. `tests/test_scraper.py` is an end-to-end smoke test that spawns `main.py` as a subprocess — it hits live Google Maps and is subject to `TRIAL` and license checks.

## Runtime configuration

Three flags in [leads_gen/config/settings.py](leads_gen/config/settings.py) materially change behavior and are worth knowing before debugging:

- `TRIAL = True` — **caps `scroll_results` to 3 businesses regardless of `--max-results`**. This overrides both the CLI arg and license limits at the scroll stage and is the usual reason "why did I only get 3 results". Flip to `False` for real runs.
- `TESTING = False` — when `True`, `main.py` skips Selenium entirely and returns `get_demo_leads()` (canned data). Useful for exercising the normalization/output pipeline without a browser.
- `HEADLESS_MODE` — env var, default `true`. Set `HEADLESS_MODE=false` to see the browser (needed when Google Maps selectors break).

`WAIT_CONFIG` in the same file centralizes Selenium timeouts and retry counts consumed by `SmartWait`.

## Architecture

### Layered pipeline

The scrape flow is a linear pipeline; each stage is a separate module and can be swapped/debugged in isolation:

1. `scraper.driver.start_driver` — builds a Chrome WebDriver via `webdriver-manager`, honoring `HEADLESS_MODE`. Includes a `resource_path()` helper for PyInstaller-frozen builds.
2. `scraper.search.search_maps` — navigates to Google Maps, dismisses cookie consent, zooms the page out (90→67%) via JS to fit more results, tries a list of search-box selectors (Google's DOM is unstable).
3. `scraper.scroll.scroll_results` — scrolls the `div[role="feed"]` sidebar until either `max_results` is reached or five consecutive scrolls produce no new `.Nv2PK` cards. **This function unconditionally applies the `TRIAL=3` cap.**
4. `scraper.scrape.scrape_business_data` — iterates the collected list cards. For each card it: (a) reads the expected name from the list item *before* clicking, (b) clicks and waits for the detail panel `h1.DUwDvf` to display the expected name (defense against Google returning a stale "Results" panel), (c) tries multiple XPath fallbacks per field (address / phone / website / rating / review count), (d) if the "website" URL is actually a social link it's rerouted into the matching social column, otherwise `extract_social_and_email_links` fetches the site with `requests` and regexes out socials + emails.
5. `core.data_normalization.process_scraped_data` — converts to DataFrame, enforces `CANONICAL_COLUMNS` schema and order, sanitizes strings for Excel, then deduplicates by website URL (fallback to name+address).
6. Output: CLI writes to `leads_gen/output/`, Streamlit UI writes to `leads_gen/leads_gen_output/` (via `utils.paths.get_output_dir` vs `get_ui_output_dir`). If the target `.xlsx` already exists, both entry points **merge and deduplicate with the existing file** rather than overwriting.

### Selector strategy

`scrape_business_data` and `search_maps` each define lists of `(By, selector)` tuples per field and iterate them via `SmartWait.wait_for_element` with short (2–3s) timeouts. Google Maps changes class names frequently, so when a field starts returning `"N/A"`, the fix is almost always to add a new selector to the top of the relevant list — not to restructure the loop.

### SmartWait

[leads_gen/utils/wait_utils.py](leads_gen/utils/wait_utils.py) wraps `WebDriverWait` with three condition modes (`presence`/`visibility`/`clickable`), configurable retries, optional exponential backoff, and a `retry_with_backoff(callable)` helper used for click retries against stale elements. All Selenium waits should go through this rather than raw `WebDriverWait`.

### Licensing

Machine-bound, offline. Flow:

- [licensing/fingerprint.py](leads_gen/licensing/fingerprint.py) hashes MAC + system UUID + hostname to a 64-char SHA-256.
- [tools/generate_license.py](tools/generate_license.py) (developer-only) JSON-serializes a `LicenseData`, appends a checksum, XOR-encrypts with `SHA256(SECRET_KEY)`, base64-encodes. The `SECRET_KEY` string is hardcoded in that file and must match between generator and validator.
- [licensing/license_manager.py](leads_gen/licensing/license_manager.py) imports `decode_license` from the tools module (unusual — the "developer tool" is a runtime dependency of the validator). It reads `leads_gen/license.key`, decodes it, verifies the fingerprint matches the current machine, checks expiry, and enforces `max_results_per_run`.
- `main.py` enforces the license before scraping and rejects any `--max-results` above the license cap. The Streamlit `app.py` does the same and surfaces the fingerprint in the UI when no license is present.
- `--no-license` bypasses the entire licensing subsystem — intended for local testing only.

### PyInstaller / frozen builds

Both `app.py` and `driver.py`/`paths.py` contain frozen-mode branches (`sys.frozen`, `sys._MEIPASS`). `app.py` monkey-patches `importlib.metadata` to fake a Streamlit distribution because PyInstaller strips package metadata. `utils.paths.get_base_dir()` returns the executable directory when frozen (so `output/`, `logs/`, `license.key` live next to the binary) and the project root otherwise. When modifying imports or adding data files, update the `hiddenimports` and `datas` lists in [leads_gen.spec](leads_gen.spec) accordingly.

### Logging

`utils.logging_utils.configure_file_logging` creates one timestamped log per session under `logs/` (CLI) or `leads_gen/logs/` (frozen), attaches a single `FileHandler` to the `"leads_gen"` logger, and disables propagation to avoid duplicate handlers on Streamlit reruns. All modules use `logging.getLogger("leads_gen")` — do not use the root logger.
