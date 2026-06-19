from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import closure_result, load_struct, sha256_file, write_json


def _resolve(base: Path, candidate: str) -> Path:
    path = Path(candidate)
    return path if path.is_absolute() else base / path


def check_freshness(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_struct(manifest_file)
    base = manifest_file.parent
    evidence: list[Any] = []
    missing_inputs: list[Any] = []
    stale_evidence: list[Any] = []
    next_actions: list[str] = []

    for item in manifest.get("files", []):
        item_path = _resolve(base, item.get("path", ""))
        item_id = item.get("id") or str(item_path)
        if not item_path.exists():
            missing_inputs.append({"id": item_id, "path": str(item_path), "reason": "file_missing"})
            continue
        actual = sha256_file(item_path)
        expected = item.get("sha256") or item.get("expected_sha256")
        evidence.append({"id": item_id, "path": str(item_path), "sha256": actual})
        if expected and expected != actual:
            stale_evidence.append(
                {
                    "id": item_id,
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                    "reason": "file_hash_mismatch",
                }
            )

    current_hashes = manifest.get("current_hashes", {})
    for report in manifest.get("validation_reports", []):
        report_id = report.get("id", "validation_report")
        for key in ("model_hash", "contract_hash", "data_hash"):
            expected = report.get(key)
            actual = current_hashes.get(key)
            if expected and actual and expected != actual:
                stale_evidence.append(
                    {
                        "id": report_id,
                        "hash_field": key,
                        "expected_hash": expected,
                        "actual_hash": actual,
                        "reason": "validation_report_references_stale_hash",
                    }
                )

    for binding in manifest.get("hash_bindings", []):
        expected = binding.get("expected") or binding.get("expected_hash")
        actual = binding.get("actual") or binding.get("actual_hash")
        if expected and actual and expected != actual:
            stale_evidence.append(
                {
                    "id": binding.get("id", "hash_binding"),
                    "source": binding.get("source"),
                    "target": binding.get("target"),
                    "expected_hash": expected,
                    "actual_hash": actual,
                    "reason": "hash_binding_mismatch",
                }
            )

    if missing_inputs:
        next_actions.append("Provide or relink missing inputs before using this evidence.")
    if stale_evidence:
        next_actions.append("Refresh the affected contracts or validation reports before broad claims.")

    status = "blocked" if missing_inputs or stale_evidence else "pass"
    safe_claim = "Freshness evidence is current for the checked manifest." if status == "pass" else ""
    unsafe = "" if status == "pass" else "Do not claim pass, validated, or reusable while freshness is blocked."
    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=missing_inputs,
        stale_evidence=stale_evidence,
        safe_claim=safe_claim,
        unsafe_claim_boundary=unsafe,
        next_actions=next_actions,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DataBank hash freshness.")
    parser.add_argument("manifest", help="JSON/YAML freshness manifest")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = check_freshness(args.manifest)
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
