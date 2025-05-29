import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
import re
import os

# Configure loguru
logger.add("away_travel.log", rotation="1 day", retention="7 days", level="INFO")

COLLECTION_URL = "https://www.awaytravel.com/collections/carry-on-luggage"
DATA_FOLDER = "AwayTravel_Data"
CACHE_DIR = "AwayTravel_Cache"
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

def get_image_urls(driver):
    # Find the swiper container
    swiper_container = driver.find_element(By.XPATH, "(//swiper-container)[2]")
    # Find all swiper slides within the container
    slides = swiper_container.find_elements(By.TAG_NAME, "swiper-slide")
    
    image_urls = []
    for slide in slides:
        try:
            # Find the img element within each slide
            img = slide.find_element(By.TAG_NAME, "img")
            # Get the src attribute
            img_url = img.get_attribute("src")
            if img_url:
                # remove the query string from the url
                img_url = img_url.split("?")[0]
                image_urls.append(img_url)
        except Exception as e:
            logger.warning(f"Could not get image URL from slide: {str(e)}")
            continue
    
    return image_urls

def get_product_data(url, driver, image_url_json, use_cache=False):
    url_brief = url.split("/")[-1]
    logger.info(f"Getting product data for {url_brief}")
    # the url brief is the last part of the url after the last /
    cache_file = f"{CACHE_DIR}/{url_brief}.json"
    if use_cache:
        # check if cache file exists
        logger.info(f"Checking for cache file for {url_brief}")
        if os.path.exists(cache_file):
            logger.info(f"Cache file found for {url_brief}")
            with open(cache_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                # Get image URLs from the image_url_json if available
                return json_data["product_name"], json_data["color"], json_data["dimensions"], json_data["weight"]
    
    # fetching product data
    logger.info(f"Fetching product data for {url_brief}")
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

    # save to cache
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"product_name": product_name, "color": color, "dimensions": dimensions, "weight": weight}, f)

    image_urls = get_image_urls(driver)
    # Initialize the dictionary for this product if it doesn't exist
    if product_name not in image_url_json:
        image_url_json[product_name] = {}
    image_url_json[product_name][color] = image_urls
    # Save image URLs after each product
    with open(f"{DATA_FOLDER}/image_urls.json", 'w', encoding="utf-8") as f:
        json.dump(image_url_json, f, indent=2)
    logger.info(f"Saved data for {product_name}")

    return product_name, color, dimensions, weight

# create a csv file with headers then return the path
def create_csv():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    base_csv_path = os.path.join(DATA_FOLDER, 'awaytravel_data.csv')
    csv_path = f"{base_csv_path}"
    counter = 1
    while os.path.exists(csv_path):
        csv_path = os.path.join(DATA_FOLDER, f'awaytravel_data({counter}).csv')
        counter += 1
    
    with open(csv_path, 'w', encoding="utf-8") as f:
        f.write("Brand, Product Name,Color,Dimensions,Weight\n")
    return csv_path    

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

    use_product_caches = input("Would you like to use product caches when possible? (y/n): ").strip() == 'y'

    # create cache dir if it doesn't exist
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    driver = uc.Chrome(headless=False, use_subprocess=False)  # Set to False for headed mode

    csv_path = create_csv()
    image_url_json = {}

    csv = open(csv_path, 'a', encoding="utf-8")
    if os.path.exists(f"{DATA_FOLDER}/image_urls.json"):
        image_url_json = json.load(open(f"{DATA_FOLDER}/image_urls.json", 'r', encoding="utf-8"))
    else:
        image_url_json = {}

    for product_type, urls in all_variants.items():
        for url in urls:
            product_name, color, dimensions, weight = get_product_data(url, driver, image_url_json, use_product_caches)
            csv.write(f"Away Travel,{product_name},{color},{dimensions},{weight}\n")
            csv.flush()  # Force write to disk

    driver.quit()
    csv.close()
    
    logger.success("Scraping completed successfully")

