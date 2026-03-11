"""
Download raw SEC filings (10-K, 10-Q, 8-K) for the company universe.

Excludes amendments. Stores HTML/text in data/raw/sec_filings/{cik}/{accession}.html.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from datetime import date

import pandas as pd
import requests

from ..common.config import ProjectConfig, load_config
from .sec_index_downloader import load_filing_index, _session, RATE_LIMIT_DELAY

SEC_BASE = "https://www.sec.gov"


def _filing_url(filename: str) -> str:
    """Build SEC URL from index filename (e.g. edgar/data/320193/0000320193-20-000123.txt)."""
    fn = str(filename).strip()
    if fn.startswith("edgar/"):
        return f"{SEC_BASE}/Archives/{fn}"
    return f"{SEC_BASE}/Archives/edgar/data/{fn}"


def download_filings(
    config: ProjectConfig | None = None,
    companies_path: Path | None = None,
    index_dir: Path | None = None,
    raw_dir: Path | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    skip_existing: bool = True,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Download target-form filings (10-K, 10-Q, 8-K) for the company universe.

    Returns a DataFrame of filing metadata (accession_number, cik, form_type, etc.)
    for successfully downloaded filings.
    """
    cfg = config or load_config()
    companies_path = companies_path or (cfg.paths.companies / "companies.parquet")
    index_dir = index_dir or cfg.paths.raw_sec_index
    raw_dir = raw_dir or cfg.paths.raw_sec_filings
    year_start = year_start or cfg.years.history_start
    year_end = year_end or cfg.years.max_year

    companies = pd.read_parquet(companies_path)
    ciks = set(companies["cik"].astype(str).str.zfill(10))

    filings = load_filing_index(
        index_dir,
        year_start=year_start,
        year_end=year_end,
        form_types=cfg.forms.target_forms,
        exclude_amendments=cfg.forms.exclude_amendments,
    )
    filings = filings[filings["cik"].isin(ciks)]
    if limit:
        filings = filings.head(limit)

    sess = _session()
    results = []
    for _, row in filings.iterrows():
        cik = str(row["cik"]).zfill(10)
        acc = row["accession_number"]
        # Use hyphenated accession for filename (SEC standard)
        acc_display = _to_accession_display(acc)
        out_path = raw_dir / cik / f"{acc_display}.txt"

        if skip_existing and out_path.exists():
            results.append(_row_to_filing_meta(row, str(out_path)))
            continue

        url = _filing_url(row["filename"])
        try:
            r = sess.get(url, timeout=120)
            r.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(r.content)
            results.append(_row_to_filing_meta(row, str(out_path)))
        except Exception as e:
            # Log but continue
            print(f"Failed {cik} {acc}: {e}")
        time.sleep(RATE_LIMIT_DELAY)

    return pd.DataFrame(results)


def _to_accession_display(acc: str) -> str:
    """Convert 000032019320000123 to 0000320193-20-000123 for display/filename."""
    acc = re.sub(r"\D", "", str(acc))
    if len(acc) >= 18:
        return f"{acc[:10]}-{acc[10:12]}-{acc[12:]}"
    return acc


def _row_to_filing_meta(row: pd.Series, local_path: str) -> dict:
    fd = pd.to_datetime(row["date_filed"])
    return {
        "accession_number": _to_accession_display(row["accession_number"]),
        "cik": str(row["cik"]).zfill(10),
        "form_type": row["form_type"],
        "filing_date": fd.date() if hasattr(fd, "date") else fd,
        "period_of_report": None,
        "fiscal_year": int(fd.year) if hasattr(fd, "year") else None,
        "filing_year_bucket": int(fd.year) if hasattr(fd, "year") else None,
        "source_url": _filing_url(row["filename"]),
        "local_path_raw": local_path,
        "local_path_clean": None,
        "text_version": "raw",
        "has_parsing_errors": False,
    }
