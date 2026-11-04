"""Independent model dataset validation domain facts and production contracts."""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Iterable

@dataclass(frozen=True)
class ValidationInput:
    case_id: str
    contracts_passed: bool
    direct_validation_ran: bool
    calibration_enabled: bool
    calibration_parameters_bounded: bool
    observed_values_mutated: bool
    optimization_success: bool
    holdout_passed: bool
    confidence_feedback_recorded: bool
    dataset_identity_current: bool = True
    mapping_review_current: bool = True
    claim_scope_honest: bool = True
    split_disjoint: bool = True
    residual_series_evaluated: bool = True
    envelope_intervals_preserved: bool = True
    coverage_universe_complete: bool = True
    temporal_adequacy_passed: bool = True
    critical_family_coverage_passed: bool = True
    parameter_temporal_adequacy_passed: bool = True
    parameter_universe_complete: bool = True
    per_parameter_denominator_current: bool = True
    manifest_point_denominator_reconciled: bool = True
    parameter_strata_adequate: bool = True
    dynamic_coverage_floor_passed: bool = True
    representative_parameter_evidence_passed: bool = True
    parameter_model_contribution_passed: bool = True
    parameter_contribution_mode: str = 'sensitive'
    non_sensitive_disposition_bounded: bool = True
    static_parameter_binding_passed: bool = True
    prediction_requested: bool = False
    stateful_dynamic: bool = False
    predictive_rollout_passed: bool = False
    missing_input_count: int = 0
    missing_input_finding_count: int = 0
    dependent_checks_not_run: bool = True

@dataclass(frozen=True)
class State:
    input_failure_reports: tuple[tuple[str, int, int, bool], ...] = ()
    contracts_ready: tuple[str, ...] = ()
    depth_inputs_ready: tuple[str, ...] = ()
    direct_validation_ran: tuple[str, ...] = ()
    calibration_ran: tuple[str, ...] = ()
    holdout_passed: tuple[str, ...] = ()
    confidence_feedback_recorded: tuple[str, ...] = ()
    validation_passed: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()

def no_pass_without_contracts(state: State, trace) -> bool:
    del trace
    missing = set(state.validation_passed) - set(state.contracts_ready)
    if missing:
        return False
    return True

def no_pass_without_direct_validation(state: State, trace) -> bool:
    del trace
    missing = set(state.validation_passed) - set(state.direct_validation_ran)
    if missing:
        return False
    return True

def no_pass_without_depth_inputs(state: State, trace) -> bool:
    del trace
    missing = set(state.validation_passed) - set(state.depth_inputs_ready)
    if missing:
        return False
    return True

def no_pass_without_holdout_and_feedback(state: State, trace) -> bool:
    del trace
    ready = set(state.holdout_passed) & set(state.confidence_feedback_recorded)
    missing = set(state.validation_passed) - ready
    if missing:
        return False
    return True

def one_finding_per_missing_input(state: State, trace) -> bool:
    del trace
    for case, unavailable, reported, not_run in state.input_failure_reports:
        if reported != unavailable or not not_run:
            return False
    return True
EXTERNAL_INPUTS = (ValidationInput('missing_declared_series', True, True, False, True, False, False, True, True, missing_input_count=1, missing_input_finding_count=1), ValidationInput('clean_no_calibration', True, True, False, True, False, False, True, True), ValidationInput('calibrated_pass', True, True, True, True, False, True, True, True), ValidationInput('optimizer_only', True, True, True, True, False, True, False, True), ValidationInput('missing_contract', False, True, False, True, False, False, True, True), ValidationInput('mutates_observed', True, True, True, True, True, True, True, True), ValidationInput('unbounded_calibration', True, True, True, False, False, True, True, True))
DEPTH_EXTERNAL_INPUTS = (ValidationInput('missing_dataset_file', True, True, False, True, False, False, True, True, dataset_identity_current=False), ValidationInput('uncertain_mapping', True, True, False, True, False, False, True, True, mapping_review_current=False), ValidationInput('snapshot_overclaim', True, True, False, True, False, False, True, True, claim_scope_honest=False), ValidationInput('split_overlap', True, True, True, True, False, True, True, True, split_disjoint=False), ValidationInput('series_missing', True, True, False, True, False, False, True, True, residual_series_evaluated=False), ValidationInput('envelope_intervals_missing', True, True, False, True, False, False, True, True, envelope_intervals_preserved=False), ValidationInput('shallow_point_universe', True, True, False, True, False, False, True, True, coverage_universe_complete=False), ValidationInput('endpoint_or_duplicate_time', True, True, False, True, False, False, True, True, temporal_adequacy_passed=False), ValidationInput('shallow_signal_family', True, True, False, True, False, False, True, True, critical_family_coverage_passed=False), ValidationInput('one_point_time_varying_parameter', True, True, False, True, False, False, True, True, parameter_temporal_adequacy_passed=False), ValidationInput('ten_thousand_parameters_two_bound', True, True, False, True, False, False, True, True, parameter_universe_complete=False), ValidationInput('parameter_denominator_missing', True, True, False, True, False, False, True, True, per_parameter_denominator_current=False), ValidationInput('manifest_point_count_mismatch', True, True, False, True, False, False, True, True, manifest_point_denominator_reconciled=False), ValidationInput('parameter_endpoints_or_same_stage', True, True, False, True, False, False, True, True, parameter_strata_adequate=False), ValidationInput('three_of_thousand', True, True, False, True, False, False, True, True, dynamic_coverage_floor_passed=False), ValidationInput('one_shallow_parameter_among_deep', True, True, False, True, False, False, True, True, parameter_temporal_adequacy_passed=False), ValidationInput('representative_parameter_without_direction_envelope', True, True, False, True, False, False, True, True, representative_parameter_evidence_passed=False), ValidationInput('disconnected_time_varying_parameter', True, True, False, True, False, False, True, True, parameter_model_contribution_passed=False), ValidationInput('effectless_sensitive_parameter', True, True, False, True, False, False, True, True, parameter_model_contribution_passed=False), ValidationInput('unbounded_non_sensitive_disposition', True, True, False, True, False, False, True, True, parameter_contribution_mode='verified_non_sensitive', non_sensitive_disposition_bounded=False), ValidationInput('verified_non_sensitive_parameter', True, True, False, True, False, False, True, True, parameter_contribution_mode='verified_non_sensitive', non_sensitive_disposition_bounded=True), ValidationInput('static_parameter_without_binding', True, True, False, True, False, False, True, True, static_parameter_binding_passed=False), ValidationInput('representative_32_of_1000', True, True, False, True, False, False, True, True), ValidationInput('pointwise_prediction', True, True, False, True, False, False, True, True, prediction_requested=True), ValidationInput('stateful_rollout_failed', True, True, False, True, False, False, True, True, prediction_requested=True, stateful_dynamic=True, predictive_rollout_passed=False), ValidationInput('stateful_rollout_pass', True, True, False, True, False, False, True, True, prediction_requested=True, stateful_dynamic=True, predictive_rollout_passed=True))
from pathlib import Path
import shutil
import sys
import tempfile
import yaml
ROOT = Path(__file__).resolve().parents[2]
PUMP = ROOT / 'examples' / 'testfile_contracts' / 'pump_loop'

def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')

def _edit_plan(pump: Path, name: str, change) -> Path:
    path = pump / 'validation' / name
    data = _load(path)
    change(pump, data)
    _write(path, data)
    return path

def _rollout(semantics: str):

    def change(pump: Path, plan: dict) -> None:

        def ref(identity_id: str, relative: str, cases=()):
            return {'identity_id': identity_id, 'path': f'../{relative}', 'case_ids': list(cases)}
        plan['depth']['model_semantics'] = semantics
        plan['depth']['predictive_rollout'] = {'rollout_id': 'conformance_rollout', 'producer_id': 'conformance-producer', 'model_identity': ref('pump_model', 'model/pump_loop_hierarchy.yaml'), 'training': [ref('training_series', 'observed/clean_observed_series.yaml', ['baseline_case', 'speed_ramp_case_01', 'speed_ramp_case_02'])], 'prediction_series': ref('prediction', 'observed/predicted_future_series.yaml'), 'future_holdout_series': ref('future_holdout', 'observed/future_holdout_series.yaml', ['future_case_1', 'future_case_2', 'future_case_3']), 'training_end_time': 0.2, 'initial_state': {'pump_signal_map.x': 11.0, 'pump_signal_map.y': 22.0}, 'step_size': 1.0, 'step_unit': 's', 'horizon_steps': 3, 'target_signals': ['pump_signal_map.x', 'pump_signal_map.y'], 'signal_scales': {'pump_signal_map.x': 1.0, 'pump_signal_map.y': 2.0}, 'threshold_source': 'conformance thresholds', 'thresholds': {'maximum_worst_step_normalized_error': 0.0, 'maximum_accumulated_normalized_error': 0.0, 'maximum_absolute_lag_steps': 0, 'maximum_phase_error': 0.0, 'maximum_drift': 0.0, 'maximum_error_growth': 0.0}}
    return change

def _uncertain_mapping(pump: Path, plan: dict) -> None:
    edges_path = pump / 'contracts' / 'clean_contract.yaml'
    edges = _load(edges_path)
    edge = edges['fields']['flow_readback_kg_s']
    edge['confidence'] = 'low'
    _write(edges_path, edges)

def _snapshot_overclaim(pump: Path, plan: dict) -> None:
    series_path = pump / 'observed' / 'clean_observed_series.yaml'
    series = _load(series_path)
    series['points'] = series['points'][:1]
    _write(series_path, series)
    plan['depth']['time_scope'] = {'claim_scope': 'time_window', 'start_time': 0.0, 'end_time': 0.0, 'time_unit': 's', 'expected_point_count': 1}
    plan['depth']['scenarios'] = plan['depth']['scenarios'][:1]

def _split_overlap(pump: Path, plan: dict) -> None:
    shutil.copyfile(pump / 'observed' / 'calibration_train.yaml', pump / 'observed' / 'renamed_holdout.yaml')
    plan['calibration']['holdout_observed'] = '../observed/renamed_holdout.yaml'
    plan['depth'] = _load(pump / 'validation' / 'clean_validation_plan.yaml')['depth']
    plan['depth']['split'] = {'training': [{'identity_id': 'train', 'path': '../observed/calibration_train.yaml', 'case_ids': ['training_case']}], 'holdout': [{'identity_id': 'holdout', 'path': '../observed/renamed_holdout.yaml', 'case_ids': ['holdout_case']}]}

def _invalid_series_point(pump: Path, plan: dict) -> None:
    series_path = pump / 'observed' / 'clean_observed_series.yaml'
    series = _load(series_path)
    series['points'][1].update({'valid': False, 'invalid_reason': 'sensor export gap', 'variables': {}})
    _write(series_path, series)

def _failing_holdout(pump: Path, plan: dict) -> None:
    holdout_path = pump / 'observed' / 'calibration_holdout.yaml'
    holdout = _load(holdout_path)
    for name, item in holdout['variables'].items():
        if name.endswith('.y'):
            item['value'] = float(item['value']) * 3.0
    _write(holdout_path, holdout)
    plan['observed_file'] = '../observed/clean_observed.yaml'
REAL_CASES = {'missing_declared_series': ('clean_validation_plan.yaml', lambda pump, plan: plan['depth']['observed_series'].update(path='../observed/absent_series.yaml')), 'clean_no_calibration': ('clean_validation_plan.yaml', lambda pump, plan: None), 'missing_contract': ('clean_validation_plan.yaml', lambda pump, plan: plan['contracts'][0].update(contract='../contracts/unclassified_contract.yaml')), 'calibrated_pass': ('calibration_validation_plan.yaml', lambda pump, plan: plan.update(observed_file='../observed/clean_observed.yaml')), 'optimizer_only': ('calibration_validation_plan.yaml', _failing_holdout), 'unbounded_calibration': ('calibration_validation_plan.yaml', lambda pump, plan: plan['calibration']['parameters'][0].pop('upper')), 'missing_dataset_file': ('clean_validation_plan.yaml', lambda pump, plan: plan['depth']['dataset']['files'][0].update(path='../data/missing.csv')), 'uncertain_mapping': ('clean_validation_plan.yaml', _uncertain_mapping), 'snapshot_overclaim': ('clean_validation_plan.yaml', _snapshot_overclaim), 'split_overlap': ('calibration_validation_plan.yaml', _split_overlap), 'series_missing': ('clean_validation_plan.yaml', _invalid_series_point), 'one_point_time_varying_parameter': ('shallow_time_varying_validation_plan.yaml', lambda pump, plan: None), 'pointwise_prediction': ('clean_validation_plan.yaml', _rollout('pointwise')), 'stateful_rollout_pass': ('clean_validation_plan.yaml', _rollout('stateful_dynamic'))}
RULE_NAMES = ('one_finding_per_missing_input', 'no_pass_without_contracts', 'no_pass_without_direct_validation', 'no_pass_without_depth_inputs', 'no_pass_without_holdout_and_feedback')
RULES = (one_finding_per_missing_input, no_pass_without_contracts, no_pass_without_direct_validation, no_pass_without_depth_inputs, no_pass_without_holdout_and_feedback)


def assert_native_contract():
    import pytest
    from .contract_cases import expected
    from physicsguard.core.model_dataset_validation import validate_model_dataset
    inputs={case.case_id:case for case in (*EXTERNAL_INPUTS,*DEPTH_EXTERNAL_INPUTS)}
    with tempfile.TemporaryDirectory() as directory:
        for index,(case,(name,change)) in enumerate(REAL_CASES.items()):
            pump=Path(directory)/str(index)/'pump_loop'
            shutil.copytree(PUMP,pump)
            plan=_edit_plan(pump,name,change)
            state=expected('model_dataset_validation',inputs[case])
            status='pass' if case in state.validation_passed else 'partial' if case in state.partial else 'fail'
            if case in ('unbounded_calibration','pointwise_prediction'):
                message='pointwise_prediction_forbidden' if case=='pointwise_prediction' else 'upper|bound'
                with pytest.raises(ValueError,match=message):
                    validate_model_dataset(plan)
                assert status=='fail'
                continue
            report=validate_model_dataset(plan)
            assert report.status==status,(case,report.status,status)
            if case=='missing_declared_series':
                assert len(report.findings)==inputs[case].missing_input_finding_count
                assert all(report.depth[key]['status']=='not_run' for key in ('time','scenarios','residual_series','envelopes','adequacy'))
