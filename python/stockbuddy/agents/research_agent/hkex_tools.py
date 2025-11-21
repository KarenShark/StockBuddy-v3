"""HKEX (Hong Kong Exchange) data fetching tools for Research Agent.

This module provides two main approaches to fetch HKEX data:
1. RSS Feed Tool - Real-time news and announcements
2. RAG-based Policy Document Search - Deep policy and regulatory documents

Author: StockBuddy Team
Date: 2025
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiohttp
import feedparser
from loguru import logger

from stockbuddy.utils.path import get_knowledge_path

from .knowledge import insert_pdf_file_to_knowledge
from .schemas import HKEXFilingMetadata, HKEXFilingResult, HKEXRSSItem

# ============================================
# 方案一：RSS 实时信息流工具
# ============================================


async def fetch_hkex_rss_feed(
    feed_type: str = "news",
    language: str = "en",
    limit: int = 10,
) -> List[HKEXRSSItem]:
    """从港交所官方 RSS 源获取最新动态、新闻和公告。

    这个工具用于获取实时信息，如最新的监管公告、新闻稿等。
    适用场景：回答"港交所今天有什么新公告？"或"最近有什么市场通告？"

    Args:
        feed_type: RSS 源类型，支持：
            - "news": 新闻稿 (News Releases)
            - "regulatory": 监管公告 (Regulatory Announcements)
            - "circulars": 通函 (Circulars)
            - "notices": 市场通知 (Market Notices)
        language: 语言选择
            - "sc": 简体中文
            - "tc": 繁体中文
            - "en": 英文
        limit: 返回的最大条目数，默认 10

    Returns:
        List[HKEXRSSItem]: RSS 条目列表，包含标题、链接、摘要和发布日期

    Examples:
        # 获取最新的新闻稿（英文，推荐）
        items = await fetch_hkex_rss_feed("news", "en", 10)

        # 获取最新的监管公告（简体中文）
        items = await fetch_hkex_rss_feed("regulatory", "sc", 5)
    """
    # RSS 源 URL 映射
    # 注意：港交所的中文 RSS 源目前可能内容较少或为空，建议优先使用英文源
    rss_urls = {
        "news": {
            "sc": "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=zh-CN",
            "tc": "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=zh-HK",
            "en": "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=en",
        },
        "regulatory": {
            "sc": "https://www.hkex.com.hk/Services/RSS-Feeds/Regulatory-Announcements?sc_lang=zh-CN",
            "tc": "https://www.hkex.com.hk/Services/RSS-Feeds/Regulatory-Announcements?sc_lang=zh-HK",
            "en": "https://www.hkex.com.hk/Services/RSS-Feeds/Regulatory-Announcements?sc_lang=en",
        },
        "circulars": {
            "sc": "https://www.hkex.com.hk/Services/RSS-Feeds/Circulars-and-Notices?sc_lang=zh-CN",
            "tc": "https://www.hkex.com.hk/Services/RSS-Feeds/Circulars-and-Notices?sc_lang=zh-HK",
            "en": "https://www.hkex.com.hk/Services/RSS-Feeds/Circulars-and-Notices?sc_lang=en",
        },
        "notices": {
            "sc": "https://www.hkex.com.hk/Services/RSS-Feeds/Market-Notices?sc_lang=zh-CN",
            "tc": "https://www.hkex.com.hk/Services/RSS-Feeds/Market-Notices?sc_lang=zh-HK",
            "en": "https://www.hkex.com.hk/Services/RSS-Feeds/Market-Notices?sc_lang=en",
        },
    }

    # 验证参数
    if feed_type not in rss_urls:
        raise ValueError(
            f"Invalid feed_type: {feed_type}. Supported types: {list(rss_urls.keys())}"
        )

    if language not in rss_urls[feed_type]:
        raise ValueError(
            f"Invalid language: {language}. "
            f"Supported languages: {list(rss_urls[feed_type].keys())}"
        )

    feed_url = rss_urls[feed_type][language]

    logger.info(f"Fetching HKEX RSS feed: {feed_type} ({language})")

    try:
        # 使用 feedparser 解析 RSS
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            logger.warning(f"No entries found in RSS feed: {feed_url}")
            return []

        # 提取条目信息
        items = []
        for entry in feed.entries[:limit]:
            item = HKEXRSSItem(
                title=entry.get("title", ""),
                link=entry.get("link", ""),
                summary=entry.get("summary", ""),
                published=entry.get("published", ""),
            )
            items.append(item)

        logger.info(f"Successfully fetched {len(items)} items from HKEX RSS")
        return items

    except Exception as e:
        logger.error(f"Error fetching HKEX RSS feed: {e}")
        raise


# ============================================
# 方案二：深度政策文档库（Web Scraping + RAG）
# ============================================


async def fetch_hkex_policy_documents(
    document_type: str = "circular",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    limit: int = 10,
) -> List[HKEXFilingResult]:
    """从港交所网站抓取政策文档（通函、规则等）并导入知识库。

    这个工具用于获取和查询具体的政策文件、通函和规则。
    适用场景：回答"港交所关于 SPAC 的规则是什么？"或"找一下最近关于互联互通的通函。"

    注意：这个函数会将文档导入到 RAG 知识库中，以便后续查询。

    Args:
        document_type: 文档类型
            - "circular": 通函
            - "listing_rules": 上市规则
            - "consultation_papers": 咨询文件
            - "guidelines": 指引
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        keywords: 关键词列表，用于过滤文档
        limit: 返回的最大文档数，默认 10

    Returns:
        List[HKEXFilingResult]: 文档列表，包含文件名、路径和元数据

    Examples:
        # 获取最近的通函
        docs = await fetch_hkex_policy_documents("circular", limit=5)

        # 获取 2024 年关于 SPAC 的文档
        docs = await fetch_hkex_policy_documents(
            "circular",
            start_date="2024-01-01",
            end_date="2024-12-31",
            keywords=["SPAC", "特殊目的收购公司"],
            limit=10
        )
    """
    # 文档类型 URL 映射
    base_urls = {
        "circular": "https://www.hkex.com.hk/Services/Circulars-and-Notices/Participant-and-Members-Circulars",
        "listing_rules": "https://www.hkex.com.hk/Listing/Rules-and-Guidance/Listing-Rules",
        "consultation_papers": "https://www.hkex.com.hk/News/Market-Consultations/Consultation-Papers",
        "guidelines": "https://www.hkex.com.hk/Listing/Rules-and-Guidance/Other-Resources/Guidance-Materials",
    }

    if document_type not in base_urls:
        raise ValueError(
            f"Invalid document_type: {document_type}. "
            f"Supported types: {list(base_urls.keys())}"
        )

    logger.info(
        f"Fetching HKEX policy documents: {document_type} "
        f"(from {start_date or 'any'} to {end_date or 'any'})"
    )

    try:
        # 调用爬虫函数抓取文档
        documents = await _scrape_hkex_documents(
            base_urls[document_type],
            document_type,
            start_date,
            end_date,
            keywords,
            limit,
        )

        # 写入本地并导入知识库
        knowledge_dir = Path(get_knowledge_path()) / "hkex"
        results = await _write_and_ingest_hkex(documents, knowledge_dir)

        logger.info(f"Successfully fetched and ingested {len(results)} HKEX documents")
        return results

    except Exception as e:
        logger.error(f"Error fetching HKEX policy documents: {e}")
        raise


async def _scrape_hkex_documents(
    base_url: str,
    document_type: str,
    start_date: Optional[str],
    end_date: Optional[str],
    keywords: Optional[List[str]],
    limit: int,
) -> List[dict]:
    """爬取港交所网站的文档列表。

    这是一个内部函数，用于从港交所网站抓取文档信息。

    Args:
        base_url: 基础 URL
        document_type: 文档类型
        start_date: 开始日期
        end_date: 结束日期
        keywords: 关键词列表
        limit: 最大文档数

    Returns:
        List[dict]: 文档信息列表
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }

    documents = []

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(
                        f"Failed to fetch HKEX page: {base_url}, "
                        f"status: {response.status}"
                    )
                    return []

                html = await response.text()

                # 使用正则表达式提取文档链接和标题
                # 这是一个简化的实现，实际应该使用 BeautifulSoup4
                # 这里提供基础模板，具体解析逻辑需要根据实际页面结构调整

                # 提取 PDF 链接模式（示例）
                pdf_pattern = r'href="([^"]*\.pdf)"[^>]*>([^<]+)'
                matches = re.findall(pdf_pattern, html, re.IGNORECASE)

                for pdf_url, title in matches[:limit]:
                    # 如果是相对路径，补全为绝对路径
                    if not pdf_url.startswith("http"):
                        if pdf_url.startswith("/"):
                            pdf_url = f"https://www.hkex.com.hk{pdf_url}"
                        else:
                            pdf_url = f"{base_url}/{pdf_url}"

                    # 关键词过滤
                    if keywords:
                        if not any(kw.lower() in title.lower() for kw in keywords):
                            continue

                    # 构建文档信息
                    doc_info = {
                        "title": title.strip(),
                        "url": pdf_url,
                        "document_type": document_type,
                        "fetch_date": datetime.now().strftime("%Y-%m-%d"),
                    }

                    documents.append(doc_info)

                    if len(documents) >= limit:
                        break

        except Exception as e:
            logger.error(f"Error scraping HKEX documents: {e}")
            raise

    return documents


async def _write_and_ingest_hkex(
    documents: List[dict],
    knowledge_dir: Path,
) -> List[HKEXFilingResult]:
    """将港交所文档写入本地并导入知识库。

    Args:
        documents: 文档信息列表
        knowledge_dir: 知识库目录

    Returns:
        List[HKEXFilingResult]: 文档结果列表
    """
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    results: List[HKEXFilingResult] = []

    for doc in documents:
        title = doc["title"]
        pdf_url = doc["url"]
        document_type = doc["document_type"]
        fetch_date = doc["fetch_date"]

        # 创建元数据
        metadata = HKEXFilingMetadata(
            document_type=document_type,
            title=title,
            fetch_date=fetch_date,
            source_url=pdf_url,
        )

        # 生成文件名（使用标题的安全版本）
        safe_title = re.sub(r"[^\w\s-]", "", title)
        safe_title = re.sub(r"[-\s]+", "_", safe_title)
        file_name = f"HKEX_{document_type}_{safe_title[:50]}.pdf"

        # 创建结果对象
        result = HKEXFilingResult(
            name=file_name,
            path=pdf_url,
            metadata=metadata,
        )
        results.append(result)

        # 导入到知识库（使用 PDF URL）
        await insert_pdf_file_to_knowledge(url=pdf_url, metadata=metadata.__dict__)

    return results


# ============================================
# RAG 查询工具
# ============================================


async def search_hkex_policy(query: str, top_k: int = 5) -> str:
    """在港交所政策知识库中搜索相关内容。

    这个工具使用 RAG 技术，在已索引的港交所文档中进行语义搜索。
    必须先使用 fetch_hkex_policy_documents 导入文档到知识库。

    Args:
        query: 查询问题或关键词
        top_k: 返回最相关的前 k 个结果，默认 5

    Returns:
        str: 格式化的搜索结果，包含相关段落和来源信息

    Examples:
        # 查询 SPAC 相关规则
        result = await search_hkex_policy("港交所关于 SPAC 的规则是什么？")

        # 查询互联互通政策
        result = await search_hkex_policy("互联互通最新政策", top_k=3)
    """
    from .knowledge import knowledge

    logger.info(f"Searching HKEX policy with query: {query}")

    try:
        # 在知识库中搜索（需要先确保 knowledge 已经包含 HKEX 文档）
        results = await knowledge.asearch(query, num_results=top_k)

        if not results:
            return "未找到相关的港交所政策文档。请先使用 fetch_hkex_policy_documents 导入文档。"

        # 格式化输出
        formatted_results = "## 港交所政策文档搜索结果\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"### 结果 {i}\n"
            formatted_results += f"**相关度分数**: {getattr(result, 'score', 'N/A')}\n"
            formatted_results += f"**内容**:\n{getattr(result, 'content', '')}\n"

            # 提取元数据
            metadata = getattr(result, "metadata", {})
            if metadata:
                formatted_results += f"**来源**: {metadata.get('source_url', 'N/A')}\n"
                formatted_results += (
                    f"**文档类型**: {metadata.get('document_type', 'N/A')}\n"
                )
                formatted_results += f"**标题**: {metadata.get('title', 'N/A')}\n"
            formatted_results += "\n"

        return formatted_results

    except Exception as e:
        logger.error(f"Error searching HKEX policy: {e}")
        return f"搜索港交所政策时出错: {str(e)}"
