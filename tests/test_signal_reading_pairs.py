"""A signal's readings are compared with each other even when its model unit needs a missing property."""
from __future__ import annotations

import pytest

from test_derived_unit_conversions import WATER, _load, _write


@pytest.mark.parametrize("raw", [False, True], ids=["model_value", "raw_value"])
@pytest.mark.parametrize("unit,value,signal,properties,outcome", [
    ("kg/s", 6, "6 L/min; 12 L/min", {}, "refused"),
    ("kg/s", 6, "6 LPM; 12 litres a minute", {}, "refused"),
    ("kg/s", 6, "6 L/min; 0.2 L/s", {}, "refused"),
    ("kg/s", 6, "6 L/min; 6 L/min", {}, "unchecked"),
    ("kg/s", 6, "6 L/min; 0.1 L/s", {}, "unchecked"),
    ("kg/s", 6, "15 C; 300 K", {}, "refused"),
    ("kg/s", 6, "15 C; 288.15 K", {}, "unchecked"),
    ("kg/s", 6, "0 C; 273.150001 K", {}, "unchecked"),
    ("kg/s", 6, "273.150001 K; 0 C", {}, "unchecked"),
    ("W", 1000, "6 L/min; 6 kg/s", {}, "unchecked"),
    ("W", 1000, "6 L/min; 6 kg/s", WATER, "refused"),
    ("W", 1000, "6 L/min; 0.1 kg/s", WATER, "unchecked"),
    ("kg/s", 0.1, "6 L/min; 0.1 kg/s", WATER, "checked"),
    ("kg/s", 6, "6 L/min; 6 kg/s", WATER, "refused"),
    ("kg/s", 0.1, "6 L/min; 0.1 L/s", WATER, "checked"),
    ("K", 288.15, "15 C; 288.15 K", {}, "checked"),
    ("K", 300, "15 C; 288.15 K", {}, "refused"),
])
def test_reading_pairs_use_their_own_conversion_and_keep_model_checks(tmp_path, raw, unit, value, signal, properties, outcome):
    row = {"value": value, "unit": unit, "external_signal": signal}
    if raw:
        row.update(raw_value=value, raw_unit=unit)
    path = _write(tmp_path, {"sensor.value": row}, properties)
    if outcome == "refused":
        with pytest.raises(ValueError, match=r"signal_reading_disagrees:sensor\.value:"):
            _load(path)
        return
    loaded = _load(path).variables["sensor.value"]
    assert loaded._conversion_checked is (outcome == "checked")
    if unit == "kg/s" and not properties and signal.startswith("6 L"):
        assert loaded._missing_property == "density"
        assert "needs a density" in loaded._conversion_check


@pytest.mark.parametrize("mass_signal,refused", [("6 kg/s", True), ("0.1 kg/s", False)])
def test_pair_uses_its_declared_density_while_the_model_row_keeps_its_pressure(tmp_path, mass_signal, refused):
    properties = {**WATER, "pressure": {"value": 100000, "unit": "Pa"}}
    path = _write(tmp_path, {"pump.power": {
        "raw_value": 6, "raw_unit": "L/min", "value": 10, "unit": "W", "conversion_property": "pressure",
        "external_signal": f"6 L/min; {mass_signal}",
    }}, properties)
    if refused:
        with pytest.raises(ValueError, match=r"signal_reading_disagrees:pump\.power:.*the readings disagree with each other"):
            _load(path)
        return
    row = _load(path).variables["pump.power"]
    assert row.value == pytest.approx(10) and "pressure 100000 Pa" in row._raw_conversion
    assert row._conversion_checked is False  # converting kg/s to W would need more than the row's one property
