from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"
FIXTURE_PROVIDER = ROOT / "tests" / "fixtures" / "module_semantics_reviewer_provider.py"
FIXTURE_KEY_ID = "physicsguard.fixture.domain-reviewer.key.v1"
FIXTURE_RSA_MODULUS_B64URL = "tl4DW0cNL0WHa15VYW_g7F9h2n_7j32sGOH0Qc64NQrofOckMU9qa4eT5sROdWOOy5PQVVmEXcMpCnlmBeo-80CZn5U09xBipMjxyxzx0SoRpHP0Flmdj3h7bgnwACETqUlnZNrfDU3x8CiEeJVNialMbiODfBxATGBI1RR4zpBNI_W5CLqhWRnjhWokycMtlZwgkVSbQvkVY-KgCNk-HYbV8nzY1qI_X1Q5HvLIR9LNnbyJkX0TYzsyaVBvRyu-aVLjeDmbrMZZshKQn4qJVdsAcxfWKlzhsJZVBX2g5o1kEleEykegI1_XZaN-WXDPKjesFYvrXdZ1as2kArj1Xw"
FOREIGN_RSA_MODULUS_B64URL = "tIBbN4uDd1eok_uvwGdkKytxp319zXuOa0ZMD13mH0dMMRcgtMwoPFj0thEnRvF6QL8UAwWMC-LWYTmLaAASYsk3qedKPaYKgo2QvP4rqp86JAE9PzRdFOd6EpK6v-7Uu9Oc-P1a1AHlkNK0AzPbOOdFl2GRYBDrDoMGgew02EsaD_Qms1iGIrCuXWBS4WleHXWJOacYRChWQgY91Avqht3ApS596q_4U8SeGnKsFFo_lp5z7W_a4F19wYhS9SOk3AwVKIS8yLYSiNS3zxngdPeOh5_xO-X3u3fHf5jELe678O7QR0fyFtLbQx5mHP8XUwyEA6tHuLQZ_25pIk-gAw"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _checker() -> ModuleType:
    return _load(ROOT / "scripts" / "check_module_equation_ledger.py", "module_semantics_checker_for_producer_test")


@lru_cache(maxsize=1)
def _producer() -> ModuleType:
    return _load(ROOT / "scripts" / "module_semantics_review_producer.py", "module_semantics_review_producer_test")


@lru_cache(maxsize=1)
def _request() -> dict:
    review = _checker().review_ledger(
        ROOT,
        LEDGER,
        review_scope="module",
        module="ActuatorDeadZoneModule",
    )
    return review["record_results"][0]["review_request"]


@lru_cache(maxsize=1)
def _blocked_production() -> tuple[dict, dict]:
    return _producer().produce(
        _request(),
        command=[
            "python",
            "scripts/module_semantics_review_producer.py",
            "request.json",
            "--result",
            "result.json",
            "--receipt",
            "receipt.json",
        ],
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_registry(
    path: Path,
    *,
    mode: str = "accepted",
    tool_sha256: str | None = None,
    provider_id: str = "physicsguard.fixture.domain-reviewer.v1",
    owner: str = "physicsguard.fixture.domain-reviewer.owner",
    modulus_b64url: str = FIXTURE_RSA_MODULUS_B64URL,
    key_id: str = FIXTURE_KEY_ID,
) -> None:
    payload = {
        "schema": _producer().REVIEWER_PROVIDER_REGISTRY_SCHEMA,
        "active_provider_id": provider_id,
        "providers": [
            {
                "provider_id": provider_id,
                "execution_owner": owner,
                "tool_path": str(FIXTURE_PROVIDER),
                "tool_sha256": tool_sha256 or _sha256(FIXTURE_PROVIDER),
                "command": [
                    sys.executable,
                    str(FIXTURE_PROVIDER),
                    "--mode",
                    mode,
                ],
                "timeout_seconds": 30,
                "public_key": {
                    "algorithm": _producer().REVIEWER_PROVIDER_SIGNATURE_ALGORITHM,
                    "key_id": key_id,
                    "modulus_b64url": modulus_b64url,
                    "exponent": 65537,
                },
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _all_machine_dimensions_pass(request: dict, authority: dict) -> dict:
    producer = _producer()
    candidate = copy.deepcopy(request)
    candidate["reviewer_provider_authority"] = authority
    for identity in producer.DIMENSIONS[:-1]:
        candidate["dimensions"][identity]["status"] = "pass"
        candidate["dimensions"][identity]["finding_count"] = 0
        candidate["dimensions"][identity]["findings_fingerprint"] = producer._canonical_hash([])
    candidate["dimensions"]["independent_review"]["status"] = "not_run"
    candidate["dimensions"]["independent_review"]["finding_count"] = 0
    candidate["dimensions"]["independent_review"]["findings_fingerprint"] = producer._canonical_hash([])
    candidate["request_fingerprint"] = producer._canonical_hash(producer._request_body(candidate))
    return candidate


def _fixture_request(
    monkeypatch,
    tmp_path: Path,
    *,
    mode: str = "accepted",
    modulus_b64url: str = FIXTURE_RSA_MODULUS_B64URL,
    key_id: str = FIXTURE_KEY_ID,
) -> tuple[dict, Path]:
    registry = tmp_path / "reviewer-provider-registry.json"
    _write_registry(
        registry,
        mode=mode,
        modulus_b64url=modulus_b64url,
        key_id=key_id,
    )
    producer = _producer()
    checker = _checker()
    monkeypatch.setattr(producer, "REVIEWER_PROVIDER_REGISTRY_PATH", str(registry))
    monkeypatch.setattr(checker, "REVIEWER_PROVIDER_REGISTRY_PATH", str(registry))
    authority = producer._reviewer_provider_authority(ROOT)
    assert authority["status"] == "ready"
    return _all_machine_dimensions_pass(_request(), authority), registry


def _canonical_command() -> list[str]:
    return [
        "python",
        "scripts/module_semantics_review_producer.py",
        "request.json",
        "--result",
        "result.json",
        "--receipt",
        "receipt.json",
    ]


def _fake_signature() -> str:
    return base64.urlsafe_b64encode(bytes(256)).rstrip(b"=").decode("ascii")


def _provider_terminal_subject(
    execution_request: dict,
    result: dict,
    receipt: dict,
) -> dict:
    receipt_body = {
        key: value
        for key, value in receipt.items()
        if key not in {"terminal_attestation", "receipt_fingerprint"}
    }
    return {
        "schema": _producer().REVIEWER_PROVIDER_TERMINAL_SUBJECT_SCHEMA,
        "execution_request": execution_request,
        "result": result,
        "receipt": receipt_body,
    }


def _rehash_public_provider_and_outer_layers(
    request: dict,
    evidence: dict,
) -> tuple[dict, dict]:
    """Recompute every public hash without access to the provider private key."""

    producer = _producer()
    checker = _checker()
    provider_result = evidence["result"]
    provider_receipt = evidence["receipt"]
    provider_result_body = {
        key: value
        for key, value in provider_result.items()
        if key != "output_fingerprint"
    }
    provider_result_fingerprint = producer._canonical_hash(provider_result_body)
    provider_result["output_fingerprint"] = provider_result_fingerprint
    provider_receipt["result_fingerprint"] = provider_result_fingerprint
    terminal_subject = _provider_terminal_subject(
        provider_receipt["execution_request"],
        provider_result,
        provider_receipt,
    )
    terminal_subject_fingerprint = producer._canonical_hash(terminal_subject)
    provider_receipt["terminal_attestation"][
        "subject_fingerprint"
    ] = terminal_subject_fingerprint
    provider_receipt_subject = {
        key: value
        for key, value in provider_receipt.items()
        if key != "receipt_fingerprint"
    }
    provider_receipt_fingerprint = producer._canonical_hash(
        provider_receipt_subject
    )
    provider_receipt["receipt_fingerprint"] = provider_receipt_fingerprint
    provider_stage = {
        "status": "success",
        "reviewer_execution_owner": provider_result["execution_owner"],
        "execution_request_fingerprint": provider_result[
            "execution_request_fingerprint"
        ],
        "terminal_subject_fingerprint": terminal_subject_fingerprint,
        "result_fingerprint": provider_result_fingerprint,
        "receipt_fingerprint": provider_receipt_fingerprint,
        "producer_command": provider_receipt["execution_request"][
            "producer_command"
        ],
        "domain_findings": provider_result["domain_findings"],
        "disposition": provider_result["disposition"],
    }
    return checker._derive_accepted_external_review_artifacts(
        ROOT,
        request,
        evidence,
        provider_stage,
    )


def _synthesize_unsigned_accepted_artifacts(request: dict) -> tuple[dict, dict]:
    """Build structurally complete accepted artifacts without running either owner."""

    producer = _producer()
    checker = _checker()
    authority = request["reviewer_provider_authority"]
    provider = authority["provider"]
    provider_command = [
        *provider["command"],
        "synthetic-execution-request.json",
        "--result",
        "synthetic-result.json",
        "--receipt",
        "synthetic-receipt.json",
    ]
    execution_body = {
        "schema": producer.REVIEWER_PROVIDER_EXECUTION_REQUEST_SCHEMA,
        "review_request": request,
        "provider_authority": authority,
        "provider_command": provider_command,
        "producer_command": _canonical_command(),
    }
    execution_request = {
        **execution_body,
        "execution_request_fingerprint": producer._canonical_hash(execution_body),
    }
    provider_tool = {
        "path": provider["tool_path"],
        "sha256": provider["tool_sha256"],
    }
    provider_result_body = {
        "schema": producer.REVIEWER_PROVIDER_RESULT_SCHEMA,
        "provider_id": provider["provider_id"],
        "execution_owner": provider["execution_owner"],
        "provider_tool": provider_tool,
        "registry_fingerprint": authority["registry"]["fingerprint"],
        "execution_request_fingerprint": execution_request[
            "execution_request_fingerprint"
        ],
        "request_fingerprint": request["request_fingerprint"],
        "domain_findings": [],
        "disposition": "accepted",
        "terminal_status": "success",
    }
    provider_result_fingerprint = producer._canonical_hash(provider_result_body)
    provider_result = {
        **provider_result_body,
        "output_fingerprint": provider_result_fingerprint,
    }
    provider_receipt_body = {
        "schema": producer.REVIEWER_PROVIDER_RECEIPT_SCHEMA,
        "provider_id": provider["provider_id"],
        "execution_owner": provider["execution_owner"],
        "provider_tool": provider_tool,
        "registry_fingerprint": authority["registry"]["fingerprint"],
        "execution_request_fingerprint": execution_request[
            "execution_request_fingerprint"
        ],
        "request_fingerprint": request["request_fingerprint"],
        "result_fingerprint": provider_result_fingerprint,
        "execution_request": execution_request,
        "command": provider_command,
        "exit_status": 0,
        "terminal_status": "success",
        "disposition": "accepted",
        "receipt_id": f"synthetic-review-{provider_result_fingerprint[:16]}",
    }
    terminal_subject = {
        "schema": producer.REVIEWER_PROVIDER_TERMINAL_SUBJECT_SCHEMA,
        "execution_request": execution_request,
        "result": provider_result,
        "receipt": provider_receipt_body,
    }
    terminal_subject_fingerprint = producer._canonical_hash(terminal_subject)
    provider_receipt_subject = {
        **provider_receipt_body,
        "terminal_attestation": {
            "schema": producer.REVIEWER_PROVIDER_ATTESTATION_SCHEMA,
            "algorithm": producer.REVIEWER_PROVIDER_SIGNATURE_ALGORITHM,
            "key_id": provider["public_key"]["key_id"],
            "subject_fingerprint": terminal_subject_fingerprint,
            "signature_b64url": _fake_signature(),
        },
    }
    provider_receipt = {
        **provider_receipt_subject,
        "receipt_fingerprint": producer._canonical_hash(provider_receipt_subject),
    }
    evidence = {"result": provider_result, "receipt": provider_receipt}
    provider_stage = {
        "status": "success",
        "reviewer_execution_owner": provider["execution_owner"],
        "execution_request_fingerprint": execution_request[
            "execution_request_fingerprint"
        ],
        "terminal_subject_fingerprint": terminal_subject_fingerprint,
        "result_fingerprint": provider_result_fingerprint,
        "receipt_fingerprint": provider_receipt["receipt_fingerprint"],
        "producer_command": _canonical_command(),
        "domain_findings": [],
        "disposition": "accepted",
    }
    return checker._derive_accepted_external_review_artifacts(
        ROOT,
        request,
        evidence,
        provider_stage,
    )


def _rebind_accepted_artifacts_to_request(
    request: dict,
    result: dict,
    receipt: dict,
) -> tuple[dict, dict]:
    producer = _producer()
    rebound_result = copy.deepcopy(result)
    rebound_receipt = copy.deepcopy(receipt)
    provider_result = rebound_result["reviewer_provider_evidence"]["result"]
    provider_receipt = rebound_result["reviewer_provider_evidence"]["receipt"]
    provider_result["request_fingerprint"] = request["request_fingerprint"]
    provider_result_body = {
        key: value for key, value in provider_result.items() if key != "output_fingerprint"
    }
    provider_result_fingerprint = producer._canonical_hash(provider_result_body)
    provider_result["output_fingerprint"] = provider_result_fingerprint
    provider_receipt["request_fingerprint"] = request["request_fingerprint"]
    provider_receipt["result_fingerprint"] = provider_result_fingerprint
    provider_receipt_body = {
        key: value for key, value in provider_receipt.items() if key != "receipt_fingerprint"
    }
    provider_receipt_fingerprint = producer._canonical_hash(provider_receipt_body)
    provider_receipt["receipt_fingerprint"] = provider_receipt_fingerprint
    rebound_result["request_fingerprint"] = request["request_fingerprint"]
    rebound_result["dimensions"] = request["dimensions"]
    rebound_result["reviewer_provider_result_fingerprint"] = provider_result_fingerprint
    rebound_result["reviewer_provider_receipt_fingerprint"] = provider_receipt_fingerprint
    rebound_result_body = {
        key: value for key, value in rebound_result.items() if key != "output_fingerprint"
    }
    rebound_result_fingerprint = producer._canonical_hash(rebound_result_body)
    rebound_result["output_fingerprint"] = rebound_result_fingerprint
    rebound_receipt["request_fingerprint"] = request["request_fingerprint"]
    rebound_receipt["result_fingerprint"] = rebound_result_fingerprint
    rebound_receipt["reviewer_provider_result_fingerprint"] = provider_result_fingerprint
    rebound_receipt["reviewer_provider_receipt_fingerprint"] = provider_receipt_fingerprint
    rebound_receipt_body = {
        key: value for key, value in rebound_receipt.items() if key != "receipt_fingerprint"
    }
    rebound_receipt["receipt_fingerprint"] = producer._canonical_hash(rebound_receipt_body)
    return rebound_result, rebound_receipt


def test_canonical_producer_replays_frozen_request_but_cannot_self_accept() -> None:
    producer = _producer()
    result, receipt = _blocked_production()

    assert result["schema"] == producer.RESULT_SCHEMA
    assert result["producer_identity"] == producer.PRODUCER_IDENTITY
    assert result["request_fingerprint"] == _request()["request_fingerprint"]
    assert result["terminal_status"] == "success"
    assert result["disposition"] == "blocked"
    assert result["reviewer_execution_owner"] is None
    assert any(
        finding["code"] == "reviewer_provider_invalid"
        for finding in result["producer_findings"]
    )
    assert result["reviewer_provider_authority"]["status"] == "no_provider"
    assert result["reviewer_provider_evidence"] is None
    assert receipt["schema"] == producer.RECEIPT_SCHEMA
    assert receipt["terminal_status"] == "success"
    assert receipt["disposition"] == "blocked"
    assert receipt["result_fingerprint"] == result["output_fingerprint"]
    assert receipt["receipt_fingerprint"] == producer._canonical_hash(
        {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}
    )


def test_retired_caller_reviewer_execution_option_has_no_cli_reader() -> None:
    with pytest.raises(SystemExit) as exc_info:
        _producer().main(
            [
                "request.json",
                "--reviewer-execution",
                "caller.json",
                "--result",
                "result.json",
                "--receipt",
                "receipt.json",
            ]
        )

    assert exc_info.value.code == 2


def test_unregistered_distinct_owner_mapping_cannot_authorize_all_pass_request(
    monkeypatch,
) -> None:
    producer = _producer()
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])
    caller_authority = {
        "schema": producer.REVIEWER_PROVIDER_AUTHORITY_SCHEMA,
        "registry": {
            "schema": producer.REVIEWER_PROVIDER_REGISTRY_SCHEMA,
            "path": "caller-authored.json",
            "fingerprint": "0" * 64,
        },
        "status": "ready",
        "provider": {
            "provider_id": "physicsguard.caller.fake-provider",
            "execution_owner": "physicsguard.caller.different-owner",
            "tool_path": "caller.py",
            "tool_sha256": "0" * 64,
            "command": ["python", "caller.py"],
            "timeout_seconds": 30,
        },
        "findings": [],
    }
    request = _all_machine_dimensions_pass(_request(), caller_authority)

    result, receipt = producer.produce(
        request,
        command=["canonical-producer-test"],
    )

    assert result["reviewer_execution_owner"] is None
    assert result["disposition"] == "blocked"
    assert receipt["disposition"] == "blocked"
    assert any(
        finding["code"] == "machine_replay_failed"
        and "current closed reviewer provider registry" in finding["message"]
        for finding in result["producer_findings"]
    )


def test_checker_validates_canonical_blocked_terminal_artifacts_without_promoting() -> None:
    result, receipt = _blocked_production()
    request = _request()

    stage = _checker()._validate_external_review_evidence(
        request,
        {"result": result, "receipt": receipt},
        root=ROOT,
        author=request["record_subject"]["provenance"]["author_owner"],
    )

    assert stage["status"] == "blocked"
    assert stage["producer_identity"] == _producer().PRODUCER_IDENTITY
    assert stage["disposition"] == "blocked"


def test_registered_provider_is_actually_executed_and_can_accept(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(monkeypatch, tmp_path)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])

    result, receipt = producer.produce(request, command=_canonical_command())

    assert result["disposition"] == "accepted"
    assert result["producer_findings"] == []
    assert result["reviewer_provider_evidence"]["result"]["disposition"] == "accepted"
    assert result["reviewer_provider_evidence"]["receipt"]["exit_status"] == 0
    stage = _checker()._validate_external_review_evidence(
        request,
        {"result": result, "receipt": receipt},
        root=ROOT,
        author=request["record_subject"]["provenance"]["author_owner"],
    )
    assert stage["status"] == "success"
    assert stage["disposition"] == "accepted"


def test_checker_rejects_caller_rehashed_accepted_pair_with_blocked_dimension(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(monkeypatch, tmp_path)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])
    result, receipt = producer.produce(request, command=_canonical_command())
    blocked_request = copy.deepcopy(request)
    blocked_request["dimensions"]["unit"]["status"] = "blocked"
    blocked_request["dimensions"]["unit"]["finding_count"] = 1
    blocked_request["request_fingerprint"] = producer._canonical_hash(
        producer._request_body(blocked_request)
    )
    forged_result, forged_receipt = _rebind_accepted_artifacts_to_request(
        blocked_request, result, receipt
    )

    stage = _checker()._validate_external_review_evidence(
        blocked_request,
        {"result": forged_result, "receipt": forged_receipt},
        root=ROOT,
        author=blocked_request["record_subject"]["provenance"]["author_owner"],
    )

    assert stage["status"] == "fail"
    assert "blocked machine-decidable dimension" in stage["error"]


@pytest.mark.parametrize(
    "mode",
    [
        "foreign-provider",
        "owner-mismatch",
        "tool-mismatch",
        "registry-mismatch",
        "request-mismatch",
        "execution-request-mismatch",
        "result-mismatch",
        "result-hash-mismatch",
        "receipt-hash-mismatch",
        "command-mismatch",
        "exit-mismatch",
        "nonzero-exit",
    ],
)
def test_registered_provider_mismatch_remains_blocked(
    monkeypatch,
    tmp_path: Path,
    mode: str,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(monkeypatch, tmp_path, mode=mode)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])

    result, receipt = producer.produce(request, command=_canonical_command())

    assert result["disposition"] == "blocked"
    assert receipt["disposition"] == "blocked"
    assert any(
        finding["code"] == "reviewer_provider_invalid"
        for finding in result["producer_findings"]
    )


def test_stale_registered_provider_tool_never_runs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry = tmp_path / "reviewer-provider-registry.json"
    _write_registry(registry, tool_sha256="0" * 64)
    producer = _producer()
    monkeypatch.setattr(producer, "REVIEWER_PROVIDER_REGISTRY_PATH", str(registry))
    authority = producer._reviewer_provider_authority(ROOT)
    assert authority["status"] == "invalid"
    request = _all_machine_dimensions_pass(_request(), authority)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])

    result, _ = producer.produce(request, command=_canonical_command())

    assert result["disposition"] == "blocked"
    assert any(
        "tool fingerprint is stale" in finding["message"]
        for finding in result["producer_findings"]
    )


def test_registry_change_after_request_freeze_blocks_replay(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, registry = _fixture_request(monkeypatch, tmp_path)
    _write_registry(registry, provider_id="physicsguard.fixture.replaced-provider.v1")
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])

    result, _ = producer.produce(request, command=_canonical_command())

    assert result["disposition"] == "blocked"
    assert any(
        "current closed reviewer provider registry" in finding["message"]
        for finding in result["producer_findings"]
    )


def test_checker_rejects_unpublished_execution_fingerprint_after_all_public_rehashes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(monkeypatch, tmp_path)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])
    signed_result, _ = producer.produce(request, command=_canonical_command())
    evidence = copy.deepcopy(signed_result["reviewer_provider_evidence"])
    unpublished_fingerprint = "f" * 64
    evidence["receipt"]["execution_request"][
        "execution_request_fingerprint"
    ] = unpublished_fingerprint
    evidence["result"][
        "execution_request_fingerprint"
    ] = unpublished_fingerprint
    evidence["receipt"][
        "execution_request_fingerprint"
    ] = unpublished_fingerprint
    forged_result, forged_receipt = _rehash_public_provider_and_outer_layers(
        request,
        evidence,
    )

    stage = _checker()._validate_external_review_evidence(
        request,
        {"result": forged_result, "receipt": forged_receipt},
        root=ROOT,
        author=request["record_subject"]["provenance"]["author_owner"],
    )

    assert stage["status"] == "fail"
    assert "execution-request fingerprint is invalid" in stage["error"]
    assert "terminal subject signature is invalid" in stage["error"]


def test_checker_rejects_pure_synthesis_without_provider_or_producer_execution(
    monkeypatch,
    tmp_path: Path,
) -> None:
    request, _ = _fixture_request(monkeypatch, tmp_path)
    forged_result, forged_receipt = _synthesize_unsigned_accepted_artifacts(
        request
    )

    stage = _checker()._validate_external_review_evidence(
        request,
        {"result": forged_result, "receipt": forged_receipt},
        root=ROOT,
        author=request["record_subject"]["provenance"]["author_owner"],
    )

    assert stage["status"] == "fail"
    assert "terminal subject signature is invalid" in stage["error"]


def test_checker_rejects_copied_signed_result_with_rewritten_outer_receipt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(monkeypatch, tmp_path)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])
    result, signed_receipt = producer.produce(
        request,
        command=_canonical_command(),
    )
    copied_receipt = copy.deepcopy(signed_receipt)
    copied_receipt["receipt_id"] = "module-review-copied-by-caller"
    copied_receipt["command"] = [
        "python",
        "scripts/module_semantics_review_producer.py",
        "copied-request.json",
        "--result",
        "copied-result.json",
        "--receipt",
        "copied-receipt.json",
    ]
    copied_receipt_subject = {
        key: value
        for key, value in copied_receipt.items()
        if key != "receipt_fingerprint"
    }
    copied_receipt["receipt_fingerprint"] = producer._canonical_hash(
        copied_receipt_subject
    )

    stage = _checker()._validate_external_review_evidence(
        request,
        {"result": result, "receipt": copied_receipt},
        root=ROOT,
        author=request["record_subject"]["provenance"]["author_owner"],
    )

    assert stage["status"] == "fail"
    assert "exact deterministic projection" in stage["error"]


def test_checker_rejects_copied_signed_provider_terminal_with_rewritten_receipt_and_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(monkeypatch, tmp_path)
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])
    signed_result, _ = producer.produce(request, command=_canonical_command())
    evidence = copy.deepcopy(signed_result["reviewer_provider_evidence"])
    provider_receipt = evidence["receipt"]
    execution_request = provider_receipt["execution_request"]
    copied_provider_command = [
        *request["reviewer_provider_authority"]["provider"]["command"],
        "copied-provider-request.json",
        "--result",
        "copied-provider-result.json",
        "--receipt",
        "copied-provider-receipt.json",
    ]
    execution_request["provider_command"] = copied_provider_command
    execution_body = {
        key: value
        for key, value in execution_request.items()
        if key != "execution_request_fingerprint"
    }
    copied_execution_fingerprint = producer._canonical_hash(execution_body)
    execution_request[
        "execution_request_fingerprint"
    ] = copied_execution_fingerprint
    evidence["result"][
        "execution_request_fingerprint"
    ] = copied_execution_fingerprint
    provider_receipt[
        "execution_request_fingerprint"
    ] = copied_execution_fingerprint
    provider_receipt["command"] = copied_provider_command
    provider_receipt["receipt_id"] = "fixture-review-copied-by-caller"
    forged_result, forged_receipt = _rehash_public_provider_and_outer_layers(
        request,
        evidence,
    )

    stage = _checker()._validate_external_review_evidence(
        request,
        {"result": forged_result, "receipt": forged_receipt},
        root=ROOT,
        author=request["record_subject"]["provenance"]["author_owner"],
    )

    assert stage["status"] == "fail"
    assert "terminal subject signature is invalid" in stage["error"]


def test_fixture_private_key_cannot_authorize_a_different_registry_public_key(
    monkeypatch,
    tmp_path: Path,
) -> None:
    producer = _producer()
    request, _ = _fixture_request(
        monkeypatch,
        tmp_path,
        modulus_b64url=FOREIGN_RSA_MODULUS_B64URL,
    )
    monkeypatch.setattr(producer, "_replay_request", lambda request: [])

    result, receipt = producer.produce(
        request,
        command=_canonical_command(),
    )

    assert result["disposition"] == "blocked"
    assert receipt["disposition"] == "blocked"
    assert any(
        finding["code"] == "reviewer_provider_invalid"
        and "terminal subject signature is invalid" in finding["message"]
        for finding in result["producer_findings"]
    )
