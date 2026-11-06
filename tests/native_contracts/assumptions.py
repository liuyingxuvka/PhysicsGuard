"""Direct assumptions contracts against production code."""
from ._audit_cases import EXPECTED_AUDIT, LABELS, ROOT, replay_case
PORT_VALUES = {'assumption_parameter_fill': 'applied', 'assumption_parameter_override': 'override_warned', 'assumption_proposed': 'not_applied', 'assumption_rejected': 'not_applied', 'assumption_variable_boundary': 'applied'}

REAL_CASE_IDS = ('assumption_parameter_fill', 'assumption_parameter_override', 'assumption_proposed', 'assumption_rejected', 'assumption_variable_boundary')


def assert_native_contract():
    mismatches = []
    for key in REAL_CASE_IDS:
        label, audit, ports, report, assumptions = replay_case(key)
        from ._audit_cases import replay_assumption_report
        replay_assumption_report(key)
        if label != LABELS[key]:
            mismatches.append(f'{key}: native label {label!r}, expected {LABELS[key]!r}')
        if audit is not None and audit != EXPECTED_AUDIT[key]:
            mismatches.append(f'{key}: audit_pass differs')
        if ports[1] != PORT_VALUES[key]:
            mismatches.append(f'{key}: native disposition {ports[1]!r}, expected {PORT_VALUES[key]!r}')
    assert not mismatches, mismatches

