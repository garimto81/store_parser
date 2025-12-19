"""Checklist models for GGStore crawling task management."""

from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a crawling job or task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class JobType(str, Enum):
    """Type of crawling job."""

    FULL_CRAWL = "full_crawl"
    INCREMENTAL = "incremental"
    RETRY_FAILED = "retry_failed"
    SINGLE_PRODUCT = "single_product"


class ErrorType(str, Enum):
    """Type of error encountered during crawling."""

    CRAWL_FAILED = "crawl_failed"
    PARSE_FAILED = "parse_failed"
    DOWNLOAD_FAILED = "download_failed"
    TIMEOUT = "timeout"


class SessionProgress(BaseModel):
    """Real-time progress tracking for current session."""

    products_discovered: int = Field(default=0, description="Total products found")
    products_crawled: int = Field(default=0, description="Products successfully crawled")
    products_skipped: int = Field(default=0, description="Products skipped (already exists)")
    images_downloaded: int = Field(default=0, description="Images successfully downloaded")
    images_failed: int = Field(default=0, description="Images failed to download")
    current_page: int = Field(default=1, description="Current pagination page")
    last_product_url: str | None = Field(default=None, description="Last processed product URL")


class CurrentSession(BaseModel):
    """Current crawling session information."""

    id: str = Field(description="Session identifier")
    started_at: datetime = Field(default_factory=datetime.now)
    status: JobStatus = Field(default=JobStatus.PENDING)
    agent: str | None = Field(default=None, description="Agent handling this session")
    progress: SessionProgress = Field(default_factory=SessionProgress)


class JobConfig(BaseModel):
    """Configuration for a crawl job."""

    headless: bool = Field(default=True, description="Run browser in headless mode")
    delay_seconds: float = Field(default=1.5, description="Delay between requests")
    max_concurrent_downloads: int = Field(default=5, description="Max concurrent image downloads")
    skip_existing: bool = Field(default=True, description="Skip already downloaded products")
    output_dir: str = Field(default="data/images", description="Image output directory")
    metadata_file: str = Field(default="data/metadata.json", description="Metadata file path")


class JobExecution(BaseModel):
    """Execution details for a crawl job."""

    agent: str | None = Field(default=None, description="Agent that executed the job")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_seconds: int | None = Field(default=None)


class JobResult(BaseModel):
    """Result of a completed crawl job."""

    success: bool = Field(default=False)
    total_products: int = Field(default=0)
    total_images: int = Field(default=0)
    new_products: int = Field(default=0)
    new_images: int = Field(default=0)
    skipped_products: int = Field(default=0)
    failed_downloads: int = Field(default=0)
    error_message: str | None = Field(default=None)


class CrawlJob(BaseModel):
    """A crawling job definition and status."""

    id: str = Field(description="Job identifier")
    type: JobType = Field(description="Type of crawl job")
    status: JobStatus = Field(default=JobStatus.PENDING)
    priority: str = Field(default="medium", description="Job priority: high, medium, low")
    execution: JobExecution = Field(default_factory=JobExecution)
    config: JobConfig = Field(default_factory=JobConfig)
    result: JobResult | None = Field(default=None)
    files_modified: list[str] = Field(default_factory=list)


class ProductCrawlInfo(BaseModel):
    """Crawl tracking information for a product."""

    first_seen: datetime = Field(description="When product was first discovered")
    last_crawled: datetime = Field(description="Last crawl timestamp")
    crawl_count: int = Field(default=1, description="Number of times crawled")
    job_id: str = Field(description="Job that last crawled this product")


class ProductImageStatus(BaseModel):
    """Image download status for a product."""

    total: int = Field(default=0, description="Total images found")
    downloaded: int = Field(default=0, description="Successfully downloaded")
    failed: int = Field(default=0, description="Failed to download")
    status: JobStatus = Field(default=JobStatus.PENDING)


class ProductPrice(BaseModel):
    """Price tracking for a product."""

    current: str | None = Field(default=None, description="Current price")
    last_seen: datetime | None = Field(default=None)


class ProductEntry(BaseModel):
    """A product entry in the checklist."""

    id: str = Field(description="Product identifier")
    name: str = Field(description="Product name")
    url: str = Field(description="Product page URL")
    status: JobStatus = Field(default=JobStatus.PENDING)
    crawl_info: ProductCrawlInfo | None = Field(default=None)
    images: ProductImageStatus = Field(default_factory=ProductImageStatus)
    price: ProductPrice = Field(default_factory=ProductPrice)
    category: str | None = Field(default=None)
    errors: list[str] = Field(default_factory=list)


class ErrorEntry(BaseModel):
    """An error log entry."""

    id: str = Field(description="Error identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    job_id: str = Field(description="Job where error occurred")
    product_id: str | None = Field(default=None)
    type: ErrorType = Field(description="Type of error")
    url: str | None = Field(default=None, description="URL that caused the error")
    message: str = Field(description="Error message")
    retry_count: int = Field(default=0)
    resolved: bool = Field(default=False)


class JobStats(BaseModel):
    """Statistics for jobs."""

    total: int = Field(default=0)
    completed: int = Field(default=0)
    failed: int = Field(default=0)
    pending: int = Field(default=0)


class DownloadStats(BaseModel):
    """Statistics for downloads."""

    successful: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)


class Stats(BaseModel):
    """Overall statistics for the checklist."""

    total_products: int = Field(default=0)
    total_images: int = Field(default=0)
    jobs: JobStats = Field(default_factory=JobStats)
    downloads: DownloadStats = Field(default_factory=DownloadStats)
    by_category: dict[str, int] = Field(default_factory=dict)
    last_full_crawl: datetime | None = Field(default=None)
    last_incremental: datetime | None = Field(default=None)
    average_crawl_time_seconds: int | None = Field(default=None)


class MetadataSync(BaseModel):
    """Sync status with metadata.json."""

    file: str = Field(default="data/metadata.json")
    last_sync: datetime | None = Field(default=None)
    products_in_metadata: int = Field(default=0)
    images_in_metadata: int = Field(default=0)
    sync_status: str = Field(default="in_sync", description="in_sync, out_of_sync, needs_rebuild")


class StoreParserChecklist(BaseModel):
    """Main checklist model for GGStore crawling task management."""

    version: str = Field(default="1.0")
    project: str = Field(default="ggp_store_parser")
    target_site: str = Field(default="https://ggstore.com")
    platform: str = Field(default="Shopify")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    current_session: CurrentSession | None = Field(default=None)
    jobs: list[CrawlJob] = Field(default_factory=list)
    products: list[ProductEntry] = Field(default_factory=list)
    errors: list[ErrorEntry] = Field(default_factory=list)
    stats: Stats = Field(default_factory=Stats)
    metadata_sync: MetadataSync = Field(default_factory=MetadataSync)

    def save(self, filepath: Path | str) -> None:
        """Save checklist to YAML file."""
        filepath = Path(filepath)
        self.updated_at = datetime.now()
        data = self.model_dump(mode="json")
        filepath.write_text(
            yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, filepath: Path | str) -> "StoreParserChecklist":
        """Load checklist from YAML file."""
        filepath = Path(filepath)
        if not filepath.exists():
            return cls()
        data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
        if data is None:
            return cls()
        return cls.model_validate(data)
