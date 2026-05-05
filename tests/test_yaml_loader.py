from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.io.yaml_loader import load_system_spec


def test_valid_dummy_yaml_loads() -> None:
    spec = load_system_spec(Path("examples/dummy_system.yaml"))
    assert spec.system_name == "dummy_clean_system"


def test_invalid_yaml_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("system_name: [", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed YAML"):
        load_system_spec(path)


def test_empty_yaml_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty YAML"):
        load_system_spec(path)


def test_malformed_schema_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "schema.yaml"
    path.write_text("system_name: ''\ncomponents: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid SystemSpec"):
        load_system_spec(path)
