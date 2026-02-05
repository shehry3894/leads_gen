import time
import re
import requests
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from leads_gen.utils.wait_utils import SmartWait
from leads_gen.config.settings import WAIT_CONFIG

logger = logging.getLogger("leads_gen")


def generate_whatsapp_link(phone_number):
    if phone_number and phone_number != 'N/A':
        wa_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        return f'https://wa.me/{wa_number}'
    return 'N/A'


def clean_emails(emails):
    cleaned = set()
    dummy_keywords = ['example', 'test', 'dummy', 'ed436f5053144538958ad06a5005e99a',
                      ' c183baa23371454f99f417f6616b724d', 'no-reply', 'noreply', 'abc', 'xyz', 'yourdomain']

    for email in emails:
        email_lower = email.lower()
        if any(keyword in email_lower for keyword in dummy_keywords):
            continue
        if re.fullmatch(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', email):
            cleaned.add(email_lower)

    return list(cleaned)


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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    }

    patterns = {
        'Facebook': "https?://(?:www\\.)?facebook\\.com/[^\\s\"'<>]+",
        'Instagram': "https?://(?:www\\.)?instagram\\.com/[^\\s\"'<>]+",
        'Twitter': "https?://(?:www\\.)?twitter\\.com/[^\\s\"'<>]+",
        'LinkedIn': "https?://(?:www\\.)?linkedin\\.com/[^\\s\"'<>]+",
        'YouTube': "https?://(?:www\\.)?youtube\\.com/[^\\s\"'<>]+",
        'Pinterest': "https?://(?:www\\.)?pinterest\\.com/[^\\s\"'<>]+",
        'TikTok': "https?://(?:www\\.)?tiktok\\.com/[^\\s\"'<>]+",
        'Threads': "https?://(?:www\\.)?threads\\.net/[^\\s\"'<>]+",
        'Snapchat': "https?://(?:www\\.)?snapchat\\.com/add/[^\\s\"'<>]+"
    }

    for _ in range(retries):
        try:
            logger.info(f'Attempting to scrape social and email links from: {website_url}')
            response = requests.get(website_url, headers=headers, timeout=10)
            if response.status_code == 200:
                html = response.text
                for platform, pattern in patterns.items():
                    match = re.search(pattern, html)
                    if match:
                        social_links[platform] = match.group()

                raw_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
                social_links['Emails'] = clean_emails(raw_emails)
                logger.info(f'Successfully scraped social and email links from {website_url}')
                break
        except Exception as e:
            logger.warning(f'Error scraping {website_url}: {str(e)}')
            time.sleep(delay)

    return social_links


def scrape_business_data(driver, max_results):
    data = []
    smart_wait = SmartWait(driver)
    
    # Wait for initial results to load
    results = smart_wait.wait_for_elements(
        By.XPATH,
        '//div[contains(@class, "Nv2PK")]',
        timeout=WAIT_CONFIG.get('search_results', 15),
        min_count=1
    )
    
    if not results:
        logger.error('No business results found')
        return data
    
    logger.info(f'Starting to scrape {len(results)} business results.')

    for i in range(len(results)):
        if max_results is not None and i >= max_results:
            logger.info(f'Reached the max results limit: {max_results}')
            break
        try:
            # Re-fetch results to avoid stale element references
            results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
            if i >= len(results):
                logger.warning(f'Result {i} no longer available')
                continue
            
            # Scroll element into view
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', results[i])
            time.sleep(0.3)  # Brief pause for scroll animation
            
            # Click with retry logic
            def click_business_card():
                results[i].click()
                return True
            
            success, _ = smart_wait.retry_with_backoff(
                click_business_card,
                max_attempts=3
            )
            
            if not success:
                logger.warning(f'Failed to click business card {i+1}')
                continue
            
            # Wait for info panel to load (h1 is the business name)
            info_timeout = WAIT_CONFIG.get('info_panel', 10)
            info_panel = smart_wait.wait_for_element(
                By.XPATH,
                '//h1',
                timeout=info_timeout,
                condition='presence'
            )
            
            if not info_panel:
                logger.warning(f'Info panel did not load for business {i+1}')
                continue

            # Extract business name with multiple fallback selectors
            name = "N/A"
            name_selectors = [
                (By.XPATH, '//h1[contains(@class,"DUwDvf")]'),
                (By.XPATH, '//h1[@class="DUwDvf lfPIob"]'),
                (By.CSS_SELECTOR, 'h1.DUwDvf'),
                (By.XPATH, '//div[@role="main"]//h1'),
                (By.TAG_NAME, 'h1'),
            ]
            for by_type, selector in name_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2, condition='visibility')
                if elem and elem.text.strip():
                    name = elem.text.strip()
                    logger.debug(f'Found name with {by_type}: {selector}')
                    break
            
            # Extract address with multiple fallback selectors
            address = "N/A"
            address_selectors = [
                (By.XPATH, '//button[contains(@aria-label,"Address")]/div/div[2]/div[1]'),
                (By.XPATH, '//button[@data-item-id="address"]//div[contains(@class,"fontBodyMedium")]'),
                (By.XPATH, '//button[@data-tooltip="Copy address"]'),
                (By.XPATH, '//div[contains(@aria-label,"Address:")]'),
            ]
            for by_type, selector in address_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem and elem.text.strip():
                    address = elem.text.strip()
                    logger.debug(f'Found address with {by_type}: {selector}')
                    break
            
            # Extract website
            website = "N/A"
            website_selectors = [
                (By.XPATH, '//a[contains(@data-item-id,"authority")]'),
                (By.XPATH, '//a[@data-item-id="authority"]'),
                (By.XPATH, '//a[contains(@aria-label,"Website:")]'),
            ]
            for by_type, selector in website_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem:
                    href = elem.get_attribute('href')
                    if href and href.strip():
                        website = href
                        logger.debug(f'Found website with {by_type}: {selector}')
                        break
            
            # Extract phone
            phone = "N/A"
            phone_selectors = [
                (By.XPATH, "//button[contains(@data-item-id,'phone')]//div[contains(@class,'fontBodyMedium')]"),
                (By.XPATH, "//button[@data-tooltip='Copy phone number']"),
                (By.XPATH, "//button[contains(@aria-label,'Phone:')]"),
            ]
            for by_type, selector in phone_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem and elem.text.strip():
                    phone = elem.text.strip()
                    logger.debug(f'Found phone with {by_type}: {selector}')
                    break
            
            # Extract rating
            rating = "N/A"
            rating_selectors = [
                (By.XPATH, '//div[contains(@class,"F7nice")]//span[@role="img"]'),
                (By.XPATH, '//div[contains(@aria-label,"stars")]'),
                (By.XPATH, '//span[contains(@aria-label,"stars")]'),
            ]
            for by_type, selector in rating_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem:
                    # Try to get aria-label first
                    aria_label = elem.get_attribute('aria-label')
                    if aria_label:
                        match = re.search(r'(\d+\.?\d*)\s+star', aria_label, re.IGNORECASE)
                        if match:
                            rating = match.group(1)
                            logger.debug(f'Found rating in aria-label: {rating}')
                            break
                    # Otherwise try text
                    if elem.text.strip():
                        rating = elem.text.strip()
                        logger.debug(f'Found rating text: {rating}')
                        break
            
            # Extract review count with improved logic
            review_count = "N/A"
            review_selectors = [
                (By.XPATH, '//div[contains(@class,"F7nice")]//span[@aria-label]'),
                (By.XPATH, '//button[contains(@aria-label,"reviews")]'),
                (By.XPATH, '//span[contains(@aria-label,"reviews")]'),
                (By.XPATH, '//div[contains(@aria-label,"reviews")]'),
            ]
            for by_type, selector in review_selectors:
                elem = smart_wait.wait_for_element(by_type, selector, timeout=2)
                if elem:
                    aria_label = elem.get_attribute('aria-label')
                    if aria_label:
                        # Extract number from aria-label like "4.5 stars 123 reviews" or "123 reviews"
                        match = re.search(r'(\d+(?:,\d+)*)\s+reviews?', aria_label, re.IGNORECASE)
                        if match:
                            review_count = match.group(1).replace(',', '')
                            logger.debug(f'Found review count: {review_count}')
                            break
                    # Also try button text
                    if elem.text and 'review' in elem.text.lower():
                        match = re.search(r'(\d+(?:,\d+)*)', elem.text)
                        if match:
                            review_count = match.group(1).replace(',', '')
                            logger.debug(f'Found review count in text: {review_count}')
                            break
            
            short_link = driver.current_url  # Get current Google Maps short URL

            social_links = extract_social_and_email_links(website) if website != "N/A" else {
                'Facebook': None, 'Instagram': None, 'Twitter': None, 'LinkedIn': None,
                'YouTube': None, 'Pinterest': None, 'TikTok': None, 'Threads': None,
                'Snapchat': None, 'Emails': []
            }

            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            whatsapp_link = generate_whatsapp_link(phone)

            data.append({
                'Name': name,
                'Google Maps Link': short_link,
                'Address': address,
                'Phone': phone,
                'WhatsApp': whatsapp_link,
                'Website': website,
                'Rating': rating,
                'Review Count': review_count,
                'Facebook': social_links['Facebook'],
                'Instagram': social_links['Instagram'],
                'Twitter': social_links['Twitter'],
                'LinkedIn': social_links['LinkedIn'],
                'YouTube': social_links['YouTube'],
                'Pinterest': social_links['Pinterest'],
                'TikTok': social_links['TikTok'],
                'Threads': social_links['Threads'],
                'Snapchat': social_links['Snapchat'],
                'Emails': ", ".join(social_links['Emails']),
                'Scraped Time': scraped_time

            })
            logger.info(f'Scraped {i + 1}. Business: {name}')
        except Exception as e:
            logger.error(f'{i + 1}. Failed to scrape business due to: {str(e)}')
            continue

    logger.info(f'Scraping completed. Total businesses scraped: {len(data)}')
    return data
