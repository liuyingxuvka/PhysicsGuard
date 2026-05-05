from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.io.observation_loader import load_observed_values


ROOT = Path(__file__).resolve().parents[1]


def test_valid_observed_yaml_loads() -> None:
    observed = load_observed_values(
        ROOT / "examples" / "observed" / "physical_coolant_observed_clean.yaml"
    )
    assert observed.observation_name == "physical_coolant_observed_clean"
    assert observed.variables["coolant.Q_dot_W"].value == 4180.0


def test_empty_observed_yaml_fails(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_observed_values(path)


def test_invalid_observed_schema_fails(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("variables:\n  bad_name:\n    value: 1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid ObservedValuesSpec"):
        load_observed_values(path)


def test_missing_observed_file_fails() -> None:
    with pytest.raises(ValueError, match="failed to read observed values"):
        load_observed_values(ROOT / "examples" / "observed" / "missing.yaml")


def test_observed_yaml_missing_variables_fails(tmp_path: Path) -> None:
    path = tmp_path / "missing_variables.yaml"
    path.write_text("observation_name: bad\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing variables"):
        load_observed_values(path)
