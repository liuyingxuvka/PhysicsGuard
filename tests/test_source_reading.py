"""PG-901–903: original public fixtures, independent boundary controls and known limits.

The third batch uses its TRUTH requirements, including the two errors in the v1
prototype (sig_range/sig_plain). A known numeric-role swap is deliberately not
counted as caught: a numeric reader cannot establish semantic roles.
"""
from pathlib import Path
import hashlib
import math

import pytest
import yaml

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.core.test_file_contract import check_test_file_contract, testfile_snapshot as snapshot
from physicsguard.core.tree_view import render_tree_view
from physicsguard.core.units import known_conversion, read_unit
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.schema.observed_conversion import read_source_value

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / 'fixtures/source_reading'


def audit_for(name):
    for prefix, audit in [('pump', 'pump'), ('tab', 'heater'), ('log', 'bench'), ('mix', 'mix'),
                          ('fan', 'fan'), ('chill', 'chiller'), ('oil', 'oilcooler'), ('inv', 'inverter')]:
        if name.startswith(prefix + '_'):
            return 'audit_' + audit + '.yaml'
    if name.startswith('tank_'):
        return 'audit_tank_clock.yaml' if name in ('tank_clock', 'tank_dt_unquoted') else 'audit_tank_ok.yaml'
    if name.startswith('day_'):
        return {'day_clockdec': 'audit_daytank_dec.yaml', 'day_midnight': 'audit_daytank_night.yaml'}.get(name, 'audit_daytank.yaml')
    if name.startswith('store_') or name == 'sig_range':
        return 'audit_coldstore_ua58.yaml' if name == 'store_ua_unquoted' else 'audit_coldstore.yaml'
    if name.startswith('sig_'):
        return 'audit_inverter.yaml'
    return 'audit_panel_area.yaml' if name == 'panel_area' else 'audit_panel.yaml'


def evaluate(folder, name, audit=None):
    base = FIXTURES / folder
    path = base / (name + ('.json' if name.startswith('k70') else '.yaml'))
    spec = load_hierarchical_audit_spec(audit or base / audit_for(name))
    observed = load_observed_values(path)
    report = HierarchicalAuditRunner(spec).to_dict(HierarchicalAuditRunner(spec).evaluate_observed(observed, skip_unobserved=True))
    return spec, observed, report


# Faults name the independently stated source error, not only a failing residual.
SECOND = [
 ('pump_ok', None), ('pump_h36', 'pump.m_dot_kg_s'), ('pump_pct', 'pump.efficiency'), ('pump_thin', 'elec.P_W'),
 ('tab_ok', None), ('tab_row', 'elec.P_W'), ('tab_col', 'heat.m_dot_kg_s'), ('tab_dec_ok', None), ('tab_decimal', 'heat.T_in_K'),
 ('log_ok', None), ('log_row', 'row:bench_log.csv'), ('log_unit', 'heat.m_dot_kg_s'),
 ('mix_range', None), ('mix_swap', None), ('mix_round', 'mix.m_dot_1_kg_s'),
 ('tank_ok', None), ('tank_clock', 'parameter:vol.dt_s'), ('tank_words', None), ('tank_dt_unquoted', None),
]
THIRD = [
 ('fan_ok', None), ('fan_2pi', 'shaft.omega_rad_s'), ('fan_quote_fake', 'shaft.omega_rad_s'), ('fan_noquote', None),
 ('day_ok', None), ('day_clockdec', 'parameter:tank.dt_s'), ('day_per60', 'tank.m_dot_in_kg_s'),
 ('day_quote_si', 'tank.m_dot_in_kg_s'), ('day_swap', None), ('day_midnight', None),
 ('chill_ok', None), ('chill_row', 'chiller.Q_cooling_W'), ('chill_col', 'chiller.Q_cooling_W'), ('chill_round', 'loop.T_in_K'),
 ('oil_ok', None), ('oil_row', 'row:oil_log.csv'), ('oil_unit', 'oil.T_in_K'), ('oil_norowkey', None),
 ('store_ok', None), ('store_sign', 'walls.T_body_K'), ('store_ua_unquoted', None),
 ('inv_ok', None), ('inv_neighbour', 'inv.efficiency'), ('inv_meter_nbsp', None), ('inv_meter_plain', None),
 ('panel_ok', None), ('panel_area', 'parameter:panel.area_m2'), ('sig_range', None), ('sig_nbsp', None), ('sig_plain', None),
]


@pytest.mark.parametrize('folder,name,fault', [('second',n,f) for n,f in SECOND] + [('third',n,f) for n,f in THIRD])
def test_every_public_seed_has_its_stated_outcome(folder, name, fault):
    _, _, report = evaluate(folder, name)
    rows = {r['id']: r for r in report['metadata']['source_readings']}
    if fault:
        assert report['audit_pass'] is False, name
        assert rows[fault]['colour'] == 'red', (name, rows[fault])
        assert any(code in rows[fault]['reason'] for code in ('source_reading_disagrees', 'quote_not_in_source', 'header unit', 'row_key')), name
    else:
        assert report['audit_pass'] is True, name
        assert not any(r['colour'] == 'red' for r in rows.values()), name
    assert all(set(('id', 'colour', 'reason', 'source_digest')) <= r.keys() for r in rows.values())


@pytest.mark.parametrize('name,failed', [('q_correct', False), ('q_mean', True), ('q_seed_p4', True),
    ('q_seed_noquote', False), ('q_seed_rawunit', True), ('q_seed_fakequote', True), ('k70', True), ('k70_edited', True)])
def test_first_public_source_replays(name, failed):
    audit = ROOT / 'examples/hierarchical/heated_tank/heated_tank.yaml' if name.startswith('k70') else FIXTURES / 'first/audit.yaml'
    _, _, report = evaluate('first', name, audit)
    assert report['audit_pass'] is not failed
    if name == 'q_seed_p4':
        assert any('x60' in row['reason'] for row in report['metadata']['source_readings'])


@pytest.mark.parametrize('name,expected', [('s0_shipped', True), ('s2_labels', True), ('s3_rawunit_slip', True)])
def test_first_legacy_control_exit_codes(name, expected):
    _, _, report = evaluate('first', name, FIXTURES / 'first/audit.yaml')
    assert report['audit_pass'] is expected


def test_legacy_disagreement_still_refuses_instead_of_passing():
    with pytest.raises(ValueError, match='signal_reading_disagrees'):
        load_observed_values(FIXTURES / 'first/s1_density.yaml')


@pytest.mark.parametrize('text,unit,value', [('efficiency 64 percent', None, .64), ('0.64', None, .64),
    ('held at −22 to −18 °C', 'K', None), ('1\u2009360 W', 'W', 1360), ('4\u00a0641 W', 'W', 4641),
    ('9:40–10:25', 's', 2700), ('7 L/min', 'L/s', 7/60), ('1450 rpm', 'rad/s', 1450*math.pi/30)])
def test_reader_uses_own_units_and_written_precision(text, unit, value):
    result = read_source_value(text, unit)
    assert result['kind'] == ('range' if value is None else 'value')
    if value is not None:
        assert result['value'] == pytest.approx(value)
    assert result['tolerance'] > 0


@pytest.mark.parametrize('text', ['6,0 L/min', '1,000 W', '1 360 W', "1'360 W", 'from 10 °C to 12 °C',
    'between -5 and 3 °C', '20 min 30 s', 'six litres', '23:45–0:15', '2 unknown_energy', '5 unknown_heat/kg/K'])
def test_unreadable_and_compound_spans_are_not_reinterpreted(text):
    assert read_source_value(text, 'K' if '°C' in text else 's' if ':' in text else 'W')['kind'] == 'unreadable'


def test_dependencies_are_traced_on_fully_observed_snapshot_and_noquote_is_all_grey():
    from dataclasses import replace
    from physicsguard.core.hierarchy import _attach_source_report
    from physicsguard.core.residual import ResidualBuilder
    spec, observed, _ = evaluate('second', 'mix_range')
    runner = HierarchicalAuditRunner(spec)
    native = runner.evaluate_observed(observed, skip_unobserved=True)
    # An absent or deliberately false report cache must not hide real module reads.
    for metadata in ({}, {'residual_dependencies': {'mix.flow_merge_temperature_balance': []}}):
        traced = _attach_source_report(replace(native, metadata=metadata), observed, spec, ResidualBuilder(spec.system), None)
        assert next(r for r in traced.block_verdicts if r['block_id']=='merge')['colour']=='green'
    spec, _, report = evaluate('third', 'fan_noquote')
    assert all(r['colour'] == 'grey' for r in report['metadata']['source_readings'])
    assert all(r['colour'] == 'grey' for r in report['block_verdicts'])
    from physicsguard.core.hierarchy import describe_hierarchy
    assert 'passes on AI values only' in render_tree_view(describe_hierarchy(spec), report)
    _, _, good = evaluate('third', 'fan_ok')
    assert {r['block_id']: r['colour'] for r in good['block_verdicts']}['drive'] == 'green'


def test_original_hash_is_read_each_run_and_quote_uses_matched_source_span(tmp_path):
    original = tmp_path / 'question.txt'
    original.write_text('meter reads 1\u2009360 W')
    data = {'sources': {'question': 'question.txt'}, 'variables': {'meter.power': {
        'value': 1360, 'unit': 'W', 'quote': {'from': 'question', 'text': 'meter reads 1 360 W'}}}}
    path = tmp_path / 'values.yaml'; path.write_text(yaml.safe_dump(data))
    observed = load_observed_values(path)
    assert observed._source_readings[0]['colour'] == 'green'
    assert observed._source_readings[0]['source_digest'] == hashlib.sha256(original.read_bytes()).hexdigest()
    original.write_text('meter reads 1\u2009361 W')
    again = load_observed_values(path)
    assert again._source_readings[0]['colour'] == 'red'
    assert 'quote_not_in_source' in again._source_readings[0]['reason']


def test_direct_conversion_cannot_silently_skip_a_quote_without_original_context():
    from physicsguard.schema.observation_spec import ObservedValueSpec
    from physicsguard.schema.observed_conversion import convert_observed_rows
    row = ObservedValueSpec(value=360, unit='W', quote={'from':'question','text':'1360 W'})
    with pytest.raises(ValueError, match='quote_requires_source_document'):
        convert_observed_rows({'meter.power':row}, {})


def test_csv_contract_unit_and_numeric_key_are_independently_checked():
    base = FIXTURES / 'third'
    assert check_test_file_contract(base / 'oil_contract_ok.yaml').ok
    review = check_test_file_contract(base / 'oil_contract_unit.yaml')
    assert not review.ok and 'header_unit_disagrees' in {r.type for r in review.findings}
    result = snapshot(base / 'oil_contract_ok.yaml', at='t_s=240')
    assert result['row_key'] == {'file': 'oil_log.csv', 'field': 't_s', 'value': 240}
    assert result['variables']['oil.T_in_K']['external_signal'].endswith('@12')
    assert all('conversion_factor' not in row and 'conversion_offset' not in row for row in result['variables'].values())


@pytest.mark.parametrize('source,target,factor', [('tonnes','kg',1000), ('kilometers','m',1000),
    ('kilometres','km',1), ('kilograms per second','kg/s',1), ('kilowatts','W',1000), ('%','1',.01),
    ('kWh','J',3.6e6), ('MWh','kWh',1000), ('MJ','J',1e6),
    ('cubic metres per hour','m^3/s',1/3600), ('square metres','cm^2',10000),
    ('kilowatt-hours','kWh',1), ('megawatt hours/day','kWh/d',1000),
    ('Ml/d','m^3/h',1000/24), ('ML/d','m^3/s',1000/86400), ('mL','L',.001)])
def test_shared_table_is_the_only_spelling_owner(source,target,factor):
    assert known_conversion(source,target) == (factor,0)
    assert read_unit('ton') is None and read_unit('tons') is None


def test_known_numeric_role_swap_and_unquoted_parameter_remain_explicit_limits():
    for folder,name,grey in [('second','mix_swap',None), ('third','day_swap',None),
                             ('third','store_ua_unquoted','parameter:walls.UA_W_K'),
                             ('third','day_midnight','parameter:tank.dt_s')]:
        _, _, report = evaluate(folder,name)
        assert report['audit_pass'] is True  # known not caught; not counted as a defect caught
        if grey:
            assert next(r for r in report['metadata']['source_readings'] if r['id']==grey)['colour']=='grey'


def test_explicit_transducer_calibration_survives_snapshot_but_is_not_source_proof(tmp_path):
    from test_test_file_contract_core import changed_contract, TANK
    contract = changed_contract(tmp_path, lambda data: data['fields']['T_amb_C'].update(
        unit='mV', conversion={'factor': .1, 'offset': 273.15}), TANK / 'tank_run_contract.yaml')
    assert check_test_file_contract(contract).ok
    result = snapshot(contract, 70)
    point = result['variables']['loss.T_ambient_K']
    assert point['raw_unit'] == 'mV' and point['conversion_factor'] == .1
    path = tmp_path / 'snapshot.yaml'
    path.write_text(yaml.safe_dump(result))
    observed = load_observed_values(path)
    row = next(r for r in observed._source_readings if r['id'] == 'loss.T_ambient_K')
    assert row['colour'] == 'grey' and 'calibration' in row['reason']
    assert observed.variables['loss.T_ambient_K']._conversion_checked is False


def test_documented_example_cli_preserves_report_schema_and_exposes_source_rows():
    import json
    from conftest import run_cli
    base = ROOT / 'examples/source_reading'
    for name, exit_code in [('observed.yaml', 0), ('observed_bad.yaml', 1)]:
        result = run_cli('hierarchy', 'evaluate', str(base/'audit.yaml'), str(base/name), '--json')
        assert result.returncode == exit_code, result.stderr
        report = json.loads(result.stdout)
        assert 'source_readings' not in report and 'sources' not in report
        rows = report['metadata']['source_readings']
        assert all(set(('id','colour','reason','source_digest')) <= row.keys() for row in rows)
        digest = hashlib.sha256((base/'question.txt').read_bytes()).hexdigest()
        assert report['metadata']['sources']['question']['sha256'] == digest
        if exit_code:
            assert any(row['colour'] == 'red' and 'x60' in row['reason'] for row in rows)
        else:
            assert not any(row['colour'] == 'red' for row in rows)


def test_quoted_parameters_do_not_turn_a_snapshot_header_into_a_parameter_catalog():
    from test_portable_model_headers import _load_header_script
    data = yaml.safe_load((ROOT/'examples/source_reading/observed.yaml').read_text())
    assert data['parameters']
    assert _load_header_script().artifact_kind(data) == 'observed-values snapshot'
