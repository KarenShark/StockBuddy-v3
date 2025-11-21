from dataclasses import dataclass
from pathlib import Path


@dataclass
class SECFilingMetadata:
    doc_type: str
    company: str
    period_of_report: str
    filing_date: str


@dataclass
class SECFilingResult:
    name: str
    path: Path
    metadata: SECFilingMetadata


@dataclass
class AShareFilingMetadata:
    """A-share filing metadata"""

    doc_type: (
        str  # Report type: annual report, semi-annual report, quarterly report, etc.
    )
    company: str  # Company name
    stock_code: str  # Stock code
    market: str  # Market: SZSE, SSE
    period_of_report: str  # Report period
    filing_date: str  # Filing date
    announcement_title: str = ""  # Announcement title for quarter filtering


@dataclass
class AShareFilingResult:
    """A-share filing result"""

    name: str
    path: Path
    metadata: AShareFilingMetadata


@dataclass
class HKEXRSSItem:
    """HKEX RSS feed item"""

    title: str  # Item title
    link: str  # Item URL
    summary: str  # Item summary
    published: str  # Publication date


@dataclass
class HKEXFilingMetadata:
    """HKEX policy document metadata"""

    document_type: str  # Document type: circular, listing_rules, etc.
    title: str  # Document title
    fetch_date: str  # Date when document was fetched
    source_url: str  # Source URL


@dataclass
class HKEXFilingResult:
    """HKEX policy document result"""

    name: str  # File name
    path: str  # File path or URL
    metadata: HKEXFilingMetadata  # Metadata
