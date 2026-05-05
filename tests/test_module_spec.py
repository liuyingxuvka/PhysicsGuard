from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.schema.module_spec import ModuleSpec


def valid_module_data() -> dict:
    return {
        "module_type": "DummyResidualModule",
        "domain": "test",
        "ports": {
            "p": {
                "name": "p",
                "variables": ["x"],
            }
        },
        "parameters": {
            "target": {
                "name": "target",
                "unit": "1",
                "required": True,
            }
        },
        "variables": {
            "x": {
                "name": "x",
                "unit": "1",
                "lower_bound": -1.0,
                "upper_bound": 1.0,
                "initial_guess": 0.0,
                "scale": 1.0,
            }
        },
        "residuals": [
            {
                "name": "target_residual",
                "scale": 1.0,
                "diagnostic_key": "dummy_target_mismatch",
            }
        ],
    }


def test_valid_module_spec_passes() -> None:
    spec = ModuleSpec.model_validate(valid_module_data())
    assert spec.module_type == "DummyResidualModule"


def test_empty_module_type_fails() -> None:
    data = valid_module_data()
    data["module_type"] = ""
    with pytest.raises(ValidationError):
        ModuleSpec.model_validate(data)


def test_empty_domain_fails() -> None:
    data = valid_module_data()
    data["domain"] = ""
    with pytest.raises(ValidationError):
        ModuleSpec.model_validate(data)


def test_port_references_unknown_variable_fails() -> None:
    data = valid_module_data()
    data["ports"]["p"]["variables"] = ["missing"]
    with pytest.raises(ValidationError, match="unknown variable"):
        ModuleSpec.model_validate(data)


def test_invalid_bounds_fail() -> None:
    data = valid_module_data()
    data["variables"]["x"]["lower_bound"] = 2.0
    data["variables"]["x"]["upper_bound"] = 1.0
    with pytest.raises(ValidationError, match="lower_bound"):
        ModuleSpec.model_validate(data)


def test_residual_with_empty_name_fails() -> None:
    data = valid_module_data()
    data["residuals"][0]["name"] = ""
    with pytest.raises(ValidationError):
        ModuleSpec.model_validate(data)


def test_variable_with_no_scale_and_insufficient_bounds_fails() -> None:
    data = valid_module_data()
    data["variables"]["x"].pop("scale")
    data["variables"]["x"].pop("upper_bound")
    with pytest.raises(ValidationError, match="positive scale"):
        ModuleSpec.model_validate(data)
