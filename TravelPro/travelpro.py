import undetected_chromedriver as uc
import json
import os
import csv
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from loguru import logger

BASE_PAGE = "https://travelpro.com/collections/carry-on-luggage?products.size=50"
csv_name = "TravelPro.csv"

def clean_product_name(product_name):
    return product_name.lower().replace(" ", "-").replace("®", "")

def wait_for_body(driver):
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

def get_product_urls(driver):
    product_urls = {}

    # check if there is a cached product_urls.json file
    if os.path.exists("product_urls.json"):
        logger.info("Would you like to use the cached product_urls.json file? (y/n)")
        if input() == "y":
            with open("product_urls.json", "r") as f:
                product_urls = json.load(f)
                return product_urls
    
    # if not, get the product urls
    driver.get(BASE_PAGE)
    wait_for_body(driver)
    products = driver.find_elements(By.XPATH, ".//div[contains(@class, 'ns-product') and contains(@class, 'ns-border-box')]")
    for product in products:
        try:
            product_name = product.find_element(By.CLASS_NAME, "ns-product-name").get_attribute("innerHTML").replace("</sup>", "").replace("<sup>", "")
            if product_name not in product_urls:
                product_urls[product_name] = {}
        except:
            # ads use the same class name as products
            continue
        if product.find_elements(By.CLASS_NAME, "swatch"):
            swatch = product.find_elements(By.CLASS_NAME, "swatch-element")
            for swatch_element in swatch:
                color_name = swatch_element.find_element(By.TAG_NAME, "input").get_attribute("value")
                url = swatch_element.find_element(By.TAG_NAME, "input").get_attribute("data-url")
                product_urls[product_name][color_name] = url
        else:
            # otherwise there is only one url/color
            url = product.find_element(By.TAG_NAME, "a").get_attribute("href")
            product_urls[product_name]["DEFAULT"] = url

    # save the product_urls to a json file
    with open("product_urls.json", "w") as f:
        json.dump(product_urls, f)
    return product_urls

def add_images_to_json(product_name, color_name, image_urls):
    if os.path.exists("images.json"):
        with open("images.json", "r") as f:
            images = json.load(f)
    else:
        images = {}
    if product_name not in images:
        images[product_name] = {}
    if color_name not in images[product_name]:
        images[product_name][color_name] = []
    images[product_name][color_name] = image_urls
    with open("images.json", "w") as f:
        json.dump(images, f)

def add_product_to_csv(product_name, color_name, dimensions, weight):
    with open(csv_name, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["TravelPro",product_name, color_name, dimensions, weight])

def get_product_details(driver, product_name, color_name, url):
    logger.info(f"Getting product details for {product_name} {color_name} at {url}")
    driver.get(url)
    wait_for_body(driver)
    # get the tab with features and dimensions
    tab = driver.find_element(By.CLASS_NAME, "cstm_tabs_section").find_elements(By.CLASS_NAME,"tab-container")[1].find_element(By.CLASS_NAME, "tabcontent")
    print(tab.find_elements(By.TAG_NAME, "p")[0].get_attribute("innerHTML"))
    if tab.find_elements(By.TAG_NAME, "p")[0].get_attribute("innerHTML") == "&nbsp:":
        dimensions = tab.find_elements(By.TAG_NAME, "p")[3].get_attribute("innerHTML").split("</strong>")[1]
        weight = tab.find_elements(By.TAG_NAME, "p")[4].get_attribute("innerHTML").split("</strong>")[1].strip()
    else:
        dimensions = tab.find_elements(By.TAG_NAME, "p")[2].get_attribute("innerHTML").split("</strong>")[1]
        weight = tab.find_elements(By.TAG_NAME, "p")[3].get_attribute("innerHTML").split("</strong>")[1].strip()

    # IMAGES
    images = driver.find_element(By.CLASS_NAME, "product-single__photos")
    image_urls = []
    for div in images.find_elements(By.XPATH, "./div"):
        try:
            img = div.find_element(By.XPATH, "./div")
            image_urls.append(img.get_attribute("data-src"))
        except:
            continue
    add_images_to_json(product_name, color_name, image_urls)

    product_details = (product_name, color_name, dimensions, weight)

    return product_details


if __name__ == "__main__":
    driver = uc.Chrome(use_subprocess=False)
    product_urls = get_product_urls(driver)
    # if TravelPro.csv exists, change file name to TravelPro(1).csv. If TravelPro(1).csv exists, change file name to TravelPro(2).csv, and so on.
    if os.path.exists(csv_name):
        i = 1
        while os.path.exists(f"{csv_name}({i}).csv"):
            i += 1
        csv_name = f"{csv_name}({i}).csv"
    
    # column headers
    with open(csv_name, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Brand","Product Name","Color","Dimensions","Weight"])

    for product_name in product_urls.keys():
        for color_name, url in product_urls[product_name].items():
            product_name,color_name,dimensions,weight = get_product_details(driver, product_name, color_name, url)
            add_product_to_csv(product_name,color_name,dimensions,weight)
            time.sleep(1)

    driver.quit()
    logger.success("Done!")
