from __future__ import annotations

import numpy as np
import pytest

from physicsguard.core.registry import VariableRegistry
from physicsguard.modules.registry import default_module_registry


def _module(module_type: str, parameters: dict[str, float]):
    return default_module_registry().create(module_type, "m", parameters)


def _residuals(module, values: dict[str, float]):
    registry = VariableRegistry()
    for variable in module.declare_variables():
        registry.add_variable(variable)
    vector = registry.dict_to_vector({f"{module.component_id}.{name}": value for name, value in values.items()})
    return module.residuals(np.asarray(vector, dtype=float), registry)


def test_brake_simple_dna_positive() -> None:
    module = _module("BrakeSimpleModule", {"residual_scale_W": 100.0})
    records = _residuals(
        module,
        {
            "brake_force_N": 1000.0,
            "vehicle_speed_m_s": 20.0,
            "brake_power_W": 20000.0,
        },
    )
    assert len(records) == 1
    assert records[0].name == "m.brake_power"
    assert records[0].value == pytest.approx(0.0)
    assert records[0].role == "equation"
    assert records[0].scale == pytest.approx(100.0)
    assert records[0].diagnostic_key == "brake_power_mismatch"


def test_brake_simple_dna_counterexample() -> None:
    module = _module("BrakeSimpleModule", {"residual_scale_W": 100.0})
    records = _residuals(
        module,
        {
            "brake_force_N": 1000.0,
            "vehicle_speed_m_s": 20.0,
            "brake_power_W": 19000.0,
        },
    )
    assert records[0].value == pytest.approx(-1000.0)
    with pytest.raises(ValueError, match="residual_scale_W"):
        _module("BrakeSimpleModule", {"residual_scale_W": 0.0})


def test_charger_simple_dna_positive() -> None:
    module = _module("ChargerSimpleModule", {"residual_scale_W": 100.0})
    records = _residuals(
        module,
        {"P_grid_W": 10000.0, "efficiency": 0.9, "P_battery_W": 9000.0},
    )
    assert len(records) == 1
    assert records[0].name == "m.charger_efficiency_power"
    assert records[0].value == pytest.approx(0.0)
    assert records[0].role == "equation"
    assert records[0].scale == pytest.approx(100.0)
    assert records[0].diagnostic_key == "charger_efficiency_power_mismatch"


def test_charger_simple_dna_counterexample() -> None:
    module = _module("ChargerSimpleModule", {"residual_scale_W": 100.0})
    records = _residuals(
        module,
        {"P_grid_W": 10000.0, "efficiency": 0.9, "P_battery_W": 8500.0},
    )
    assert records[0].value == pytest.approx(-500.0)
    with pytest.raises(ValueError, match="residual_scale_W"):
        _module("ChargerSimpleModule", {"residual_scale_W": 0.0})
