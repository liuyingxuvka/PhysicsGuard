"""Refresh PhysicsGuard SkillGuard V2 purpose and blockability authorities.

The table in this file is the reviewable source for route-specific protected
purposes, independently discovered external universes, semantic obligations,
and native failure classes. Generated JSON stays target-local and current-only.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
import shutil


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"
AUTHORITY_DIR = ".skillguard/authority-templates"
PURPOSE_MARKER_START = "<!-- BEGIN MANAGED PURPOSE AND BLOCKABILITY -->"
PURPOSE_MARKER_END = "<!-- END MANAGED PURPOSE AND BLOCKABILITY -->"
SKILLGUARD_LAYER_START = "<!-- BEGIN SKILLGUARD CONTRACT LAYER -->"
SKILLGUARD_LAYER_END = "<!-- END SKILLGUARD CONTRACT LAYER -->"
PURPOSE_CAPABILITIES = {
    "independent-external-universe.v1",
    "purpose-contract-identity.v1",
    "semantic-calibration-sensitivity.v1",
}
CANONICAL_SATELLITE = SKILL_ROOT / "physicsguard-ai-debugging" / ".skillguard" / "runtime"
PRIMARY_RUNTIME = (
    SKILL_ROOT
    / "physicsguard-model-dataset-validation"
    / ".skillguard"
    / "runtime"
    / "physicsguard"
)


def failure(suffix: str, title: str, block_when: str) -> dict[str, str]:
    return {"suffix": suffix, "title": title, "block_when": block_when}


def binding_id_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


TARGETS: dict[str, dict[str, Any]] = {
    "physicsguard-ai-debugging": {
        "purpose": "Localize a visible engineering-simulation fault only when current physical boundaries, topology, mappings, residuals, assumptions, and evidence depth support that localization.",
        "claim_boundary": "This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.",
        "failures": [
            failure("symptom-mislocalized", "Symptom or residual mislocalized", "the visible symptom, failing subsystem, or residual source is not supported by current native evidence"),
            failure("physical-boundary-violation", "Physical boundary or topology violation", "units, signs, balances, connectivity, or declared physical boundaries are inconsistent"),
            failure("mapping-identity-wrong", "Signal or parameter mapping is wrong", "a signal, parameter, revision, conversion, or target variable binding is missing, stale, or inconsistent"),
            failure("validation-too-shallow", "Validation evidence is too shallow", "the available object, signal, parameter, scenario, or time universe is not adequately evaluated"),
            failure("assumption-or-scope-overreach", "Assumption or claim scope is overreached", "an unresolved assumption, access gap, or bounded result is promoted beyond the checked scope"),
        ],
        "external": [
            ("observed-symptom", "Current visible symptom and failure evidence", "project symptom report and native diagnostic artifacts"),
            ("physical-boundary", "Current physical boundary, units, topology, and subsystem inventory", "model-understanding preflight and target model structure"),
            ("mapped-evidence", "Current signal, parameter, dataset, and mapping inventory", "project evidence registry and target-owned mappings"),
            ("validation-scope", "Current validation, assumptions, scenario, and claim-scope inventory", "native validation and closure plans"),
        ],
        "failure_by_obligation": {
            "visible_symptom": "symptom-mislocalized", "physical_boundary": "physical-boundary-violation", "topology_inventory": "physical-boundary-violation", "signal_parameter_mapping": "mapping-identity-wrong", "validation_depth": "validation-too-shallow", "residual_localization": "symptom-mislocalized", "assumption_boundary": "assumption-or-scope-overreach", "safe_claim_boundary": "assumption-or-scope-overreach",
        },
    },
    "physicsguard-audit-closure": {
        "purpose": "Prevent an engineering audit from being declared complete while required native checks, current evidence, blockers, predictive conditions, or the bounded claim scope remain unresolved.",
        "claim_boundary": "Closure proves only the exact requested audit scope represented by current native receipts; skipped, stale, partial, and predictive gaps remain non-pass.",
        "failures": [
            failure("required-check-missing", "Required native check is missing", "the closure plan omits or lacks a current required PhysicsGuard check"),
            failure("stale-or-skipped-promoted", "Stale or skipped evidence is promoted", "stale, skipped, not-run, or foreign evidence is treated as passed"),
            failure("blocker-suppressed", "Unresolved blocker is suppressed", "a current native blocker or missing-input condition is absent from closure"),
            failure("predictive-overclaim", "Predictive readiness is overclaimed", "pointwise or non-predictive evidence is used for a predictive closure request"),
            failure("closure-scope-overreach", "Closure scope is overreached", "the final statement exceeds the exact checked evidence and assumptions"),
        ],
        "external": [
            ("closure-plan", "Requested closure profile and required checks", "target-owned closure plan"),
            ("native-receipts", "Current native check, validation-depth, and predictive receipts", "immutable PhysicsGuard receipt inventory"),
            ("open-blockers", "Current blockers, skipped checks, stale evidence, and missing inputs", "native audit result and evidence registry"),
            ("requested-claim", "Requested and covered claim scope", "closure request and native claim boundary"),
        ],
        "failure_by_obligation": {
            "closure_plan": "required-check-missing", "required_native_checks": "required-check-missing", "validation_depth": "stale-or-skipped-promoted", "blockers_reconciled": "blocker-suppressed", "stale_and_skipped_accounted": "stale-or-skipped-promoted", "predictive_rollout_if_requested": "predictive-overclaim", "safe_claim_boundary": "closure-scope-overreach",
        },
    },
    "physicsguard-candidate-model-blueprint": {
        "purpose": "Prevent generation of a candidate simulation blueprint until the hierarchy, block readiness, interfaces, signal/parameter mappings, and rollout boundary are validated for the requested bounded use.",
        "claim_boundary": "Generation eligibility covers only a candidate low-fidelity blueprint for the declared target and interfaces; it is not an implemented or validated high-fidelity model.",
        "failures": [
            failure("hierarchy-not-validated", "Hierarchy or blocks are not ready", "the required hierarchy, component blocks, or physical interfaces are missing or unvalidated"),
            failure("interface-mapping-incomplete", "Interface or mapping inventory is incomplete", "required signal, parameter, unit, or interface bindings are missing"),
            failure("rollout-boundary-unclear", "Rollout boundary is unclear", "the intended pointwise or stateful semantics and rollout limits are not explicit"),
            failure("generation-despite-blocker", "Generation proceeds despite a blocker", "generation eligibility is asserted while a required readiness condition is blocked"),
        ],
        "external": [
            ("validated-hierarchy", "Validated hierarchy and component-block inventory", "current PhysicsGuard hierarchy"),
            ("interface-inventory", "Required interfaces, signals, parameters, units, and mappings", "target model and mapping registry"),
            ("rollout-request", "Requested semantics and rollout boundary", "target-owned generation request"),
            ("readiness-findings", "Current readiness blockers and validation receipts", "native preflight and validation outputs"),
        ],
        "failure_by_obligation": {
            "validated_hierarchy": "hierarchy-not-validated", "block_readiness": "hierarchy-not-validated", "signal_parameter_mapping": "interface-mapping-incomplete", "interface_inventory": "interface-mapping-incomplete", "rollout_boundary": "rollout-boundary-unclear", "generation_eligibility": "generation-despite-blocker",
        },
    },
    "physicsguard-model-dataset-validation": {
        "purpose": "Prevent a model/dataset consistency or predictive claim unless exact model, dataset, mapping, signal, parameter, time, scenario, physical-envelope, and claim-scope obligations pass the native evaluator.",
        "claim_boundary": "A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.",
        "failures": [
            failure("validation-identity-wrong", "Validation identity is wrong", "the model, dataset, plan, mapping, split, or receipt identity is missing, stale, or mismatched"),
            failure("coverage-universe-shallow", "Coverage universe is shallow", "signals, parameters, timepoints, events, scenarios, or families are missing or inadequately sampled"),
            failure("physical-relation-violated", "Physical relation or envelope is violated", "native residual, unit, sign, balance, constitutive, or physical-envelope checks fail"),
            failure("prediction-semantics-overclaimed", "Prediction semantics are overclaimed", "pointwise evidence or a stale/partial rollout is used to authorize prediction"),
            failure("validation-scope-overreach", "Validation scope is overreached", "the requested claim exceeds the native receipt's covered scope"),
        ],
        "external": [
            ("dataset-manifest", "Current raw dataset rows, fields, cases, timestamps, and hashes", "target-owned data manifest"),
            ("model-hierarchy", "Current required variables, parameters, blocks, units, and assumptions", "validated model hierarchy"),
            ("mapping-and-roles", "Current signal/parameter mappings, role matrix, exclusions, and critical targets", "mapping ledger and role matrix"),
            ("validation-plan", "Current sampling, scenario, residual, envelope, split, and threshold plan", "target-owned validation plan"),
            ("prediction-holdout", "Current stateful rollout, initial state, horizon, and disjoint holdout identities", "predictive plan and holdout registry"),
        ],
        "failure_by_obligation": {
            "obligation:claim-scope-compatible": "validation-scope-overreach", "obligation:coverage-universe-adequate": "coverage-universe-shallow", "obligation:exact-validation-inputs": "validation-identity-wrong", "obligation:native-depth-receipt-current": "validation-identity-wrong", "obligation:per-parameter-depth-adequate": "coverage-universe-shallow", "obligation:per-signal-depth-adequate": "physical-relation-violated", "obligation:predictive-semantics-honest": "prediction-semantics-overclaimed",
        },
        "semantic_fixtures": {
            "validation-identity-wrong": {
                "test_node_id": "tests/test_validation_depth_receipts.py::test_changed_dataset_content_makes_receipt_stale",
                "assertion_kind": "native_finding_type",
                "expected_observation": "dataset_identity_stale",
            },
            "coverage-universe-shallow": {
                "test_node_id": "tests/test_validation_adequacy.py::test_10000_signals_with_only_two_selected_are_blocked",
                "assertion_kind": "native_finding_type",
                "expected_observation": "signal_coverage_ratio_not_met",
            },
            "physical-relation-violated": {
                "test_node_id": "tests/test_model_dataset_validation.py::test_conservative_calibration_does_not_turn_direct_failure_into_pass",
                "assertion_kind": "native_finding_type",
                "expected_observation": "direct_validation_audit_failed",
            },
            "prediction-semantics-overclaimed": {
                "test_node_id": "tests/test_predictive_rollout_validation.py::test_pointwise_prediction_is_forbidden",
                "assertion_kind": "native_finding_code",
                "expected_observation": "pointwise_prediction_forbidden",
            },
            "validation-scope-overreach": {
                "test_node_id": "tests/test_validation_adequacy.py::test_snapshot_receipt_cannot_satisfy_validation_ready_closure",
                "assertion_kind": "native_issue_code",
                "expected_observation": "snapshot_scope_incompatible",
            },
        },
    },
    "physicsguard-model-library": {
        "purpose": "Prevent reuse of a PhysicsGuard model asset unless its profile, testbench, compatibility evidence, gaps, validation receipt, and bounded reuse scope are current for the requested project.",
        "claim_boundary": "Library readiness licenses only the selected asset/profile/testbench combination and exact bounded reuse scope; it does not validate a new project automatically.",
        "failures": [
            failure("library-inventory-incomplete", "Library inventory is incomplete", "selected assets, profiles, or testbenches are absent from the current inventory"),
            failure("compatibility-not-proven", "Compatibility is not proven", "the selected asset and target testbench/model interfaces are incompatible or unevaluated"),
            failure("validation-or-gap-stale", "Validation or gap evidence is stale", "the validation receipt is stale, missing, or unresolved gaps are hidden"),
            failure("reuse-scope-overreach", "Reuse scope is overreached", "the requested reuse exceeds the validated compatibility boundary"),
        ],
        "external": [
            ("asset-catalog", "Current model asset and profile inventory", "PhysicsGuard model library index"),
            ("target-testbench", "Current target model/testbench/interface identity", "target project evidence registry"),
            ("compatibility-evidence", "Current compatibility, validation, and known-limit receipts", "library validation records"),
            ("reuse-request", "Requested reuse scope", "target-owned reuse request"),
        ],
        "failure_by_obligation": {
            "asset_inventory": "library-inventory-incomplete", "profile_inventory": "library-inventory-incomplete", "testbench_compatibility": "compatibility-not-proven", "gap_gate": "validation-or-gap-stale", "validation_receipt": "validation-or-gap-stale", "bounded_reuse_scope": "reuse-scope-overreach",
        },
    },
    "physicsguard-model-understanding-preflight": {
        "purpose": "Prevent physical audit or modeling work from starting with an unclear symptom, physical boundary, subsystem, signal, parameter, assumption, or access universe.",
        "claim_boundary": "Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.",
        "failures": [
            failure("symptom-or-boundary-unclear", "Symptom or physical boundary is unclear", "the visible symptom, units, operating boundary, or subsystem scope is missing"),
            failure("required-inventory-missing", "Required model inventory is missing", "required subsystems, signals, or parameters are absent from the discovered universe"),
            failure("assumption-hidden", "Assumption is hidden", "a material model or operating assumption is missing or unresolved"),
            failure("access-gap-suppressed", "Access gap is suppressed", "unavailable model, signal, parameter, or evidence access is not reported"),
        ],
        "external": [
            ("visible-symptom", "Current symptom and expected behavior", "target issue or audit request"),
            ("physical-scope", "Current physical, subsystem, unit, and operating boundary", "target model inventory"),
            ("required-signals-parameters", "Required signal and parameter inventory", "model hierarchy and testbench contract"),
            ("assumptions-access", "Current assumptions and access gaps", "project evidence registry"),
        ],
        "failure_by_obligation": {
            "visible_symptom": "symptom-or-boundary-unclear", "physical_boundary": "symptom-or-boundary-unclear", "subsystem_inventory": "required-inventory-missing", "signal_inventory": "required-inventory-missing", "parameter_inventory": "required-inventory-missing", "assumption_inventory": "assumption-hidden", "access_gaps": "access-gap-suppressed",
        },
    },
    "physicsguard-project-adoption": {
        "purpose": "Prevent a repository from claiming PhysicsGuard adoption when project records, supported toolchain identity, native artifact inventory, blockers, or required revalidation are absent or stale.",
        "claim_boundary": "Adoption proves only current workflow records and toolchain/artifact readiness; it never substitutes for model execution, validation, closure, installation, or release evidence.",
        "failures": [
            failure("adoption-record-stale", "Adoption record is stale", "project adoption records do not match the current repository or toolchain"),
            failure("toolchain-unsupported", "Toolchain is unsupported", "the real PhysicsGuard/FlowGuard toolchain is missing or incompatible"),
            failure("native-artifacts-incomplete", "Native artifact inventory is incomplete", "required project models, plans, registries, or receipts are missing"),
            failure("blocker-or-revalidation-omitted", "Blocker or revalidation is omitted", "known blockers or required affected checks are not preserved"),
        ],
        "external": [
            ("repository-records", "Current project adoption records", "repository AGENTS and project manifests"),
            ("toolchain-identity", "Current supported PhysicsGuard and FlowGuard identities", "installed runtime and project records"),
            ("native-artifacts", "Current native model, plan, registry, and receipt inventory", "repository discovery"),
            ("revalidation-scope", "Current blockers and affected revalidation set", "project audit result"),
        ],
        "failure_by_obligation": {
            "project_record_current": "adoption-record-stale", "toolchain_supported": "toolchain-unsupported", "native_artifact_inventory": "native-artifacts-incomplete", "blocker_inventory": "blocker-or-revalidation-omitted", "required_revalidation": "blocker-or-revalidation-omitted",
        },
    },
    "physicsguard-project-evidence-registry": {
        "purpose": "Prevent a project evidence claim from shrinking or misbinding the declared, discovered, required, excluded, role-bound, and critical file universe.",
        "claim_boundary": "Registry closure covers only the exact current project evidence bundle and declared roles/bindings; unresolved critical gaps or out-of-scope files remain blocking.",
        "failures": [
            failure("artifact-universe-shrunk", "Artifact universe is shrunk", "declared, discovered, required, or excluded files are not completely reconciled"),
            failure("binding-or-role-missing", "Binding or role is missing", "a required evidence-to-model edge or evidence role has no current proof"),
            failure("critical-gap-hidden", "Critical evidence gap is hidden", "a required or critical artifact is missing, stale, or invalidly excluded"),
            failure("bundle-scope-overreach", "Evidence bundle scope is overreached", "the claimed project scope exceeds the exact bound bundle"),
        ],
        "external": [
            ("filesystem-discovery", "Current discovered project files", "canonical project-root discovery"),
            ("declared-required-files", "Declared and required evidence inventory", "project profile and role contracts"),
            ("binding-graph", "Current evidence-to-model and evidence-to-check bindings", "project evidence registry"),
            ("exclusions-and-gaps", "Current exclusions, critical gaps, and bundle scope", "registry reconciliation"),
        ],
        "failure_by_obligation": {
            "artifact_inventory_reconciled": "artifact-universe-shrunk", "binding_edges": "binding-or-role-missing", "role_coverage": "binding-or-role-missing", "critical_gaps": "critical-gap-hidden", "bundle_scope": "bundle-scope-overreach",
        },
    },
    "physicsguard-signal-mapping-review": {
        "purpose": "Prevent an external signal from being treated as a PhysicsGuard variable unless target identity, unit/conversion, revision, confidence/review, temporal coverage, and mapping evidence are current.",
        "claim_boundary": "A mapping pass licenses only the exact external signal, target variable, conversion, revision, temporal range, and reviewed confidence in the receipt.",
        "failures": [
            failure("signal-target-mismatch", "Signal and target variable mismatch", "the governed external signal does not bind to the intended PhysicsGuard variable"),
            failure("unit-conversion-invalid", "Unit or conversion is invalid", "unit evidence or conversion semantics are missing, inconsistent, or physically invalid"),
            failure("revision-or-time-stale", "Revision or temporal evidence is stale", "revision identity or temporal coverage no longer matches the source data"),
            failure("review-confidence-unresolved", "Review or confidence is unresolved", "required review, evidence, or confidence disposition is incomplete"),
        ],
        "external": [
            ("governed-signals", "Current external signal inventory", "source/test-file contract"),
            ("target-variables", "Current PhysicsGuard target variable and unit inventory", "model hierarchy"),
            ("conversion-revision", "Current conversion, revision, and lineage evidence", "mapping ledger"),
            ("temporal-review", "Current temporal coverage, confidence, and review state", "mapping review records"),
        ],
        "failure_by_obligation": {
            "governed_mapping_inventory": "signal-target-mismatch", "unit_evidence": "unit-conversion-invalid", "conversion_evidence": "unit-conversion-invalid", "revision_evidence": "revision-or-time-stale", "confidence_review": "review-confidence-unresolved", "temporal_coverage": "revision-or-time-stale", "target_variable_binding": "signal-target-mismatch",
        },
    },
    "physicsguard-test-file-contract-review": {
        "purpose": "Prevent a test file from authorizing validation unless file/field identities, units, timing, testbench/model bindings, per-signal depth, mappings, and project gaps are complete and current.",
        "claim_boundary": "A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the receipt.",
        "failures": [
            failure("file-or-field-identity-missing", "File or field identity is missing", "a governed test file or required field is absent, stale, duplicated, or misidentified"),
            failure("unit-or-timing-mismatch", "Unit or timing contract mismatches", "field units, timestamps, step, duration, or temporal semantics are inconsistent"),
            failure("testbench-model-binding-wrong", "Testbench or model binding is wrong", "the file is bound to the wrong testbench, model, version, or interface"),
            failure("per-signal-evidence-shallow", "Per-signal evidence is shallow", "required signal depth or mapping evidence is missing or inadequate"),
            failure("project-gap-hidden", "Project-level gap is hidden", "a current project evidence gap is omitted from the contract result"),
        ],
        "external": [
            ("test-file-inventory", "Current governed test files and hashes", "project evidence registry"),
            ("field-contracts", "Current required fields, units, and timing identities", "test-file contract"),
            ("testbench-model-identity", "Current testbench/model/version/interface binding", "project profile"),
            ("signal-mapping-depth", "Current per-signal mappings, depth, and project gaps", "mapping ledger and validation plan"),
        ],
        "failure_by_obligation": {
            "file_inventory": "file-or-field-identity-missing", "field_inventory": "file-or-field-identity-missing", "unit_contract": "unit-or-timing-mismatch", "timing_contract": "unit-or-timing-mismatch", "testbench_binding": "testbench-model-binding-wrong", "model_binding": "testbench-model-binding-wrong", "per_signal_depth": "per-signal-evidence-shallow", "mapping_evidence": "per-signal-evidence-shallow", "project_gaps": "project-gap-hidden",
        },
    },
}


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def canonical_fingerprint(value: object) -> str:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest().upper()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def authority_documents(skill_id: str, config: dict[str, Any], obligations: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    failures = {
        row["suffix"]: {
            "failure_claim_id": f"failure:{skill_id}:{row['suffix']}",
            "title": row["title"],
            "block_when": row["block_when"],
        }
        for row in config["failures"]
    }
    mapped = config["failure_by_obligation"]
    if set(mapped) != set(obligations):
        raise ValueError(f"{skill_id}: obligation mapping mismatch: {sorted(set(obligations) ^ set(mapped))}")
    used = set(mapped.values())
    if used != set(failures):
        raise ValueError(f"{skill_id}: unowned failure claims: {sorted(set(failures) - used)}")
    semantic_rows = []
    for obligation in obligations:
        semantic_id = f"semantic-obligation:{skill_id}:{slug(obligation)}"
        failure_row = failures[mapped[obligation]]
        semantic_rows.append(
            {
                "semantic_obligation_id": semantic_id,
                "workflow_obligation_ids": [obligation],
                "oracle_id": f"oracle:{skill_id}:{slug(obligation)}",
                "description": f"The target-native oracle for '{obligation}' must evaluate the current independent external universe and block {failure_row['title'].lower()} when detected.",
                "protected_failure_claim_ids": [failure_row["failure_claim_id"]],
                "expected_finding_codes": [f"finding-code:{skill_id}:{slug(obligation)}-blocked"],
            }
        )
    purpose = {
        "schema_version": "skillguard.target_purpose_contract.v1",
        "target_skill_id": skill_id,
        "protected_purpose_statement": config["purpose"],
        "claim_boundary": config["claim_boundary"],
        "protected_failure_claims": list(failures.values()),
        "authoring_order": "freeze_before_candidate_model",
    }
    external = {
        "schema_version": "skillguard.target_external_universe.v1",
        "target_skill_id": skill_id,
        "universe_rule": "Derive the concrete production object set from the named target-owned sources before candidate modeling. This installed template is calibration guidance only and cannot authorize production.",
        "objects": [
            {
                "object_id": f"external-object:{skill_id}:{object_id}",
                "description": description,
                "discovery_source": source,
                "critical": True,
            }
            for object_id, description, source in config["external"]
        ],
    }
    semantic = {
        "schema_version": "skillguard.target_semantic_obligation_universe.v1",
        "target_skill_id": skill_id,
        "semantic_obligations": semantic_rows,
        "important_semantic_obligation_ids": [row["semantic_obligation_id"] for row in semantic_rows],
    }
    return purpose, external, semantic


def managed_prompt(config: dict[str, Any]) -> str:
    failures = "\n".join(f"- `{row['title']}`: block when {row['block_when']}." for row in config["failures"])
    return (
        f"{PURPOSE_MARKER_START}\n"
        "## Purpose and blockability contract\n\n"
        f"Protected purpose: {config['purpose']}\n\n"
        f"Bounded claim: {config['claim_boundary']}\n\n"
        "This route must block these declared failure classes when its target-native oracle detects them:\n\n"
        f"{failures}\n\n"
        "Before AI builds or fills a candidate model, it must: (1) write and freeze the target purpose contract; (2) derive the concrete external object universe from current target-owned sources, independently of the candidate; (3) declare every semantic obligation, native oracle, expected finding code, and protected failure mapping; and only then (4) build and evaluate the candidate model. The purpose, external-universe, semantic-universe, and candidate files must be four disjoint input roles.\n\n"
        "A broad claim requires every important semantic obligation to have a current target-native passed finding. Positive and shallow calibration must share the exact same purpose and universe identities; the shallow case must omit exactly one declared semantic obligation and be blocked for that exact reason. Installed authority templates are capability fixtures only and cannot close scheduled production.\n"
        f"{PURPOSE_MARKER_END}"
    )


def add_selector(edge: dict[str, Any], path: str) -> None:
    selectors = edge.setdefault("input_selectors", [])
    selector = {"kind": "path", "path": path}
    if selector not in selectors:
        selectors.append(selector)


def upgrade_target(skill_id: str, config: dict[str, Any]) -> None:
    skill_root = SKILL_ROOT / skill_id
    source_path = skill_root / ".skillguard" / "contract-source.json"
    contract = json.loads(source_path.read_text(encoding="utf-8"))
    profile = contract["depth_profile"]
    calibration = profile["calibration"]
    obligations = [str(item) for item in calibration["important_obligation_ids"]]
    purpose, external, semantic = authority_documents(skill_id, config, obligations)
    authority_root = skill_root / AUTHORITY_DIR
    authority_root.mkdir(parents=True, exist_ok=True)
    (authority_root / "purpose-contract.json").write_text(stable_json(purpose), encoding="utf-8")
    (authority_root / "external-universe.json").write_text(stable_json(external), encoding="utf-8")
    (authority_root / "semantic-obligation-universe.json").write_text(stable_json(semantic), encoding="utf-8")

    profile["purpose_contract_policy"] = {
        "policy_id": "skillguard.purpose_contract_policy.current",
        "provider_id": profile["provider_runtime"]["provider_id"],
        "native_check_id": calibration["native_evaluator_check_id"],
        "purpose_contract_input_role": "target_purpose_contract",
        "external_universe_input_role": "target_external_universe",
        "semantic_obligation_universe_input_role": "target_semantic_obligation_universe",
        "candidate_model_input_role": "candidate_model",
        "require_independent_external_universe": True,
        "require_nonempty_protected_failure_claims": True,
        "require_nonempty_semantic_obligations": True,
    }
    semantic_ids = semantic["important_semantic_obligation_ids"]
    calibration["important_semantic_obligation_ids"] = semantic_ids
    semantic_by_workflow = {
        row["workflow_obligation_ids"][0]: row["semantic_obligation_id"]
        for row in semantic["semantic_obligations"]
    }
    for case in calibration.get("shallow_cases", []):
        omitted = str(case["omitted_important_obligation_id"])
        case["omitted_semantic_obligation_id"] = semantic_by_workflow[omitted]
    for container in (calibration, profile["provider_runtime"]):
        container["required_capability_ids"] = sorted(
            set(container["required_capability_ids"]) | PURPOSE_CAPABILITIES
        )

    authority_paths = [
        f"{AUTHORITY_DIR}/purpose-contract.json",
        f"{AUTHORITY_DIR}/external-universe.json",
        f"{AUTHORITY_DIR}/semantic-obligation-universe.json",
    ]
    contract["implementation_paths"] = sorted(set(contract["implementation_paths"]) | set(authority_paths))
    overrides = [row for row in contract.get("content_role_overrides", []) if row.get("path") != AUTHORITY_DIR]
    overrides.append({
        "path": AUTHORITY_DIR,
        "role": "documentation_model",
        "install_disposition": "copy",
        "reason": "target-owned purpose, external-universe, and semantic-obligation templates",
    })
    contract["content_role_overrides"] = overrides
    edges = contract.get("portfolio_target_edges", [])
    if isinstance(edges, dict):
        edges = [edges]
        contract["portfolio_target_edges"] = edges
    for edge in edges:
        for path in authority_paths:
            add_selector(edge, path)
    source_path.write_text(stable_json(contract), encoding="utf-8")

    skill_path = skill_root / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    section = managed_prompt(config)
    if PURPOSE_MARKER_START in text or PURPOSE_MARKER_END in text:
        if text.count(PURPOSE_MARKER_START) != 1 or text.count(PURPOSE_MARKER_END) != 1:
            raise ValueError(f"{skill_id}: malformed managed purpose markers")
        prefix, remainder = text.split(PURPOSE_MARKER_START, 1)
        _, suffix = remainder.split(PURPOSE_MARKER_END, 1)
        text = prefix.rstrip() + "\n\n" + section + suffix
    else:
        text = text.rstrip() + "\n\n" + section + "\n"
    skill_path.write_text(text, encoding="utf-8")


def _current_obligations(skill_root: Path, contract: dict[str, Any]) -> list[str]:
    oracle_path = skill_root / "guard-model" / "oracles.json"
    if oracle_path.is_file():
        value = json.loads(oracle_path.read_text(encoding="utf-8"))
        rows = value.get("required_obligation_ids", [])
        if isinstance(rows, list) and rows:
            return [str(item) for item in rows]
    calibration = (contract.get("depth_profile") or {}).get("calibration") or {}
    rows = calibration.get("important_obligation_ids", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{skill_root.name}: cannot recover the native obligation inventory")
    return [str(item) for item in rows]


def _native_identity(
    skill_root: Path, skill_id: str, contract: dict[str, Any]
) -> tuple[str, str]:
    current_path = skill_root / "guard-model" / "contract.json"
    if current_path.is_file():
        current = json.loads(current_path.read_text(encoding="utf-8"))
        owner = str(current.get("native_owner_id", ""))
        route = str(current.get("native_route_id", ""))
        if owner and route:
            return owner, route
    if skill_id == "physicsguard-model-dataset-validation":
        return (
            str(contract.get("native_route_owner") or "physicsguard-model-dataset-validation"),
            "route:physicsguard-model-dataset-validation",
        )
    profile = contract.get("depth_profile") or {}
    owner = str(profile.get("native_owner_id", ""))
    routes = profile.get("native_route_ids") or []
    if not owner or not isinstance(routes, list) or len(routes) != 1:
        raise ValueError(f"{skill_id}: exact native owner/route cannot be recovered")
    return owner, str(routes[0])


def _guard_documents(
    skill_id: str,
    config: dict[str, Any],
    obligations: list[str],
    owner: str,
    route: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    failure_by_suffix = {row["suffix"]: row for row in config["failures"]}
    mapping = config["failure_by_obligation"]
    if set(mapping) != set(obligations):
        raise ValueError(
            f"{skill_id}: obligation mapping mismatch: {sorted(set(mapping) ^ set(obligations))}"
        )
    failures: list[dict[str, Any]] = []
    semantic_fixtures = config.get("semantic_fixtures") or {}
    semantic_detection = skill_id == "physicsguard-model-dataset-validation"
    for suffix, row in failure_by_suffix.items():
        fixture = semantic_fixtures.get(suffix)
        if semantic_detection and not isinstance(fixture, dict):
            raise ValueError(f"{skill_id}: semantic fixture missing for {suffix}")
        proof_strength = (
            "native_semantic_detection"
            if semantic_detection
            else "native_obligation_admission_gate"
        )
        original_title = row["title"]
        original_block_when = row["block_when"]
        failures.append(
            {
                "failure_id": f"failure:{skill_id}:{suffix}",
                "title": (
                    original_title
                    if semantic_detection
                    else f"Candidate is not proven against {original_title.lower()}"
                ),
                "block_when": (
                    original_block_when
                    if semantic_detection
                    else "the candidate lacks current passing target-native obligation evidence "
                    f"for this bounded route condition: {original_block_when}"
                ),
                "expected_finding_code": (
                    str(fixture["expected_observation"])
                    if semantic_detection
                    else "missing_target_obligation"
                ),
                "proof_strength": proof_strength,
                "known_limit": (
                    "The named target-native PhysicsGuard fixture and assertion prove only this bounded semantic failure and do not prove every future physical operating point."
                    if semantic_detection
                    else "This admission proof rejects a candidate whose governed obligation evidence is absent or native-failed; it does not detect the underlying physical, mapping, topology, or evidence defect and does not certify upstream truth."
                ),
                "claim_boundary": (
                    f"Native semantic detection is limited to {fixture['test_node_id']} and its asserted observation {fixture['expected_observation']!r}."
                    if semantic_detection
                    else "This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected."
                ),
            }
        )
    failure_ids = {row["failure_id"] for row in failures}
    oracles = []
    for obligation in obligations:
        suffix = mapping[obligation]
        failure_id = f"failure:{skill_id}:{suffix}"
        finding = next(
            row["expected_finding_code"] for row in failures if row["failure_id"] == failure_id
        )
        oracles.append(
            {
                "oracle_id": f"oracle:{skill_id}:{slug(obligation)}",
                "obligation_id": obligation,
                "failure_id": failure_id,
                "predicate_kind": (
                    "native_semantic_fixture_must_block"
                    if semantic_detection
                    else "native_obligation_admission_must_pass"
                ),
                "predicate": (
                    f"The exact target-native fixture for {failure_id!r} must assert the bounded semantic observation; otherwise semantic detection is unproved."
                    if semantic_detection
                    else f"The target-native result for {obligation!r} must be current and pass; otherwise candidate admission blocks with missing_target_obligation."
                ),
                "expected_finding_code": finding,
            }
        )
    first_obligation_by_failure: dict[str, str] = {}
    for oracle in oracles:
        first_obligation_by_failure.setdefault(
            str(oracle["failure_id"]), str(oracle["obligation_id"])
        )
    if set(first_obligation_by_failure) != failure_ids:
        raise ValueError(f"{skill_id}: every failure must own at least one oracle")
    guard_claim_boundary = (
        config["claim_boundary"]
        if semantic_detection
        else "This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth."
    )
    guard_contract = {
        "schema_version": "physicsguard.family_baseline_contract.v1",
        "artifact_role": "family_baseline_regression",
        "target_skill_id": skill_id,
        "native_owner_id": owner,
        "native_route_id": route,
        "prevented_failure_purpose": config["purpose"],
        "physical_or_evidence_boundary": [
            {
                "boundary_id": f"boundary:{skill_id}:{object_id}",
                "description": description,
                "authority_source": source,
                "required": True,
            }
            for object_id, description, source in config["external"]
        ],
        "prevented_failure_classes": failures,
        "claim_boundary": guard_claim_boundary,
        "authoring_order": [
            "freeze_prevented_failure_contract",
            "build_candidate",
            "prove_known_good",
            "prove_every_known_bad",
            "issue_native_receipt",
        ],
        "candidate_requires_contract_fingerprint": True,
        "candidate_admission": {
            "artifact_ref": "guard-model/candidate.json",
            "schema_version": "physicsguard.family_baseline_candidate.v1",
            "fingerprint_algorithm": "sha256-canonical-json-uppercase-v1",
            "required_event_order": [
                "purpose_contract_frozen",
                "candidate_built",
            ],
            "failure_codes": [
                "candidate_artifact_missing",
                "candidate_contract_fingerprint_mismatch",
                "candidate_built_before_purpose_or_event_chain_broken",
            ],
        },
    }
    oracle_set = {
        "schema_version": "physicsguard.family_baseline_oracle_set.v1",
        "artifact_role": "family_baseline_regression",
        "target_skill_id": skill_id,
        "required_obligation_ids": obligations,
        "oracles": oracles,
    }
    known_good = {
        "schema_version": "physicsguard.family_baseline_known_good.v1",
        "artifact_role": "family_baseline_regression",
        "case_id": f"known-good:{skill_id}:complete-native-route",
        "target_skill_id": skill_id,
        "covered_obligation_ids": obligations,
        "expected_native_status": "pass",
        "self_reported_outcome_allowed": False,
    }
    known_bad = {
        "schema_version": "physicsguard.family_baseline_known_bad_set.v1",
        "artifact_role": "family_baseline_regression",
        "target_skill_id": skill_id,
        "cases": [
            {
                "case_id": f"known-bad:{failure_id.rsplit(':', 1)[-1]}",
                "failure_id": failure_id,
                "trigger_obligation_id": first_obligation_by_failure[failure_id],
                "expected_native_status": "blocked",
                "expected_finding_code": next(
                    row["expected_finding_code"]
                    for row in failures
                    if row["failure_id"] == failure_id
                ),
                "self_reported_outcome_allowed": False,
                "proof_strength": next(
                    row["proof_strength"]
                    for row in failures
                    if row["failure_id"] == failure_id
                ),
                **(
                    {
                        "native_fixture": semantic_fixtures[
                            failure_id.rsplit(":", 1)[-1]
                        ]
                    }
                    if semantic_detection
                    else {}
                ),
            }
            for failure_id in sorted(failure_ids)
        ],
    }
    contract_fingerprint = canonical_fingerprint(guard_contract)
    candidate_definition = {
        "native_owner_id": owner,
        "native_route_id": route,
        "protected_failure_ids": sorted(failure_ids),
        "required_obligation_ids": obligations,
        "claim_boundary": guard_claim_boundary,
    }
    purpose_event = {
        "event_id": f"event:{skill_id}:purpose-contract-frozen",
        "sequence": 1,
        "event_kind": "purpose_contract_frozen",
        "purpose_contract_fingerprint": contract_fingerprint,
    }
    candidate_event = {
        "event_id": f"event:{skill_id}:candidate-built",
        "sequence": 2,
        "event_kind": "candidate_built",
        "purpose_contract_fingerprint": contract_fingerprint,
        "previous_event_fingerprint": canonical_fingerprint(purpose_event),
        "candidate_definition_fingerprint": canonical_fingerprint(
            candidate_definition
        ),
    }
    candidate = {
        "schema_version": "physicsguard.family_baseline_candidate.v1",
        "artifact_role": "family_baseline_regression",
        "target_skill_id": skill_id,
        "candidate_id": f"candidate:{skill_id}:guard-model-current",
        "purpose_contract_ref": "guard-model/contract.json",
        "purpose_contract_fingerprint": contract_fingerprint,
        "candidate_definition": candidate_definition,
        "authoring_events": [purpose_event, candidate_event],
    }
    return guard_contract, candidate, oracle_set, known_good, known_bad


def _flowguard_export(
    skill_id: str,
    owner: str,
    route: str,
    guard_contract: dict[str, Any],
) -> dict[str, Any]:
    purpose_step = f"step:{skill_id}:family-baseline-contract"
    candidate_step = f"step:{skill_id}:family-baseline-candidate"
    good_step = f"step:{skill_id}:family-baseline-good"
    bad_steps = [
        f"step:{skill_id}:family-baseline-bad:{row['failure_id'].rsplit(':', 1)[-1]}"
        for row in guard_contract["prevented_failure_classes"]
    ]
    terminal = f"terminal:{skill_id}:current"
    blocked = f"terminal:{skill_id}:blocked"
    steps = [
        {"step_id": purpose_step, "route_id": route, "owner_id": owner, "action_kind": "contract", "terminal_kind": "", "prerequisite_step_ids": []},
        {"step_id": candidate_step, "route_id": route, "owner_id": owner, "action_kind": "candidate_admission", "terminal_kind": "", "prerequisite_step_ids": [purpose_step]},
        {"step_id": good_step, "route_id": route, "owner_id": owner, "action_kind": "native", "terminal_kind": "", "prerequisite_step_ids": [candidate_step]},
        *[
            {"step_id": step_id, "route_id": route, "owner_id": owner, "action_kind": "native", "terminal_kind": "", "prerequisite_step_ids": [good_step]}
            for step_id in bad_steps
        ],
        {"step_id": terminal, "route_id": route, "owner_id": owner, "action_kind": "terminal", "terminal_kind": "success", "prerequisite_step_ids": bad_steps},
        {"step_id": blocked, "route_id": route, "owner_id": owner, "action_kind": "terminal", "terminal_kind": "blocked", "prerequisite_step_ids": []},
    ]
    obligations = [
        {
            "obligation_id": f"obligation:{skill_id}:family-baseline-contract",
            "invariant_id": f"invariant:{skill_id}:family-baseline-contract",
            "owner_step_ids": [purpose_step],
            "required": True,
        },
        {
            "obligation_id": f"obligation:{skill_id}:family-baseline-good",
            "invariant_id": f"invariant:{skill_id}:family-baseline-good",
            "owner_step_ids": [good_step],
            "required": True,
        },
        {
            "obligation_id": f"obligation:{skill_id}:family-baseline-candidate-bound",
            "invariant_id": f"invariant:{skill_id}:family-baseline-candidate-bound",
            "owner_step_ids": [candidate_step],
            "required": True,
        },
        *[
            {
                "obligation_id": f"obligation:{skill_id}:family-baseline-blocks:{row['failure_id'].rsplit(':', 1)[-1]}",
                "invariant_id": f"invariant:{skill_id}:family-baseline-blocks:{row['failure_id'].rsplit(':', 1)[-1]}",
                "owner_step_ids": [step_id],
                "required": True,
            }
            for row, step_id in zip(guard_contract["prevented_failure_classes"], bad_steps)
        ],
    ]
    return {
        "schema_version": "skillguard.flowguard_model_export.v2",
        "flowguard_schema_version": "1.0",
        "model_id": f"{skill_id}.family-baseline-regression.current",
        "parent_model_id": "physicsguard.guard-family.family-baseline-regression.current",
        "functions": [{"function_id": f"function:{skill_id}:guard-model", "business_intent": "Prove the maintained family baseline checker capability only: " + guard_contract["prevented_failure_purpose"], "owner_id": owner, "route_ids": [route]}],
        "routes": [{"route_id": route, "function_id": f"function:{skill_id}:guard-model", "owner_id": owner, "step_ids": [row["step_id"] for row in steps], "success_terminal_step_id": terminal, "blocked_terminal_step_id": blocked, "handoffs": []}],
        "steps": steps,
        "obligations": obligations,
        "invariant_ids": [row["invariant_id"] for row in obligations],
        "claim_boundary": "This model proves only maintained family baseline regression. A concrete PhysicsGuard model requires a separate target-local current_model_purpose contract and proofs.",
    }


def _model_source(export: dict[str, Any]) -> str:
    payload = json.dumps(export, ensure_ascii=False, separators=(",", ":"))
    return (
        '"""Executable PhysicsGuard purpose-before-candidate contract model."""\n\n'
        "import json\n\n"
        'FLOWGUARD_MODEL_MARKER = "flowguard-executable-model"\n'
        f"EXPORT = json.loads(r'''{payload}''')\n\n\n"
        "def export_contract_model():\n    return EXPORT\n"
    )


def _managed_current_prompt(
    config: dict[str, Any], guard_contract: dict[str, Any]
) -> str:
    failures = "\n".join(
        f"- `{row['title']}` ({row['proof_strength']}): block when {row['block_when']}. "
        f"Claim boundary: {row['claim_boundary']}"
        for row in guard_contract["prevented_failure_classes"]
    )
    return (
        f"{PURPOSE_MARKER_START}\n"
        "## PhysicsGuard dynamic model-purpose and family baseline\n\n"
        f"Family capability baseline purpose: {config['purpose']}\n\n"
        f"Family route bounded claim: {config['claim_boundary']}\n\n"
        f"Family baseline proof boundary: {guard_contract['claim_boundary']}\n\n"
        "The bundled `guard-model/` files declare these maintained family baseline regression classes:\n\n"
        f"{failures}\n\n"
        "These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.\n\n"
        "For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.\n\n"
        "Use `guard-model/verify.py check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.\n\n"
        "`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.\n\n"
        "`guard-model/verify.py` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.\n"
        f"{PURPOSE_MARKER_END}"
    )


def _content_role_overrides(skill_id: str) -> list[dict[str, str]]:
    rows = [
        {
            "path": f"skill/{skill_id}/guard-model",
            "role": "test_dev",
            "install_disposition": "source_only",
            "reason": "author_only_guard_contract",
        }
    ]
    if skill_id == "physicsguard-model-dataset-validation":
        rows.extend(
            [
                {
                    "path": f"skill/{skill_id}/runtime/native-runtime-manifest.json",
                    "role": "test_dev",
                    "install_disposition": "source_only",
                    "reason": "author_only_runtime_inventory",
                },
                {
                    "path": f"skill/{skill_id}/runtime/physicsguard/guard_model_contract.py",
                    "role": "test_dev",
                    "install_disposition": "source_only",
                    "reason": "author_only_guard_contract_runtime",
                },
                {
                    "path": f"skill/{skill_id}/runtime/physicsguard/skillguard_template_adapter.py",
                    "role": "test_dev",
                    "install_disposition": "source_only",
                    "reason": "author_only_template_projection_adapter",
                },
            ]
        )
    return rows


def _implementation_paths(skill_root: Path) -> list[str]:
    excluded_names = {"compiled-contract.json", "check-manifest.json"}
    rows: list[str] = []
    for path in skill_root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(skill_root).as_posix()
        if relative.startswith(".skillguard/runs/") or path.name in excluded_names:
            continue
        if relative == ".skillguard/contract-source.json":
            continue
        rows.append(path.relative_to(ROOT).as_posix())
    return sorted(rows)


def _sync_native_runtime(skill_root: Path, skill_id: str) -> list[str]:
    runtime_root = skill_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    canonical_depth = ROOT / "src" / "physicsguard" / "skill_execution_depth.py"
    shutil.copyfile(canonical_depth, runtime_root / "skill_execution_depth.py")
    if skill_id == "physicsguard-model-dataset-validation":
        source_package = ROOT / "src" / "physicsguard"
        target_package = runtime_root / "physicsguard"
        for source in sorted(source_package.rglob("*.py")):
            if "__pycache__" in source.parts:
                continue
            destination = target_package / source.relative_to(source_package)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        runtime_files = [
            path
            for path in runtime_root.rglob("*.py")
            if "__pycache__" not in path.parts
        ]
        rows = [
            {
                "path": path.relative_to(runtime_root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted(runtime_files)
        ]
        manifest = {
            "schema_version": "physicsguard.installed_native_runtime_manifest.v1",
            "target_skill_id": skill_id,
            "runtime_root": "runtime",
            "source_file_count": len(rows),
            "source_inventory_fingerprint": canonical_fingerprint(rows),
            "files": rows,
            "claim_boundary": "This manifest proves only byte-complete bundled PhysicsGuard Python runtime authority for the current installed skill projection; it does not prove native checks executed.",
        }
        (runtime_root / "native-runtime-manifest.json").write_text(
            stable_json(manifest), encoding="utf-8"
        )
    return [
        path.relative_to(skill_root).as_posix()
        for path in sorted(runtime_root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and (path.suffix == ".py" or path.name == "native-runtime-manifest.json")
    ]


def upgrade_target_current(skill_id: str, config: dict[str, Any]) -> None:
    skill_root = SKILL_ROOT / skill_id
    source_path = skill_root / ".skillguard" / "contract-source.json"
    previous = json.loads(source_path.read_text(encoding="utf-8"))
    obligations = _current_obligations(skill_root, previous)
    owner, route = _native_identity(skill_root, skill_id, previous)
    guard_contract, candidate, oracles, known_good, known_bad = _guard_documents(
        skill_id, config, obligations, owner, route
    )
    guard_root = skill_root / "guard-model"
    guard_root.mkdir(parents=True, exist_ok=True)
    (guard_root / "contract.json").write_text(stable_json(guard_contract), encoding="utf-8")
    (guard_root / "candidate.json").write_text(stable_json(candidate), encoding="utf-8")
    (guard_root / "oracles.json").write_text(stable_json(oracles), encoding="utf-8")
    (guard_root / "known-good.json").write_text(stable_json(known_good), encoding="utf-8")
    (guard_root / "known-bad.json").write_text(stable_json(known_bad), encoding="utf-8")
    shutil.copyfile(ROOT / "src" / "physicsguard" / "guard_model_contract.py", guard_root / "verify.py")
    runtime_paths = _sync_native_runtime(skill_root, skill_id)

    export = _flowguard_export(skill_id, owner, route, guard_contract)
    model_path = skill_root / ".skillguard" / "contract_model.py"
    model_path.write_text(_model_source(export), encoding="utf-8")

    contract_obligation = f"obligation:{skill_id}:family-baseline-contract"
    candidate_obligation = f"obligation:{skill_id}:family-baseline-candidate-bound"
    good_obligation = f"obligation:{skill_id}:family-baseline-good"
    contract_check = f"check:{skill_id}:family-baseline-contract"
    candidate_check = f"check:{skill_id}:family-baseline-candidate"
    good_check = f"check:{skill_id}:family-baseline-good"
    repository_prefix = f"skill/{skill_id}"
    contract_selectors = [
        {"kind": "path", "path": f"{repository_prefix}/guard-model/contract.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/oracles.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/known-good.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/known-bad.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/verify.py"},
        *[
            {"kind": "path", "path": f"{repository_prefix}/{path}"}
            for path in runtime_paths
        ],
    ]
    candidate_selectors = [
        *contract_selectors,
        {
            "kind": "path",
            "path": f"{repository_prefix}/guard-model/candidate.json",
        },
    ]
    checks: list[dict[str, Any]] = [
        {
            "check_id": contract_check,
            "semantic_check_id": f"semantic:{skill_id}:family-baseline-contract",
            "kind": "command",
            "command": "python",
            "args": ["guard-model/verify.py", "check-baseline-contract", "--skill-root", "{{target_root}}"],
            "cwd_token": "target_root",
            "expected": {"exit_code": 0},
            "timeout_seconds": 120,
            "evidence_class": "hard",
            "evidence_domain_id": f"{skill_id}:guard-model-proof",
            "execution_owner_id": f"owner:{skill_id}:guard-model-contract",
            "covers_obligation_ids": [contract_obligation],
            "depends_on_check_ids": [],
            "input_selectors": contract_selectors,
        },
        {
            "check_id": candidate_check,
            "semantic_check_id": f"semantic:{skill_id}:family-baseline-candidate",
            "kind": "command",
            "command": "python",
            "args": ["guard-model/verify.py", "check-baseline-candidate", "--skill-root", "{{target_root}}"],
            "cwd_token": "target_root",
            "expected": {"exit_code": 0},
            "timeout_seconds": 120,
            "evidence_class": "hard",
            "evidence_domain_id": f"{skill_id}:guard-model-proof",
            "execution_owner_id": f"owner:{skill_id}:candidate-bound",
            "covers_obligation_ids": [candidate_obligation],
            "depends_on_check_ids": [contract_check],
            "input_selectors": candidate_selectors,
        },
        {
            "check_id": good_check,
            "semantic_check_id": f"semantic:{skill_id}:family-baseline-good",
            "kind": "command",
            "command": "python",
            "args": ["guard-model/verify.py", "prove-baseline-good", "--skill-root", "{{target_root}}"],
            "cwd_token": "target_root",
            "expected": {"exit_code": 0},
            "timeout_seconds": 240,
            "evidence_class": "hard",
            "evidence_domain_id": f"{skill_id}:guard-model-proof",
            "execution_owner_id": f"owner:{skill_id}:known-good",
            "covers_obligation_ids": [good_obligation],
            "depends_on_check_ids": [candidate_check],
            "input_selectors": candidate_selectors,
        },
    ]
    bad_obligations: list[str] = []
    for failure in guard_contract["prevented_failure_classes"]:
        failure_id = str(failure["failure_id"])
        suffix = failure_id.rsplit(":", 1)[-1]
        obligation = f"obligation:{skill_id}:family-baseline-blocks:{suffix}"
        check_id = f"check:{skill_id}:family-baseline-bad:{suffix}"
        bad_obligations.append(obligation)
        checks.append(
            {
                "check_id": check_id,
                "semantic_check_id": f"semantic:{skill_id}:family-baseline-blocks:{suffix}",
                "kind": "command",
                "command": "python",
                "args": ["guard-model/verify.py", "prove-baseline-bad", "--skill-root", "{{target_root}}", "--failure-id", failure_id],
                "cwd_token": "target_root",
                "expected": {"exit_code": 0},
                "timeout_seconds": 240,
                "evidence_class": "hard",
                "evidence_domain_id": f"{skill_id}:guard-model-proof",
                "execution_owner_id": f"owner:{skill_id}:known-bad:{suffix}",
                "covers_obligation_ids": [obligation],
                "depends_on_check_ids": [good_check],
                "input_selectors": candidate_selectors,
            }
        )
    for check in checks:
        check["maintenance_unit_id"] = "unit:physicsguard-family"
        check["member_skill_id"] = skill_id
        check["evidence_subject_id"] = f"subject:{check['check_id']}"
    required = [
        contract_obligation,
        candidate_obligation,
        good_obligation,
        *bad_obligations,
    ]
    check_ids = [str(check["check_id"]) for check in checks]
    source_contract = {
        "schema_version": "skillguard.contract_source.v2",
        "skill_id": skill_id,
        "model_id": export["model_id"],
        "model_path": f"{repository_prefix}/.skillguard/contract_model.py",
        "confirmed": True,
        "integration_mode": "native-integrated",
        "native_route_owner": owner,
        "default_route_id": route,
        "native_route_bindings": [
            {
                "binding_id": f"native:{skill_id}:current",
                "native_route_id": route,
                "required_before_closure": True,
                "source": "guard-model/contract.json",
            }
        ],
        "native_check_bindings": [
            {
                "binding_id": (
                    f"native-check:{skill_id}:"
                    f"{binding_id_fragment(str(check['check_id']))}"
                ),
                "evidence_source": "guard-model/verify.py",
                "native_check_id": str(check["check_id"]),
                "required": True,
            }
            for check in checks
        ],
        "depth_profile": {
            "schema_version": "skillguard.depth_profile.v2",
            "profile_id": f"profile:{skill_id}:family-baseline-regression",
            "target_skill_id": skill_id,
            "integration_mode": "native-integrated",
            "native_owner_id": owner,
            "native_route_ids": [route],
            "native_check_ids": check_ids,
            "skillguard_adds_domain_route": False,
            "enforcement_level": "enforced",
            "required_closure_profiles": ["enforced"],
            "provider_runtime": {
                "provider_id": "skillguard-local-provider",
                "required_runtime_contract_id": (
                    "skillguard-declared-check-supervision-current"
                ),
                "required_capability_ids": [
                    "declared-check-inventory.v1",
                    "declared-check-receipt-reconciliation.v1",
                    "installation-receipt-binding.v1",
                    "installation-currentness-replay.v1",
                    "provider-runtime-enrollment.v1",
                    "single-flight-check-execution.v1",
                ],
                "required_enrollment_status": "enrolled",
                "readiness_check_ids": [contract_check],
            },
            "claim_boundary": (
                "PhysicsGuard owns the family baseline semantics and every target-local "
                "current-model purpose, failure, native oracle, proof, residual risk, and "
                "bounded claim. SkillGuard only executes and reconciles the declared "
                "family baseline inventory; that receipt cannot close a current model."
            ),
        },
        "may_define_parallel_execution_route": False,
        "may_define_skillguard_runtime_route": False,
        "release_eligible": False,
        "claim_boundary": guard_contract["claim_boundary"],
        "checks": checks,
        "artifacts": [],
        "judgment_rubrics": [],
        "closure_profiles": [{"profile_id": "enforced", "required_obligation_ids": required}],
        "step_bindings": [
            {
                "step_id": f"step:{skill_id}:family-baseline-contract",
                "check_ids": [contract_check],
                "output_artifact_ids": [],
                "action": {"kind": "contract", "summary": "Validate the immutable PhysicsGuard family baseline contract; this is not current-model purpose authority."},
            },
            {
                "step_id": f"step:{skill_id}:family-baseline-candidate",
                "check_ids": [candidate_check],
                "output_artifact_ids": [],
                "action": {
                    "kind": "candidate_admission",
                    "summary": "Admit only the family baseline candidate bound to its exact baseline contract and ordered authoring chain.",
                },
            },
            {
                "step_id": f"step:{skill_id}:family-baseline-good",
                "check_ids": [good_check],
                "output_artifact_ids": [],
                "action": {"kind": "native", "summary": "Execute the mandatory family baseline known-good proof."},
            },
            *[
                {
                    "step_id": f"step:{skill_id}:family-baseline-bad:{row['failure_id'].rsplit(':', 1)[-1]}",
                    "check_ids": [f"check:{skill_id}:family-baseline-bad:{row['failure_id'].rsplit(':', 1)[-1]}"],
                    "output_artifact_ids": [],
                    "action": {"kind": "native", "summary": f"Prove the maintained family baseline blocks its declared regression case: {row['title']}."},
                }
                for row in guard_contract["prevented_failure_classes"]
            ],
        ],
        "implementation_paths": [],
        "repository_role": "skill_maintainer_source",
        "maintenance_unit_id": "unit:physicsguard-family",
        "member_skill_ids": sorted(TARGETS),
        "consumer_projection": {
            "prohibited_path_prefixes": [".skillguard/"],
            "prohibited_prompt_tokens": ["SkillGuard", ".skillguard", "skillguard.py"],
            "projection_id": "projection:consumer-distribution",
            "release_manifest_path": "consumer-release.json",
        },
        "content_role_overrides": _content_role_overrides(skill_id),
    }
    source_path.write_text(stable_json(source_contract), encoding="utf-8")

    skill_path = skill_root / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    if SKILLGUARD_LAYER_START in text and SKILLGUARD_LAYER_END in text:
        prefix, remainder = text.split(SKILLGUARD_LAYER_START, 1)
        _, suffix = remainder.split(SKILLGUARD_LAYER_END, 1)
        text = prefix.rstrip() + suffix
    section = _managed_current_prompt(config, guard_contract)
    if PURPOSE_MARKER_START in text and PURPOSE_MARKER_END in text:
        prefix, remainder = text.split(PURPOSE_MARKER_START, 1)
        _, suffix = remainder.split(PURPOSE_MARKER_END, 1)
        text = prefix.rstrip() + "\n\n" + section + suffix
    else:
        text = text.rstrip() + "\n\n" + section + "\n"
    skill_path.write_text(text, encoding="utf-8")

    source_contract["implementation_paths"] = _implementation_paths(skill_root)
    source_path.write_text(stable_json(source_contract), encoding="utf-8")


def main() -> int:
    discovered = {
        path.parent.parent.name
        for path in SKILL_ROOT.glob("physicsguard*/.skillguard/contract-source.json")
    }
    if discovered != set(TARGETS):
        raise SystemExit(
            f"PhysicsGuard target inventory mismatch: missing={sorted(discovered - set(TARGETS))}; extra={sorted(set(TARGETS) - discovered)}"
        )
    for skill_id in sorted(TARGETS):
        upgrade_target_current(skill_id, TARGETS[skill_id])
    print(stable_json({"status": "pass", "updated_targets": sorted(TARGETS)}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
