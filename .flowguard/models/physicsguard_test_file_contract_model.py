"""Executable single-file contracts: freshness, field roles, SI mappings, then claim.

The optional model-only route makes no test-data claim. When data is present,
every manifest field needs a role, active mappings need evidence and known
model targets/units, and the native contract must pass. Native conformance
replays current pump-loop fixtures and small mutations of their declarations.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import shutil
import tempfile

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow, ReplayObservation, replay_trace, select_covering_traces
from flowguard.conformance import projected_state_matches, projected_output_matches
from flowguard.explorer import Explorer

MODEL_ID = 'test_file_contract'
PARENT = 'system'
COMPONENTS = ['evidence', 'schema']
ROOT = Path(__file__).resolve().parents[2]
PUMP = ROOT / 'examples/testfile_contracts/pump_loop'
IMPLEMENTED_BY = {
    'Manifest': 'src/physicsguard/core/test_file_contract.py:_manifest_findings',
    'Mappings': 'src/physicsguard/core/parameter_coverage.py:check_field_mappings',
    'Claim': 'src/physicsguard/core/test_file_contract.py:check_test_file_contract',
    'Snapshot': 'src/physicsguard/core/test_file_contract.py:testfile_snapshot',
}
TESTED_BY = {
    'no_testfile_claim_without_manifest': ['tests/test_test_file_contract_core.py:test_bad_contracts_preserve_their_failure_meaning'],
    'no_testfile_claim_without_field_roles_and_mappings': ['tests/test_test_file_contract_core.py:test_added_manifest_field_blocks_contract'],
    'no_testfile_claim_without_mapping_evidence_or_known_targets': [
        'tests/test_test_file_contract_core.py:test_mapping_without_evidence_does_not_count_as_covered',
        'tests/test_test_file_contract_core.py:test_unknown_target_blocks_contract'],
    'no_testfile_claim_without_contract_pass': [
        'tests/test_test_file_contract_core.py:test_clean_contract_passes_with_evidence_backed_mappings',
        'tests/test_test_file_contract_core.py:test_review_required_contract_is_partial_and_not_ok'],
}


@dataclass(frozen=True)
class Case:
    name: str
    fresh: bool = True
    roles: bool = True
    mappings: bool = True
    passed: bool = True
    data: bool = True


@dataclass(frozen=True)
class State:
    case: str = ''
    checked: bool = False
    data: bool = True
    fresh: bool = False
    roles: bool = False
    mappings: bool = False
    passed: bool = False
    broad: bool = False


CASES = (Case('no_data', data=False), Case('clean'), Case('multi_segment'),
         Case('stale_extractor', fresh=False, passed=False), Case('added_field', roles=False, passed=False),
         Case('unclassified', roles=False, passed=False), Case('missing_evidence', mappings=False, passed=False),
         Case('unknown_target', mappings=False, passed=False), Case('stale_model', passed=False),
         Case('review_required', passed=False))


class Step:
    name = 'Step'
    reads = ('checked', 'data', 'fresh', 'roles', 'mappings', 'passed')
    writes = ('case', 'checked', 'data', 'fresh', 'roles', 'mappings', 'passed', 'broad')
    ignore = ''

    def allowed(self, state):
        if not state.checked:
            return False
        if not state.data:
            return True
        required = {'fresh': state.fresh, 'roles': state.roles, 'mappings': state.mappings, 'passed': state.passed}
        # A broken gate trusts its own partial check instead of requiring a native pass.
        return all(value for name, value in required.items() if name not in {self.ignore, 'passed'}) if self.ignore else all(required.values())

    def apply(self, event, state):
        if isinstance(event, Case):
            result = State(event.name, True, event.data, event.fresh, event.roles, event.mappings, event.passed)
            return (FunctionResult('checked', result, label=event.name),)
        broad = self.allowed(state)
        return (FunctionResult('allowed' if broad else 'blocked', replace(state, broad=broad), label='claim'),)


class SkipManifest(Step):
    ignore = 'fresh'


class SkipRoles(Step):
    ignore = 'roles'


class SkipMapping(Step):
    ignore = 'mappings'


class SkipPass(Step):
    ignore = 'passed'


def gate(field, message):
    def check(state, trace):
        if state.broad and state.data and not getattr(state, field):
            return InvariantResult.fail(message)
        return InvariantResult.pass_()
    return check


INVARIANTS = tuple(Invariant(name, description, gate(field, description)) for name,field,description in (
    ('no_testfile_claim_without_manifest','fresh','Test data needs a fresh manifest and extractor hash.'),
    ('no_testfile_claim_without_field_roles_and_mappings','roles','Every field needs a declared role and target or explicit disposition.'),
    ('no_testfile_claim_without_mapping_evidence_or_known_targets','mappings','Mapped fields need evidence, convertible units and known targets.'),
    ('no_testfile_claim_without_contract_pass','passed','A test-file claim needs a native contract pass.'),
))


def explorer(step):
    return Explorer(workflow=Workflow((step,)), initial_states=(State(),), external_inputs=(*CASES, 'claim'),
                    invariants=INVARIANTS, max_sequence_length=2, progress_steps=0)


def build_explorer():
    return explorer(Step())


def broken_variants():
    return {'claim_without_fresh_manifest':explorer(SkipManifest()), 'claim_with_unclassified_fields':explorer(SkipRoles()),
            'claim_without_mapping_evidence_or_known_targets':explorer(SkipMapping()), 'claim_without_contract_pass':explorer(SkipPass())}


class Native:
    def reset(self, state):
        self.root = Path(tempfile.mkdtemp(prefix='pg-contract-model-'))
        self.pump = self.root / 'pump'
        shutil.copytree(PUMP, self.pump)
        self.state = state

    def apply_step(self, step):
        import yaml
        from physicsguard.core.test_file_contract import check_test_file_contract, testfile_snapshot
        event = step.function_input
        if isinstance(event, Case):
            shutil.copyfile(PUMP / "contracts/clean_contract.yaml", self.pump / "contracts/clean_contract.yaml")
            if event.name == 'no_data':
                flags = (True, True, True, True)
            else:
                name = event.name
                if name in {'missing_evidence','unknown_target','review_required'}:
                    path = self.pump / 'contracts/clean_contract.yaml'
                    value = yaml.safe_load(path.read_text())
                    field = value['fields']['flow_readback_kg_s']
                    if name == 'missing_evidence':field.pop('evidence', None)
                    elif name == 'unknown_target':field['target']='not_a_model_variable.x'
                    else:field['review_required']=True
                    path.write_text(yaml.safe_dump(value))
                else:
                    path = self.pump / f'contracts/{name}_contract.yaml'
                report = check_test_file_contract(path)
                if report.ok and not self.state.checked:
                    testfile_snapshot(path, 0)
                codes = {finding.type for finding in report.findings}
                flags = (not bool(codes & {'source_file_hash_mismatch','extractor_script_hash_mismatch','manifest_field_signature_mismatch'}),
                         not bool(codes & {'field_unclassified','contract_field_missing','mapping_missing_target','ignored_without_reason'}),
                         not bool(codes & {'mapping_missing_evidence','mapping_unknown_target','unit_not_convertible','conversion_disagrees_with_unit_table'}), report.ok)
            self.state = State(event.name, True, event.data, *flags)
            output = 'checked'
        else:
            broad = self.state.checked and (not self.state.data or self.state.passed)
            self.state = replace(self.state, broad=broad)
            output = 'allowed' if broad else 'blocked'
        return ReplayObservation(function_name=step.function_name, observed_output=output, observed_state=self.state)

    def observe_state(self):return self.state
    def observe_output(self):return None


def conformance():
    result = None
    # Each selected trace starts with fresh fixture bytes; repeated case inputs need independent copies.
    for trace in select_covering_traces(build_explorer().explore().traces):
        adapter = Native()
        try:
            result = replay_trace(trace=trace, adapter=adapter, invariants=INVARIANTS,
                                  rules=(projected_state_matches(), projected_output_matches()))
        finally:
            shutil.rmtree(getattr(adapter,'root',''), ignore_errors=True)
        if not result.ok:return result
    return result
