"""
Download SEC EDGAR filing index and company metadata.

Uses SEC full-index files (company.idx) and company_tickers.json.
Respects SEC rate limits; use User-Agent per SEC guidelines.

SEC requires: User-Agent with format "CompanyName AdminContact@company.com"
Update config sec_user_agent with your real email. 403 = blocked (bad User-Agent or cloud IP).
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Iterator

import pandas as pd
import requests

SEC_BASE = "https://www.sec.gov"
RATE_LIMIT_DELAY = 0.2  # ~5 req/sec to stay under SEC limit
MAX_RETRIES = 3


def _get_user_agent() -> str:
    """User-Agent from config, env, or fallback. SEC requires real contact info."""
    ua = os.environ.get("SEC_USER_AGENT")
    if ua:
        return ua
    try:
        from ..common.config import load_config
        cfg = load_config()
        ua = getattr(cfg, "sec_user_agent", "") or ""
        if ua and "example.com" not in ua.lower():
            return ua
    except Exception:
        pass
    return "temporal-competition-graph research project / contact@example.com"


def _session(user_agent: str | None = None) -> requests.Session:
    ua = user_agent or _get_user_agent()
    s = requests.Session()
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov",
    })
    return s


def _get(url: str, session: requests.Session | None = None) -> str:
    sess = session or _session()
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            r = sess.get(url, timeout=90)
            r.raise_for_status()
            time.sleep(RATE_LIMIT_DELAY)
            return r.text
        except requests.HTTPError as e:
            last_err = e
            if e.response.status_code in (403, 429):
                wait = (attempt + 1) * 2
                print(f"SEC {e.response.status_code}, retry in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise last_err


def download_company_tickers(out_path: Path) -> Path:
    """Download SEC company_tickers.json (CIK, ticker, name) to out_path."""
    url = f"{SEC_BASE}/files/company_tickers.json"
    text = _get(url)
    data = json.loads(text)
    # Normalize to list of dicts
    rows = []
    for k, v in data.items():
        rows.append({
            "cik": str(v["cik_str"]).zfill(10),
            "ticker": v.get("ticker"),
            "company_name": v.get("title", ""),
        })
    df = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return out_path


def _parse_company_idx(text: str) -> pd.DataFrame:
    """Parse SEC company.idx format. Skip header lines until we find pipe-delimited data."""
    lines = text.strip().split("\n")
    # Skip header: find first line with Company Name|Form Type|CIK|Date Filed|Filename pattern
    data_lines = []
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 5 and parts[2].strip().isdigit():  # CIK is numeric
            data_lines.append(line)
    rows = []
    for line in data_lines:
        parts = line.split("|")
        if len(parts) >= 5:
            company_name, form_type, cik, date_filed, filename = parts[0], parts[1], parts[2], parts[3], parts[4]
            cik = str(cik).zfill(10)
            rows.append({
                "company_name": company_name.strip(),
                "form_type": form_type.strip(),
                "cik": cik,
                "date_filed": date_filed.strip(),
                "filename": filename.strip(),
            })
    return pd.DataFrame(rows)


def download_quarterly_index(year: int, quarter: int, out_path: Path) -> Path:
    """Download company.idx for a given year/quarter."""
    qtr = f"QTR{quarter}"
    url = f"{SEC_BASE}/Archives/edgar/full-index/{year}/{qtr}/company.idx"
    text = _get(url)
    df = _parse_company_idx(text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    return out_path


def download_sec_index(
    out_dir: Path,
    year_start: int = 2015,
    year_end: int = 2025,
) -> tuple[Path, list[Path]]:
    """
    Download SEC company tickers and full-index files for each year/quarter.

    Returns:
        (company_tickers_path, list of quarterly index paths)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tickers_path = out_dir / "company_tickers.parquet"
    download_company_tickers(tickers_path)

    index_paths = []
    sess = _session()
    for year in range(year_start, year_end + 1):
        for qtr in range(1, 5):
            qpath = out_dir / f"full_index_{year}_QTR{qtr}.parquet"
            download_quarterly_index(year, qtr, qpath)
            index_paths.append(qpath)

    return tickers_path, index_paths


def load_filing_index(
    index_dir: Path,
    year_start: int = 2015,
    year_end: int = 2025,
    form_types: list[str] | None = None,
    exclude_amendments: bool = True,
) -> pd.DataFrame:
    """
    Load and concatenate quarterly indices, filter by form type.

    form_types: e.g. ["10-K", "10-Q", "8-K"]. If None, use all.
    exclude_amendments: drop 10-K/A, 10-Q/A, etc.
    """
    amendment_suffix = re.compile(r"/A$")

    dfs = []
    for year in range(year_start, year_end + 1):
        for qtr in range(1, 5):
            p = index_dir / f"full_index_{year}_QTR{qtr}.parquet"
            if not p.exists():
                continue
            df = pd.read_parquet(p)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined["date_filed"] = pd.to_datetime(combined["date_filed"], errors="coerce")
    combined = combined.dropna(subset=["date_filed"])
    combined["filing_year"] = combined["date_filed"].dt.year.astype(int)

    if exclude_amendments:
        combined = combined[~combined["form_type"].str.match(amendment_suffix, na=False)]

    if form_types:
        combined = combined[combined["form_type"].isin(form_types)]

    # Build accession number from filename (e.g. edgar/data/320193/0000320193-20-000123.txt -> 0000320193-20-000123)
    def _extract_accession(fn: str) -> str:
        s = str(fn).strip()
        s = re.sub(r"^edgar/data/\d+/", "", s)
        return s.replace(".txt", "") if s else ""

    combined["accession_number"] = combined["filename"].apply(_extract_accession)
    # Keep original filename for URL construction
    combined["filename"] = combined["filename"].astype(str)

    return combined.sort_values(["cik", "date_filed"]).reset_index(drop=True)
