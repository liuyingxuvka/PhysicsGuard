from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.schema.assumption_spec import AssumptionDeckSpec, AssumptionSpec
from physicsguard.schema.system_spec import SystemSpec


def valid_assumption_data() -> dict:
    return {
        "id": "assume_temperature",
        "target_type": "variable",
        "target": "coolant.T_in_K",
        "value": 300.0,
        "unit": "K",
        "reason": "Signal is missing.",
        "source": "missing_signal",
        "impact": "high",
    }


def test_valid_assumption_passes_and_default_penalty_applies() -> None:
    assumption = AssumptionSpec.model_validate(valid_assumption_data())
    assert assumption.id == "assume_temperature"
    assert assumption.effective_confidence_penalty == pytest.approx(0.25)


def test_low_and_medium_default_penalties() -> None:
    low = AssumptionSpec.model_validate({**valid_assumption_data(), "id": "low", "impact": "low"})
    medium = AssumptionSpec.model_validate({**valid_assumption_data(), "id": "medium", "impact": "medium"})
    assert low.effective_confidence_penalty == pytest.approx(0.02)
    assert medium.effective_confidence_penalty == pytest.approx(0.10)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("id", "", "assumption id"),
        ("target_type", "bad", "target_type"),
        ("status", "bad", "status"),
        ("impact", "severe", "impact"),
        ("reason", "", "assumption reason"),
        ("confidence_penalty", -0.1, "confidence_penalty"),
    ],
)
def test_invalid_assumption_fields_fail(field: str, value, match: str) -> None:
    data = valid_assumption_data()
    data[field] = value
    with pytest.raises(ValidationError, match=match):
        AssumptionSpec.model_validate(data)


def test_variable_and_parameter_targets_must_be_qualified() -> None:
    data = valid_assumption_data()
    data["target"] = "temperature"
    with pytest.raises(ValidationError, match="component.name"):
        AssumptionSpec.model_validate(data)


def test_context_target_may_be_unqualified() -> None:
    assumption = AssumptionSpec.model_validate(
        {
            "id": "context",
            "target_type": "context",
            "target": "ambient lab condition",
            "value": "nominal",
            "reason": "Documented test context.",
        }
    )
    assert assumption.target == "ambient lab condition"


def test_duplicate_assumption_ids_fail_in_deck() -> None:
    data = valid_assumption_data()
    with pytest.raises(ValidationError, match="unique"):
        AssumptionDeckSpec.model_validate(
            {"assumptions": [data, {**data, "target": "coolant.T_out_K"}]}
        )


def test_duplicate_assumption_ids_fail_in_system_spec() -> None:
    data = valid_assumption_data()
    with pytest.raises(ValidationError, match="unique"):
        SystemSpec.model_validate(
            {
                "system_name": "duplicates",
                "components": [
                    {
                        "id": "coolant",
                        "type": "CoolantHeatBalanceModule",
                        "parameters": {},
                    }
                ],
                "assumptions": [data, {**data, "target": "coolant.T_out_K"}],
            }
        )
