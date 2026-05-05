from __future__ import annotations

import numpy as np
import pytest

from physicsguard.core.registry import VariableRecord
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.registry import ModuleRegistry, default_module_registry
from physicsguard.schema.system_spec import SystemSpec


def system(data: dict) -> SystemSpec:
    return SystemSpec.model_validate(data)


def one_dummy_system(**parameters) -> SystemSpec:
    params = {
        "target": 5.0,
        "lower_bound": -100.0,
        "upper_bound": 100.0,
        "initial_guess": 0.0,
        "scale": 1.0,
    }
    params.update(parameters)
    return system(
        {
            "system_name": "one",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": params,
                }
            ],
        }
    )


def test_one_dummy_module_residual_works() -> None:
    builder = ResidualBuilder(one_dummy_system())
    records = builder.residual_records(np.array([0.0]))
    assert records[0].name == "a.dummy_target"
    assert records[0].value == -5.0
    assert records[0].role == "equation"


def test_dummy_residual_zero_when_x_equals_target() -> None:
    builder = ResidualBuilder(one_dummy_system())
    records = builder.residual_records(np.array([5.0]))
    assert records[0].normalized_value == 0.0


def test_boundary_residual_works() -> None:
    spec = system(
        {
            "system_name": "boundary",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {
                        "target": 5.0,
                        "lower_bound": -100.0,
                        "upper_bound": 100.0,
                        "initial_guess": 0.0,
                        "scale": 1.0,
                    },
                }
            ],
            "boundaries": [{"variable": "a.x", "value": 3.0}],
        }
    )
    builder = ResidualBuilder(spec)
    records = builder.residual_records(np.array([5.0]))
    boundary = [record for record in records if record.source == "boundary"][0]
    assert boundary.value == 2.0
    assert boundary.role == "boundary"


def test_connection_residual_works() -> None:
    spec = system(
        {
            "system_name": "two",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
                {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
            "connections": [{"from_variable": "a.x", "to_variable": "b.x"}],
        }
    )
    builder = ResidualBuilder(spec)
    records = builder.residual_records(np.array([3.0, 1.0]))
    connection = [record for record in records if record.source == "connection"][0]
    assert connection.value == 2.0
    assert connection.role == "connection"


def test_missing_connection_variable_fails() -> None:
    spec = system(
        {
            "system_name": "bad_connection",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
            "connections": [{"from_variable": "a.x", "to_variable": "b.x"}],
        }
    )
    builder = ResidualBuilder(spec)
    with pytest.raises(KeyError, match="connection"):
        builder.residual_vector(np.array([0.0]))


def test_missing_boundary_variable_fails() -> None:
    spec = system(
        {
            "system_name": "bad_boundary",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
            "boundaries": [{"variable": "b.x", "value": 0.0}],
        }
    )
    builder = ResidualBuilder(spec)
    with pytest.raises(KeyError, match="boundary"):
        builder.residual_vector(np.array([0.0]))


def test_residual_vector_returns_normalized_values() -> None:
    builder = ResidualBuilder(one_dummy_system(target=10.0, scale=2.0))
    vector = builder.residual_vector(np.array([6.0]))
    assert vector.tolist() == [-2.0]


def test_wrong_x_length_fails() -> None:
    builder = ResidualBuilder(one_dummy_system())
    with pytest.raises(ValueError, match="length"):
        builder.residual_records(np.array([1.0, 2.0]))


def test_residual_record_role_validation() -> None:
    with pytest.raises(ValueError, match="residual role"):
        ResidualRecord(
            name="bad",
            value=0.0,
            scale=1.0,
            source="test",
            role="invalid",
        )


def test_post_check_cannot_be_active_in_solver() -> None:
    with pytest.raises(ValueError, match="post_check residuals cannot enter the solver"):
        ResidualRecord(
            name="bad_post_check",
            value=0.0,
            scale=1.0,
            source="test",
            role="post_check",
            active_in_solver=True,
        )


def test_variable_override_by_local_name_works() -> None:
    spec = system(
        {
            "system_name": "override_local",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {"target": 0.0},
                    "variable_overrides": {
                        "x": {
                            "lower_bound": -2.0,
                            "upper_bound": 2.0,
                            "initial_guess": 1.0,
                            "scale": 4.0,
                        }
                    },
                }
            ],
        }
    )
    record = ResidualBuilder(spec).build_registry().get_record("a.x")
    assert record.initial_guess == 1.0
    assert record.scale == 4.0


def test_variable_override_by_fully_qualified_name_works() -> None:
    spec = system(
        {
            "system_name": "override_full",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {"target": 0.0},
                    "variable_overrides": {
                        "a.x": {
                            "lower_bound": -3.0,
                            "upper_bound": 3.0,
                            "initial_guess": 2.0,
                            "scale": 5.0,
                        }
                    },
                }
            ],
        }
    )
    record = ResidualBuilder(spec).build_registry().get_record("a.x")
    assert record.initial_guess == 2.0
    assert record.scale == 5.0


class CustomModule(BaseModule):
    def declare_variables(self) -> list[VariableRecord]:
        return [
            VariableRecord(
                name=f"{self.component_id}.y",
                unit=None,
                lower_bound=-1.0,
                upper_bound=1.0,
                initial_guess=0.0,
                scale=1.0,
                source_component=self.component_id,
                local_name="y",
            )
        ]

    def residuals(self, x, registry):
        return []

    def metadata(self) -> dict:
        return {"module_type": self.module_type}


class DuplicateVariableModule(CustomModule):
    def declare_variables(self) -> list[VariableRecord]:
        name = f"{self.component_id}.y"
        return [
            VariableRecord(
                name=name,
                unit=None,
                lower_bound=-1.0,
                upper_bound=1.0,
                initial_guess=0.0,
                scale=1.0,
                source_component=self.component_id,
                local_name="y",
            ),
            VariableRecord(
                name=name,
                unit=None,
                lower_bound=-1.0,
                upper_bound=1.0,
                initial_guess=0.0,
                scale=1.0,
                source_component=self.component_id,
                local_name="y",
            )
        ]


def test_module_registry_registration_works() -> None:
    registry = ModuleRegistry()
    registry.register("CustomModule", lambda component_id, parameters: CustomModule(component_id, "CustomModule", parameters))
    spec = system(
        {
            "system_name": "custom",
            "components": [
                {"id": "c", "type": "CustomModule", "parameters": {}},
            ],
        }
    )
    builder = ResidualBuilder(spec, module_registry=registry)
    assert builder.build_registry().names() == ["c.y"]


def test_unknown_module_type_fails_clearly() -> None:
    spec = system(
        {
            "system_name": "unknown",
            "components": [
                {"id": "a", "type": "NotRegistered", "parameters": {}},
            ],
        }
    )
    with pytest.raises(ValueError, match="unknown module type"):
        ResidualBuilder(spec).build_modules()


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


def linear_parameters(**overrides) -> dict:
    parameters = {
        "a": 2.0,
        "b": 1.0,
        "x_lower_bound": -10.0,
        "x_upper_bound": 10.0,
        "x_initial_guess": 0.0,
        "x_scale": 1.0,
        "y_lower_bound": -20.0,
        "y_upper_bound": 20.0,
        "y_initial_guess": 0.0,
        "y_scale": 1.0,
        "residual_scale": 1.0,
    }
    parameters.update(overrides)
    return parameters


def test_default_module_registry_includes_generic_modules() -> None:
    spec = system(
        {
            "system_name": "generic_registry",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": linear_parameters(),
                },
                {
                    "id": "sum",
                    "type": "ConservationSumModule",
                    "parameters": {
                        "input_variables": ["rel.y"],
                        "output_variables": [],
                        "target": 1.0,
                    },
                },
                {
                    "id": "range",
                    "type": "RangeCheckModule",
                    "parameters": {"variable": "rel.x", "lower_bound": -1.0, "upper_bound": 1.0},
                },
            ],
        }
    )
    registry = ResidualBuilder(spec).build_registry()
    assert registry.names() == ["rel.x", "rel.y"]


def test_default_module_registry_includes_low_fidelity_physical_modules() -> None:
    registered = default_module_registry().registered_types()
    assert "CoolantHeatBalanceModule" in registered
    assert "IdealGasStateModule" in registered
    assert "ElectrochemicalFaradayRateModule" in registered


def test_linear_relation_module_residual_works() -> None:
    spec = system(
        {
            "system_name": "linear",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": linear_parameters(),
                }
            ],
        }
    )
    builder = ResidualBuilder(spec)
    records = builder.residual_records(np.array([2.0, 5.0]))
    assert records[0].diagnostic_key == "linear_relation_mismatch"
    assert records[0].normalized_value == 0.0
    assert records[0].role == "equation"


def test_conservation_sum_module_references_existing_variables() -> None:
    spec = system(
        {
            "system_name": "conservation",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": linear_parameters(),
                },
                {
                    "id": "sum",
                    "type": "ConservationSumModule",
                    "parameters": {
                        "input_variables": ["rel.y"],
                        "output_variables": ["rel.x"],
                        "target": 3.0,
                        "residual_scale": 1.0,
                    },
                },
            ],
        }
    )
    builder = ResidualBuilder(spec)
    records = builder.residual_records(np.array([2.0, 5.0]))
    conservation = [record for record in records if record.diagnostic_key == "conservation_sum_mismatch"][0]
    assert conservation.normalized_value == 0.0


def test_range_check_module_reports_soft_range_violation() -> None:
    spec = system(
        {
            "system_name": "range_check",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": linear_parameters(),
                },
                {
                    "id": "range",
                    "type": "RangeCheckModule",
                    "parameters": {
                        "variable": "rel.x",
                        "lower_bound": -1.0,
                        "upper_bound": 1.0,
                        "residual_scale": 1.0,
                    },
                },
            ],
        }
    )
    builder = ResidualBuilder(spec)
    records = builder.residual_records(np.array([2.0, 5.0]))
    range_record = [record for record in records if record.diagnostic_key == "range_check_violation"][0]
    assert range_record.normalized_value == 1.0
    assert range_record.role == "post_check"


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


def test_soft_check_residual_can_be_explicitly_enabled_for_solver() -> None:
    spec = system(
        {
            "system_name": "soft_check_vector",
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
                        "role": "soft_check",
                        "include_in_solver": True,
                        "residual_scale": 1.0,
                    },
                },
            ],
        }
    )
    builder = ResidualBuilder(spec)
    assert builder.residual_vector(np.array([2.0, 2.0])).tolist() == [0.0, 1.0]


def test_range_check_rejects_post_check_solver_participation() -> None:
    spec = system(
        {
            "system_name": "bad_post_check",
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
                        "role": "post_check",
                        "include_in_solver": True,
                    },
                },
            ],
        }
    )
    with pytest.raises(ValueError, match="post_check residuals cannot enter the solver"):
        ResidualBuilder(spec).build_modules()
