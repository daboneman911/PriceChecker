import re
import json
import httpx
from bs4 import BeautifulSoup

_PRICE_RE = re.compile(r"[\$£€]?\s*([\d,]+\.\d{2})")
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PriceTracker/1.0)"}


def _parse_price(text):
    if text is None:
        return None
    cleaned = str(text).replace(",", "")
    m = _PRICE_RE.search(cleaned)
    if m:
        try:
            return round(float(m.group(1)), 2)
        except ValueError:
            return None
    return None


def _extract_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                offers = entry.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0]
                price = _parse_price(str(offers.get("price", "")))
                if price is not None:
                    return price
        except (json.JSONDecodeError, AttributeError):
            continue

    # Strategy 2: Open Graph / meta tags
    for prop in ("product:price:amount", "og:price:amount"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag:
            price = _parse_price(tag.get("content"))
            if price is not None:
                return price

    # Strategy 3: Schema.org microdata
    tag = soup.find(attrs={"itemprop": "price"})
    if tag:
        price = _parse_price(tag.get("content") or tag.get_text())
        if price is not None:
            return price

    # Strategy 4: Common CSS class patterns
    for pattern in (r"product[-_]?price", r"\bprice\b", r"current[-_]?price", r"sale[-_]?price"):
        tag = soup.find(class_=re.compile(pattern, re.IGNORECASE))
        if tag:
            price = _parse_price(tag.get_text())
            if price is not None:
                return price

    return None


def _fetch_static(url):
    resp = httpx.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    return resp.text


def _fetch_playwright(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            return page.content()
        finally:
            browser.close()


def get_price(url):
    """
    Returns float price or raises ValueError if price cannot be extracted.
    Tries static extraction first; falls back to Playwright if needed.
    """
    # Static path
    try:
        html = _fetch_static(url)
        price = _extract_from_html(html)
        if price is not None:
            return price
    except Exception:
        pass

    # Playwright path
    try:
        html = _fetch_playwright(url)
    except Exception as exc:
        raise ValueError(f"Could not extract price from {url}") from exc

    price = _extract_from_html(html)
    if price is not None:
        return price

    raise ValueError(f"Could not extract price from {url}")
