import pytest
from unittest.mock import patch, MagicMock
import scraper


# --- _parse_price ---

def test_parse_price_dollar_sign():
    assert scraper._parse_price("$89.99") == 89.99


def test_parse_price_plain_number():
    assert scraper._parse_price("89.99") == 89.99


def test_parse_price_with_commas():
    assert scraper._parse_price("1,234.56") == 1234.56


def test_parse_price_returns_none_for_garbage():
    assert scraper._parse_price("Out of stock") is None


def test_parse_price_returns_none_for_none():
    assert scraper._parse_price(None) is None


# --- _extract_from_html ---

def test_extract_jsonld_single_product():
    html = """<html><head>
    <script type="application/ld+json">
    {"@type": "Product", "offers": {"price": "89.99", "priceCurrency": "USD"}}
    </script>
    </head><body></body></html>"""
    assert scraper._extract_from_html(html) == 89.99


def test_extract_jsonld_list_of_products():
    html = """<html><head>
    <script type="application/ld+json">
    [{"@type": "Product", "offers": {"price": "120.00"}}]
    </script>
    </head><body></body></html>"""
    assert scraper._extract_from_html(html) == 120.00


def test_extract_meta_product_price():
    html = '<html><head><meta property="product:price:amount" content="59.99"></head><body></body></html>'
    assert scraper._extract_from_html(html) == 59.99


def test_extract_itemprop_content_attr():
    html = '<html><body><span itemprop="price" content="75.00">$75.00</span></body></html>'
    assert scraper._extract_from_html(html) == 75.00


def test_extract_itemprop_text_content():
    html = '<html><body><span itemprop="price">$75.00</span></body></html>'
    assert scraper._extract_from_html(html) == 75.00


def test_extract_css_class_product_price():
    html = '<html><body><span class="product-price">$89.99</span></body></html>'
    assert scraper._extract_from_html(html) == 89.99


def test_extract_css_class_price():
    html = '<html><body><div class="price">$110.00</div></body></html>'
    assert scraper._extract_from_html(html) == 110.00


def test_extract_returns_none_when_no_price():
    html = "<html><body><p>No price here</p></body></html>"
    assert scraper._extract_from_html(html) is None


# --- get_price ---

def test_get_price_uses_static_when_price_found():
    html = """<html><head>
    <script type="application/ld+json">{"offers": {"price": "89.99"}}</script>
    </head></html>"""
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        price = scraper.get_price("https://example.com/product")

    assert price == 89.99


def test_get_price_falls_back_to_playwright():
    static_html = "<html><body>Loading...</body></html>"
    rendered_html = '<html><body><span itemprop="price" content="99.99">$99.99</span></body></html>'

    mock_resp = MagicMock()
    mock_resp.text = static_html
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        with patch("scraper._fetch_playwright", return_value=rendered_html):
            price = scraper.get_price("https://example.com/product")

    assert price == 99.99


def test_get_price_raises_when_all_strategies_fail():
    empty_html = "<html><body>Loading...</body></html>"

    mock_resp = MagicMock()
    mock_resp.text = empty_html
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        with patch("scraper._fetch_playwright", return_value=empty_html):
            with pytest.raises(ValueError, match="Could not extract price"):
                scraper.get_price("https://example.com/product")


def test_get_price_uses_playwright_when_static_fetch_fails():
    rendered_html = '<html><body><span itemprop="price" content="45.00">$45.00</span></body></html>'

    with patch("httpx.get", side_effect=Exception("connection refused")):
        with patch("scraper._fetch_playwright", return_value=rendered_html):
            price = scraper.get_price("https://example.com/product")

    assert price == 45.00
