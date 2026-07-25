.PHONY: help install install-build ui cli test test-all test-live test-live-visible test-ui test-ui-visible fingerprint license build clean lint format typecheck check quality

PYTHON ?= uv run python
UV     ?= uv

# Paths passed to the quality tools. Keep this in sync with pyproject exclude lists.
CODE_PATHS := leads_gen tests tools app.py main.py

# --- Build metadata ---
# Version is read from leads_gen/version.py, arch from uname. Pure-shell (no
# Python invocation) so `make help` stays fast. Windows AMD64 normalises to
# x86_64 so builds across Intel Mac, Linux x64, and Windows x64 share a name.
#
# Dots in the version are replaced with dashes for the filename: macOS Finder
# would otherwise treat "1.0.0" as an unknown ".0" extension and refuse to
# double-click-launch the binary. Semver stays intact in version.py.
BUILD_VERSION := $(shell awk -F'"' '/^__version__/ {print $$2}' leads_gen/version.py 2>/dev/null)
BUILD_VERSION_FILENAME := $(shell echo "$(BUILD_VERSION)" | tr '.' '-')
BUILD_ARCH := $(shell uname -m 2>/dev/null | tr '[:upper:]' '[:lower:]' | sed 's/amd64/x86_64/')
BUILD_NAME := leads-gen_$(BUILD_ARCH)_$(BUILD_VERSION_FILENAME)

help:
	@echo "Targets:"
	@echo "  install        Install runtime dependencies from pyproject.toml"
	@echo "  install-build  Install runtime + build extras (streamlit-desktop-app)"
	@echo "  ui             Run the Streamlit web UI (http://localhost:8501)"
	@echo "  cli            Run the CLI in interactive mode"
	@echo "  test           Run the fast pytest suite (no browser, no network)"
	@echo "  test-live      Run the live end-to-end scraper test (needs Chrome + internet)"
	@echo "  test-live-visible  Same as test-live but with a visible browser window"
	@echo "  test-ui        Drive the Streamlit UI end-to-end in a headless browser"
	@echo "  test-ui-visible  Same as test-ui but with a visible browser window"
	@echo "  test-all       Run fast + live + ui suites"
	@echo "  format         Apply isort + black to all source files"
	@echo "  lint           Run ruff (auto-fixing) on all source files"
	@echo "  typecheck      Run mypy on the leads_gen package"
	@echo "  check          Verify format/lint/types/tests (read-only; for CI)"
	@echo "  quality        Auto-fix format + lint, then run typecheck + tests (one-shot dev command)"
	@echo "  fingerprint    Print the machine fingerprint for licensing"
	@echo "  license        (Issuer-only) Generate a license key for a customer."
	@echo "                 Required: FINGERPRINT=<uuid> MAX_RESULTS_PER_RUN=<int>"
	@echo "                 Pick one duration: DAYS=<int> | MONTHS=<int> | EXPIRY_DATE=YYYY-MM-DD"
	@echo "                 Optional: TEST_DECODE=1 (verify the key round-trips before printing)"
	@echo "  build          Build the standalone GUI executable"
	@echo "                 Output: dist/leads-gen_<arch>_<version> (e.g. leads-gen_arm64_1-0-0)"
	@echo "                 Version dots -> dashes so Finder can double-click launch."
	@echo "  clean          Remove build/dist artifacts"

install:
	$(UV) pip install -e .

install-build:
	$(UV) pip install -e ".[build]"

ui:
	$(UV) run streamlit run app.py

cli:
	$(PYTHON) main.py

# Fast tests only (no Chrome, no network). Env vars honored:
#   LEADS_GEN_TESTING=true  → makes app.py return demo data instead of scraping (used by test-ui)
test:
	$(UV) run pytest

# Live end-to-end scrape test (hits Google Maps). Env vars honored:
#   HEADLESS_MODE=false       → show the Chrome window
#   CHROMEDRIVER_PATH=/path   → skip webdriver-manager download, use local driver
#                               (needed on machines with strict firewalls or bundled builds)
test-live:
	$(UV) run pytest -m live

# Same as test-live with a visible Chrome window. To debug slow selectors, prepend
# extra env, e.g.:
#   HEADLESS_MODE=false CHROMEDRIVER_PATH=~/.wdm/... make test-live-visible
test-live-visible:
	HEADLESS_MODE=false $(UV) run pytest -m live -v -s

# UI tests drive the Streamlit app through Selenium. Env vars honored:
#   UI_HEADLESS=false         → show the Chrome window driving the UI
#   CHROMEDRIVER_PATH=/path   → use a specific chromedriver binary
#   LEADS_GEN_TESTING=true    → auto-set inside the spawned Streamlit subprocess
#                               (returns demo data, no live scrape)
test-ui:
	$(UV) run pytest -m ui -v

# Same as test-ui but with visible browser. Chain env vars, e.g.:
#   UI_HEADLESS=false CHROMEDRIVER_PATH=~/.wdm/... make test-ui-visible
test-ui-visible:
	UI_HEADLESS=false $(UV) run pytest -m ui -v -s

test-all:
	$(UV) run pytest -m "live or ui or not live"

fingerprint:
	$(PYTHON) -c "from leads_gen.licensing.fingerprint import generate_machine_fingerprint; print(generate_machine_fingerprint())"

# Issuer-only. tools/generate_license.py holds the SECRET_KEY and is not shipped
# with the distributed binary. Never expose this target on a customer machine.
#
# Usage:
#   make license FINGERPRINT=5172A6D1-D8D1-525D-B275-C891BB687412 MAX_RESULTS_PER_RUN=500 DAYS=30
#   make license FINGERPRINT=5172A6D1-D8D1-525D-B275-C891BB687412 MAX_RESULTS_PER_RUN=5000 MONTHS=12
#   make license FINGERPRINT=5172A6D1-D8D1-525D-B275-C891BB687412 MAX_RESULTS_PER_RUN=1000 EXPIRY_DATE=2027-06-30
#   make license FINGERPRINT=5172A6D1-D8D1-525D-B275-C891BB687412 MAX_RESULTS_PER_RUN=500 DAYS=30 TEST_DECODE=1
license:
	@if [ -z "$(FINGERPRINT)" ]; then echo "Error: FINGERPRINT is required. e.g. make license FINGERPRINT=<uuid> MAX_RESULTS_PER_RUN=500 DAYS=30"; exit 1; fi
	@if [ -z "$(MAX_RESULTS_PER_RUN)" ]; then echo "Error: MAX_RESULTS_PER_RUN is required. e.g. make license FINGERPRINT=<uuid> MAX_RESULTS_PER_RUN=500 DAYS=30"; exit 1; fi
	@if [ -z "$(DAYS)$(MONTHS)$(EXPIRY_DATE)" ]; then echo "Error: pick one of DAYS=<int>, MONTHS=<int>, or EXPIRY_DATE=YYYY-MM-DD"; exit 1; fi
	$(PYTHON) tools/generate_license.py \
		--fingerprint $(FINGERPRINT) \
		--max-results $(MAX_RESULTS_PER_RUN) \
		$(if $(DAYS),--days $(DAYS)) \
		$(if $(MONTHS),--months $(MONTHS)) \
		$(if $(EXPIRY_DATE),--expiry-date $(EXPIRY_DATE)) \
		$(if $(TEST_DECODE),--test-decode)

build:
	@echo "==> Building $(BUILD_NAME) (arch=$(BUILD_ARCH), version=$(BUILD_VERSION))"
	$(UV) run streamlit-desktop-app build app.py \
		--name $(BUILD_NAME) \
		--pyinstaller-options \
			--onefile \
			--clean \
			--console \
			--paths ./ \
			--hidden-import leads_gen \
			--hidden-import leads_gen.scraper \
			--hidden-import leads_gen.utils \
			--hidden-import leads_gen.config \
			--hidden-import leads_gen.core \
			--hidden-import leads_gen.licensing \
			--add-data "leads_gen:leads_gen" \
			--collect-all streamlit \
			--collect-all openpyxl \
			--collect-all pandas \
			--collect-all requests \
			--collect-all selenium \
			--collect-all webdriver_manager \
			--collect-all xlsxwriter
	@echo "==> Built dist/$(BUILD_NAME)"

clean:
	rm -rf build/ dist/

format:
	$(UV) run isort $(CODE_PATHS)
	$(UV) run black $(CODE_PATHS)

lint:
	$(UV) run ruff check --fix $(CODE_PATHS)

typecheck:
	$(UV) run mypy leads_gen

check:
	$(UV) run isort --check-only $(CODE_PATHS)
	$(UV) run black --check $(CODE_PATHS)
	$(UV) run ruff check $(CODE_PATHS)
	$(UV) run mypy leads_gen
	$(UV) run pytest

# One-shot: auto-fix everything fixable, then verify what isn't.
quality:
	@echo "==> isort"
	$(UV) run isort $(CODE_PATHS)
	@echo "==> black"
	$(UV) run black $(CODE_PATHS)
	@echo "==> ruff (auto-fix)"
	$(UV) run ruff check --fix $(CODE_PATHS)
	@echo "==> mypy"
	$(UV) run mypy leads_gen
	@echo "==> pytest"
	$(UV) run pytest
	@echo "✓ quality checks complete"
