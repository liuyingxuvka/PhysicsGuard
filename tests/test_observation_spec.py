from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.schema.observation_spec import ObservedValuesSpec


def test_valid_observed_values_spec_passes() -> None:
    spec = ObservedValuesSpec.model_validate(
        {
            "observation_name": "obs",
            "variables": {
                "coolant.Q_dot_W": {
                    "value": 4180.0,
                    "unit": "W",
                    "source": "test",
                }
            },
            "metadata": {"case": "clean"},
        }
    )
    assert spec.observation_name == "obs"
    assert spec.variables["coolant.Q_dot_W"].value == 4180.0


def test_malformed_observed_variable_name_fails() -> None:
    with pytest.raises(ValidationError, match="component.variable"):
        ObservedValuesSpec.model_validate(
            {"variables": {"not_qualified": {"value": 1.0}}}
        )


def test_nan_or_inf_observed_value_fails() -> None:
    with pytest.raises(ValidationError, match="finite"):
        ObservedValuesSpec.model_validate(
            {"variables": {"a.x": {"value": float("inf")}}}
        )


def test_empty_observed_variables_fail() -> None:
    with pytest.raises(ValidationError, match="cannot be empty"):
        ObservedValuesSpec.model_validate({"variables": {}})


def test_non_json_metadata_fails() -> None:
    with pytest.raises(ValidationError, match="JSON-serializable"):
        ObservedValuesSpec.model_validate(
            {
                "variables": {"a.x": {"value": 1.0}},
                "metadata": {"bad": object()},
            }
        )


def test_numeric_mapping_confidence_is_rejected_with_the_word_mapping() -> None:
    with pytest.raises(ValidationError, match=r"mapping confidence uses high\|medium\|low\|proposed"):
        ObservedValuesSpec.model_validate({"variables": {"signal.x": {"value": 1., "mapping_confidence": .9}}})


def test_snapshot_accepts_source_model_and_rejects_unknown_keys() -> None:
    header = {"model_name": " model A ", "tool": "exporter", "scenario": "run A"}
    spec = ObservedValuesSpec.model_validate({"variables": {"a.x": {"value": 1.}}, "source_model": header})
    assert spec.source_model.model_dump(exclude_unset=True) == header
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ObservedValuesSpec.model_validate({"variables": {"a.x": {"value": 1.}},
                                           "source_model": {"unknown": "value"}})


def _raw_snapshot(tmp_path, original="observed_ai.yaml"):
    import yaml
    from pathlib import Path
    shower = Path(__file__).resolve().parents[1] / "examples/hierarchical/shower_mix"
    return shower, yaml.safe_load((shower / original).read_text()), tmp_path / "observed.yaml"


def test_raw_value_and_unit_are_converted_at_load(tmp_path) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.core.hierarchy import HierarchicalAuditRunner

    shower, data, path = _raw_snapshot(tmp_path)
    flow = data["variables"]["heater.m_dot_kg_s"]
    flow.pop("value")
    flow.update(raw_value=6, raw_unit="L/min", conversion_factor=0.0166667)
    temperature = data["variables"]["heater.T_in_K"]
    temperature.pop("value")
    temperature.pop("conversion_offset")
    temperature.update(raw_value=15, raw_unit="degC")
    path.write_text(yaml.safe_dump(data))
    observed = load_observed_values(path)
    assert observed.variables["heater.m_dot_kg_s"].value == pytest.approx(0.1, rel=1e-5)
    assert observed.variables["heater.T_in_K"].value == pytest.approx(288.15)
    runner = HierarchicalAuditRunner(load_hierarchical_audit_spec(shower / "audit.yaml"), shower)
    report = runner.to_dict(runner.evaluate_observed(observed))
    ledger = {row["physics_variable"]: row for row in report["signal_mapping_ledger"]}
    assert ledger["heater.m_dot_kg_s"]["raw_conversion"] == "6 L/min x 0.0166667 -> 0.1 kg/s"
    assert ledger["heater.T_in_K"]["raw_conversion"] == "15 degC x 1 + 273.15 -> 288.15 K"
    # The separately documented raw/value tolerance accepts the existing rounded factor.
    flow.update(value=0.1, conversion_factor=0.016667)
    path.write_text(yaml.safe_dump(data))
    assert load_observed_values(path).variables["heater.m_dot_kg_s"].value == pytest.approx(0.100002)


def test_disagreeing_value_and_raw_conversion_is_refused(tmp_path) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values

    _shower, data, path = _raw_snapshot(tmp_path, "observed_unit_err.yaml")
    data["variables"]["heater.m_dot_kg_s"].update(raw_value=6, raw_unit="L/min")
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="observed_value_disagrees_with_conversion:heater.m_dot_kg_s"):
        load_observed_values(path)


def test_table_conversion_contradicting_recorded_factor_is_refused(tmp_path) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values

    _shower, data, path = _raw_snapshot(tmp_path)
    data["variables"]["heater.Q_dot_W"].update(raw_value=18.837, raw_unit="kW", conversion_factor=1.0)
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="observed_value_disagrees_with_conversion:heater.Q_dot_W"):
        load_observed_values(path)


@pytest.mark.parametrize("raw", [
    {"raw_value": 6}, {"raw_unit": "L/min"},
    {"raw_value": 6, "raw_unit": " "},
    {"raw_value": float("inf"), "raw_unit": "L/min"},
])
def test_raw_fields_must_be_paired_nonblank_and_finite(tmp_path, raw) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values

    path = tmp_path / "invalid_raw.yaml"
    path.write_text(yaml.safe_dump({"variables": {"a.x": {"value": 1.0, "unit": "kg/s", **raw}}}))
    with pytest.raises(ValueError, match="invalid ObservedValuesSpec"):
        load_observed_values(path)


@pytest.mark.parametrize("offset", [None, 0.0])
def test_cross_dimension_raw_conversion_requires_recorded_factor(tmp_path, offset) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values

    path = tmp_path / "needs_factor.yaml"
    row = {"raw_value": 6, "raw_unit": "L/min", "unit": "kg/s"}
    if offset is not None:
        row["conversion_offset"] = offset
    path.write_text(yaml.safe_dump({"variables": {"heater.m_dot_kg_s": row}}))
    with pytest.raises(ValueError, match="unit_not_convertible:heater.m_dot_kg_s"):
        load_observed_values(path)


@pytest.mark.parametrize("row, expected", [
    ({"raw_value": 1, "raw_unit": "kW", "unit": "W", "conversion_offset": 0.0}, 1000.0),
    ({"raw_value": 15, "raw_unit": "degC", "unit": "K", "conversion_factor": 1.0}, 288.15),
])
def test_partial_explicit_conversion_uses_known_unit_fields(tmp_path, row, expected) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values

    path = tmp_path / "partial_conversion.yaml"
    path.write_text(yaml.safe_dump({"variables": {"a.x": row}}))
    assert load_observed_values(path).variables["a.x"].value == pytest.approx(expected)


def test_computed_raw_conversion_must_be_finite(tmp_path) -> None:
    import yaml
    from physicsguard.io.observation_loader import load_observed_values

    path = tmp_path / "overflow.yaml"
    row = {"raw_value": 1e308, "raw_unit": "L/min", "unit": "kg/s", "conversion_factor": 1e308}
    path.write_text(yaml.safe_dump({"variables": {"a.x": row}}))
    with pytest.raises(ValueError, match="observed_value_disagrees_with_conversion:a.x.*finite"):
        load_observed_values(path)


def test_unloaded_raw_rows_are_refused_by_direct_and_series_construction() -> None:
    from physicsguard.schema.validation_depth import ObservedSeriesPointSpec

    raw = {"raw_value": 6, "raw_unit": "L/min", "unit": "kg/s", "conversion_factor": 1/60}
    for data, model in [
        ({"variables": {"a.x": raw}}, ObservedValuesSpec),
        ({"point_id": "p1", "variables": {"a.x": raw}}, ObservedSeriesPointSpec),
    ]:
        with pytest.raises(ValidationError, match="raw_snapshot_requires_load"):
            model.model_validate(data)


def test_counterfactual_copy_keeps_the_original_raw_conversion_evidence(tmp_path) -> None:
    import yaml
    from physicsguard.core.diagnosability import _variant_data
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    shower, data, path = _raw_snapshot(tmp_path)
    data["variables"]["mix.T_out_K"].update(raw_value=37.5, raw_unit="degC")
    path.write_text(yaml.safe_dump(data))
    nominal = load_observed_values(path)
    spec = load_hierarchical_audit_spec(shower / "audit.yaml")
    variant = next(item for item in spec.fault_variants if item.id == "mix_arithmetic_mean")
    changed, _values = _variant_data(spec, nominal, [variant], shower)
    assert changed.variables["mix.T_out_K"].value == pytest.approx(315.15)
    runner = HierarchicalAuditRunner(spec, shower)
    report = runner.evaluate_observed(changed)
    row = next(item for item in report.signal_mapping_ledger if item.physics_variable == "mix.T_out_K")
    assert row.raw_conversion == "37.5 degC x 1 + 273.15 -> 310.65 K"
    assert row.to_dict()["raw_conversion"] == row.raw_conversion
    assert row.source == "counterfactual variant measurement change"
    assert nominal.variables["mix.T_out_K"].value == pytest.approx(310.65)
