Temporal Competition Graph from SEC Filings
===========================================

This repository contains a research-grade pipeline for building a temporally evaluated, directed, weighted competition graph over U.S. public companies using SEC filings (10-K, 10-Q, 8-K).

**Current scope:**
- **Universe**: 2023–2025 only (10-K, 10-Q, 8-K; no amendments).
- **Data foundation**: Company universe + filing download + cleaning (Colab/Drive supported).
- **Next**: Explicit competitor extraction, implicit/event evidence, yearly edge aggregation.

For full technical details, see `docs/spec.md` (once populated).

