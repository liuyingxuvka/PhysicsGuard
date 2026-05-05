from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.schema.system_spec import SystemSpec


def valid_system_data() -> dict:
    return {
        "system_name": "demo",
        "components": [
            {
                "id": "a",
                "type": "DummyResidualModule",
                "parameters": {"target": 1.0},
            }
        ],
        "connections": [{"from_variable": "a.x", "to_variable": "a.x"}],
        "boundaries": [{"variable": "a.x", "value": 1.0}],
    }


def test_valid_system_spec_passes() -> None:
    spec = SystemSpec.model_validate(valid_system_data())
    assert spec.system_name == "demo"
    assert spec.solver.method == "least_squares"
    assert spec.solver.audit_threshold == 1.0


def test_duplicate_component_id_fails() -> None:
    data = valid_system_data()
    data["components"].append({"id": "a", "type": "DummyResidualModule"})
    with pytest.raises(ValidationError, match="unique"):
        SystemSpec.model_validate(data)


def test_component_id_containing_dot_fails() -> None:
    data = valid_system_data()
    data["components"][0]["id"] = "a.bad"
    with pytest.raises(ValidationError, match="dots"):
        SystemSpec.model_validate(data)


def test_malformed_connection_endpoint_fails() -> None:
    data = valid_system_data()
    data["connections"][0]["from_variable"] = "x"
    with pytest.raises(ValidationError, match="component.variable"):
        SystemSpec.model_validate(data)


def test_malformed_boundary_variable_fails() -> None:
    data = valid_system_data()
    data["boundaries"][0]["variable"] = "x"
    with pytest.raises(ValidationError, match="component.variable"):
        SystemSpec.model_validate(data)


def test_invalid_solver_settings_fail() -> None:
    data = valid_system_data()
    data["solver"] = {"max_iterations": 0, "tolerance": -1.0, "audit_threshold": 0.0}
    with pytest.raises(ValidationError):
        SystemSpec.model_validate(data)


def test_unsupported_method_fails() -> None:
    data = valid_system_data()
    data["solver"] = {"method": "other"}
    with pytest.raises(ValidationError, match="least_squares"):
        SystemSpec.model_validate(data)
