## Core Data Schemas

This document specifies the logical schemas for the main tables. Implementation may use Parquet, Arrow, or relational databases, but column names and meanings should match this spec.

### 1. Company Table (`companies`)

- **Primary key**
  - `cik` (string/int) — SEC Central Index Key.

- **Columns**
  - `cik` (string/int, not null)
  - `ticker` (string, nullable)
  - `company_name` (string, not null)
  - `sic` (string/int, nullable) — Standard Industrial Classification.
  - `sector` (string, nullable)
  - `industry` (string, nullable)
  - `issuer_type` (string, not null) — `us_domestic` or `foreign_private`.
  - `is_us_public` (bool, not null) — `true` iff `issuer_type == "us_domestic"`; kept for backward compatibility.
  - `first_year` (int, not null) — first calendar year with any relevant filing.
  - `last_year` (int, not null) — last calendar year with any relevant filing.

### 2. Filing Table (`filings`)

- **Primary key**
  - `accession_number` (string, not null)

- **Columns**
  - `accession_number` (string, not null)
  - `cik` (string/int, not null)
  - `form_type` (string, not null) — e.g., `10-K`, `10-K/A`, `10-Q`, `10-Q/A`, `8-K`, `20-F`, `20-F/A`, `6-K`.
  - `filing_date` (date, not null)
  - `period_of_report` (date, nullable)
  - `fiscal_year` (int, nullable)
  - `filing_year_bucket` (int, not null) — calendar year of `filing_date`.
  - `source_url` (string, not null)
  - `local_path_raw` (string, not null) — path to raw HTML/EDGAR file.
  - `local_path_clean` (string, nullable at first) — path to cleaned text file for `text_version`.
  - `text_version` (string, not null, default `cleaned_v1` once cleaning is run)
  - `has_parsing_errors` (bool, not null, default false)

### 3. Evidence Table (`evidence`)

This is a logical unified view; in storage you may partition by `signal_type` (explicit/implicit/event).

- **Logical primary key**
  - `(accession_number, evidence_id)` — `evidence_id` is a per-filing integer or UUID.

- **Columns**
  - `accession_number` (string, not null)
  - `evidence_id` (string/int, not null)
  - `source_cik` (string/int, not null)
  - `target_cik` (string/int, nullable) — null when unresolved.
  - `target_name_str` (string, nullable) — as appears in text for explicit mentions.
  - `signal_type` (string, not null) — one of `explicit`, `implicit`, `event`.
  - `subtype` (string, not null) — e.g., `named_competitor`, `product_overlap`, `pricing_pressure`, `event_mna`.
  - `section` (string, nullable) — coarse section label (e.g., `MD&A`, `risk_factors`).
  - `snippet_start_char` (int, nullable) — character offset in cleaned text.
  - `snippet_end_char` (int, nullable)
  - `snippet_text` (string, not null) — text span used as evidence.
  - `score` (float, not null) — intensity/confidence in [0, 1] or comparable bounded range.
  - `direction` (string, not null, default `source_to_target`) — for sanity checks.
  - `evidence_year` (int, not null) — equals `filing_year_bucket` of the source filing.
  - `resolution_confidence` (float, nullable) — for cases with resolved `target_cik`.

### 4. Yearly Edge Table (`yearly_edges`)

- **Primary key**
  - `(source_cik, target_cik, year)` — directed edge snapshot.

- **Columns**
  - `source_cik` (string/int, not null)
  - `target_cik` (string/int, not null)
  - `year` (int, not null)
  - `explicit_intensity` (float, not null, default 0.0)
  - `implicit_intensity` (float, not null, default 0.0)
  - `event_intensity` (float, not null, default 0.0)
  - `fused_weight` (float, not null, default 0.0)
  - `num_filings` (int, not null, default 0) — filings contributing evidence in this year.
  - `num_evidence_items` (int, not null, default 0)

### 5. Firm-Year Implicit Signals (`implicit_firm_year_signals`)

- **Primary key**
  - `(cik, year, subtype)`

- **Columns**
  - `cik` (string/int, not null)
  - `year` (int, not null)
  - `subtype` (string, not null) — same label space as implicit evidence (e.g., `pricing_pressure`).
  - `signal_intensity` (float, not null) — aggregate of sentence-level scores.
  - `num_sentences` (int, not null)

### 6. Event Table (`events_raw`)

- **Primary key**
  - `(accession_number, event_id)`

- **Columns**
  - `accession_number` (string, not null)
  - `event_id` (string/int, not null)
  - `source_cik` (string/int, not null)
  - `event_date` (date, not null)
  - `event_type` (string, not null) — e.g., `mna`, `market_entry`, `market_exit`, `major_customer_win`.
  - `event_year` (int, not null) — calendar year of `event_date`.
  - `snippet_text` (string, not null)
  - `raw_item_number` (string, nullable) — 8-K item code if available.

## JSON Schema Stubs

For programmatic validation, we will mirror these definitions as JSON Schema in the `schemas/` directory:

- `schemas/company.json` — matches the Company table.
- `schemas/filing.json` — matches the Filing table.
- `schemas/evidence.json` — matches the Evidence table.
- `schemas/yearly_edge.json` — matches the Yearly Edge table.

These JSON files should be minimal but enforce:

- Required fields and types.
- Primary key uniqueness (where supported by the downstream system).
- Allowed value sets for `signal_type` and simple enums where appropriate.

