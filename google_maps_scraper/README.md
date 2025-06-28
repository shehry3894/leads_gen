
# 🗺️ Google Maps Scraper

This project is a Python-based web scraper for **Google Maps**. It allows users to extract detailed business information such as name, address, phone, website, ratings, emails, and social media links.

It supports both:
- **Command Line Interface (CLI)** via `main.py`
- **Web Interface** via **Streamlit** using `app.py`

---

## ✨ Features

- 🔍 Search for businesses by custom query (e.g., "gyms in New York")
- 📥 Automatically scroll and extract multiple results
- 🌐 Extract email + social links (Facebook, Instagram, etc.) from business websites
- 📄 Output data into Excel files (in `/output/` folder)
- 🔁 Updates existing rows if duplicate businesses are found
- 🔗 Adds Google Maps short links to each entry

---

## 🧰 Folder Structure

google_maps_scraper/
│
├── input/ # User input and config
├── scraper/ # Scraping modules (driver, scroll, zooming, etc.)
├── output/ # Saved Excel results
├── app.py # Streamlit app
├── main.py # CLI script
├── Dockerfile # Docker container config
├── requirements.txt # Python dependencies
├── environment.yml # (optional Conda environment)
└── README.md # You’re reading it 🙂

---

## ⚙️ Local Setup (No Docker)

### ✅ Requirements

- Python 3.9 or later
- pip

### 🔧 Installation

```bash
git clone https://github.com/DaudRasheed/google_maps_scraper.git
cd google_maps_scraper

# (Optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### ▶️ Run CLI Script

```bash
python main.py
```

You'll be prompted to enter a search term and result limit.  
Output will be saved as an Excel file in `/output`.

---

### 🖥️ Run Streamlit Web App

```bash
streamlit run app.py
```

Visit: http://localhost:8501  
Enter your query, start scraping, download results.

---

## 🐳 Docker Usage (Recommended for Consistency)

### 🧱 Step 1: Build Docker Image

```bash
docker build -t gmaps-scraper .
```

### ▶️ Step 2: Run Streamlit App in Docker

```bash
docker run -it --rm -p 8501:8501 gmaps-scraper
```

Open browser at: http://localhost:8501

---

### 💾 Optional: Mount Output Folder

To save Excel files to your local machine:

**On macOS/Linux:**
```bash
docker run -it --rm -v ${PWD}/output:/app/output -p 8501:8501 gmaps-scraper
```

**On Windows CMD:**
```bash
docker run -it --rm -v %cd%/output:/app/output -p 8501:8501 gmaps-scraper
```

---

### ⚙️ Run CLI Mode in Docker (instead of Streamlit)

```bash
docker run -it --rm gmaps-scraper python main.py
```
