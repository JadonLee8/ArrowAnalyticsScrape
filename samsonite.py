from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# data url: https://shop.samsonite.com/on/demandware.store/Sites-samsonite-Site/en_US/Search-UpdateGrid?cgid=luggage-carry-on&srule=category-position&start=0&sz=60

def setup_driver():
    # Configure Chrome options
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def main():
    url = "https://shop.samsonite.com/luggage/carry-on-luggage/"
    
    try:
        # Setup the driver
        driver = setup_driver()
        
        # Load the webpage
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(15)  # Basic wait to ensure page loads. May have to complete a bot protection challenge. Just rerun if it prompts for a challenge.
        
        # Get the page source
        html = driver.page_source
        print("Successfully loaded the page")
        with open('samsonite_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Page source saved to samsonite_page.html")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    main()
