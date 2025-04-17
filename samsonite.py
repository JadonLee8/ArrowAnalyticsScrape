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
import re
import requests


# NOTE ABOUT IDS:
# the product id is expressed as 117224XXXX where the last 4 digits differentiate colors
# so really the color id is a product id, but specifies which color of a product as well

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
# - create class with all information for each product.
# - create object to track dimensions + object for weight?

def sanitize_filename(filename):
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # Remove any leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    return sanitized

# returns a dictionary with product name as the key and a dictionary of color names to color ids as the values.
def get_product_color_ids(driver, pid):
    url = QUICK_VIEW_BASE_URL + pid
    logger.info(f"Loading product details from {url}")
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pre_tag = soup.find('pre') # note can't use a simple cloudscraper or requests get because it tends to set off the bot detector more
    if pre_tag:
        try:
            product_data = json.loads(pre_tag.text)
            product_name = product_data["product"]["productName"]
            sanitized_name = sanitize_filename(product_name)
            
            # Create the directory if it doesn't exist
            base_details_path = os.path.join(RAW_DATA_FOLDER, "Base_Details")
            os.makedirs(base_details_path, exist_ok=True)
            
            with open(os.path.join(base_details_path, f'samsonite_product_details_{sanitized_name}.json'), 'w', encoding='utf-8') as f:
                json.dump(product_data, f, indent=2)
            logger.info(f"Saved base product details raw data for {product_name}")

            # get the color ids
            color_mapping = {}
            variationAttributes = product_data["product"]["variationAttributes"]
            for attribute in variationAttributes:
                if attribute["attributeId"] == "color":
                    colors = attribute["values"]
                    logger.info(f"Found {len(colors)} color IDs for {product_name}")
                    for color in colors:
                        color_id = color["value"]
                        color_name = color["displayValue"]
                        color_mapping[color_name] = color_id
                        logger.info(f"Color ID: {color_id}, Color Name: {color_name}")
            
            return {product_name: color_mapping}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for product {pid}: {str(e)}")
    return None

def append_to_image_urls():
    print("append")
    # TODO: this function takes in a list of image urls, a product brand, name, and color and puts the image urls under that specific heirarchy in a json. the json should key each image with the name of the file which it will be downloaded to later and values of the actual url.

# returns (product brand, product name, product color, product dimensions, product weight)
# calls download images function with list of image urls
# TODO: wrap the json getting stuff and driver.get(url) in a try that checks for a attribute error since that means theres a captcha. if there is a captcha, keep the window open and wait for the user to complete it
def get_product_color_details(driver, color_id):
    pid = color_id[:-4] + "XXXX"
    url = f"{QUICK_VIEW_BASE_URL}{pid}&dwvar_{pid}_color={color_id}"
    logger.info(f"Loading product details from {url}")
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    product_data = json.loads(soup.find('pre').text)["product"]
    product_name = product_data["productName"]
    product_brand = "Samsonite"
    for attribute in product_data["variationAttributes"]:
        if attribute["attributeId"] == "color":
            product_color = attribute["displayValue"]
    
    product_dimensions = product_data["product-dimensions"]
    product_weight = str(product_data["unit-weight"]) + " " + product_data["unit-weight-type"]
    
    # Get all image URLs except for background, highlight, and thumbnail images
    excluded_types = ["pdp-background", "stacked-highlight", "video-thumbnail"]
    image_urls = [
        image["url"]
        for image_type, images in product_data["images"].items()
        if image_type not in excluded_types
        for image in images
    ]
    
    return (product_brand, product_name, product_color, product_dimensions, product_weight)

def main():
    # Create the main raw data folder if it doesn't exist
    os.makedirs(RAW_DATA_FOLDER, exist_ok=True)
    
    pids = get_product_ids()
    driver = setup_driver()
    product_colors = {}
    refetch = 'y' if not os.path.exists(os.path.join(RAW_DATA_FOLDER, 'product_colors.json')) else input("Would you like to refetch product color IDs? (y/n): ")
    
    if refetch.lower() == 'y':
        try:
            for pid in pids:
                result = get_product_color_ids(driver, pid)
                if result:
                    product_colors.update(result)
                time.sleep(1)
        finally:
            driver.quit()
            # Save the final color mappings
        with open(os.path.join(RAW_DATA_FOLDER, 'product_colors.json'), 'w', encoding='utf-8') as f:
            json.dump(product_colors, f, indent=2)
        logger.info(f"Saved color mappings for {len(product_colors)} products")
    else:
        logger.info("Loading existing color mappings")
        # Load existing color mappings from JSON
        with open(os.path.join(RAW_DATA_FOLDER, 'product_colors.json'), 'r', encoding='utf-8') as f:
            product_colors = json.load(f)
        driver.quit()
    driver = setup_driver()
    for product_name, color_mapping in product_colors.items():
        for color_name, color_id in color_mapping.items():
            product_details = get_product_color_details(driver, color_id)
            print(product_details)
            time.sleep(1)
    driver.quit()
    # TODO: write function and call it that appends all the info to a csv


if __name__ == "__main__":
    main()
