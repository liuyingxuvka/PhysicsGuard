"""Real core/child report contracts, with independent literal outcomes."""
from ._audit_cases import replay_case, LABELS, EXPECTED_AUDIT
CHILD_RESULTS = {'bad_schema': ('not_observed', 'none', 'no checks', 'not_run'), 'assumption_variable_boundary': ('not_observed', 'applied', 'no checks', 'not_run'), 'assumption_proposed': ('not_observed', 'not_applied', 'no checks', 'not_run'), 'assumption_parameter_override': ('not_observed', 'override_warned', 'no checks', 'not_run'), 'evaluate_clean': ('evaluated', 'none', 'PASS', 'not_run'), 'converged_bad_audit': ('not_observed', 'none', 'FAIL', 'failed'), 'clean': ('not_observed', 'none', 'PASS', 'passed'), 'hierarchy_evaluate_partial_unresolved': ('unobserved_listed', 'none', 'PASS', 'not_run'), 'hierarchy_evaluate_partial_tree_view_not_checked': ('unobserved_listed', 'none', 'not checked', 'not_run')}


REAL_CASE_IDS = ('clean', 'bad_schema', 'hierarchy_describe')


def assert_native_contract():
    from ._audit_cases import replay_case
    for key in tuple(dict.fromkeys((*REAL_CASE_IDS,*CHILD_RESULTS))):
        label,audit,ports,report,assumptions=replay_case(key)
        assert label == LABELS[key],(key,label,LABELS[key])
        if key in REAL_CASE_IDS:
            if audit is not None:
                assert audit is EXPECTED_AUDIT[key],key
        if key in CHILD_RESULTS:
            assert tuple(ports)==CHILD_RESULTS[key],(key,ports,CHILD_RESULTS[key])

