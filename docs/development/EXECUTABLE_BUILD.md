# Building the standalone executable

The app can be packaged as a single-file, no-Python-required executable using [`streamlit-desktop-app`](https://github.com/BeyondEvil/streamlit-desktop-app) (which wraps PyInstaller).

## Build

```bash
make install-build     # adds streamlit-desktop-app to the env
make clean             # optional: remove previous build/ and dist/
make build             # produces dist/leads_gen
```

The full PyInstaller invocation (hidden imports, `--collect-all`, etc.) lives in [Makefile](../../Makefile) under the `build:` target — edit that if you need to tweak flags. Never call `streamlit-desktop-app` directly; the Makefile is the source of truth.

Build takes 1–2 min. Output is roughly 90–100 MB.

## Run

```bash
open dist/leads_gen         # macOS Finder-style launch
./dist/leads_gen            # or run directly
```

The executable launches a local Streamlit server and opens a native window.

## Distribute

The `dist/leads_gen` binary is self-contained — copy it to another machine of the **same OS + architecture** and it runs. It is built for one target only (the machine you built it on).

### macOS Gatekeeper

Unsigned binaries need one-time approval:

```bash
xattr -d com.apple.quarantine dist/leads_gen
```

Or right-click → Open in Finder on first launch.

### Code signing (optional)

```bash
codesign --force --deep --sign "Developer ID Application: Your Name" dist/leads_gen
codesign -dv dist/leads_gen
```

For public distribution outside the App Store you'll also need notarization (`xcrun notarytool submit ...`).

## When it breaks

**"Module not found" at runtime.** PyInstaller didn't pick up a dynamically-imported package. Add `--hidden-import <pkg>` or `--collect-all <pkg>` to the `build:` target in the Makefile and rebuild.

**Build warnings.** Read `build/leads_gen/warn-leads_gen.txt` — anything critical will be flagged there.

**License file missing at runtime.** The build does not bundle `leads_gen/license.key`. Users activate on their own machine after install (see [../licensing/LICENSING_GUIDE.md](../licensing/LICENSING_GUIDE.md)).

## Constraints

- Built on macOS ARM64 → runs only on macOS ARM64. Build once per target OS/arch.
- Python 3.11+ (frozen into the binary; can't be swapped at runtime).
- No hot-reload; every code change requires a rebuild.
