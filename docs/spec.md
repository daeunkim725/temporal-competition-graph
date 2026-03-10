## Project Specification

### Scope and Objective

This project builds a **temporally evaluated, directed, weighted competition graph** over U.S. public companies using SEC filings (10-K, 10-Q, 8-K).

The primary goals are:
- **G1**: Construct a leakage-safe, year-indexed competition graph where edges represent directed competition intensity from a *source* firm (disclosing filer) to a *target* firm (named or inferred competitor).
- **G2**: Support **future edge existence** and **future edge intensity** prediction under strict temporal forecasting (no same-graph completion).
- **G3**: Preserve decomposed evidence layers (explicit, implicit, event) for interpretability and ablation.

### Universe Definition

- **Entity key**: `cik` (Central Index Key) is the primary identifier for all firms.
- **Universe**: U.S. public firms that:
  - File at least one **10-K** in the window **2015–2025**.
  - Are tagged as U.S. issuers in SEC metadata.
- **Inclusion window per firm**:
  - `first_year`: first calendar year in which we observe a qualifying filing (10-K / 10-Q / 8-K).
  - `last_year`: last calendar year in which we observe any relevant filing.
  - Firms are considered *eligible* only in `[first_year, last_year]` for sampling and graph construction.

### Temporal Horizon and Granularity

- **Modeling horizon**: 2015–2025 inclusive.
- **Graph time unit**: **calendar year**.
- **Filing-to-year mapping**:
  - `filing_year_bucket = year(filing_date)` (calendar year of `filing_date`).
  - All evidence derived from a filing is assigned to `evidence_year = filing_year_bucket`.
- **Graph snapshot key**: `(source_cik, target_cik, year)` where:
  - `year` refers to the **evidence year** used to construct the edge weight for that snapshot.

### Edge Semantics and Layers

- **Base semantics**:
  - A directed edge `(source_cik → target_cik, year = t)` represents that, **based on filings up to and including calendar year t**, firm `source_cik` treats `target_cik` as a competitor in year `t` with some **competition intensity**.
- **Layers**:
  - **Explicit layer**:
    - Evidence from directly named competitors in filings (e.g., “our competitors include X, Y, Z”).
    - Primary forms: 10-K (and possibly 10-K/A; 10-Q later).
  - **Implicit layer**:
    - Evidence from text suggesting competition without explicit naming, including:
      - Product-market overlap.
      - Customer overlap.
      - Geographic overlap.
      - Substitute products/services.
      - Pricing pressure.
      - Rivalry language.
    - May be directed (when co-mentioned competitors exist) or stored as firm-year signals.
  - **Event layer**:
    - Evidence derived from **8-K** event disclosures indicating changes in competitive intensity, such as:
      - M&A involving competitors.
      - Entry into / exit from markets.
      - Major customer wins/losses that affect rivalry.
  - **Fused layer**:
    - Aggregated, bounded combination of the three components into a single **fused competition intensity** used as the primary edge weight.

### Prediction Tasks

1. **Future directed edge existence**
   - **Input**: Graph structure and features based on evidence up to year `t`.
   - **Target**: Binary label indicating whether `(source_cik → target_cik)` has a **non-zero fused weight** in year `t+1`.
   - **Special evaluation subsets**:
     - `repeated_future_edges`: edges that existed in any year ≤ t.
     - `brand_new_future_edges`: edges that did **not** exist in any year ≤ t.

2. **Future directed edge intensity**
   - **Input**: Same as above.
   - **Target**: Real-valued label `fused_weight_{t+1}` (possibly transformed or bucketed) for `(source_cik → target_cik)` in year `t+1`.

### Temporal Splits and Prediction Horizon

- **History years**: 2015–2022 (used for feature construction and context, not as prediction targets).
- **Train / validation / test years (as targets)**:
  - Train targets: **2023** edges, using history up to **2022**.
  - Validation targets: **2024** edges, using history up to **2023**.
  - Test targets: **2025** edges, using history up to **2024**.
- **Prediction horizon**:
  - **One-year ahead**: for each cutoff year `t`, predict edges in `t+1` using only information from years `≤ t`.

### Leakage Policy

To avoid recreating weaknesses of prior work (especially graph splitting leakage), we impose strict rules:

- **No future text leakage**:
  - When constructing features or labels for cutoff year `t`, **exclude** all filings with `filing_year_bucket > t`.
  - No textual evidence from year `t+1` or later can influence:
    - Node/edge features at time `t`.
    - Graph structure used as input at time `t`.
    - Any model parameters, if the model is trained only on pre-`t` data.

- **No future label leakage**:
  - When defining labels for year `t+1`, do not aggregate information from years `> t+1` into the label or its normalization.

- **No cross-year aggregation leakage**:
  - Any aggregation over multiple years (e.g., decayed counts) used as **features** at time `t` must be truncated at `t` (or earlier, depending on design).
  - Labels for year `t+1` must not be rescaled using statistics computed from years `> t+1`.

- **Split discipline**:
  - Splits are **year-based**, never random over edges or nodes.
  - All model selection, hyperparameter tuning, and threshold calibration are done using **train (2015–2023)** and **validation (up to 2024)** only.
  - Test-year (2025) labels and features are constructed without any knowledge of their values at model-design time.

- **Model training for text components**:
  - If implicit or event models are trained on historical text, constrain the training corpus to **pre-2023** when evaluating 2023+ predictions, or treat them explicitly as external oracles with careful documentation.

### Data Tables (High-Level)

The following logical tables will be used (detailed schemas in `docs/schemas.md`):

- **Company table** (`companies`)
  - Key: `cik`.
  - Fields: identifiers, basic firm attributes, `first_year`, `last_year`, etc.

- **Filing table** (`filings`)
  - Key: `accession_number`.
  - Fields: `cik`, `form_type`, `filing_date`, `period_of_report`, `fiscal_year`, `filing_year_bucket`, `source_url`, `local_path_raw`, `local_path_clean`, `text_version`.

- **Evidence table** (`evidence`)
  - Key: `(accession_number, evidence_id)` (logical).
  - Fields: `source_cik`, `target_cik` (nullable), `target_name_str`, `signal_type` (explicit / implicit / event), `subtype`, `section`, positions, `snippet_text`, `score`, `direction`, `evidence_year`.

- **Yearly edge table** (`yearly_edges`)
  - Key: `(source_cik, target_cik, year)`.
  - Fields: `explicit_intensity`, `implicit_intensity`, `event_intensity`, `fused_weight`, `num_filings`, `num_evidence_items`.

### Modeling and Baselines (High-Level)

- **Main model**: GAT-based graph neural network for link prediction and edge regression under temporal forecasting.
- **Baselines**:
  - Persistence: carry forward fused weights from previous years.
  - Graph heuristics: common neighbor-like metrics, degree-based scores, temporal motifs.
  - Tabular ML: gradient boosting / logistic regression on engineered features.
  - GraphSAGE: to compare against prior thesis architecture.

Implementation and hyperparameter details are deferred to later design documents; this spec focuses on data and leakage-safe graph construction.

