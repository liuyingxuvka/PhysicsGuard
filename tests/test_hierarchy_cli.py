from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest


from conftest import FC, OBSERVED, ROOT, TANK, _block_lines, cli_env, run_cli

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


def test_hierarchy_evaluate_prints_the_tree_without_input_echo() -> None:
    args = ("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(OBSERVED / "pitch_feedback_observed_fault.yaml"))
    tree = run_cli(*args)
    full = run_cli(*args, "--json")
    assert tree.returncode == full.returncode == 1, tree.stderr
    assert len(tree.stdout) < 4096 < len(full.stdout)
    assert not tree.stdout.startswith("{")
    assert tree.stdout.startswith("audit observed_pitch_feedback_level_0 on pitch_feedback_observed_fault: FAIL;")
    line = next(row for row in tree.stdout.splitlines() if row.startswith("  pitch_rate_feedback [L1]"))
    assert "own FAIL" in line and "controller_q_gain.linear_relation" in line
    assert "hierarchy" not in json.loads(full.stdout)["metadata"]


@pytest.mark.parametrize("fault", [False, True])
def test_pitch_parent_verdict_and_own_score_are_distinct(fault) -> None:
    snapshot = "pitch_feedback_observed_fault.yaml" if fault else "pitch_feedback_observed_clean.yaml"
    result = run_cli("hierarchy", "evaluate", str(OBSERVED / "pitch_feedback_level_0.yaml"), str(OBSERVED / snapshot), "--json")
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
    assert rows["heater"] == {"mapped": 3, "review_required": 1, "declared_required_missing": 0}
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
    full, tree = run_cli(*args, "--json"), run_cli(*args)
    assert full.returncode == tree.returncode == 0, full.stderr
    ledger = json.loads(full.stdout)["signal_mapping_ledger"]
    issues = sum(bool(row["issue_codes"]) for row in ledger)
    assert f"; mapping {len(ledger)} rows, {issues} with issues" in tree.stdout.splitlines()[0]
    mapping = next(line for line in tree.stdout.splitlines() if line.startswith("mapping: "))
    assert all(code in mapping for code in ("stale_mapping", "low_confidence", "missing_unit"))


HEAD_REPORT_KEYS = {
    "assumptions", "audit_name", "audit_pass", "block_assignments", "bug_family_followups", "checked_residuals",
    "derived_variables", "max_abs_normalized_residual", "metadata", "missing_required_parameters",
    "missing_required_variables", "optimization_success", "recommended_refinements", "refinement_checks",
    "residual_norm", "signal_mapping_ledger", "system_name", "top_blocks", "top_residuals", "unassigned_residuals",
    "unchecked_residuals", "warnings",
}


def test_variants_prints_the_tree_with_signatures() -> None:
    args = ("hierarchy", "variants", str(TANK / "heated_tank.yaml"), str(TANK / "measured_k30.yaml"),
            "--pairs", "--observed", str(TANK / "measured_k70.yaml"))
    tree, full = run_cli(*args), run_cli(*args, "--json")
    assert tree.returncode == full.returncode == 0, tree.stderr
    assert len(tree.stdout) <= 3000
    lines = _block_lines(tree.stdout)
    assert "variants failing here: heater_half(-)" in lines["heater"]
    for text in ("masked: heater_half+inlet_temp_offset", "matches: heater_half", "model miss: no",
                 "indistinguishable: extra_wall_loss+inlet_temp_offset next signal heat.Q_out_W",
                 "variant outflow_rounding benign: neutral", "pair heater_half+inlet_temp_offset: masked", "boundary: "):
        assert text in tree.stdout
    data = json.loads(full.stdout)
    assert {"pairwise", "masked_pairs", "next_signal", "generated_values"} <= set(data) | set(data["variants"][0])


def test_json_keeps_the_full_report() -> None:
    for snapshot in ("sparse_measured_k70.yaml", "measured_k30.yaml"):
        result = run_cli("hierarchy", "evaluate", str(TANK / "heated_tank.yaml"), str(TANK / snapshot), "--json")
        data = json.loads(result.stdout)
        assert set(data) == HEAD_REPORT_KEYS | {"block_verdicts"}
        assert [row["block_id"] for row in data["block_verdicts"]] == ["tank", "hydraulics", "thermal", "heater", "throughflow", "envelope"]
    compare = run_cli("hierarchy", "compare", str(OBSERVED / "pitch_feedback_level_0.yaml"),
                      str(OBSERVED / "pitch_feedback_observed_fault.yaml"))
    assert compare.returncode == 1 and "; reference PASS" in compare.stdout.splitlines()[0]


def test_describe_observed_counts_declared_needs() -> None:
    result = run_cli("hierarchy", "describe", str(TANK / "heated_tank.yaml"), "--observed", str(TANK / "sparse_measured_k70.yaml"))
    assert result.returncode == 0, result.stderr
    assert "0 declared needs missing" in _block_lines(result.stdout)["heater"]
    full = run_cli("hierarchy", "describe", str(TANK / "heated_tank.yaml"), "--observed", str(TANK / "sparse_measured_k70.yaml"), "--json")
    signals = {block["id"]: block["signals"] for block in json.loads(full.stdout)["blocks"]}
    assert set(signals["heater"]) == {"mapped", "review_required", "declared_required_missing"}


def test_describe_names_benign_variants_and_assumption_blocks() -> None:
    result = run_cli("hierarchy", "describe", str(TANK / "heated_tank.yaml"))
    assert result.returncode == 0, result.stderr
    first, *_ = result.stdout.splitlines()
    assert first.endswith("; benign: outflow_rounding")
    lines = _block_lines(result.stdout)
    assert "assumptions: heater_nameplate_efficiency" in lines["heater"]
    assert sum("assumptions:" in line for line in lines.values()) == 1
