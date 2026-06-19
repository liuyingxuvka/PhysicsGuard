from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import (
    REQUIRED_CLOSURE_KEYS,
    as_list,
    closure_result,
    load_struct,
    normalize_status,
    write_json,
)


BROAD_CLAIMS = {
    "pass",
    "validated",
    "fully_validated",
    "active_validated",
    "active_reusable",
    "reusable",
}


def _provider_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("providers"), list):
        return data["providers"]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _catalog_claims(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for key in ("claim", "status", "validation_state", "lifecycle_state"):
        if key in catalog:
            claims.append({"id": key, "value": str(catalog[key]).lower()})
    for project in as_list(catalog.get("projects")):
        if not isinstance(project, dict):
            continue
        for key in ("claim", "status", "validation_state", "lifecycle_state"):
            if key in project:
                claims.append(
                    {
                        "id": project.get("id") or project.get("project_id") or key,
                        "field": key,
                        "value": str(project[key]).lower(),
                    }
                )
    return claims


def check_closure(provider_paths: list[str | Path], catalog_path: str | Path | None = None) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_path in provider_paths:
        providers.extend(_provider_records(load_struct(provider_path)))

    evidence: list[Any] = []
    missing_inputs: list[Any] = []
    stale_evidence: list[Any] = []
    skipped_checks: list[Any] = []
    next_actions: list[str] = []

    if not providers:
        missing_inputs.append({"id": "providers", "reason": "no_provider_results"})

    aggregate_status = "pass"
    for index, provider in enumerate(providers):
        provider_id = provider.get("id") or provider.get("provider") or f"provider_{index + 1}"
        missing_keys = sorted(REQUIRED_CLOSURE_KEYS - set(provider.keys()))
        if missing_keys:
            missing_inputs.append({"id": provider_id, "missing_fields": missing_keys})
            aggregate_status = "blocked"
            continue
        provider_status = normalize_status(provider.get("status"))
        evidence.append({"id": provider_id, "status": provider_status, "safe_claim": provider.get("safe_claim", "")})
        stale_evidence.extend({"provider": provider_id, **item} for item in as_list(provider.get("stale_evidence")))
        skipped_checks.extend({"provider": provider_id, **item} for item in as_list(provider.get("skipped_checks")))
        if provider.get("missing_inputs"):
            missing_inputs.extend({"provider": provider_id, **item} for item in as_list(provider.get("missing_inputs")))
        if provider_status == "blocked":
            aggregate_status = "blocked"
        elif provider_status in {"partial", "downgraded"} and aggregate_status == "pass":
            aggregate_status = provider_status

    if missing_inputs or stale_evidence or skipped_checks:
        aggregate_status = "blocked"

    catalog_conflicts: list[Any] = []
    if catalog_path:
        catalog = load_struct(catalog_path)
        for claim in _catalog_claims(catalog):
            if claim["value"] in BROAD_CLAIMS and aggregate_status != "pass":
                catalog_conflicts.append(
                    {
                        **claim,
                        "reason": "catalog_claim_exceeds_current_closure",
                        "closure_status": aggregate_status,
                    }
                )

    status = aggregate_status
    if catalog_conflicts:
        status = "downgraded"
        next_actions.append("Downgrade catalog/status claims or refresh blocked provider evidence.")
    elif status != "pass":
        next_actions.append("Resolve missing, stale, skipped, or blocked provider evidence before broad claims.")

    unsafe = "" if status == "pass" else "Do not claim database pass, validated, or reusable for this scope."
    safe = "All checked provider closures are current for the requested scope." if status == "pass" else ""
    return closure_result(
        status,
        evidence=evidence,
        missing_inputs=missing_inputs,
        stale_evidence=stale_evidence,
        skipped_checks=skipped_checks,
        safe_claim=safe,
        unsafe_claim_boundary=unsafe,
        next_actions=next_actions,
        extra={"catalog_conflicts": catalog_conflicts},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate DataBank provider closures.")
    parser.add_argument("--provider", action="append", required=True, help="Provider closure JSON/YAML file")
    parser.add_argument("--catalog", help="Optional catalog/status JSON/YAML file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = check_closure(args.provider, args.catalog)
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
