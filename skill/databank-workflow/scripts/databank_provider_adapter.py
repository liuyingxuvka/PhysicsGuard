from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import (
    REQUIRED_CLOSURE_KEYS,
    as_list,
    closure_result,
    dump_json,
    load_struct,
    normalize_status,
    write_json,
)


ISSUE_KEYS = ("missing_inputs", "missing", "blocking_gaps", "gaps")
STALE_KEYS = ("stale_evidence", "stale_paths", "stale")
SKIPPED_KEYS = ("skipped_checks", "skipped")


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and isinstance(value.get("providers"), list):
        return [item for item in value["providers"] if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _collect(record: dict[str, Any], keys: tuple[str, ...]) -> list[Any]:
    collected: list[Any] = []
    for key in keys:
        collected.extend(as_list(record.get(key)))
    return collected


def adapt_record(record: dict[str, Any], provider: str, index: int = 0) -> dict[str, Any]:
    provider_id = str(record.get("id") or record.get("provider") or record.get("artifact_kind") or f"{provider}_{index + 1}")
    missing_fields = sorted(REQUIRED_CLOSURE_KEYS - set(record.keys()))
    if not missing_fields:
        status = normalize_status(record.get("status"))
        if record.get("missing_inputs") or record.get("stale_evidence") or record.get("skipped_checks"):
            status = "blocked"
        return closure_result(
            status,
            evidence=as_list(record.get("evidence")),
            missing_inputs=as_list(record.get("missing_inputs")),
            stale_evidence=as_list(record.get("stale_evidence")),
            skipped_checks=as_list(record.get("skipped_checks")),
            safe_claim=str(record.get("safe_claim") or "") if status == "pass" else "",
            unsafe_claim_boundary=str(record.get("unsafe_claim_boundary") or "") if status != "pass" else "",
            next_actions=as_list(record.get("next_actions")),
            extra={"id": provider_id, "provider": provider, "source_shape": "closure_envelope"},
        )

    missing_inputs = _collect(record, ISSUE_KEYS)
    stale_evidence = _collect(record, STALE_KEYS)
    skipped_checks = _collect(record, SKIPPED_KEYS)
    explicit_status = normalize_status(record.get("status") or record.get("validation_state") or record.get("lifecycle_state"))
    status = "blocked" if missing_inputs or stale_evidence or skipped_checks or explicit_status != "pass" else "pass"

    evidence = as_list(record.get("evidence"))
    if not evidence:
        evidence = [
            {
                "id": provider_id,
                "provider": provider,
                "artifact_kind": record.get("artifact_kind"),
                "source_status": record.get("status") or record.get("validation_state") or record.get("lifecycle_state"),
            }
        ]

    if status != "pass" and not missing_inputs and not stale_evidence and not skipped_checks:
        missing_inputs = [
            {
                "id": provider_id,
                "reason": "provider_status_not_pass_or_unrecognized_shape",
                "source_status": record.get("status") or record.get("validation_state") or record.get("lifecycle_state"),
                "missing_envelope_fields": missing_fields,
            }
        ]

    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=missing_inputs,
        stale_evidence=stale_evidence,
        skipped_checks=skipped_checks,
        safe_claim=f"{provider} provider result is current for the requested DataBank scope." if status == "pass" else "",
        unsafe_claim_boundary="" if status == "pass" else f"Do not use {provider} provider output for broad DataBank claims until closure passes.",
        next_actions=["Emit the full DataBank closure envelope from this provider."] if status != "pass" else [],
        extra={"id": provider_id, "provider": provider, "source_shape": "adapted_provider_result"},
    )


def adapt_provider(path: str | Path, provider: str) -> dict[str, Any]:
    data = load_struct(path)
    results = [adapt_record(record, provider, index) for index, record in enumerate(_records(data))]
    if not results:
        return closure_result(
            "blocked",
            missing_inputs=[{"id": "provider_input", "path": str(path), "reason": "no_provider_records"}],
            unsafe_claim_boundary="Cannot adapt an empty provider result.",
            next_actions=["Provide a JSON/YAML provider result."],
        )

    aggregate = "pass"
    missing_inputs: list[Any] = []
    stale_evidence: list[Any] = []
    skipped_checks: list[Any] = []
    evidence: list[Any] = []
    for result in results:
        evidence.append({"id": result.get("id"), "provider": result.get("provider"), "status": result["status"]})
        missing_inputs.extend(as_list(result.get("missing_inputs")))
        stale_evidence.extend(as_list(result.get("stale_evidence")))
        skipped_checks.extend(as_list(result.get("skipped_checks")))
        if result["status"] == "blocked":
            aggregate = "blocked"
        elif result["status"] in {"partial", "downgraded"} and aggregate == "pass":
            aggregate = result["status"]

    if missing_inputs or stale_evidence or skipped_checks:
        aggregate = "blocked"
    return closure_result(
        aggregate,
        evidence=evidence,
        missing_inputs=missing_inputs,
        stale_evidence=stale_evidence,
        skipped_checks=skipped_checks,
        safe_claim=f"All {provider} provider records adapted to DataBank closure." if aggregate == "pass" else "",
        unsafe_claim_boundary="" if aggregate == "pass" else f"{provider} provider closure is not safe for broad DataBank claims.",
        next_actions=[] if aggregate == "pass" else ["Fix provider output or preserve blocked status in the DataBank catalog."],
        extra={"provider": provider, "records": results},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Adapt a Guard provider result into a DataBank closure envelope.")
    parser.add_argument("provider_result", help="Provider JSON/YAML result")
    parser.add_argument("--provider", required=True, help="Provider name, for example physicsguard or logicguard")
    parser.add_argument("--output", help="Optional output closure JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = adapt_provider(args.provider_result, args.provider)
    if args.output:
        dump_json(result, args.output)
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
