# 📍 Google Maps Scraper & Lead Generator

A comprehensive Python-based web scraper designed to extract business intelligence from Google Maps. This tool automates the process of finding business details, contact information, and social media presence, saving the results directly to Excel.

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

## 🛠️ Installation

### Prerequisites
* Python 3.11 or higher
* Google Chrome installed (for Selenium)
* [`uv` (Python package manager)](https://docs.astral.sh/uv/)

#### Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### Steps (using uv – recommended)
1. **Clone the repository** and navigate to the project folder.
2. **Create and sync a virtual environment with uv:**

```bash
uv sync
```

This will create a `.venv` and install all dependencies from `pyproject.toml`.

3. **Activate the environment:**

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\activate
```

### Legacy steps (pip + venv)
You can still use the older workflow if needed:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```



---

## 💻 Usage

### 1. Web Interface (Recommended)

Launch a user-friendly dashboard in your browser:

```bash
uv run streamlit run app.py
# or
streamlit run app.py
```

**Features:**
- Choose between "Start Fresh" or "Append to Existing" workflows
- Upload existing Excel files to append data
- Visual progress tracking
- Download results directly from the browser

### 2. Command Line Interface

Run the script directly in your terminal:

```bash
uv run python main.py
# or
python main.py
```

**Workflow:**
1. Enter your search query (e.g., "gyms in New York")
2. Specify maximum number of results (or type "all")
3. Wait for scraping to complete
4. Find results in the `output/` directory

**Note:** Trial mode limits results to 3 for quick testing.

### 3. Docker

To run without local Python configuration:

```bash
docker build . -t leads_gen
docker run -p 8501:8501 leads_gen

```

Access the UI at `http://localhost:8501`.

---

## 📦 Creating a Standalone Executable

Build a portable executable using PyInstaller:

```bash
pyinstaller leads_gen.spec
```

The executable will be in the `dist/` directory.

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