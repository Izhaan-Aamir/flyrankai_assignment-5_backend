import os

import requests


URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = "cache/catalogue-page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}


def fetch_page():
    # If the page is already cached, use the local copy.
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            html = file.read()

        print("CACHE HIT")
        print(f"Response size: {len(html)} bytes")
        return html

    # The page is not cached, so request it from the website.
    print("FETCH")

    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=5
        )
    except requests.RequestException as error:
        print(f"Request failed: {error}")
        return None

    # Only HTTP 200 is accepted as a successful page.
    if response.status_code != 200:
        print(f"Fetch failed with status code: {response.status_code}")
        return None

    html = response.text

    # Save the successful response to the local cache.
    os.makedirs("cache", exist_ok=True)

    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"Response size: {len(html)} bytes")

    return html


if __name__ == "__main__":
    fetch_page()