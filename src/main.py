import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}

CACHE_DIR = "cache"


def get_cache_file(url):
    """
    Convert a catalogue page URL into a local cache filename.
    """
    page_number = url.split("page-")[-1].replace(".html", "")
    return os.path.join(
        CACHE_DIR,
        f"catalogue-page-{page_number}.html"
    )


def fetch_page(url):
    """
    Fetch a page from the website or use the local cache.
    """

    cache_file = get_cache_file(url)

    # Use cached page if it already exists.
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as file:
            html = file.read()

        print(f"CACHE HIT: {url}")
        print(f"Response size: {len(html)} bytes")

        return html

    # Real website request.
    print(f"FETCH: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=5
        )
    except requests.RequestException as error:
        print(f"Request failed: {error}")
        return None

    # Only accept HTTP 200.
    if response.status_code != 200:
        print(
            f"Fetch failed with status code: "
            f"{response.status_code}"
        )
        return None

    html = response.text

    os.makedirs(CACHE_DIR, exist_ok=True)

    with open(cache_file, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"Response size: {len(html)} bytes")

    return html


def discover_catalogue_pages():
    """
    Discover the first three catalogue pages and all book URLs.
    """

    current_url = START_URL

    catalogue_pages = []
    book_urls = set()

    while current_url and len(catalogue_pages) < 3:

        # Wait before a real request.
        cache_file = get_cache_file(current_url)

        if not os.path.exists(cache_file):
            if catalogue_pages:
                time.sleep(0.5)

        html = fetch_page(current_url)

        if html is None:
            print(f"Could not process: {current_url}")
            break

        catalogue_pages.append(current_url)

        soup = BeautifulSoup(html, "html.parser")

        # Find every book link on this catalogue page.
        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")

            if link and link.get("href"):
                absolute_url = urljoin(
                    current_url,
                    link["href"]
                )

                book_urls.add(absolute_url)

        # Find the Next catalogue page.
        next_link = soup.select_one("li.next a")

        if next_link and next_link.get("href"):
            current_url = urljoin(
                current_url,
                next_link["href"]
            )
        else:
            current_url = None

    print()
    print(f"catalogue_pages={len(catalogue_pages)}")
    print(f"discovered={len(book_urls)}")
    print(f"unique_urls={len(book_urls)}")

    return catalogue_pages, sorted(book_urls)


if __name__ == "__main__":
    discover_catalogue_pages()