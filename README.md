# 📍 Google Maps Scraper & Lead Generator

A comprehensive Python-based web scraper designed to extract business intelligence from Google Maps. This tool automates the process of finding business details, contact information, and social media presence, saving the results directly to Excel.

## 🚀 Features

* **Multi-Interface:** Choose between a simple Command Line (CLI) or a modern Streamlit Web UI.
* **Deep Data Extraction:** Scrapes name, address, phone number, website, and ratings.
* **Contact Discovery:** Automatically crawls business websites to find email addresses and social media links (LinkedIn, Facebook, Instagram, etc.).
* **Custom Limits:** Define exactly how many leads you want to collect.
* **Automated Export:** Generates clean, formatted `.xlsx` files automatically.
* **Docker Ready:** Easily containerized for consistent deployment.

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
python -m streamlit run app.py

```

### 2. Command Line Interface

Run the script directly in your terminal:

```bash
python main.py

```

* Follow the prompts to enter your search query (e.g., "Dental clinics in London").
* Results will be saved in the `output/` directory.

### 3. Docker

To run without local Python configuration:

```bash
docker build . -t leads_gen
docker run -p 8501:8501 leads_gen

```

Access the UI at `http://localhost:8501`.

---

## 📦 Creating a Standalone Executable

If you need to build a portable `.exe` for Windows, use the following command (requires `streamlit-desktop-app`):

```bash
streamlit-desktop-app build app.py --name leads_gen --pyinstaller-options --onefile \
--clean \
--console \
--paths ./ \
--hidden-import scraper \
--hidden-import utils \
--add-data "scraper:scraper" \
--add-data "utils:utils" \
--add-data "input:input" \
--collect-all streamlit \
--collect-all openpyxl \
--collect-all pandas \
--collect-all requests \
--collect-all selenium \
--collect-all webdriver_manager \
--collect-all xlsxwriter
```

---

## 📂 Project Structure

* `main.py`: Entry point for CLI usage.
* `app.py`: Entry point for the Streamlit UI.
* `scraper/`: Contains the Selenium logic for Google Maps interaction.
* `utils/`: Contains logic for website crawling and social link extraction.
* `output/`: Default folder for your generated Excel leads.