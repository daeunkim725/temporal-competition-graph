"""
Clean SEC filings: parse HTML, remove boilerplate, segment into sections and sentences.

Implements:
- HTML/iXBRL removal, boilerplate stripping
- Section segmentation (10-K: Item 1, 1A, 7; 10-Q: Part I Item 2, Part II Item 1A; 8-K: items)
- Sentence-level chunks with stable IDs and offsets
- Deduplication of repeated passages
- Deterministic, auditable, no future-period logic
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from ..common.config import ProjectConfig, load_config


# Section patterns for 10-K, 10-Q, 8-K
SECTION_PATTERNS = {
    "10-K": [
        (r"item\s+1\.?\s*[:\-]?\s*(business|description)", "item_1_business", re.I),
        (r"item\s+1a\.?\s*[:\-]?\s*(risk\s+factors)?", "item_1a_risk_factors", re.I),
        (r"item\s+7\.?\s*[:\-]?\s*(management'?s?\s+discussion|mda)", "item_7_mda", re.I),
    ],
    "10-Q": [
        (r"part\s+i\s+item\s+2\.?\s*[:\-]?", "part_i_item_2_mda", re.I),
        (r"part\s+ii\s+item\s+1a\.?\s*[:\-]?\s*(risk\s+factors)?", "part_ii_item_1a_risk", re.I),
    ],
    "8-K": [
        (r"item\s+(\d+\.?\d*)\s*[:\-]?", "item", re.I),
    ],
}

# Boilerplate / remove patterns
BOILERPLATE_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"<style[^>]*>.*?</style>",
    r"<ix:nonnumeric[^>]*>.*?</ix:nonnumeric>",
    r"<ix:nonfraction[^>]*>.*?</ix:nonfraction>",
    r"<[^>]*:[\w-]+[^>]*>",  # iXBRL and other namespaced tags
    r"<table[^>]*>.*?</table>",  # tables (can be aggressive; optionally keep)
    r"^\s*page\s+\d+\s*$",
    r"^\s*\{.*?\}\s*$",  # JSON-like artifacts
]
# Signature block indicators
SIGNATURE_PATTERNS = [
    r"^\s*/s/",
    r"^\s*signature\s*$",
    r"^\s*by:\s*$",
    r"^\s*_________________________",
]
# TOC / exhibit index
TOC_PATTERNS = [
    r"^\s*table\s+of\s+contents\s*$",
    r"^\s*exhibit\s+index\s*$",
    r"^\s*item\s+\d+\.\s+\.+\s*\d+",  # TOC line like "Item 1. .... 3"
]


def _strip_html_and_ixbrl(html: str) -> str:
    """Remove HTML tags, iXBRL, scripts, styles. Extract text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    # Remove iXBRL and other namespaced elements
    for tag in soup.find_all(re.compile(r"^[a-z]+:", re.I)):
        tag.decompose()
    # Remove all remaining tags, get text
    text = soup.get_text(separator="\n")
    return text


def _normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace, trim lines."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def _remove_boilerplate(text: str) -> str:
    """Remove signature blocks, TOC, exhibit index, page numbers."""
    lines = text.split("\n")
    out = []
    skip_until_blank = False
    for i, ln in enumerate(lines):
        ln_strip = ln.strip()
        if not ln_strip:
            skip_until_blank = False
            out.append("")
            continue
        # Skip signature block
        if any(re.search(p, ln_strip, re.I) for p in SIGNATURE_PATTERNS):
            skip_until_blank = True
            continue
        if skip_until_blank and len(ln_strip) < 80:
            continue
        # Skip TOC / exhibit index
        if any(re.search(p, ln_strip, re.I) for p in TOC_PATTERNS):
            continue
        # Skip page numbers
        if re.match(r"^\s*page\s+\d+\s*$", ln_strip, re.I):
            continue
        out.append(ln)
    return "\n".join(out)


def _deduplicate_paragraphs(text: str, min_len: int = 50) -> str:
    """Remove repeated or near-identical paragraphs."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= min_len]
    seen_hashes: set[str] = set()
    unique = []
    for p in paragraphs:
        h = hashlib.sha256(p.encode("utf-8")).hexdigest()
        if h in seen_hashes:
            continue
        # Also skip very similar (first 100 chars match)
        prefix = p[:100] if len(p) >= 100 else p
        h2 = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
        if h2 in seen_hashes:
            continue
        seen_hashes.add(h)
        seen_hashes.add(h2)
        unique.append(p)
    return "\n\n".join(unique)


def _split_sentences(text: str) -> list[str]:
    """Simple sentence split (preserve boundaries)."""
    # Split on sentence-ending punctuation followed by space and capital
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [p.strip() for p in parts if p.strip()]


def _segment_sections(text: str, form_type: str) -> list[dict[str, Any]]:
    """Segment text into sections based on form type."""
    patterns = SECTION_PATTERNS.get(form_type, [])
    if not patterns:
        return [{"section_id": "full", "section_label": "full", "start_char": 0, "end_char": len(text), "text": text}]

    # Find all section start positions
    matches = []
    for pattern, label, flags in patterns:
        for m in re.finditer(pattern, text, flags):
            matches.append((m.start(), label))

    if not matches:
        return [{"section_id": "full", "section_label": "full", "start_char": 0, "end_char": len(text), "text": text}]

    matches.sort(key=lambda x: x[0])
    # Deduplicate by position, keep first label
    seen = set()
    unique = []
    for pos, label in matches:
        if pos not in seen:
            seen.add(pos)
            unique.append((pos, label))

    sections = []
    for i, (start, label) in enumerate(unique):
        end = unique[i + 1][0] if i + 1 < len(unique) else len(text)
        sec_text = text[start:end]
        sections.append({
            "section_id": f"{label}_{i}",
            "section_label": label,
            "start_char": start,
            "end_char": end,
            "text": sec_text,
        })
    return sections


def clean_single_filing(
    raw_path: Path,
    form_type: str,
) -> tuple[str, list[dict], list[dict]]:
    """
    Clean a single filing. Returns (full_text, sections, sentences).
    """
    html = raw_path.read_bytes().decode("utf-8", errors="replace")
    text = _strip_html_and_ixbrl(html)
    text = _normalize_whitespace(text)
    text = _remove_boilerplate(text)
    text = _deduplicate_paragraphs(text)

    sections = _segment_sections(text, form_type)
    all_sentences = []
    for sec in sections:
        sents = _split_sentences(sec["text"])
        offset = 0
        for j, sent in enumerate(sents):
            idx = sec["text"].find(sent, offset)
            if idx < 0:
                idx = offset
            start = sec["start_char"] + idx
            end = start + len(sent)
            offset = idx + len(sent)
            all_sentences.append({
                "section_id": sec["section_id"],
                "sentence_id": f"{sec['section_id']}_s{j}",
                "start_char": start,
                "end_char": end,
                "text": sent,
            })

    return text, sections, all_sentences


def clean_filings(
    config: ProjectConfig | None = None,
    filings_df: pd.DataFrame | None = None,
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
) -> pd.DataFrame:
    """
    Clean all filings in filings_df (from download_filings).
    Writes cleaned text, sections, and sentences. Returns updated filings metadata.
    """
    cfg = config or load_config()
    raw_dir = raw_dir or cfg.paths.raw_sec_filings
    processed_dir = processed_dir or (cfg.paths.processed_root / "sec_filings")

    if filings_df is None or filings_df.empty:
        raise ValueError("filings_df required. Run download_filings first.")

    sections_all = []
    sentences_all = []
    updated = []

    for _, row in filings_df.iterrows():
        raw_path = Path(row["local_path_raw"])
        if not raw_path.exists():
            continue
        form = row["form_type"]
        acc = row["accession_number"]
        cik = row["cik"]

        try:
            full_text, sections, sentences = clean_single_filing(raw_path, form)
        except Exception as e:
            updated.append({**row.to_dict(), "has_parsing_errors": True})
            continue

        out_dir = processed_dir / cik
        out_dir.mkdir(parents=True, exist_ok=True)
        clean_path = out_dir / f"{acc}_clean_v1.txt"
        clean_path.write_text(full_text, encoding="utf-8")

        for s in sections:
            sections_all.append({
                "accession_number": acc,
                "cik": cik,
                "form_type": form,
                "section_id": s["section_id"],
                "section_label": s["section_label"],
                "start_char": s["start_char"],
                "end_char": s["end_char"],
                "text": s["text"][:50000],  # cap for storage
            })
        for s in sentences:
            sentences_all.append({
                "accession_number": acc,
                "cik": cik,
                "section_id": s["section_id"],
                "sentence_id": s["sentence_id"],
                "start_char": s["start_char"],
                "end_char": s["end_char"],
                "text": s["text"],
            })

        updated.append({
            **row.to_dict(),
            "local_path_clean": str(clean_path),
            "text_version": "cleaned_v1",
            "has_parsing_errors": False,
        })

    # Write section and sentence tables
    sections_dir = cfg.paths.filings_sections
    sentences_dir = cfg.paths.filings_sentences
    sections_dir.mkdir(parents=True, exist_ok=True)
    sentences_dir.mkdir(parents=True, exist_ok=True)

    if sections_all:
        pd.DataFrame(sections_all).to_parquet(sections_dir / "filings_sections.parquet", index=False)
    if sentences_all:
        pd.DataFrame(sentences_all).to_parquet(sentences_dir / "filings_sentences.parquet", index=False)

    return pd.DataFrame(updated)


def build_filings_table(
    config: ProjectConfig | None = None,
    filings_df: pd.DataFrame | None = None,
    out_path: Path | None = None,
) -> pd.DataFrame:
    """
    Build filings.parquet from cleaned filings metadata.
    """
    cfg = config or load_config()
    out_path = out_path or (cfg.paths.filings / "filings.parquet")

    if filings_df is None or filings_df.empty:
        raise ValueError("filings_df required.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    filings_df.to_parquet(out_path, index=False)
    return filings_df
