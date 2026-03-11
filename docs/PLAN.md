# Project Plan

## Current Scope (Updated)

- **Universe**: 2023–2025 only
- **Forms**: 10-K, 10-Q, 8-K (no amendments)
- **Company inclusion**: Firms with at least one 10-K in 2023–2025

## Completed

1. Spec, assumptions, schemas, config
2. SEC index download (company tickers + quarterly indices)
3. Company universe construction
4. Filing download (10-K, 10-Q, 8-K)
5. Filing cleaning (HTML removal, section segmentation, sentence chunks, deduplication)
6. Colab/Drive support, SEC User-Agent handling

## Next Steps (in order)

1. **Explicit competitor extraction** – Rule-based patterns + entity resolution for named competitors
2. **Implicit evidence pipeline** – Sentence-level signals (product overlap, pricing pressure, etc.)
3. **Event evidence (8-K)** – Structured event extraction
4. **Yearly edge aggregation** – Combine evidence into `(source_cik, target_cik, year)` weights
5. **Temporal splits + leakage checks** – Train 2023, val 2024, test 2025
6. **GNN modeling** – GAT, baselines (persistence, heuristics, GraphSAGE)

## Config Reference

| Setting | Value |
|---------|-------|
| universe_start | 2023 |
| universe_end | 2025 |
| target_forms | 10-K, 10-Q, 8-K |
| exclude_amendments | true |
