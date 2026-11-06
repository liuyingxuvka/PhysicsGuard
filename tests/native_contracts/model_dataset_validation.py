"""Real dataset/plan mutations and their independent expected report statuses."""
from pathlib import Path
import shutil, tempfile, yaml
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


EXPECTED_STATUS = {'missing_declared_series': 'fail', 'clean_no_calibration': 'pass', 'missing_contract': 'fail', 'calibrated_pass': 'pass', 'optimizer_only': 'partial', 'unbounded_calibration': 'fail', 'missing_dataset_file': 'fail', 'uncertain_mapping': 'fail', 'snapshot_overclaim': 'fail', 'split_overlap': 'fail', 'series_missing': 'fail', 'one_point_time_varying_parameter': 'partial', 'pointwise_prediction': 'fail', 'stateful_rollout_pass': 'pass'}

REAL_CASES = {'missing_declared_series': ('clean_validation_plan.yaml', lambda pump, plan: plan['depth']['observed_series'].update(path='../observed/absent_series.yaml')), 'clean_no_calibration': ('clean_validation_plan.yaml', lambda pump, plan: None), 'missing_contract': ('clean_validation_plan.yaml', lambda pump, plan: plan['contracts'][0].update(contract='../contracts/unclassified_contract.yaml')), 'calibrated_pass': ('calibration_validation_plan.yaml', lambda pump, plan: plan.update(observed_file='../observed/clean_observed.yaml')), 'optimizer_only': ('calibration_validation_plan.yaml', _failing_holdout), 'unbounded_calibration': ('calibration_validation_plan.yaml', lambda pump, plan: plan['calibration']['parameters'][0].pop('upper')), 'missing_dataset_file': ('clean_validation_plan.yaml', lambda pump, plan: plan['depth']['dataset']['files'][0].update(path='../data/missing.csv')), 'uncertain_mapping': ('clean_validation_plan.yaml', _uncertain_mapping), 'snapshot_overclaim': ('clean_validation_plan.yaml', _snapshot_overclaim), 'split_overlap': ('calibration_validation_plan.yaml', _split_overlap), 'series_missing': ('clean_validation_plan.yaml', _invalid_series_point), 'one_point_time_varying_parameter': ('shallow_time_varying_validation_plan.yaml', lambda pump, plan: None), 'pointwise_prediction': ('clean_validation_plan.yaml', _rollout('pointwise')), 'stateful_rollout_pass': ('clean_validation_plan.yaml', _rollout('stateful_dynamic'))}


def assert_native_contract():
    import pytest
    from physicsguard.core.model_dataset_validation import validate_model_dataset
    with tempfile.TemporaryDirectory() as directory:
        for index,(case,(name,change)) in enumerate(REAL_CASES.items()):
            pump=Path(directory)/str(index)/'pump_loop'
            shutil.copytree(PUMP,pump)
            plan=_edit_plan(pump,name,change)
            status=EXPECTED_STATUS[case]
            if case in ('unbounded_calibration','pointwise_prediction'):
                message='pointwise_prediction_forbidden' if case=='pointwise_prediction' else 'upper|bound'
                with pytest.raises(ValueError,match=message):
                    validate_model_dataset(plan)
                assert status=='fail'
                continue
            report=validate_model_dataset(plan)
            assert report.status==status,(case,report.status,status)
            if case=='missing_declared_series':
                assert len(report.findings)==1
                assert all(report.depth[key]['status']=='not_run' for key in ('time','scenarios','residual_series','envelopes','adequacy'))

