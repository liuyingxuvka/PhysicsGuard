from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"


def test_valid_hierarchical_yaml_loads() -> None:
    spec = load_hierarchical_audit_spec(FC / "level_0_system_balance.yaml")
    assert spec.audit_name == "fuel_cell_level_0_system_balance"
    assert spec.system.system_name == "fuel_cell_level_0_system_balance"
    assert spec.hierarchy.blocks[0].id == "fc_system"


def test_missing_hierarchical_yaml_file_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_hierarchical_audit_spec(tmp_path / "missing.yaml")


def test_empty_hierarchical_yaml_fails(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        load_hierarchical_audit_spec(path)


def test_hierarchical_yaml_missing_system_fails(tmp_path: Path) -> None:
    path = tmp_path / "missing_system.yaml"
    path.write_text(
        """
audit_name: bad
hierarchy:
  blocks:
    - id: root
      level: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="system"):
        load_hierarchical_audit_spec(path)


def test_hierarchical_yaml_missing_hierarchy_fails(tmp_path: Path) -> None:
    path = tmp_path / "missing_hierarchy.yaml"
    path.write_text(
        """
audit_name: bad
system:
  system_name: bad
  components:
    - id: d
      type: DummyResidualModule
      parameters:
        target: 0.0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hierarchy"):
        load_hierarchical_audit_spec(path)


def test_invalid_block_in_hierarchical_yaml_fails(tmp_path: Path) -> None:
    path = tmp_path / "invalid_block.yaml"
    path.write_text(
        """
audit_name: bad
system:
  system_name: bad
  components:
    - id: d
      type: DummyResidualModule
      parameters:
        target: 0.0
hierarchy:
  blocks:
    - id: ""
      level: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid hierarchical audit schema"):
        load_hierarchical_audit_spec(path)
