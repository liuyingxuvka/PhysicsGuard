"""Real file contract mutations; model-only no_data policy is retired."""
from pathlib import Path
import shutil, tempfile
ROOT = Path(__file__).resolve().parents[2]


PUMP = ROOT / 'examples/testfile_contracts/pump_loop'


EXPECTED = {'clean': (True, True, True, True, True), 'multi_segment': (True, True, True, True, True), 'stale_extractor': (False, True, True, False, False), 'added_field': (True, False, True, False, False), 'unclassified': (True, False, True, False, False), 'missing_evidence': (True, True, False, False, False), 'unknown_target': (True, True, False, False, False), 'stale_model': (True, True, True, False, False), 'review_required': (True, True, True, False, False)}

CASES = tuple(EXPECTED)


def assert_native_contract():
    import yaml
    from physicsguard.core.test_file_contract import check_test_file_contract,testfile_snapshot
    with tempfile.TemporaryDirectory() as directory:
        for index,case in enumerate(CASES):
            pump=Path(directory)/str(index)/'pump'
            shutil.copytree(PUMP,pump)
            if case in ('missing_evidence','unknown_target','review_required'):
                path=pump/'contracts/clean_contract.yaml'
                value=yaml.safe_load(path.read_text())
                field=value['fields']['flow_readback_kg_s']
                if case=='missing_evidence':
                    del field['evidence']
                elif case=='unknown_target':
                    field['target']='not_a_model_variable.x'
                else:
                    field['review_required']=True
                path.write_text(yaml.safe_dump(value))
            else:
                path=pump/f'contracts/{case}_contract.yaml'
            report=check_test_file_contract(path)
            codes={finding.type for finding in report.findings}
            actual=(
                not bool(codes & {'source_file_hash_mismatch','extractor_script_hash_mismatch','manifest_field_signature_mismatch'}),
                not bool(codes & {'field_unclassified','contract_field_missing','mapping_missing_target','ignored_without_reason'}),
                not bool(codes & {'mapping_missing_evidence','mapping_unknown_target','unit_not_convertible','conversion_disagrees_with_unit_table'}),
                report.ok,report.ok)
            wanted=EXPECTED[case]
            assert actual==wanted,(case,actual,wanted)
            if report.ok:
                testfile_snapshot(path,0)

