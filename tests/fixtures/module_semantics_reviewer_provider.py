from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any


EXECUTION_REQUEST_SCHEMA = "physicsguard.module_semantics_reviewer_provider_execution_request.v1"
RESULT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_result.v1"
RECEIPT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_receipt.v1"
TERMINAL_SUBJECT_SCHEMA = "physicsguard.module_semantics_reviewer_provider_terminal_subject.v1"
ATTESTATION_SCHEMA = "physicsguard.module_semantics_reviewer_provider_attestation.v1"
SIGNATURE_ALGORITHM = "rsassa-pkcs1-v1_5-sha256"
FIXTURE_KEY_ID = "physicsguard.fixture.domain-reviewer.key.v1"
FIXTURE_RSA_MODULUS_B64URL = "tl4DW0cNL0WHa15VYW_g7F9h2n_7j32sGOH0Qc64NQrofOckMU9qa4eT5sROdWOOy5PQVVmEXcMpCnlmBeo-80CZn5U09xBipMjxyxzx0SoRpHP0Flmdj3h7bgnwACETqUlnZNrfDU3x8CiEeJVNialMbiODfBxATGBI1RR4zpBNI_W5CLqhWRnjhWokycMtlZwgkVSbQvkVY-KgCNk-HYbV8nzY1qI_X1Q5HvLIR9LNnbyJkX0TYzsyaVBvRyu-aVLjeDmbrMZZshKQn4qJVdsAcxfWKlzhsJZVBX2g5o1kEleEykegI1_XZaN-WXDPKjesFYvrXdZ1as2kArj1Xw"
FIXTURE_RSA_PRIVATE_EXPONENT_B64URL = "JvSzM9rcIqZwFIvsoilDe0quvP2Mz6yRSClwQ2R0rgP8AL5hWVU1Du5BtlBl0CapuKwFG05Je7v2NuIS3J2av9yjVFcLnuE1qSyxlelDcKJTbXVFhUa0ZRLgDvP5fBWUvRtMhltIvW9SiLInBhkinI75ICfe7PKd-5KvzDCY08rbKVO9DDydWNH9jsD3Lok0PCt7dTdQy5CyWAPi3yADtpddDagublCVdeb8uDi-36GgXLetibaDaE6x8t3oT4G7mK5EAaezFTJkJPB0vMFMdINcmQBrNIjAJncSqhHmiPNhKxva3I0GWaHjz8HkX_DPauKG_Ki6I-kK2KoiOpiPkQ"
FIXTURE_RSA_EXPONENT = 65537


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sign(subject: dict[str, Any]) -> str:
    modulus_bytes = _b64url_decode(FIXTURE_RSA_MODULUS_B64URL)
    modulus = int.from_bytes(modulus_bytes, "big")
    private_exponent = int.from_bytes(
        _b64url_decode(FIXTURE_RSA_PRIVATE_EXPONENT_B64URL), "big"
    )
    digest = hashlib.sha256(
        json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).digest()
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    padding_length = len(modulus_bytes) - len(digest_info) - 3
    encoded = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info
    signature = pow(
        int.from_bytes(encoded, "big"), private_exponent, modulus
    ).to_bytes(len(modulus_bytes), "big")
    return _b64url_encode(signature)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("execution_request", type=Path)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "accepted",
            "blocked",
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
        ),
        default="accepted",
    )
    args = parser.parse_args()
    execution = json.loads(args.execution_request.read_text(encoding="utf-8"))
    execution_body = {
        key: value
        for key, value in execution.items()
        if key != "execution_request_fingerprint"
    }
    if (
        execution.get("schema") != EXECUTION_REQUEST_SCHEMA
        or execution.get("execution_request_fingerprint")
        != _canonical_hash(execution_body)
    ):
        return 2
    review_request = execution["review_request"]
    authority = execution["provider_authority"]
    provider = authority["provider"]
    provider_id = provider["provider_id"]
    owner = provider["execution_owner"]
    provider_tool = {
        "path": provider["tool_path"],
        "sha256": provider["tool_sha256"],
    }
    registry_fingerprint = authority["registry"]["fingerprint"]
    request_fingerprint = review_request["request_fingerprint"]
    execution_request_fingerprint = execution["execution_request_fingerprint"]
    disposition = "blocked" if args.mode == "blocked" else "accepted"
    findings = (
        [{"code": "fixture_domain_finding", "message": "Fixture reviewer blocked the request."}]
        if disposition == "blocked"
        else []
    )
    if args.mode == "foreign-provider":
        provider_id = "physicsguard.fixture.foreign-provider"
    if args.mode == "owner-mismatch":
        owner = "physicsguard.fixture.foreign-owner"
    if args.mode == "tool-mismatch":
        provider_tool = {"path": provider["tool_path"], "sha256": "0" * 64}
    if args.mode == "registry-mismatch":
        registry_fingerprint = "0" * 64
    if args.mode == "request-mismatch":
        request_fingerprint = "0" * 64
    if args.mode == "execution-request-mismatch":
        execution_request_fingerprint = "0" * 64
    result_body = {
        "schema": RESULT_SCHEMA,
        "provider_id": provider_id,
        "execution_owner": owner,
        "provider_tool": provider_tool,
        "registry_fingerprint": registry_fingerprint,
        "execution_request_fingerprint": execution_request_fingerprint,
        "request_fingerprint": request_fingerprint,
        "domain_findings": findings,
        "disposition": disposition,
        "terminal_status": "success",
    }
    result_fingerprint = _canonical_hash(result_body)
    result = {**result_body, "output_fingerprint": result_fingerprint}
    if args.mode == "result-hash-mismatch":
        result["output_fingerprint"] = "0" * 64
    receipt_body = {
        "schema": RECEIPT_SCHEMA,
        "provider_id": provider_id,
        "execution_owner": owner,
        "provider_tool": provider_tool,
        "registry_fingerprint": registry_fingerprint,
        "execution_request_fingerprint": execution_request_fingerprint,
        "request_fingerprint": request_fingerprint,
        "result_fingerprint": result_fingerprint,
        "execution_request": execution,
        "command": execution["provider_command"],
        "exit_status": 7 if args.mode in {"exit-mismatch", "nonzero-exit"} else 0,
        "terminal_status": "success",
        "disposition": disposition,
        "receipt_id": f"fixture-review-{result_fingerprint[:16]}",
    }
    if args.mode == "result-mismatch":
        receipt_body["result_fingerprint"] = "0" * 64
    if args.mode == "command-mismatch":
        receipt_body["command"] = [*execution["provider_command"], "unexpected"]
    terminal_subject = {
        "schema": TERMINAL_SUBJECT_SCHEMA,
        "execution_request": execution,
        "result": result,
        "receipt": receipt_body,
    }
    terminal_attestation = {
        "schema": ATTESTATION_SCHEMA,
        "algorithm": SIGNATURE_ALGORITHM,
        "key_id": FIXTURE_KEY_ID,
        "subject_fingerprint": _canonical_hash(terminal_subject),
        "signature_b64url": _sign(terminal_subject),
    }
    receipt_subject = {
        **receipt_body,
        "terminal_attestation": terminal_attestation,
    }
    receipt = {**receipt_subject, "receipt_fingerprint": _canonical_hash(receipt_subject)}
    if args.mode == "receipt-hash-mismatch":
        receipt["receipt_fingerprint"] = "0" * 64
    _write(args.result, result)
    _write(args.receipt, receipt)
    return 7 if args.mode == "nonzero-exit" else 0


if __name__ == "__main__":
    raise SystemExit(main())
