from __future__ import annotations

from pathlib import Path
import json

import yaml

import pytest

from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec


ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"


def test_valid_hierarchical_yaml_loads() -> None:
    spec = load_hierarchical_audit_spec(FC / "tree.yaml")
    assert spec.audit_name == "fuel_cell_connected_tree"
    assert spec.system.system_name == "fuel_cell_connected_tree"
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


def test_system_only_yaml_reads_as_one_block_tree(tmp_path: Path) -> None:
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

    spec = load_hierarchical_audit_spec(path)
    block, = spec.hierarchy.blocks
    assert spec.audit_name == spec.system.system_name == "bad"
    assert block.id == "bad" and block.level == 0 and block.parent_id is None
    assert block.components == ["d"]
    assert spec.metadata["wrapped_single_block"] is True


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


def test_flat_system_file_reads_as_one_block_tree(capsys) -> None:
    from physicsguard.cli import main

    path = ROOT / "examples/foundation/thermal_conductor.yaml"
    spec = load_hierarchical_audit_spec(path)
    block, = spec.hierarchy.blocks
    assert block.id == spec.system.system_name and block.level == 0
    assert block.components == [component.id for component in spec.system.components]
    assert spec.metadata["wrapped_single_block"] is True
    assert main(["hierarchy", "run", str(path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["metadata"]["wrapped_single_block"] is True


@pytest.mark.parametrize("name", ["tank system", " plant\t1 "])
def test_single_system_name_keeps_display_with_a_legal_root_id(tmp_path, name) -> None:
    path = tmp_path / "flat.yaml"
    path.write_text(yaml.safe_dump({"system_name": name, "components": [
        {"id": "d", "type": "DummyResidualModule", "parameters": {"target": 0.0}}]}), encoding="utf-8")
    spec = load_hierarchical_audit_spec(path)
    block, = spec.hierarchy.blocks
    assert spec.audit_name == spec.system.system_name == block.name == name
    assert block.id and not any(character.isspace() for character in block.id)
    assert load_hierarchical_audit_spec(path).hierarchy.blocks[0].id == block.id


def test_flat_and_tree_files_give_the_same_verdict(tmp_path, capsys) -> None:
    from physicsguard.cli import main

    directory = ROOT / "examples/hierarchical/heated_tank"
    tree = directory / "heated_tank.yaml"
    observed = directory / "measured_k70.yaml"
    source = load_hierarchical_audit_spec(tree)
    flat = tmp_path / "flat.yaml"
    flat.write_text(yaml.safe_dump(source.system.model_dump(mode="json")), encoding="utf-8")
    assert main(["hierarchy", "evaluate", str(tree), str(observed), "--json"]) == 1
    tree_report = json.loads(capsys.readouterr().out)
    assert main(["hierarchy", "evaluate", str(flat), str(observed), "--json"]) == 1
    flat_report = json.loads(capsys.readouterr().out)
    assert flat_report["audit_pass"] is tree_report["audit_pass"] is False
    assert set(flat_report["derived_variables"]) == set(tree_report["derived_variables"])
    assert flat_report["top_blocks"][0]["block_id"] == load_hierarchical_audit_spec(flat).hierarchy.blocks[0].id
    assert tree_report["top_blocks"][0]["block_id"] == "heater"
    assert flat_report["metadata"]["wrapped_single_block"] is True
