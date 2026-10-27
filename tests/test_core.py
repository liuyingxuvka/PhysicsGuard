from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import numpy as np
from physicsguard.core.registry import VariableRecord
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.registry import ModuleRegistry, default_module_registry
from physicsguard.schema.system_spec import SystemSpec


from conftest import CustomModule, DuplicateVariableModule, FC, OBSERVED, ROOT, TANK, _block_lines, cli_env, linear_parameters, one_dummy_system, run_cli, system


def test_describe_json_keeps_every_inspect_field(monkeypatch) -> None:
    result = run_cli("hierarchy", "describe", str(FC / "tree.yaml"), "--pretty", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["audit_name"] == "fuel_cell_connected_tree"
    assert data["root_blocks"] == ["fc_system"]
    assert data["blocks"][0]["id"] == "fc_system"
    assert data["missing_components"] == []
    from physicsguard.core.hierarchy import describe_hierarchy, HierarchicalAuditRunner
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    def forbidden(*args, **kwargs):
        pytest.fail("description must not solve or evaluate")
    monkeypatch.setattr(BoundedSolver, "solve", forbidden)
    monkeypatch.setattr(HierarchicalAuditRunner, "evaluate_observed", forbidden)
    spec = load_hierarchical_audit_spec(FC / "tree.yaml")
    before = spec.model_dump(mode="json")
    declared = describe_hierarchy(spec)
    assert spec.model_dump(mode="json") == before
    assert declared["solver_attempted"] is False
    assert {"root_blocks", "unassigned_components", "scoring", "confidence", "referenced_components", "missing_components"} <= data.keys()
    assert data["scoring"] == spec.hierarchy.scoring.model_dump()
    assert data["confidence"] == spec.hierarchy.confidence.model_dump()
    for block, row in zip(spec.hierarchy.blocks, data["blocks"]):
        assert row["component_ids"] == block.components
        for key in ("required_variables", "optional_variables", "required_parameters", "optional_parameters", "refines", "tags"):
            assert row[key] == getattr(block, key)
    assert data["blocks"] == declared["blocks"]


def test_evaluate_prints_the_tree_with_verdicts(capsys) -> None:
    from physicsguard.cli import main

    args = ("hierarchy", "evaluate", str(TANK / "heated_tank.yaml"), str(TANK / "sparse_measured_k70.yaml"))
    code = main(list(args))
    tree = subprocess.CompletedProcess(args, code, capsys.readouterr().out, "")
    full = run_cli(*args, "--json")
    assert tree.returncode == full.returncode == 1, full.stderr
    assert not tree.stdout.startswith("{") and len(tree.stdout) <= 3000
    assert tree.stdout.startswith("audit heated_tank on tank_run_sparse_step_70: FAIL;")
    assert "components:" not in tree.stdout and not any(line.startswith("links:") for line in tree.stdout.splitlines())
    with_structure = run_cli(*args, "--full")
    assert with_structure.returncode == tree.returncode and "components:" in with_structure.stdout
    lines = _block_lines(tree.stdout)
    assert "own FAIL" in lines["thermal"]
    assert "not checked: 6 inputs missing" in lines["heater"]
    assert "assumptions: heater_nameplate_efficiency" in lines["heater"]
    for block in ("throughflow", "envelope"):
        assert "no checks" in lines[block] and "PASS" not in lines[block]
    assert "next: refine_thermal -> heater (block) needs heater current" in tree.stdout
    # The rule tree_view_shows_every_block_verdict: every block, with the report's own verdict.
    verdicts = {row["block_id"]: row for row in json.loads(full.stdout)["block_verdicts"]}
    assert set(lines) == set(verdicts)
    for block_id, row in verdicts.items():
        line = lines[block_id]
        if row["checked_residual_count"]:
            assert f"own {'PASS' if row['own_audit_pass'] else 'FAIL'} " in line
        else:
            assert "own PASS" not in line and "own FAIL" not in line
        assert ("not checked: " in line) is bool(row["missing_required_variables"])
    clean = run_cli("hierarchy", "evaluate", str(TANK / "heated_tank.yaml"), str(TANK / "measured_k30.yaml"))
    assert clean.returncode == 0 and ": PASS;" in clean.stdout.splitlines()[0]


def test_hierarchy_evaluate_reports_a_partial_snapshot(tmp_path: Path) -> None:
    import yaml

    from physicsguard.core.residual import ResidualBuilder
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    audit = ROOT / "examples" / "hierarchical" / "coolant_loop" / "tree.yaml"
    spec = load_hierarchical_audit_spec(audit)
    solved = BoundedSolver(ResidualBuilder(spec.system), spec.system.solver).solve().variables
    snapshot = {"variables": {name: {"value": float(value)} for name, value in solved.items() if name != "cool.Q_stack_heat_W"}}
    (tmp_path / "partial.yaml").write_text(yaml.safe_dump(snapshot), encoding="utf-8")
    result = run_cli("hierarchy", "evaluate", str(audit), str(tmp_path / "partial.yaml"))
    assert result.returncode == 0, result.stderr
    head = result.stdout.splitlines()[0]
    assert ": PASS;" in head and " 0 unchecked, 1 derived;" in head
    assert int(head.split(": PASS; ")[1].split(" checked")[0]) > 0
    assert "not checked:" not in result.stdout
    full = run_cli("hierarchy", "evaluate", str(audit), str(tmp_path / "partial.yaml"), "--json")
    assert full.returncode == 0, full.stderr
    report = json.loads(full.stdout)
    producing = report["derived_variables"]["cool.Q_stack_heat_W"]["residual_occurrence"]
    assert producing not in report["metadata"]["checked_residual_occurrences"]
    assert report["metadata"]["observed_variable_count"] == len(snapshot["variables"])

    fault = yaml.safe_load((OBSERVED / "pitch_feedback_observed_fault.yaml").read_text(encoding="utf-8"))
    del fault["variables"]["controller_q_gain.y"]
    (tmp_path / "nothing_left.yaml").write_text(yaml.safe_dump(fault), encoding="utf-8")
    result = run_cli("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(tmp_path / "nothing_left.yaml"))
    assert result.returncode == 2
    assert "no residual can be evaluated without them" in result.stderr


def test_duplicate_fully_qualified_variables_fail() -> None:
    registry = ModuleRegistry()
    registry.register(
        "DuplicateVariableModule",
        lambda component_id, parameters: DuplicateVariableModule(
            component_id,
            "DuplicateVariableModule",
            parameters,
        ),
    )
    spec = system(
        {
            "system_name": "duplicate_vars",
            "components": [
                {"id": "a", "type": "DuplicateVariableModule", "parameters": {}},
            ],
        }
    )
    with pytest.raises(ValueError, match="duplicate variable"):
        ResidualBuilder(spec, module_registry=registry).build_registry()


def test_post_check_residuals_are_not_in_solver_vector() -> None:
    spec = system(
        {
            "system_name": "post_check_vector",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": linear_parameters(a=1.0, b=0.0),
                },
                {
                    "id": "range",
                    "type": "RangeCheckModule",
                    "parameters": {
                        "variable": "rel.x",
                        "upper_bound": 1.0,
                        "residual_scale": 1.0,
                    },
                },
            ],
        }
    )
    builder = ResidualBuilder(spec)
    assert builder.residual_vector(np.array([2.0, 2.0])).tolist() == [0.0]
    diagnostic_records = builder.diagnostic_residual_records(np.array([2.0, 2.0]))
    assert [record.role for record in diagnostic_records] == ["equation", "post_check"]


def test_residual_vector_returns_normalized_values() -> None:
    builder = ResidualBuilder(one_dummy_system(target=10.0, scale=2.0))
    vector = builder.residual_vector(np.array([6.0]))
    assert vector.tolist() == [-2.0]
