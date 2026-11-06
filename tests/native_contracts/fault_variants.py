"""Original real fault fixtures, masking evidence and independent expected signatures."""
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from physicsguard.core.diagnosability import evaluate_fault_variants
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_values
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec
ROOT = Path(__file__).resolve().parents[2]


EXAMPLE = ROOT / 'examples/hierarchical/heated_tank'


SPEC = load_hierarchical_audit_spec(EXAMPLE / 'heated_tank.yaml')


NOMINAL = load_observed_values(EXAMPLE / 'measured_k30.yaml')


@dataclass(frozen=True)
class VariantCase:
    name: str
    selected: tuple[str, ...] = ()
    fault_count: int = 0
    expected_blocks: tuple[str, ...] = ()
    reference_blocks: tuple[str, ...] | None = ()
    benign: bool = False
    known_masked: bool = False
    fixture: str = 'tank'
    observed_failed: bool | None = None
    matching: tuple[str, ...] = ()
    pairwise: bool = False


def _pair_status(failed, expected):
    if failed is None:
        return None
    actual, expected = (set(failed), set(expected))
    if not actual:
        return 'undetected'
    if actual == expected:
        return 'ok'
    if actual < expected:
        return 'masked'
    return 'outside'


def _fault_pairs():
    return tuple(combinations(tuple((v.id for v in SPEC.fault_variants if v.kind == 'fault')), 2))


def _cases():
    cases = [VariantCase('clean')]
    variants = tuple(SPEC.fault_variants)
    for count in (1, 2):
        for group in combinations(variants, count):
            faults = tuple((v for v in group if v.kind == 'fault'))
            selected = tuple((v.id for v in group))
            expected = tuple(sorted({b for v in faults for b in v.expect_blocks}))
            masked = set(selected) == {'heater_half', 'inlet_temp_offset'}
            reference = ('heater',) if masked else expected
            cases.append(VariantCase('+'.join(selected), selected, len(faults), expected, reference, any((v.kind == 'benign' for v in group)), masked))
    cases.extend((VariantCase('unmasked_two_owners', ('parent_fault', 'child_fault'), 2, ('heater', 'thermal'), ('heater', 'thermal'), fixture='unmasked'), VariantCase('cancelled_pair', ('plus', 'minus'), 2, ('thermal',), (), fixture='cancelled'), VariantCase('outside_pair', ('parent_fault', 'wrong_owner'), 2, ('thermal',), ('heater', 'thermal'), fixture='outside'), VariantCase('unavailable_pair', ('heater_half', 'original_inflow_unit_x1000'), 2, ('heater', 'hydraulics'), None, fixture='unavailable'), VariantCase('all_fault_pairs', pairwise=True), VariantCase('observed_explained', observed_failed=True, matching=('heater_half',), fixture='explained'), VariantCase('observed_unexplained', observed_failed=True, fixture='unexplained')))
    return tuple(cases)


CASES = _cases()


def _fixture(case):
    if case.fixture in {'tank', 'explained'}:
        return (SPEC, NOMINAL)
    if case.fixture == 'unavailable':
        spec = SPEC.model_copy(deep=True)
        spec.fault_variants = [v for v in spec.fault_variants if v.id in {'heater_half', 'outflow_unit_x1000'}]
        flow = next((v for v in spec.fault_variants if v.id == 'outflow_unit_x1000'))
        flow.id = 'original_inflow_unit_x1000'
        flow.changes[0].variable = 'inflow_mass.V_dot_m3_s'
        return (spec, NOMINAL)

    def fault(name, variable, offset, block):
        return {'id': name, 'kind': 'fault', 'changes': [{'variable': variable, 'offset': offset}], 'expect_blocks': [block]}
    if case.fixture == 'cancelled':
        variants = [fault('plus', 'a.x', 2.0, 'thermal'), fault('minus', 'a.x', -2.0, 'thermal')]
    else:
        variants = [fault('parent_fault', 'a.x', 2.0, 'thermal')]
        if case.fixture != 'unexplained':
            variants.append(fault('wrong_owner' if case.fixture == 'outside' else 'child_fault', 'b.x', 3.0, 'thermal' if case.fixture == 'outside' else 'heater'))
    spec = HierarchicalAuditSpec.model_validate({'audit_name': 'variant-boundaries', 'system': {'system_name': 'variant-boundaries', 'components': [{'id': 'a', 'type': 'DummyResidualModule', 'parameters': {'target': 0.0}}, {'id': 'b', 'type': 'DummyResidualModule', 'parameters': {'target': 0.0}}]}, 'hierarchy': {'blocks': [{'id': 'thermal', 'level': 0, 'components': ['a']}, {'id': 'heater', 'parent_id': 'thermal', 'level': 1, 'components': ['b']}]}, 'fault_variants': variants})
    nominal = ObservedValuesSpec(variables={'a.x': {'value': 0.0}, 'b.x': {'value': 0.0}})
    return (spec, nominal)


def _review(case):
    spec, nominal = _fixture(case)
    observed = load_observed_values(EXAMPLE / 'measured_k70.yaml') if case.fixture == 'explained' else ObservedValuesSpec(variables={'a.x': {'value': 2.0}, 'b.x': {'value': 3.0}}) if case.fixture == 'unexplained' else None
    before = tuple((item.model_dump(mode='json') for item in (spec, nominal, observed) if item is not None))
    result = evaluate_fault_variants(spec, nominal, pairs=case.pairwise, observed=observed, base_dir=EXAMPLE, variant_ids=None if case.pairwise or observed is not None else case.selected)
    assert tuple((item.model_dump(mode='json') for item in (spec, nominal, observed) if item is not None)) == before
    assert {'pairwise', 'next_signal', 'masked_pairs', 'model_miss'} <= result.keys(), 'unified fault-variant result fields are missing'
    assert result['nominal_audit_pass'] and result['nominal_signature'] == {}
    expected_miss = case.observed_failed and not case.matching if case.observed_failed is not None else None
    assert result['model_miss'] is expected_miss
    if observed is not None:
        assert tuple(result['matching_variants']) == case.matching
    if case.pairwise or observed is not None or (not case.selected):
        if case.fault_count == 0:
            assert result['nominal_audit_pass'] is True
        if case.pairwise:
            actual = [tuple(sorted(row['variants'])) for row in result['pairwise']]
            wanted = {tuple(sorted(pair)) for pair in _fault_pairs()}
            assert len(actual) == len(wanted) and set(actual) == wanted
        return
    row, = result['variants']
    if row['status'] == 'not_evaluable':
        assert case.reference_blocks is None, 'a declared evaluable physical fixture unexpectedly became unavailable'
        assert row['signature'] is None and row['audit_pass'] is None and (row['pair_status'] is None)
        assert not row['ok']
        return
    assert row['status'] == 'evaluated'
    assert 'pair_status' in row, 'unified physical pair classification is missing'
    assert set(row['failed_blocks']) == set(row['signature'])
    if case.reference_blocks is None:
        raise AssertionError('an unavailable fixture unexpectedly became evaluable')
    expected_status = _pair_status(case.reference_blocks, case.expected_blocks) if case.fault_count >= 2 else None
    assert row['pair_status'] == expected_status
    assert set(row['failed_blocks']) == set(case.reference_blocks)
    expected_ok = expected_status in {'ok', 'masked'} if case.fault_count >= 2 else bool(case.fault_count) or row['neutral']
    assert row['ok'] is expected_ok and result['ok'] is expected_ok
    assert row['expect_blocks_met'] is (set(case.expected_blocks) <= set(row['failed_blocks']))
    if case.fault_count == 0:
        assert row['audit_pass'] is True
    if case.fault_count == 1:
        assert row['audit_pass'] is False
    if case.fault_count and row['audit_pass'] is False and not case.known_masked:
        assert set(case.expected_blocks) <= set(row['failed_blocks'])
    if case.benign:
        assert (row['audit_pass'], tuple(sorted(row['failed_blocks']))) == (not case.reference_blocks, case.reference_blocks)
    if expected_status == 'masked':
        assert row['id'] in result['masked_pairs']


def assert_native_contract():
    for case in CASES:
        _review(case)
