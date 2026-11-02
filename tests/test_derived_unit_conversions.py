"""Cross-quantity conversions are computed by the tool, never taken from a factor the AI wrote.

The rows below are the round-12 trial variants of the shower mix (6 L/min of water read as kg/s):
v0 keeps the AI's own converted value, v1/v2 give raw L/min with the AI's wrong factor 1.0 (it forgot
the /60), v6 gives raw kg/min.
"""
from __future__ import annotations

import math

import pytest
import yaml

from conftest import ROOT, run_cli

SHOWER = ROOT / "examples" / "hierarchical" / "shower_mix"
WATER = {"water_density": {"value": 1.0, "unit": "kg/L", "source": "given: water 1 kg/L"}}


def _write(tmp_path, variables, properties=None, name="observed.yaml"):
    data = {"observation_name": "trial", "variables": variables}
    if properties is not None:
        data["properties"] = properties
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _load(path):
    from physicsguard.io.observation_loader import load_observed_values

    return load_observed_values(path)


def _trial(tmp_path, edits, properties=None):
    """The v0.16.0 trial file observed_unit_err.yaml with per-variable edits (None drops a key)."""
    data = yaml.safe_load((SHOWER / "observed_unit_err.yaml").read_text(encoding="utf-8"))
    for variable, update in edits.items():
        row = data["variables"][variable]
        for key, value in update.items():
            if value is None:
                row.pop(key, None)
            else:
                row[key] = value
    if properties is not None:
        data["properties"] = properties
    path = tmp_path / "trial.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


V1 = {"heater.m_dot_kg_s": {"raw_value": 6, "raw_unit": "L/min", "conversion_factor": 1.0},
      "mix.m_dot_2_kg_s": {"raw_value": 9, "raw_unit": "L/min", "conversion_factor": 1.0}}
V2 = {variable: {**row, "value": None} for variable, row in V1.items()}


def test_mass_flow_per_minute_is_in_the_unit_table(tmp_path) -> None:
    from physicsguard.core.units import unit_conversion

    assert unit_conversion("kg/min", "kg/s") == pytest.approx((1 / 60, 0.0))
    path = _write(tmp_path, {"heater.m_dot_kg_s": {"raw_value": 6, "raw_unit": "kg/min", "unit": "kg/s"}})
    assert _load(path).variables["heater.m_dot_kg_s"].value == pytest.approx(0.1)


def test_volume_flow_becomes_mass_flow_through_a_declared_density(tmp_path) -> None:
    path = _write(tmp_path, {"heater.m_dot_kg_s": {
        "raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "water_density"}}, WATER)
    row = _load(path).variables["heater.m_dot_kg_s"]
    assert row.value == pytest.approx(0.1, rel=1e-12)
    assert row._raw_conversion == "6 L/min x 0.0166667 (water_density 1 kg/L) -> 0.1 kg/s"


def test_mass_flow_becomes_volume_flow_by_dividing_by_the_density(tmp_path) -> None:
    path = _write(tmp_path, {"pump.V_dot_m3_s": {
        "raw_value": 3600, "raw_unit": "kg/h", "unit": "m^3/s", "conversion_property": "water_density"}}, WATER)
    assert _load(path).variables["pump.V_dot_m3_s"].value == pytest.approx(0.001, rel=1e-12)


@pytest.mark.parametrize("factor, accepted", [(0.016667, True), (1.0, False)])
def test_a_recorded_factor_is_checked_against_the_computed_one(tmp_path, factor, accepted) -> None:
    path = _write(tmp_path, {"heater.m_dot_kg_s": {
        "raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "water_density",
        "conversion_factor": factor}}, WATER)
    if accepted:
        # The rounded factor agrees within the raw-value tolerance; the tool's own factor is applied.
        assert _load(path).variables["heater.m_dot_kg_s"].value == pytest.approx(0.1, rel=1e-12)
    else:
        with pytest.raises(ValueError, match=r"observed_value_disagrees_with_conversion:heater\.m_dot_kg_s:.*water_density"):
            _load(path)


@pytest.mark.parametrize("edits", [V1, V2], ids=["v1_wrong_factor_with_value", "v2_wrong_factor_no_value"])
def test_a_cross_quantity_factor_the_ai_wrote_is_not_enough(tmp_path, edits) -> None:
    path = _trial(tmp_path, edits)
    with pytest.raises(ValueError, match=r"unit_not_convertible:heater\.m_dot_kg_s: L/min \(volume_flow\) -> kg/s \(mass_flow\).*conversion_property"):
        _load(path)


def test_trial_v1_and_v2_are_refused_by_the_command(tmp_path) -> None:
    for edits in (V1, V2):
        result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, edits)))
        assert result.returncode == 2, result.stdout
        assert result.stderr.startswith("physicsguard error: unit_not_convertible:heater.m_dot_kg_s"), result.stderr


def test_trial_v1_with_the_density_declared_fails_on_the_wrong_factor(tmp_path) -> None:
    edits = {variable: {**row, "conversion_property": "water_density"} for variable, row in V1.items()}
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, edits, WATER)))
    assert result.returncode == 2
    assert result.stderr.startswith("physicsguard error: observed_value_disagrees_with_conversion:heater.m_dot_kg_s")


def test_trial_v6_raw_mass_per_minute_is_converted(tmp_path) -> None:
    edits = {"heater.m_dot_kg_s": {"raw_value": 6, "raw_unit": "kg/min", "conversion_factor": None, "value": None},
             "mix.m_dot_2_kg_s": {"raw_value": 9, "raw_unit": "kg/min", "conversion_factor": None, "value": None}}
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, edits)))
    assert result.returncode in {0, 1}, result.stderr
    assert result.stdout.startswith("audit shower_mix on ai_answer:")


@pytest.mark.parametrize("raw_unit, unit", [("L/min", "m^3/s"), ("W", "kg/s"), ("degC", "kg/s")])
def test_a_property_that_does_not_link_the_two_units_is_refused(tmp_path, raw_unit, unit) -> None:
    path = _write(tmp_path, {"a.x": {"raw_value": 1, "raw_unit": raw_unit, "unit": unit,
                                     "conversion_property": "water_density"}}, WATER)
    with pytest.raises(ValueError, match=r"unit_not_convertible:a\.x: .*water_density"):
        _load(path)


def test_a_conversion_property_must_be_declared(tmp_path) -> None:
    path = _write(tmp_path, {"heater.m_dot_kg_s": {
        "raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "oil_density"}}, WATER)
    with pytest.raises(ValueError, match="conversion_property oil_density is not declared under properties"):
        _load(path)


@pytest.mark.parametrize("prop", [{"value": 0.0, "unit": "kg/L"}, {"value": -1.0, "unit": "kg/L"},
                                  {"value": math.inf, "unit": "kg/L"}, {"value": 1.0, "unit": " "}])
def test_a_declared_property_needs_a_positive_finite_value_and_a_unit(tmp_path, prop) -> None:
    path = _write(tmp_path, {"a.x": {"value": 1.0, "unit": "kg/s"}}, {"rho": prop})
    with pytest.raises(ValueError, match="invalid ObservedValuesSpec"):
        _load(path)


def test_a_property_in_a_unit_outside_the_table_is_refused(tmp_path) -> None:
    path = _write(tmp_path, {"heater.m_dot_kg_s": {
        "raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "rho"}},
        {"rho": {"value": 1.0, "unit": "lb/gal"}})
    with pytest.raises(ValueError, match=r"unit_not_convertible:heater\.m_dot_kg_s: .*lb/gal"):
        _load(path)


def _ledger(audit, observed):
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec

    runner = HierarchicalAuditRunner(load_hierarchical_audit_spec(audit), audit.parent)
    report = runner.to_dict(runner.evaluate_observed(observed, skip_unobserved=True))
    return report, {row["physics_variable"]: row for row in report["signal_mapping_ledger"]}


def test_trial_v0_conversion_the_ai_did_itself_is_reported_as_unchecked(tmp_path) -> None:
    report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, {})))
    assert "conversion_unchecked" in ledger["heater.m_dot_kg_s"]["issue_codes"]
    assert "conversion_unchecked" in ledger["heater.T_in_K"]["issue_codes"]
    assert "conversion_unchecked" not in ledger["heater.Q_dot_W"]["issue_codes"]
    assert any(warning.startswith("heater.m_dot_kg_s: signal mapping needs review (conversion_unchecked)")
               for warning in report["warnings"])


def test_trial_v0_warning_is_visible_in_the_tree(tmp_path) -> None:
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, {})))
    first, *rest = result.stdout.splitlines()
    assert first.endswith("mapping 8 rows, 6 with issues")
    warnings = next(line for line in rest if line.startswith("warnings:"))
    assert "heater.m_dot_kg_s: signal mapping needs review (conversion_unchecked)" in warnings


def test_tool_checked_conversions_are_not_flagged(tmp_path) -> None:
    path = _write(tmp_path, {
        "heater.m_dot_kg_s": {"raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "water_density",
                              "external_signal": "given 6 L/min"},
        "heater.T_in_K": {"raw_value": 15, "raw_unit": "degC", "unit": "K", "external_signal": "given 15 C"},
        "heater.T_out_K": {"raw_value": 60, "raw_unit": "degC", "unit": "K", "external_signal": "given 60 C"},
        "heater.Q_dot_W": {"value": 18837.0, "unit": "W", "external_signal": "AI heater power"},
    }, WATER)
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    assert all("conversion_unchecked" not in row["issue_codes"] for row in ledger.values())


@pytest.mark.parametrize("record", [{"conversion_factor": 1.0}, {"conversion_offset": 0.0},
                                    {"conversion_factor": 1.0, "conversion_offset": 0.0},
                                    {"conversion_note": "1 kg/L"}])
def test_any_recorded_conversion_without_a_raw_value_is_unchecked(tmp_path, record) -> None:
    """A factor of 1.0 is what the AI wrote for L/min to kg/s when it forgot the /60: it is not an identity."""
    path = _write(tmp_path, {"heater.Q_dot_W": {"value": 18837.0, "unit": "W", "external_signal": "AI heater power", **record}})
    row = _load(path).variables["heater.Q_dot_W"]
    assert row._conversion_checked is False
    assert "without raw_value" in row._conversion_check


# Round-12 trial v1 written in v0's SI-only form: the AI's value 6.0 kg/s with the reading in external_signal.
V1_SI = {"heater.m_dot_kg_s": {"conversion_factor": 1.0, "conversion_note": "1 kg/L"},
         "mix.m_dot_2_kg_s": {"conversion_factor": 1.0}}
V1_SI_BARE = {variable: {"conversion_factor": None, "conversion_note": None} for variable in V1_SI}


@pytest.mark.parametrize("edits", [V1_SI, V1_SI_BARE], ids=["factor_1_recorded", "no_factor"])
def test_trial_v1_in_si_form_is_reported_unchecked(tmp_path, edits) -> None:
    report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, edits)))
    for variable in V1_SI:
        assert "conversion_unchecked" in ledger[variable]["issue_codes"], ledger[variable]
        assert "L/min" in ledger[variable]["conversion_check"]
    result = run_cli("hierarchy", "evaluate", str(SHOWER / "audit.yaml"), str(_trial(tmp_path, edits)))
    warnings = next(line for line in result.stdout.splitlines() if line.startswith("warnings:"))
    assert "heater.m_dot_kg_s: signal mapping needs review (conversion_unchecked)" in warnings
    mapping = next(line for line in result.stdout.splitlines() if line.startswith("mapping:"))
    assert "heater.m_dot_kg_s conversion_unchecked" in mapping


@pytest.mark.parametrize("signal, value, codes", [
    ("6 kg/min", 0.1, []),
    ("6 kg/min", 6.0, ["signal_reading_disagrees"]),
    ("0.1 kg/s", 0.1, []),
    ("6 L/min", 0.1, ["conversion_unchecked"]),
    ("6 litres a minute", 6.0, []),
])
def test_an_external_signal_that_is_a_reading_is_checked_against_the_value(tmp_path, signal, value, codes) -> None:
    path = _trial(tmp_path, {"heater.m_dot_kg_s": {"value": value, "external_signal": signal,
                                                   "conversion_factor": None, "conversion_note": None}})
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(path))
    assert [code for code in ledger["heater.m_dot_kg_s"]["issue_codes"]
            if code in {"conversion_unchecked", "signal_reading_disagrees"}] == codes


@pytest.mark.parametrize("offset, codes", [(273.15, []), (273.0, ["signal_reading_disagrees"]), (None, [])])
def test_a_temperature_reading_in_degc_checks_the_recorded_offset(tmp_path, offset, codes) -> None:
    edits = {"heater.T_in_K": {"value": 288.15, "external_signal": "15 degC", "conversion_offset": offset}}
    _report, ledger = _ledger(SHOWER / "audit.yaml", _load(_trial(tmp_path, edits)))
    assert [code for code in ledger["heater.T_in_K"]["issue_codes"]
            if code in {"conversion_unchecked", "signal_reading_disagrees"}] == codes


@pytest.mark.parametrize("prop, accepted", [({"value": 1.0, "unit": "kg/L"}, True), ({"value": 19.3, "unit": "g/cm^3"}, True),
                                            ({"value": 60.0, "unit": "kg/L"}, False),
                                            ({"value": 60000.0, "unit": "kg/m^3"}, False)])
def test_a_declared_density_denser_than_any_material_is_refused(tmp_path, prop, accepted) -> None:
    path = _write(tmp_path, {"heater.m_dot_kg_s": {
        "raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_property": "water_density"}},
        {"water_density": prop})
    if accepted:
        assert _load(path).variables["heater.m_dot_kg_s"].value > 0
    else:
        with pytest.raises(ValueError, match=r"implausible_property: .*denser than any material"):
            _load(path)


def test_a_factor_for_units_outside_the_table_is_used_but_reported_unchecked(tmp_path) -> None:
    path = _trial(tmp_path, {"heater.Q_dot_W": {"raw_value": 7.5, "raw_unit": "V", "conversion_factor": 2511.6,
                                                "value": None, "external_signal": "power transducer"}})
    observed = _load(path)
    assert observed.variables["heater.Q_dot_W"].value == pytest.approx(18837.0)
    _report, ledger = _ledger(SHOWER / "audit.yaml", observed)
    assert "conversion_unchecked" in ledger["heater.Q_dot_W"]["issue_codes"]


def _contract_with(tmp_path, change):
    from test_test_file_contract_core import TANK, changed_contract

    return changed_contract(tmp_path, change, TANK / "tank_run_contract.yaml")


def _mass_flow_column(data, conversion=None, prop=WATER["water_density"]):
    field = data["fields"]["inflow_Lps"]  # mapped to inflow_mass.V_dot_m3_s, a volume flow
    field["unit"] = "kg/s"
    field["conversion_property"] = "water_density"
    if conversion is not None:
        field["conversion"] = conversion
    data["properties"] = {"water_density": prop}


def test_a_contract_crosses_quantities_through_a_declared_property(tmp_path) -> None:
    from physicsguard.core.test_file_contract import check_test_file_contract, testfile_snapshot

    path = _contract_with(tmp_path, _mass_flow_column)
    review = check_test_file_contract(path)
    assert review.ok, [finding.type for finding in review.findings]
    snapshot = testfile_snapshot(path, 70)
    inflow = snapshot["variables"]["inflow_mass.V_dot_m3_s"]
    assert (inflow["raw_value"], inflow["raw_unit"], inflow["conversion_property"]) == (1.0, "kg/s", "water_density")
    assert inflow["value"] == pytest.approx(0.001)
    assert snapshot["properties"]["water_density"] == {"value": 1.0, "unit": "kg/L", "source": "given: water 1 kg/L"}
    written = tmp_path / "snapshot.yaml"
    written.write_text(yaml.safe_dump(snapshot, sort_keys=False), encoding="utf-8")
    row = _load(written).variables["inflow_mass.V_dot_m3_s"]
    assert row._raw_conversion == "1 kg/s x 0.001 (water_density 1 kg/L) -> 0.001 m^3/s"


@pytest.mark.parametrize("change, code", [
    (lambda data: _mass_flow_column(data, {"factor": 1.0}), "conversion_disagrees_with_property"),
    (lambda data: _mass_flow_column(data, prop={"value": 1.0, "unit": "kg/s"}), "unit_not_convertible"),
])
def test_a_contract_property_conversion_is_checked(tmp_path, change, code) -> None:
    from physicsguard.core.test_file_contract import check_test_file_contract

    assert code in {finding.type for finding in check_test_file_contract(_contract_with(tmp_path, change)).findings}


def test_a_contract_property_must_be_declared(tmp_path) -> None:
    from physicsguard.core.test_file_contract import check_test_file_contract

    def change(data):
        _mass_flow_column(data)
        del data["properties"]

    with pytest.raises(ValueError, match="conversion_property water_density is not declared under properties"):
        check_test_file_contract(_contract_with(tmp_path, change))


def test_contract_series_keep_the_raw_reading_and_mark_unchecked_conversions(tmp_path) -> None:
    from physicsguard.core.test_file_contract import testfile_series
    from physicsguard.io.observation_loader import observed_series_from_mapping

    def change(data):
        _mass_flow_column(data)
        data["fields"]["T_amb_C"].update(unit="mV", conversion={"factor": 0.1, "offset": 273.15})

    path = _contract_with(tmp_path, change)
    native = testfile_series(path, "70:72")
    assert native["properties"] == {"water_density": WATER["water_density"]}
    point = native["points"][0]["variables"]
    assert point["loss.T_ambient_K"]["raw_unit"] == "mV" and point["inflow_mass.V_dot_m3_s"]["raw_unit"] == "kg/s"
    series = observed_series_from_mapping(native)
    rows = series.points[0].variables
    assert rows["inflow_mass.V_dot_m3_s"].value == pytest.approx(0.001) and rows["inflow_mass.V_dot_m3_s"]._conversion_checked
    assert rows["loss.T_ambient_K"]._conversion_checked is False
    assert rows["through.T_in_K"]._conversion_checked is True


def test_a_contract_cannot_cross_quantities_with_a_bare_factor(tmp_path) -> None:
    from physicsguard.core.test_file_contract import check_test_file_contract
    from test_test_file_contract_core import TANK, changed_contract

    def change(data):
        field = data["fields"]["inflow_Lps"]  # mapped to inflow_mass.V_dot_m3_s, a volume flow
        field["unit"] = "kg/s"
        field["conversion"] = {"factor": 0.001}

    path = changed_contract(tmp_path, change, TANK / "tank_run_contract.yaml")
    findings = {finding.type for finding in check_test_file_contract(path).findings}
    assert "unit_not_convertible" in findings


def test_contract_snapshots_carry_the_raw_reading_so_the_loader_checks_them(tmp_path) -> None:
    from physicsguard.core.test_file_contract import testfile_snapshot
    from test_test_file_contract_core import TANK

    snapshot = testfile_snapshot(TANK / "tank_run_contract.yaml", 70)
    inflow = snapshot["variables"]["inflow_mass.V_dot_m3_s"]
    assert (inflow["raw_value"], inflow["raw_unit"], inflow["unit"]) == (1.0, "L/s", "m^3/s")
    path = tmp_path / "snapshot.yaml"
    path.write_text(yaml.safe_dump(snapshot, sort_keys=False), encoding="utf-8")
    observed = _load(path)
    assert observed.variables["inflow_mass.V_dot_m3_s"]._raw_conversion == "1 L/s x 0.001 -> 0.001 m^3/s"
    _report, ledger = _ledger(TANK / "heated_tank.yaml", observed)
    assert all("conversion_unchecked" not in row["issue_codes"] for row in ledger.values())
