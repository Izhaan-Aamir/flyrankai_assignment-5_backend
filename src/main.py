import hashlib
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}

CACHE_DIR = "cache"
OUTPUT_DIR = "output"


class Book(BaseModel):
    """
    Validated book record.
    """

    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None
    description: str | None
    source_page: HttpUrl
    fetched_at: datetime


def get_cache_file(url):
    """
    Create a short, deterministic cache filename for a URL.
    """

    if "catalogue/page-" in url:
        page_number = url.split("page-")[-1].replace(".html", "")

        return os.path.join(
            CACHE_DIR,
            f"catalogue-page-{page_number}.html"
        )

    # Use a short hash for book URLs.
    url_hash = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]

    return os.path.join(
        CACHE_DIR,
        f"book-{url_hash}.html"
    )


def fetch_page(url):
    """
    Fetch a page from the website or use the local cache.
    """

    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = get_cache_file(url)

    if os.path.exists(cache_file):

        with open(cache_file, "r", encoding="utf-8") as file:
            html = file.read()

        print(f"CACHE HIT: {url}")

        return html

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

        if not os.path.exists(cache_file):
            if catalogue_pages:
                time.sleep(0.5)

        html = fetch_page(current_url)

        if html is None:
            break

        catalogue_pages.append(current_url)

        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):

            link = article.select_one("h3 a")

            if link and link.get("href"):

                absolute_url = urljoin(
                    current_url,
                    link["href"]
                )

                book_urls.add(absolute_url)

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
    Extract raw fields from one book page.
    """

    html = fetch_page(book_url)

    if html is None:
        return None

    soup = BeautifulSoup(html, "html.parser")

    title_element = soup.select_one(
        "div.product_main h1"
    )
    title = extract_text(title_element)

    price_element = soup.select_one(
        "div.product_main .price_color"
    )
    price_text = extract_text(price_element)

    availability_element = soup.select_one(
        "div.product_main .availability"
    )
    availability_text = extract_text(
        availability_element
    )

    rating_element = soup.select_one(
        "div.product_main p.star-rating"
    )

    rating_text = None

    if rating_element:

        rating_classes = rating_element.get(
            "class",
            []
        )

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

    description_element = soup.select_one(
        "#product_description + p"
    )

    description = extract_text(
        description_element
    )

    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

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
    Visit every discovered book page.
    """

    records = []

    book_sources = {}

    for source_page in catalogue_pages:

        html = fetch_page(source_page)

        if html is None:
            continue

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        for article in soup.select(
            "article.product_pod"
        ):

            link = article.select_one(
                "h3 a"
            )

            if link and link.get("href"):

                book_url = urljoin(
                    source_page,
                    link["href"]
                )

                book_sources[
                    book_url
                ] = source_page

    for index, book_url in enumerate(
        book_urls,
        start=1
    ):

        source_page = book_sources.get(
            book_url,
            catalogue_pages[0]
        )

        cache_file = get_cache_file(
            book_url
        )

        if not os.path.exists(cache_file):
            time.sleep(0.5)

        record = extract_book_details(
            book_url,
            source_page
        )

        if record is not None:
            records.append(record)

        print(
            f"Processed book "
            f"{index}/{len(book_urls)}"
        )

    return records


def normalize_price(price_text):
    """
    Convert a raw price such as £51.77
    into a numeric GBP value.
    """

    if not price_text:
        raise ValueError(
            "Missing price"
        )

    cleaned = (
        price_text
        .replace("Â£", "")
        .replace("£", "")
        .strip()
    )

    return float(cleaned)


def normalize_record(raw_record):
    """
    Normalize one raw scraped record.
    """

    normalized = raw_record.copy()

    normalized["price_gbp"] = normalize_price(
        raw_record["price_text"]
    )

    return normalized


def validate_records(raw_records):
    """
    Normalize and validate all records.

    Valid records are returned separately
    from invalid records.
    """

    valid_records = []
    errors = []

    for raw_record in raw_records:

        try:

            normalized = normalize_record(
                raw_record
            )

            book = Book.model_validate(
                normalized
            )

            valid_records.append(
                book.model_dump(mode="json")
            )

        except (
            ValueError,
            ValidationError
        ) as error:

            errors.append(
                {
                    "record": raw_record,
                    "error": str(error)
                }
            )

    return valid_records, errors


def save_json(filename, data):
    """
    Save data as formatted JSON.
    """

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    return path


if __name__ == "__main__":

    catalogue_pages, book_urls = (
        discover_catalogue_pages()
    )

    raw_records = extract_all_books(
        catalogue_pages,
        book_urls
    )

    print()
    print(
        f"detail_pages={len(raw_records)}"
    )

    valid_records, errors = (
        validate_records(raw_records)
    )

    save_json(
        "books.json",
        valid_records
    )

    save_json(
        "errors.json",
        errors
    )

    print()
    print(
        f"valid_records={len(valid_records)}"
    )

    print(
        f"invalid_records={len(errors)}"
    )

    print(
        f"saved=output/books.json"
    )

    print(
        f"saved=output/errors.json"
    )