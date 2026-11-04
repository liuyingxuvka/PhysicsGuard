"""Readings cannot disappear at labels, adjacent numbers, or an unsupported unit spelling."""
from __future__ import annotations

import pytest

from test_derived_unit_conversions import WATER, _load, _write


@pytest.mark.parametrize("signal", [
    "pump flow 6 L/min", "6 kg/s(6 L/min)", "6 kg/s,6 L/min",
    "6 kg/s;6 L/min", "6 kg/s=6 L/min", "6 L/min,6 kg/s",
])
def test_every_convertible_reading_rejects_disagreement(tmp_path, signal) -> None:
    path = _write(tmp_path, {"pump.flow": {
        "raw_value": 6, "raw_unit": "kg/s", "unit": "kg/s", "external_signal": signal,
    }}, WATER)
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:pump\.flow:.*6 L/min = 0\.1 kg/s"):
        _load(path)


@pytest.mark.parametrize("signal", [
    "6 gpm", "6 GPM", "6 gallons", "6 °X", "6 L min−1", "6 L a fortnight",
    "valve 2 open", "6 kg/s unknown_suffix",
])
def test_a_numeric_unit_candidate_is_never_silently_dropped_or_shortened(tmp_path, signal) -> None:
    path = _write(tmp_path, {"pump.flow": {"value": 6, "unit": "kg/s", "external_signal": signal}}, WATER)
    row = _load(path).variables["pump.flow"]
    assert row._signal_unreadable is True
    assert "signal_reading_unreadable:pump.flow:" in row._conversion_check
    assert "agrees with external_signal" not in row._conversion_check


@pytest.mark.parametrize("signal", ["6 L min-1", "6 L min^-1", "6 dm^3/min", "6 L·min⁻¹"])
def test_exponent_digits_are_not_mistaken_for_new_readings(tmp_path, signal) -> None:
    row = _load(_write(tmp_path, {"pump.flow": {
        "value": 0.1, "unit": "kg/s", "external_signal": signal,
    }}, WATER)).variables["pump.flow"]
    assert row._conversion_checked is True and not row._signal_unreadable


@pytest.mark.parametrize("signal", ["−6 L/min", "−6e0 L/min", "6e−1 L/min"])
def test_unicode_minus_readings_are_checked_instead_of_dropped(tmp_path, signal) -> None:
    path = _write(tmp_path, {"pump.flow": {
        "value": 6, "unit": "kg/s", "external_signal": signal,
    }}, WATER)
    with pytest.raises(ValueError, match="signal_reading_disagrees:pump.flow:"):
        _load(path)


def test_unicode_minus_can_agree_with_a_negative_value(tmp_path) -> None:
    row = _load(_write(tmp_path, {"pump.flow": {
        "value": -0.1, "unit": "kg/s", "external_signal": "−6 L/min",
    }}, WATER)).variables["pump.flow"]
    assert row._conversion_checked is True and not row._signal_unreadable
