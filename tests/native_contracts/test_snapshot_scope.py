"""Actual scalar-route payload obligations, separate from the thin intent adapter."""
import pytest
from tests._intent_cases import snapshot_inputs
from physicsguard.core.validation_depth import evaluate_validation_depth


@pytest.mark.parametrize('audit,observed,status,scope', [
    (True, True, 'partial', 'snapshot'),
    (False, True, 'blocked', None),
    (True, False, 'blocked', None),
    (False, False, 'blocked', None),
])
def test_no_declared_depth_limits_the_real_payload_to_available_scalar_inputs(audit, observed, status, scope):
    inputs = snapshot_inputs(audit, observed)
    assert inputs['plan'].depth is None
    payload = evaluate_validation_depth(**inputs).payload
    assert payload['status'] == status
    assert payload['ok'] is False
    assert payload['covered_scope'] == scope
    if scope == 'snapshot':
        assert 'validation_depth_not_declared' in {finding['type'] for finding in payload['findings']}
        assert payload['time']['snapshot_only'] is True
    else:
        assert payload['residual_series']['status'] == 'not_run'
