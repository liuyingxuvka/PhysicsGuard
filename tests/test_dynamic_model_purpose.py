from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from physicsguard.guard_model_contract import (
    DYNAMIC_ROLE,
    GuardModelContractError,
    execute_dynamic_proofs,
    validate_dynamic_candidate_binding,
    validate_dynamic_closure,
    validate_dynamic_contract_bundle,
)


def _canonical_fingerprint(value: object) -> str:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_current_model(root: Path) -> dict[str, Path]:
    authority = root / ".physicsguard" / "model-purpose" / "demo"
    model = root / "models" / "demo.model"
    model.parent.mkdir(parents=True)
    model.write_text("candidate-v1\n", encoding="utf-8")
    runner = root / "tools" / "native_oracle.py"
    runner.parent.mkdir(parents=True)
    runner.write_text(
        """from __future__ import annotations
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', required=True)
parser.add_argument('--fixture', required=True)
parser.add_argument('--oracle-id', required=True)
parser.add_argument('--case-id', required=True)
args = parser.parse_args()
fixture = json.loads(Path(args.fixture).read_text(encoding='utf-8'))
candidate = Path(args.candidate).read_text(encoding='utf-8').strip()
status = fixture['status'] if candidate == fixture['expected_candidate'] else 'blocked'
result = {
    'schema_version': 'physicsguard.native_model_oracle_result.v1',
    'native_owner_id': 'physicsguard-native-demo',
    'oracle_id': args.oracle_id,
    'case_id': args.case_id,
    'status': status,
    'finding_codes': fixture['finding_codes'] if status == 'blocked' else [],
}
print(json.dumps(result, sort_keys=True))
""",
        encoding="utf-8",
    )
    good_fixture = root / "fixtures" / "good.json"
    bad_fixture = root / "fixtures" / "bad.json"
    _write_json(
        good_fixture,
        {"status": "pass", "expected_candidate": "candidate-v1", "finding_codes": []},
    )
    _write_json(
        bad_fixture,
        {
            "status": "blocked",
            "expected_candidate": "candidate-v1",
            "finding_codes": ["energy_balance_exceeded"],
        },
    )
    contract = {
        "schema_version": "physicsguard.model_purpose_contract.v1",
        "artifact_role": DYNAMIC_ROLE,
        "model_id": "model:demo",
        "native_owner_id": "physicsguard-native-demo",
        "native_route_id": "route:energy-balance",
        "prevented_failure_purpose": "Prevent this pump model from accepting a run whose energy balance exceeds the declared envelope.",
        "physical_or_evidence_boundary": [
            {
                "boundary_id": "boundary:demo:energy",
                "description": "Input power, output power, and loss are measured in watts for the declared pump operating envelope.",
            }
        ],
        "prevented_failure_classes": [
            {
                "failure_id": "failure:demo:energy-balance",
                "title": "Energy balance exceeds the modeled physical envelope",
                "block_when": "absolute input-output-loss residual exceeds the declared tolerance",
                "expected_finding_code": "energy_balance_exceeded",
                "proof_strength": "native_semantic_detection",
                "known_limit": "The proof covers only the declared fixture envelope and tolerance.",
                "claim_boundary": "Blocks this residual violation; it does not prove all pump physics.",
            }
        ],
        "claim_boundary": "The model is licensed only for the declared energy-balance envelope.",
        "authoring_order": [
            "freeze_current_model_purpose",
            "build_candidate",
            "prove_known_good",
            "prove_every_known_bad",
            "issue_current_model_receipt",
        ],
    }
    contract_fingerprint = _canonical_fingerprint(contract)
    oracle_id = "oracle:demo:energy-balance"
    oracles = {
        "schema_version": "physicsguard.model_native_oracle_set.v1",
        "artifact_role": DYNAMIC_ROLE,
        "model_id": "model:demo",
        "purpose_contract_fingerprint": contract_fingerprint,
        "oracles": [
            {
                "oracle_id": oracle_id,
                "failure_id": "failure:demo:energy-balance",
                "native_owner_id": "physicsguard-native-demo",
                "expected_finding_code": "energy_balance_exceeded",
                "runner_ref": "tools/native_oracle.py",
                "runner_fingerprint": _file_fingerprint(runner),
            }
        ],
    }
    good = {
        "schema_version": "physicsguard.model_known_good_set.v1",
        "artifact_role": DYNAMIC_ROLE,
        "model_id": "model:demo",
        "purpose_contract_fingerprint": contract_fingerprint,
        "cases": [
            {
                "case_id": "case:demo:good:energy",
                "failure_id": "failure:demo:energy-balance",
                "oracle_id": oracle_id,
                "fixture_ref": "fixtures/good.json",
                "fixture_fingerprint": _file_fingerprint(good_fixture),
                "expected_native_status": "pass",
                "self_reported_outcome_allowed": False,
            }
        ],
    }
    bad = {
        "schema_version": "physicsguard.model_known_bad_set.v1",
        "artifact_role": DYNAMIC_ROLE,
        "model_id": "model:demo",
        "purpose_contract_fingerprint": contract_fingerprint,
        "cases": [
            {
                "case_id": "case:demo:bad:energy",
                "failure_id": "failure:demo:energy-balance",
                "oracle_id": oracle_id,
                "fixture_ref": "fixtures/bad.json",
                "fixture_fingerprint": _file_fingerprint(bad_fixture),
                "expected_native_status": "blocked",
                "expected_finding_code": "energy_balance_exceeded",
                "self_reported_outcome_allowed": False,
            }
        ],
    }
    purpose_event = {
        "event_id": "event:model:demo:purpose-contract-frozen",
        "sequence": 1,
        "event_kind": "purpose_contract_frozen",
        "purpose_contract_fingerprint": contract_fingerprint,
    }
    candidate = {
        "schema_version": "physicsguard.model_candidate_binding.v1",
        "artifact_role": DYNAMIC_ROLE,
        "model_id": "model:demo",
        "candidate_id": "candidate:demo:v1",
        "purpose_contract_ref": ".physicsguard/model-purpose/demo/contract.json",
        "purpose_contract_fingerprint": contract_fingerprint,
        "protected_failure_ids": ["failure:demo:energy-balance"],
        "candidate_artifact_ref": "models/demo.model",
        "candidate_artifact_fingerprint": _file_fingerprint(model),
        "authoring_events": [
            purpose_event,
            {
                "event_id": "event:model:demo:candidate-built",
                "sequence": 2,
                "event_kind": "candidate_built",
                "purpose_contract_fingerprint": contract_fingerprint,
                "previous_event_fingerprint": _canonical_fingerprint(purpose_event),
                "candidate_id": "candidate:demo:v1",
                "candidate_artifact_fingerprint": _file_fingerprint(model),
                "protected_failure_ids": ["failure:demo:energy-balance"],
            },
        ],
    }
    values = {
        "contract": contract,
        "oracles": oracles,
        "known-good": good,
        "known-bad": bad,
        "candidate": candidate,
    }
    paths = {name: authority / f"{name}.json" for name in values}
    for name, value in values.items():
        _write_json(paths[name], value)
    paths["proofs"] = authority / "proofs.json"
    paths["model"] = model
    return paths


def _contract_bundle(root: Path, paths: dict[str, Path]) -> dict[str, object]:
    return validate_dynamic_contract_bundle(
        root,
        paths["contract"],
        paths["oracles"],
        paths["known-good"],
        paths["known-bad"],
    )


def test_current_model_declares_binds_proves_and_closes(tmp_path: Path) -> None:
    paths = _build_current_model(tmp_path)
    bundle = _contract_bundle(tmp_path, paths)
    bundle = validate_dynamic_candidate_binding(tmp_path, paths["candidate"], bundle)
    proof_set = execute_dynamic_proofs(bundle, paths["proofs"])
    closed = validate_dynamic_closure(bundle, paths["proofs"])

    assert bundle["artifact_role"] == DYNAMIC_ROLE
    assert proof_set["artifact_role"] == DYNAMIC_ROLE
    assert [row["native_status"] for row in proof_set["results"]] == [
        "pass",
        "blocked",
    ]
    assert closed["proof_result_count"] == 2


def test_dynamic_contract_rejects_baseline_and_empty_failure_universe(
    tmp_path: Path,
) -> None:
    paths = _build_current_model(tmp_path)
    contract = json.loads(paths["contract"].read_text(encoding="utf-8"))
    contract["artifact_role"] = "family_baseline_regression"
    _write_json(paths["contract"], contract)
    with pytest.raises(GuardModelContractError, match="not_current_model_purpose"):
        _contract_bundle(tmp_path, paths)

    paths = _build_current_model(tmp_path / "empty")
    contract = json.loads(paths["contract"].read_text(encoding="utf-8"))
    contract["prevented_failure_classes"] = []
    _write_json(paths["contract"], contract)
    with pytest.raises(GuardModelContractError, match="at_least_one_dynamic"):
        _contract_bundle(tmp_path / "empty", paths)


def test_current_candidate_order_and_model_content_are_freshness_inputs(
    tmp_path: Path,
) -> None:
    paths = _build_current_model(tmp_path)
    bundle = _contract_bundle(tmp_path, paths)
    candidate = json.loads(paths["candidate"].read_text(encoding="utf-8"))
    candidate["authoring_events"] = list(reversed(candidate["authoring_events"]))
    _write_json(paths["candidate"], candidate)
    with pytest.raises(GuardModelContractError, match="event_chain_broken"):
        validate_dynamic_candidate_binding(tmp_path, paths["candidate"], bundle)

    paths = _build_current_model(tmp_path / "stale")
    bundle = _contract_bundle(tmp_path / "stale", paths)
    paths["model"].write_text("candidate-v2\n", encoding="utf-8")
    with pytest.raises(GuardModelContractError, match="artifact_fingerprint_mismatch"):
        validate_dynamic_candidate_binding(
            tmp_path / "stale", paths["candidate"], bundle
        )


def test_every_failure_needs_cases_and_every_proof_remains_bound(tmp_path: Path) -> None:
    paths = _build_current_model(tmp_path)
    bad = json.loads(paths["known-bad"].read_text(encoding="utf-8"))
    bad["cases"] = []
    _write_json(paths["known-bad"], bad)
    with pytest.raises(GuardModelContractError, match="known_bad_cases_required"):
        _contract_bundle(tmp_path, paths)

    paths = _build_current_model(tmp_path / "proof")
    bundle = _contract_bundle(tmp_path / "proof", paths)
    bundle = validate_dynamic_candidate_binding(
        tmp_path / "proof", paths["candidate"], bundle
    )
    execute_dynamic_proofs(bundle, paths["proofs"])
    proof_set = json.loads(paths["proofs"].read_text(encoding="utf-8"))
    proof_set["results"] = proof_set["results"][:-1]
    _write_json(paths["proofs"], proof_set)
    with pytest.raises(GuardModelContractError, match="not_exhaustive"):
        validate_dynamic_closure(bundle, paths["proofs"])


def test_current_authority_cannot_escape_explicit_target_root(tmp_path: Path) -> None:
    target = tmp_path / "target"
    outside = tmp_path / "outside"
    paths = _build_current_model(target)
    copied = outside / "contract.json"
    copied.parent.mkdir()
    copied.write_text(paths["contract"].read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(GuardModelContractError, match="outside_target_root"):
        validate_dynamic_contract_bundle(
            target,
            copied,
            paths["oracles"],
            paths["known-good"],
            paths["known-bad"],
        )
