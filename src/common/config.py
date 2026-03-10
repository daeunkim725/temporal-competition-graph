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


def load_config(config_path: str | Path = "config/config.yaml") -> ProjectConfig:
    """
    Load the project configuration from YAML and return a typed ProjectConfig.

    This helper should be used by all scripts to ensure a single source of truth
    for paths, years, and leakage-related settings.
    """
    path = Path(config_path)
    raw = _load_yaml(path)

    paths_cfg = PathsConfig(
        data_root=Path(raw["paths"]["data_root"]),
        raw_sec_index=Path(raw["paths"]["raw_sec_index"]),
        raw_sec_filings=Path(raw["paths"]["raw_sec_filings"]),
        processed_root=Path(raw["paths"]["processed_root"]),
        companies=Path(raw["paths"]["companies"]),
        filings=Path(raw["paths"]["filings"]),
        evidence=Path(raw["paths"]["evidence"]),
        graphs=Path(raw["paths"]["graphs"]),
        firm_year=Path(raw["paths"]["firm_year"]),
        splits=Path(raw["paths"]["splits"]),
    )

    years_cfg = YearsConfig(
        history_start=int(raw["years"]["history_start"]),
        history_end=int(raw["years"]["history_end"]),
        train_target=int(raw["years"]["train_target"]),
        val_target=int(raw["years"]["val_target"]),
        test_target=int(raw["years"]["test_target"]),
        max_year=int(raw["years"]["max_year"]),
    )

    forms_cfg = FormsConfig(primary=list(raw["forms"]["primary"]))

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

