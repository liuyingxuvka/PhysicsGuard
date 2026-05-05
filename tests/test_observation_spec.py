from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.schema.observation_spec import ObservedValuesSpec


def test_valid_observed_values_spec_passes() -> None:
    spec = ObservedValuesSpec.model_validate(
        {
            "observation_name": "obs",
            "variables": {
                "coolant.Q_dot_W": {
                    "value": 4180.0,
                    "unit": "W",
                    "source": "test",
                }
            },
            "metadata": {"case": "clean"},
        }
    )
    assert spec.observation_name == "obs"
    assert spec.variables["coolant.Q_dot_W"].value == 4180.0


def test_malformed_observed_variable_name_fails() -> None:
    with pytest.raises(ValidationError, match="component.variable"):
        ObservedValuesSpec.model_validate(
            {"variables": {"not_qualified": {"value": 1.0}}}
        )


def test_nan_or_inf_observed_value_fails() -> None:
    with pytest.raises(ValidationError, match="finite"):
        ObservedValuesSpec.model_validate(
            {"variables": {"a.x": {"value": float("inf")}}}
        )


def test_empty_observed_variables_fail() -> None:
    with pytest.raises(ValidationError, match="cannot be empty"):
        ObservedValuesSpec.model_validate({"variables": {}})


def test_non_json_metadata_fails() -> None:
    with pytest.raises(ValidationError, match="JSON-serializable"):
        ObservedValuesSpec.model_validate(
            {
                "variables": {"a.x": {"value": 1.0}},
                "metadata": {"bad": object()},
            }
        )
