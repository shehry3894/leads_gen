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

    scraped_links = set()  # Track which businesses we've already scraped to avoid duplicates
    
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
            
            # STEP 1: Extract the expected business name from the list card BEFORE clicking
            expected_name = None
            try:
                # Try to get business name from the list item
                name_elem = results[i].find_element(By.CSS_SELECTOR, 'div.fontHeadlineSmall')
                expected_name = name_elem.text.strip() if name_elem else None
                logger.debug(f'Expected business name from list: {expected_name}')
            except Exception as e:
                logger.debug(f'Could not get expected name from list item: {str(e)}')
            
            # Get the aria-label or href to identify this business uniquely
            try:
                link_elem = results[i].find_element(By.TAG_NAME, 'a')
                business_href = link_elem.get_attribute('href') if link_elem else None
                business_label = results[i].get_attribute('aria-label') or ''
                
                # If we didn't get expected_name, try from aria-label
                if not expected_name and business_label:
                    expected_name = business_label.split('·')[0].strip()
                
                # Create a unique identifier
                unique_id = business_href or business_label
                
                # Skip if we've already scraped this business
                if unique_id and unique_id in scraped_links:
                    logger.info(f'Skipping duplicate business at index {i}: {business_label[:50]}...')
                    continue
                    
            except Exception as e:
                logger.debug(f'Could not get unique ID for result {i}: {str(e)}')
                unique_id = None
            
            # Scroll element into view
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', results[i])
            time.sleep(0.3)  # Brief pause for scroll animation
            
            # STEP 2: Click the business card
            def click_business_card():
                # Re-fetch the element to avoid stale reference
                fresh_results = driver.find_elements(By.XPATH, '//div[contains(@class, "Nv2PK")]')
                if i < len(fresh_results):
                    fresh_results[i].click()
                    return True
                return False
            
            success, _ = smart_wait.retry_with_backoff(
                click_business_card,
                max_attempts=3
            )
            
            if not success:
                logger.warning(f'Failed to click business card {i+1}')
                continue
                
            # Mark this business as scraped
            if unique_id:
                scraped_links.add(unique_id)
            
            # STEP 3: Wait for the info panel container to appear
            info_panel = smart_wait.wait_for_element(
                By.XPATH,
                '//div[contains(@class, "m6QErb")]',
                timeout=WAIT_CONFIG.get('info_panel', 10),
                condition='presence'
            )
            
            if not info_panel:
                logger.warning(f'Info panel did not load for business {i+1}')
                continue
            
            # STEP 4: Wait for the SPECIFIC business name to appear in the detail panel
            name = "N/A"
            if expected_name:
                logger.debug(f'Waiting for expected name "{expected_name}" to appear in detail panel...')
                # Wait for h1 with the expected name to appear
                max_wait_for_name = 15  # seconds
                name_found = False
                
                for attempt in range(max_wait_for_name):
                    try:
                        h1_elements = driver.find_elements(By.XPATH, '//div[contains(@class, "m6QErb")]//h1[contains(@class,"DUwDvf")]')
                        for h1 in h1_elements:
                            h1_text = h1.text.strip()
                            if h1_text and h1_text.lower() != "results" and expected_name.lower() in h1_text.lower():
                                name = h1_text
                                name_found = True
                                logger.info(f'✓ Expected name found in detail panel: {name}')
                                break
                        
                        if name_found:
                            break
                        
                        time.sleep(1)
                    except Exception as e:
                        logger.debug(f'Error checking for name: {str(e)}')
                        time.sleep(1)
                
                if not name_found:
                    logger.warning(f'Expected name "{expected_name}" did not appear after {max_wait_for_name}s, proceeding anyway')
            
            # STEP 5: If we still don't have the name, try standard extraction
            if name == "N/A":
                name_selectors = [
                    (By.XPATH, '//div[contains(@class, "m6QErb")]//h1[contains(@class,"DUwDvf")]'),
                    (By.XPATH, '//div[@role="main"]//h1[contains(@class,"DUwDvf")]'),
                    (By.CSS_SELECTOR, 'h1.DUwDvf.lfPIob'),
                ]
                for by_type, selector in name_selectors:
                    elem = smart_wait.wait_for_element(by_type, selector, timeout=3, condition='visibility')
                    if elem and elem.text.strip() and elem.text.strip().lower() != "results":
                        name = elem.text.strip()
                        break
            
            # Final check
            if name in ["N/A", "Results"]:
                logger.warning(f'Business {i+1}: Could not extract valid name, got "{name}"')
            
            # STEP 6: Wait a bit more to ensure ALL details are loaded
            logger.debug(f'Name confirmed, waiting for all details to load...')
            time.sleep(2)  # Extra wait for address, phone, website, etc. to load
            
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
            
            # Double-check: Skip if we've already scraped this URL
            if short_link in scraped_links:
                logger.warning(f'Duplicate detected by URL: {short_link} - skipping')
                continue
            
            # Mark this URL as scraped
            scraped_links.add(short_link)

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
            
            # Log detailed business information
            logger.info(f'✓ Scraped business {i + 1}/{len(results)}: {name}')
            logger.info(f'  └─ Google Maps: {short_link}')
            logger.info(f'  └─ Address: {address}')
            logger.info(f'  └─ Phone: {phone}')
            logger.info(f'  └─ Website: {website}')
            logger.info(f'  └─ Rating: {rating} ({review_count} reviews)')
        except Exception as e:
            logger.error(f'{i + 1}. Failed to scrape business due to: {str(e)}')
            continue

    logger.info(f'Scraping completed. Total businesses scraped: {len(data)}')
    return data
