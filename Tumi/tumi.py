import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
from loguru import logger
import os
import json

# CAPTCHA TYPE: PX

ALL_LUGGAGE_URL = "https://www.tumi.com/c/luggage/carryon-luggage/?pageNumber=6"
RAW_DATA_FOLDER = "Tumi_Raw"

def has_captcha(html):
    soup = BeautifulSoup(html, 'html.parser')
    captcha_div = soup.find('div', class_='px-captcha-header')
    if captcha_div and "Before we continue..." in captcha_div.text:
        return True
    return False

def fetch_html(driver, url):
    driver.get(url)
    time.sleep(2)  # Wait for the page to load
    html = driver.page_source
    # Check for captcha
    if has_captcha(html):
        logger.warning("Captcha detected. Waiting 2 minutes for user to solve it...")
        time.sleep(120)  # Wait for 2 minutes
        html = driver.page_source
        if has_captcha(html):
            logger.error("Captcha still present after waiting.")
            raise Exception("Captcha still present after waiting.")
    return html

def find_app_script_of_type(soup, type_name):
    script_tags = soup.find_all("script", type="application/ld+json")
    for script_tag in script_tags:
        if script_tag.string:
            json_data = json.loads(script_tag.string)
            if json_data.get("@type") == type_name:
                logger.info(f"Found a script tag with type '{type_name}'")
                return json_data
    logger.warning(f"No script tag found with type '{type_name}'")
    return None

def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")
    else:
        logger.info(f"Directory already exists: {directory}")

def fetch_base_luggage_urls(driver):
    if os.path.exists(os.path.join(RAW_DATA_FOLDER, "tumi_base_urls.json")):
        user_input = input("tumi_base_urls.json already exists. Do you want to refetch product base URLs? (y/n): ").strip().lower()
        if user_input != "y":
            logger.info("Loading data from existing tumi_base_urls.json")
            with open(os.path.join(RAW_DATA_FOLDER, "tumi_base_urls.json"), "r") as file:
                return json.load(file)
    html = fetch_html(driver, ALL_LUGGAGE_URL)
    soup = BeautifulSoup(html, "html.parser")
    json_data = find_app_script_of_type(soup, "ItemList")
    num_items = json_data.get("numberOfItems")
    logger.info(f"Found {num_items} items in the JSON data")
    json.dump(json_data, open(os.path.join(RAW_DATA_FOLDER, "tumi_base_urls.json"), "w"), indent=2)
    logger.info("Data successfully written to tumi_base_urls.json")
    return json_data

def get_base_urls_list(json_data):
    base_urls = {}
    for item in json_data.get("itemListElement", []):
        base_urls.update({item.get("name"): item.get("url")})
    logger.info(f"Extracted {len(base_urls)} base URLs")
    return base_urls

def main():
    create_directory_if_not_exists(RAW_DATA_FOLDER)
    driver = uc.Chrome(headless=False, use_subprocess=False)
    base_urls_json = fetch_base_luggage_urls(driver)
    base_urls = get_base_urls_list(base_urls_json)
    
    driver.quit()

if __name__ == "__main__":
    main()