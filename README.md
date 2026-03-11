Below is a README-style version you can paste directly into your project.

# Project Goal and Execution Guide

## Project objective

This project aims to build a temporally evaluated, directed weighted competition graph of U.S. public companies from SEC filings and to prepare a high-quality pre-ML dataset that can later support future directed link prediction and edge-weight prediction. The core idea is to move beyond a simple explicit-competitor graph and instead construct a richer competition representation from three sources of evidence: explicit named competitors, implicit competition signals contained in business language, and event-based signals from 8-K filings. The final pre-ML outcome of this stage is not yet a trained model, but a reproducible research pipeline that produces clean company and filing datasets, structured competition-relevant text snippets, resolved company identities, explicit edge candidates, implicit market-competition profiles, fused graph snapshots by year, and a full set of diagnostics showing that the data is clean, the extraction logic is defensible, and the temporal setup is leakage-aware.

More specifically, the project seeks to answer the following pre-ML question: can SEC filings be transformed into a high-quality, time-aware, directed, and interpretable competition dataset that is rich enough to support future forecasting of competitive relationships? The work up to the NLP stage is therefore focused on data architecture, corpus construction, filing cleaning, competition snippet harvesting, named-entity extraction, alias resolution, implicit descriptor extraction, graph assembly, and analytical validation. The goal is to reach the modeling stage with a dataset that is not only usable, but also explainable, auditable, and strong enough to support meaningful comparisons later between explicit-only, implicit-only, and fused graph learning approaches.

## High-level research design

The project is built around the following design choices:

* **Node set**: CIK-resolved U.S. public companies only
* **Primary filings**: 10-K, 10-Q, and 8-K
* **Edge direction**: from the filing company to the competitor target
* **Graph type**: directed, weighted, multi-signal competition graph
* **Signals**:

  * explicit competition evidence from directly named competitors
  * implicit competition evidence from rivalry language and market descriptors
  * event-based reinforcement from 8-K filings
* **Temporal setup**:

  * 2023 train period
  * 2024 validation period
  * 2025 test period
* **Pre-ML deliverable**:

  * a complete graph-building and NLP pipeline with diagnostics, analysis, and report-ready figures

## What this README covers

This guide covers the full pipeline from project setup through the NLP and graph-construction stages, stopping just before machine learning. By the end of these steps, the project should already have:

* a locked project specification
* a defined company universe
* downloaded and parsed SEC filings
* cleaned and sectioned filing text
* competition-triggered snippets
* explicit competitor mention candidates
* resolved company aliases and CIK mappings
* implicit competition profiles
* yearly explicit, implicit, and fused graph snapshots
* pre-ML labels, metadata, and diagnostics
* figures, tables, and validation outputs for the report

---

# Phase 1 - Project framing and research specification

## Goal

Lock the research design before implementation so the project does not drift into ad hoc decisions later.

## Tasks

1. Write the formal project objective.
2. Define the unit of analysis.
3. Define the node identity policy.
4. Define what counts as explicit competition evidence.
5. Define what counts as implicit competition evidence.
6. Define how 8-K evidence will be used.
7. Define the temporal split and leakage rules.
8. Define the pre-ML outputs you must produce.

## Decisions to lock

* Nodes are only CIK-resolved U.S. public firms.
* Ambiguous names, private firms, foreign firms, and unresolved brand mentions do not become official nodes.
* Edge direction goes from source filer to mentioned or inferred rival.
* The project will maintain three graph layers:

  * explicit graph
  * implicit graph
  * event graph
* A fused graph is built after the three layers are individually validated.
* The pipeline must never use 2025 information to create 2023 or 2024 features.

## Deliverables

* `project_specification.md`
* `label_dictionary.md`
* `data_dictionary.md`
* `leakage_policy.md`

## Report outputs

### Table

* Project comparison table: prior thesis vs current project

### Figure

* Pipeline overview diagram from filing ingestion to final graph snapshots

### Results to include

* One concise statement of the scientific objective
* One paragraph on why temporal evaluation is necessary
* One paragraph on why explicit-only graphs are insufficient

---

# Phase 2 - Company universe construction

## Goal

Build a clean, stable universe of firms that will serve as graph nodes and filing owners.

## Tasks

1. Collect the initial company universe from SEC identifier data.
2. Build the canonical company table keyed by CIK.
3. Store official names, tickers, normalized names, and sector metadata if available.
4. Freeze the universe for the selected time range.
5. Decide how to handle name changes and historical identities.

## What to store

Each company record should contain:

* `cik`
* `official_name`
* `normalized_name`
* `ticker`
* `valid_from`
* `valid_to`
* `industry_code` or sector field if available
* `status`
* `source`

## Key design rule

CIK is the only true node identity. Names, tickers, brands, and aliases are all secondary resolution aids.

## Deliverables

* `companies.parquet`
* `company_metadata.parquet`
* `company_universe_summary.md`

## Report outputs

### Table

* Number of companies in final node universe
* Number excluded and why
* Number with missing metadata

### Figures

* Bar chart of company counts by sector
* Histogram of market coverage by sector or SIC group
* Coverage plot of firms with filings in each year

### Results to include

* Total number of eligible public companies
* Share with at least one 10-K, 10-Q, or 8-K
* Summary of exclusions
* Commentary on whether the node universe is broad enough for meaningful competition inference

---

# Phase 3 - Filing collection and corpus assembly

## Goal

Download and organize the filing corpus for all target companies and target years.

## Tasks

1. Download filing metadata for 2023, 2024, and 2025.
2. Keep only 10-K, 10-Q, and 8-K.
3. Store amendments separately rather than mixing them into the main corpus.
4. Download the main filing document.
5. Preserve raw metadata and source locations.
6. Track failed downloads and retry logic.

## Raw data structure

Each filing should initially have:

* `filing_id`
* `cik`
* `company_name`
* `form_type`
* `filing_date`
* `accession_number`
* `primary_doc_url`
* `raw_text_path`
* `download_status`

## Important rules

* Do not merge filings across years.
* Do not discard filing dates.
* Do not silently overwrite failed or duplicated downloads.
* Keep raw files immutable.

## Deliverables

* `filings_raw_metadata.parquet`
* `raw_filings/`
* `download_log.csv`
* `download_failures.csv`

## Report outputs

### Tables

* Filing counts by year and form type
* Download success/failure counts
* Amendment counts by form type

### Figures

* Stacked bar chart: filings by year and form type
* Data attrition funnel: universe -> filings found -> filings downloaded -> filings parsed -> filings kept
* Heatmap: sector x form type counts
* Time-series line chart: filings per month or quarter

### Results to include

* Number of filings collected
* Breakdown by 10-K, 10-Q, 8-K
* Number of failed downloads and whether missingness is systematic
* Explanation of whether amendment filings are excluded, stored separately, or used later

---

# Phase 4 - Filing parsing and structural cleaning

## Goal

Convert raw filing documents into clean, structured text that preserves section boundaries and is suitable for NLP.

## Tasks

1. Parse HTML or text filings into normalized plain text.
2. Remove HTML and Inline XBRL markup.
3. Strip signatures, exhibits, tables of contents, and repeated formatting artifacts.
4. Preserve section boundaries and filing item labels.
5. Standardize whitespace, encoding, and punctuation.
6. Keep sentence boundaries intact.
7. Store both original-clean and normalized-clean text.

## Sectioning policy

### 10-K

Prioritize:

* Item 1 Business
* Item 1A Risk Factors
* Item 7 MD&A

### 10-Q

Prioritize:

* Part I Item 2 MD&A
* Part II Item 1A Risk Factors

### 8-K

Preserve:

* item numbers
* item titles
* event text

## What to store

At the section level:

* `filing_id`
* `section_id`
* `section_label`
* `section_order`
* `section_text_original_clean`
* `section_text_normalized`
* `char_count`
* `sentence_count`

## Deliverables

* `filings_parsed_sections.parquet`
* `cleaning_log.csv`
* `removed_boilerplate_log.csv`

## Report outputs

### Tables

* Section extraction success rates by form type
* Average section lengths
* Most common missing sections

### Figures

* Boxplots of section length by form type and section
* Histogram of sentence counts per filing
* Bar chart of parsed section coverage
* Before/after text cleaning examples

### Results to include

* Percentage of filings successfully sectioned
* Which sections produce the richest competition text
* Whether 8-Ks contain useful competition-related content or mostly noise
* Evidence that cleaning reduced noise without destroying content

---

# Phase 5 - Sentence segmentation and chunk construction

## Goal

Create stable sentence-level and paragraph-level units that can be used for snippet extraction and later auditing.

## Tasks

1. Split cleaned section text into sentences.
2. Assign stable sentence IDs and offsets.
3. Optionally group sentences into paragraph-level chunks.
4. Retain document order.
5. Keep links back to filing, section, and company.

## Recommended chunk schema

* `chunk_id`
* `filing_id`
* `cik`
* `form_type`
* `filing_date`
* `section_id`
* `sentence_start_idx`
* `sentence_end_idx`
* `chunk_text`
* `char_start`
* `char_end`

## Design rule

Every extracted snippet later in the pipeline should be traceable back to the original filing and exact sentence positions.

## Deliverables

* `filing_sentences.parquet`
* `filing_chunks.parquet`

## Report outputs

### Tables

* Total sentence counts by form type
* Average chunk length
* Number of chunks per filing

### Figures

* Histogram of sentence length
* Histogram of chunk length
* Distribution of chunk counts per filing

### Results to include

* Whether chunk sizes are reasonable for NER and descriptor extraction
* Whether certain filing types are much noisier than others

---

# Phase 6 - Deduplication and boilerplate control

## Goal

Remove repeated passages that would otherwise inflate counts, distort edge weights, and create misleading evidence.

## Tasks

1. Detect exact duplicate sentences or paragraphs within filings.
2. Detect near-duplicate boilerplate across repeated filings from the same company.
3. Mark repeated legal disclaimers and safe-harbor text.
4. Create deduplicated text views for extraction while preserving raw-clean versions for audit.

## Key risk

Without deduplication, quarterly repetition and repeated legal language will falsely increase competition intensity.

## Deliverables

* `dedup_flags.parquet`
* `filing_chunks_dedup.parquet`
* `boilerplate_dictionary.json`

## Report outputs

### Tables

* Duplicate rates by form type
* Duplicate rates by section
* Top repeated boilerplate patterns

### Figures

* Bar chart of duplicate share by form type
* Company-level histogram of repeated text ratios
* Before/after comparison of snippet counts pre- and post-deduplication

### Results to include

* How much text was removed or downweighted as boilerplate
* Whether deduplication materially changed snippet volume
* Whether some companies disproportionately reuse text

---

# Phase 7 - Competition trigger lexicon and snippet harvesting

## Goal

Find the local windows of text most likely to contain either explicit competitors or useful implicit competition signals.

## Tasks

1. Build a competition-trigger lexicon.
2. Scan sentence-level text for trigger terms.
3. Create snippet windows around each trigger.
4. Store trigger type and trigger location.
5. Separate snippet harvesting from actual extraction logic.

## Suggested trigger families

* direct competition words:

  * competitor
  * competition
  * compete
  * competing
  * competitive
  * rivalry
  * rivals

* market overlap words:

  * substitute
  * alternatives
  * pricing pressure
  * market share
  * fragmented market
  * industry peers

* threat or pressure words:

  * lower-priced
  * differentiated
  * customer switching
  * technological change
  * new entrants

## Recommended snippet window

* 1 sentence before
* trigger sentence
* 2 sentences after

Store the full window even if the name is not in the trigger sentence itself.

## Snippet schema

* `snippet_id`
* `filing_id`
* `cik`
* `form_type`
* `filing_date`
* `section_id`
* `trigger_sentence_id`
* `trigger_term`
* `trigger_family`
* `window_start_sentence`
* `window_end_sentence`
* `snippet_text`
* `dedup_flag`

## Deliverables

* `trigger_lexicon.yml`
* `competition_snippets.parquet`

## Report outputs

### Tables

* Trigger counts by keyword
* Trigger counts by form type
* Trigger counts by section

### Figures

* Bar chart of top trigger terms
* Stacked bar chart of snippet source by section
* Trend chart of snippet volume over time
* Heatmap of trigger families by form type

### Results to include

* Which sections and forms contain most competition-relevant language
* Whether the snippet approach improves concentration of relevant evidence
* Whether the trigger lexicon is too narrow or too noisy

---

# Phase 8 - Explicit competitor extraction

## Goal

Identify snippets that explicitly name competitors and extract candidate target organizations.

## Tasks

1. Run NER over competition snippets.
2. Detect organization mentions.
3. Filter out obvious non-competitor organization types where possible.
4. Create explicit competitor candidate records.
5. Preserve confidence and provenance for every extracted candidate.

## Important principle

At this stage, extracted organizations are only candidate competitors, not final graph edges yet.

## Explicit candidate schema

* `candidate_id`
* `source_cik`
* `filing_id`
* `snippet_id`
* `org_mention_raw`
* `org_mention_normalized`
* `mention_start`
* `mention_end`
* `ner_model`
* `context_text`
* `is_candidate_explicit_competitor`

## Suggested validation approach

Perform a manual spot-check sample of extracted candidates and label them as:

* true competitor mention
* false positive organization
* correct organization but wrong role
* unclear

## Deliverables

* `explicit_org_candidates.parquet`
* `explicit_extraction_sample_validation.csv`

## Report outputs

### Tables

* Number of snippets with at least one ORG mention
* Top extracted organization mentions
* Manual validation confusion table

### Figures

* Histogram of ORG mentions per snippet
* Bar chart of most common extracted organization strings
* Precision estimate plot from manual validation sample
* Error-type bar chart

### Results to include

* Estimated precision of explicit extraction
* Common false positives
* Evidence that the snippet method captures names missed by sentence-only extraction
* Discussion of whether 8-Ks produce useful explicit competitor mentions or mostly unrelated organizations

---

# Phase 9 - Alias handling and entity resolution

## Goal

Map extracted organization mentions to canonical CIK-resolved company nodes without polluting the graph with bad matches.

## Tasks

1. Build a canonical alias table from company names, normalized variants, and tickers.
2. Add automatically generated lexical aliases.
3. Add historical names where available.
4. Generate candidate CIK matches for each extracted mention.
5. Score candidates by string quality, alias type, ambiguity, and context.
6. Resolve only high-confidence cases.
7. Send ambiguous cases to an unresolved audit table.

## Resolution philosophy

Do not force every mention into the graph. High precision matters more than full recall at this stage.

## Suggested alias types

* official_name
* normalized_name
* ticker_alias
* historical_name
* brand_alias
* weak_surface_form

## Resolution tables

### Alias table

* `alias_text`
* `alias_norm`
* `cik`
* `alias_type`
* `valid_from`
* `valid_to`
* `source`
* `default_confidence`

### Resolution result table

* `candidate_id`
* `source_cik`
* `mention_text`
* `resolved_target_cik`
* `match_score`
* `match_type`
* `ambiguity_count`
* `resolution_status`

## Deliverables

* `company_aliases.parquet`
* `resolved_explicit_mentions.parquet`
* `unresolved_mentions.parquet`
* `resolution_audit_sample.csv`

## Report outputs

### Tables

* Resolution rates
* Match types by frequency
* Top unresolved mentions
* Top ambiguous aliases

### Figures

* Histogram of match confidence
* Bar chart of alias types used in successful resolutions
* Precision-by-confidence plot from manual sample
* Ambiguity distribution plot

### Results to include

* Share of extracted mentions resolved to official nodes
* Major alias-resolution pain points
* Brand-vs-filer issues
* Whether unresolved mentions are random or concentrated in certain sectors or filing types

---

# Phase 10 - Explicit edge construction

## Goal

Convert resolved explicit competitor mentions into directed explicit graph edges with interpretable weights.

## Tasks

1. Group resolved mentions by source CIK, target CIK, filing, year, and possibly section.
2. Count supporting mentions.
3. Decide on an explicit edge-weight rule.
4. Build yearly explicit graph snapshots.
5. Separate repeated and new edges over time.

## Recommended explicit weight components

* number of supporting snippets
* number of distinct filings mentioning the target
* number of distinct sections mentioning the target
* optional time decay within year

## Explicit edge schema

* `year`
* `source_cik`
* `target_cik`
* `explicit_support_count`
* `distinct_filing_count`
* `distinct_section_count`
* `explicit_weight`

## Deliverables

* `explicit_edges_2023.parquet`
* `explicit_edges_2024.parquet`
* `explicit_edges_2025.parquet`

## Report outputs

### Tables

* Number of explicit edges by year
* Average explicit weight by year
* Number of new vs repeated explicit edges

### Figures

* Histogram of explicit edge weights
* In-degree and out-degree distributions
* Network size over time
* Sankey or transition chart for repeated vs new edges

### Results to include

* Whether explicit graph density is stable or changing
* Whether most firms have very low out-degree
* Whether edge weights are highly skewed
* Whether repeated edges dominate over new ones

---

# Phase 11 - Implicit competition signal extraction

## Goal

Use competition-related snippets to extract market descriptors that imply rivalry even when no competitor is named.

## Tasks

1. Define the descriptor categories to extract.
2. Extract descriptor phrases from snippets.
3. Normalize and aggregate descriptors at the company-year level.
4. Build company competition profiles.
5. Assess whether these profiles reveal plausible rival similarity structures.

## Suggested descriptor categories

* product or service category
* customer segment
* geographic market
* pricing pressure
* technology or innovation dimension
* distribution channel
* quality or performance dimension
* regulation or compliance dimension
* switching-cost language
* market fragmentation or concentration language

## Recommended profile schema

* `cik`
* `year`
* `descriptor_type`
* `descriptor_value`
* `count`
* `source_snippet_count`
* `supporting_forms`

## Deliverables

* `implicit_descriptors.parquet`
* `company_year_profiles.parquet`
* `descriptor_dictionary.yml`

## Report outputs

### Tables

* Top descriptor categories
* Top normalized descriptors
* Average descriptor richness per company-year

### Figures

* Bar chart of most common descriptors
* Descriptor-type distribution by form type
* Heatmap of descriptor usage across sectors
* Temporal drift chart of descriptor frequencies
* UMAP or t-SNE of company profiles for exploratory visualization

### Results to include

* Whether the snippets contain enough detail to support implicit competition inference
* Which descriptor types are most informative
* Whether sectors separate naturally in descriptor space
* Whether 8-Ks add unique implicit information or mostly reinforce existing 10-K/10-Q signals

---

# Phase 12 - Implicit similarity and candidate rival generation

## Goal

Convert company competition profiles into implicit rival candidates and implicit edge weights.

## Tasks

1. Build company-year similarity measures from descriptors.
2. Compare different similarity rules.
3. Generate candidate rival pairs.
4. Limit candidates to reasonable neighborhoods if needed.
5. Build yearly implicit graph snapshots.

## Similarity options

* lexical overlap on normalized descriptors
* weighted overlap by descriptor type
* embedding similarity of aggregated snippet text
* hybrid score combining structured overlap and semantic similarity

## Important rule

Implicit edges should not be treated as truth labels. They are inferred evidence and should remain distinct from explicit edges.

## Implicit edge schema

* `year`
* `source_cik`
* `target_cik`
* `implicit_similarity_score`
* `shared_descriptor_count`
* `implicit_support_count`
* `implicit_weight`

## Deliverables

* `implicit_edges_2023.parquet`
* `implicit_edges_2024.parquet`
* `implicit_edges_2025.parquet`
* `similarity_diagnostics.csv`

## Report outputs

### Tables

* Number of implicit edges by year
* Distribution of similarity scores
* Overlap between explicit and implicit neighbor sets

### Figures

* Histogram of implicit weights
* CDF of similarity scores
* Scatter plot of explicit weight vs implicit similarity for overlapping pairs
* Heatmap of descriptor overlap by sector pair
* Neighbor-overlap plot for top-K rivals

### Results to include

* Whether explicit and implicit signals align at all
* Whether implicit edges are too dense or too sparse
* Whether similarity neighborhoods are economically plausible
* Whether implicit profiles help identify likely rivals not explicitly named

---

# Phase 13 - 8-K event evidence layer

## Goal

Capture dynamic competition-relevant events that may strengthen, weaken, or refresh rivalry evidence.

## Tasks

1. Identify 8-K item types likely to matter for competition.
2. Extract event-level snippets.
3. Build event descriptors or event flags.
4. Aggregate event evidence at company-year or company-period level.
5. Create event reinforcement scores for source-target pairs or source-company profiles.

## Examples of potentially relevant 8-K content

* acquisitions or dispositions
* major customer or supplier changes
* strategic agreements
* distress or restructuring
* earnings shocks or guidance
* major operational shifts
* leadership changes with strategic significance
* other material events that could reshape competition

## Deliverables

* `event_snippets.parquet`
* `event_features.parquet`
* `event_layer_edges.parquet` or `company_event_profiles.parquet`

## Report outputs

### Tables

* Event counts by 8-K item type
* Share of 8-Ks deemed competition-relevant
* Top event categories

### Figures

* Bar chart of useful 8-K item categories
* Timeline of event frequency
* Plot of event evidence contribution by sector
* Comparison of graphs with and without event reinforcement

### Results to include

* Whether 8-Ks meaningfully enrich the competition signal
* Which event types are most useful
* Whether 8-Ks contribute new edges or mostly strengthen existing ones

---

# Phase 14 - Fused graph construction

## Goal

Combine explicit, implicit, and event evidence into interpretable yearly graph snapshots.

## Tasks

1. Normalize explicit, implicit, and event evidence to comparable scales.
2. Define the fused edge-weight formula.
3. Create yearly fused graphs.
4. Retain the original signal components for transparency.
5. Produce edge-level provenance for every fused weight.

## Recommended fused edge record

* `year`
* `source_cik`
* `target_cik`
* `explicit_weight`
* `implicit_weight`
* `event_weight`
* `fused_weight`
* `fused_edge_exists`
* `provenance_count`

## Deliverables

* `fused_edges_2023.parquet`
* `fused_edges_2024.parquet`
* `fused_edges_2025.parquet`
* `fused_weight_spec.md`

## Report outputs

### Tables

* Edge counts by graph layer and year
* Mean and median weights by layer
* Overlap matrix between explicit, implicit, and fused graphs

### Figures

* Histogram of fused weights
* Layer overlap Venn diagram or overlap table
* Density comparison across graph layers
* In-degree and out-degree distributions for fused graph
* Scatter plots comparing explicit vs fused and implicit vs fused weights

### Results to include

* Whether the fused graph is dominated by one signal
* Whether fusion creates plausible additional coverage
* Whether fusion over-densifies the graph
* Whether the resulting weight distribution is usable for later learning

---

# Phase 15 - Temporal graph snapshots and pre-ML label preparation

## Goal

Prepare the final graph snapshots and supervision targets that will later feed the ML stage.

## Tasks

1. Freeze the 2023, 2024, and 2025 snapshots.
2. Define what constitutes a positive edge in each year.
3. Identify repeated and new edges.
4. Build edge candidate tables for later modeling.
5. Keep message-passing data distinct from supervision labels for future stages.

## Required outputs

* graph snapshots by layer and year
* edge candidate tables
* label tables for edge existence
* target tables for edge weight
* repeated/new edge flags
* negative-sampling design notes for future work

## Deliverables

* `graph_snapshots/`
* `edge_labels_2024.parquet`
* `edge_labels_2025.parquet`
* `weight_targets_2024.parquet`
* `weight_targets_2025.parquet`
* `split_integrity_report.md`

## Report outputs

### Tables

* Final graph statistics by year and layer
* Repeated vs new edge counts
* Node and edge retention across years

### Figures

* Temporal change in graph size
* Repeated vs new edge shares
* Weight distribution across years
* Transition plots for edge persistence
* Graph summary dashboard

### Results to include

* How stable the graph is year to year
* Whether enough new edges exist to make forecasting nontrivial
* Whether graph density and coverage are appropriate for later modeling

---

# Phase 16 - Quality control, validation, and leakage audit

## Goal

Prove that the pipeline is not quietly broken before moving to ML.

## Tasks

1. Run manual validation samples for each major pipeline stage.
2. Check alias-resolution precision.
3. Check explicit extraction precision.
4. Check whether implicit descriptors are meaningful.
5. Verify temporal split integrity.
6. Confirm that no future data is used in earlier feature construction.
7. Confirm that deduplication and section filtering do not leak labels.

## Validation samples to create

* explicit snippet sample
* resolved mention sample
* unresolved mention sample
* implicit descriptor sample
* fused-edge audit sample

## Leakage audit questions

* Were any dictionaries built using 2025 content and then applied to 2023 or 2024?
* Were company profiles built with future snippets?
* Were similarity neighborhoods computed using future-year text?
* Were aliases approved using knowledge from later periods?
* Did deduplication compare across train and test in a way that exposes future text?

## Deliverables

* `manual_validation/`
* `leakage_audit.md`
* `quality_checks.md`

## Report outputs

### Tables

* Manual validation precision estimates by stage
* Leakage checklist
* Failure modes and mitigations

### Figures

* Confidence vs precision curves for entity resolution
* Error-type breakdown charts
* Stage-by-stage quality dashboard

### Results to include

* Estimated precision of the explicit pipeline
* Estimated quality of the resolution pipeline
* Whether implicit features appear noisy or meaningful
* Clear statement that temporal leakage controls are in place

---

# Minimum final pre-ML deliverables

Before touching machine learning, the project should have all of the following:

1. A frozen project specification
2. A canonical company universe
3. A full filing corpus for 2023-2025
4. Cleaned and sectioned filings
5. Sentence-level and snippet-level datasets
6. A validated trigger lexicon
7. Explicit candidate competitor mentions
8. An alias-resolution pipeline with unresolved audit handling
9. Yearly explicit graph snapshots
10. Company-year implicit competition profiles
11. Yearly implicit graph snapshots
12. A competition-relevant 8-K event layer
13. Yearly fused graph snapshots
14. Temporal labels for future edge existence and weight
15. A leakage audit and manual validation package
16. A full set of report-ready descriptive figures and tables

---

# Suggested figures and tables checklist for the report

## Core descriptive tables

* Project design comparison table
* Company universe summary
* Filing counts by year and form
* Section extraction success table
* Trigger frequency table
* Explicit extraction validation table
* Resolution validation table
* Graph statistics by layer and year
* Repeated vs new edge table
* Leakage audit table

## Core descriptive figures

* End-to-end pipeline diagram
* Data attrition funnel
* Filings by year and form type
* Section coverage plot
* Trigger term frequency plot
* Snippet distribution by section
* ORG mention frequency plot
* Alias confidence histogram
* Explicit edge-weight histogram
* Degree distributions
* Descriptor frequency plot
* Sector-descriptor heatmap
* Implicit similarity distribution
* Layer overlap comparison
* Temporal graph growth plot
* Repeated vs new edge plot
* Quality-control dashboard

## High-value optional figures

* UMAP or t-SNE of company competition profiles
* Sankey diagram of edge persistence
* Sector-pair heatmap of competition intensity
* Example snippet panels for explicit and implicit extraction
* Error-analysis chart by failure mode
* Comparison of graph statistics before and after deduplication

---

# Recommended narrative for the report

Your report should show that this is not just a data collection exercise, but a structured graph-building pipeline. The narrative should progress as follows: first define the firm universe and filing corpus, then show how filings are cleaned and sectioned, then demonstrate how competition-focused snippets are harvested, then show how explicit competitors and implicit descriptors are extracted from those snippets, then show how those signals are converted into explicit, implicit, and event graph layers, and finally show that the resulting graph snapshots are interpretable, temporally valid, and suitable for future modeling. The analysis should repeatedly emphasize three things: interpretability, temporal discipline, and auditability. At every stage, the report should include not only counts but also evidence that the stage is working correctly, such as manual validation, error analysis, coverage plots, and comparisons before and after key preprocessing decisions.

---

# End state before ML

At the end of this stage, the project should be able to say the following: a reproducible pipeline was built to transform SEC filings into yearly directed weighted competition graphs using explicit competitor mentions, implicit competition descriptors, and event-based filing evidence; all entities were resolved to a stable CIK-based node system where possible; ambiguous cases were quarantined rather than forced into the graph; yearly graph layers were constructed and fused; and the resulting pre-ML dataset includes interpretable edge weights, temporal graph snapshots, descriptive diagnostics, and leakage-aware labels suitable for later link and weight prediction.

The next stage begins only once this pre-ML dataset is stable enough that any later performance difference can be attributed to the models rather than to broken data preparation.
