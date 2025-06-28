# Google Maps Scraper

This Python project is a web scraper for Google Maps. It extracts business information such as name, address, phone number, website, ratings, and social media links from Google Maps results. It also allows users to input search queries, define a limit for the number of results, and save the scraped data to an Excel file.

## Features
- Search for businesses on Google Maps based on user-provided queries (e.g., "gyms in New York").
- Automatically scroll through search results and scrape business data.
- Extract social media links and emails from business websites.
- Save scraped data in an Excel file for further analysis or use.

## Installation

### Prerequisites
Ensure you have the following installed:
- Python 3.x
- pip (Python package manager)

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/DaudRasheed/google_maps_scraper.git

2. **Navigate to the project folder**:
    ```bash
   cd google-maps-scraper

3. **Install dependencies: Create a virtual environment (optional but recommended)**:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows, use venv\Scripts\activate

4. **Install the required libraries**:
    ```bash
    pip install -r requirements.txt

## Usage

1. **Run the script**:
     ```bash
     python main.py

2. **Enter search query**:
  You will be prompted to enter a search term (e.g., "gyms in New York") and specify the number of businesses you want to scrape (or leave blank for no limit).

3. **Output**:
  The scraped data will be saved in an Excel file. The filename will be based on your search term             (e.g., "gyms_in_New_York.xlsx").

**To install all dependencies, use**:
 ```bash
     pip install -r requirements.txt
  ```


### RUN via docker
1. Build the image
``` bash
docker build . -t leads_gen
```
2. Run the image
```bash
docker run -p 8501:8501 leads_gen
```
2. Visit http://localhost:8501/


