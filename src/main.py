import os
import time
from datetime import datetime, timezone
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
    Create a safe cache filename for a URL.
    """

    if "catalogue/page-" in url:
        page_number = url.split("page-")[-1].replace(".html", "")

        return os.path.join(
            CACHE_DIR,
            f"catalogue-page-{page_number}.html"
        )

    # Create a filename based on the final part of the book URL.
    filename = url.rstrip("/").split("/")[-1]

    return os.path.join(
        CACHE_DIR,
        f"book-{filename}.html"
    )


def fetch_page(url):
    """
    Fetch a page from the website or use the local cache.
    """

    cache_file = get_cache_file(url)

    # Use cache if available.
    if os.path.exists(cache_file):

        with open(cache_file, "r", encoding="utf-8") as file:
            html = file.read()

        print(f"CACHE HIT: {url}")

        return html

    # Real request.
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

    return html


def discover_catalogue_pages():
    """
    Discover the first three catalogue pages
    and all book URLs on those pages.
    """

    current_url = START_URL

    catalogue_pages = []
    book_urls = set()

    while current_url and len(catalogue_pages) < 3:

        cache_file = get_cache_file(current_url)

        # Only delay before a real request.
        if not os.path.exists(cache_file):
            if catalogue_pages:
                time.sleep(0.5)

        html = fetch_page(current_url)

        if html is None:
            break

        catalogue_pages.append(current_url)

        soup = BeautifulSoup(html, "html.parser")

        # Find every book on this catalogue page.
        for article in soup.select("article.product_pod"):

            link = article.select_one("h3 a")

            if link and link.get("href"):

                absolute_url = urljoin(
                    current_url,
                    link["href"]
                )

                book_urls.add(absolute_url)

        # Find the next catalogue page.
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


def extract_text(element):
    """
    Return cleaned text from a BeautifulSoup element.
    """

    if element is None:
        return None

    text = element.get_text(" ", strip=True)

    return text if text else None


def extract_book_details(book_url, source_page):
    """
    Extract the required raw fields from one book page.
    """

    html = fetch_page(book_url)

    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_element = soup.select_one("div.product_main h1")
    title = extract_text(title_element)

    # Price
    price_element = soup.select_one(
        "div.product_main .price_color"
    )
    price_text = extract_text(price_element)

    # Availability
    availability_element = soup.select_one(
        "div.product_main .availability"
    )
    availability_text = extract_text(availability_element)

    # Rating
    rating_element = soup.select_one(
        "div.product_main p.star-rating"
    )

    rating_text = None

    if rating_element:
        rating_classes = rating_element.get("class", [])

        # The rating is stored in the CSS class:
        # One, Two, Three, Four, or Five.
        rating_words = {
            "One",
            "Two",
            "Three",
            "Four",
            "Five"
        }

        for rating in rating_classes:
            if rating in rating_words:
                rating_text = rating
                break

    # Description
    description_element = soup.select_one(
        "#product_description + p"
    )
    description = extract_text(description_element)

    # Current UTC timestamp
    fetched_at = datetime.now(timezone.utc).isoformat()

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


def extract_all_books(catalogue_pages, book_urls):
    """
    Visit every discovered book page and extract its raw data.
    """

    records = []

    # Map each book URL to its catalogue source page.
    book_sources = {}

    for source_page in catalogue_pages:

        html = fetch_page(source_page)

        if html is None:
            continue

        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):

            link = article.select_one("h3 a")

            if link and link.get("href"):

                book_url = urljoin(
                    source_page,
                    link["href"]
                )

                book_sources[book_url] = source_page

    # Visit every book page.
    for index, book_url in enumerate(book_urls, start=1):

        source_page = book_sources.get(
            book_url,
            catalogue_pages[0]
        )

        # Wait before real requests.
        cache_file = get_cache_file(book_url)

        if not os.path.exists(cache_file):
            time.sleep(0.5)

        record = extract_book_details(
            book_url,
            source_page
        )

        if record is not None:
            records.append(record)

        print(
            f"Processed book {index}/{len(book_urls)}"
        )

    return records


if __name__ == "__main__":

    catalogue_pages, book_urls = discover_catalogue_pages()

    records = extract_all_books(
        catalogue_pages,
        book_urls
    )

    print()
    print(f"detail_pages={len(records)}")

    if records:
        print()
        print("Sample raw record:")
        print(records[0])