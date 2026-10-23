from __future__ import annotations

import json
from pathlib import Path
import shutil

import yaml
import pytest

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.schema.model_dataset_validation import ModelDatasetValidationReportSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def _copy_pump(tmp_path: Path) -> Path:
    target = tmp_path / "pump_loop"
    shutil.copytree(PUMP, target)
    return target


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _clean_plan(pump: Path) -> Path:
    return pump / "validation" / "clean_validation_plan.yaml"


def test_passing_depth_preserves_exact_pointwise_scope() -> None:
    report = validate_model_dataset(_clean_plan(PUMP))
    receipt = report.depth

    assert report.ok
    assert receipt["artifact_kind"] == "physicsguard_validation_depth"
    assert receipt["status"] == "pass"
    assert receipt["dataset"]["status"] == "current"
    assert {item["identity_id"] for item in receipt["dataset"]["files"]} == {
        "clean_csv",
        "clean_observed_series",
    }
    assert receipt["mapping"]["status"] == "pass"
    assert receipt["time"]["declared_scope"] == "scenario_set"
    assert receipt["time"]["observed_scope"] == "scenario_set"
    assert receipt["time"]["point_count"] == 3
    assert receipt["scenarios"]["perturbation_count"] == 1
    assert receipt["split"]["status"] == "not_applicable"
    assert len(receipt["residual_series"]["points"]) == 3
    assert receipt["residual_series"]["aggregate"]["evaluated_point_count"] == 3
    assert receipt["envelopes"]["aggregate"]["violation_count"] == 0
    assert "commercial" in receipt["unsafe_claim_boundary"]
    assert ModelDatasetValidationReportSpec.model_validate(report.to_dict()).status == "pass"


@pytest.mark.parametrize("drop_temperatures", [False, True])
def test_series_required_variables_are_checked_after_native_derivation(drop_temperatures) -> None:
    from physicsguard.core.validation_depth import _residual_series_receipt
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values
    from physicsguard.schema.validation_depth import ObservedSeriesSpec

    example = ROOT / "examples/hierarchical/heated_tank"
    spec = load_hierarchical_audit_spec(example / "first_step_level0.yaml")
    blocks = [block.model_copy(update={"required_variables": ["heat.Q_out_W"]}) if block.id == "thermal" else block
              for block in spec.hierarchy.blocks]
    spec = spec.model_copy(update={"hierarchy": spec.hierarchy.model_copy(update={"blocks": blocks})})
    variables = load_observed_values(example / "first_step_measured_k30.yaml").model_dump(mode="json")["variables"]
    if drop_temperatures:
        del variables["heat.T_previous_K"]
        del variables["heat.T_current_K"]
    series = ObservedSeriesSpec.model_validate({"series_id": "measured", "points": [
        {"point_id": "p30", "timestamp": 300., "variables": variables},
    ]})
    before = series.model_dump(mode="json")
    findings = []
    receipt, _ = _residual_series_receipt(spec, series, findings)
    assert series.model_dump(mode="json") == before
    if drop_temperatures:
        assert receipt["status"] == "blocked"
        assert receipt["aggregate"]["missing_point_count"] == 1
        assert any(item["type"] == "residual_series_required_values_missing" for item in findings)
    else:
        assert receipt["status"] == "pass"
        assert receipt["aggregate"]["evaluated_point_count"] == 1
        assert "heat.Q_out_W" in receipt["points"][0]["derived_variables"]
        assert receipt["points"][0]["checked_residuals"]


def test_uncertain_required_mapping_blocks_broad_validation(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    edges_path = pump / "contracts" / "clean_contract.yaml"
    edges = _load(edges_path)
    edge = edges["fields"]["flow_readback_kg_s"]
    edge.pop("evidence")
    edge["confidence"] = 0.4
    edge["review_required"] = True
    _write(edges_path, edges)
    plan_path = _clean_plan(pump)

    report = validate_model_dataset(plan_path)
    mapping = report.depth["mapping"]

    assert report.status == "fail"
    assert mapping["status"] == "blocked"
    assert "pump_signal_map.y" in mapping["unresolved_targets"]
    signal = next(item for item in mapping["signals"] if item["target"] == "pump_signal_map.y")
    assert "unit_evidence_missing" in signal["issue_codes"]
    assert "confidence_below_threshold" in signal["issue_codes"]
    assert "human_review_required" in signal["issue_codes"]
    assert any(item["type"] == "mapping_required_signal_uncertain" for item in report.findings)


def test_single_point_cannot_claim_time_window(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"] = series["points"][:1]
    _write(series_path, series)
    plan_path = _clean_plan(pump)
    plan = _load(plan_path)
    plan["depth"]["time_scope"] = {
        "claim_scope": "time_window",
        "start_time": 0.0,
        "end_time": 0.0,
        "time_unit": "s",
        "expected_point_count": 1,
    }
    plan["depth"]["scenarios"] = plan["depth"]["scenarios"][:1]
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)

    assert report.status == "fail"
    assert report.depth["time"]["observed_scope"] == "snapshot"
    assert report.depth["time"]["snapshot_only"] is True
    assert any(item["type"] == "snapshot_scope_overclaim" for item in report.findings)


def test_identical_content_under_different_holdout_label_is_overlap(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    train = pump / "observed" / "calibration_train.yaml"
    holdout_clone = pump / "observed" / "renamed_holdout.yaml"
    shutil.copyfile(train, holdout_clone)
    plan_path = pump / "validation" / "calibration_validation_plan.yaml"
    plan = _load(plan_path)
    plan["calibration"]["holdout_observed"] = "../observed/renamed_holdout.yaml"
    plan["depth"] = _load(_clean_plan(pump))["depth"]
    plan["depth"]["split"] = {
        "training": [
            {
                "identity_id": "calibration_training",
                "path": "../observed/calibration_train.yaml",
                "case_ids": ["training_case"],
            }
        ],
        "holdout": [
            {
                "identity_id": "renamed_holdout",
                "path": "../observed/renamed_holdout.yaml",
                "case_ids": ["holdout_case"],
            }
        ],
    }
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)
    split = report.depth["split"]

    assert report.status == "fail"
    assert split["status"] == "blocked"
    assert split["overlapping_paths"] == []
    assert split["overlapping_contents"] == ["calibration_training=renamed_holdout"]
    assert any(item["type"] == "calibration_holdout_identity_overlap" for item in report.findings)


def test_short_hard_envelope_violation_cannot_hide_behind_series_aggregate(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"][1]["variables"]["pump_signal_map.y"]["value"] = 301.0
    _write(series_path, series)
    plan_path = _clean_plan(pump)
    plan = _load(plan_path)
    envelope = next(item for item in plan["physical_envelopes"] if item["target"] == "pump_signal_map.y")
    envelope["severity"] = "error"
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)
    receipt = report.depth

    assert report.status == "fail"
    assert receipt["envelopes"]["status"] == "blocked"
    assert receipt["envelopes"]["aggregate"]["hard_violation_count"] == 1
    assert receipt["envelopes"]["violations"][0]["point_id"] == "speed_ramp_t1"
    assert receipt["residual_series"]["audit_pass"] is False
    assert receipt["envelopes"]["violation_intervals"]
    assert any(item["type"] == "physical_envelope_interval_violation" for item in report.findings)


def test_invalid_series_interval_is_preserved_and_blocks_depth(tmp_path: Path) -> None:
    pump = _copy_pump(tmp_path)
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"][1]["valid"] = False
    series["points"][1]["invalid_reason"] = "sensor export gap"
    series["points"][1]["variables"] = {}
    _write(series_path, series)
    plan_path = _clean_plan(pump)
    plan = _load(plan_path)
    _write(plan_path, plan)

    report = validate_model_dataset(plan_path)
    residual = report.depth["residual_series"]

    assert report.status == "fail"
    assert residual["status"] == "blocked"
    assert residual["aggregate"]["invalid_point_count"] == 1
    assert residual["invalid_intervals"][0]["reason"] == "sensor export gap"


def test_same_stat_holdout_rewrite_is_rejected_as_content_overlap(tmp_path: Path) -> None:
    import os

    pump = _copy_pump(tmp_path)
    training = pump / "observed" / "calibration_train.yaml"
    holdout = pump / "observed" / "independent_holdout.yaml"
    content = training.read_bytes()
    distinct = content.replace(b"PhysicsGuard", b"physicsGuard", 1)
    assert distinct != content and len(distinct) == len(content)
    holdout.write_bytes(distinct)
    stat = holdout.stat()
    plan_path = pump / "validation" / "calibration_validation_plan.yaml"
    plan = _load(plan_path)
    plan["calibration"]["holdout_observed"] = "../observed/independent_holdout.yaml"
    plan["depth"] = _load(_clean_plan(pump))["depth"]
    plan["depth"]["split"] = {
        "training": [{"identity_id": "training", "path": "../observed/calibration_train.yaml", "case_ids": ["train"]}],
        "holdout": [{"identity_id": "holdout", "path": "../observed/independent_holdout.yaml", "case_ids": ["future"]}],
    }
    _write(plan_path, plan)
    separate = validate_model_dataset(plan_path)
    assert separate.depth["split"]["status"] == "pass"
    assert separate.depth["split"]["overlapping_contents"] == []
    assert not any(item["type"] == "calibration_holdout_identity_overlap" for item in separate.findings)

    holdout.write_bytes(content)
    os.utime(holdout, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert (holdout.stat().st_size, holdout.stat().st_mtime_ns) == (stat.st_size, stat.st_mtime_ns)
    overlap = validate_model_dataset(plan_path)
    split = overlap.depth["split"]
    assert split["overlapping_paths"] == []
    assert split["overlapping_case_ids"] == []
    assert split["overlapping_contents"] == ["training=holdout"]
    assert any(item["type"] == "calibration_holdout_identity_overlap" for item in overlap.findings)
    assert split["status"] == "blocked"
    assert overlap.depth["status"] == "blocked"
    assert overlap.status == "fail"


def test_report_carries_a_compact_depth_summary() -> None:
    report = validate_model_dataset(_clean_plan(PUMP))
    summary = report.depth_summary
    assert summary["status"] == "pass"
    assert summary["claim_scope"] == "scenario_set"
    assert summary["adequacy"]["status"] == "pass"
    assert len(json.dumps(summary)) < 2000


def test_adequacy_floors_are_warnings_not_failures() -> None:
    report = validate_model_dataset(PUMP / "validation" / "shallow_time_varying_validation_plan.yaml")
    severities = {item["type"]: item["severity"] for item in report.findings}
    adequacy_codes = {
        "critical_parameter_uncovered",
        "subsystem_critical_coverage_missing",
        "time_varying_parameter_model_contribution_missing",
        "time_varying_parameter_time_coverage_insufficient",
    }
    assert report.status == "partial"
    assert {severities[code] for code in adequacy_codes} == {"warning"}
    assert report.depth_summary["adequacy"]["parameters_below_floor"] == ["pump_signal_map.a"]


def test_failures_are_grouped_by_contiguous_points_and_worst_block():
    from physicsguard.core.validation_depth import _failing_intervals, _series_top_blocks
    def point(index, status='fail', block='heater'):
        return dict(point_id=f'p{index}', status=status, top_block=block, top_residual='r:heat',
                    max_abs_normalized_residual=float(index+1), timestamp=index*10., scenario_id='default')
    points=[point(0),point(1),point(2,'pass'),point(3),point(4,block='thermal'),point(5,'missing'),point(6)]
    intervals=_failing_intervals(points)
    assert [(i['start_point'],i['end_point'],i['points'],i['top_block']) for i in intervals] == [
        ('p0','p1',2,'heater'),('p3','p3',1,'heater'),('p4','p4',1,'thermal'),('p6','p6',1,'heater')]
    assert intervals[0]['max_abs']==2 and intervals[0]['_point_ids']==['p0','p1']
    assert _series_top_blocks(points)[0]['block_id']=='heater'
    assert _series_top_blocks(points)[0]['failing_points']==4


def test_omitted_adequacy_uses_manifest_facts_without_an_extra_plan_warning(tmp_path):
    pump=_copy_pump(tmp_path)
    path=_clean_plan(pump)
    plan=_load(path)
    plan['depth'].pop('adequacy')
    _write(path,plan)
    report=validate_model_dataset(path)
    assert report.status=='pass'
    assert report.depth_summary['adequacy']['available_point_count']==3
    assert 'validation_adequacy_plan_missing' not in {f['type'] for f in report.findings}
