"""Checklist manager for GGStore crawling tasks."""

import uuid
from datetime import datetime
from pathlib import Path

from .checklist import (
    CrawlJob,
    CurrentSession,
    ErrorEntry,
    ErrorType,
    JobConfig,
    JobResult,
    JobStatus,
    JobType,
    ProductCrawlInfo,
    ProductEntry,
    ProductImageStatus,
    ProductPrice,
    SessionProgress,
    StoreParserChecklist,
)
from .models import CrawlResult


class ChecklistManager:
    """Manager for the crawling checklist."""

    def __init__(self, checklist_path: Path | str = "store_parser_checklist.yaml"):
        self.checklist_path = Path(checklist_path)
        self.checklist = StoreParserChecklist.load(self.checklist_path)

    def save(self) -> None:
        """Save current checklist state."""
        self.checklist.save(self.checklist_path)

    def reload(self) -> None:
        """Reload checklist from file."""
        self.checklist = StoreParserChecklist.load(self.checklist_path)

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(self, agent: str = "crawler-agent") -> CurrentSession:
        """Start a new crawling session."""
        session = CurrentSession(
            id=f"SESSION-{uuid.uuid4().hex[:8].upper()}",
            started_at=datetime.now(),
            status=JobStatus.IN_PROGRESS,
            agent=agent,
            progress=SessionProgress(),
        )
        self.checklist.current_session = session
        self.save()
        return session

    def update_session_progress(
        self,
        products_discovered: int | None = None,
        products_crawled: int | None = None,
        products_skipped: int | None = None,
        images_downloaded: int | None = None,
        images_failed: int | None = None,
        current_page: int | None = None,
        last_product_url: str | None = None,
    ) -> None:
        """Update current session progress."""
        if not self.checklist.current_session:
            return

        progress = self.checklist.current_session.progress
        if products_discovered is not None:
            progress.products_discovered = products_discovered
        if products_crawled is not None:
            progress.products_crawled = products_crawled
        if products_skipped is not None:
            progress.products_skipped = products_skipped
        if images_downloaded is not None:
            progress.images_downloaded = images_downloaded
        if images_failed is not None:
            progress.images_failed = images_failed
        if current_page is not None:
            progress.current_page = current_page
        if last_product_url is not None:
            progress.last_product_url = last_product_url

        self.save()

    def end_session(self, status: JobStatus = JobStatus.COMPLETED) -> None:
        """End current session."""
        if self.checklist.current_session:
            self.checklist.current_session.status = status
        self.save()

    # =========================================================================
    # Job Management
    # =========================================================================

    def create_job(
        self,
        job_type: JobType,
        config: JobConfig | None = None,
        priority: str = "medium",
    ) -> CrawlJob:
        """Create a new crawl job."""
        job_id = f"JOB-{len(self.checklist.jobs) + 1:03d}"
        job = CrawlJob(
            id=job_id,
            type=job_type,
            status=JobStatus.PENDING,
            priority=priority,
            config=config or JobConfig(),
        )
        self.checklist.jobs.append(job)
        self.checklist.stats.jobs.total += 1
        self.checklist.stats.jobs.pending += 1
        self.save()
        return job

    def start_job(self, job_id: str, agent: str) -> CrawlJob | None:
        """Start a job execution."""
        job = self._find_job(job_id)
        if not job:
            return None

        job.status = JobStatus.IN_PROGRESS
        job.execution.agent = agent
        job.execution.started_at = datetime.now()

        if self.checklist.stats.jobs.pending > 0:
            self.checklist.stats.jobs.pending -= 1
        self.save()
        return job

    def complete_job(self, job_id: str, result: JobResult) -> CrawlJob | None:
        """Complete a job with results."""
        job = self._find_job(job_id)
        if not job:
            return None

        job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
        job.execution.completed_at = datetime.now()

        if job.execution.started_at:
            duration = (job.execution.completed_at - job.execution.started_at).seconds
            job.execution.duration_seconds = duration

        job.result = result

        # Update stats
        if result.success:
            self.checklist.stats.jobs.completed += 1
            if job.type == JobType.FULL_CRAWL:
                self.checklist.stats.last_full_crawl = datetime.now()
            elif job.type == JobType.INCREMENTAL:
                self.checklist.stats.last_incremental = datetime.now()
        else:
            self.checklist.stats.jobs.failed += 1

        self.save()
        return job

    def _find_job(self, job_id: str) -> CrawlJob | None:
        """Find a job by ID."""
        for job in self.checklist.jobs:
            if job.id == job_id:
                return job
        return None

    def get_pending_jobs(self) -> list[CrawlJob]:
        """Get all pending jobs."""
        return [job for job in self.checklist.jobs if job.status == JobStatus.PENDING]

    # =========================================================================
    # Product Tracking
    # =========================================================================

    def add_or_update_product(
        self,
        product_id: str,
        name: str,
        url: str,
        job_id: str,
        status: JobStatus = JobStatus.COMPLETED,
        image_count: int = 0,
        downloaded_count: int = 0,
        failed_count: int = 0,
        price: str | None = None,
        category: str | None = None,
    ) -> ProductEntry:
        """Add or update a product entry."""
        existing = self._find_product(product_id)
        now = datetime.now()

        if existing:
            existing.status = status
            if existing.crawl_info:
                existing.crawl_info.last_crawled = now
                existing.crawl_info.crawl_count += 1
                existing.crawl_info.job_id = job_id
            existing.images.total = image_count
            existing.images.downloaded = downloaded_count
            existing.images.failed = failed_count
            existing.images.status = status
            if price:
                existing.price.current = price
                existing.price.last_seen = now
            if category:
                existing.category = category
            product = existing
        else:
            product = ProductEntry(
                id=product_id,
                name=name,
                url=url,
                status=status,
                crawl_info=ProductCrawlInfo(
                    first_seen=now,
                    last_crawled=now,
                    crawl_count=1,
                    job_id=job_id,
                ),
                images=ProductImageStatus(
                    total=image_count,
                    downloaded=downloaded_count,
                    failed=failed_count,
                    status=status,
                ),
                price=ProductPrice(
                    current=price,
                    last_seen=now if price else None,
                ),
                category=category,
            )
            self.checklist.products.append(product)
            self.checklist.stats.total_products = len(self.checklist.products)

            # Update category stats
            if category:
                if category not in self.checklist.stats.by_category:
                    self.checklist.stats.by_category[category] = 0
                self.checklist.stats.by_category[category] += 1

        self.save()
        return product

    def _find_product(self, product_id: str) -> ProductEntry | None:
        """Find a product by ID."""
        for product in self.checklist.products:
            if product.id == product_id:
                return product
        return None

    def get_failed_products(self) -> list[ProductEntry]:
        """Get all products with failed status."""
        return [p for p in self.checklist.products if p.status == JobStatus.FAILED]

    # =========================================================================
    # Error Tracking
    # =========================================================================

    def log_error(
        self,
        job_id: str,
        error_type: ErrorType,
        message: str,
        product_id: str | None = None,
        url: str | None = None,
    ) -> ErrorEntry:
        """Log an error."""
        error = ErrorEntry(
            id=f"ERR-{len(self.checklist.errors) + 1:03d}",
            timestamp=datetime.now(),
            job_id=job_id,
            product_id=product_id,
            type=error_type,
            url=url,
            message=message,
        )
        self.checklist.errors.append(error)
        self.save()
        return error

    def get_unresolved_errors(self) -> list[ErrorEntry]:
        """Get all unresolved errors."""
        return [e for e in self.checklist.errors if not e.resolved]

    def resolve_error(self, error_id: str) -> bool:
        """Mark an error as resolved."""
        for error in self.checklist.errors:
            if error.id == error_id:
                error.resolved = True
                self.save()
                return True
        return False

    # =========================================================================
    # Metadata Sync
    # =========================================================================

    def sync_from_metadata(self, crawl_result: CrawlResult) -> None:
        """Sync checklist with existing metadata.json."""
        self.checklist.stats.total_products = crawl_result.total_products
        self.checklist.stats.total_images = crawl_result.total_images
        self.checklist.stats.downloads.successful = crawl_result.total_images

        self.checklist.metadata_sync.last_sync = datetime.now()
        self.checklist.metadata_sync.products_in_metadata = crawl_result.total_products
        self.checklist.metadata_sync.images_in_metadata = crawl_result.total_images
        self.checklist.metadata_sync.sync_status = "in_sync"

        self.save()

    # =========================================================================
    # Summary & Reporting
    # =========================================================================

    def get_summary(self) -> dict:
        """Get a summary of the checklist state."""
        return {
            "project": self.checklist.project,
            "target_site": self.checklist.target_site,
            "updated_at": self.checklist.updated_at.isoformat(),
            "current_session": {
                "id": self.checklist.current_session.id if self.checklist.current_session else None,
                "status": (
                    self.checklist.current_session.status.value
                    if self.checklist.current_session
                    else None
                ),
                "progress": (
                    self.checklist.current_session.progress.model_dump()
                    if self.checklist.current_session
                    else None
                ),
            },
            "stats": {
                "total_products": self.checklist.stats.total_products,
                "total_images": self.checklist.stats.total_images,
                "jobs_total": self.checklist.stats.jobs.total,
                "jobs_completed": self.checklist.stats.jobs.completed,
                "jobs_pending": self.checklist.stats.jobs.pending,
                "jobs_failed": self.checklist.stats.jobs.failed,
                "errors_count": len(self.checklist.errors),
                "unresolved_errors": len(self.get_unresolved_errors()),
            },
            "metadata_sync": {
                "status": self.checklist.metadata_sync.sync_status,
                "last_sync": (
                    self.checklist.metadata_sync.last_sync.isoformat()
                    if self.checklist.metadata_sync.last_sync
                    else None
                ),
            },
        }

    def print_status(self) -> str:
        """Get a formatted status string."""
        summary = self.get_summary()
        lines = [
            f"=== {summary['project']} Checklist Status ===",
            f"Target: {summary['target_site']}",
            f"Updated: {summary['updated_at']}",
            "",
            "Session:",
            f"  ID: {summary['current_session']['id'] or 'None'}",
            f"  Status: {summary['current_session']['status'] or 'No active session'}",
            "",
            "Statistics:",
            f"  Products: {summary['stats']['total_products']}",
            f"  Images: {summary['stats']['total_images']}",
            f"  Jobs: {summary['stats']['jobs_completed']}/{summary['stats']['jobs_total']}",
            f"  Errors: {summary['stats']['unresolved_errors']} unresolved",
            "",
            "Metadata Sync:",
            f"  Status: {summary['metadata_sync']['status']}",
            f"  Last Sync: {summary['metadata_sync']['last_sync'] or 'Never'}",
        ]
        return "\n".join(lines)
