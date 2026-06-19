from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import (
    ACTIVE_BROAD_STATES,
    LIFECYCLE_STATES,
    TERMINAL_LIFECYCLE_STATES,
    append_jsonl,
    closure_result,
    dump_json,
    load_struct,
    normalize_lifecycle_state,
    normalize_status,
    utc_now,
    write_json,
)


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"candidate", "placeholder", "active_registered", "blocked"},
    "candidate": {"placeholder", "active_registered", "blocked", "rejected", "archived"},
    "placeholder": {"candidate", "active_registered", "blocked", "rejected", "archived"},
    "active_registered": {"active_validated", "blocked", "archived", "deprecated", "superseded"},
    "active_validated": {"active_reusable", "blocked", "downgraded", "archived", "deprecated", "superseded"},
    "active_reusable": {"blocked", "downgraded", "archived", "deprecated", "superseded"},
    "blocked": {"candidate", "active_registered", "archived", "rejected"},
    "downgraded": {"active_registered", "blocked", "archived", "deprecated", "superseded"},
    "archived": set(),
    "deprecated": set(),
    "superseded": set(),
    "rejected": set(),
}


def _catalog_path(root: Path) -> Path:
    return root / "database_catalog.json"


def _history_path(root: Path) -> Path:
    return root / "database_history.jsonl"


def _find_project(catalog: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for project in catalog.setdefault("projects", []):
        if isinstance(project, dict) and str(project.get("id") or project.get("project_id")) == project_id:
            return project
    return None


def _closure_status(path: str | Path | None) -> tuple[str, list[Any]]:
    if not path:
        return "blocked", [{"id": "closure", "reason": "required_for_broad_lifecycle_state"}]
    data = load_struct(path)
    status = normalize_status(data.get("status") if isinstance(data, dict) else None)
    issues: list[Any] = []
    if status != "pass":
        issues.append({"id": "closure", "path": str(path), "reason": "closure_not_pass", "status": status})
    if isinstance(data, dict):
        for key in ("missing_inputs", "stale_evidence", "skipped_checks"):
            if data.get(key):
                issues.append({"id": key, "path": str(path), "reason": f"closure_has_{key}"})
    return status, issues


def update_lifecycle(
    database_root: str | Path,
    project_id: str,
    target_state: str,
    *,
    reason: str,
    closure_path: str | Path | None = None,
    apply: bool = False,
    actor: str = "databank_lifecycle",
) -> dict[str, Any]:
    root = Path(database_root).resolve()
    catalog_path = _catalog_path(root)
    history_path = _history_path(root)
    missing_inputs: list[Any] = []
    evidence: list[Any] = []

    if not catalog_path.exists():
        return closure_result(
            "blocked",
            missing_inputs=[{"id": "database_catalog", "path": str(catalog_path), "reason": "missing"}],
            unsafe_claim_boundary="Cannot update lifecycle without a DataBank catalog.",
            next_actions=["Initialize or repair the DataBank root."],
        )

    state = normalize_lifecycle_state(target_state)
    if state not in LIFECYCLE_STATES:
        missing_inputs.append({"id": "target_state", "value": target_state, "reason": "unknown_lifecycle_state"})
    if not reason.strip():
        missing_inputs.append({"id": "reason", "reason": "required_for_history_event"})

    catalog = load_struct(catalog_path)
    if not isinstance(catalog, dict):
        return closure_result(
            "blocked",
            missing_inputs=[{"id": "database_catalog", "path": str(catalog_path), "reason": "not_an_object"}],
            unsafe_claim_boundary="Cannot update lifecycle from a malformed catalog.",
            next_actions=["Repair database_catalog.json."],
        )

    project = _find_project(catalog, project_id)
    old_state = normalize_lifecycle_state(project.get("lifecycle_state") if project else "new")
    if old_state in TERMINAL_LIFECYCLE_STATES:
        missing_inputs.append({"id": project_id, "reason": "terminal_state_cannot_be_silently_reopened", "old_state": old_state})
    elif state not in ALLOWED_TRANSITIONS.get(old_state, set()):
        missing_inputs.append(
            {
                "id": project_id,
                "reason": "transition_not_allowed",
                "old_state": old_state,
                "target_state": state,
                "allowed": sorted(ALLOWED_TRANSITIONS.get(old_state, set())),
            }
        )

    if state in ACTIVE_BROAD_STATES:
        closure_status, closure_issues = _closure_status(closure_path)
        evidence.append({"id": "closure", "path": str(closure_path), "status": closure_status})
        missing_inputs.extend(closure_issues)

    if missing_inputs:
        return closure_result(
            "blocked",
            evidence=evidence,
            missing_inputs=missing_inputs,
            unsafe_claim_boundary="Do not update broad or terminal lifecycle state until the transition is supported.",
            next_actions=["Provide a supported transition, reason, and passing closure evidence when required."],
        )

    event = {
        "event_type": "lifecycle_transition",
        "project_id": project_id,
        "old_state": old_state,
        "new_state": state,
        "reason": reason,
        "actor": actor,
        "created_at": utc_now(),
        "closure_path": str(closure_path) if closure_path else None,
        "applied": apply,
    }
    updated_project = dict(project or {"id": project_id})
    updated_project["id"] = project_id
    updated_project["lifecycle_state"] = state
    updated_project["last_lifecycle_event"] = event
    if project is None:
        catalog.setdefault("projects", []).append(updated_project)
    else:
        project.clear()
        project.update(updated_project)

    if apply:
        dump_json(catalog, catalog_path)
        append_jsonl(history_path, event)

    return closure_result(
        "pass",
        evidence=evidence + [{"id": "lifecycle_event", **event}],
        safe_claim="Lifecycle transition is supported and recorded." if apply else "Lifecycle transition dry-run is supported.",
        next_actions=[] if apply else ["Rerun with --apply to write the catalog and history event."],
        extra={"catalog_path": str(catalog_path), "history_path": str(history_path), "project": updated_project, "dry_run": not apply},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or apply a DataBank lifecycle transition.")
    parser.add_argument("database_root", help="Explicit DataBank root")
    parser.add_argument("project_id", help="Project id")
    parser.add_argument("--state", required=True, help="Target lifecycle state")
    parser.add_argument("--reason", required=True, help="Reason saved to history")
    parser.add_argument("--closure", help="Closure report required for active_validated or active_reusable")
    parser.add_argument("--actor", default="databank_lifecycle", help="History actor")
    parser.add_argument("--apply", action="store_true", help="Write catalog and history event")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = update_lifecycle(
        args.database_root,
        args.project_id,
        args.state,
        reason=args.reason,
        closure_path=args.closure,
        apply=args.apply,
        actor=args.actor,
    )
    write_json(result, pretty=args.pretty)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
