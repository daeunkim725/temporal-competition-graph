## Project Assumptions

This document records explicit assumptions that shape the data pipeline, graph construction, and evaluation. Deviations or changes must be versioned here to preserve reproducibility.

### Identification and Universe

- **A1 (Primary key)**: The **CIK** is treated as the stable identifier for each firm. Tickers and names are auxiliary and may change over time.
- **A2 (Universe filter)**: The universe includes **SEC-registered public companies** only: (a) U.S. domestic issuers filing at least one 10-K in 2015–2025, and (b) foreign private issuers (FPIs) filing at least one 20-F in 2015–2025. Non-SEC-registered firms are excluded.
- **A3 (CIK persistence)**: A CIK represents a persistent reporting entity. Corporate actions (mergers, spin-offs) that change the reporting entity appear as distinct CIKs according to SEC; there is no manual consolidation across CIKs.
- **A4 (Active years)**: A firm is considered active only between `first_year` and `last_year`, derived from observed filings. We do **not** extrapolate activity outside this interval.

### Filings and Time Mapping

- **A5 (Form types)**: Relevant forms are 10-K, 10-K/A, 10-Q, 10-Q/A, 8-K (U.S. domestic); 20-F, 20-F/A, 6-K (foreign private issuers). Other forms are ignored for now.
- **A6 (Calendar year bucketing)**: `filing_year_bucket` is defined as the calendar year of `filing_date`. Fiscal year differences are not explicitly modeled at this stage.
- **A7 (Evidence year)**: All evidence derived from a filing is assigned `evidence_year = filing_year_bucket`. This simplifies temporal alignment at the cost of small timing imprecision.
- **A8 (Multiple filings per year)**: If a firm files multiple relevant forms in a year, all evidence from those filings contributes to the same `evidence_year`.

### Text Processing

- **A9 (Raw vs cleaned text)**: Raw HTML/EDGAR markup is preserved in `data/raw/sec_filings`. All extraction is performed on a **deterministically cleaned** text representation (`cleaned_v1`) stored separately.
- **A10 (Cleaning rules)**: `cleaned_v1` uses a fixed HTML→text pipeline (library versions pinned later), with:
  - Removal of most boilerplate headers/footers and navigation.
  - Best-effort preservation of bullet lists and section headings.
  - Removal or heavy down-weighting of large tables, while being careful not to lose competitor lists often expressed as bullets.
- **A11 (Section boundaries)**: Sections (e.g., MD&A, risk factors) are identified heuristically from headings; exact boundaries may be noisy but are logged for analysis.

### Evidence and Edges

- **A12 (Source firm)**: For all evidence derived from a filing, the **source firm** is the filer’s `cik`.
- **A13 (Directionality)**: Directed edges always point from **source (filer)** to **target (competitor)**. We do not symmetrize edges by default.
- **A14 (Explicit mentions)**: Phrases that unambiguously enumerate competitors (e.g., “our competitors include X, Y, Z”) are treated as explicit evidence, regardless of strength.
- **A15 (Entity resolution)**: Mapping `target_name_str` to `target_cik` is performed in a separate, auditable step with confidence scores. Mentions that cannot be resolved above a threshold remain with `target_cik = null`.
- **A16 (Implicit evidence without names)**: Sentences indicating competition without naming specific rivals are first stored as **firm-year-level signals** and only later mapped to directed edges where justifiable.
- **A17 (Events)**: 8-K (U.S.) and 6-K (foreign) events are assumed to affect competition intensity for at least one year starting at `event_date`. Exact decay windows are a modeling choice, not a data fact.

### Temporal Forecasting and Leakage

- **A18 (Forecasting horizon)**: All main prediction tasks are **one-year-ahead**: predicting edges in `t+1` using only information from years ≤ `t`.
- **A19 (History usage)**: Historical years 2015–2022 are used strictly for context/features and not as prediction targets in primary experiments.
- **A20 (Strict year-based splits)**: Train/validation/test sets are defined at the **year** level; no random edge-level or node-level splits mix years.
- **A21 (Feature truncation)**: Any cumulative or decayed feature at time `t` only aggregates evidence from years ≤ `t`. No feature for cutoff `t` may depend on data from `t+1` or later.
- **A22 (Global statistics)**: If global statistics (e.g., mean/variance for normalization) are needed, they are computed using **train-only** years unless otherwise justified and documented.

### Modeling-Related Assumptions (Early)

- **A23 (External models)**: If large language models or pre-trained transformers are used for implicit/event detection, they are treated as external oracles that do not themselves introduce time-indexed leakage (but training corpora and fine-tuning data must still respect temporal boundaries where possible).
- **A24 (Label definition)**: A non-zero fused weight in year `t` is treated as an edge “existing” in that year for binary existence tasks; thresholds or transformations are documented separately.
- **A25 (Repeated vs brand-new)**: An edge in `t+1` is **repeated** if it appeared in any year ≤ `t`; otherwise it is **brand-new**. This categorization is central for evaluation.

### Evaluation and Reproducibility

- **A26 (Randomness control)**: All scripts that involve sampling or randomness (e.g., negative sampling, train/val splits for auxiliary models) will expose an explicit `random_seed` parameter and log it.
- **A27 (Versioning)**: Key pipeline components (cleaning rules, evidence extraction models, aggregation logic) will be versioned via explicit identifiers (e.g., `text_version`, `evidence_pipeline_version`).
- **A28 (Re-runs)**: Re-running the pipeline with the same inputs, versions, and seeds is expected to produce identical outputs up to stable file ordering.

These assumptions are intentionally conservative to minimize hidden leakage and ambiguity. Any change should be treated as a potential source of evaluation drift and updated here alongside code and configuration changes.

