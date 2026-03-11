Temporal Competition Graph from SEC Filings
===========================================

This repository contains a research-grade pipeline for building a temporally evaluated, directed, weighted competition graph over U.S. public companies using SEC filings (10-K, 10-Q, 8-K).

The near-term focus is on:

- **Spec and schemas**: Locking down the project specification, data schemas, and leakage policy.
- **Data foundation**: Building a clean company universe and filing corpus keyed by CIK.
- **Evidence layers**: Designing explicit, implicit, and event-based competition evidence representations.

### Next steps pipeline

After the filing download and cleaning pipeline runs, the planned **alias and entity-resolution pipeline** is:

1. **Canonical company table** — SEC CIK-based identity (e.g. `company_tickers.json`) → one table keyed by CIK (name, ticker, etc.).
2. **Alias generation** — Normalized name variants, ticker aliases, and historical former names with time windows (from/to).
3. **Alias scoring** — Score by source quality, string quality, ambiguity, and time validity (high/medium/lower confidence).
4. **Mention resolution** — For each mention: generate candidate CIKs from aliases (with time validity), rank by industry fit and context, then **auto-resolve** only when the top candidate is clearly stronger; otherwise send to an **unresolved audit table**.
5. **Outputs** — Canonical company table, alias table (scores + time validity), resolved mentions (for the graph), unresolved audit table.

Only high-confidence resolutions feed the main graph; ambiguous cases stay in audit for review. Full prompt and implementation notes: `docs/GEMINI_PROMPT_NEXT_STEPS.md`.

---

For full technical details, see `docs/spec.md` (once populated).

