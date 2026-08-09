from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "check_module_equation_ledger.py"
PRODUCER_IDENTITY = "physicsguard.module_semantics_review_producer.v1"
REQUEST_SCHEMA = "physicsguard.module_semantics_review_request.v1"
RESULT_SCHEMA = "physicsguard.module_semantics_review_result.v1"
RECEIPT_SCHEMA = "physicsguard.module_semantics_review_receipt.v1"
REVIEWER_PROVIDER_REGISTRY_SCHEMA = "physicsguard.module_semantics_reviewer_provider_registry.v1"
REVIEWER_PROVIDER_AUTHORITY_SCHEMA = "physicsguard.module_semantics_reviewer_provider_authority.v1"
REVIEWER_PROVIDER_EXECUTION_REQUEST_SCHEMA = "physicsguard.module_semantics_reviewer_provider_execution_request.v1"
REVIEWER_PROVIDER_RESULT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_result.v1"
REVIEWER_PROVIDER_RECEIPT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_receipt.v1"
REVIEWER_PROVIDER_TERMINAL_SUBJECT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_terminal_subject.v1"
REVIEWER_PROVIDER_ATTESTATION_SCHEMA = "physicsguard.module_semantics_reviewer_provider_attestation.v1"
REVIEWER_PROVIDER_SIGNATURE_ALGORITHM = "rsassa-pkcs1-v1_5-sha256"
REVIEWER_PROVIDER_REGISTRY_PATH = ".physicsguard/module_semantics_reviewer_provider_registry.json"
DIMENSIONS = (
    "registry_inventory",
    "function_block",
    "equation_dependency",
    "unit",
    "constraint_valid_region",
    "behavioral_test",
    "counterexample",
    "independent_oracle",
    "independent_review",
)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_checker() -> Any:
    spec = importlib.util.spec_from_file_location(
        "physicsguard_module_semantics_checker_for_producer", CHECKER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical checker cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _request_body(request: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in request.items()
        if key not in {"request_id", "request_fingerprint"}
    }


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _b64url_decode(value: Any) -> bytes | None:
    if not _nonempty_string(value) or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in value
    ):
        return None
    try:
        return base64.urlsafe_b64decode(str(value) + "=" * (-len(str(value)) % 4))
    except (ValueError, TypeError):
        return None


def _valid_provider_public_key(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "algorithm",
        "key_id",
        "modulus_b64url",
        "exponent",
    }:
        return False
    modulus = _b64url_decode(value.get("modulus_b64url"))
    exponent = value.get("exponent")
    return (
        value.get("algorithm") == REVIEWER_PROVIDER_SIGNATURE_ALGORITHM
        and _nonempty_string(value.get("key_id"))
        and isinstance(modulus, bytes)
        and len(modulus) >= 256
        and isinstance(exponent, int)
        and not isinstance(exponent, bool)
        and exponent >= 3
        and exponent % 2 == 1
    )


def _verify_provider_attestation(
    subject: dict[str, Any],
    attestation: Any,
    public_key: Any,
) -> bool:
    if not _valid_provider_public_key(public_key):
        return False
    if not isinstance(attestation, dict) or set(attestation) != {
        "schema",
        "algorithm",
        "key_id",
        "subject_fingerprint",
        "signature_b64url",
    }:
        return False
    if (
        attestation.get("schema") != REVIEWER_PROVIDER_ATTESTATION_SCHEMA
        or attestation.get("algorithm") != public_key.get("algorithm")
        or attestation.get("key_id") != public_key.get("key_id")
        or attestation.get("subject_fingerprint") != _canonical_hash(subject)
    ):
        return False
    modulus_bytes = _b64url_decode(public_key.get("modulus_b64url"))
    signature = _b64url_decode(attestation.get("signature_b64url"))
    if modulus_bytes is None or signature is None or len(signature) != len(modulus_bytes):
        return False
    modulus = int.from_bytes(modulus_bytes, "big")
    signature_value = int.from_bytes(signature, "big")
    if signature_value >= modulus:
        return False
    digest = hashlib.sha256(
        json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).digest()
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    padding_length = len(modulus_bytes) - len(digest_info) - 3
    if padding_length < 8:
        return False
    expected = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info
    observed = pow(signature_value, int(public_key["exponent"]), modulus).to_bytes(
        len(modulus_bytes), "big"
    )
    return hmac.compare_digest(observed, expected)


def _reviewer_provider_registry_path(root: Path) -> Path:
    configured = Path(REVIEWER_PROVIDER_REGISTRY_PATH)
    return configured if configured.is_absolute() else root / configured


def _reviewer_provider_tool_path(root: Path, provider: dict[str, Any]) -> Path | None:
    value = provider.get("tool_path")
    if not _nonempty_string(value):
        return None
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _reviewer_provider_authority(root: Path = ROOT) -> dict[str, Any]:
    registry_path = _reviewer_provider_registry_path(root)
    try:
        payload = _load(registry_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError):
        payload = None
    registry_fingerprint = (
        _canonical_hash(payload)
        if isinstance(payload, dict)
        else _sha256(registry_path)
        if registry_path.is_file()
        else None
    )
    findings: list[str] = []
    providers_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(payload, dict):
        findings.append("reviewer provider registry is missing or malformed")
    else:
        if set(payload) != {"schema", "active_provider_id", "providers"}:
            findings.append("reviewer provider registry fields are not the sole current schema")
        if payload.get("schema") != REVIEWER_PROVIDER_REGISTRY_SCHEMA:
            findings.append("reviewer provider registry schema is not current")
        providers = payload.get("providers")
        if not isinstance(providers, list):
            findings.append("reviewer provider registry providers must be a list")
            providers = []
        required_provider_fields = {
            "provider_id",
            "execution_owner",
            "tool_path",
            "tool_sha256",
            "command",
            "timeout_seconds",
            "public_key",
        }
        for index, item in enumerate(providers):
            if not isinstance(item, dict) or set(item) != required_provider_fields:
                findings.append(f"reviewer provider {index} fields are invalid")
                continue
            provider_id = item.get("provider_id")
            owner = item.get("execution_owner")
            command = item.get("command")
            timeout_seconds = item.get("timeout_seconds")
            if not _nonempty_string(provider_id) or provider_id in providers_by_id:
                findings.append(f"reviewer provider {index} has a missing or duplicate provider_id")
                continue
            if not _nonempty_string(owner) or owner == PRODUCER_IDENTITY:
                findings.append(f"reviewer provider {provider_id} has an invalid execution_owner")
            if not isinstance(command, list) or not command or not all(_nonempty_string(part) for part in command):
                findings.append(f"reviewer provider {provider_id} command is invalid")
            elif item.get("tool_path") not in command:
                findings.append(f"reviewer provider {provider_id} command does not execute its registered tool")
            if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= 300:
                findings.append(f"reviewer provider {provider_id} timeout_seconds is invalid")
            if not _valid_provider_public_key(item.get("public_key")):
                findings.append(f"reviewer provider {provider_id} public verification key is invalid")
            tool_path = _reviewer_provider_tool_path(root, item)
            if tool_path is None or not tool_path.is_file():
                findings.append(f"reviewer provider {provider_id} tool is missing")
            elif item.get("tool_sha256") != _sha256(tool_path):
                findings.append(f"reviewer provider {provider_id} tool fingerprint is stale")
            providers_by_id[str(provider_id)] = dict(item)
    active_provider_id = payload.get("active_provider_id") if isinstance(payload, dict) else None
    provider: dict[str, Any] | None = None
    status = "invalid" if findings else "no_provider"
    if active_provider_id is not None:
        if not _nonempty_string(active_provider_id) or active_provider_id not in providers_by_id:
            findings.append("active reviewer provider is not exactly registered")
            status = "invalid"
        elif not findings:
            provider = providers_by_id[str(active_provider_id)]
            status = "ready"
    return {
        "schema": REVIEWER_PROVIDER_AUTHORITY_SCHEMA,
        "registry": {
            "schema": REVIEWER_PROVIDER_REGISTRY_SCHEMA,
            "path": REVIEWER_PROVIDER_REGISTRY_PATH,
            "fingerprint": registry_fingerprint,
        },
        "status": status,
        "provider": provider,
        "findings": findings,
    }


def _validate_request_shape(request: Any) -> list[str]:
    if not isinstance(request, dict):
        return ["request root must be a mapping"]
    errors: list[str] = []
    if request.get("schema") != REQUEST_SCHEMA:
        errors.append(f"request schema must be {REQUEST_SCHEMA}")
    if request.get("request_fingerprint") != _canonical_hash(_request_body(request)):
        errors.append("request_fingerprint does not bind the frozen request body")
    producer = request.get("producer")
    if not isinstance(producer, dict):
        errors.append("request producer is missing")
    else:
        if producer.get("identity") != PRODUCER_IDENTITY:
            errors.append("request selects a non-canonical producer")
        if producer.get("path") != "scripts/module_semantics_review_producer.py":
            errors.append("request producer path is not canonical")
        if producer.get("sha256") != _sha256(Path(__file__).resolve()):
            errors.append("request producer fingerprint is stale")
    if not isinstance(request.get("module_type"), str) or not request["module_type"].strip():
        errors.append("request module_type is missing")
    if not isinstance(request.get("record_subject"), dict):
        errors.append("request record_subject is missing")
    elif request.get("record_fingerprint") != _canonical_hash(request["record_subject"]):
        errors.append("request record fingerprint is invalid")
    dimensions = request.get("dimensions")
    if not isinstance(dimensions, dict) or tuple(dimensions) != DIMENSIONS:
        errors.append("request must carry the exact nine ordered dimensions")
    else:
        for identity in DIMENSIONS:
            item = dimensions.get(identity)
            if not isinstance(item, dict):
                errors.append(f"dimension {identity} is not a mapping")
                continue
            if item.get("status") not in {"pass", "blocked", "not_run"}:
                errors.append(f"dimension {identity} has an invalid status")
            if not isinstance(item.get("finding_count"), int) or item["finding_count"] < 0:
                errors.append(f"dimension {identity} has an invalid finding count")
            if not isinstance(item.get("findings_fingerprint"), str):
                errors.append(f"dimension {identity} has no findings fingerprint")
    if request.get("reviewer_provider_authority") != _reviewer_provider_authority(ROOT):
        errors.append("request does not bind the current closed reviewer provider registry")
    reviewer_requirement = request.get("reviewer_requirement")
    if not isinstance(reviewer_requirement, dict):
        errors.append("request reviewer requirement is missing")
    else:
        if reviewer_requirement.get("provider_result_schema") != REVIEWER_PROVIDER_RESULT_SCHEMA:
            errors.append("request reviewer result schema is not current")
        if reviewer_requirement.get("provider_receipt_schema") != REVIEWER_PROVIDER_RECEIPT_SCHEMA:
            errors.append("request reviewer receipt schema is not current")
    return errors


def _replay_request(request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ledger_materials = [
        item
        for item in request.get("observed_materials", [])
        if isinstance(item, dict) and item.get("role") == "ledger"
    ]
    if len(ledger_materials) != 1:
        return ["frozen request must identify exactly one ledger material"]
    ledger_path = (ROOT / str(ledger_materials[0].get("path"))).resolve()
    try:
        ledger_path.relative_to(ROOT.resolve())
    except ValueError:
        return ["ledger material escapes the repository"]
    if not ledger_path.is_file():
        return ["ledger material no longer exists"]
    for material in request.get("observed_materials", []):
        if not isinstance(material, dict) or not isinstance(material.get("path"), str):
            errors.append("observed material is malformed")
            continue
        path = (ROOT / material["path"]).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"material escapes repository: {material['path']}")
            continue
        observed = _sha256(path) if path.is_file() else None
        if observed != material.get("observed_sha256"):
            errors.append(f"material changed since freeze: {material['path']}")
    if errors:
        return errors
    checker = _load_checker()
    replay = checker.review_ledger(
        ROOT,
        ledger_path,
        review_scope="module",
        module=request["module_type"],
    )
    results = replay.get("record_results")
    if not isinstance(results, list) or len(results) != 1:
        return ["checker replay did not return exactly one module result"]
    replay_request = results[0].get("review_request")
    if replay_request != request:
        errors.append("checker replay did not reproduce the exact frozen request")
    return errors


def _validate_provider_evidence(
    request: dict[str, Any],
    evidence: Any,
    *,
    command: list[str],
    producer_command: list[str],
    expected_execution_request_fingerprint: str,
    observed_exit_status: int,
) -> dict[str, Any]:
    authority = request.get("reviewer_provider_authority")
    provider = authority.get("provider") if isinstance(authority, dict) else None
    if not isinstance(provider, dict):
        return {
            "status": "fail",
            "errors": ["no ready reviewer provider is frozen in the current registry"],
            "result": None,
            "receipt": None,
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "disposition": "blocked",
        }
    if not isinstance(evidence, dict) or not isinstance(evidence.get("result"), dict) or not isinstance(evidence.get("receipt"), dict):
        return {
            "status": "fail",
            "errors": ["reviewer provider did not emit one parseable result and receipt"],
            "result": evidence.get("result") if isinstance(evidence, dict) else None,
            "receipt": evidence.get("receipt") if isinstance(evidence, dict) else None,
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "disposition": "blocked",
        }
    result = evidence["result"]
    receipt = evidence["receipt"]
    result_subject = {key: value for key, value in result.items() if key != "output_fingerprint"}
    result_fingerprint = _canonical_hash(result_subject)
    receipt_subject = {key: value for key, value in receipt.items() if key != "receipt_fingerprint"}
    receipt_fingerprint = _canonical_hash(receipt_subject)
    errors: list[str] = []
    result_fields = {
        "schema",
        "provider_id",
        "execution_owner",
        "provider_tool",
        "registry_fingerprint",
        "execution_request_fingerprint",
        "request_fingerprint",
        "domain_findings",
        "disposition",
        "terminal_status",
        "output_fingerprint",
    }
    receipt_fields = {
        "schema",
        "provider_id",
        "execution_owner",
        "provider_tool",
        "registry_fingerprint",
        "execution_request_fingerprint",
        "request_fingerprint",
        "result_fingerprint",
        "execution_request",
        "command",
        "exit_status",
        "terminal_status",
        "disposition",
        "receipt_id",
        "terminal_attestation",
        "receipt_fingerprint",
    }
    if set(result) != result_fields or set(receipt) != receipt_fields:
        errors.append("reviewer provider result/receipt fields are not the sole current schema")
    if result.get("schema") != REVIEWER_PROVIDER_RESULT_SCHEMA or receipt.get("schema") != REVIEWER_PROVIDER_RECEIPT_SCHEMA:
        errors.append("reviewer provider schemas are not current")
    expected_tool = {"path": provider.get("tool_path"), "sha256": provider.get("tool_sha256")}
    if result.get("provider_tool") != expected_tool or receipt.get("provider_tool") != expected_tool:
        errors.append("reviewer provider evidence is not bound to the registered tool")
    if result.get("provider_id") != provider.get("provider_id") or receipt.get("provider_id") != provider.get("provider_id"):
        errors.append("reviewer provider identity differs from the frozen registry")
    expected_owner = provider.get("execution_owner")
    author = request.get("record_subject", {}).get("provenance", {}).get("author_owner") if isinstance(request.get("record_subject"), dict) else None
    owner = result.get("execution_owner")
    if owner != expected_owner or receipt.get("execution_owner") != expected_owner or owner in {author, PRODUCER_IDENTITY}:
        errors.append("reviewer provider execution owner is not the exact independent registered owner")
    registry_fingerprint = authority.get("registry", {}).get("fingerprint") if isinstance(authority, dict) else None
    if result.get("registry_fingerprint") != registry_fingerprint or receipt.get("registry_fingerprint") != registry_fingerprint:
        errors.append("reviewer provider evidence does not bind the frozen registry")
    if result.get("request_fingerprint") != request.get("request_fingerprint") or receipt.get("request_fingerprint") != request.get("request_fingerprint"):
        errors.append("reviewer provider evidence does not bind the frozen review request")
    execution_request = receipt.get("execution_request")
    execution_body = (
        {
            key: value
            for key, value in execution_request.items()
            if key != "execution_request_fingerprint"
        }
        if isinstance(execution_request, dict)
        else None
    )
    execution_fingerprint = (
        execution_request.get("execution_request_fingerprint")
        if isinstance(execution_request, dict)
        else None
    )
    if (
        execution_fingerprint != expected_execution_request_fingerprint
        or not isinstance(execution_body, dict)
        or _canonical_hash(execution_body) != expected_execution_request_fingerprint
        or execution_request.get("schema") != REVIEWER_PROVIDER_EXECUTION_REQUEST_SCHEMA
        or execution_request.get("review_request") != request
        or execution_request.get("provider_authority") != authority
        or execution_request.get("provider_command") != command
        or execution_request.get("producer_command") != producer_command
        or result.get("execution_request_fingerprint") != expected_execution_request_fingerprint
        or receipt.get("execution_request_fingerprint") != expected_execution_request_fingerprint
    ):
        errors.append("reviewer provider execution-request fingerprint is invalid or inconsistent")
    findings = result.get("domain_findings")
    if not isinstance(findings, list):
        findings = []
        errors.append("reviewer provider result lacks an explicit domain_findings list")
    disposition = result.get("disposition")
    if disposition not in {"accepted", "blocked"} or receipt.get("disposition") != disposition:
        errors.append("reviewer provider disposition is invalid or inconsistent")
    if result.get("terminal_status") != "success" or receipt.get("terminal_status") != "success":
        errors.append("reviewer provider evidence is not terminal success")
    if observed_exit_status != 0 or receipt.get("exit_status") != observed_exit_status:
        errors.append("reviewer provider receipt does not bind the observed zero exit status")
    if result.get("output_fingerprint") != result_fingerprint:
        errors.append("reviewer provider result fingerprint is invalid")
    if receipt.get("result_fingerprint") != result_fingerprint or receipt.get("receipt_fingerprint") != receipt_fingerprint:
        errors.append("reviewer provider receipt fingerprint is invalid")
    if receipt.get("command") != command:
        errors.append("reviewer provider receipt does not bind the exact executed command")
    receipt_body = {
        key: value
        for key, value in receipt.items()
        if key not in {"terminal_attestation", "receipt_fingerprint"}
    }
    terminal_subject = {
        "schema": REVIEWER_PROVIDER_TERMINAL_SUBJECT_SCHEMA,
        "execution_request": execution_request,
        "result": result,
        "receipt": receipt_body,
    }
    if not _verify_provider_attestation(
        terminal_subject,
        receipt.get("terminal_attestation"),
        provider.get("public_key"),
    ):
        errors.append("reviewer provider terminal subject signature is invalid")
    if disposition == "accepted" and findings:
        errors.append("accepted reviewer provider evidence retains domain findings")
    return {
        "status": "fail" if errors else "success" if disposition == "accepted" else "blocked",
        "errors": errors,
        "result": result,
        "receipt": receipt,
        "result_fingerprint": result_fingerprint,
        "receipt_fingerprint": receipt_fingerprint,
        "reviewer_execution_owner": owner,
        "execution_request_fingerprint": execution_fingerprint,
        "terminal_subject_fingerprint": _canonical_hash(terminal_subject),
        "producer_command": producer_command,
        "domain_findings": findings,
        "disposition": disposition,
    }


def _execute_registered_provider(
    request: dict[str, Any],
    *,
    producer_command: list[str],
) -> dict[str, Any]:
    authority = request.get("reviewer_provider_authority")
    provider = authority.get("provider") if isinstance(authority, dict) else None
    if not isinstance(authority, dict) or authority.get("status") != "ready" or not isinstance(provider, dict):
        findings = authority.get("findings") if isinstance(authority, dict) else None
        return {
            "status": "blocked",
            "errors": list(findings) if isinstance(findings, list) and findings else ["no active independent reviewer provider is registered"],
            "result": None,
            "receipt": None,
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "disposition": "blocked",
        }
    command_prefix = provider.get("command")
    if not isinstance(command_prefix, list):
        return {
            "status": "fail",
            "errors": ["registered reviewer provider command is invalid"],
            "result": None,
            "receipt": None,
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "disposition": "blocked",
        }
    with tempfile.TemporaryDirectory(prefix="physicsguard-review-provider-") as temporary_directory:
        working_directory = Path(temporary_directory)
        execution_request_path = working_directory / "provider-execution-request.json"
        result_path = working_directory / "provider-result.json"
        receipt_path = working_directory / "provider-receipt.json"
        command = [
            *command_prefix,
            str(execution_request_path),
            "--result",
            str(result_path),
            "--receipt",
            str(receipt_path),
        ]
        execution_body = {
            "schema": REVIEWER_PROVIDER_EXECUTION_REQUEST_SCHEMA,
            "review_request": request,
            "provider_authority": authority,
            "provider_command": command,
            "producer_command": producer_command,
        }
        execution_request = {
            **execution_body,
            "execution_request_fingerprint": _canonical_hash(execution_body),
        }
        _write_json(execution_request_path, execution_request)
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            completed = subprocess.run(
                command,
                cwd=working_directory,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=provider["timeout_seconds"],
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "status": "fail",
                "errors": [f"registered reviewer provider execution failed: {exc}"],
                "result": None,
                "receipt": None,
                "result_fingerprint": None,
                "receipt_fingerprint": None,
                "reviewer_execution_owner": provider.get("execution_owner"),
                "domain_findings": [],
                "disposition": "blocked",
            }
        try:
            result = _load(result_path) if result_path.is_file() else None
            receipt = _load(receipt_path) if receipt_path.is_file() else None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
            return {
                "status": "fail",
                "errors": [f"registered reviewer provider artifacts cannot be parsed: {exc}"],
                "result": None,
                "receipt": None,
                "result_fingerprint": None,
                "receipt_fingerprint": None,
                "reviewer_execution_owner": provider.get("execution_owner"),
                "domain_findings": [],
                "disposition": "blocked",
            }
        return _validate_provider_evidence(
            request,
            {"result": result, "receipt": receipt},
            command=command,
            producer_command=producer_command,
            expected_execution_request_fingerprint=execution_request["execution_request_fingerprint"],
            observed_exit_status=completed.returncode,
        )


def produce(
    request: dict[str, Any],
    *,
    command: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    machine_errors = _validate_request_shape(request)
    if not machine_errors:
        machine_errors.extend(_replay_request(request))
    dimensions = request.get("dimensions") if isinstance(request, dict) else {}
    nonreview_dimensions_pass = (
        isinstance(dimensions, dict)
        and all(
            isinstance(dimensions.get(identity), dict)
            and dimensions[identity].get("status") == "pass"
            for identity in DIMENSIONS[:-1]
        )
        and isinstance(dimensions.get("independent_review"), dict)
        and dimensions["independent_review"].get("status") == "not_run"
    )
    provider_stage = (
        _execute_registered_provider(request, producer_command=command)
        if not machine_errors and nonreview_dimensions_pass
        else {
            "status": "blocked",
            "errors": ["reviewer provider was not run because machine-decidable review is not closed"],
            "result": None,
            "receipt": None,
            "result_fingerprint": None,
            "receipt_fingerprint": None,
            "reviewer_execution_owner": None,
            "domain_findings": [],
            "disposition": "blocked",
        }
    )
    reviewer_owner = provider_stage.get("reviewer_execution_owner")
    domain_findings = provider_stage.get("domain_findings") if isinstance(provider_stage.get("domain_findings"), list) else []
    disposition = (
        "accepted"
        if not machine_errors
        and nonreview_dimensions_pass
        and provider_stage.get("status") == "success"
        and provider_stage.get("disposition") == "accepted"
        and not domain_findings
        else "blocked"
    )
    producer_findings = [
        {"code": "machine_replay_failed", "message": message}
        for message in machine_errors
    ] + [
        {"code": "reviewer_provider_invalid", "message": message}
        for message in provider_stage.get("errors", [])
    ]
    if not nonreview_dimensions_pass:
        producer_findings.append(
            {
                "code": "machine_dimensions_not_closed",
                "message": "All eight machine-decidable dimensions must pass and independent review must be not_run before domain acceptance.",
            }
        )
    producer_tool = {
        "path": "scripts/module_semantics_review_producer.py",
        "sha256": _sha256(Path(__file__).resolve()),
    }
    result_body = {
        "schema": RESULT_SCHEMA,
        "producer_identity": PRODUCER_IDENTITY,
        "producer_tool": producer_tool,
        "module_type": request.get("module_type"),
        "request_fingerprint": request.get("request_fingerprint"),
        "input_fingerprints": request.get("input_fingerprints"),
        "dimensions": dimensions,
        "reviewer_provider_authority": request.get("reviewer_provider_authority"),
        "reviewer_provider_evidence": (
            {"result": provider_stage.get("result"), "receipt": provider_stage.get("receipt")}
            if provider_stage.get("result") is not None or provider_stage.get("receipt") is not None
            else None
        ),
        "reviewer_execution_owner": reviewer_owner,
        "reviewer_provider_execution_request_fingerprint": provider_stage.get("execution_request_fingerprint"),
        "reviewer_provider_terminal_subject_fingerprint": provider_stage.get("terminal_subject_fingerprint"),
        "reviewer_provider_result_fingerprint": provider_stage.get("result_fingerprint"),
        "reviewer_provider_receipt_fingerprint": provider_stage.get("receipt_fingerprint"),
        "domain_findings": domain_findings,
        "producer_findings": producer_findings,
        "replay": {
            "status": "success" if not machine_errors else "fail",
            "observed_materials_fingerprint": _canonical_hash(
                request.get("observed_materials")
            ),
        },
        "disposition": disposition,
        "terminal_status": "success",
    }
    result_fingerprint = _canonical_hash(result_body)
    result = {**result_body, "output_fingerprint": result_fingerprint}
    receipt_body = {
        "schema": RECEIPT_SCHEMA,
        "producer_identity": PRODUCER_IDENTITY,
        "producer_tool": producer_tool,
        "execution_owner": PRODUCER_IDENTITY,
        "request_fingerprint": request.get("request_fingerprint"),
        "result_fingerprint": result_fingerprint,
        "reviewer_provider_registry_fingerprint": request.get("reviewer_provider_authority", {}).get("registry", {}).get("fingerprint") if isinstance(request.get("reviewer_provider_authority"), dict) else None,
        "reviewer_provider_execution_request_fingerprint": provider_stage.get("execution_request_fingerprint"),
        "reviewer_provider_terminal_subject_fingerprint": provider_stage.get("terminal_subject_fingerprint"),
        "reviewer_provider_result_fingerprint": provider_stage.get("result_fingerprint"),
        "reviewer_provider_receipt_fingerprint": provider_stage.get("receipt_fingerprint"),
        "reviewer_execution_owner": reviewer_owner,
        "command": command,
        "exit_status": 0,
        "terminal_status": "success",
        "disposition": disposition,
        "receipt_id": f"module-review-{str(request.get('module_type'))}-{result_fingerprint[:16]}",
    }
    receipt = {**receipt_body, "receipt_fingerprint": _canonical_hash(receipt_body)}
    return result, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay one frozen module-semantics review request through the sole canonical producer."
    )
    parser.add_argument("request", type=Path)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = _load(args.request)
        if not isinstance(request, dict):
            raise ValueError("request root must be a mapping")
        command = [
            "python",
            "scripts/module_semantics_review_producer.py",
            str(args.request),
            "--result",
            str(args.result),
            "--receipt",
            str(args.receipt),
        ]
        result, receipt = produce(
            request,
            command=command,
        )
        _write_json(args.result, result)
        _write_json(args.receipt, receipt)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
