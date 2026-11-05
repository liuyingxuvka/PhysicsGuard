"""Readings cannot disappear at labels, adjacent numbers, or an unsupported unit spelling."""
from __future__ import annotations

import pytest
import yaml

from conftest import run_cli
from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.validation_depth import ObservedSeriesSpec
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


@pytest.mark.parametrize("signal", ["6 L min-1", "6 L min^-1", "6 dm^3/min", "6 L·min⁻¹", "6 L min^-1,0.1 kg/s"])
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


@pytest.mark.parametrize("signal, mistaken_value", [
    ("6,0 L/min", 0), ("6,5 L/min", 5), ("1,000 L/min", 0), ("6, 0 L/min", 0),
    ("1,234.5 L/min", 234.5), ("1.234,5 L/min", 5),
    ("pump flow −6,0e−1 L/min", 0),
])
@pytest.mark.parametrize("series", [False, True], ids=["snapshot", "series"])
def test_comma_numbers_are_refused_without_guessing_a_fragment(signal, mistaken_value, series) -> None:
    variables = {"pump.flow": {"value": mistaken_value, "unit": "L/min", "external_signal": signal}}
    with pytest.raises(ValueError, match="signal_reading_unreadable:pump.flow:") as caught:
        if series:
            ObservedSeriesSpec.model_validate({"series_id": "comma", "points": [{"point_id": "first", "variables": variables}]})
        else:
            ObservedValuesSpec(variables=variables)
    assert signal in str(caught.value)
    assert "commas" in str(caught.value)


@pytest.mark.parametrize("signal", ["6 to 7 L/min", "6-7 L/min", "6–7 L/min", "-6 to -7 L/min"])
def test_numeric_ranges_are_explicitly_refused_instead_of_reading_the_last_number(signal) -> None:
    with pytest.raises(ValueError, match="signal_reading_unreadable:pump.flow:") as caught:
        ObservedValuesSpec(variables={"pump.flow": {"value": 7, "unit": "L/min", "external_signal": signal}})
    assert signal in str(caught.value)
    assert "ranges are not supported" in str(caught.value)
    assert "reads 7 L/min" not in str(caught.value)


@pytest.mark.parametrize("signal", ["6,0 L/min", "6,000 L/min"])
def test_zero_balance_cannot_pass_after_a_comma_reading_loses_its_leading_digits(tmp_path, signal) -> None:
    audit = {"audit_name": "zero_reading", "system": {"system_name": "zero_reading", "components": [
        {"id": name, "type": "MappedSignalModule", "parameters": {"unit": "kg/s"}}
        for name in ("pump", "outlet")
    ] + [{"id": "balance", "type": "MassBalanceRateModule", "parameters": {
        "input_variables": ["pump.value"], "output_variables": ["outlet.value"]}}]},
        "hierarchy": {"blocks": [{"id": "plant", "components": ["pump", "outlet", "balance"]}]}}
    audit_path = tmp_path / "audit.yaml"
    audit_path.write_text(yaml.safe_dump(audit), encoding="utf-8")
    variables = {"pump.value": {"value": 0, "unit": "kg/s", "external_signal": "0 L/min"},
                 "outlet.value": {"value": 0, "unit": "kg/s"}}
    control = run_cli("hierarchy", "evaluate", str(audit_path), str(_write(tmp_path, variables, WATER)))
    assert control.returncode == 0 and "PASS" in control.stdout, control.stdout + control.stderr
    variables["pump.value"]["external_signal"] = signal
    result = run_cli("hierarchy", "evaluate", str(audit_path), str(_write(tmp_path, variables, WATER)))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "signal_reading_unreadable:pump.value:" in result.stderr and signal in result.stderr
    assert "PASS" not in result.stdout
