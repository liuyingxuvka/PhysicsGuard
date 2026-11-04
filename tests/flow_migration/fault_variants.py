"""Finite alternate-device singles and physical pair-policy witnesses.

Expected signatures are declared before replay, never learned from engine output.
A known masked fixture is distinct from an unmasked pair losing its second code.
"""
from dataclasses import dataclass, replace
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

@dataclass(frozen=True)
class VariantState:
    case: VariantCase | None = None
    audit_pass: bool | None = None
    failed_blocks: tuple[str, ...] | None = None
    pair_status: str | None = None
    row_ok: bool = False
    masked_listed: bool = False
    pairwise_pairs: tuple[tuple[str, str], ...] = ()
    model_miss: bool | None = None

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

def expected(case, state, mutation=''):
    failed = case.reference_blocks
    status = _pair_status(failed, case.expected_blocks) if case.fault_count >= 2 else None
    audit_pass = not failed if failed is not None else None
    ok = status in {'ok', 'masked'} if case.fault_count >= 2 else bool(failed) and set(case.expected_blocks) <= set(failed) if case.fault_count else audit_pass is True
    outcome = VariantState(case, audit_pass, failed, status, ok, status == 'masked', _fault_pairs() if case.pairwise else (), case.observed_failed and (not case.matching) if case.observed_failed is not None else None)
    return outcome

def clean_input_accepted(state, trace):
    c = state.case
    if c and c.fault_count == 0 and (state.audit_pass is not True):
        return False
    return True

def each_defect_rejected(state, trace):
    c = state.case
    if c and c.fault_count == 1 and (state.audit_pass is not False):
        return False
    return True

def every_defect_reported(state, trace):
    c = state.case
    if c and c.fault_count and (state.audit_pass is False) and (not c.known_masked):
        if set(c.expected_blocks) - set(state.failed_blocks or ()):
            return False
    return True

def benign_features_neutral(state, trace):
    c = state.case
    if c and c.benign and ((state.audit_pass, state.failed_blocks) != (not c.reference_blocks, c.reference_blocks)):
        return False
    return True

def masked_pairs_accepted(state, trace):
    c = state.case
    if c and c.fault_count >= 2 and (_pair_status(c.reference_blocks, c.expected_blocks) == 'masked'):
        if state.pair_status != 'masked' or not state.row_ok or (not state.masked_listed):
            return False
    return True

def undetected_pairs_rejected(state, trace):
    c = state.case
    if c and c.fault_count >= 2 and (_pair_status(c.reference_blocks, c.expected_blocks) == 'undetected'):
        if state.pair_status != 'undetected' or state.row_ok:
            return False
    return True

def outside_pairs_rejected(state, trace):
    c = state.case
    if c and c.fault_count >= 2 and (_pair_status(c.reference_blocks, c.expected_blocks) == 'outside'):
        if state.pair_status != 'outside' or state.row_ok:
            return False
    return True

def pairwise_evidence_complete(state, trace):
    if state.case and state.case.pairwise:
        actual = [tuple(sorted(pair)) for pair in state.pairwise_pairs]
        expected = {tuple(sorted(pair)) for pair in _fault_pairs()}
        if len(actual) != len(expected) or set(actual) != expected:
            return False
    return True

def model_miss_is_explicit(state, trace):
    c = state.case
    if c and state.model_miss != (c.observed_failed and (not c.matching) if c.observed_failed is not None else None):
        return False
    return True

def unevaluable_remains_explicit(state, trace):
    c = state.case
    if c and c.reference_blocks is None:
        if state.failed_blocks is not None or state.audit_pass is not None or state.pair_status is not None or state.row_ok:
            return False
    return True

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
    if observed is not None:
        assert tuple(result['matching_variants']) == case.matching
    if case.pairwise or observed is not None or (not case.selected):
        return VariantState(case, result['nominal_audit_pass'], tuple(result['nominal_signature']), row_ok=result['ok'], pairwise_pairs=tuple((tuple(row['variants']) for row in result['pairwise'])), model_miss=result['model_miss'])
    row, = result['variants']
    if row['status'] == 'not_evaluable':
        assert case.reference_blocks is None, 'a declared evaluable physical fixture unexpectedly became unavailable'
        assert row['signature'] is None and row['audit_pass'] is None and (row['pair_status'] is None)
        return VariantState(case, None, None, None, row['ok'], model_miss=result['model_miss'])
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
    return VariantState(case, row['audit_pass'], tuple(sorted(row['failed_blocks'])), row['pair_status'], row['ok'], row['id'] in result['masked_pairs'], model_miss=result['model_miss'])
RULE_NAMES = ('clean_input_accepted', 'each_defect_rejected', 'every_defect_reported', 'benign_features_neutral', 'masked_pairs_accepted', 'undetected_pairs_rejected', 'outside_pairs_rejected', 'pairwise_evidence_complete', 'model_miss_is_explicit', 'unevaluable_remains_explicit')
RULES = (clean_input_accepted, each_defect_rejected, every_defect_reported, benign_features_neutral, masked_pairs_accepted, undetected_pairs_rejected, outside_pairs_rejected, pairwise_evidence_complete, model_miss_is_explicit, unevaluable_remains_explicit)


def assert_native_contract():
    for case in CASES:
        state=_review(case)
        assert all(rule(state,None) for rule in RULES),case.name
