import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger

# Configure loguru
logger.add("away_travel.log", rotation="1 day", retention="7 days", level="INFO")

COLLECTION_URL = "https://www.awaytravel.com/collections/carry-on-luggage"
OUTPUT_JSON   = "urls.json"
SCROLL_PAUSE  = 1             # seconds between scroll checks
PAGE_LOAD_WAIT = 10          # seconds to wait for page load

def process_product_page(driver, url):
    try:
        logger.info(f"Processing product page: {url}")
        driver.get(url)
        
        # Wait for the page to load
        WebDriverWait(driver, PAGE_LOAD_WAIT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get the product type from the h1 element
        try:
            product_type = driver.find_element(
                By.CSS_SELECTOR,
                'div[sub-section-id^="title--template--"] h1'
            ).text.strip()
            logger.info(f"Found product type: {product_type}")
        except Exception as e:
            logger.error(f"Could not find product type: {str(e)}")
            return
        
        # Find all color variant radio inputs
        color_variants = driver.find_elements(
            By.CSS_SELECTOR,
            'input[type="radio"][data-product-url]'
        )
        
        # Extract URLs and organize by type
        variant_urls = {
            "https://www.awaytravel.com" + input.get_attribute("data-product-url")
            if input.get_attribute("data-product-url").startswith("/")
            else input.get_attribute("data-product-url")
            for input in color_variants
        }
        
        # Load existing data or create new structure
        try:
            with open("product_variants.json", "r", encoding="utf-8") as f:
                all_variants = json.load(f)
        except FileNotFoundError:
            all_variants = {}
        
        # Update the data structure
        if product_type not in all_variants:
            all_variants[product_type] = []
        
        # Add new URLs, avoiding duplicates
        existing_urls = set(all_variants[product_type])
        new_urls = list(variant_urls - existing_urls)
        all_variants[product_type].extend(new_urls)
        
        # Save updated data
        with open("product_variants.json", "w", encoding="utf-8") as f:
            json.dump(all_variants, f, indent=2)
        
        logger.success(f"Found {len(variant_urls)} color variants for {product_type}")
        if new_urls:
            logger.info(f"Added {len(new_urls)} new URLs to {product_type}")
        
        time.sleep(2)  # Small delay between pages to be respectful
        
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")

def load_cached_urls():
    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            urls = json.load(f)
            logger.success(f"Loaded {len(urls)} product URLs from cache")
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

        # 2️⃣  Scroll until no new content loads
        logger.info("Scrolling to load all products")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:   # reached the bottom
                break
            last_height = new_height

        # 3️⃣  Grab every /products/… link that appears on the page
        logger.info("Collecting product URLs")
        anchors = driver.find_elements(
            By.CSS_SELECTOR,
            'accessible-link.block.group\\/product[href^="/products/"]'
        )
        urls = {
            "https://www.awaytravel.com" + a.get_attribute("href")
            if a.get_attribute("href").startswith("/")
            else a.get_attribute("href")
            for a in anchors
        }

        # 4️⃣  Persist to JSON
        logger.info(f"Saving {len(urls)} URLs to {OUTPUT_JSON}")
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(sorted(urls), f, indent=2)

        logger.success(f"Saved {len(urls)} product URLs to {OUTPUT_JSON}")
        return urls

    finally:
        logger.info("Closing browser session")
        driver.quit()

if __name__ == "__main__":
    logger.info("Starting Away Travel scraper")
    
    # Ask user if they want to use cached URLs or fetch new ones
    while True:
        choice = input("Would you like to:\n1. Use cached product URLs\n2. Fetch new product URLs\nEnter 1 or 2: ").strip()
        if choice in ["1", "2"]:
            break
        logger.warning("Invalid choice. Please enter 1 or 2.")

    if choice == "1":
        urls = load_cached_urls()
        if urls is None:
            logger.info("No cached URLs found. Fetching new URLs...")
            urls = collect_product_urls()
    else:
        urls = collect_product_urls()
    
    # Then process each product page
    logger.info("Starting product page processing")
    driver = uc.Chrome(headless=False, use_subprocess=False)
    try:
        for url in urls:
            process_product_page(driver, url)
    finally:
        logger.info("Closing browser session")
        driver.quit()
    
    logger.success("Scraping completed successfully")
