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
    ("6 litres a minute", 6.0, ["conversion_unchecked"]),  # read as 6 L/min, a volume flow beside a kg/s value
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


def test_bypass_a_without_a_declared_density_is_flagged_and_names_the_missing_property(tmp_path) -> None:
    """v0 with the AI's factor replaced by raw_value 6 raw_unit kg/s; external_signal still says '6 L/min'."""
    path = _trial(tmp_path, RAW_A)
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    for variable, reading in (("heater.m_dot_kg_s", "6 L/min"), ("mix.m_dot_2_kg_s", "9 L/min")):
        row = ledger[variable]
        assert "conversion_unchecked" in row["issue_codes"], row
        assert reading in row["conversion_check"] and "needs a density" in row["conversion_check"], row["conversion_check"]
        assert row["missing_property"] == "density"
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.stdout.splitlines()[0].endswith("mapping 8 rows, 2 with issues"), result.stdout
    mapping = next(line for line in result.stdout.splitlines() if line.startswith("mapping:"))
    assert "heater.m_dot_kg_s conversion_unchecked (needs a density under properties)" in mapping


@pytest.mark.parametrize("density", [WATER["water_density"], WATER_M3["water_density"]], ids=["kg_per_L", "kg_per_m3"])
def test_bypass_a_with_the_density_declared_stops_the_run(tmp_path, density) -> None:
    """The same raw 6 kg/s beside '6 L/min', with water_density in the file: 6 L/min is 0.1 kg/s, not 6."""
    path = _trial(tmp_path, RAW_A, {"water_density": density})
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.m_dot_kg_s: external_signal reads 6 L/min = "
                                         r"0\.1 kg/s through water_density .*but raw_value 6 kg/s converts to 6 kg/s"):
        _load(path)
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.returncode == 2 and result.stderr.startswith("physicsguard error: signal_reading_disagrees:heater.m_dot_kg_s")


@pytest.mark.parametrize("row", [
    {"raw_value": 6, "raw_unit": "kg/s", "unit": "kg/s"},                                         # model unit kg/s
    {"raw_value": 6, "raw_unit": "kg/s", "unit": "m^3/s", "conversion_property": "water_density"},  # model unit m^3/s
    {"value": 6.0, "unit": "kg/s"},                                                               # no raw value
], ids=["model_unit_mass_flow", "model_unit_volume_flow", "value_only"])
def test_a_reading_of_another_quantity_is_compared_through_the_declared_property_on_either_side(tmp_path, row) -> None:
    variable = "pump.V_dot_m3_s" if row["unit"] == "m^3/s" else "heater.m_dot_kg_s"
    path = _write(tmp_path, {variable: {**row, "external_signal": "6 L/min"}}, WATER)
    with pytest.raises(ValueError, match=rf"signal_reading_disagrees:{re.escape(variable)}: external_signal reads 6 L/min"):
        _load(path)


@pytest.mark.parametrize("row", [{"raw_value": 0.1, "raw_unit": "kg/s", "unit": "kg/s"}, {"value": 0.1, "unit": "kg/s"}],
                         ids=["raw", "value_only"])
def test_a_reading_that_agrees_through_the_declared_property_is_checked(tmp_path, row) -> None:
    loaded = _load(_write(tmp_path, {"heater.m_dot_kg_s": {**row, "external_signal": "6 L/min"}}, WATER))
    checked = loaded.variables["heater.m_dot_kg_s"]
    assert checked._conversion_checked is True and not checked._signal_disagrees
    assert "agrees with external_signal 6 L/min through water_density (1 kg/L)" in checked._conversion_check


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


# Review round 4: a reading written with SI exponents, brackets or "a minute" is read whole, so the forgotten "/60"
# cannot hide behind a spelling the unit table does not know.

EXPONENT_SPELLINGS = ["L min^-1", "L min-1", "L·min⁻¹", "dm^3/min", "(L/min)", "[L/min]", "l.min-1", "litres a minute"]


@pytest.mark.parametrize("spelling", EXPONENT_SPELLINGS)
def test_the_unit_table_reads_exponent_bracket_and_word_spellings(spelling) -> None:
    from physicsguard.core.units import known_conversion, unit_quantity

    assert known_conversion(spelling, "L/min") == pytest.approx((1.0, 0.0))
    assert unit_quantity(spelling) == "volume_flow"


@pytest.mark.parametrize("spelling", ["L min", "kg/s m", "L min^-1 pump", "(L/min"])
def test_a_space_joins_units_only_before_an_explicit_power(spelling) -> None:
    """'L min' is not read as L/min (nor as L*min): only a power such as min^-1 makes a space a product."""
    from physicsguard.core.units import read_unit

    assert read_unit(spelling) is None


@pytest.mark.parametrize("spelling", EXPONENT_SPELLINGS)
def test_bypass_b_written_in_exponent_or_bracket_spelling_stops_the_run(tmp_path, spelling) -> None:
    edits = {"heater.m_dot_kg_s": {**RAW_B["heater.m_dot_kg_s"], "external_signal": f"6 {spelling}"}}
    path = _trial(tmp_path, edits, WATER_M3)
    with pytest.raises(ValueError, match=r"signal_reading_disagrees:heater\.m_dot_kg_s: external_signal reads 6 .* = 0\.1 kg/s"):
        _load(path)
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.returncode == 2 and "signal_reading_disagrees:heater.m_dot_kg_s" in result.stderr


# A number followed by a unit is never dropped: a reading the tool cannot compare is marked with why, and a unit it
# cannot read is flagged signal_reading_unreadable. The other flow row is given a plain label so only this row counts.

MIX_LABEL = {"mix.m_dot_2_kg_s": {"external_signal": "cold flow", "conversion_factor": None}}


def _mapping_line(path) -> tuple[str, str]:
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(path))
    assert result.returncode in (0, 1), result.stderr  # the audit's own verdict; a refusal would be 2
    lines = result.stdout.splitlines()
    return lines[0], next((line for line in lines if line.startswith("mapping:")), "")


@pytest.mark.parametrize("signal, fragment", [
    ("6 gallons/min", "6 gallons/min"), ("6 L fortnight^-1", "6 L fortnight^-1"), ("pump 6 lit/min", "6 lit/min"),
])
def test_a_number_followed_by_a_unit_the_tool_cannot_read_is_flagged(tmp_path, signal, fragment) -> None:
    edits = {**MIX_LABEL, "heater.m_dot_kg_s": {**RAW_B["heater.m_dot_kg_s"], "external_signal": signal}}
    path = _trial(tmp_path, edits, WATER_M3)
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    row = ledger["heater.m_dot_kg_s"]
    assert "signal_reading_unreadable" in row["issue_codes"], row
    assert f'signal_reading_unreadable:heater.m_dot_kg_s: "{fragment}"' in row["conversion_check"]
    head, mapping = _mapping_line(path)
    assert head.endswith("mapping 8 rows, 1 with issues") and "heater.m_dot_kg_s signal_reading_unreadable" in mapping


@pytest.mark.parametrize("signal", ["6 L", "inlet 3 m upstream"])
def test_a_reading_no_declared_property_relates_to_the_model_unit_is_reported(tmp_path, signal) -> None:
    """A volume (or a length) beside a mass flow: neither the table nor one property turns it into kg/s."""
    edits = {**MIX_LABEL, "heater.m_dot_kg_s": {"external_signal": signal, "conversion_factor": None, "conversion_note": None,
                                                 "value": 0.1}}
    path = _trial(tmp_path, edits, WATER)
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    row = ledger["heater.m_dot_kg_s"]
    assert list(row["issue_codes"]) == ["conversion_unchecked"], row
    assert "neither the unit table nor one declared property turns it into kg/s" in row["conversion_check"]
    head, _mapping = _mapping_line(path)
    assert head.endswith("mapping 8 rows, 1 with issues")


@pytest.mark.parametrize("signal", ["valve 2 open", "T_tank_C@70", "pump 2 at full speed"])
def test_a_number_without_a_unit_is_not_a_reading(tmp_path, signal) -> None:
    edits = {**MIX_LABEL, "heater.m_dot_kg_s": {"external_signal": signal, "conversion_factor": None, "conversion_note": None}}
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, edits)))
    assert list(ledger["heater.m_dot_kg_s"]["issue_codes"]) == []
