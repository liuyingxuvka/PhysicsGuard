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
ROOT = Path(__file__).resolve().parents[2]
PUMP = ROOT / 'examples/testfile_contracts/pump_loop'

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
CASES = (Case('no_data', data=False), Case('clean'), Case('multi_segment'), Case('stale_extractor', fresh=False, passed=False), Case('added_field', roles=False, passed=False), Case('unclassified', roles=False, passed=False), Case('missing_evidence', mappings=False, passed=False), Case('unknown_target', mappings=False, passed=False), Case('stale_model', passed=False), Case('review_required', passed=False))

def gate(field, message):

    def check(state, trace):
        if state.broad and state.data and (not getattr(state, field)):
            return False
        return True
    return check
RULE_NAMES = ('no_testfile_claim_without_manifest', 'no_testfile_claim_without_field_roles_and_mappings', 'no_testfile_claim_without_mapping_evidence_or_known_targets', 'no_testfile_claim_without_contract_pass')
RULES = (gate('fresh', 'Test data needs a fresh manifest and extractor hash.'), gate('roles', 'Every field needs a declared role and target or explicit disposition.'), gate('mappings', 'Mapped fields need evidence, convertible units and known targets.'), gate('passed', 'A test-file claim needs a native contract pass.'))


def assert_native_contract():
    import yaml
    from physicsguard.core.test_file_contract import check_test_file_contract,testfile_snapshot
    from .contract_cases import expected
    with tempfile.TemporaryDirectory() as directory:
        for index,case in enumerate(CASES):
            if not case.data:
                # Original no_data was an abstract model-only policy, not a native data claim.
                assert expected('test_file_contract',case).broad
                continue
            pump=Path(directory)/str(index)/'pump'
            shutil.copytree(PUMP,pump)
            if case.name in ('missing_evidence','unknown_target','review_required'):
                path=pump/'contracts/clean_contract.yaml'
                value=yaml.safe_load(path.read_text())
                field=value['fields']['flow_readback_kg_s']
                if case.name=='missing_evidence':
                    del field['evidence']
                elif case.name=='unknown_target':
                    field['target']='not_a_model_variable.x'
                else:
                    field['review_required']=True
                path.write_text(yaml.safe_dump(value))
            else:
                path=pump/f'contracts/{case.name}_contract.yaml'
            report=check_test_file_contract(path)
            codes={finding.type for finding in report.findings}
            state=State(case.name,True,True,
                not bool(codes & {'source_file_hash_mismatch','extractor_script_hash_mismatch','manifest_field_signature_mismatch'}),
                not bool(codes & {'field_unclassified','contract_field_missing','mapping_missing_target','ignored_without_reason'}),
                not bool(codes & {'mapping_missing_evidence','mapping_unknown_target','unit_not_convertible','conversion_disagrees_with_unit_table'}),
                report.ok,report.ok)
            wanted=expected('test_file_contract',case)
            assert state==wanted,(case,state,wanted)
            assert all(rule(state,None) for rule in RULES),case
            if report.ok:
                testfile_snapshot(path,0)
