"""Data models for GGStore crawler."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProductImage(BaseModel):
    """Individual product image metadata."""

    filename: str = Field(description="Local filename")
    original_url: str = Field(description="Original CDN URL")
    local_path: str = Field(description="Local file path")
    downloaded_at: datetime = Field(default_factory=datetime.now)


class Product(BaseModel):
    """Product information with images."""

    id: str = Field(description="Product identifier")
    name: str = Field(description="Product name")
    url: str = Field(description="Product page URL")
    price: str | None = Field(default=None, description="Product price")
    category: str | None = Field(default=None, description="Product category")
    images: list[ProductImage] = Field(default_factory=list)
    crawled_at: datetime = Field(default_factory=datetime.now)


class CrawlResult(BaseModel):
    """Complete crawl result."""

    products: list[Product] = Field(default_factory=list)
    crawled_at: datetime = Field(default_factory=datetime.now)
    total_products: int = Field(default=0)
    total_images: int = Field(default=0)

    def add_product(self, product: Product) -> None:
        """Add a product and update counts."""
        self.products.append(product)
        self.total_products = len(self.products)
        self.total_images = sum(len(p.images) for p in self.products)
