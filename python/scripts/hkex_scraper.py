"""HKEX Document Scraper and Indexer Script

This script is designed to periodically scrape HKEX documents and index them
into the vector database for RAG-based querying.

Usage:
    python scripts/hkex_scraper.py --document-type circular --limit 20
    python scripts/hkex_scraper.py --all  # Scrape all document types
    python scripts/hkex_scraper.py --update-index  # Only update the index

Author: StockBuddy Team
Date: 2025
"""

import argparse
import asyncio

# Import HKEX tools
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from stockbuddy.agents.research_agent.hkex_tools import (
    fetch_hkex_policy_documents,
    fetch_hkex_rss_feed,
)


async def scrape_documents(
    document_types: list[str],
    limit_per_type: int = 50,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """抓取港交所文档并索引到知识库。

    Args:
        document_types: 要抓取的文档类型列表
        limit_per_type: 每种类型抓取的最大文档数
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    """
    logger.info("=" * 60)
    logger.info("HKEX Document Scraper Started")
    logger.info(f"Document Types: {document_types}")
    logger.info(f"Limit per Type: {limit_per_type}")
    logger.info(f"Date Range: {start_date or 'any'} to {end_date or 'any'}")
    logger.info("=" * 60)

    total_documents = 0

    for doc_type in document_types:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Scraping {doc_type.upper()} documents...")
        logger.info(f"{'=' * 60}")

        try:
            results = await fetch_hkex_policy_documents(
                document_type=doc_type,
                start_date=start_date,
                end_date=end_date,
                limit=limit_per_type,
            )

            logger.success(
                f"✓ Successfully scraped and indexed {len(results)} {doc_type} documents"
            )
            total_documents += len(results)

            # 显示抓取的文档
            for i, result in enumerate(results, 1):
                logger.info(
                    f"  {i}. {result.metadata.title[:60]}... "
                    f"({result.metadata.document_type})"
                )

        except Exception as e:
            logger.error(f"✗ Error scraping {doc_type}: {e}")
            continue

    logger.info(f"\n{'=' * 60}")
    logger.success(f"✓ Total documents scraped and indexed: {total_documents}")
    logger.info(f"{'=' * 60}")

    return total_documents


async def scrape_rss_feeds(feed_types: list[str], limit_per_feed: int = 20):
    """抓取港交所 RSS 动态。

    Args:
        feed_types: RSS 源类型列表
        limit_per_feed: 每个源抓取的最大条目数
    """
    logger.info("=" * 60)
    logger.info("HKEX RSS Feed Scraper Started")
    logger.info(f"Feed Types: {feed_types}")
    logger.info(f"Limit per Feed: {limit_per_feed}")
    logger.info("=" * 60)

    total_items = 0

    for feed_type in feed_types:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Fetching {feed_type.upper()} RSS feed...")
        logger.info(f"{'=' * 60}")

        try:
            items = await fetch_hkex_rss_feed(
                feed_type=feed_type,
                language="en",  # 使用英文源（更稳定）
                limit=limit_per_feed,
            )

            logger.success(f"✓ Successfully fetched {len(items)} {feed_type} RSS items")
            total_items += len(items)

            # 显示 RSS 条目
            for i, item in enumerate(items, 1):
                logger.info(f"  {i}. {item.title[:60]}... ({item.published})")

        except Exception as e:
            logger.error(f"✗ Error fetching {feed_type} RSS: {e}")
            continue

    logger.info(f"\n{'=' * 60}")
    logger.success(f"✓ Total RSS items fetched: {total_items}")
    logger.info(f"{'=' * 60}")

    return total_items


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="HKEX Document Scraper and Indexer")

    # 文档类型参数
    parser.add_argument(
        "--document-type",
        "-d",
        choices=["circular", "listing_rules", "consultation_papers", "guidelines"],
        help="Document type to scrape",
    )

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Scrape all document types",
    )

    # RSS 源参数
    parser.add_argument(
        "--rss",
        "-r",
        action="store_true",
        help="Fetch RSS feeds",
    )

    parser.add_argument(
        "--rss-type",
        choices=["news", "regulatory", "circulars", "notices"],
        help="RSS feed type to fetch",
    )

    # 通用参数
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=50,
        help="Maximum number of items to fetch per type (default: 50)",
    )

    parser.add_argument(
        "--start-date",
        help="Start date for document filtering (YYYY-MM-DD)",
    )

    parser.add_argument(
        "--end-date",
        help="End date for document filtering (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    # 如果没有指定任何参数，显示帮助
    if not (args.all or args.document_type or args.rss or args.rss_type):
        parser.print_help()
        return

    # 抓取文档
    if args.all:
        document_types = [
            "circular",
            "listing_rules",
            "consultation_papers",
            "guidelines",
        ]
        await scrape_documents(
            document_types,
            limit_per_type=args.limit,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    elif args.document_type:
        await scrape_documents(
            [args.document_type],
            limit_per_type=args.limit,
            start_date=args.start_date,
            end_date=args.end_date,
        )

    # 抓取 RSS
    if args.rss:
        feed_types = ["news", "regulatory", "circulars", "notices"]
        await scrape_rss_feeds(feed_types, limit_per_feed=args.limit)
    elif args.rss_type:
        await scrape_rss_feeds([args.rss_type], limit_per_feed=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
