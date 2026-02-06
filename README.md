# 📍 Google Maps Scraper & Lead Generator

A comprehensive Python-based web scraper designed to extract business intelligence from Google Maps. This tool automates the process of finding business details, contact information, and social media presence, saving the results directly to Excel.

---

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Installation & Setup](#️-installation--setup)
- [Running the Application](#-running-the-application)
  - [Web Interface](#method-1-web-interface-recommended-for-beginners)
  - [Command Line Interface](#method-2-command-line-interface-advanced-users)
  - [Docker](#method-3-docker-no-local-setup-required)
- [Building a Standalone Executable](#-building-a-standalone-executable)
- [Licensing System](#-licensing-system)
- [Project Structure](#-project-structure)

---

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/shehry3894/leads_gen.git
cd leads_gen

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Run the web interface
uv run streamlit run app.py

# OR run CLI with arguments
uv run python main.py --query "gyms in NYC" --max-results 10 --no-license
```

The web interface will open at `http://localhost:8501`

---

## 🚀 Features

* **Multi-Interface:** Choose between a simple Command Line (CLI) or a modern Streamlit Web UI
* **Deep Data Extraction:** Scrapes name, address, phone number, website, ratings, and review counts
* **Contact Discovery:** Automatically crawls business websites to find email addresses and social media links (LinkedIn, Facebook, Instagram, YouTube, TikTok, etc.)
* **Smart Wait Logic:** Intelligent element detection with configurable timeouts and retries
* **Data Normalization:** Automatic deduplication and data cleaning
* **Machine-Bound Licensing:** Secure, offline licensing system
* **Custom Limits:** Define exactly how many leads you want to collect
* **Automated Export:** Generates clean, formatted `.xlsx` files automatically
* **Production Ready:** Professional structure, comprehensive logging, and error handling

---

## 🛠️ Installation & Setup

### Prerequisites

* **Python 3.11 or higher** ([Download Python](https://www.python.org/downloads/))
* **Google Chrome** installed (for Selenium web automation)
* **`uv` Python package manager** (recommended) or `pip`

### Step 1: Install uv (Recommended)

`uv` is a fast Python package manager that simplifies dependency management.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

Verify installation:
```bash
uv --version
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/shehry3894/leads_gen.git
cd leads_gen
```

### Step 3: Install Dependencies

**Option A: Using uv (Recommended)**

```bash
# Install all dependencies
uv pip install -r requirements.txt
```

**Option B: Using pip + venv (Legacy)**

```bash
# Create virtual environment
python -m venv venv

# Activate environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
# Check if all packages are installed
uv pip list
# or with pip:
pip list
```

You should see packages like: `selenium`, `pandas`, `streamlit`, `openpyxl`, etc.



---

## 💻 Running the Application

### Method 1: Web Interface (Recommended for Beginners)

The Streamlit web interface provides a user-friendly GUI for scraping.

**Step 1: Launch the Web UI**

```bash
# Using uv (recommended)
uv run streamlit run app.py

# Or if you activated venv
streamlit run app.py
```

**Step 2: Open in Browser**

The app will automatically open at `http://localhost:8501`

**Step 3: Use the Interface**

1. **Start Fresh Mode:**
   - Enter search query (e.g., "coffee shops in Brooklyn")
   - Set max results (e.g., 20)
   - Click "Start Scraping"
   - Download Excel file when complete

2. **Append to Existing Mode:**
   - Upload existing Excel file
   - Enter new search query
   - Set max results
   - Click "Append & Scrape"
   - Download merged Excel file

**Features:**
- ✅ Visual progress tracking with real-time updates
- ✅ Preview scraped data before downloading
- ✅ Merge with existing data files
- ✅ Download results directly from browser

---

### Method 2: Command Line Interface (Advanced Users)

The CLI provides more control and is perfect for automation.

**Interactive Mode:**

```bash
# Run the script
uv run python main.py

# Follow the prompts:
# 1. Enter search query: gyms in New York
# 2. Enter max results: 20
```

**CLI with Arguments (Fast Testing):**

```bash
# Basic usage
uv run python main.py --query "restaurants in Paris" --max-results 10

# Skip license validation (for testing)
uv run python main.py -q "cafes in Tokyo" -m 5 --no-license

# Scrape all available results
uv run python main.py --query "hotels in Miami" --max-results all

# Show help
uv run python main.py --help
```

**Output Location:**
- Files saved to: `leads_gen/output/`
- Filename format: `{query_with_underscores}.xlsx`
- Example: `gyms_in_New_York.xlsx`

**CLI Options:**
- `--query` or `-q`: Search query (e.g., "gyms in NYC")
- `--max-results` or `-m`: Number of results (or "all")
- `--no-license`: Skip license check (testing only)
- `--version`: Show version information
- `--help`: Display help message

**Environment Variables:**

Control application behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLESS_MODE` | `true` | Run Chrome browser in headless mode (no visible window). Set to `false` to see the browser during scraping (useful for debugging). |

**Examples:**

```bash
# Run with visible browser (for debugging)
HEADLESS_MODE=false uv run streamlit run app.py

# Or for CLI
HEADLESS_MODE=false uv run python main.py --query "gyms in NYC" --max-results 10

# Run in headless mode (default - no need to specify)
uv run streamlit run app.py
```

---

### Method 3: Docker (No Local Setup Required)

Run the application in a Docker container without installing Python locally.

**Step 1: Build the Docker Image**

```bash
docker build -t leads_gen .
```

**Step 2: Run the Container**

```bash
docker run -p 8501:8501 leads_gen
```

**Step 3: Access the UI**

Open your browser to: `http://localhost:8501`

---

### Example Workflows

**Example 1: Quick Test (3 Results)**

```bash
uv run python main.py --query "gyms in Manhattan" --max-results 3 --no-license
```

**Example 2: Production Run (50 Results with License)**

```bash
uv run python main.py --query "dental clinics in Los Angeles" --max-results 50
```

**Example 3: Web UI for Presentation**

```bash
uv run streamlit run app.py
# Then use the browser interface
```

**Example 4: Batch Processing Multiple Queries**

```bash
# Create a shell script
for query in "gyms in NYC" "cafes in SF" "hotels in LA"; do
  uv run python main.py --query "$query" --max-results 20 --no-license
done
```

---

## 📦 Building a Standalone Executable

Create a portable desktop application that runs without Python installed.

### Prerequisites for Building

- All dependencies installed (see Installation section)
- `streamlit-desktop-app` package (included in requirements.txt)
- macOS (for Mac builds) or Windows (for Windows builds)

### Step 1: Ensure All Dependencies Are Installed

```bash
# Make sure streamlit-desktop-app is installed
uv pip install streamlit-desktop-app

# Or install all requirements
uv pip install -r requirements.txt
```

### Step 2: Clean Previous Builds (Optional)

```bash
# Remove old build artifacts
rm -rf build/ dist/
```

### Step 3: Build the Executable

**For Mac (GUI Application):**

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

**Alternative: CLI-Only Executable (Using PyInstaller):**

```bash
uv run pyinstaller leads_gen_cli.spec --clean
```

### Step 4: Locate the Executable

After successful build:

```bash
# On macOS
ls -lh dist/leads_gen

# On Windows
dir dist\leads_gen.exe
```

**Build Output:**
- **Mac GUI**: `dist/leads_gen` (~91 MB)
- **CLI Version**: `dist/leads_gen_cli` (~76 MB)

### Step 5: Test the Executable

**Test Mac GUI App:**

```bash
# Double-click in Finder, or run:
open dist/leads_gen

# Or execute directly:
./dist/leads_gen
```

**Test CLI App:**

```bash
./dist/leads_gen_cli --query "test query" --max-results 3 --no-license
```

### Build Time & Requirements

- **Build Duration**: 1-2 minutes
- **Disk Space**: ~500 MB during build, ~100 MB final
- **RAM**: 2 GB minimum
- **Output Size**: 
  - GUI App: ~91 MB
  - CLI App: ~76 MB

### Distribution

The executable is **self-contained** and can be distributed to other users:

1. **Copy the file** from `dist/` to destination
2. **No Python required** on target machine
3. **System dependencies**: Only needs macOS (for Mac build) or Windows (for Windows build)

**For macOS:**
- May need to right-click → Open on first launch (Gatekeeper)
- Or remove quarantine: `xattr -d com.apple.quarantine dist/leads_gen`

**For Windows:**
- May trigger Windows Defender (expected for unsigned executables)
- Add exception or code-sign for production distribution

### Code Signing (Optional, for Distribution)

**macOS:**

```bash
# Sign with your Apple Developer certificate
codesign --force --deep --sign "Developer ID Application: Your Name" dist/leads_gen

# Verify signature
codesign -dv dist/leads_gen
```

**Windows:**

```bash
# Sign with your code signing certificate
signtool sign /f certificate.pfx /p password dist/leads_gen.exe
```

### Troubleshooting Build Issues

**Issue: Module not found errors**

```bash
# Add missing module to hidden imports
--hidden-import module_name
```

**Issue: Build hangs or fails**

```bash
# Try building without UPX compression
# Edit .spec file: upx=False
```

**Issue: Executable won't run**

```bash
# Check build warnings
cat build/leads_gen/warn-leads_gen.txt
```

For detailed build documentation, see: `docs/development/EXECUTABLE_BUILD.md`

---

## 🔐 Licensing System

This application uses a **machine-bound, time-limited license** system.

### First-Time Setup

1. **Get your machine fingerprint:**
   ```bash
   uv run python -c "from leads_gen.licensing.fingerprint import generate_machine_fingerprint; print(generate_machine_fingerprint())"
   ```

2. **Send the fingerprint to the developer** to receive your license key.

3. **Activate your license:**
   ```bash
   # Save the license key to a file
   echo "YOUR_LICENSE_KEY_HERE" > leads_gen/license.key
   ```

### License Information

- Trial licenses: 7-30 days, limited results
- Full licenses: 6-12 months, higher result limits
- Licenses are tied to your specific machine
- No internet required for validation

See `docs/licensing/LICENSING_GUIDE.md` for detailed instructions.

---

## 📂 Project Structure

* `main.py`: Entry point for CLI usage
* `app.py`: Entry point for Streamlit Web UI
* `leads_gen/`: Main application package
  * `scraper/`: Google Maps scraping engine
  * `core/`: Business logic and data processing
  * `licensing/`: License validation system
  * `config/`: Application configuration
  * `utils/`: Shared utilities
* `tools/`: Developer tools (license generation)
* `tests/`: Test files
* `docs/`: Comprehensive documentation
* `output/`: CLI output files (Excel)
* `leads_gen_output/`: UI output files (Excel)