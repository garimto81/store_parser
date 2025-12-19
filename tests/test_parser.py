"""Tests for GGStore parser."""

import pytest

from src.parser import GGStoreParser


@pytest.fixture
def parser():
    """Create parser instance."""
    return GGStoreParser()


class TestExtractProductId:
    """Tests for product ID extraction."""

    def test_extract_from_standard_url(self, parser):
        url = "https://ggstore.com/products/classic-tee"
        assert parser._extract_product_id(url) == "classic-tee"

    def test_extract_with_query_params(self, parser):
        url = "https://ggstore.com/products/hoodie-black?variant=123"
        assert parser._extract_product_id(url) == "hoodie-black"

    def test_extract_with_trailing_slash(self, parser):
        url = "https://ggstore.com/products/cap-red/"
        assert parser._extract_product_id(url) == "cap-red"


class TestExtractProductName:
    """Tests for product name extraction."""

    def test_extract_from_og_title(self, parser):
        html = '<meta property="og:title" content="Classic T-Shirt">'
        assert parser._extract_product_name(html) == "Classic T-Shirt"

    def test_extract_from_title_tag(self, parser):
        html = "<title>Premium Hoodie | GGStore</title>"
        assert parser._extract_product_name(html) == "Premium Hoodie"

    def test_extract_from_h1(self, parser):
        html = "<h1 class='product-title'>Limited Edition Cap</h1>"
        assert parser._extract_product_name(html) == "Limited Edition Cap"

    def test_fallback_to_unknown(self, parser):
        html = "<div>No product name here</div>"
        assert parser._extract_product_name(html) == "Unknown Product"


class TestIsProductImage:
    """Tests for product image URL validation."""

    def test_valid_cdn_image(self, parser):
        url = "https://ggstore.com/cdn/shop/products/tee.jpg"
        assert parser._is_product_image(url) is True

    def test_non_cdn_url(self, parser):
        url = "https://example.com/image.jpg"
        assert parser._is_product_image(url) is False

    def test_non_image_url(self, parser):
        url = "https://ggstore.com/cdn/shop/products/data.json"
        assert parser._is_product_image(url) is False

    def test_empty_url(self, parser):
        assert parser._is_product_image("") is False


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_protocol_relative_url(self, parser):
        url = "//ggstore.com/cdn/shop/products/tee.jpg"
        assert parser._normalize_url(url).startswith("https://")

    def test_removes_query_params(self, parser):
        url = "https://ggstore.com/cdn/shop/products/tee.jpg?width=500"
        result = parser._normalize_url(url)
        assert "?" not in result

    def test_decodes_html_entities(self, parser):
        url = "https://ggstore.com/cdn/shop/products/tee.jpg?a=1&amp;b=2"
        result = parser._normalize_url(url)
        assert "&amp;" not in result
