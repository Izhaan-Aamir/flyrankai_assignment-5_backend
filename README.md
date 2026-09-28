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

- Title
- Product URL
- Price
- Availability
- Rating
- Description
- Source catalogue page
- Fetch timestamp

The scraped information will later be cleaned, validated, and stored as JSON.

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

## Stage 1 — Fetch and Cache

The scraper downloads the first Books to Scrape catalogue page:

```text
https://books.toscrape.com/catalogue/page-1.html
```

The request uses:

- An identifying User-Agent
- A 5-second timeout
- HTTP status-code validation

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

## Stage 2 — Discover Three Catalogue Pages

The scraper now parses the saved catalogue HTML using Beautiful Soup.

It starts from catalogue page 1 and follows the catalogue's `Next` link until exactly three catalogue pages have been processed.

For each catalogue page, the scraper:

1. Finds every book link.
2. Converts relative links into absolute URLs.
3. Adds the URLs to a set to remove duplicates.
4. Follows the `Next` catalogue link.
5. Stops after three catalogue pages.

The scraper also waits at least 0.5 seconds before each new real catalogue-page request. Cached pages do not require a delay.

### Stage 2 Checkpoint

Expected result:

```text
catalogue_pages=3
discovered=60
unique_urls=60