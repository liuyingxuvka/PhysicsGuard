"""Direct solver audit contracts against production code."""
from ._audit_cases import EXPECTED_AUDIT, LABELS, ROOT, replay_case
PORT_VALUES = {'converged_bad_audit': 'failed'}

REAL_CASE_IDS = ('converged_bad_audit',)


def assert_native_contract():
    mismatches = []
    for key in REAL_CASE_IDS:
        label, audit, ports, report, assumptions = replay_case(key)
        if label != LABELS[key]:
            mismatches.append(f'{key}: native label {label!r}, expected {LABELS[key]!r}')
        if audit is not None and audit != EXPECTED_AUDIT[key]:
            mismatches.append(f'{key}: audit_pass differs')
        if ports[3] != PORT_VALUES[key]:
            mismatches.append(f'{key}: native audit {ports[3]!r}, expected {PORT_VALUES[key]!r}')
    assert not mismatches, mismatches

