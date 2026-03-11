"""
Pipeline entry point for Colab and other runners.

Re-exports run_pipeline so notebooks can use: from src.pipeline import run_pipeline
"""

from __future__ import annotations

import sys
from pathlib import Path


def __get_run_pipeline():
    # Ensure project root is on path when loading from scripts
    _caller_dir = Path(__file__).resolve().parent.parent
    if str(_caller_dir) not in sys.path:
        sys.path.insert(0, str(_caller_dir))
    from scripts.run_pipeline_colab import run_pipeline
    return run_pipeline


run_pipeline = __get_run_pipeline()

__all__ = ["run_pipeline"]
