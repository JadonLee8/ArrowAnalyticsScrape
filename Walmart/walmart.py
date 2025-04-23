import asyncio
import json
import math
from urllib.parse import urlencode

import httpx
import pandas as pd
from loguru import logger
from parsel import Selector

# Base URL for Walmart search
BASE_URL = "https://www.walmart.com/search"

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_dimensions(text):
    """
    Extract dimensions from a given text string.
    Looks for patterns like '20 x 14 x 9 inches'.
    """
    import re

    pattern = re.compile(r'(\d+\.?\d*)\s?[xX×]\s?(\d+\.?\d*)\s?[xX×]\s?(\d+\.?\d*)\s?(inches|inch|")?', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return f"{match.group(1)} x {match.group(2)} x {match.group(3)}"
    return None


def parse_search(html_text):
    """
    Extract product data from Walmart search HTML response.
    """
    sel = Selector(text=html_text)
    data_script = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
    if not data_script:
        logger.warning("No __NEXT_DATA__ script tag found.")
        return [], 0

    try:
        data = json.loads(data_script)
        item_stacks = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
        if not item_stacks:
            logger.warning("No itemStacks found in JSON data.")
            return [], 0

        items = item_stacks[0].get("items", [])
        total_results = item_stacks[0].get("count", 0)
        return items, total_results
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing JSON data: {e}")
        return [], 0


async def fetch_page(client, params):
    """
    Fetch a single search results page.
    """
    url = f"{BASE_URL}?{urlencode(params)}"
    try:
        response = await client.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        logger.error(f"HTTP error while fetching {url}: {e}")
        return ""


async def scrape_walmart_carry_on_luggage(max_pages=3):
    """
    Scrape carry-on luggage data from Walmart.
    """
    results = []
    async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
        # Fetch the first page to determine total results
        params = {"q": "carry on luggage", "page": 1}
        html_text = await fetch_page(client, params)
        items, total_results = parse_search(html_text)
        results.extend(items)

        # Calculate total pages
        items_per_page = len(items) if items else 40
        total_pages = math.ceil(total_results / items_per_page)
        total_pages = min(total_pages, max_pages)

        logger.info(f"Total results: {total_results}, Pages to scrape: {total_pages}")

        # Fetch remaining pages
        tasks = []
        for page in range(2, total_pages + 1):
            params = {"q": "carry on luggage", "page": page}
            tasks.append(fetch_page(client, params))

        pages = await asyncio.gather(*tasks)
        for html in pages:
            items, _ = parse_search(html)
            results.extend(items)

    # Process results
    data = []
    for item in results:
        title = item.get("title", "")
        image_url = item.get("imageInfo", {}).get("thumbnailUrl", "")
        product_page_url = f"https://www.walmart.com{item.get('canonicalUrl', '')}"
        dimensions = extract_dimensions(title)
        data.append({
            "Title": title,
            "Image_URL": image_url,
            "Product_Page_URL": product_page_url,
            "Dimensions": dimensions,
        })

    return data


if __name__ == "__main__":
    data = asyncio.run(scrape_walmart_carry_on_luggage(max_pages=3))
    df = pd.DataFrame(data)
    df.to_csv("walmart_carry_on_luggage.csv", index=False)
    logger.success("Scraping complete. Data saved to walmart_carry_on_luggage.csv")
