from __future__ import annotations

import json

import pytest

from physicsguard.cli import main
from physicsguard.core.diagnosability import evaluate_fault_variants
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec


def test_next_signal_uses_unmeasured_scaled_separation_and_pairwise_is_native(tmp_path, capsys) -> None:
    # The original export oracle's actual device parameters and physical scale contrast.
    spec = HierarchicalAuditSpec.model_validate({
        "audit_name": "variant-boundaries",
        "system": {"system_name": "variant-boundaries", "components": [
            {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.}},
            {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 0.}},
            {"id": "fine", "type": "DummyResidualModule", "parameters": {"target": 10., "scale": 1.}},
            {"id": "wide", "type": "DummyResidualModule", "parameters": {
                "target": 100., "scale": 1000., "lower_bound": 0., "upper_bound": 10000.}},
        ]},
        "hierarchy": {"blocks": [
            {"id": "thermal", "level": 0, "components": ["a", "fine", "wide"]},
            {"id": "heater", "parent_id": "thermal", "level": 1, "components": ["b"]},
        ]},
        "fault_variants": [
            {"id": "one", "kind": "fault", "changes": [{"variable": "a.x", "offset": 2.}],
             "expect_blocks": ["thermal"], "parameters": {"fine.target": 10., "wide.target": 1000.}},
            {"id": "two", "kind": "fault", "changes": [{"variable": "a.x", "offset": 2.}],
             "expect_blocks": ["thermal"], "parameters": {"fine.target": 20., "wide.target": 2000.}},
        ],
    })
    nominal = ObservedValuesSpec(variables={"a.x": {"value": 0.}, "b.x": {"value": 0.}})
    before = spec.model_dump(mode="json"), nominal.model_dump(mode="json")
    result = evaluate_fault_variants(spec, nominal)
    group, = result["indistinguishable"]
    assert group["variant_ids"] == ["one", "two"] and group["signature"] == {"thermal": "+"}
    assert group["next_signal"] == "fine.x" and group["next_signal"] not in nominal.variables
    assert group["normalized_separation"] == pytest.approx(10.)
    pair, = result["pairwise"]
    assert pair["variants"] == ["one", "two"] and pair["separable_by"] == "fine.x"
    assert pair["normalized_separation"] == pytest.approx(10.)
    ranked = result["next_signal"]
    assert [row["signal"] for row in ranked] == ["fine.x", "wide.x"]
    assert ranked[0]["separates"] == ranked[1]["separates"] == [["one", "two"]]
    assert ranked[0]["normalized_separation"] == pytest.approx(10.)
    assert ranked[1]["normalized_separation"] == pytest.approx(1.)
    audit_path, nominal_path = tmp_path / "audit.yaml", tmp_path / "nominal.yaml"
    audit_path.write_text(json.dumps(spec.model_dump(mode="json")), encoding="utf-8")
    nominal_path.write_text(json.dumps(nominal.model_dump(mode="json")), encoding="utf-8")
    assert main(["hierarchy", "variants", str(audit_path), str(nominal_path), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"]
    assert output["pairwise"] == result["pairwise"] and output["next_signal"] == result["next_signal"]
    assert (spec.model_dump(mode="json"), nominal.model_dump(mode="json")) == before
