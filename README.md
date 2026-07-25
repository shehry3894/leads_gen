# Google Maps Lead Generator

Scrape business leads (name, address, phone, website, socials, emails) from Google Maps into an Excel file. Ships as a Streamlit web UI and a CLI. Machine-bound offline licensing.

## Quick start

```bash
make install          # install deps via uv
make ui               # Streamlit UI at http://localhost:8501
make cli              # interactive CLI
```

Skip licensing for local development:
```bash
uv run python main.py --query "gyms in NYC" --max-results 10 --no-license
```

## Prerequisites

- Python 3.11+
- Google Chrome (Selenium drives it via `webdriver-manager`)
- [`uv`](https://docs.astral.sh/uv/) — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Make targets

| Target | What it does |
|---|---|
| `make install` | Install runtime deps (`uv pip install -e .`) |
| `make install-build` | Adds `streamlit-desktop-app` for `make build` |
| `make ui` | Run Streamlit UI |
| `make cli` | Run CLI in interactive mode |
| `make fingerprint` | Print this machine's licensing fingerprint |
| `make build` | Build a standalone GUI executable (see [EXECUTABLE_BUILD.md](docs/development/EXECUTABLE_BUILD.md)) |
| `make test` | Fast pytest suite (no browser, no network) |
| `make test-live` / `test-live-visible` | End-to-end scraper against real Google Maps |
| `make test-ui` / `test-ui-visible` | End-to-end Streamlit UI drive |
| `make quality` | Auto-fix format + lint, then run mypy + tests |
| `make check` | Read-only verify (for CI): format + lint + mypy + tests |
| `make clean` | Remove `build/` and `dist/` |

Env vars honored by the test targets are documented inline in the [Makefile](Makefile).

## Runtime configuration

Three settings in [leads_gen/config/settings.py](leads_gen/config/settings.py) drive behavior:

- **`TRIAL`** — env-controlled (`LEADS_GEN_TRIAL=true`), default `false`. When on, caps the scroll stage at 3 businesses regardless of `--max-results` or license cap — a dev-only fast switch. **Customer builds must ship with this off** (the default).
- **`TESTING`** — env-controlled (`LEADS_GEN_TESTING=true`). Bypasses Selenium and returns canned demo data. Useful for exercising the normalization/output pipeline without a browser.
- **`HEADLESS_MODE`** — env-controlled, default `false`. Chrome runs visibly by default so Google Maps' bot detection doesn't throttle the scroll feed. Set `HEADLESS_MODE=true` for server / automated runs where the yield drop is acceptable.

`WAIT_CONFIG` in the same file centralizes Selenium timeouts consumed by `SmartWait`.

## CLI

```bash
uv run python main.py --query "cafes in Paris" --max-results 20
uv run python main.py --query "hotels in Miami" --max-results all
uv run python main.py --help
```

Output lands in `output/{query_with_underscores}.xlsx`. If the file already exists, new rows are merged and deduplicated with the existing file. CLI exit codes:

| Code | Meaning |
|---|---|
| 1 | License required or invalid |
| 2 | Chrome / driver could not start |
| 3 | Scraper hit an unexpected error |
| 4 | Could not write the output file |

## Streamlit UI

Two modes:
- **Start fresh** — new query, new Excel file. If a file with the same auto-generated name already exists, the UI opens a blocking modal asking whether to **Discard & scrape fresh**, **Append to existing**, or **Cancel**.
- **Append to existing** — upload/point at an existing `.xlsx` and merge new rows into it.

UI output goes to `leads_gen_output/`. License status, machine fingerprint, and a Trial-mode button are all in the sidebar.

## Known limitations

**Review Count is best-effort.** Google Maps serves a "limited view" of the place panel to unauthenticated / headless sessions and omits the review count from that view; the rating still comes through, but the count is captured only when Google classifies the session as a full view. Every other field (name, address, phone, website, socials, emails, rating, Google Maps link) is reliable.

## Licensing (short version)

Machine-bound, offline.

```bash
make fingerprint                                          # get this machine's fingerprint
# send it to the license issuer
echo "YOUR_LICENSE_KEY" > leads_gen/license.key           # activate
```

The `--no-license` CLI flag bypasses licensing entirely (local dev only). Full details in [docs/licensing/LICENSING_GUIDE.md](docs/licensing/LICENSING_GUIDE.md).

## Docker

```bash
docker build -t leads_gen .
docker run -p 8501:8501 leads_gen
```

## Project layout

```
app.py                    # Streamlit entry point
main.py                   # CLI entry point
leads_gen/
  config/settings.py      # TRIAL, TESTING, HEADLESS_MODE, WAIT_CONFIG
  scraper/                # driver, search, scrape (interleaved scroll+scrape), zooming
  core/                   # data_normalization, demo_data
  licensing/              # fingerprint, license_codec, license_manager, license_model
  utils/                  # paths, logging_utils, wait_utils (SmartWait)
tools/generate_license.py # developer-only license issuer
tests/                    # pytest suite (fast + live + ui markers)
docs/                     # PROJECT_STRUCTURE, EXECUTABLE_BUILD, LICENSING_GUIDE
```

More detail in [docs/development/PROJECT_STRUCTURE.md](docs/development/PROJECT_STRUCTURE.md).
