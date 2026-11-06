"""Direct observed derivation contracts against production code."""
from ._audit_cases import EXPECTED_AUDIT, LABELS, ROOT, replay_case
PORT_VALUES = {'evaluate_clean': 'evaluated', 'evaluate_bad_audit': 'evaluated', 'evaluate_missing_observed': 'evaluated', 'compare_bad_audit': 'evaluated', 'hierarchy_clean': 'not_observed', 'hierarchy_bad_audit': 'not_observed', 'hierarchy_evaluate_clean': 'evaluated', 'hierarchy_evaluate_bad_audit': 'evaluated', 'hierarchy_evaluate_missing_observed': 'not_observed', 'hierarchy_evaluate_derived_bad_audit': 'unobserved_listed', 'hierarchy_evaluate_partial_unresolved': 'unobserved_listed', 'hierarchy_evaluate_zero_product': 'not_observed', 'hierarchy_evaluate_partial_snapshot': 'evaluated'}

REAL_CASE_IDS = ('evaluate_clean', 'evaluate_bad_audit', 'evaluate_missing_observed', 'compare_bad_audit', 'hierarchy_clean', 'hierarchy_bad_audit', 'hierarchy_evaluate_clean', 'hierarchy_evaluate_bad_audit', 'hierarchy_evaluate_missing_observed', 'hierarchy_evaluate_derived_bad_audit', 'hierarchy_evaluate_partial_unresolved', 'hierarchy_evaluate_zero_product', 'hierarchy_evaluate_partial_snapshot')


def _unit_hint_slip():
    from pathlib import Path
    import yaml
    from physicsguard.core import hierarchy
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.schema.observation_spec import ObservedValuesSpec
    tank = Path(__file__).resolve().parents[2] / 'examples/hierarchical/heated_tank'
    data = yaml.safe_load((tank / 'measured_k30.yaml').read_text())
    for row in data['variables'].values():
        row.pop('raw_value')
        row.pop('raw_unit')
    variable = 'inflow_mass.V_dot_m3_s'
    data['variables'][variable]['value'] *= 1000
    observed = ObservedValuesSpec.model_validate(data)
    before = observed.model_dump()
    measured = {name: row.value for name, row in observed.variables.items()}
    attempted = set()
    original = hierarchy._derive_unobserved

    def counted(builder, registry, known):
        attempted.update((name for name, value in measured.items() if name in known and known[name] != value))
        return original(builder, registry, known)
    hierarchy._derive_unobserved = counted
    try:
        spec = load_hierarchical_audit_spec(tank / 'heated_tank.yaml')
        report = hierarchy.HierarchicalAuditRunner(spec).evaluate_observed(observed, _resolution=False)
    finally:
        hierarchy._derive_unobserved = original
    problems = []
    if observed.model_dump() != before:
        problems.append('unit_hint_slip: observations changed')
    names = tuple((name for followup in report.bug_family_followups if followup.followup_id == 'unit_conversion_family' for name in followup.affected_variables))
    if names != (variable,):
        problems.append(f'unit_hint_slip: hint names {names!r}')
    if len(attempted) > 20:
        problems.append(f'unit_hint_slip: probed {len(attempted)} variables')
    return problems


def assert_native_contract():
    mismatches = []
    for key in REAL_CASE_IDS:
        label, audit, ports, report, assumptions = replay_case(key)
        if label != LABELS[key]:
            mismatches.append(f'{key}: native label {label!r}, expected {LABELS[key]!r}')
        if audit is not None and audit != EXPECTED_AUDIT[key]:
            mismatches.append(f'{key}: audit_pass differs')
        if ports[0] != PORT_VALUES[key]:
            mismatches.append(f'{key}: native observed {ports[0]!r}, expected {PORT_VALUES[key]!r}')
    mismatches.extend(_unit_hint_slip())
    assert not mismatches, mismatches

