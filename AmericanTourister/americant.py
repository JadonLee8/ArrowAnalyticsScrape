import undetected_chromedriver as uc
from loguru import logger
import time
from bs4 import BeautifulSoup
import os
import json
import re
import requests
import csv

# NOTE: this script was originally written for samsonite. turns out, american tourist uses the exact same infrastrucutre!

# NOTE ABOUT IDS:
# the product id is expressed as 117224XXXX where the last 4 digits differentiate colors
# so really the color id is a product id, but specifies which color of a product as well

# data url: https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=category-position&start=0&sz=60
# sort options: {"options":[{"displayName":"Featured","id":"category-position","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=category-position&start=0&sz=30"},{"displayName":"Best Sellers","id":"best-sellers","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=best-sellers-7-days-revenue-updated&start=0&sz=30"},{"displayName":"Top Rated","id":"top-rated","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=top-rated&start=0&sz=30"},{"displayName":"Price Low To High","id":"price-low-to-high","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=price-low-to-high&start=0&sz=30"},{"displayName":"Price High to Low","id":"price-high-to-low","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=price-high-to-low&start=0&sz=30"},{"displayName":"Product Name A - Z","id":"product-name-ascending","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=product-name-a-z&start=0&sz=30"},{"displayName":"Product Name Z - A","id":"product-name-descending","url":"https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=product-name-z-a&start=0&sz=30"}],"ruleId":"category-position"}
QUICK_VIEW_BASE_URL = "https://shop.americantourister.com/on/demandware.store/Sites-americantourister-Site/en_US/Product-ShowQuickView?pid="
LUGGAGE_LIST_URL = "https://shop.americantourister.com/on/demandware.store/Sites-americantourister-Site/en_US/Search-UpdateGrid?cgid=carry-on&start=0&sz=60"
SAMSONITE_BASE_URL = "https://shop.americantourister.com/"

RAW_DATA_FOLDER = "American_Tourister_Raw" 

def setup_driver():
    driver = uc.Chrome(headless=False, use_subprocess=False)
    return driver

def has_captcha(html):
    soup = BeautifulSoup(html, 'html.parser')
    captcha_div = soup.find('div', class_='px-captcha-header')
    if captcha_div and "Before we continue..." in captcha_div.text:
        return True
    return False

def get_product_ids():
    # Get all luggage URLs from the page
    html = ""
    driver = None
    
    refetch = 'y' if not os.path.exists('americant_all_luggage.html') else input("Would you like to refetch product IDs? (y/n)")
    if refetch == "y":
        try:
            driver = setup_driver()
            
            # Load the webpage
            logger.info("Loading from URL: " + LUGGAGE_LIST_URL)
            html = fetch_html(driver, LUGGAGE_LIST_URL)
            
            logger.info("Successfully loaded the page without captcha")
            with open('americant_all_luggage.html', 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info("Page source saved to americant_all_luggage.html")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")

        if driver:
            driver.quit()
    else:
        logger.info("Loading from cached file")
        with open('americant_all_luggage.html', 'r', encoding='utf-8') as f:
            html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    product_ids = []
    for product in soup.find_all('div', class_='product'):
        product_id = product.get('data-pid')
        if product_id:
            product_ids.append(product_id)
    logger.info(f"Found {len(product_ids)} product IDs")
    return product_ids

# TODOLIST:
# - more elegent dimension/weight formatting
# - image download functionality
# - undetectable driver? https://github.com/UltrafunkAmsterdam/undetected-chromedriver

def fetch_html(driver, url):
    driver.get(url)
    time.sleep(2)  # Wait for the page to load
    html = driver.page_source
    # Check for captcha
    if has_captcha(html):
        logger.warning("Captcha detected. Waiting 2 minutes for user to solve it...")
        time.sleep(60)  # Wait for 1 minute
        html = driver.page_source
        if has_captcha(html):
            logger.error("Captcha still present after waiting.")
            raise Exception("Captcha still present after waiting.")
    return html

def sanitize_filename(filename):
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # Remove any leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    return sanitized

# returns a dictionary with product name as the key and a dictionary of color names to color ids as the values
def get_product_color_ids(driver, pid):
    url = QUICK_VIEW_BASE_URL + pid
    logger.info(f"Loading product details from {url}")
    html = fetch_html(driver, url)
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
            
            with open(os.path.join(base_details_path, f'americant_product_details_{sanitized_name}.json'), 'w', encoding='utf-8') as f:
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

def append_to_image_urls(images, brand, name, color):
    # Define the path for the JSON file
    json_path = os.path.join(RAW_DATA_FOLDER, "image_urls.json")

    # Load existing data if the JSON file already exists
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            image_data = json.load(f)
    else:
        image_data = {}

    # Navigate the hierarchy: brand -> name -> color
    if brand not in image_data:
        image_data[brand] = {}
    if name not in image_data[brand]:
        image_data[brand][name] = {}
    if color not in image_data[brand][name]:
        image_data[brand][name][color] = []

    # Append the new image URLs to the list for the specific color
    image_data[brand][name][color].extend(images)

    # Remove duplicates while preserving order
    image_data[brand][name][color] = list(dict.fromkeys(image_data[brand][name][color]))

    # Save the updated image data to the JSON file
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(image_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save image URLs to {json_path}: {str(e)}")

    logger.info(f"Appended {len(images)} image URLs under {brand} -> {name} -> {color} in {json_path}")

# returns (product brand, product name, product color, product dimensions, product weight)
# calls download images function with list of image urls
def get_product_color_details(driver, color_id):
    pid = color_id[:-4] + "XXXX"
    url = f"{QUICK_VIEW_BASE_URL}{pid}&dwvar_{pid}_color={color_id}"
    logger.info(f"Loading product details from {url}")
    # Check if the JSON file for this color ID already exists
    # Search for the JSON file in the entire American_Tourister_RAW directory
    json_file_path = None
    product_data = ""
    for root, _, files in os.walk(RAW_DATA_FOLDER):
        for file in files:
            if sanitize_filename(color_id) in file and file.endswith(".json"):
                json_file_path = os.path.join(root, file)
                break
        if json_file_path:
            break
    if json_file_path is not None and os.path.exists(json_file_path):
        logger.info(f"JSON file for color ID {color_id} already exists. Loading from file.")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            product_data = json.load(f)
    else:
        driver.get(url)
        time.sleep(2)
        html = driver.page_source

        # Check for captcha
        if has_captcha(html):
            logger.warning("Captcha detected. Waiting 2 minutes for user to solve it...")
            time.sleep(120)  # Wait for 2 minutes
            html = driver.page_source
            if has_captcha(html):
                logger.error("Captcha still present after waiting. Exiting gracefully.")
                return None

        soup = BeautifulSoup(html, 'html.parser')
        product_data = json.loads(soup.find('pre').text)["product"]
    product_name = product_data["productName"]
    product_brand = "American Tourister"
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
    append_to_image_urls(image_urls, product_brand, product_name, product_color)
    # Create the directory structure for saving the product data
    product_folder = os.path.join(RAW_DATA_FOLDER, sanitize_filename(product_name), sanitize_filename(product_color))
    os.makedirs(product_folder, exist_ok=True)

    # Save the product data as a JSON file
    json_file_path = os.path.join(product_folder, f"americant_{color_id}_{sanitize_filename(product_name)}_{sanitize_filename(product_color)}_raw.json")
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(product_data, f, indent=2)
        logger.info(f"Saved product data to {json_file_path}")
    except Exception as e:
        logger.error(f"Failed to save product data to {json_file_path}: {str(e)}")
    return (product_brand, product_name, product_color, product_dimensions, product_weight)

def main():
    # Create the main raw data folder if it doesn't exist
    os.makedirs(RAW_DATA_FOLDER, exist_ok=True)
    
    # Define CSV headers and base path
    headers = ['Brand', 'Product Name', 'Color', 'Dimensions', 'Weight']
    base_csv_path = os.path.join(RAW_DATA_FOLDER, 'american_tourister_data.csv')
    
    # Find an available filename
    csv_path = base_csv_path
    counter = 1
    while os.path.exists(csv_path):
        csv_path = os.path.join(RAW_DATA_FOLDER, f'american_tourister_data({counter}).csv')
        counter += 1
    
    # Create new CSV with headers
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
    
    logger.info(f"Created new CSV file: {csv_path}")
    
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
            if product_details:  # Only append if we got valid details
                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(product_details)
                logger.info(f"Appended details for {product_name} - {color_name} to CSV")
    driver.quit()


if __name__ == "__main__":
    main()
