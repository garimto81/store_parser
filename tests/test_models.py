"""Tests for Pydantic models."""

from datetime import datetime

import pytest

from src.models import CrawlResult, Product, ProductImage


class TestProductImage:
    """Tests for ProductImage model."""

    def test_create_image(self):
        image = ProductImage(
            filename="product_01.jpg",
            original_url="https://example.com/img.jpg",
            local_path="data/images/product_01.jpg",
        )
        assert image.filename == "product_01.jpg"
        assert isinstance(image.downloaded_at, datetime)


class TestProduct:
    """Tests for Product model."""

    def test_create_product(self):
        product = Product(
            id="test-product",
            name="Test Product",
            url="https://ggstore.com/products/test",
        )
        assert product.id == "test-product"
        assert product.price is None
        assert product.images == []

    def test_product_with_images(self):
        image = ProductImage(
            filename="test_01.jpg",
            original_url="https://example.com/img.jpg",
            local_path="data/images/test_01.jpg",
        )
        product = Product(
            id="test-product",
            name="Test Product",
            url="https://ggstore.com/products/test",
            images=[image],
        )
        assert len(product.images) == 1


class TestCrawlResult:
    """Tests for CrawlResult model."""

    def test_empty_result(self):
        result = CrawlResult()
        assert result.total_products == 0
        assert result.total_images == 0
        assert result.products == []

    def test_add_product(self):
        result = CrawlResult()
        image = ProductImage(
            filename="test_01.jpg",
            original_url="https://example.com/img.jpg",
            local_path="data/images/test_01.jpg",
        )
        product = Product(
            id="test-product",
            name="Test Product",
            url="https://ggstore.com/products/test",
            images=[image, image],
        )

        result.add_product(product)

        assert result.total_products == 1
        assert result.total_images == 2

    def test_add_multiple_products(self):
        result = CrawlResult()

        for i in range(3):
            product = Product(
                id=f"product-{i}",
                name=f"Product {i}",
                url=f"https://ggstore.com/products/product-{i}",
            )
            result.add_product(product)

        assert result.total_products == 3
