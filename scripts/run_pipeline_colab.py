"""
Run Step 1 (company universe) and Step 2 (filing download + cleaning) on Google Colab.

Usage in Colab:
  1. Mount Google Drive
  2. cd to project directory
  3. Run: python scripts/run_pipeline_colab.py

Or import and call run_pipeline(drive_root="/content/drive/MyDrive/temporal-competition-graph")
"""

from __future__ import annotations

import sys
from pathlib import Path


def run_pipeline(
    drive_root: str | Path,
    config_path: str | Path | None = None,
    year_start: int = 2023,
    year_end: int = 2025,
    download_limit: int | None = None,
) -> None:
    """
    Run full pipeline: index download -> company universe -> filing download -> cleaning.

    drive_root: Path to project root on Google Drive (e.g. /content/drive/MyDrive/temporal-competition-graph)
    download_limit: If set, only download this many filings (for testing). None = all.
    """
    drive_root = Path(drive_root)
    config_path = config_path or (drive_root / "config" / "config.yaml")

    # Add project to path
    if str(drive_root) not in sys.path:
        sys.path.insert(0, str(drive_root))

    from src.common.config import load_config
    from src.data.sec_index_downloader import download_sec_index, load_filing_index
    from src.data.build_company_universe import build_company_universe
    from src.data.download_filings import download_filings
    from src.data.clean_filings import clean_filings, build_filings_table

    cfg = load_config(config_path=config_path, base_path=drive_root)

    print("Step 1a: Downloading SEC index...")
    download_sec_index(cfg.paths.raw_sec_index, year_start=year_start, year_end=year_end)

    print("Step 1b: Building company universe...")
    build_company_universe(config=cfg)

    print("Step 2a: Downloading filings...")
    filings_df = download_filings(
        config=cfg,
        year_start=year_start,
        year_end=year_end,
        limit=download_limit,
    )
    print(f"  Downloaded {len(filings_df)} filings")

    print("Step 2b: Cleaning filings...")
    cleaned_df = clean_filings(config=cfg, filings_df=filings_df)

    print("Step 2c: Building filings table...")
    build_filings_table(config=cfg, filings_df=cleaned_df)

    print("Done. Outputs in:", cfg.paths.processed_root)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--drive-root", default="/content/drive/MyDrive/temporal-competition-graph")
    p.add_argument("--year-start", type=int, default=2015)
    p.add_argument("--year-end", type=int, default=2025)
    p.add_argument("--download-limit", type=int, default=None, help="Limit filings for testing")
    args = p.parse_args()
    run_pipeline(
        drive_root=args.drive_root,
        year_start=args.year_start,
        year_end=args.year_end,
        download_limit=args.download_limit,
    )
