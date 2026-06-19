from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import (
    CLOSURE_STATUSES,
    REQUIRED_CLOSURE_KEYS,
    as_list,
    closure_result,
    is_non_empty,
    is_sha256_hex,
    load_struct,
    resolve_path,
    write_json,
)


REQUIRED_FIELDS: dict[str, set[str]] = {
    "source": {"id", "path", "sha256", "source_type", "read_only", "provenance"},
    "data": {"id", "path", "sha256", "row_count", "fields", "time_range", "units", "parameter_roles"},
    "model": {"id", "path", "model_hash", "model_targets", "inputs", "outputs", "parent_model", "child_models"},
    "binding": {"field_id", "model_target", "evidence", "confidence", "review_state", "unit_evidence"},
    "logic": {"claim_id", "claim_text", "supporting_evidence", "assumptions", "limitations", "unsafe_claim_boundary"},
    "timeline": {"event_id", "event_type", "source_ref", "source_date", "coverage_period", "precedes", "supersedes"},
    "freshness": {"current_hashes", "validation_reports", "hash_bindings", "invalidated_by", "stale_evidence"},
    "query": {"query", "scope", "matches", "reason"},
    "closure": REQUIRED_CLOSURE_KEYS,
}

PATH_FIELDS = {"path"}
SHA256_FIELDS = {"sha256"}
LIST_OR_MAP_FIELDS = {
    "evidence",
    "missing_inputs",
    "stale_evidence",
    "skipped_checks",
    "next_actions",
    "fields",
    "units",
    "parameter_roles",
    "model_targets",
    "inputs",
    "outputs",
    "parent_model",
    "child_models",
    "supporting_evidence",
    "assumptions",
    "limitations",
    "precedes",
    "supersedes",
    "current_hashes",
    "validation_reports",
    "hash_bindings",
    "invalidated_by",
    "matches",
    "scope",
    "query",
}


def _records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and "contracts" in data:
        return [item for item in as_list(data.get("contracts")) if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _record_missing_fields(record: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(field for field in required if field not in record)


def _record_value_errors(
    record: dict[str, Any],
    contract_type: str,
    *,
    check_paths: bool,
    base_path: str | Path | None,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for field, value in record.items():
        if field in PATH_FIELDS and is_non_empty(value) and check_paths:
            base = Path(base_path) if base_path else Path.cwd()
            resolved = resolve_path(base, str(value))
            if not resolved.exists():
                errors.append({"field": field, "reason": "path_missing", "path": str(resolved)})
        if field in SHA256_FIELDS and is_non_empty(value) and not is_sha256_hex(value):
            errors.append({"field": field, "reason": "invalid_sha256", "value": value})

    for field in REQUIRED_FIELDS[contract_type]:
        if field in LIST_OR_MAP_FIELDS:
            continue
        if field in record and not is_non_empty(record[field]):
            errors.append({"field": field, "reason": "empty_required_value"})

    if contract_type == "closure":
        status = str(record.get("status", "")).strip().lower()
        if status not in CLOSURE_STATUSES:
            errors.append({"field": "status", "reason": "unknown_closure_status", "allowed": sorted(CLOSURE_STATUSES)})
        if status == "pass":
            if not as_list(record.get("evidence")):
                errors.append({"field": "evidence", "reason": "pass_requires_evidence"})
            for field in ("missing_inputs", "stale_evidence", "skipped_checks"):
                if as_list(record.get(field)):
                    errors.append({"field": field, "reason": "pass_cannot_have_blocking_items"})

    if contract_type == "query" and not as_list(record.get("matches")) and not is_non_empty(record.get("reason")):
        errors.append({"field": "reason", "reason": "empty_query_requires_reason"})

    return errors


def check_contracts(path: str | Path, *, check_paths: bool = False, base_path: str | Path | None = None) -> dict[str, Any]:
    records = _records(load_struct(path))
    missing_inputs: list[Any] = []
    evidence: list[Any] = []
    skipped_checks: list[Any] = []

    if not records:
        missing_inputs.append({"id": "contracts", "reason": "no_contract_records"})

    for index, record in enumerate(records):
        contract_type = str(record.get("contract_type") or record.get("type") or "").strip().lower()
        record_id = record.get("id") or record.get("contract_id") or f"contract_{index + 1}"
        if contract_type not in REQUIRED_FIELDS:
            missing_inputs.append(
                {
                    "id": record_id,
                    "reason": "unknown_contract_type",
                    "contract_type": contract_type,
                    "allowed_types": sorted(REQUIRED_FIELDS),
                }
            )
            continue
        missing = _record_missing_fields(record, REQUIRED_FIELDS[contract_type])
        if missing:
            missing_inputs.append(
                {
                    "id": record_id,
                    "contract_type": contract_type,
                    "missing_fields": missing,
                }
            )
            continue
        value_errors = _record_value_errors(record, contract_type, check_paths=check_paths, base_path=base_path or Path(path).parent)
        if value_errors:
            missing_inputs.append(
                {
                    "id": record_id,
                    "contract_type": contract_type,
                    "invalid_fields": value_errors,
                }
            )
            continue
        evidence.append({"id": record_id, "contract_type": contract_type, "required_fields_present": True})

        if contract_type == "data" and record.get("copied_raw_data") is True:
            missing_inputs.append(
                {
                    "id": record_id,
                    "contract_type": contract_type,
                    "reason": "raw_data_copy_not_allowed",
                }
            )

    status = "blocked" if missing_inputs else "pass"
    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=missing_inputs,
        skipped_checks=skipped_checks,
        safe_claim="Required DataBank contract fields are present." if status == "pass" else "",
        unsafe_claim_boundary="" if status == "pass" else "Do not use incomplete DataBank contracts for closure claims.",
        next_actions=["Fill missing required fields or use an allowed contract_type."] if status != "pass" else [],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DataBank required contract fields.")
    parser.add_argument("contracts", help="JSON/YAML contract file or list")
    parser.add_argument("--check-paths", action="store_true", help="Require path fields to resolve")
    parser.add_argument("--base", help="Base directory for relative path checks")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = check_contracts(args.contracts, check_paths=args.check_paths, base_path=args.base)
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
