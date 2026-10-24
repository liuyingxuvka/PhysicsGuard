from pathlib import Path
import copy
import math
import pytest
import yaml
from physicsguard.core.contract_diff import diff_test_file_contracts
from physicsguard.core.data_file_manifest import generate_delimited_manifest, field_signature_hash
from physicsguard.core.test_file_contract import check_test_file_contract, testfile_snapshot as snapshot, testfile_series as series

ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / 'examples/testfile_contracts/pump_loop'
TANK = ROOT / 'examples/hierarchical/heated_tank'


def changed_contract(tmp_path, change, source=None):
    source = source or PUMP / 'contracts/clean_contract.yaml'
    data = yaml.safe_load(source.read_text())
    for key in ('data_file', 'manifest', 'model'):
        data[key] = str((source.parent / data[key]).resolve())
    change(data)
    target = tmp_path / 'contract.yaml'
    target.write_text(yaml.safe_dump(data))
    return target


def test_generate_delimited_manifest_counts_fields_time_and_signature(tmp_path):
    path = tmp_path / 'sample.csv';path.write_text('time_s,x,y\n0,1,2\n0.1,1.5,3\n')
    result = generate_delimited_manifest(path, time_column='time_s')
    assert result.shape.field_count == 3 and result.shape.row_count == 2
    assert result.time.duration_s == .1
    assert result.field_signature_hash == field_signature_hash(result)


def test_clean_contract_passes_with_evidence_backed_mappings():
    result = check_test_file_contract(PUMP / 'contracts/clean_contract.yaml')
    assert result.ok and result.summary['analysis_claim_gate'] == 'open_for_scoped_analysis'


@pytest.mark.parametrize('case,code', [
 ('added_field','field_unclassified'), ('renamed_field','contract_field_missing'),
 ('stale_model','model_hash_mismatch'), ('stale_extractor','extractor_script_hash_mismatch'),
 ('unclassified','field_unclassified'), ('excluded_without_reason','ignored_without_reason')])
def test_bad_contracts_preserve_their_failure_meaning(case, code):
    result = check_test_file_contract(PUMP / f'contracts/{case}_contract.yaml')
    assert result.status == 'fail'
    assert code in {f.type for f in result.findings}


def test_added_manifest_field_blocks_contract():
    assert check_test_file_contract(PUMP / 'contracts/added_field_contract.yaml').status == 'fail'


def test_mapping_without_evidence_does_not_count_as_covered(tmp_path):
    path = changed_contract(tmp_path, lambda d:d['fields']['flow_readback_kg_s'].pop('evidence'))
    assert 'mapping_missing_evidence' in {f.type for f in check_test_file_contract(path).findings}


def test_unknown_target_blocks_contract(tmp_path):
    path = changed_contract(tmp_path, lambda d:d['fields']['flow_readback_kg_s'].update(target='unknown.x'))
    assert 'mapping_unknown_target' in {f.type for f in check_test_file_contract(path).findings}


def test_review_required_contract_is_partial_and_not_ok(tmp_path):
    path = changed_contract(tmp_path, lambda d:d['fields']['flow_readback_kg_s'].update(review_required=True))
    result = check_test_file_contract(path)
    assert not result.ok and result.status == 'partial'
    assert result.summary['analysis_claim_gate'] == 'limited_claims_only'


def test_contract_diff_flags_possible_rename():
    result = diff_test_file_contracts(PUMP/'contracts/clean_contract.yaml', PUMP/'contracts/renamed_field_contract.yaml')
    assert result.status == 'changed'
    assert any(r['type']=='possible_field_rename' for r in result.changes)


@pytest.mark.parametrize('row',[30,70])
@pytest.mark.parametrize('contract,prefix',[('tank_run_contract.yaml','measured')])
def test_snapshot_matches_existing_tank_values(contract,prefix,row):
    actual = snapshot(TANK/contract,row)
    stored = yaml.safe_load((TANK/f'{prefix}_k{row}.yaml').read_text())
    assert {k:v['value'] for k,v in actual['variables'].items()} == {k:v['value'] for k,v in stored['variables'].items()}
    assert actual['variables']['inflow_mass.V_dot_m3_s']['conversion_factor'] == .001
    assert actual['variables']['heat.T_previous_K']['conversion_offset'] == 273.15
    assert actual['variables']['heat.T_current_K']['external_signal'] == f'T_tank_C@{row+1}'


@pytest.mark.parametrize('unit,conversion,code',[
 ('unknown',None,'unit_not_convertible'), ('degC',{'factor':1},'conversion_disagrees_with_unit_table')])
def test_units_fail_closed(tmp_path,unit,conversion,code):
    def change(data):
        field=data['fields']['T_tank_C'];field['unit']=unit
        if conversion is not None:field['conversion']=conversion
    path=changed_contract(tmp_path,change,TANK/'tank_run_contract.yaml')
    assert code in {f.type for f in check_test_file_contract(path).findings}


def test_series_has_120_single_step_points_and_preserves_si_values():
    from physicsguard.schema.validation_depth import ObservedSeriesSpec
    result=series(TANK/'tank_run_contract.yaml')
    parsed=ObservedSeriesSpec.model_validate(result)
    assert len(parsed.points)==120
    assert parsed.points[60].timestamp==600
    assert parsed.points[70].variables['heat.T_previous_K'].value == snapshot(TANK/'tank_run_contract.yaml',70)['variables']['heat.T_previous_K']['value']
    assert len(series(TANK/'tank_run_contract.yaml','70:72')['points'])==2


def test_next_row_and_nonfinite_values_cannot_be_invented():
    with pytest.raises(ValueError,match='next_row'):
        snapshot(TANK/'tank_run_contract.yaml',120)


@pytest.mark.parametrize('source,target,factor,offset',[
 ('degC','K',1,273.15),('kW','W',1000,0),('L/min','m³/s',.001/60,0),
 ('bar','Pa',1e5,0),('rpm','rad/s',math.pi/30,0),('kg/h','kg/s',1/3600,0),
 ('mm','m',.001,0),('h','s',3600,0),('A','A',1,0)])
def test_documented_unit_table(source,target,factor,offset):
    from physicsguard.core.units import unit_conversion
    assert unit_conversion(source,target)==pytest.approx((factor,offset))


def test_snapshot_copies_the_contract_source_model(tmp_path):
    from physicsguard.schema.validation_depth import ObservedSeriesSpec

    header = {"model_name": " model A ", "tool": "exporter", "scenario": "run A"}
    path = changed_contract(tmp_path, lambda data: None)
    baseline = snapshot(path, 0)
    assert 'source_model' not in baseline
    assert 'source_model' not in series(path, '0:2')
    contract = yaml.safe_load(path.read_text())
    contract['source_model'] = header
    path.write_text(yaml.safe_dump(contract))
    copied = snapshot(path, 0)
    sequence = series(path, '0:2')
    assert copied['source_model'] == sequence['source_model'] == header
    assert ObservedSeriesSpec.model_validate(sequence).source_model.model_dump(exclude_unset=True) == header
    assert copied['variables'] == baseline['variables']
