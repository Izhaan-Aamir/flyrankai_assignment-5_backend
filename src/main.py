import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl


BASE_URL = "https://books.toscrape.com/"
FIRST_CATALOGUE_URL = (
    "https://books.toscrape.com/catalogue/page-1.html"
)

CACHE_DIR = "cache"
OUTPUT_DIR = "output"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}

REQUEST_TIMEOUT = 5
REQUEST_DELAY = 0.5


# ---------------------------------------------------------
# Stage 5 run statistics
# ---------------------------------------------------------

run_stats = {
    "pages_fetched": 0,
    "cache_hits": 0,
    "failed_pages": 0,
}

failed_pages = []

last_request_time = None


# ---------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------

class Book(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None
    description: str | None
    source_page: HttpUrl
    fetched_at: datetime


# ---------------------------------------------------------
# Polite request handling
# ---------------------------------------------------------

def wait_before_request():
    """
    Make sure there is at least 0.5 seconds between
    real HTTP requests.
    """
    global last_request_time

    if last_request_time is not None:
        elapsed = time.monotonic() - last_request_time

        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)


def make_request(url):
    """
    Fetch a URL politely.

    Retry rules:
    - timeout / connection error -> retry once
    - HTTP 5xx -> retry once
    - HTTP 403/404 -> do not retry
    - other non-200 responses -> fail without retry
    """

    global last_request_time

    attempts = 2

    for attempt in range(1, attempts + 1):

        wait_before_request()

        print(f"FETCH: {url}")

        try:
            last_request_time = time.monotonic()

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

        except requests.RequestException as error:

            print(
                f"Request error on attempt {attempt}: {error}"
            )

            if attempt < attempts:
                print("Retrying once...")
                continue

            return None

        # Successful response
        if response.status_code == 200:
            run_stats["pages_fetched"] += 1
            return response.text

        # 5xx -> retry once
        if 500 <= response.status_code <= 599:

            print(
                f"Server error {response.status_code} "
                f"on attempt {attempt}"
            )

            if attempt < attempts:
                print("Retrying once...")
                continue

            return None

        # 403 / 404 -> no retry
        if response.status_code in (403, 404):

            print(
                f"Non-retryable status code: "
                f"{response.status_code}"
            )

            return None

        # Other status codes
        print(
            f"Fetch failed with status code: "
            f"{response.status_code}"
        )

        return None

    return None


# ---------------------------------------------------------
# Cache handling
# ---------------------------------------------------------

def get_cache_file(url):
    """
    Generate a safe cache filename.

    Catalogue pages use readable names.

    Book URLs use a short SHA-256 hash so very long
    book titles do not create Windows filename problems.
    """

    if "catalogue/page-" in url:
        page_number = (
            url.split("page-")[-1]
            .replace(".html", "")
        )

        return os.path.join(
            CACHE_DIR,
            f"catalogue-page-{page_number}.html"
        )

    url_hash = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]

    return os.path.join(
        CACHE_DIR,
        f"book-{url_hash}.html"
    )


def fetch_page(url):
    """
    Read a page from cache if available.

    Otherwise perform a real HTTP request.
    """

    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = get_cache_file(url)

    if os.path.exists(cache_file):

        with open(
            cache_file,
            "r",
            encoding="utf-8"
        ) as file:
            html = file.read()

        run_stats["cache_hits"] += 1

        print(f"CACHE HIT: {url}")
        print(f"Response size: {len(html)} bytes")

        return html

    html = make_request(url)

    if html is None:
        return None

    with open(
        cache_file,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(html)

    print(f"Response size: {len(html)} bytes")

    return html


# ---------------------------------------------------------
# Catalogue discovery
# ---------------------------------------------------------

def discover_catalogue_pages():
    """
    Discover the first three catalogue pages.
    """

    catalogue_urls = []
    current_url = FIRST_CATALOGUE_URL

    for _ in range(3):

        if current_url in catalogue_urls:
            break

        catalogue_urls.append(current_url)

        html = fetch_page(current_url)

        if html is None:
            failed_pages.append(current_url)
            run_stats["failed_pages"] += 1
            break

        soup = BeautifulSoup(html, "html.parser")

        next_link = soup.select_one(
            "li.next a"
        )

        if next_link is None:
            break

        href = next_link.get("href")

        if not href:
            break

        from urllib.parse import urljoin

        current_url = urljoin(
            current_url,
            href
        )

    return catalogue_urls


# ---------------------------------------------------------
# Book URL discovery
# ---------------------------------------------------------

def discover_book_urls(catalogue_pages):
    """
    Collect all unique book URLs from the catalogue pages.
    """

    book_urls = []
    seen = set()

    for page_url in catalogue_pages:

        html = fetch_page(page_url)

        if html is None:
            if page_url not in failed_pages:
                failed_pages.append(page_url)
                run_stats["failed_pages"] += 1
            continue

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        from urllib.parse import urljoin

        for article in soup.select(
            "article.product_pod"
        ):

            link = article.select_one(
                "h3 a"
            )

            if not link:
                continue

            href = link.get("href")

            if not href:
                continue

            product_url = urljoin(
                page_url,
                href
            )

            if product_url not in seen:
                seen.add(product_url)
                book_urls.append(
                    product_url
                )

    return book_urls


# ---------------------------------------------------------
# Book extraction
# ---------------------------------------------------------

def extract_book(
    html,
    product_url,
    source_page
):
    """
    Extract the eight raw fields required by the assignment.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title_element = soup.select_one(
        "div.product_main h1"
    )

    price_element = soup.select_one(
        "div.product_main .price_color"
    )

    availability_element = soup.select_one(
        "div.product_main .availability"
    )

    rating_element = soup.select_one(
        "div.product_main p.star-rating"
    )

    description_element = soup.select_one(
        "#product_description + p"
    )

    title = (
        title_element.get_text(strip=True)
        if title_element
        else ""
    )

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else ""
    )

    availability_text = (
        availability_element.get_text(
            " ",
            strip=True
        )
        if availability_element
        else ""
    )

    rating_text = None

    if rating_element:
        classes = rating_element.get(
            "class",
            []
        )

        rating_names = {
            "One",
            "Two",
            "Three",
            "Four",
            "Five",
        }

        for value in classes:
            if value in rating_names:
                rating_text = value
                break

    description = None

    if description_element:
        description = (
            description_element.get_text(
                " ",
                strip=True
            )
        )

    fetched_at = datetime.now(
        timezone.utc
    )

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at.isoformat(),
    }


# ---------------------------------------------------------
# Normalization
# ---------------------------------------------------------

def normalize_price(price_text):
    """
    Convert the raw GBP price into a float.
    """

    cleaned = (
        price_text
        .replace("Â£", "")
        .replace("£", "")
        .replace(",", "")
        .strip()
    )

    return float(cleaned)


def normalize_record(record):
    """
    Add the normalized numeric price while preserving
    the original price_text.
    """

    record["price_gbp"] = normalize_price(
        record["price_text"]
    )

    return record


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

def validate_records(raw_records):
    valid_records = []
    invalid_records = []

    for record in raw_records:

        try:
            book = Book.model_validate(
                record
            )

            valid_records.append(
                book.model_dump(mode="json")
            )

        except Exception as error:

            invalid_records.append(
                {
                    "record": record,
                    "error": str(error),
                }
            )

    return valid_records, invalid_records


# ---------------------------------------------------------
# JSON storage
# ---------------------------------------------------------

def save_json(filename, data):

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

    print(f"saved={path}")


# ---------------------------------------------------------
# Run report
# ---------------------------------------------------------

def save_run_report(
    started_at,
    duration_seconds,
    valid_count,
    invalid_count
):

    report = {
        "started_at": started_at,
        "duration_seconds": round(
            duration_seconds,
            2
        ),
        "catalogue_pages": 3,
        "pages_fetched": run_stats[
            "pages_fetched"
        ],
        "cache_hits": run_stats[
            "cache_hits"
        ],
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "failed_pages": run_stats[
            "failed_pages"
        ],
        "failed_page_urls": failed_pages,
    }

    save_json(
        "run-report.json",
        report
    )


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------

def main(test_failure=False):

    started_at_datetime = datetime.now(
        timezone.utc
    )

    started_at = started_at_datetime.isoformat()

    start_time = time.monotonic()

    # Stage 2: catalogue discovery
    catalogue_pages = (
        discover_catalogue_pages()
    )

    print(
        f"catalogue_pages="
        f"{len(catalogue_pages)}"
    )

    # Stage 2: book URL discovery
    book_urls = discover_book_urls(
        catalogue_pages
    )

    print(
        f"discovered={len(book_urls)}"
    )

    print(
        f"unique_urls={len(set(book_urls))}"
    )

    # Stage 5 test:
    # Add one intentionally broken URL.
    if test_failure:

        fake_url = (
            "https://books.toscrape.com/"
            "catalogue/this-page-does-not-exist-"
            "for-stage-5/index.html"
        )

        book_urls.append(fake_url)

        print(
            "\nSTAGE 5 FAILURE TEST ENABLED"
        )

        print(
            f"Added fake URL: {fake_url}"
        )

    # Stage 3 + 4: extract, normalize, validate
    raw_records = []

    for index, product_url in enumerate(
        book_urls,
        start=1
    ):

        # Do not count the fake URL as a book record.
        # It is only there to prove failure isolation.
        html = fetch_page(
            product_url
        )

        if html is None:

            if product_url not in failed_pages:
                failed_pages.append(
                    product_url
                )

                run_stats[
                    "failed_pages"
                ] += 1

            print(
                f"FAILED PAGE - continuing: "
                f"{product_url}"
            )

            continue

        source_page = (
            catalogue_pages[
                (index - 1) // 20
            ]
            if index <= 60
            else catalogue_pages[-1]
        )

        try:

            record = extract_book(
                html,
                product_url,
                source_page
            )

            record = normalize_record(
                record
            )

            raw_records.append(
                record
            )

        except Exception as error:

            print(
                f"EXTRACTION ERROR - continuing: "
                f"{product_url}"
            )

            print(error)

            failed_pages.append(
                product_url
            )

            run_stats[
                "failed_pages"
            ] += 1

        print(
            f"Processed book "
            f"{min(index, 60)}/60"
        )

    print(
        f"\ndetail_pages="
        f"{len(raw_records)}"
    )

    valid_records, invalid_records = (
        validate_records(raw_records)
    )

    print(
        f"\nvalid_records="
        f"{len(valid_records)}"
    )

    print(
        f"invalid_records="
        f"{len(invalid_records)}"
    )

    save_json(
        "books.json",
        valid_records
    )

    save_json(
        "errors.json",
        invalid_records
    )

    duration_seconds = (
        time.monotonic()
        - start_time
    )

    save_run_report(
        started_at,
        duration_seconds,
        len(valid_records),
        len(invalid_records)
    )


# ---------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test-failure",
        action="store_true",
        help=(
            "Add one fake book URL to verify "
            "failure isolation."
        ),
    )

    args = parser.parse_args()

    main(
        test_failure=args.test_failure
    )