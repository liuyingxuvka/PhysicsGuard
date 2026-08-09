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


def test_dcdc_converter_simple_dna_positive() -> None:
    module = _module("DCDCConverterSimpleModule", {"residual_scale_power_W": 100.0})
    records = _residuals(
        module,
        {
            "V_in_V": 400.0,
            "I_in_A": 10.0,
            "P_in_W": 4000.0,
            "V_out_V": 200.0,
            "I_out_A": 18.0,
            "P_out_W": 3600.0,
            "efficiency": 0.9,
        },
    )
    assert [(record.name, record.value) for record in records] == [
        ("m.dcdc_input_power", pytest.approx(0.0)),
        ("m.dcdc_output_power", pytest.approx(0.0)),
        ("m.dcdc_efficiency_power", pytest.approx(0.0)),
    ]
    assert {record.role for record in records} == {"equation"}
    assert all(record.scale == pytest.approx(100.0) for record in records)
    assert {record.diagnostic_key for record in records} == {
        "dcdc_input_power_mismatch",
        "dcdc_output_power_mismatch",
        "dcdc_efficiency_power_mismatch",
    }


def test_dcdc_converter_simple_dna_counterexample() -> None:
    module = _module("DCDCConverterSimpleModule", {"residual_scale_power_W": 100.0})
    records = _residuals(
        module,
        {
            "V_in_V": 400.0,
            "I_in_A": 10.0,
            "P_in_W": 4000.0,
            "V_out_V": 200.0,
            "I_out_A": 18.0,
            "P_out_W": 3500.0,
            "efficiency": 0.9,
        },
    )
    assert [record.value for record in records] == pytest.approx([0.0, -100.0, -100.0])
    with pytest.raises(ValueError, match="residual_scale_power_W"):
        _module("DCDCConverterSimpleModule", {"residual_scale_power_W": 0.0})


def test_inverter_simple_dna_positive() -> None:
    module = _module("InverterSimpleModule", {"residual_scale_power_W": 100.0})
    records = _residuals(
        module,
        {"P_dc_W": 4000.0, "P_ac_W": 3600.0, "efficiency": 0.9},
    )
    assert len(records) == 1
    assert records[0].name == "m.inverter_efficiency_power"
    assert records[0].value == pytest.approx(0.0)
    assert records[0].role == "equation"
    assert records[0].scale == pytest.approx(100.0)
    assert records[0].diagnostic_key == "inverter_efficiency_power_mismatch"


def test_inverter_simple_dna_counterexample() -> None:
    module = _module("InverterSimpleModule", {"residual_scale_power_W": 100.0})
    records = _residuals(
        module,
        {"P_dc_W": 4000.0, "P_ac_W": 3500.0, "efficiency": 0.9},
    )
    assert records[0].value == pytest.approx(-100.0)
    with pytest.raises(ValueError, match="residual_scale_power_W"):
        _module("InverterSimpleModule", {"residual_scale_power_W": 0.0})
