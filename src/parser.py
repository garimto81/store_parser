"""HTML parser for GGStore product pages."""

import html
import logging
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class GGStoreParser:
    """Parser for GGStore product HTML."""

    CDN_PATTERN = re.compile(r'//ggstore\.com/cdn/shop/')
    IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')

    def __init__(self, base_url: str = "https://ggstore.com"):
        """Initialize parser.

        Args:
            base_url: Base URL for resolving relative URLs
        """
        self.base_url = base_url

    def parse_product(self, html: str, url: str) -> dict:
        """Parse product information from HTML.

        Args:
            html: HTML content
            url: Product page URL

        Returns:
            Dictionary with product info
        """
        product_id = self._extract_product_id(url)
        name = self._extract_product_name(html)
        price = self._extract_price(html)
        category = self._extract_category(html)
        image_urls = self._extract_image_urls(html)

        return {
            "id": product_id,
            "name": name,
            "url": url,
            "price": price,
            "category": category,
            "image_urls": image_urls,
        }

    def _extract_product_id(self, url: str) -> str:
        """Extract product ID from URL.

        Args:
            url: Product URL

        Returns:
            Product ID
        """
        # URL format: /products/product-name
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        if 'products' in parts:
            idx = parts.index('products')
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return path.strip('/').replace('/', '-')

    def _extract_product_name(self, html: str) -> str:
        """Extract product name from HTML.

        Args:
            html: HTML content

        Returns:
            Product name
        """
        # Try meta og:title first
        og_title_match = re.search(
            r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE
        )
        if og_title_match:
            return og_title_match.group(1).strip()

        # Try title tag
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # Remove site name suffix
            if '|' in title:
                title = title.split('|')[0].strip()
            if '–' in title:
                title = title.split('–')[0].strip()
            return title

        # Try h1 tag
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()

        return "Unknown Product"

    def _extract_price(self, html: str) -> str | None:
        """Extract product price from HTML.

        Args:
            html: HTML content

        Returns:
            Price string or None
        """
        # Look for price patterns
        price_patterns = [
            r'<span[^>]*class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*\$?([\d,.]+)',
            r'"price":\s*"?\$?([\d,.]+)',
            r'data-price=["\'](\d+)',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price = match.group(1).strip()
                if price:
                    return f"${price}"

        return None

    def _extract_category(self, html: str) -> str | None:
        """Extract product category from HTML.

        Args:
            html: HTML content

        Returns:
            Category name or None
        """
        # Look for breadcrumb or collection links
        breadcrumb_match = re.search(
            r'/collections/([^/"\'?\s]+)',
            html
        )
        if breadcrumb_match:
            category = breadcrumb_match.group(1)
            if category.lower() != 'all':
                return category.upper().replace('-', ' ')

        return None

    def _extract_image_urls(self, html: str) -> list[str]:
        """Extract all product image URLs from HTML.

        Args:
            html: HTML content

        Returns:
            List of image URLs (high resolution)
        """
        image_urls: set[str] = set()

        # Pattern 1: srcset attributes (Shopify lazy loading)
        srcset_pattern = re.compile(
            r'srcset=["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        for match in srcset_pattern.finditer(html):
            srcset = match.group(1)
            for src in srcset.split(','):
                url = src.strip().split()[0]
                if self._is_product_image(url):
                    image_urls.add(self._normalize_url(url))

        # Pattern 2: src attributes
        src_pattern = re.compile(
            r'src=["\']([^"\']+(?:cdn/shop/(?:files|products)/)[^"\']+)["\']',
            re.IGNORECASE
        )
        for match in src_pattern.finditer(html):
            url = match.group(1)
            if self._is_product_image(url):
                image_urls.add(self._normalize_url(url))

        # Pattern 3: data-src attributes (lazy loading)
        data_src_pattern = re.compile(
            r'data-src=["\']([^"\']+)["\']',
            re.IGNORECASE
        )
        for match in data_src_pattern.finditer(html):
            url = match.group(1)
            if self._is_product_image(url):
                image_urls.add(self._normalize_url(url))

        # Pattern 4: JSON data
        json_pattern = re.compile(
            r'"src":\s*"([^"]+cdn/shop/[^"]+)"',
            re.IGNORECASE
        )
        for match in json_pattern.finditer(html):
            url = match.group(1).replace('\\/', '/')
            if self._is_product_image(url):
                image_urls.add(self._normalize_url(url))

        logger.debug(f"Found {len(image_urls)} unique images")
        return sorted(image_urls)

    def _is_product_image(self, url: str) -> bool:
        """Check if URL is a product image.

        Args:
            url: Image URL

        Returns:
            True if it's a product image
        """
        if not url:
            return False

        # Must be from CDN
        if 'cdn/shop/' not in url:
            return False

        # Must have image extension
        url_path = urlparse(url).path.lower()
        has_ext = any(url_path.endswith(ext) or ext + '?' in url_path.lower()
                      for ext in self.IMAGE_EXTENSIONS)

        # Also check for extension before query params
        if not has_ext:
            for ext in self.IMAGE_EXTENSIONS:
                if ext in url_path:
                    has_ext = True
                    break

        return has_ext

    def _normalize_url(self, url: str) -> str:
        """Normalize image URL to get highest resolution.

        Args:
            url: Original image URL

        Returns:
            Normalized URL with https and no query params (original size)
        """
        # Decode HTML entities (e.g., &amp; -> &)
        url = html.unescape(url)

        # Fix protocol-relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith('http'):
            url = urljoin(self.base_url, url)

        # Remove all query parameters to get original image
        # Shopify CDN provides same image with different width params
        parsed = urlparse(url)
        normalized = parsed._replace(query='').geturl()

        return normalized
