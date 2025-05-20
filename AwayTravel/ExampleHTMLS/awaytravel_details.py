import json, time, re, pathlib
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

BASE    = "https://www.awaytravel.com"
INPUT   = "urls.json"          # output from the previous script
OUTPUT  = "variants_by_product.json"
PAUSE   = 0.5                  # seconds between page actions

# —— helpers ————————————————————————————————————————————————————————————————

def to_soup(driver):
    return BeautifulSoup(driver.page_source, "lxml")

def base_name_from_title(title):
    """
    Product titles come through like
    “The Softside Bigger Carry-On in Navy Blue”.
    Everything before “ in ” is the base product name.
    """
    return title.split(" in ")[0].strip()

def extract_variants(page_html):
    """
    On Away product pages, every colour swatch <input> carries
    a data-product-url attribute that already contains the right
    variant URL, e.g.  /products/softside-bigger-carry-on-jet-black
    :contentReference[oaicite:0]{index=0}&#8203;:contentReference[oaicite:1]{index=1}
    """
    soup = BeautifulSoup(page_html, "lxml")
    swatches = soup.select('input.swatch-input[data-product-url]')
    return {BASE + s["data-product-url"] for s in swatches}

# —— main ————————————————————————————————————————————————————————————————

def main():
    # load the product URLs you collected in step 1
    product_urls = json.loads(pathlib.Path(INPUT).read_text())


    driver = uc.Chrome(headless=False, use_subprocess=False)  # Set to False for headed mode

    variants_by_product = {}

    try:
        for url in product_urls:
            driver.get(url)
            time.sleep(PAUSE)                       # let the page settle

            # pull the product title from the embedded Shopify JSON
            # (first <script type="application/ld+json"> that contains "product")
            soup = to_soup(driver)
            product_json = soup.find(
                "script",
                type=re.compile("application/ld\\+json"),
                string=re.compile('"category_name"')
            )
            if not product_json:                    # fallback if structure changes
                product_json = soup.select_one('[data-tracking-product]')

            title_match = re.search(r'"title":"([^"]+)"', product_json.string)
            title = title_match.group(1) if title_match else "Unknown Product"

            base_name = base_name_from_title(title)  # e.g. “The Softside Bigger Carry-On”

            # collect variant links
            variants = extract_variants(driver.page_source)

            # ensure the original URL is included (it’s one of the variants)
            variants.add(url)

            # store
            variants_by_product.setdefault(base_name, set()).update(variants)

            print(f"✔ {base_name}: {len(variants)} variants")

    finally:
        driver.quit()

    # convert sets → sorted lists, then write JSON
    clean = {k: sorted(v) for k, v in variants_by_product.items()}
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)

    print(f"\nSaved variant map to {OUTPUT}")

if __name__ == "__main__":
    main()
