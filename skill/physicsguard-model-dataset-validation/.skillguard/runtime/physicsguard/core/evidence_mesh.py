"""Evidence mesh review for strong PhysicsGuard claim readiness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from physicsguard.io.test_file_contract_loader import load_evidence_mesh
from physicsguard.schema.evidence_mesh import (
    CodeContractSpec,
    EvidenceMeshFindingSpec,
    EvidenceMeshReportSpec,
    EvidenceMeshSpec,
    EvidenceMeshTestEvidenceSpec,
    RouteId,
)


@dataclass(frozen=True)
class EvidenceMeshFinding:
    severity: str
    type: str
    message: str
    source: str
    target: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceMeshReport:
    artifact_kind: str
    mesh_id: str
    claim_scope: str
    status: str
    ok: bool
    route_status: dict[str, str]
    blocking_findings: list[dict[str, Any]]
    review_findings: list[dict[str, Any]]
    optional_findings: list[dict[str, Any]]
    safe_claim: str
    unsafe_claim_boundary: str
    next_actions: list[str]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_evidence_mesh(path: str | Path) -> EvidenceMeshReport:
    """Load and review an evidence mesh YAML artifact."""

    return review_evidence_mesh(load_evidence_mesh(path))


def review_evidence_mesh(mesh: EvidenceMeshSpec) -> EvidenceMeshReport:
    """Review a parsed evidence mesh artifact."""

    findings: list[EvidenceMeshFinding] = []
    route_status: dict[str, str] = {}

    _check_required_route_payloads(mesh, findings)
    _check_model_mesh(mesh, findings)
    _check_model_test_alignment(mesh, findings)
    _check_contract_exhaustion(mesh, findings)
    _check_test_mesh(mesh, findings)
    _check_field_lifecycle(mesh, findings)
    _check_risk_ledger(mesh, findings)

    for route in mesh.required_routes:
        route_findings = [item for item in findings if item.source == route]
        if any(item.severity == "error" for item in route_findings):
            route_status[route] = "fail"
        elif any(item.severity == "warning" for item in route_findings):
            route_status[route] = "partial"
        else:
            route_status[route] = "pass"

    blocking = [finding for finding in findings if finding.severity == "error"]
    review = [finding for finding in findings if finding.severity == "warning"]
    optional = [finding for finding in findings if finding.severity == "info"]
    if blocking:
        status = "fail"
    elif review:
        status = "partial"
    else:
        status = "pass"

    report = EvidenceMeshReport(
        artifact_kind="physicsguard_evidence_mesh_report",
        mesh_id=mesh.mesh_id,
        claim_scope=mesh.claim_scope,
        status=status,
        ok=status == "pass",
        route_status=route_status,
        blocking_findings=[item.to_dict() for item in blocking],
        review_findings=[item.to_dict() for item in review],
        optional_findings=[item.to_dict() for item in optional],
        safe_claim=_safe_claim(mesh, status),
        unsafe_claim_boundary=_unsafe_claim_boundary(mesh),
        next_actions=_next_actions(blocking, review),
        summary={
            "required_routes": list(mesh.required_routes),
            "parent_model_count": len(mesh.parent_models),
            "child_model_evidence_count": len(mesh.child_model_evidence),
            "model_obligation_count": len(mesh.model_obligations),
            "code_contract_count": len(mesh.code_contracts),
            "test_evidence_count": len(mesh.test_evidence),
            "contract_case_count": len(mesh.contract_cases),
            "test_suite_count": len(mesh.test_suites),
            "field_lifecycle_count": len(mesh.field_lifecycle),
            "risk_ledger_count": len(mesh.risk_ledger),
            "blocking_finding_count": len(blocking),
            "review_finding_count": len(review),
            "optional_finding_count": len(optional),
            "semantics": (
                "evidence mesh proves claim-readiness evidence closure inside "
                "the declared PhysicsGuard boundary; it is not physical correctness proof"
            ),
        },
    )
    EvidenceMeshReportSpec.model_validate(report.to_dict())
    return report


def _check_required_route_payloads(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    required: dict[RouteId, tuple[int, str]] = {
        "model_mesh": (len(mesh.parent_models), "parent model mesh rows"),
        "model_test_alignment": (len(mesh.model_obligations), "model obligations"),
        "contract_exhaustion": (len(mesh.contract_cases), "generated contract cases"),
        "test_mesh": (len(mesh.test_suites), "test mesh suite rows"),
        "field_lifecycle": (len(mesh.field_lifecycle), "field lifecycle rows"),
        "risk_ledger": (len(mesh.risk_ledger), "risk ledger rows"),
    }
    for route in mesh.required_routes:
        count, label = required[route]
        if count == 0:
            findings.append(_finding("error", "required_route_missing_rows", f"required route has no {label}", route))


def _check_model_mesh(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    child_by_id = {item.evidence_id: item for item in mesh.child_model_evidence}
    for parent in mesh.parent_models:
        if parent.status != "pass" or parent.freshness != "current":
            findings.append(
                _finding(
                    "error",
                    "parent_model_mesh_not_current",
                    "parent model mesh evidence is not current passing evidence",
                    "model_mesh",
                    parent.model_id,
                    {"status": parent.status, "freshness": parent.freshness},
                )
            )
        for child_id in parent.required_child_evidence_ids:
            child = child_by_id.get(child_id)
            if child is None:
                findings.append(_finding("error", "required_child_evidence_missing", "required child evidence is missing", "model_mesh", child_id))
                continue
            if child.evidence_id not in parent.consumed_child_evidence_ids:
                findings.append(
                    _finding(
                        "error",
                        "child_evidence_not_consumed_by_parent",
                        "child evidence is local-only and has not been consumed by the parent mesh",
                        "model_mesh",
                        child.evidence_id,
                        {"parent_model_id": parent.model_id},
                    )
                )
            if child.status != "pass" or child.freshness != "current":
                findings.append(
                    _finding(
                        "error",
                        "child_evidence_not_current",
                        "child evidence is not current passing evidence",
                        "model_mesh",
                        child.evidence_id,
                        {"status": child.status, "freshness": child.freshness},
                    )
                )
            if child.parent_model_id and child.parent_model_id != parent.model_id:
                findings.append(
                    _finding(
                        "error",
                        "child_parent_mismatch",
                        "child evidence names a different parent model",
                        "model_mesh",
                        child.evidence_id,
                        {"child_parent_model_id": child.parent_model_id, "parent_model_id": parent.model_id},
                    )
                )
            if not child.inputs_accepted or not child.outputs_emitted:
                findings.append(
                    _finding(
                        "error",
                        "child_interface_incomplete",
                        "child evidence must declare accepted inputs and emitted outputs",
                        "model_mesh",
                        child.evidence_id,
                    )
                )
        for item in parent.partition_items:
            if item.ownership == "out_of_scope" and not item.scoped_out_reason:
                findings.append(_finding("error", "partition_out_of_scope_without_reason", "out-of-scope partition item lacks rationale", "model_mesh", item.item_id))


def _check_model_test_alignment(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    contracts = list(mesh.code_contracts)
    tests = list(mesh.test_evidence)
    obligation_ids = {item.obligation_id for item in mesh.model_obligations}
    for contract in contracts:
        for obligation_id in contract.model_obligation_ids:
            if obligation_id not in obligation_ids:
                findings.append(
                    _finding(
                        "error",
                        "code_contract_unknown_obligation",
                        "code contract references an unknown model obligation",
                        "model_test_alignment",
                        contract.contract_id,
                        {"obligation_id": obligation_id},
                    )
                )
        if contract.status != "pass":
            findings.append(_finding("error", "code_contract_not_pass", "code contract status is not pass", "model_test_alignment", contract.contract_id))

    for obligation in mesh.model_obligations:
        if not obligation.required:
            continue
        owner_contracts = [contract for contract in contracts if obligation.obligation_id in contract.model_obligation_ids and contract.required]
        if not owner_contracts:
            findings.append(
                _finding(
                    "error",
                    "required_obligation_missing_code_contract",
                    "required model obligation has no owner code contract",
                    "model_test_alignment",
                    obligation.obligation_id,
                )
            )
            continue
        if not any(_has_passing_test(obligation.obligation_id, contract, tests) for contract in owner_contracts):
            findings.append(
                _finding(
                    "error",
                    "required_obligation_missing_external_test",
                    "required model obligation has no current passing test bound to its owner code contract",
                    "model_test_alignment",
                    obligation.obligation_id,
                    {"code_contract_ids": [contract.contract_id for contract in owner_contracts]},
                )
            )

    contract_ids = {item.contract_id for item in contracts}
    for test in tests:
        for obligation_id in test.covers_obligation_ids:
            if obligation_id not in obligation_ids:
                findings.append(_finding("error", "test_unknown_obligation", "test evidence references an unknown model obligation", "model_test_alignment", test.evidence_id, {"obligation_id": obligation_id}))
        for contract_id in test.covers_code_contract_ids:
            if contract_id not in contract_ids:
                findings.append(_finding("error", "test_unknown_code_contract", "test evidence references an unknown code contract", "model_test_alignment", test.evidence_id, {"contract_id": contract_id}))
        if test.status == "pass" and test.freshness == "current" and not test.result_ref:
            findings.append(_finding("error", "test_evidence_missing_result_ref", "passing current test evidence needs a result reference", "model_test_alignment", test.evidence_id))


def _has_passing_test(obligation_id: str, contract: CodeContractSpec, tests: list[EvidenceMeshTestEvidenceSpec]) -> bool:
    return any(
        test.status == "pass"
        and test.freshness == "current"
        and test.scope in {"external", "mixed"}
        and not test.progress_only
        and test.result_ref
        and obligation_id in test.covers_obligation_ids
        and contract.contract_id in test.covers_code_contract_ids
        for test in tests
    )


def _check_contract_exhaustion(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    test_by_id = {item.evidence_id: item for item in mesh.test_evidence}
    for case in mesh.contract_cases:
        if case.required and not case.generated:
            findings.append(_finding("error", "contract_case_not_generated", "required bad case is hand-written only and lacks generated coverage authority", "contract_exhaustion", case.case_id))
        if not case.oracle:
            findings.append(_finding("error", "contract_case_missing_oracle", "contract case requires an oracle", "contract_exhaustion", case.case_id))
        owner = test_by_id.get(case.owner_test_evidence_id)
        if owner is None:
            findings.append(_finding("error", "contract_case_owner_test_missing", "contract case owner test evidence is missing", "contract_exhaustion", case.case_id, {"owner_test_evidence_id": case.owner_test_evidence_id}))
        elif owner.status != "pass" or owner.freshness != "current" or owner.progress_only:
            findings.append(_finding("error", "contract_case_owner_test_not_current", "contract case owner test is not current passing evidence", "contract_exhaustion", case.case_id, {"owner_test_evidence_id": owner.evidence_id}))
        if case.required and not case.downstream_routes:
            findings.append(_finding("error", "contract_case_not_consumed_downstream", "required contract case has no downstream route consumers", "contract_exhaustion", case.case_id))


def _check_test_mesh(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    suite_by_id = {item.suite_id: item for item in mesh.test_suites}
    for suite in mesh.test_suites:
        if suite.status != "pass" or suite.freshness != "current" or suite.progress_only:
            findings.append(_finding("error", "test_suite_not_current", "test suite is not current passing evidence", "test_mesh", suite.suite_id, {"status": suite.status, "freshness": suite.freshness, "progress_only": suite.progress_only}))
        if suite.status == "pass" and suite.freshness == "current" and not suite.result_ref:
            findings.append(_finding("error", "test_suite_missing_result_ref", "current passing test suite needs a result reference", "test_mesh", suite.suite_id))
        if suite.suite_kind == "parent":
            for child_id in suite.child_suite_ids:
                child = suite_by_id.get(child_id)
                if child is None:
                    findings.append(_finding("error", "child_test_suite_missing", "parent test suite references missing child suite", "test_mesh", suite.suite_id, {"child_suite_id": child_id}))
                    continue
                if child_id not in suite.consumed_child_suite_ids:
                    findings.append(_finding("error", "child_test_suite_not_consumed", "parent test suite has not consumed child suite evidence", "test_mesh", suite.suite_id, {"child_suite_id": child_id}))
                if child.status != "pass" or child.freshness != "current" or child.progress_only:
                    findings.append(_finding("error", "child_test_suite_not_current", "child test suite is not current passing evidence", "test_mesh", child_id))


def _check_field_lifecycle(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    evidence_ids = {item.evidence_id for item in mesh.test_evidence} | {item.evidence_id for item in mesh.child_model_evidence}
    for row in mesh.field_lifecycle:
        if row.behavior_bearing:
            if not row.projection_target:
                findings.append(_finding("error", "behavior_field_missing_projection", "behavior-bearing field lacks projection target", "field_lifecycle", row.field_id))
            if not row.downstream_evidence_ids:
                findings.append(_finding("error", "behavior_field_missing_downstream_evidence", "behavior-bearing field lacks downstream evidence", "field_lifecycle", row.field_id))
        if row.lifecycle in {"renamed", "deprecated", "removed", "preserved"} and not row.old_field_disposition:
            findings.append(_finding("error", "old_field_missing_disposition", "old or compatibility field lacks disposition", "field_lifecycle", row.field_id))
        for evidence_id in row.downstream_evidence_ids:
            if evidence_id not in evidence_ids:
                findings.append(_finding("warning", "field_downstream_evidence_unknown", "field downstream evidence id was not found in mesh evidence rows", "field_lifecycle", row.field_id, {"evidence_id": evidence_id}))


def _check_risk_ledger(mesh: EvidenceMeshSpec, findings: list[EvidenceMeshFinding]) -> None:
    required_routes = set(mesh.required_routes)
    matching = [row for row in mesh.risk_ledger if row.claim_scope == mesh.claim_scope]
    if not matching:
        findings.append(_finding("error", "risk_ledger_claim_row_missing", "risk ledger has no row for the mesh claim scope", "risk_ledger", mesh.claim_scope))
        return
    for row in matching:
        if row.decision != "pass" or row.freshness != "current":
            findings.append(_finding("error", "risk_ledger_not_pass", "risk ledger decision is not current pass", "risk_ledger", row.risk_id, {"decision": row.decision, "freshness": row.freshness}))
        missing_routes = sorted(required_routes - set(row.consumed_routes))
        if missing_routes:
            findings.append(_finding("error", "risk_ledger_missing_required_routes", "risk ledger row omits required route receipts", "risk_ledger", row.risk_id, {"missing_routes": missing_routes}))


def _safe_claim(mesh: EvidenceMeshSpec, status: str) -> str:
    if status == "pass":
        return f"{mesh.claim_scope} evidence mesh passed inside the declared PhysicsGuard evidence boundary."
    if status == "partial":
        return f"{mesh.claim_scope} evidence mesh is partial; broad claims need visible scoped gaps."
    return f"{mesh.claim_scope} evidence mesh is blocked until route findings are resolved."


def _unsafe_claim_boundary(mesh: EvidenceMeshSpec) -> str:
    return (
        f"Do not claim {mesh.claim_scope} beyond the parent/child models, code contracts, tests, "
        "generated cases, field rows, risk-ledger receipts, and project evidence listed in this mesh. "
        "Evidence mesh closure is claim-readiness proof, not physical correctness proof."
    )


def _next_actions(blocking: Iterable[EvidenceMeshFinding], review: Iterable[EvidenceMeshFinding]) -> list[str]:
    actions: set[str] = set()
    for item in blocking:
        if item.source == "model_mesh":
            actions.add("reattach current child evidence to the parent model mesh")
        elif item.source == "model_test_alignment":
            actions.add("bind required model obligations to owner code contracts and current external tests")
        elif item.source == "contract_exhaustion":
            actions.add("generate canonical bad cases with oracle and current downstream test evidence")
        elif item.source == "test_mesh":
            actions.add("refresh parent and child test mesh evidence before broad claims")
        elif item.source == "field_lifecycle":
            actions.add("close behavior-bearing field lifecycle and old-field dispositions")
        elif item.source == "risk_ledger":
            actions.add("update the risk ledger to consume all required route receipts")
    if list(review):
        actions.add("review scoped or unknown evidence ids before release confidence")
    return sorted(actions)


def _finding(
    severity: str,
    kind: str,
    message: str,
    source: str,
    target: str | None = None,
    details: dict[str, Any] | None = None,
) -> EvidenceMeshFinding:
    item = EvidenceMeshFinding(severity, kind, message, source, target, details or {})
    EvidenceMeshFindingSpec.model_validate(item.to_dict())
    return item


__all__ = ["EvidenceMeshFinding", "EvidenceMeshReport", "check_evidence_mesh", "review_evidence_mesh"]
