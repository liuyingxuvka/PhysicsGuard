"""A reading in external_signal is checked against the row's value, with or without raw_value.

The rows are the round-12 shower trial variants used in test_derived_unit_conversions: the tool finds a
number and a unit in external_signal, converts it to the model unit and compares it with the value the AI
gave or the value the tool converted from raw_value and raw_unit.
"""
from __future__ import annotations

import re

import pytest

from conftest import run_cli
from test_derived_unit_conversions import SHOWER, WATER, _ledger, _load, _trial, _write


@pytest.mark.parametrize("signal, value, codes", [
    ("6 kg/min", 0.1, []),
    ("0.1 kg/s", 0.1, []),
    ("6 L/min", 0.1, ["conversion_unchecked"]),
    ("6 litres a minute", 6.0, []),
    # A reading inside a longer label is checked and reported; the whole-reading disagreement stops (below).
    ("pump 6 kg/min", 6.0, ["signal_reading_disagrees"]),
    ("pump 6 kg/min", 0.1, []),
    ("shower flow 6 L/min", 6.0, ["conversion_unchecked"]),
    ("6 L/min (0.1 kg/s)", 0.1, ["conversion_unchecked"]),
])
def test_an_external_signal_that_is_a_reading_is_checked_against_the_value(tmp_path, signal, value, codes) -> None:
    path = _trial(tmp_path, {"heater.m_dot_kg_s": {"value": value, "external_signal": signal,
                                                   "conversion_factor": None, "conversion_note": None}})
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    assert [code for code in ledger["heater.m_dot_kg_s"]["issue_codes"]
            if code in {"conversion_unchecked", "signal_reading_disagrees"}] == codes

@pytest.mark.parametrize("signal, offset, codes", [("15 degC", 273.15, []), ("15 degC", None, []),
                                                   ("inlet 15 degC", 273.15, []),
                                                   ("inlet 15 degC", 273.0, ["signal_reading_disagrees"])])
def test_a_temperature_reading_in_degc_checks_the_recorded_offset(tmp_path, signal, offset, codes) -> None:
    edits = {"heater.T_in_K": {"value": 288.15, "external_signal": signal, "conversion_offset": offset}}
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, edits)))
    assert [code for code in ledger["heater.T_in_K"]["issue_codes"]
            if code in {"conversion_unchecked", "signal_reading_disagrees"}] == codes

def test_a_reading_of_another_quantity_inside_free_text_is_flagged(tmp_path) -> None:
    """The silent case: value 6.0 kg/s, no conversion fields, the reading only inside a longer label."""
    edits = {"heater.m_dot_kg_s": {"external_signal": "shower flow 6 L/min", "conversion_factor": None, "conversion_note": None}}
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, edits)))
    assert "conversion_unchecked" in ledger["heater.m_dot_kg_s"]["issue_codes"]
    assert "6 L/min" in ledger["heater.m_dot_kg_s"]["conversion_check"]
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, edits)))
    mapping = next(line for line in result.stdout.splitlines() if line.startswith("mapping:"))
    assert "heater.m_dot_kg_s conversion_unchecked" in mapping

def test_trial_v0_flags_only_the_rows_the_tool_cannot_check(tmp_path) -> None:
    """v0's temperatures say '15 C', which the tool reads and checks, so only the two flow rows stay flagged."""
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, {})))
    flagged = sorted(name for name, row in ledger.items() if row["issue_codes"])
    assert flagged == ["heater.m_dot_kg_s", "mix.m_dot_2_kg_s"]
    for name in ("heater.T_in_K", "heater.T_out_K", "mix.T_2_K", "mix.T_out_K"):
        assert ledger[name]["conversion_check"].startswith("value agrees with external_signal"), ledger[name]
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, {})))
    assert result.stdout.splitlines()[0].endswith("mapping 8 rows, 2 with issues")

@pytest.mark.parametrize("variable, update", [
    ("heater.m_dot_kg_s", {"value": 6.0, "external_signal": "6 kg/min", "conversion_factor": None, "conversion_note": None}),
    ("heater.T_out_K", {"value": 333.15, "external_signal": "20 degC", "conversion_offset": None}),
    ("heater.T_in_K", {"value": 288.15, "external_signal": "15 degC", "conversion_offset": 273.0}),
], ids=["kg_per_min_as_kg_per_s", "temperature_mismatch", "recorded_offset_wrong"])
def test_a_whole_signal_reading_that_disagrees_stops_the_run(tmp_path, variable, update) -> None:
    path = _trial(tmp_path, {variable: update})
    with pytest.raises(ValueError, match=rf"signal_reading_disagrees:{re.escape(variable)}: external_signal reads"):
        _load(path)
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.returncode == 2 and result.stderr.startswith(f"physicsguard error: signal_reading_disagrees:{variable}")

def test_a_reading_inside_free_text_that_disagrees_is_reported_and_the_audit_runs() -> None:
    """observed_q_kw: the AI wrote 'AI heater power 18.837 kW' and put 18.837 in the W slot."""
    report, ledger = _ledger(SHOWER / "audit.yaml", _load(SHOWER / "observed_q_kw.yaml"))
    row = ledger["heater.Q_dot_W"]
    assert "signal_reading_disagrees" in row["issue_codes"]
    assert "18.837 kW = 18837 W" in row["conversion_check"] and "reported, not enforced" in row["conversion_check"]
    assert report["audit_pass"] is False


# Review round 3: a row with raw_value/raw_unit is checked against the reading its external_signal names on the
# same route as a row without them; both readings are converted to the model unit and compared.

RAW_A = {"heater.m_dot_kg_s": {"raw_value": 6, "raw_unit": "kg/s", "conversion_factor": None, "conversion_note": None},
         "mix.m_dot_2_kg_s": {"raw_value": 9, "raw_unit": "kg/s", "conversion_factor": None}}
RAW_B = {variable: {**row, "raw_unit": "L/s", "conversion_property": "water_density", "value": None}
         for variable, row in RAW_A.items()}
WATER_M3 = {"water_density": {"value": 1000.0, "unit": "kg/m^3"}}


def test_bypass_a_a_raw_reading_of_another_quantity_than_its_signal_is_flagged(tmp_path) -> None:
    """v0 with the AI's factor replaced by raw_value 6 raw_unit kg/s; external_signal still says '6 L/min'."""
    path = _trial(tmp_path, RAW_A)
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    for variable, reading in (("heater.m_dot_kg_s", "6 L/min"), ("mix.m_dot_2_kg_s", "9 L/min")):
        assert "conversion_unchecked" in ledger[variable]["issue_codes"], ledger[variable]
        assert reading in ledger[variable]["conversion_check"] and "raw_unit is kg/s" in ledger[variable]["conversion_check"]
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.stdout.splitlines()[0].endswith("mapping 8 rows, 2 with issues"), result.stdout
    mapping = next(line for line in result.stdout.splitlines() if line.startswith("mapping:"))
    assert "heater.m_dot_kg_s conversion_unchecked" in mapping


def test_bypass_b_the_forgotten_sixty_moved_into_raw_unit_stops_the_run(tmp_path) -> None:
    """raw_value 6 raw_unit L/s through water_density, while external_signal says '6 L/min': 0.1 kg/s, not 6."""
    path = _trial(tmp_path, RAW_B, WATER_M3)
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.m_dot_kg_s: external_signal reads 6 L/min = "
                                         r"0\.1 kg/s .*but raw_value 6 L/s converts to 6 kg/s"):
        _load(path)
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.returncode == 2 and result.stderr.startswith("physicsguard error: signal_reading_disagrees:heater.m_dot_kg_s")


def test_bypass_b_inside_a_longer_label_is_reported_and_the_audit_runs(tmp_path) -> None:
    edits = {variable: {**row, "external_signal": f"shower flow {row['raw_value']} L/min"} for variable, row in RAW_B.items()}
    report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, edits, WATER_M3)))
    row = ledger["heater.m_dot_kg_s"]
    assert "signal_reading_disagrees" in row["issue_codes"] and "reported, not enforced" in row["conversion_check"]
    assert any(warning.startswith("heater.m_dot_kg_s: signal mapping needs review (signal_reading_disagrees)")
               for warning in report["warnings"])


@pytest.mark.parametrize("signal", ["6 L/min", "0.1 kg/s", "given 6 L/min", "pump 360 L/h"])
def test_a_raw_reading_that_agrees_with_its_signal_stays_checked(tmp_path, signal) -> None:
    path = _write(tmp_path, {"heater.m_dot_kg_s": {
        "raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "water_density",
        "external_signal": signal}}, WATER)
    row = _load(path).variables["heater.m_dot_kg_s"]
    assert row._conversion_checked is True and not row._signal_disagrees
    assert row._conversion_check.startswith("converted by the tool: 6 L/min x 0.0166667")
    assert f"agrees with external_signal {' '.join(signal.split()[-2:])}" in row._conversion_check


@pytest.mark.parametrize("raw, signal, accepted", [
    ({"raw_value": 15, "raw_unit": "degC"}, "15 C", True),
    ({"raw_value": 15, "raw_unit": "degC"}, "20 degC", False),
    ({"raw_value": 288.15, "raw_unit": "K"}, "20 degC", False),
    ({"raw_value": 59, "raw_unit": "degF"}, "15 C", True),
])
def test_a_raw_temperature_is_compared_with_its_signal_in_the_model_unit(tmp_path, raw, signal, accepted) -> None:
    path = _write(tmp_path, {"heater.T_in_K": {**raw, "unit": "K", "external_signal": signal}})
    if accepted:
        assert _load(path).variables["heater.T_in_K"]._conversion_checked is True
        return
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.T_in_K: external_signal reads"):
        _load(path)


def test_a_transducer_reading_is_compared_with_its_signal_before_the_calibration(tmp_path) -> None:
    row = {"raw_value": 7.5, "raw_unit": "V", "conversion_factor": 2511.6, "unit": "W"}
    agreeing = _write(tmp_path, {"heater.Q_dot_W": {**row, "external_signal": "7.5 V"}}, name="agree.yaml")
    loaded = _load(agreeing).variables["heater.Q_dot_W"]
    assert loaded._conversion_checked is False and not loaded._signal_disagrees  # the calibration stays unchecked
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.Q_dot_W"):
        _load(_write(tmp_path, {"heater.Q_dot_W": {**row, "external_signal": "9 V"}}, name="whole.yaml"))
    label = _load(_write(tmp_path, {"heater.Q_dot_W": {**row, "external_signal": "power transducer 9 V"}}, name="label.yaml"))
    assert label.variables["heater.Q_dot_W"]._signal_disagrees is True


def test_a_series_point_with_a_raw_reading_is_checked_against_its_signal_too() -> None:
    from physicsguard.io.observation_loader import observed_series_from_mapping

    point = {"heater.m_dot_kg_s": {"raw_value": 6, "raw_unit": "L/s", "unit": "kg/s",
                                   "conversion_property": "water_density", "external_signal": "6 L/min"}}
    series = {"series_id": "trial", "time_unit": "s", "properties": WATER_M3,
              "points": [{"point_id": "p0", "timestamp": 0.0, "variables": point}]}
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.m_dot_kg_s"):
        observed_series_from_mapping(series)
