"""Playwright-based crawler for GGStore."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)


class GGStoreCrawler:
    """Crawler for GGStore product pages."""

    BASE_URL = "https://ggstore.com"
    COLLECTION_URL = f"{BASE_URL}/collections/all"

    def __init__(self, headless: bool = True, delay: float = 1.0):
        """Initialize crawler.

        Args:
            headless: Run browser in headless mode
            delay: Delay between requests in seconds
        """
        self.headless = headless
        self.delay = delay
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> "GGStoreCrawler":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Start the browser."""
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()

        # Set user agent to avoid bot detection
        await self._page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        logger.info("Browser started")

    async def close(self) -> None:
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
            logger.info("Browser closed")

    async def _wait(self) -> None:
        """Wait between requests."""
        await asyncio.sleep(self.delay)

    async def get_product_urls(self) -> list[str]:
        """Get all product URLs from the collection page.

        Returns:
            List of product URLs
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        product_urls: list[str] = []
        page_num = 1

        while True:
            url = f"{self.COLLECTION_URL}?page={page_num}"
            logger.info(f"Fetching page {page_num}: {url}")

            await self._page.goto(url, wait_until="networkidle")
            await self._wait()

            # Find product links
            product_links = await self._page.query_selector_all(
                'a[href*="/products/"]'
            )

            if not product_links:
                logger.info(f"No products found on page {page_num}, stopping")
                break

            page_urls = []
            for link in product_links:
                href = await link.get_attribute("href")
                if href and "/products/" in href:
                    full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    if full_url not in product_urls and full_url not in page_urls:
                        page_urls.append(full_url)

            if not page_urls:
                logger.info("No new products found, stopping pagination")
                break

            product_urls.extend(page_urls)
            logger.info(f"Found {len(page_urls)} products on page {page_num}")

            page_num += 1

            # Safety limit
            if page_num > 50:
                logger.warning("Reached page limit (50), stopping")
                break

        logger.info(f"Total products found: {len(product_urls)}")
        return product_urls

    async def get_product_html(self, url: str) -> str:
        """Get HTML content of a product page.

        Args:
            url: Product page URL

        Returns:
            HTML content
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        logger.debug(f"Fetching product: {url}")
        await self._page.goto(url, wait_until="networkidle")
        await self._wait()

        return await self._page.content()

    async def crawl_products(self) -> AsyncGenerator[tuple[str, str], None]:
        """Crawl all products and yield URL and HTML.

        Yields:
            Tuple of (product_url, html_content)
        """
        product_urls = await self.get_product_urls()

        for i, url in enumerate(product_urls, 1):
            logger.info(f"Processing product {i}/{len(product_urls)}: {url}")
            try:
                html = await self.get_product_html(url)
                yield url, html
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                continue
