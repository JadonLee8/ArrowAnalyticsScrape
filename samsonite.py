from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
import time
from bs4 import BeautifulSoup
import os
import json


# data url: https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=category-position&start=0&sz=60
# sort options: {"options":[{"displayName":"Featured","id":"category-position","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=category-position&start=0&sz=30"},{"displayName":"Best Sellers","id":"best-sellers","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=best-sellers-7-days-revenue-updated&start=0&sz=30"},{"displayName":"Top Rated","id":"top-rated","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=top-rated&start=0&sz=30"},{"displayName":"Price Low To High","id":"price-low-to-high","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=price-low-to-high&start=0&sz=30"},{"displayName":"Price High to Low","id":"price-high-to-low","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=price-high-to-low&start=0&sz=30"},{"displayName":"Product Name A - Z","id":"product-name-ascending","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=product-name-a-z&start=0&sz=30"},{"displayName":"Product Name Z - A","id":"product-name-descending","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=product-name-z-a&start=0&sz=30"}],"ruleId":"category-position"}
QUICK_VIEW_BASE_URL = "https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Product-ShowQuickView?pid="
LUGGAGE_LIST_URL = "https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&start=0&sz=60"
SAMSONITE_BASE_URL = "https://shop.samsonite.com/"

RAW_DATA_FOLDER = "Samsonite_Raw"

def setup_driver():
    # Configure Chrome options
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def has_captcha(html):
    soup = BeautifulSoup(html, 'html.parser')
    captcha_div = soup.find('div', class_='px-captcha-header')
    if captcha_div and "Before we continue..." in captcha_div.text:
        return True
    return False

def get_product_ids():
    # Get all luggage URLs from the page
    max_retries = 5
    retry_count = 0
    html = ""
    driver = None
    
    while retry_count < max_retries:
        refetch = 'y' if not os.path.exists('samsonite_all_luggage.html') else input("Would you like to refetch product IDs? (y/n)")
        if refetch == "y":
            try:
                if driver:
                    driver.quit()
                    time.sleep(2)  # Wait a bit before reopening
                driver = setup_driver()
                
                # Load the webpage
                logger.info("Loading from URL: " + LUGGAGE_LIST_URL)
                driver.get(LUGGAGE_LIST_URL)
                
                # Wait for the page to load
                time.sleep(2)
                
                # Get the page source
                html = driver.page_source
                
                # Check for captcha
                if has_captcha(html):
                    retry_count += 1
                    logger.warning(f"Captcha detected, retrying with new browser window... (Attempt {retry_count}/{max_retries})")
                    time.sleep(5)  # Wait a bit before retrying
                    continue
                
                logger.info("Successfully loaded the page without captcha")
                with open('samsonite_all_luggage.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info("Page source saved to samsonite_page.html")
                break
                
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Max retries reached, giving up")
                    break
            
            if retry_count >= max_retries:
                logger.error("Failed to bypass captcha after maximum retries")
            
            if driver:
                driver.quit()
        else:
            logger.info("Loading from cached file")
            with open('samsonite_all_luggage.html', 'r', encoding='utf-8') as f:
                html = f.read()
            break

    soup = BeautifulSoup(html, 'html.parser')
    product_ids = []
    for product in soup.find_all('div', class_='product'):
        product_id = product.get('data-pid')
        if product_id:
            product_ids.append(product_id)
    logger.info(f"Found {len(product_ids)} product IDs")
    return product_ids

# TODOLIST:
# - if the page shows a captcha, wait until the user solves it and then continue. make some kinda of notification. keep checking for the captcha page to go away.
# - get the color ids then get the product details for each color.
# - opt to not refetch the product details from the page if the file already exists.
# - proper file naming and folder structure.

def get_product_details(driver, pid):
    url = QUICK_VIEW_BASE_URL + pid
    logger.info(f"Loading product details from {url}")
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pre_tag = soup.find('pre') # note can't use a simple cloudscraper or requests get because it tends to set off the bot detector more
    if pre_tag:
        try:
            return json.loads(pre_tag.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for product {pid}: {str(e)}")
            return None
    return None

def main():
    pids = get_product_ids()
    driver = setup_driver()
    try:
        for pid in pids:
            product_data = get_product_details(driver, pid)
            if product_data:
                with open(f'samsonite_product_details_{pid}.json', 'w', encoding='utf-8') as f:
                    json.dump(product_data, f, indent=2)
                logger.info(f"Saved product details for {pid}")
            time.sleep(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
