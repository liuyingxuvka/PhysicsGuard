from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest


ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"
OBSERVED = ROOT / "examples" / "hierarchical" / "observed_debugging"


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "physicsguard.cli", *args],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_hierarchy_run_clean_example_returns_valid_json() -> None:
    result = run_cli("hierarchy", "run", str(FC / "tree.yaml"), "--pretty", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["audit_pass"]
    assert data["optimization_success"]
    root = next(block for block in data["top_blocks"] if block["block_id"] == "fc_system")
    assert root["audit_pass"] and root["own_audit_pass"]
    assert {
        "audit_name",
        "system_name",
        "optimization_success",
        "audit_pass",
        "residual_norm",
        "max_abs_normalized_residual",
        "top_residuals",
        "top_blocks",
        "block_assignments",
        "warnings",
    }.issubset(data)


def test_hierarchy_run_conflict_fails_with_code_1_and_audit_false(tmp_path) -> None:
    import yaml
    data = yaml.safe_load((FC / "tree.yaml").read_text())
    nominal = yaml.safe_load((FC / "nominal_observed.yaml").read_text())
    variant = next(row for row in data["fault_variants"] if row["id"] == "hydrogen_power_underread")
    change, = variant["changes"]
    value = nominal["variables"][change["variable"]]["value"] * change["scale"]
    data["system"]["boundaries"].append({"variable": change["variable"], "value": value,
                                          "scale": data["system"]["boundaries"][0]["scale"]})
    audit = tmp_path / "same-tree-underread.yaml"
    audit.write_text(yaml.safe_dump(data))
    result = run_cli("hierarchy", "run", str(audit), "--pretty", "--json")
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert not data["audit_pass"]
    root = next(block for block in data["top_blocks"] if block["block_id"] == "fc_system")
    assert not root["audit_pass"] and not data["top_blocks"][0]["audit_pass"]
    assert data["recommended_refinements"]


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


def test_hierarchy_evaluate_observed_fault_returns_block_rollup_without_solver() -> None:
    result = run_cli(
        "hierarchy",
        "evaluate",
        str(OBSERVED / "pitch_feedback_level_0.yaml"),
        str(OBSERVED / "pitch_feedback_observed_fault.yaml"),
        "--pretty",
        "--json",
    )
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert not data["audit_pass"]
    assert data["metadata"]["mode"] == "hierarchy_evaluate"
    assert data["metadata"]["solver_attempted"] is False
    assert data["top_blocks"][0]["block_id"] == "pitch_rate_feedback"
    assert data["recommended_refinements"][0]["next_required_variables"]


def test_hierarchy_compare_observed_fault_returns_deviations_and_hierarchy() -> None:
    result = run_cli(
        "hierarchy",
        "compare",
        str(OBSERVED / "pitch_feedback_level_0.yaml"),
        str(OBSERVED / "pitch_feedback_observed_fault.yaml"),
        "--pretty",
        "--json",
    )
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert data["metadata"]["mode"] == "hierarchy_compare"
    assert data["reference_audit_pass"]
    assert not data["observed_audit_pass"]
    assert data["top_variable_deviations"][0]["variable"] == "controller_q_gain.y"
    assert data["observed_hierarchy"]["top_blocks"][0]["block_id"] == "pitch_rate_feedback"


def test_hierarchy_invalid_file_returns_nonzero() -> None:
    result = run_cli("hierarchy", "run", str(FC / "missing.yaml"))
    assert result.returncode == 2


def test_single_system_runs_through_hierarchy_cli() -> None:
    result = run_cli("hierarchy", "run", str(ROOT / "examples" / "dummy_system.yaml"), "--pretty", "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["system_name"] == "dummy_clean_system"


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
    data = json.loads(result.stdout)
    assert data["audit_pass"]
    assert data["missing_required_variables"] == []
    assert data["derived_variables"] == ["cool.Q_stack_heat_W"]
    assert data["checked_residual_count"] > 0
    assert data["unchecked_residual_count"] == 0
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


def test_hierarchy_evaluate_prints_a_compact_summary_without_input_echo() -> None:
    args = ("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(OBSERVED / "pitch_feedback_observed_fault.yaml"))
    summary = run_cli(*args)
    full = run_cli(*args, "--json")
    assert summary.returncode == full.returncode == 1, summary.stderr
    assert len(summary.stdout) < 4096 < len(full.stdout)
    data = json.loads(summary.stdout)
    assert data["output"] == "summary only; add --json for the full report"
    assert data["audit_pass"] is False
    assert data["top_blocks"][0]["block_id"] == "pitch_rate_feedback"
    assert {item["followup_id"] for item in data["bug_family_followups"]} == {"linear_gain_sign_family"}
    assert "metadata" not in data and "block_assignments" not in data
    assert "hierarchy" not in json.loads(full.stdout)["metadata"]


@pytest.mark.parametrize("fault", [False, True])
def test_pitch_parent_verdict_and_own_score_are_distinct(fault) -> None:
    snapshot = "pitch_feedback_observed_fault.yaml" if fault else "pitch_feedback_observed_clean.yaml"
    result = run_cli("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(OBSERVED / snapshot))
    assert result.returncode == int(fault), result.stderr
    data = json.loads(result.stdout)
    parent = next(block for block in data["top_blocks"] if block["block_id"] == "f14_flight_control")
    assert parent["audit_pass"] is (not fault)
    assert parent["own_audit_pass"] is True and parent["score"] == 0
    if fault:
        assert parent["subtree_score"] == data["top_blocks"][0]["score"] > 1


def test_cli_resolves_real_coolant_templates_and_reports_missing_files(tmp_path) -> None:
    import yaml
    directory = ROOT / "examples/hierarchical/coolant_loop"
    audit_data = yaml.safe_load((directory / "tree.yaml").read_text())
    observed = yaml.safe_load((directory / "nominal_observed.yaml").read_text())
    variant = next(row for row in audit_data["fault_variants"] if row["id"] == "heat_rejection")
    change, = variant["changes"]
    observed["variables"][change["variable"]]["value"] *= change["scale"]
    measured = tmp_path / "heat-rejection.yaml"
    measured.write_text(yaml.safe_dump(observed))
    result = run_cli("hierarchy", "evaluate", str(directory / "tree.yaml"), str(measured), "--json")
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert any(rec["template_status"].get("radiator") == "block" for rec in data["recommended_refinements"])
    # File and unbuilt targets remain separately observable in a temporary rule,
    # while shipped tree rules resolve only to their real local blocks.
    existing = tmp_path / "existing_detail.yaml"
    existing.write_text("# A future audit file is present, but this check must not load it.\n")
    audit_data["hierarchy"]["refinement_rules"][0]["next_template_ids"] = [existing.name, "future_detail"]
    audit = tmp_path / "same-tree-new-detail.yaml"
    audit.write_text(yaml.safe_dump(audit_data))
    result = run_cli("hierarchy", "evaluate", str(audit), str(measured), "--json")
    assert result.returncode == 1, result.stderr
    data = json.loads(result.stdout)
    assert any(rec["template_status"].get(existing.name) == "file" for rec in data["recommended_refinements"])
    assert any(rec["template_status"].get("future_detail") == "planned" for rec in data["recommended_refinements"])
    assert "refinement_template_planned: future_detail" in data["warnings"]


def test_removed_hierarchy_plan_exits_two():
    assert run_cli('hierarchy','plan','x.yaml').returncode == 2


def test_describe_prints_a_readable_tree_with_variants() -> None:
    tank = ROOT / "examples/hierarchical/heated_tank/heated_tank.yaml"
    result = run_cli("hierarchy", "describe", str(tank))
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.encode()) <= 3000
    assert result.stdout.startswith("audit heated_tank: 6 blocks,")
    heater = next(line for line in result.stdout.splitlines() if line.lstrip().startswith("heater [L2]"))
    assert "variants: heater_half" in heater and "heater_el(ElectricalPowerModule)" in heater
    assert "refines: tank_energy" in result.stdout and "heater (block)" in result.stdout
    assert "links: " in result.stdout
    assert run_cli("hierarchy", "inspect", str(tank)).returncode == 2


def test_describe_observed_counts_signals_per_block(monkeypatch) -> None:
    from physicsguard.core.hierarchy import describe_hierarchy, HierarchicalAuditRunner
    from physicsguard.core.solver import BoundedSolver
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    directory = ROOT / "examples/hierarchical/heated_tank"
    result = run_cli("hierarchy", "describe", str(directory / "heated_tank.yaml"),
                     "--observed", str(directory / "measured_k70.yaml"))
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("| signals:") == 6
    spec = load_hierarchical_audit_spec(directory / "heated_tank.yaml")
    observed = load_observed_values(directory / "measured_k70.yaml")
    observed.variables["heater_el.current_A"].review_required = True
    before = spec.model_dump(mode="json"), observed.model_dump(mode="json")
    def forbidden(*args, **kwargs):
        pytest.fail("signal description must not solve or evaluate")
    monkeypatch.setattr(BoundedSolver, "solve", forbidden)
    monkeypatch.setattr(HierarchicalAuditRunner, "evaluate_observed", forbidden)
    description = describe_hierarchy(spec, observed=observed)
    assert (spec.model_dump(mode="json"), observed.model_dump(mode="json")) == before
    rows = {block["id"]: block["signals"] for block in description["blocks"]}
    assert rows["heater"] == {"mapped": 3, "review_required": 1, "required_missing": 0}
    assert sum(row["mapped"] for row in rows.values()) == len(observed.variables)
    assert description["solver_attempted"] is False


def test_full_evaluation_preserves_source_model_without_changing_the_verdict(tmp_path):
    import yaml

    audit = OBSERVED / "pitch_feedback_level_0.yaml"
    original = OBSERVED / "pitch_feedback_observed_fault.yaml"
    payload = yaml.safe_load(original.read_text())
    header = {"model_name": " model A ", "tool": "exporter", "scenario": "run A"}
    payload["source_model"] = header
    measured = tmp_path / "source-model.yaml"
    measured.write_text(yaml.safe_dump(payload))
    plain = run_cli("hierarchy", "evaluate", str(audit), str(original), "--json")
    tagged = run_cli("hierarchy", "evaluate", str(audit), str(measured), "--json")
    assert plain.returncode == tagged.returncode == 1, tagged.stderr
    before, after = json.loads(plain.stdout), json.loads(tagged.stdout)
    assert after["metadata"].pop("source_model") == header
    assert after == before


def test_full_evaluation_without_source_model_omits_the_header():
    result = run_cli("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"),
                     str(OBSERVED / "pitch_feedback_observed_fault.yaml"), "--json")
    assert result.returncode == 1, result.stderr
    assert "source_model" not in json.loads(result.stdout)["metadata"]


def test_mapping_summary_counts_the_whole_native_ledger(tmp_path):
    import yaml

    directory = ROOT / "examples/hierarchical/building_hvac"
    payload = yaml.safe_load((directory / "nominal_observed.yaml").read_text())
    variable = next(iter(payload["variables"].values()))
    variable.update(mapping_confidence="low", mapping_status="stale", review_required=True)
    variable.pop("unit", None)
    observed = tmp_path / "mapping.yaml"
    observed.write_text(yaml.safe_dump(payload))
    args = ("hierarchy", "evaluate", str(directory / "tree.yaml"), str(observed))
    full, compact = run_cli(*args, "--json"), run_cli(*args)
    assert full.returncode == compact.returncode == 0, full.stderr
    ledger = json.loads(full.stdout)["signal_mapping_ledger"]
    summary = json.loads(compact.stdout)["mapping_summary"]
    assert summary == {
        "rows": len(ledger),
        "with_issues": sum(bool(row["issue_codes"]) for row in ledger),
        "review_required": sum(row["review_required"] is True for row in ledger),
        "stale": sum("stale_mapping" in row["issue_codes"] for row in ledger),
        "low_confidence": sum("low_confidence" in row["issue_codes"] for row in ledger),
        "missing_unit": sum("missing_unit" in row["issue_codes"] for row in ledger),
    }
    assert all(summary[key] >= 1 for key in ("stale", "low_confidence", "review_required"))
    assert summary["missing_unit"] >= 1
