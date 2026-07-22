.PHONY: help install install-build ui cli test test-all test-live test-live-visible test-ui test-ui-visible fingerprint build clean lint format typecheck check quality

PYTHON ?= uv run python
UV     ?= uv

# Paths passed to the quality tools. Keep this in sync with pyproject exclude lists.
CODE_PATHS := leads_gen tests tools app.py main.py

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
	@echo "  build          Build the standalone GUI executable"
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

build:
	$(UV) run streamlit-desktop-app build app.py \
		--name leads_gen \
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
