"""
Re-export for Colab: from src.pipeline import run_pipeline

Implementation lives in scripts/run_pipeline_colab.py.
Ensure project root (with config/, src/, scripts/) is on sys.path.
"""

from __future__ import annotations

from scripts.run_pipeline_colab import run_pipeline

__all__ = ["run_pipeline"]
