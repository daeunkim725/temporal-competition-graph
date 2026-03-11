"""
Build company universe from SEC index.

Includes firms that file at least one 10-K in the configured year range.
U.S. domestic issuers only for the initial pipeline (10-K, 10-Q, 8-K).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..common.config import ProjectConfig, load_config


def build_company_universe(
    config: ProjectConfig | None = None,
    index_dir: Path | None = None,
    tickers_path: Path | None = None,
    out_path: Path | None = None,
) -> pd.DataFrame:
    """
    Build companies.parquet from SEC index.

    Inclusion: at least one 10-K in [universe_start, universe_end].
    Sets first_year, last_year from observed filings (10-K, 10-Q, 8-K).
    """
    cfg = config or load_config()
    index_dir = index_dir or cfg.paths.raw_sec_index
    tickers_path = tickers_path or (index_dir / "company_tickers.parquet")
    out_path = out_path or (cfg.paths.companies / "companies.parquet")

    # Load tickers
    if not tickers_path.exists():
        raise FileNotFoundError(
            f"Company tickers not found at {tickers_path}. Run download_sec_index first."
        )
    tickers = pd.read_parquet(tickers_path)

    # Load filing index for target forms (10-K, 10-Q, 8-K) to compute first/last year
    from .sec_index_downloader import load_filing_index

    filings = load_filing_index(
        index_dir,
        year_start=cfg.years.universe_start,
        year_end=cfg.years.universe_end,
        form_types=cfg.forms.target_forms,
        exclude_amendments=cfg.forms.exclude_amendments,
    )

    if filings.empty:
        raise ValueError("No filings found in index. Check index_dir and form filters.")

    # Universe: firms with at least one 10-K
    tenk = filings[filings["form_type"] == "10-K"]
    universe_ciks = set(tenk["cik"].unique())

    # First/last year per CIK from all target-form filings
    agg = filings.groupby("cik").agg(
        first_year=("filing_year", "min"),
        last_year=("filing_year", "max"),
    ).reset_index()

    # Merge with tickers
    companies = tickers[tickers["cik"].isin(universe_ciks)].copy()
    companies = companies.drop_duplicates(subset=["cik"], keep="first")
    companies = companies.merge(agg, on="cik", how="left")

    # Fill missing SIC/sector/industry (we don't have them from tickers; add placeholders)
    for col in ["sic", "sector", "industry"]:
        if col not in companies.columns:
            companies[col] = None

    companies["issuer_type"] = "us_domestic"
    companies["is_us_public"] = True

    # Ensure required columns
    companies = companies[
        [
            "cik",
            "ticker",
            "company_name",
            "sic",
            "sector",
            "industry",
            "issuer_type",
            "is_us_public",
            "first_year",
            "last_year",
        ]
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    companies.to_parquet(out_path, index=False)
    return companies
