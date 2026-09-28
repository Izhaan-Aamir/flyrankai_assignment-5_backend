# The Polite Scraper — FlyRank AI Internship Assignment 5

A small Python scraping pipeline that collects book information from the **Books to Scrape** practice sandbox.

The project is built as a staged pipeline:

```text
Fetch → Extract → Normalize → Validate → Store → Report
```

## Target Classification

### Target

**Books to Scrape**

Website:

https://books.toscrape.com/

Books to Scrape is a public practice sandbox designed for learning and experimenting with web scraping.

### Scope

This scraper will process **only the first three catalogue pages** of Books to Scrape.

The expected result is:

```text
3 catalogue pages
60 unique book URLs
60 book records
```

The scraper will not crawl beyond the first three catalogue pages.

### Data Collected

For each book, the scraper will collect:

* Title
* Product URL
* Price
* Availability
* Rating
* Description
* Source catalogue page
* Fetch timestamp

The scraped information is cleaned, normalized, validated, and stored as JSON.

### Robots Check

The following URL was checked once:

```text
https://books.toscrape.com/robots.txt
```

Result:

```text
404 Not Found
```

The server returned:

```text
nginx/1.21.6
```

Therefore, **no robots file was found**.

A missing `robots.txt` file is not treated as permission to scrape other websites. This assignment uses Books to Scrape because it is specifically provided as a public practice sandbox.

### Why This Target Is Appropriate

Books to Scrape is intended for practicing web scraping, so it provides an appropriate controlled environment for learning HTTP requests, HTML extraction, normalization, validation, caching, and failure handling.

The scraper will use only the required three catalogue pages and will follow polite request practices such as identifying itself, using timeouts, caching downloaded pages, and adding delays between real requests.

> I will not reuse this code on another site without checking its rules and terms first.

---

## Stage 1 — Fetch and Cache

The scraper downloads the first Books to Scrape catalogue page:

```text
https://books.toscrape.com/catalogue/page-1.html
```

The request uses:

* An identifying User-Agent
* A 5-second timeout
* HTTP status-code validation

A successful response is saved locally as:

```text
cache/catalogue-page-1.html
```

During development, the cached file is reused instead of requesting the same page repeatedly.

### Stage 1 Checkpoint

The first run produces:

```text
FETCH
Response size: <number> bytes
```

A second run produces:

```text
CACHE HIT
Response size: <same number> bytes
```

The complete HTML document is not printed to the terminal.

---

## Stage 2 — Discover Three Catalogue Pages

The scraper parses the saved catalogue HTML using Beautiful Soup.

It starts from catalogue page 1 and follows the catalogue's `Next` link until exactly three catalogue pages have been processed.

For each catalogue page, the scraper:

1. Finds every book link.
2. Converts relative links into absolute URLs.
3. Removes duplicate URLs.
4. Follows the `Next` catalogue link.
5. Stops after three catalogue pages.

The scraper also waits at least 0.5 seconds before each new real catalogue-page request. Cached pages do not require a delay.

### Stage 2 Checkpoint

The scraper successfully produces:

```text
catalogue_pages=3
discovered=60
unique_urls=60
```

---

## Stage 3 — Extract Book Details

The scraper visits every unique book URL discovered from the first three catalogue pages.

For each book page, the scraper extracts the following raw fields:

* `title`
* `product_url`
* `price_text`
* `availability_text`
* `rating_text`
* `description`
* `source_page`
* `fetched_at`

The original price is kept as `price_text` at this stage. Normalization into a numeric `price_gbp` field is handled in Stage 4.

The `source_page` field preserves the catalogue page where the book was discovered.

Book HTML pages are also cached locally so repeated development runs do not repeatedly request the same pages.

A delay of at least 0.5 seconds is used before each real book-page request. Cached pages do not require a delay.

### Stage 3 Checkpoint

The scraper successfully processes:

```text
catalogue_pages=3
discovered=60
unique_urls=60
detail_pages=60
```

A complete raw record contains all eight required fields.

---

## Stage 4 — Normalize and Validate

The raw book records are cleaned and validated before being stored.

### Normalization

The scraper:

* Preserves the original `price_text`.
* Converts the price into a numeric `price_gbp` value.
* Keeps the product URL as the record's identity.
* Preserves the source catalogue page and fetch timestamp.

For example:

```text
price_text = "£51.77"
price_gbp  = 51.77
```

### Validation

The project uses a Pydantic `Book` model to validate the normalized records.

The validated schema contains:

* `title`
* `product_url`
* `price_text`
* `price_gbp`
* `availability_text`
* `rating_text`
* `description`
* `source_page`
* `fetched_at`

Valid records are written to:

```text
output/books.json
```

Invalid records are written to:

```text
output/errors.json
```

This keeps validation failures separate from successfully processed records.

### Stage 4 Checkpoint

The scraper successfully produced:

```text
detail_pages=60

valid_records=60
invalid_records=0

saved=output/books.json
saved=output/errors.json
```

The output contains exactly 60 valid book records.

---

## Stage 5 — Failure Isolation and Run Reporting

The scraper now handles individual page failures without stopping the entire run.

### Failure Handling

* Request timeouts and connection errors are retried once.
* HTTP 5xx server errors are retried once.
* HTTP 403 and 404 errors are treated as non-retryable.
* A failed page is recorded and the scraper continues processing the remaining pages.
* Failed pages do not terminate the entire scraping run.

### Run Report

Every run creates:

```text
output/run-report.json
```

The report records:

* Run start time
* Run duration
* Number of catalogue pages
* Pages fetched
* Cache hits
* Valid records
* Invalid records
* Failed pages
* Failed page URLs

### Normal Run Checkpoint

The normal run produces:

```text
catalogue_pages=3
discovered=60
unique_urls=60

detail_pages=60

valid_records=60
invalid_records=0
failed_pages=0
```

### Failure-Isolation Test

The scraper includes a test using an intentionally invalid book URL.

The test demonstrates that:

```text
404 response
    ↓
No retry
    ↓
Failed page recorded
    ↓
Scraper continues
    ↓
60 valid records still produced
    ↓
run-report.json records 1 failed page
```

The failure test produces:

```text
valid_records=60
invalid_records=0
failed_pages=1
```

This demonstrates that a single broken page does not terminate the entire scraping run.

---

## Output Files

The scraper produces the following JSON outputs:

```text
output/
├── books.json
├── errors.json
└── run-report.json
```

### `books.json`

Contains the validated book records.

### `errors.json`

Contains records that failed validation.

### `run-report.json`

Contains an honest summary of the scraping run, including successful processing, cache usage, and failures.

---

## Installation and Usage

### Requirements

* Python 3.10 or newer
* Internet connection for the initial scraping run

### Install

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/Izhaan-Aamir/flyrankai_assignment-5_backend.git
cd flyrankai_assignment-5_backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

### Run the Scraper

Run:

```powershell
python src/main.py
```

The scraper processes the first three catalogue pages and produces:

```text
output/books.json
output/errors.json
output/run-report.json
```

### Run the Failure Test

The failure-isolation test can be run with:

```powershell
python src/main.py --test-failure
```

This adds an intentionally invalid URL and verifies that the scraper continues processing the remaining books.

---

## Data Schema

Each validated book record contains:

```text
title
product_url
price_text
price_gbp
availability_text
rating_text
description
source_page
fetched_at
```

The `price_text` field preserves the original extracted price, while `price_gbp` contains the normalized numeric value.

Invalid records are separated into:

```text
output/errors.json
```

---

## Politeness Rules

The scraper follows these practices:

* Uses a descriptive User-Agent.
* Uses a 5-second request timeout.
* Waits at least 0.5 seconds between real requests.
* Uses local caching to avoid unnecessary repeated requests.
* Retries timeouts and connection errors once.
* Retries HTTP 5xx server errors once.
* Does not retry HTTP 403 or 404 responses.
* Limits crawling to the first three catalogue pages.
* Continues processing when an individual page fails.

Cached pages do not require a new request or delay.

---

## Why No Browser Was Used

A browser automation tool was not necessary for this target.

Books to Scrape provides the required catalogue and book information directly in server-rendered HTML. The required data can therefore be retrieved using normal HTTP requests and parsed with Beautiful Soup.

Using direct HTTP requests keeps the scraper simple and appropriate for the limited three-page scope of this assignment.

---

## Honest Limitation

This project is intentionally limited to the first three catalogue pages of Books to Scrape.

It is a learning-focused scraper rather than a general-purpose crawling framework.

The scraper also depends on the current HTML structure of Books to Scrape. Changes to the site's markup could require updates to the extraction selectors.

The project should not be reused on another website without first checking that site's rules, terms, and applicable restrictions.

---

## Ethics Note

This project was created for the controlled Books to Scrape practice environment.

The scraper uses:

* A descriptive User-Agent
* Request timeouts
* Delays between real requests
* Local caching
* Limited crawling scope
* Failure isolation
* No paid proxies or bypass mechanisms

> I will not reuse this code on another site without checking its rules and terms first.

---

## Stage 6 — Publication

The project is prepared for publication as a public GitHub repository containing:

* Scraper source code
* Dependency information
* Documentation
* Sample JSON output
* Run report evidence

The local HTML cache is excluded from version control because it is generated data and is not required for another user to understand or run the scraper.

The repository provides a copy-paste installation and run process so that a new user can set up the project and execute the scraper without relying on the developer's local environment.

The published repository should contain the project source and sample evidence, but should not contain the generated HTML cache.

---

## Project Pipeline

The complete scraper pipeline is:

```text
Fetch
  ↓
Extract
  ↓
Normalize
  ↓
Validate
  ↓
Store
  ↓
Report
```

The final implementation demonstrates:

* Catalogue discovery
* HTML parsing
* Book detail extraction
* Data normalization
* Pydantic validation
* JSON storage
* Local caching
* Request politeness
* Failure isolation
* Retry handling
* Honest run reporting
