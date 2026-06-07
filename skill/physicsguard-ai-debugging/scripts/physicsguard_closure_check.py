#!/usr/bin/env python
"""Wrap PhysicsGuard hierarchy audit results in a Guard-family closure report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def _run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True)
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-6000:],
        "stderr": completed.stderr[-4000:],
    }


def _finding(severity: str, kind: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"severity": severity, "type": kind, "message": message, **extra}


def _extract_json(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def check(args: argparse.Namespace) -> dict[str, Any]:
    ledger = _load_json(args.ledger)
    checked_inputs: list[dict[str, str]] = []
    findings: list[dict[str, Any]] = []
    missing_inputs: list[dict[str, str]] = []
    stale_evidence: list[dict[str, str]] = []
    skipped_checks: list[dict[str, str]] = []
    command_results: list[dict[str, Any]] = []
    audit_data: dict[str, Any] = {}

    if args.audit is None:
        missing_inputs.append({"field": "audit", "message": "No PhysicsGuard audit/hierarchy file was provided."})
    elif args.observed is None:
        missing_inputs.append({"field": "observed", "message": "No observed snapshot was provided."})
    else:
        checked_inputs.append({"check": "physicsguard_hierarchy_evaluate", "path": str(args.audit)})
        command = [sys.executable, "-m", "physicsguard.cli", "hierarchy", "evaluate", str(args.audit), str(args.observed), "--pretty"]
        result = _run(command)
        command_results.append(result)
        if result["returncode"] != 0:
            findings.append(_finding("error", "physicsguard_evaluate_failed", "PhysicsGuard hierarchy evaluate failed.", command=result["command"]))
        audit_data = _extract_json(result["stdout"])

        plan = _run([sys.executable, "-m", "physicsguard.cli", "hierarchy", "plan", str(args.audit), "--pretty"])
        command_results.append(plan)
        if plan["returncode"] != 0:
            findings.append(_finding("warning", "physicsguard_plan_failed", "PhysicsGuard hierarchy plan did not produce refinement data.", command=plan["command"]))

    merged = {**audit_data, **ledger}
    if merged.get("audit_pass") is False:
        findings.append(_finding("error", "audit_failed", "PhysicsGuard audit_pass is false."))

    for field in ("missing_required_variables", "missing_required_parameters", "recommended_refinements", "bug_family_followups"):
        rows = _list(merged.get(field))
        if rows:
            severity = "error" if field.startswith("missing_required") else "warning"
            findings.append(_finding(severity, field, f"PhysicsGuard reported {field}.", count=len(rows), rows=rows))

    signal_rows = _list(merged.get("signal_mapping_ledger"))
    review_rows = [
        row for row in signal_rows
        if isinstance(row, dict) and str(row.get("review_required", "")).lower() in {"true", "yes", "1"}
    ]
    if review_rows:
        findings.append(_finding("warning", "signal_mapping_review_required", "Signal mappings still need review.", count=len(review_rows), rows=review_rows))

    if str(ledger.get("observed_snapshot_changed_after_audit", "")).lower() in {"true", "yes", "1"}:
        stale_evidence.append({"field": "observed_snapshot_changed_after_audit", "message": "Observed snapshot changed after audit."})

    for item in ledger.get("skipped_checks", []) if isinstance(ledger.get("skipped_checks"), list) else []:
        skipped_checks.append({"check": str(item), "message": "PhysicsGuard ledger records a skipped check."})

    if missing_inputs:
        findings.append(_finding("warning", "physicsguard_missing_inputs", "PhysicsGuard closure inputs are incomplete.", count=len(missing_inputs)))
    if stale_evidence:
        findings.append(_finding("error", "stale_physicsguard_evidence", "PhysicsGuard evidence is stale.", count=len(stale_evidence)))

    hard = any(str(item.get("severity", "")).lower() in {"error", "blocker"} for item in findings)
    declared = str(ledger.get("closure_status", "")).lower()
    if hard:
        closure_status = "blocked"
    elif declared in {"passed", "partial", "blocked", "downgraded"}:
        closure_status = declared
    elif findings or missing_inputs:
        closure_status = "partial"
    else:
        closure_status = "passed"

    next_actions = []
    if missing_inputs:
        next_actions.append({"owner": "physicsguard-ai-debugging", "action": "provide_audit_and_observed_snapshot"})
    if any(item.get("type", "").startswith("missing_required") for item in findings):
        next_actions.append({"owner": "physicsguard-ai-debugging", "action": "request_next_required_signals_or_parameters"})
    if any(item.get("type") == "recommended_refinements" for item in findings):
        next_actions.append({"owner": "physicsguard-ai-debugging", "action": "refine_suspicious_block_one_level"})
    if any(item.get("type") == "bug_family_followups" for item in findings):
        next_actions.append({"owner": "physicsguard-ai-debugging", "action": "inspect_same_family_unit_sign_map_or_balance_followups"})
    if stale_evidence:
        next_actions.append({"owner": "flowguard", "action": "rerun_physicsguard_after_observed_snapshot_change"})

    return {
        "owner_guard": "physicsguard-ai-debugging",
        "artifact_kind": "physicsguard_closure",
        "closure_status": closure_status,
        "checked_inputs": checked_inputs,
        "findings": findings,
        "missing_inputs": missing_inputs,
        "stale_evidence": stale_evidence,
        "skipped_checks": skipped_checks,
        "next_actions": next_actions,
        "safe_claim": ledger.get("safe_claim", "PhysicsGuard can localize low-fidelity residual and mapping issues within the checked audit boundary."),
        "unsafe_claim_boundary": ledger.get("unsafe_claim_boundary", "Do not claim commercial-model equivalence, high-fidelity proof, or full localization while variables, mappings, refinements, or same-family followups remain open."),
        "command_results": command_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PhysicsGuard closure checks.")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--observed", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = check(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['closure_status'].upper()}: PhysicsGuard closure")
        for finding in result["findings"]:
            print(f"- {finding.get('severity', 'warning')}: {finding.get('type', '')}".rstrip())
    return 0 if result["closure_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
