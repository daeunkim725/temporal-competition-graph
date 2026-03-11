from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclasses.dataclass
class PathsConfig:
    data_root: Path
    raw_sec_index: Path
    raw_sec_filings: Path
    processed_root: Path
    companies: Path
    filings: Path
    filings_sections: Path
    filings_sentences: Path
    evidence: Path
    graphs: Path
    firm_year: Path
    splits: Path


@dataclasses.dataclass
class YearsConfig:
    history_start: int
    history_end: int
    train_target: int
    val_target: int
    test_target: int
    max_year: int


@dataclasses.dataclass
class FormsConfig:
    primary: list[str]
    target_forms: list[str]
    exclude_amendments: bool


@dataclasses.dataclass
class LeakagePolicyConfig:
    prediction_horizon: int
    enforce_year_truncation: bool
    disallow_future_text: bool


@dataclasses.dataclass
class ProjectConfig:
    project_name: str
    paths: PathsConfig
    years: YearsConfig
    forms: FormsConfig
    leakage_policy: LeakagePolicyConfig
    random_seed: int

    @property
    def train_cutoff_year(self) -> int:
        """Latest year allowed when constructing features for the train target."""
        return self.years.train_target - self.leakage_policy.prediction_horizon

    @property
    def val_cutoff_year(self) -> int:
        return self.years.val_target - self.leakage_policy.prediction_horizon

    @property
    def test_cutoff_year(self) -> int:
        return self.years.test_target - self.leakage_policy.prediction_horizon


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config(
    config_path: str | Path = "config/config.yaml",
    base_path: str | Path | None = None,
) -> ProjectConfig:
    """
    Load the project configuration from YAML and return a typed ProjectConfig.

    base_path: If set, all data paths are resolved relative to this (e.g. Google
        Drive root). If None, uses config "base_path" or project-relative paths.
    """
    path = Path(config_path)
    raw = _load_yaml(path)

    base = Path(base_path) if base_path is not None else Path(raw.get("base_path", ""))
    def _p(rel: str) -> Path:
        p = Path(rel)
        return (base / p) if base else p

    paths_cfg = PathsConfig(
        data_root=_p(raw["paths"]["data_root"]),
        raw_sec_index=_p(raw["paths"]["raw_sec_index"]),
        raw_sec_filings=_p(raw["paths"]["raw_sec_filings"]),
        processed_root=_p(raw["paths"]["processed_root"]),
        companies=_p(raw["paths"]["companies"]),
        filings=_p(raw["paths"]["filings"]),
        filings_sections=_p(raw["paths"].get("filings_sections", str(Path(raw["paths"]["filings"]) / "sections"))),
        filings_sentences=_p(raw["paths"].get("filings_sentences", str(Path(raw["paths"]["filings"]) / "sentences"))),
        evidence=_p(raw["paths"]["evidence"]),
        graphs=_p(raw["paths"]["graphs"]),
        firm_year=_p(raw["paths"]["firm_year"]),
        splits=_p(raw["paths"]["splits"]),
    )

    years_cfg = YearsConfig(
        history_start=int(raw["years"]["history_start"]),
        history_end=int(raw["years"]["history_end"]),
        train_target=int(raw["years"]["train_target"]),
        val_target=int(raw["years"]["val_target"]),
        test_target=int(raw["years"]["test_target"]),
        max_year=int(raw["years"]["max_year"]),
    )

    forms_cfg = FormsConfig(
        primary=list(raw["forms"]["primary"]),
        target_forms=list(raw["forms"].get("target_forms", ["10-K", "10-Q", "8-K"])),
        exclude_amendments=bool(raw["forms"].get("exclude_amendments", True)),
    )

    leakage_cfg = LeakagePolicyConfig(
        prediction_horizon=int(raw["leakage_policy"]["prediction_horizon"]),
        enforce_year_truncation=bool(raw["leakage_policy"]["enforce_year_truncation"]),
        disallow_future_text=bool(raw["leakage_policy"]["disallow_future_text"]),
    )

    return ProjectConfig(
        project_name=str(raw["project_name"]),
        paths=paths_cfg,
        years=years_cfg,
        forms=forms_cfg,
        leakage_policy=leakage_cfg,
        random_seed=int(raw["random_seed"]),
    )


__all__ = ["ProjectConfig", "PathsConfig", "YearsConfig", "FormsConfig", "LeakagePolicyConfig", "load_config"]

