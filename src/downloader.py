"""Image downloader for GGStore products."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .models import CrawlResult, ProductImage

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Async image downloader with metadata tracking."""

    def __init__(
        self,
        output_dir: Path | str = "data/images",
        metadata_file: Path | str = "data/metadata.json",
        max_concurrent: int = 5,
    ):
        """Initialize downloader.

        Args:
            output_dir: Directory to save images
            metadata_file: Path to metadata JSON file
            max_concurrent: Max concurrent downloads
        """
        self.output_dir = Path(output_dir)
        self.metadata_file = Path(metadata_file)
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client: httpx.AsyncClient | None = None

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self) -> "ImageDownloader":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_filename(self, product_id: str, index: int, url: str) -> str:
        """Generate filename for image.

        Args:
            product_id: Product identifier
            index: Image index
            url: Original image URL

        Returns:
            Filename with extension
        """
        # Extract extension from URL
        path = urlparse(url).path
        ext = Path(path).suffix.lower()
        if not ext or ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            ext = '.jpg'

        return f"{product_id}_{index:02d}{ext}"

    async def download_image(self, url: str, filepath: Path) -> bool:
        """Download a single image.

        Args:
            url: Image URL
            filepath: Destination file path

        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Downloader not started. Use async context manager.")

        async with self._semaphore:
            try:
                response = await self._client.get(url)
                response.raise_for_status()

                filepath.write_bytes(response.content)
                logger.debug(f"Downloaded: {filepath.name}")
                return True

            except httpx.HTTPError as e:
                logger.error(f"Failed to download {url}: {e}")
                return False

    async def download_product_images(
        self,
        product_id: str,
        image_urls: list[str],
    ) -> list[ProductImage]:
        """Download all images for a product.

        Args:
            product_id: Product identifier
            image_urls: List of image URLs

        Returns:
            List of ProductImage objects
        """
        images: list[ProductImage] = []
        tasks = []

        for i, url in enumerate(image_urls, 1):
            filename = self._get_filename(product_id, i, url)
            filepath = self.output_dir / filename

            # Skip if already downloaded
            if filepath.exists():
                logger.debug(f"Skipping existing: {filename}")
                images.append(ProductImage(
                    filename=filename,
                    original_url=url,
                    local_path=str(filepath),
                    downloaded_at=datetime.now(),
                ))
                continue

            tasks.append((url, filepath, filename))

        # Download new images
        for url, filepath, filename in tasks:
            success = await self.download_image(url, filepath)
            if success:
                images.append(ProductImage(
                    filename=filename,
                    original_url=url,
                    local_path=str(filepath),
                    downloaded_at=datetime.now(),
                ))

        return images

    def load_metadata(self) -> CrawlResult | None:
        """Load existing metadata from file.

        Returns:
            CrawlResult or None if not exists
        """
        if not self.metadata_file.exists():
            return None

        try:
            data = json.loads(self.metadata_file.read_text(encoding='utf-8'))
            return CrawlResult.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

    def save_metadata(self, result: CrawlResult) -> None:
        """Save metadata to file.

        Args:
            result: CrawlResult to save
        """
        data = result.model_dump(mode='json')
        self.metadata_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        logger.info(f"Metadata saved: {self.metadata_file}")

    def get_downloaded_product_ids(self) -> set[str]:
        """Get set of already downloaded product IDs.

        Returns:
            Set of product IDs
        """
        metadata = self.load_metadata()
        if metadata:
            return {p.id for p in metadata.products}
        return set()
