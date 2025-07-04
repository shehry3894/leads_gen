import time
import re
import requests
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_social_and_email_links(website_url, retries=2, delay=3):
    social_links = {
        'Facebook': None,
        'Instagram': None,
        'Twitter': None,
        'LinkedIn': None,
        'YouTube': None,
        'Pinterest': None,
        'TikTok': None,
        'Threads': None,
        'Snapchat': None,
        'Emails': []
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"}

    for _ in range(retries):
        try:
            
            logging.info(f'Attempting to scrape social and email links from: {website_url}')
            
            response = requests.get(website_url, headers=headers, timeout=10)
            if response.status_code == 200:
                html = response.text
                patterns = {
                    'Facebook': r'https?://(?:www\.)?facebook\.com/[^\s"\'<>]+',
                    'Instagram': r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+',
                    'Twitter': r'https?://(?:www\.)?twitter\.com/[^\s"\'<>]+',
                    'LinkedIn': r'https?://(?:www\.)?linkedin\.com/[^\s"\'<>]+',
                    'YouTube': r'https?://(?:www\.)?youtube\.com/[^\s"\'<>]+',
                    'Pinterest': r'https?://(?:www\.)?pinterest\.com/[^\s"\'<>]+',
                    'TikTok': r'https?://(?:www\.)?tiktok\.com/[^\s"\'<>]+',
                    'Threads': r'https?://(?:www\.)?threads\.net/[^\s"\'<>]+',
                    'Snapchat': r'https?://(?:www\.)?snapchat\.com/add/[^\s"\'<>]+'
                }

                for platform, pattern in patterns.items():
                    match = re.search(pattern, html)
                    if match:
                        social_links[platform] = match.group()

                emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
                social_links['Emails'] = list(set(emails))
                
                logging.info(f'Successfully scraped social and email links from {website_url}')
                
                break
                
        except Exception as e:
            logging.warning(f"Error scraping {website_url}: {str(e)}")
            time.sleep(delay)

    return social_links

def scrape_business_data(driver, max_results):
    data = []
    results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
    
    logging.info(f'Starting to scrape {len(results)} business results.')

    for i in range(len(results)):
        if max_results is not None and i >= max_results:
            logging.info(f"Reached the max results limit: {max_results}")
            
            break

        try:
            results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
            driver.execute_script("arguments[0].scrollIntoView();", results[i])
            time.sleep(1)
            results[i].click()
            time.sleep(3)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//h1')))

            try:
                name = driver.find_element(By.XPATH, '//h1[contains(@class,"DUwDvf")]').text
            except:
                name = "N/A"

            try:
                address = driver.find_element(By.XPATH, '//button[contains(@aria-label,"Address")]/div/div[2]/div[1]').text
            except:
                address = "N/A"

            try:
                website = driver.find_element(By.XPATH, '//a[contains(@data-item-id,"authority")]').get_attribute('href')
            except:
                website = "N/A"

            try:
                phone = driver.find_element(By.XPATH, "//button[contains(@data-item-id,'phone')]//div[@class='rogA2c ']/div[1]").text
            except:
                phone = "N/A"

            try:
                rating = driver.find_element(By.XPATH, '(//div[contains(@class,"F7nice ")]/span/span)[1]').text
            except:
                rating = "N/A"

            social_links = extract_social_and_email_links(website) if website != "N/A" else {
                'Facebook': None,
                'Instagram': None,
                'Twitter': None,
                'LinkedIn': None,
                'YouTube': None,
                'Pinterest': None,
                'TikTok': None,
                'Threads': None,
                'Snapchat': None,
                'Emails': []
            }
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data.append({
                "Name": name,
                "Address": address,
                "Phone": phone,
                "Website": website,
                "Rating": rating,
                "Facebook": social_links['Facebook'],
                "Instagram": social_links['Instagram'],
                "Twitter": social_links['Twitter'],
                "LinkedIn": social_links['LinkedIn'],
                "YouTube": social_links['YouTube'],
                "Pinterest": social_links['Pinterest'],
                "TikTok": social_links['TikTok'],
                "Threads": social_links['Threads'],
                "Snapchat": social_links['Snapchat'],
                "Emails": ", ".join(social_links['Emails']),
                "Scraped Time": scraped_time
            })

            logging.info(f"Scraped {i+1}. Business: {name}")

        except Exception as e:
            logging.error(f"{i+1}. Failed to scrape business due to: {str(e)}")
            continue
    logging.info(f"Scraping completed. Total businesses scraped: {len(data)}")
    return data