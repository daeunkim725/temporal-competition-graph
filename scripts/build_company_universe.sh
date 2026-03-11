#!/usr/bin/env bash
# Build company universe from SEC index. Run download_sec_index first.
set -e
cd "$(dirname "$0")/.."
python -c "
from src.common.config import load_config
from src.data.sec_index_downloader import download_sec_index
from src.data.build_company_universe import build_company_universe

cfg = load_config()
print('Downloading SEC index...')
download_sec_index(cfg.paths.raw_sec_index, cfg.years.history_start, cfg.years.max_year)
print('Building company universe...')
build_company_universe(config=cfg)
print('Done:', cfg.paths.companies / 'companies.parquet')
"
