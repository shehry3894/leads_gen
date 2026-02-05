# Building Mac Executable

This guide explains how to build a standalone Mac executable for the Google Maps Lead Generator.

## Prerequisites

- Python 3.12+
- macOS with Apple Silicon (ARM64) or Intel
- `uv` package manager
- All project dependencies installed

## Method: streamlit-desktop-app

We use `streamlit-desktop-app` which creates a desktop application with a native GUI wrapper around the Streamlit interface.

### Installation

```bash
uv pip install streamlit-desktop-app
```

### Build Command

From the project root directory:

```bash
uv run streamlit-desktop-app build app.py \
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
```

### Quick Build Script

```bash
# Clean previous builds
rm -rf build/ dist/

# Build the executable
uv run streamlit-desktop-app build app.py --name leads_gen \
  --pyinstaller-options --onefile --clean --console --paths ./ \
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
```

## Build Output

After successful build:

- **Executable location**: `dist/leads_gen`
- **Size**: ~90-95 MB
- **Format**: Mach-O 64-bit ARM64 executable
- **Dependencies**: Self-contained (only requires system libraries)

## Running the Executable

### Method 1: Double-click (Recommended)

Simply double-click `dist/leads_gen` in Finder. The app will:
1. Launch a local Streamlit server
2. Open a native window with the web interface
3. Be fully functional with all features

### Method 2: Command Line

```bash
./dist/leads_gen
```

Or from anywhere:

```bash
open /path/to/dist/leads_gen
```

## Distribution

### Basic Distribution

Simply copy the `dist/leads_gen` file to another Mac. The executable is self-contained.

### Code Signing (Optional)

For distribution outside your organization, you should code sign the app:

```bash
# Sign with your Apple Developer certificate
codesign --force --deep --sign "Developer ID Application: Your Name" dist/leads_gen

# Verify signature
codesign -dv dist/leads_gen
```

### Notarization (For Public Distribution)

For apps distributed outside the App Store:

```bash
# Create a DMG or ZIP
hdiutil create -volname "Google Maps Lead Generator" -srcfolder dist/leads_gen -ov -format UDZO leads_gen.dmg

# Submit for notarization
xcrun notarytool submit leads_gen.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# Staple the notarization ticket
xcrun stapler staple leads_gen.dmg
```

## Troubleshooting

### App Won't Open

**Issue**: macOS Gatekeeper blocks the app

**Solution**: Right-click → Open, then click "Open" in the dialog

Or remove quarantine attribute:
```bash
xattr -d com.apple.quarantine dist/leads_gen
```

### Missing Dependencies Error

**Issue**: Module not found errors

**Solution**: Rebuild with additional `--hidden-import` or `--collect-all` flags:

```bash
--hidden-import missing_module_name
--collect-all package_name
```

### Performance Issues

**Issue**: Slow startup or execution

**Solutions**:
1. Use `--onefile` flag (already included)
2. Exclude unnecessary packages with `--exclude-module`
3. Use PyInstaller's `--upx-dir` for compression

### License File Not Found

**Issue**: Executable can't find `license.key`

**Solution**: The license file is bundled. Make sure `leads_gen/license.key` exists before building.

## Build Configuration

The build uses PyInstaller under the hood with these key settings:

- **Mode**: One-file bundle (all dependencies in single executable)
- **Console**: Enabled (for debugging)
- **Optimization**: UPX compression enabled
- **Code signing**: Adhoc (for personal use)

## File Structure After Build

```
dist/
└── leads_gen              # Standalone executable (91MB)

build/                     # Temporary build files (can be deleted)
└── leads_gen/
    ├── Analysis-00.toc
    ├── base_library.zip
    ├── PKG-00.toc
    └── warn-leads_gen.txt # Check for build warnings
```

## Performance Characteristics

- **Startup time**: 2-5 seconds (first launch)
- **Memory usage**: ~150-200 MB
- **Disk space**: ~91 MB
- **Runtime**: Identical to Python version

## Updating the Executable

When code changes:

1. Update source code
2. Clean previous build: `rm -rf build/ dist/`
3. Run build command again
4. Test the new executable
5. Distribute updated version

## Known Limitations

1. **Platform-specific**: Built on Mac ARM64 → runs only on Mac ARM64
2. **Python version**: Frozen with Python 3.12 (can't be changed without rebuild)
3. **Hot-reload**: Not available (restart required for changes)
4. **License**: Must be bundled during build or user must activate separately

## Alternative: CLI-Only Executable

If you need a command-line version (without Streamlit GUI), use the `leads_gen_cli.spec` file:

```bash
uv run pyinstaller leads_gen_cli.spec --clean
```

This creates `dist/leads_gen_cli` for CLI-only usage with arguments:

```bash
./dist/leads_gen_cli --query "gyms in NYC" --max-results 20 --no-license
```

---

## Summary

✅ **Recommended**: Use `streamlit-desktop-app` for full GUI app
✅ **Alternative**: Use `pyinstaller leads_gen_cli.spec` for CLI-only version
✅ **Size**: ~91 MB
✅ **Platform**: macOS ARM64 (Apple Silicon)

For questions or issues, refer to:
- [streamlit-desktop-app documentation](https://github.com/BeyondEvil/streamlit-desktop-app)
- [PyInstaller documentation](https://pyinstaller.org/)
