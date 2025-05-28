import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
import re

# Configure loguru
logger.add("away_travel.log", rotation="1 day", retention="7 days", level="INFO")

COLLECTION_URL = "https://www.awaytravel.com/collections/carry-on-luggage"
DATA_FOLDER = "AwayTravel_Data"
OUTPUT_JSON   = "urls.json"
SCROLL_PAUSE  = 1             # seconds between scroll checks
PAGE_LOAD_WAIT = 2          # seconds to wait for page load

def load_cached_urls():
    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            urls = json.load(f)
            logger.success(f"Loaded variants for {len(urls)} products from cache")
            return urls
    except FileNotFoundError:
        logger.warning("No cached URLs found")
        return None

def collect_product_urls():
    logger.info("Starting URL collection process")
    driver = uc.Chrome(headless=False, use_subprocess=False)  # Set to False for headed mode

    try:
        logger.info(f"Navigating to {COLLECTION_URL}")
        driver.get(COLLECTION_URL)

        # Scroll until no new content loads
        logger.info("Scrolling to load all products")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:   # reached the bottom
                break
            last_height = new_height

        # Find all variant pickers and their color variants
        logger.info("Collecting variant URLs")
        variant_pickers = driver.find_elements(By.CSS_SELECTOR, 'variant-picker')
        
        all_variants = {}
        for picker in variant_pickers:
            # Get the product type from the parent main-product element
            try:
                product_type = picker.find_element(
                    By.XPATH,
                    './ancestor::main-product//a[contains(@class, "h6")]'
                ).text.strip()
            except Exception as e:
                logger.error(f"Could not find product type for a variant picker: {str(e)}")
                continue

            # Find all radio inputs within this variant picker
            radio_inputs = picker.find_elements(
                By.CSS_SELECTOR,
                'swiper-slide input[type="radio"][data-product-url]'
            )
            
            # Extract URLs for this product type
            variant_urls = {
                "https://www.awaytravel.com" + input.get_attribute("data-product-url")
                if input.get_attribute("data-product-url").startswith("/")
                else input.get_attribute("data-product-url")
                for input in radio_inputs
            }
            
            if variant_urls:
                all_variants[product_type] = list(variant_urls)
                logger.info(f"Found {len(variant_urls)} variants for {product_type}")

        # Persist to JSON
        logger.info(f"Saving variants for {len(all_variants)} products to {OUTPUT_JSON}")
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(all_variants, f, indent=2)

        logger.success(f"Saved variants for {len(all_variants)} products to {OUTPUT_JSON}")
        return all_variants

    finally:
        logger.info("Closing browser session")
        driver.quit()

def get_product_data(url):
    logger.info(f"Getting product data for {url}")
    driver = uc.Chrome(headless=False, use_subprocess=False)  # Set to False for headed mode
    driver.get(url)
    time.sleep(PAGE_LOAD_WAIT)

    # wait for body to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # get color
    color = driver.find_element(By.XPATH, '//span[@data-selected-value]').text.strip()
    product_name = driver.find_element(By.XPATH, '//main-product[1]//section//div//h1').text.strip()
    
    size_attributes = driver.find_element(By.XPATH, "//below-the-fold-listener//section//div//div[3]//div//div//div//p").get_attribute("innerHTML")
    size_attributes = re.split(r'<br>|</strong>', size_attributes)
    dimensions = size_attributes[1]
    weight = size_attributes[5]
    return product_name, color, dimensions, weight

if __name__ == "__main__":
    logger.info("Starting Away Travel scraper")
    
    # Check if we have cached URLs
    cached_urls = load_cached_urls()
    all_variants = []
    if cached_urls:
        # Ask user if they want to use cached URLs or fetch new ones
        while True:
            choice = input("Would you like to:\n1. Use cached product URLs\n2. Fetch new product URLs\nEnter 1 or 2: ").strip()
            if choice in ["1", "2"]:
                break
            logger.warning("Invalid choice. Please enter 1 or 2.")

        if choice == "1":
            logger.info("Using cached URLs")
            all_variants = cached_urls
        else:
            logger.info("Fetching new URLs")
            all_variants = collect_product_urls()
    else:
        logger.info("No cached URLs found. Fetching new URLs...")
        all_variants = collect_product_urls()

    # Test get_product_data with first URL
    if all_variants:
        first_product_type = next(iter(all_variants))
        first_url = all_variants[first_product_type][0]
        logger.info(f"Testing get_product_data with URL: {first_url}")
        product_name, color, dimensions, weight = get_product_data(first_url)
        logger.info(f"Product Name: {product_name}")
        logger.info(f"Color: {color}")
        logger.info(f"Dimensions: {dimensions}")
        logger.info(f"Weight: {weight}")
    
    logger.success("Scraping completed successfully")

