# Prompt for Gemini: Fix Import and Next Steps

Copy the text below into Gemini (or another assistant) after you have updated the repo on Colab/Drive with the latest code (including `src/pipeline.py` and `scripts/__init__.py`).

---

## What was wrong and what was fixed

The Colab notebook was failing with:

```text
ImportError: No module named 'src.pipeline'
```

The project never had a module named `src.pipeline`. The pipeline runner lives in `scripts/run_pipeline_colab.py` and defines `run_pipeline`. This has been fixed by:

1. Adding **`scripts/__init__.py`** so `scripts` is a proper Python package.
2. Adding **`src/pipeline.py`**, which re-exports `run_pipeline` from `scripts.run_pipeline_colab`.

So this import now works when the project root is on `sys.path`:

```python
from src.pipeline import run_pipeline
```

**What I need you to do:**

1. **Confirm the fix on Colab**
   - Ensure the project root in Google Drive is the folder that contains `config/`, `src/`, and `scripts/` (not a parent folder that only contains a subfolder named `temporal-competition-graph`).
   - Set the project root and path, then run the pipeline:
   ```python
   import sys
   import os
   DRIVE_ROOT = '/content/drive/MyDrive/temporal-competition-graph'
   if DRIVE_ROOT not in sys.path:
       sys.path.insert(0, DRIVE_ROOT)
   os.chdir(DRIVE_ROOT)
   from src.pipeline import run_pipeline
   run_pipeline(drive_root=DRIVE_ROOT, download_limit=100)
   ```
   - If you still see `No module named 'src.pipeline'`, the Drive copy may be missing the new `src/pipeline.py`; re-copy or pull the repo so that `src/pipeline.py` and `scripts/__init__.py` exist.

2. **After the pipeline runs successfully, implement the alias and entity-resolution pipeline** as follows. Do not manually maintain a long list of company aliases. Instead:

   - **Canonical company table**
     - Start from SEC’s CIK-based identity data (e.g. `company_tickers.json` and any other SEC company lists you use).
     - Build one canonical company table keyed by CIK (company name, ticker, and any other fields you keep).

   - **Automatic alias generation**
     - From the canonical table, generate normalized lexical variants of official company names (e.g. lowercasing, stripping punctuation, handling “Inc.”, “Corp.”, etc.).
     - Add ticker-based aliases (ticker as an alias for the company).
     - When available, add historical “former names” from SEC filing headers or other SEC sources and link them to the same CIK with a time window (e.g. from-date / to-date) so you can enforce time-validity later.

   - **Alias scoring**
     - Score each alias by: (1) source quality (e.g. official name vs ticker vs inferred), (2) string quality (e.g. length, whether it looks like a full name), (3) ambiguity (e.g. one-word or very short names like “Apple”, “Meta”, “Google” are risky), (4) time validity (alias only valid in a given filing year range).
     - High confidence: exact or normalized official names, former SEC names with a valid period.
     - Medium confidence: tickers.
     - Lower confidence / cautious: short, brand-like one-word aliases unless context strongly supports them.

   - **Mention resolution (candidate generation + ranking, not direct mapping)**
     - Do **not** map every mention directly to a company. For each mention:
       - Use the alias table to **generate candidate CIKs** (all companies that have an alias matching the mention, subject to time validity).
       - **Rank** candidates using: industry fit (if you have industry/SIC), filing-period validity (company active in that year), and whether the mention appears in a competition-related snippet (e.g. “competitors include X”).
     - **Auto-resolve** only when the top candidate is clearly stronger than the rest (e.g. score above a threshold and gap to the second candidate above another threshold).
     - All other cases (ambiguous or weak matches) should go into an **unresolved audit table**, not into the main graph. The main graph should only contain links where resolution confidence is sufficient.

   - **Outputs**
     - Maintain: (1) canonical company table, (2) alias table with scores and time validity, (3) resolved mentions (for the main graph), (4) unresolved audit table for manual review or later refinement.

Implement this as a clear pipeline: canonical table → alias generation → alias scoring → mention candidate generation → candidate ranking → auto-resolve vs audit, and wire it into the existing SEC filing pipeline so that after filings are cleaned, explicit competitor mentions are run through this resolution pipeline and only high-confidence resolutions feed the graph.

---

Use this prompt as-is or adapt the “What I need you to do” and the alias/resolution section to your exact codebase and tool (e.g. Gemini in Colab).
