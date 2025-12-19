"""Main entry point for GGStore image crawler."""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from .checklist import ErrorType, JobConfig, JobResult, JobStatus, JobType
from .checklist_manager import ChecklistManager
from .crawler import GGStoreCrawler
from .downloader import ImageDownloader
from .models import CrawlResult, Product
from .parser import GGStoreParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


async def run_crawler(
    output_dir: str = "data/images",
    metadata_file: str = "data/metadata.json",
    checklist_file: str = "store_parser_checklist.yaml",
    headless: bool = True,
    delay: float = 1.5,
    skip_existing: bool = True,
) -> CrawlResult:
    """Run the GGStore image crawler with checklist tracking.

    Args:
        output_dir: Directory to save images
        metadata_file: Path to metadata JSON file
        checklist_file: Path to checklist YAML file
        headless: Run browser in headless mode
        delay: Delay between requests in seconds
        skip_existing: Skip already downloaded products

    Returns:
        CrawlResult with all crawled data
    """
    # Initialize checklist manager
    checklist_mgr = ChecklistManager(checklist_file)

    # Create job configuration
    job_config = JobConfig(
        headless=headless,
        delay_seconds=delay,
        skip_existing=skip_existing,
        output_dir=output_dir,
        metadata_file=metadata_file,
    )

    # Create and start job
    job = checklist_mgr.create_job(JobType.FULL_CRAWL, job_config, priority="high")
    checklist_mgr.start_session("crawler-agent")
    checklist_mgr.start_job(job.id, "crawler-agent")

    parser = GGStoreParser()
    result = CrawlResult(crawled_at=datetime.now())
    skipped_count = 0
    crawled_count = 0

    try:
        async with ImageDownloader(output_dir, metadata_file) as downloader:
            # Get already downloaded products
            existing_ids = downloader.get_downloaded_product_ids() if skip_existing else set()
            if existing_ids:
                logger.info(f"Found {len(existing_ids)} already downloaded products")

            async with GGStoreCrawler(headless=headless, delay=delay) as crawler:
                # Get all product URLs
                product_urls = await crawler.get_product_urls()
                logger.info(f"Found {len(product_urls)} products to process")

                # Update checklist with discovered products
                checklist_mgr.update_session_progress(products_discovered=len(product_urls))

                # Process each product
                for i, url in enumerate(product_urls, 1):
                    product_id = parser._extract_product_id(url)

                    # Skip if already downloaded
                    if product_id in existing_ids:
                        logger.info(f"[{i}/{len(product_urls)}] Skipping existing: {product_id}")
                        skipped_count += 1
                        checklist_mgr.update_session_progress(
                            products_skipped=skipped_count,
                            last_product_url=url,
                        )
                        continue

                    logger.info(f"[{i}/{len(product_urls)}] Processing: {product_id}")

                    try:
                        # Fetch and parse product page
                        html = await crawler.get_product_html(url)
                        product_data = parser.parse_product(html, url)

                        # Download images
                        images = await downloader.download_product_images(
                            product_id=product_data["id"],
                            image_urls=product_data["image_urls"],
                        )

                        # Create product record
                        product = Product(
                            id=product_data["id"],
                            name=product_data["name"],
                            url=product_data["url"],
                            price=product_data["price"],
                            category=product_data["category"],
                            images=images,
                            crawled_at=datetime.now(),
                        )
                        result.add_product(product)
                        crawled_count += 1

                        # Track product in checklist
                        checklist_mgr.add_or_update_product(
                            product_id=product_data["id"],
                            name=product_data["name"],
                            url=url,
                            job_id=job.id,
                            status=JobStatus.COMPLETED,
                            image_count=len(product_data["image_urls"]),
                            downloaded_count=len(images),
                            failed_count=len(product_data["image_urls"]) - len(images),
                            price=product_data["price"],
                            category=product_data["category"],
                        )

                        # Update session progress
                        checklist_mgr.update_session_progress(
                            products_crawled=crawled_count,
                            images_downloaded=result.total_images,
                            last_product_url=url,
                        )

                        logger.info(
                            f"  Downloaded {len(images)} images for '{product.name}'"
                        )

                        # Save metadata periodically
                        if i % 10 == 0:
                            downloader.save_metadata(result)

                    except Exception as e:
                        logger.error(f"Failed to process {url}: {e}")
                        # Log error to checklist
                        checklist_mgr.log_error(
                            job_id=job.id,
                            error_type=ErrorType.CRAWL_FAILED,
                            message=str(e),
                            product_id=product_id,
                            url=url,
                        )
                        continue

                # Final save
                downloader.save_metadata(result)

        # Complete job successfully
        job_result = JobResult(
            success=True,
            total_products=result.total_products,
            total_images=result.total_images,
            new_products=result.total_products,
            new_images=result.total_images,
            skipped_products=skipped_count,
        )
        checklist_mgr.complete_job(job.id, job_result)
        checklist_mgr.sync_from_metadata(result)
        checklist_mgr.end_session(JobStatus.COMPLETED)

    except Exception as e:
        # Complete job with failure
        job_result = JobResult(
            success=False,
            error_message=str(e),
        )
        checklist_mgr.complete_job(job.id, job_result)
        checklist_mgr.end_session(JobStatus.FAILED)
        raise

    logger.info(f"Crawl complete: {result.total_products} products, {result.total_images} images")
    return result


def show_status(checklist_file: str) -> int:
    """Show checklist status."""
    mgr = ChecklistManager(checklist_file)
    print(mgr.print_status())
    return 0


def show_errors(checklist_file: str, limit: int = 10) -> int:
    """Show error log."""
    mgr = ChecklistManager(checklist_file)
    errors = mgr.get_unresolved_errors()

    if not errors:
        print("No unresolved errors.")
        return 0

    print(f"=== Unresolved Errors ({len(errors)} total) ===\n")
    for error in errors[:limit]:
        print(f"[{error.id}] {error.timestamp.isoformat()}")
        print(f"  Type: {error.type.value}")
        print(f"  Job: {error.job_id}")
        if error.product_id:
            print(f"  Product: {error.product_id}")
        if error.url:
            print(f"  URL: {error.url}")
        print(f"  Message: {error.message}")
        print()

    if len(errors) > limit:
        print(f"... and {len(errors) - limit} more errors")

    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GGStore Image Crawler - Download all product images"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Crawl command (default)
    crawl_parser = subparsers.add_parser("crawl", help="Run the crawler")
    crawl_parser.add_argument(
        "-o", "--output",
        default="data/images",
        help="Output directory for images (default: data/images)"
    )
    crawl_parser.add_argument(
        "-m", "--metadata",
        default="data/metadata.json",
        help="Metadata file path (default: data/metadata.json)"
    )
    crawl_parser.add_argument(
        "-c", "--checklist",
        default="store_parser_checklist.yaml",
        help="Checklist file path (default: store_parser_checklist.yaml)"
    )
    crawl_parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window"
    )
    crawl_parser.add_argument(
        "-d", "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)"
    )
    crawl_parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-download existing products"
    )
    crawl_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show checklist status")
    status_parser.add_argument(
        "-c", "--checklist",
        default="store_parser_checklist.yaml",
        help="Checklist file path"
    )

    # Errors command
    errors_parser = subparsers.add_parser("errors", help="Show error log")
    errors_parser.add_argument(
        "-c", "--checklist",
        default="store_parser_checklist.yaml",
        help="Checklist file path"
    )
    errors_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of errors to show (default: 10)"
    )

    args = parser.parse_args()

    # Handle status command
    if args.command == "status":
        return show_status(args.checklist)

    # Handle errors command
    if args.command == "errors":
        return show_errors(args.checklist, args.limit)

    # Handle crawl command (or no command for backwards compatibility)
    if args.command == "crawl" or args.command is None:
        # For backwards compatibility when no subcommand is given
        if args.command is None:
            # Re-parse with default crawl args
            args = crawl_parser.parse_args([])

        if hasattr(args, "verbose") and args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        try:
            result = asyncio.run(run_crawler(
                output_dir=args.output,
                metadata_file=args.metadata,
                checklist_file=args.checklist,
                headless=not args.no_headless,
                delay=args.delay,
                skip_existing=not args.no_skip,
            ))

            print(f"\n{'='*50}")
            print("Crawl Complete!")
            print(f"{'='*50}")
            print(f"Total Products: {result.total_products}")
            print(f"Total Images:   {result.total_images}")
            print(f"Output Dir:     {args.output}")
            print(f"Metadata:       {args.metadata}")
            print(f"Checklist:      {args.checklist}")
            print(f"{'='*50}")

            return 0

        except KeyboardInterrupt:
            logger.info("Crawl interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
