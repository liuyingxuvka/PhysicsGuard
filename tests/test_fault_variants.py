from __future__ import annotations

import json
from pathlib import Path

import pytest

from physicsguard.cli import main
from physicsguard.core.diagnosability import evaluate_fault_variants
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec


TANK = Path(__file__).resolve().parents[1] / "examples/hierarchical/heated_tank"


def _case(variants, *, unmeasured_signals=False):
    """Two directly checked blocks; the parent also owns its own equation."""
    components = [
        {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.}},
        {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 0.}},
    ]
    if unmeasured_signals:
        components.extend([
            {"id": "fine", "type": "DummyResidualModule", "parameters": {"target": 10., "scale": 1.}},
            {"id": "wide", "type": "DummyResidualModule", "parameters": {
                "target": 100., "scale": 1000., "lower_bound": 0., "upper_bound": 10000.,
            }},
        ])
    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "variant-boundaries",
        "system": {"system_name": "variant-boundaries", "components": components},
        "hierarchy": {"blocks": [
            {"id": "thermal", "level": 0, "components": [item["id"] for item in components if item["id"] != "b"]},
            {"id": "heater", "parent_id": "thermal", "level": 1, "components": ["b"]},
        ]},
        "fault_variants": variants,
    })
    nominal = ObservedValuesSpec(variables={"a.x": {"value": 0.}, "b.x": {"value": 0.}})
    return spec, nominal


def _fault(identifier, variable, offset, block):
    return {"id": identifier, "kind": "fault", "changes": [{"variable": variable, "offset": offset}],
            "expect_blocks": [block]}


def test_clean_nominal_is_accepted_without_mutating_inputs() -> None:
    spec, nominal = _case([_fault("heated", "a.x", 2., "thermal")])
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")

    result = evaluate_fault_variants(spec, nominal, variant_ids=())

    assert result["nominal_audit_pass"] and result["ok"]
    assert result["nominal_signature"] == {} and result["variants"] == []
    assert result["model_miss"] is None
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before


def test_each_declared_tank_fault_is_detected_with_direct_block_evidence() -> None:
    spec = load_hierarchical_audit_spec(TANK / "heated_tank.yaml")
    nominal = load_observed_values(TANK / "measured_k30.yaml")
    observed = load_observed_values(TANK / "measured_k70.yaml")
    before = tuple(item.model_dump(mode="json") for item in (spec, nominal, observed))

    result = evaluate_fault_variants(spec, nominal, observed=observed, base_dir=TANK)

    assert result["nominal_audit_pass"] and result["nominal_signature"] == {}
    rows = {row["id"]: row for row in result["variants"]}
    faults = {variant.id for variant in spec.fault_variants if variant.kind == "fault"}
    assert faults == {"heater_half", "extra_wall_loss", "inlet_temp_offset", "outflow_unit_x1000"}
    assert result["ok"]
    assert all(rows[name]["detected"] and rows[name]["expect_blocks_met"] and not rows[name]["audit_pass"]
               for name in faults)
    assert rows["heater_half"]["signature"] == {"heater": "-"}
    # thermal owns heat/qout despite having children; its own failure is not discarded.
    assert rows["extra_wall_loss"]["signature"] == {"tank": "-", "thermal": "-"}
    assert rows["inlet_temp_offset"]["signature"] == {"tank": "-", "thermal": "-"}
    assert rows["outflow_unit_x1000"]["signature"] == {"hydraulics": "+", "tank": "+"}
    assert rows["outflow_rounding"]["neutral"] and rows["outflow_rounding"]["signature"] == {}
    assert "heater_half" in result["matching_variants"]
    assert tuple(item.model_dump(mode="json") for item in (spec, nominal, observed)) == before


def test_combined_faults_report_every_direct_failure() -> None:
    spec, nominal = _case([_fault("parent_fault", "a.x", 2., "thermal"),
                           _fault("child_fault", "b.x", 3., "heater")])

    result = evaluate_fault_variants(spec, nominal, pairs=True)

    rows = {row["id"]: row for row in result["variants"]}
    assert rows["parent_fault"]["signature"] == {"thermal": "+"}
    assert rows["child_fault"]["signature"] == {"heater": "+"}
    assert len(result["pairs"]) == 1
    pair = result["pairs"][0]
    assert pair["variant_ids"] == ["parent_fault", "child_fault"]
    assert pair["signature"] == {"heater": "+", "thermal": "+"}
    assert pair["generated_values"]["a.x"] == 2. and pair["generated_values"]["b.x"] == 3.
    assert pair["expected_blocks"] == ["heater", "thermal"]
    assert pair["detected"] and pair["expect_blocks_met"] and result["ok"]
    assert pair["pair_status"] == "ok"


def test_benign_default_parameter_override_keeps_the_verdict() -> None:
    spec, nominal = _case([{"id": "default_scale", "kind": "benign", "parameters": {"a.scale": 2.}}])
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")
    assert "scale" not in spec.system.components[0].parameters

    result = evaluate_fault_variants(spec, nominal)

    row = result["variants"][0]
    assert row["neutral"] and row["audit_pass"] and row["ok"] and result["ok"]
    assert row["signature"] == {} and row["generated_values"] == {"a.x": 0., "b.x": 0.}
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before


def test_alternate_device_rederives_data_then_checks_the_nominal_model() -> None:
    spec, nominal = _case([{"id": "alternate_target", "kind": "fault", "parameters": {"a.target": 4.},
                            "rederive": ["a.x"], "expect_blocks": ["thermal"]}])
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")

    result = evaluate_fault_variants(spec, nominal)

    row = result["variants"][0]
    assert row["rederived_variables"] == ["a.x"]
    assert row["generated_values"]["a.x"] == pytest.approx(4.)
    assert row["device_values"]["a.x"] == pytest.approx(4.)
    # The alternate device accepts x=4; only the unchanged target=0 model rejects it.
    assert row["signature"] == {"thermal": "+"}
    assert not row["audit_pass"] and row["detected"] and row["expect_blocks_met"]
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before


def test_a_noop_fault_cannot_claim_detection(tmp_path, capsys) -> None:
    spec, nominal = _case([{"id": "noop", "kind": "fault", "changes": [{"variable": "a.x", "scale": 1.}],
                            "expect_blocks": ["thermal"]}])

    result = evaluate_fault_variants(spec, nominal)

    row = result["variants"][0]
    assert row["audit_pass"] and row["signature"] == {}
    assert not row["detected"] and not row["expect_blocks_met"] and not row["ok"] and not result["ok"]
    audit, measured = tmp_path / "noop.yaml", tmp_path / "nominal.yaml"
    audit.write_text(json.dumps(spec.model_dump(mode="json")))
    measured.write_text(json.dumps(nominal.model_dump(mode="json")))
    assert main(["hierarchy", "variants", str(audit), str(measured), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["variants"][0]["detected"] is False


@pytest.mark.parametrize("error", ["two_operations", "unknown_component", "unknown_expected_block"])
def test_variant_input_errors_keep_exit_two(error, tmp_path, capsys) -> None:
    spec, nominal = _case([_fault("bad", "a.x", 2., "thermal")])
    data = spec.model_dump(mode="json")
    variant = data["fault_variants"][0]
    if error == "two_operations":
        variant["changes"][0]["scale"] = 2.
    elif error == "unknown_component":
        variant["parameters"] = {"absent.scale": 2.}
    else:
        variant["expect_blocks"] = ["absent"]
    audit, measured = tmp_path / "bad.yaml", tmp_path / "nominal.yaml"
    audit.write_text(json.dumps(data))
    measured.write_text(json.dumps(nominal.model_dump(mode="json")))
    assert main(["hierarchy", "variants", str(audit), str(measured), "--json"]) == 2
    captured = capsys.readouterr()
    assert "physicsguard error:" in captured.err and not captured.out


def test_undetected_pair_fails() -> None:
    spec, nominal = _case([_fault("plus", "a.x", 2., "thermal"), _fault("minus", "a.x", -2., "thermal")])

    result = evaluate_fault_variants(spec, nominal, pairs=True)

    assert {row["id"]: row["signature"] for row in result["variants"]} == {
        "plus": {"thermal": "+"}, "minus": {"thermal": "-"},
    }
    pair = result["pairs"][0]
    assert pair["generated_values"]["a.x"] == 0. and pair["audit_pass"]
    assert pair["signature"] == {} and not pair["detected"] and not pair["expect_blocks_met"]
    assert not pair["ok"] and not result["ok"]
    assert pair["pair_status"] == "undetected"


def test_out_of_domain_pair_remains_explicit_without_losing_other_results() -> None:
    spec = load_hierarchical_audit_spec(TANK / "heated_tank.yaml").model_copy(deep=True)
    nominal = load_observed_values(TANK / "measured_k30.yaml")
    spec.fault_variants = [variant for variant in spec.fault_variants if variant.id in {"heater_half", "outflow_unit_x1000"}]
    flow = next(variant for variant in spec.fault_variants if variant.id == "outflow_unit_x1000")
    flow.id = "original_inflow_unit_x1000"
    flow.changes[0].variable = "inflow_mass.V_dot_m3_s"

    result = evaluate_fault_variants(spec, nominal, pairs=True)

    assert len(result["variants"]) == 2 and all(row["status"] == "evaluated" for row in result["variants"])
    pair, = result["pairs"]
    assert pair["status"] == "not_evaluable" and "could not rederive" in pair["reason"]
    assert pair["signature"] is None and pair["audit_pass"] is None
    assert not pair["detected"] and not pair["ok"] and not result["ok"]
    assert pair["pair_status"] is None


def test_unavailable_single_preserves_valid_rows(tmp_path, capsys) -> None:
    spec, nominal = _case([
        {"id": "outside_bounds", "kind": "fault", "parameters": {"a.target": 200.}, "rederive": ["a.x"]},
        _fault("valid_fault", "b.x", 2., "heater"),
    ])
    audit, measured = (tmp_path / name for name in ("audit.yaml", "nominal.yaml"))
    audit.write_text(json.dumps(spec.model_dump(mode="json")))
    measured.write_text(json.dumps(nominal.model_dump(mode="json")))
    assert main(["hierarchy", "variants", str(audit), str(measured), "--json"]) == 1
    output = json.loads(capsys.readouterr().out)
    rows = {row["id"]: row for row in output["variants"]}
    assert rows["outside_bounds"]["status"] == "not_evaluable" and rows["outside_bounds"]["signature"] is None
    assert rows["valid_fault"]["status"] == "evaluated" and rows["valid_fault"]["signature"] == {"heater": "+"}
    assert not output["ok"]
    assert output["pairwise"] == []  # one evaluated fault cannot form a usable pair
    assert rows["outside_bounds"]["pair_status"] is None


@pytest.mark.parametrize(("operation", "value", "expected"), [("scale", .5, 1.5), ("offset", 2., 5.), ("set", 0., 0.), ("flip_sign", True, -3.)])
def test_each_measurement_edit_uses_the_real_changed_value(operation, value, expected) -> None:
    spec, nominal = _case([{"id": "edit", "kind": "fault",
                            "changes": [{"variable": "a.x", operation: value}], "expect_blocks": ["thermal"]}])
    spec.system.components[0].parameters["target"] = 3.
    nominal.variables["a.x"].value = 3.

    result = evaluate_fault_variants(spec, nominal)

    row, = result["variants"]
    assert row["generated_values"]["a.x"] == expected
    assert row["detected"] and row["expect_blocks_met"]
    assert nominal.variables["a.x"].value == 3.


def test_masked_pair_is_listed_not_failed() -> None:
    spec = load_hierarchical_audit_spec(TANK / "heated_tank.yaml")
    nominal = load_observed_values(TANK / "measured_k30.yaml")
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")
    result = evaluate_fault_variants(spec, nominal, pairs=True, base_dir=TANK)
    pair = next(row for row in result["pairs"] if row["id"] == "heater_half+inlet_temp_offset")
    assert pair["status"] == "evaluated" and pair["pair_status"] == "masked"
    assert pair["signature"] == {"heater": "-"}
    assert pair["expected_blocks"] == ["heater", "tank", "thermal"]
    assert pair["detected"] and not pair["expect_blocks_met"] and pair["ok"]
    assert result["masked_pairs"] == [pair["id"]]
    assert result["ok"]
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before


def test_failure_outside_the_expected_blocks_fails() -> None:
    variants = [_fault("one", "a.x", 2., "thermal"), _fault("two", "a.x", 3., "thermal")]
    for variant in variants:
        variant["changes"].append({"variable": "b.x", "offset": .75})
    spec, nominal = _case(variants)
    for component in spec.system.components:
        component.parameters["scale"] = 1.
    result = evaluate_fault_variants(spec, nominal, pairs=True)
    assert all(row["ok"] and row["signature"] == {"thermal": "+"} for row in result["variants"])
    pair, = result["pairs"]
    assert pair["generated_values"] == {"a.x": 5., "b.x": 1.5}
    assert pair["signature"] == {"heater": "+", "thermal": "+"}
    assert pair["expected_blocks"] == ["thermal"]
    assert pair["pair_status"] == "outside" and not pair["ok"] and not result["ok"]
    assert result["masked_pairs"] == []


def test_observed_failure_no_variant_explains_is_a_model_miss(tmp_path, capsys) -> None:
    spec, nominal = _case([_fault("one", "a.x", 2., "thermal")])
    observed = nominal.model_copy(deep=True)
    observed.variables["b.x"].value = 2.
    before = tuple(item.model_dump(mode="json") for item in (spec, nominal, observed))
    result = evaluate_fault_variants(spec, nominal, observed=observed)
    assert result["nominal_audit_pass"] and result["ok"]
    assert result["matching_variants"] == [] and result["model_miss"] is True
    audit, measured, actual = (tmp_path / name for name in ("audit.yaml", "nominal.yaml", "observed.yaml"))
    for path, value in ((audit, spec), (measured, nominal), (actual, observed)):
        path.write_text(json.dumps(value.model_dump(mode="json")), encoding="utf-8")
    assert main(["hierarchy", "variants", str(audit), str(measured), "--observed", str(actual), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["model_miss"] is True
    healthy = evaluate_fault_variants(spec, nominal, observed=nominal)
    assert healthy["matching_variants"] == [] and healthy["model_miss"] is False
    assert tuple(item.model_dump(mode="json") for item in (spec, nominal, observed)) == before


def test_pairwise_rows_cover_every_fault_pair() -> None:
    spec, nominal = _case([
        _fault("one", "a.x", 2., "thermal"), _fault("two", "a.x", 3., "thermal"),
        _fault("three", "a.x", -2., "thermal"),
        {"id": "rounding", "kind": "benign", "parameters": {"a.scale": 1.}},
    ])
    result = evaluate_fault_variants(spec, nominal)
    rows = result["pairwise"]
    assert len(rows) == 3
    by_pair = {frozenset(row["variants"]): row for row in rows}
    assert set(by_pair) == {frozenset(("one", "two")), frozenset(("one", "three")), frozenset(("two", "three"))}
    assert by_pair[frozenset(("one", "two"))]["separable_by"] is None
    assert by_pair[frozenset(("one", "three"))]["separable_by"] == "signature"
    assert by_pair[frozenset(("two", "three"))]["separable_by"] == "signature"
    assert result["next_signal"] == []
