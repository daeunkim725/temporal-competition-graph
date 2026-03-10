from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Company:
    cik: str
    ticker: Optional[str]
    company_name: str
    sic: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    is_us_public: bool
    first_year: int
    last_year: int


@dataclass
class Filing:
    accession_number: str
    cik: str
    form_type: str
    filing_date: date
    period_of_report: Optional[date]
    fiscal_year: Optional[int]
    filing_year_bucket: int
    source_url: str
    local_path_raw: str
    local_path_clean: Optional[str]
    text_version: str
    has_parsing_errors: bool = False


@dataclass
class Evidence:
    accession_number: str
    evidence_id: str
    source_cik: str
    target_cik: Optional[str]
    target_name_str: Optional[str]
    signal_type: str  # explicit | implicit | event
    subtype: str
    section: Optional[str]
    snippet_start_char: Optional[int]
    snippet_end_char: Optional[int]
    snippet_text: str
    score: float
    direction: str  # expected "source_to_target"
    evidence_year: int
    resolution_confidence: Optional[float]


@dataclass
class YearlyEdge:
    source_cik: str
    target_cik: str
    year: int
    explicit_intensity: float
    implicit_intensity: float
    event_intensity: float
    fused_weight: float
    num_filings: int
    num_evidence_items: int


__all__ = ["Company", "Filing", "Evidence", "YearlyEdge"]

