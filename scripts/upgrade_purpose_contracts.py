"""Generate the current PhysicsGuard skill contracts and consumer metadata.

The table in this file is the reviewable source for route-specific protected
purposes, independently discovered external universes, semantic obligations,
and native failure classes. Generated JSON stays target-local and current-only.
"""

from __future__ import annotations

import ast
import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
import re
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
from typing import Any, Iterator, Mapping


sys.dont_write_bytecode = True

from flowguard.model_purpose import (
    build_model_purpose_closure,
    file_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from physicsguard_skill_install_authority import (  # noqa: E402
    DEFAULT_SKILLGUARD_ROOT,
    fingerprint_python_package_tree,
    load_skillguard_consumer_api,
    resolve_python_package_authority,
    verify_loaded_package_modules,
)


SKILL_ROOT = ROOT / "skill"
FLOWGUARD_PROJECT_PATH = ROOT / ".flowguard" / "project.toml"
SKILLGUARD_LAYER_START = "<!-- BEGIN SKILLGUARD CONTRACT LAYER -->"
SKILLGUARD_LAYER_END = "<!-- END SKILLGUARD CONTRACT LAYER -->"
CANONICAL_SATELLITE = SKILL_ROOT / "physicsguard-ai-debugging" / ".skillguard" / "runtime"
PRIMARY_RUNTIME = (
    SKILL_ROOT
    / "physicsguard-model-dataset-validation"
    / ".skillguard"
    / "runtime"
    / "physicsguard"
)
CANONICAL_RUNTIME_INPUTS = (
    "src/physicsguard/guard_model_contract.py",
    "src/physicsguard/skill_execution_depth.py",
    "src/physicsguard/schema/task_local_revision.py",
    "src/physicsguard/core/task_local_revision.py",
    "src/physicsguard/cli.py",
)
RUNTIME_REQUIREMENT_SCHEMA = "physicsguard.skill_runtime_requirement.v1"
ROUTE_CAPSULE_SCHEMA = "physicsguard.skill_route_capsule.v1"
PROMPT_LOAD_GRAPH_SCHEMA = "physicsguard.skill_prompt_load_graph.v1"
PROMPT_LOAD_GRAPH_PATH = ROOT / ".flowguard" / "physicsguard_skill_prompt_load_graph.json"
MODEL_REGRESSION_MANIFEST_PATH = (
    ROOT / ".flowguard" / "model-regression-manifest.json"
)
UNIT_TEST_MESH_PATH = ROOT / ".skillguard" / "test-mesh.json"
UNIT_TEST_MESH_SCHEMA = "skillguard.test_mesh_manifest.current"
UNIT_TEST_MESH_ID = "physicsguard-family-owner-receipt-mesh"
FAMILY_MAINTENANCE_PROJECTION_ID = (
    "projection:physicsguard-family-maintenance-definition"
)
FAMILY_MAINTENANCE_MEMBER_ID = "physicsguard-audit-closure"
FAMILY_MAINTENANCE_CHECK_ID = (
    "check:physicsguard-family:distribution-authority"
)
FAMILY_MAINTENANCE_OWNER_ID = (
    "owner:physicsguard-family:distribution-authority"
)
FAMILY_MAINTENANCE_OBLIGATION_ID = (
    "obligation:physicsguard-family:distribution-authority"
)
NATIVE_ROUTE_REFERENCE = "references/native-route-protocol.md"
NATIVE_DEPTH_REFERENCE = "references/native-depth-and-purpose.md"
TEMPLATE_PACK_REFERENCE = "references/template-pack-routing.md"
ROUTE_CAPSULE_REFERENCE = "references/route-capsule.json"
MAX_SKILL_ENTRY_BYTES = 6_000
MAX_INITIAL_ROUTE_BYTES = 12_000
DEEP_CAPABILITIES = [
    "execution_depth",
    "mapping",
    "residual",
    "uncertainty",
    "diagnosability",
    "predictive_rollout",
    "purpose_before_candidate",
    "prediction_before_observation",
    "model_miss",
    "typed_regression",
    "independent_holdout",
    "exact_terminal_boundary",
]
ENTRY_SHARED_GOVERNED_INPUTS = (
    ".flowguard/check_physicsguard_skill_suite_mesh.py",
    ".flowguard/model-regression-manifest.json",
    ".flowguard/physicsguard_skill_prompt_load_graph.json",
    ".flowguard/physicsguard_skill_suite_mesh.json",
    "VERSION",
    "pyproject.toml",
    "src/physicsguard/__init__.py",
    "scripts/check_installed_physicsguard_skills.py",
    # These two author-side helpers are imported by the shared entry/loading
    # checks.  Keep them in the shared governed spine so the import-closure
    # owner is explicit rather than accidentally duplicating the family-only
    # maintenance owner on an exclusive component.
    "scripts/physicsguard_skill_install_authority.py",
    "scripts/upgrade_purpose_contracts.py",
    "scripts/verify_guard_simulation_readiness.py",
    "tests/test_guard_skill_mesh.py",
    "tests/test_installed_skill_sync.py",
    "tests/test_physicsguard_skill_entry_loading.py",
    "tests/test_post_archive_retirement_authority.py",
    "tests/test_skillguard_v2_runtime_authority_audit.py",
    "tests/test_version_consistency.py",
)
ENTRY_GOVERNED_IMPLEMENTATION_PATHS = (
    *ENTRY_SHARED_GOVERNED_INPUTS,
    ".flowguard/model-regression-manifest.json",
    "scripts/check_installed_physicsguard_skills.py",
    "scripts/verify_guard_simulation_readiness.py",
    "tests/test_guard_skill_mesh.py",
    "tests/test_installed_skill_sync.py",
    "tests/test_post_archive_retirement_authority.py",
    "tests/test_skillguard_v2_runtime_authority_audit.py",
    "tests/test_version_consistency.py",
)
FAMILY_MAINTENANCE_INPUTS = (
    ".flowguard/check_physicsguard_skill_suite_mesh.py",
    ".flowguard/model-regression-manifest.json",
    ".flowguard/physicsguard_skill_prompt_load_graph.json",
    ".flowguard/physicsguard_skill_suite_mesh.json",
    ".skillguard/test-mesh.json",
    "VERSION",
    "pyproject.toml",
    "scripts/check_physicsguard_test_mesh.py",
    "scripts/check_installed_physicsguard_skills.py",
    "scripts/install_physicsguard_skills.py",
    "scripts/physicsguard_skill_install_authority.py",
    "scripts/report_physicsguard_skill_suite.py",
    "scripts/upgrade_purpose_contracts.py",
    "scripts/verify_guard_simulation_readiness.py",
    "src/physicsguard/__init__.py",
    "tests/test_guard_skill_mesh.py",
    "tests/test_installed_skill_sync.py",
    "tests/test_install_physicsguard_skills.py",
    "tests/test_physicsguard_family_maintenance.py",
    "tests/test_physicsguard_skill_install_authority.py",
    "tests/test_post_archive_retirement_authority.py",
    "tests/test_skillguard_v2_runtime_authority_audit.py",
    "tests/test_version_consistency.py",
)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical_identity_fingerprint(value: Mapping[str, object]) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _physicsguard_source_version(init_path: Path) -> str:
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise RuntimeError(
            f"physicsguard_source_version_unreadable:{type(exc).__name__}:{init_path}"
        ) from exc
    matches: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in targets):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            raise RuntimeError(
                f"physicsguard_source_version_not_literal:{init_path}"
            )
        matches.append(value.value)
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(
            f"physicsguard_source_version_ambiguous:count={len(matches)}:{init_path}"
        )
    return matches[0]


def _physicsguard_version_authority(repository_root: Path) -> dict[str, str]:
    root = Path(repository_root).resolve(strict=True)
    pyproject_path = root / "pyproject.toml"
    version_path = root / "VERSION"
    init_path = root / "src" / "physicsguard" / "__init__.py"
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        pyproject_version = str(pyproject["project"]["version"])
        version_file_version = version_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(
            f"physicsguard_version_authority_unreadable:{type(exc).__name__}"
        ) from exc
    source_version = _physicsguard_source_version(init_path)
    observed = {
        "pyproject": pyproject_version,
        "VERSION": version_file_version,
        "source": source_version,
    }
    if not pyproject_version or len(set(observed.values())) != 1:
        raise RuntimeError(
            "physicsguard_version_authority_mismatch:"
            + ":".join(f"{name}={value}" for name, value in observed.items())
        )
    source_hashes = {
        "pyproject_sha256": _sha256_bytes(pyproject_path.read_bytes()),
        "version_file_sha256": _sha256_bytes(version_path.read_bytes()),
        "source_init_sha256": _sha256_bytes(init_path.read_bytes()),
    }
    return {
        "version": pyproject_version,
        **source_hashes,
        "authority_sha256": _canonical_identity_fingerprint(
            {"version": pyproject_version, **source_hashes}
        ),
    }


def current_toolchain_identity(
    *,
    repository_root: Path = ROOT,
    flowguard_project_path: Path | None = None,
    skillguard_root: Path = DEFAULT_SKILLGUARD_ROOT,
) -> dict[str, str]:
    """Resolve tool identities from current explicit authorities or block.

    The generator must never silently preserve an older literal.  FlowGuard's
    adopted project record must equal the importable package/schema, and the
    selected installed SkillGuard root must expose its current consumer API.
    """

    repository = Path(repository_root).resolve(strict=True)
    physicsguard_authority = _physicsguard_version_authority(repository)
    project_path = Path(
        flowguard_project_path
        if flowguard_project_path is not None
        else repository / ".flowguard" / "project.toml"
    ).resolve(strict=True)
    project = tomllib.loads(project_path.read_text(encoding="utf-8"))
    declared_flowguard_version = str(
        project["flowguard"]["adopted_package_version"]
    )
    declared_flowguard_schema = str(project["flowguard"]["schema_version"])
    flowguard_authority = resolve_python_package_authority("flowguard", "flowguard")
    flowguard_module = importlib.import_module("flowguard")
    verify_loaded_package_modules("flowguard", flowguard_authority.package_root)
    flowguard_tree_after_import = fingerprint_python_package_tree(
        flowguard_authority.package_root
    )
    if (
        flowguard_tree_after_import.sha256
        != flowguard_authority.package_tree_sha256
        or flowguard_tree_after_import.file_count
        != flowguard_authority.package_file_count
    ):
        raise RuntimeError(
            "flowguard_package_tree_changed_during_authority_freeze:"
            f"before={flowguard_authority.package_tree_sha256}:"
            f"after={flowguard_tree_after_import.sha256}"
        )
    observed_flowguard_version = flowguard_authority.distribution_version
    observed_flowguard_schema = str(
        getattr(flowguard_module, "SCHEMA_VERSION", "missing")
    )
    if (
        declared_flowguard_version != observed_flowguard_version
        or declared_flowguard_schema != observed_flowguard_schema
    ):
        raise RuntimeError(
            "flowguard_authority_mismatch:"
            f"project={declared_flowguard_version}/{declared_flowguard_schema}:"
            f"installed={observed_flowguard_version}/{observed_flowguard_schema}"
        )
    skillguard_api = load_skillguard_consumer_api(skillguard_root)
    observed_skillguard_version = str(skillguard_api.distribution_version or "")
    if not observed_skillguard_version or not skillguard_api.distribution_authority_sha256:
        raise RuntimeError("skillguard_distribution_authority_unproved")
    if (
        not skillguard_api.package_tree_sha256
        or skillguard_api.package_tree_sha256
        != skillguard_api.distribution_package_tree_sha256
    ):
        raise RuntimeError("skillguard_installed_distribution_authority_unproved")
    # The project record is the local adoption/currentness projection.  It is
    # updated by FlowGuard model activation (snapshot, generation, and head
    # fields), so including its whole-file hash here creates a self-invalidating
    # loop: activating a model changes the declared toolchain fingerprint,
    # which then makes the generated graph stale even though FlowGuard itself
    # did not change.  Version/schema equality above still protects the
    # adoption boundary; the bound package authority must remain stable across
    # those ordinary model-pointer updates.
    flowguard_bound_authority = _canonical_identity_fingerprint(
        {
            "distribution_authority_sha256": flowguard_authority.authority_sha256,
            "package_tree_sha256": flowguard_tree_after_import.sha256,
            "package_file_count": flowguard_tree_after_import.file_count,
            "schema_version": observed_flowguard_schema,
            "project_version": declared_flowguard_version,
            "project_schema": declared_flowguard_schema,
        }
    )
    return {
        "physicsguard_version": physicsguard_authority["version"],
        "physicsguard_authority_sha256": physicsguard_authority["authority_sha256"],
        "flowguard_version": observed_flowguard_version,
        "flowguard_schema_version": observed_flowguard_schema,
        "flowguard_package_tree_sha256": flowguard_tree_after_import.sha256,
        "flowguard_direct_url_sha256": str(
            flowguard_authority.direct_url_sha256 or "none"
        ),
        "flowguard_authority_sha256": flowguard_bound_authority,
        "skillguard_version": observed_skillguard_version,
        "skillguard_api_tree_sha256": str(skillguard_api.package_tree_sha256),
        "skillguard_distribution_tree_sha256": str(
            skillguard_api.distribution_package_tree_sha256
        ),
        "skillguard_direct_url_sha256": str(
            skillguard_api.distribution_direct_url_sha256 or "none"
        ),
        "skillguard_authority_sha256": str(
            skillguard_api.distribution_authority_sha256
        ),
    }


def expected_unit_test_mesh_manifest() -> dict[str, Any]:
    """Return the sole current TestMesh definition for the maintenance unit."""

    return {
        "schema_version": UNIT_TEST_MESH_SCHEMA,
        "mesh_id": UNIT_TEST_MESH_ID,
        "source_model_id": "physicsguard.family.validation_composition.current",
        "profiles": [
            {
                "profile_id": "focused",
                "closure_profile_id": "enforced",
                "full_admission_required": False,
            },
            {
                "profile_id": "full",
                "closure_profile_id": "enforced",
                "full_admission_required": True,
            },
        ],
        "claim_boundary": (
            "This one unit-level definition selects each PhysicsGuard member's "
            "existing enforced closure, including eighty-four target-domain/model "
            "owners and one family distribution owner declared only by the "
            "audit-closure member. One legitimate claimed run per member is "
            "required before member-specific plan_only can freeze owners. It "
            "declares no commands, source paths, aliases, fallback, execution "
            "result, or receipt authority; full remains separately admitted."
        ),
    }


def _write_unit_test_mesh_manifest() -> None:
    UNIT_TEST_MESH_PATH.parent.mkdir(parents=True, exist_ok=True)
    UNIT_TEST_MESH_PATH.write_text(
        stable_json(expected_unit_test_mesh_manifest()), encoding="utf-8"
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


ROUTE_ENTRIES: dict[str, dict[str, Any]] = {
    "physicsguard-ai-debugging": {
        "title": "PhysicsGuard AI Debugging",
        "description": "Use only for mixed or unclear AI-guided engineering-simulation debugging that genuinely spans multiple specialized PhysicsGuard routes, including coarse-to-fine localization and candidate-model coordination. For a clear adoption, preflight, mapping, test-file, dataset-validation, library, evidence-registry, blueprint, or closure request, use that direct skill instead.",
        "display_name": "PhysicsGuard AI Debugging",
        "short_description": "Coordinate mixed PhysicsGuard debugging routes",
        "role": "composite",
        "accept_when": [
            "The visible engineering fault spans several PhysicsGuard responsibilities and cannot be owned by one direct route.",
            "The correct PhysicsGuard route remains genuinely ambiguous after comparing the ten route capsules.",
            "Coarse-to-fine localization requires typed handoffs among preflight, mapping, validation, and closure owners.",
        ],
        "reject_handoffs": [
            ("Repository adoption or upgrade is the whole request.", "physicsguard-project-adoption"),
            ("External-model boundary and inventory understanding is the whole request.", "physicsguard-model-understanding-preflight"),
            ("Signal identity, units, conversion, confidence, or temporal mapping is the whole request.", "physicsguard-signal-mapping-review"),
            ("A concrete test-data file contract is the whole request.", "physicsguard-test-file-contract-review"),
            ("Exact model/dataset validation is the whole request.", "physicsguard-model-dataset-validation"),
            ("Project evidence inventory and binding gaps are the whole request.", "physicsguard-project-evidence-registry"),
            ("Reusable model asset compatibility is the whole request.", "physicsguard-model-library"),
            ("Candidate blueprint generation is the whole request.", "physicsguard-candidate-model-blueprint"),
            ("Audit completion or localization closure is the whole request.", "physicsguard-audit-closure"),
        ],
        "minimum_inputs": ["visible_symptom", "physical_boundary_or_gap", "route_ambiguity", "current_blueprint_summary_affected_or_reverse_trace"],
        "required_outputs": ["selected_native_routes", "localized_findings", "blueprint_trace_projection", "delegated_blueprint_owner", "next_required_evidence", "bounded_claim"],
        "post_runtime_section": "## Blueprint coordination boundary\n\nConsume a current summary to choose the minimum direct route, an affected or reverse-trace projection to localize a named symptom, and never author or fully review `PhysicalModelBlueprint`. Whole-blueprint work belongs to `physicsguard-candidate-model-blueprint`; final claims belong to the relevant direct owner. A missing/stale/ambiguous projection blocks the handoff and does not authorize loading every skill, every blueprint member, or the repository as fallback.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_summary_for_route_selection_required", "blueprint_affected_or_reverse_trace_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_mixed_route_coordination"],
        "workflow": [
            "Confirm that no single direct capsule owns the complete request; otherwise hand off and stop this composite route.",
            "Verify the current PhysicsGuard runtime, then load the native route protocol only for the selected debugging work.",
            "Keep every specialist's native judgment and evidence separate while coordinating the smallest necessary handoff chain.",
            "Close only through the direct native owner that owns the requested final claim.",
        ],
    },
    "physicsguard-audit-closure": {
        "title": "PhysicsGuard Audit Closure",
        "description": "Use directly before claiming a PhysicsGuard audit, localization, validation, reuse, or prediction result is complete; reconcile required native checks, blockers, stale or skipped evidence, mappings, refinements, holdout and rollout evidence, and the exact safe claim boundary.",
        "display_name": "PhysicsGuard Audit Closure",
        "short_description": "Close bounded PhysicsGuard audit claims",
        "role": "direct",
        "accept_when": [
            "The requested outcome is a final audit, localization, validation, reuse, handoff, or prediction-readiness claim.",
            "Current native results must be reconciled into passed, partial, downgraded, or blocked closure.",
        ],
        "reject_handoffs": [
            ("Evidence is still being generated or the physical fault is still being localized.", "physicsguard-ai-debugging"),
            ("The request is only to build the project evidence map.", "physicsguard-project-evidence-registry"),
        ],
        "minimum_inputs": ["requested_claim", "closure_plan", "native_receipts", "open_blockers", "current_whole_or_affected_blueprint_review", "current_execution_receipts_if_claimed"],
        "required_outputs": ["closure_status", "safe_claim", "blueprint_scope_fingerprint", "blueprint_depth_and_first_gap", "in_memory_projection_identity", "in_memory_query_status", "current_execution_status", "execution_claim_licensed", "blockers", "next_actions"],
        "post_runtime_section": "## Blueprint closure input\n\nConsume a current whole or affected `PhysicalModelBlueprintReview` projection matching the requested claim. The native blueprint directory, its tests, and its model/code/evidence bindings are the only DNA authority. A compact projection may be composed in memory for one requested selector, but it is not a second artifact or transport package and it never becomes execution evidence. Report current native execution separately and never turn a projection, a frozen interpretation, or an AI answer into fresh evidence or closure. This route does not author or fully review the blueprint; missing, stale, ambiguous, unsupported, unresolved, or not-run evidence remains non-pass and cannot broaden to a repository scan or larger projection.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_affected_closure_required", "blueprint_whole_boundary_closure_required", "in_memory_blueprint_projection_closure_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_closure_projection", "in_memory_blueprint_projection_claim_boundary"],
        "workflow": [
            "Bind the exact requested claim and current native receipt inventory.",
            "Load the native route protocol and reconcile failures, skips, stale evidence, mappings, refinements, predictive conditions, and any in-memory projection identity or query gap.",
            "Keep in-memory interpretation projections and current target-native execution as separate states; return one exact closure state and a claim that does not exceed current evidence.",
        ],
    },
    "physicsguard-candidate-model-blueprint": {
        "title": "PhysicsGuard Candidate Model Blueprint",
        "description": "Use directly to turn a validated PhysicsGuard hierarchy into a bounded candidate model blueprint through an official target-model interface; require ready blocks, interfaces, mappings, model semantics, validation and rollout boundaries, without claiming recovered commercial-model equivalence.",
        "display_name": "PhysicsGuard Candidate Blueprint",
        "short_description": "Build a validated low-fidelity model blueprint",
        "role": "direct",
        "accept_when": [
            "The user asks to build a candidate model from already validated PhysicsGuard evidence.",
            "Generation readiness, interfaces, or rollout boundaries must be decided before target-model creation.",
        ],
        "reject_handoffs": [
            ("The hierarchy or external-model boundary is not yet understood.", "physicsguard-model-understanding-preflight"),
            ("The model still lacks current dataset validation evidence.", "physicsguard-model-dataset-validation"),
        ],
        "minimum_inputs": ["validated_hierarchy", "independent_target_inventory", "current_blueprint_or_authoring_target", "blueprint_artifact_root", "explicit_material_root_if_declared", "ready_blocks", "interface_inventory", "model_semantics", "in_memory_projection_if_requested", "in_memory_selector_if_requested"],
        "required_outputs": ["candidate_blueprint", "physical_blueprint_review", "blueprint_fingerprint", "material_root_disposition", "native_execution_status", "deepest_licensed_layer", "first_gap", "safe_claim", "native_directory_dna_status", "in_memory_query_identity_and_gaps", "execution_claim_licensed", "generation_eligibility", "rollout_boundary", "blockers"],
        "post_runtime_section": "## Blueprint ownership and loading\n\nThis is the sole PhysicsGuard route that authors or fully reviews `PhysicalModelBlueprint`. Resolve `artifact_root` before review: `blueprint_directory` binds local `repo_path` values below the blueprint directory, while `explicit_material_root` requires the caller-selected `--material-root` and never triggers discovery, download, or repository fallback. Without that material, return the concise `external_resource_not_run` boundary and `native_execution_status=not_run`. The blueprint directory, its tests, and its model/code/evidence bindings are the target DNA. A compact projection may be composed in memory for one requested `module`, `element`, `case`, `impact`, or `reverse` selector; the retired disk bundle route remains visibly blocked. Run the canonical review with `python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --pretty`.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_summary_required", "blueprint_affected_slice_required", "blueprint_author_or_full_review_required", "explicit_material_root_or_fmi_observation_required", "in_memory_blueprint_projection_query_required"],
        "native_route_required_for": ["target_native_domain_workflow", "canonical_physical_blueprint_authority", "in_memory_physical_blueprint_projection"],
        "workflow": [
            "Bind one independently inventoried target, resolve `blueprint_directory` versus `explicit_material_root`, and author or load its canonical `PhysicalModelBlueprint`.",
            "Run the canonical review with `--material-root ROOT` only when the blueprint declares `explicit_material_root`; reconcile hierarchy/refinement, typed interfaces/state/effects, independent physical semantics, and exact native model/code/test/resource/oracle bindings.",
            "For FMI targets, use the provider-neutral `physicsguard.fmi-observation-request.v1` contract and its restricted source-independent oracle; keep caller expectations, native outputs, and oracle results distinct.",
            "Use the full projection only for authoring or a whole-boundary review. Keep the native blueprint directory, tests, and bindings as DNA; on explicit request, compose only an in-memory projection or one selector while preserving every identity-only and execution-licensing gap.",
            "Generate a target-model candidate only through an official or user-owned interface, map outputs back to PhysicsGuard, and accept only inside the checked validation and rollout boundary.",
        ],
    },
    "physicsguard-model-dataset-validation": {
        "title": "PhysicsGuard Model-Dataset Validation",
        "description": "Use directly after current test-file contracts pass to validate a low-fidelity model against exact dataset, mapping, signal, parameter, time, scenario, envelope, holdout, and predictive-rollout identities with target-owned native receipts and bounded claims.",
        "display_name": "PhysicsGuard Dataset Validation",
        "short_description": "Validate models against exact project datasets",
        "role": "direct",
        "accept_when": [
            "A concrete model and contracted dataset must be checked for bounded consistency, validation, or prediction readiness.",
            "Coverage adequacy, calibration/holdout separation, residual envelopes, or future rollout must be evaluated.",
        ],
        "reject_handoffs": [
            ("A concrete data file lacks a current passing contract.", "physicsguard-test-file-contract-review"),
            ("Required mappings remain unresolved before validation.", "physicsguard-signal-mapping-review"),
        ],
        "minimum_inputs": ["model", "passing_test_file_contracts", "dataset_identity", "validation_plan", "mapping_evidence", "current_affected_or_whole_blueprint_projection"],
        "required_outputs": ["validation_status", "depth_receipt", "adequacy_findings", "per_blueprint_element_coverage", "affected_slice_fingerprint", "unsupported_claims", "bounded_validation_claim"],
        "post_runtime_section": "## Blueprint slice\n\nConsume the current affected projection for bounded validation and the full qualified projection only when the requested claim covers the whole target. Report coverage per blueprint element and obligation, including validation mode, validity boundary, residual/oracle identity, dataset and evidence fingerprints, and every unsupported claim. This route does not author or fully review the blueprint. Aggregate pass counts cannot hide an uncovered member. Stale or missing projection identity blocks without a run-all or full-scan fallback.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_affected_validation_slice_required", "whole_target_validation_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_validation_coverage_projection"],
        "workflow": [
            "Verify every referenced file contract and exact model, dataset, mapping, and plan identity.",
            "Load the native route protocol and run direct residual, envelope, adequacy, split, and rollout checks required by the claim.",
            "Return the native receipt, current blockers, and only the exact covered scope.",
        ],
    },
    "physicsguard-model-library": {
        "title": "PhysicsGuard Model Library",
        "description": "Use directly to index or select reusable PhysicsGuard model assets and check profile, testbench, validation-receipt, known-limit, gap, predictive-horizon, and bounded-reuse compatibility without storing raw datasets or implying universal validity.",
        "display_name": "PhysicsGuard Model Library",
        "short_description": "Check bounded PhysicsGuard model reuse",
        "role": "direct",
        "accept_when": [
            "The task is to index validated model assets or decide whether one is reusable for a named target context.",
            "Asset, profile, testbench, validation, gap, or predictive-horizon compatibility must be checked.",
        ],
        "reject_handoffs": [
            ("The asset has no current model/dataset validation receipt.", "physicsguard-model-dataset-validation"),
            ("The request is a cross-project database or historical-ledger query.", "none"),
        ],
        "minimum_inputs": ["asset_inventory", "target_context", "validation_receipts", "known_limits", "current_blueprint_fingerprint_and_projection"],
        "required_outputs": ["compatible_assets", "reuse_status", "selected_blueprint_fingerprints", "verified_reuse_limits", "gaps", "bounded_reuse_scope"],
        "post_runtime_section": "## Blueprint slice\n\nIndex and select assets by exact blueprint fingerprint, physical obligation, target profile, validity boundary, testbench, native receipt, and verified reuse limit. Use summary for discovery, affected projection for one reuse decision, and full projection only for whole-target qualification. This route does not author or fully review the blueprint. Loose similarity is not compatibility. Missing/stale projection identity is blocking and does not authorize scanning or validating unrelated assets.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_summary_for_discovery_required", "blueprint_affected_reuse_slice_required", "whole_target_reuse_qualification_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_reuse_compatibility_projection"],
        "workflow": [
            "Bind the selected asset and exact target profile/testbench context.",
            "Load the native route protocol and check current compatibility, validation, gaps, and known limits.",
            "Report only the exact reusable boundary; keep database-level discovery out of scope.",
        ],
    },
    "physicsguard-model-understanding-preflight": {
        "title": "PhysicsGuard Model Understanding Preflight",
        "description": "Use directly before a non-trivial external-model audit to capture the visible symptom, physical boundary, subsystem, signal, parameter, unit, assumption, access, model-semantics, and stop-condition universe; preflight is planning evidence, not residual validation.",
        "display_name": "PhysicsGuard Model Preflight",
        "short_description": "Bound external-model understanding before audit",
        "role": "direct",
        "accept_when": [
            "A non-trivial external model must be understood before residual interpretation or blueprint work.",
            "The physical boundary, inventory, assumptions, access gaps, semantics, or stop conditions need a current review.",
        ],
        "reject_handoffs": [
            ("The request is only to resolve signal identity, unit, conversion, or confidence.", "physicsguard-signal-mapping-review"),
            ("A concrete test-data file needs field-level coverage first.", "physicsguard-test-file-contract-review"),
        ],
        "minimum_inputs": ["visible_symptom", "external_source_of_truth", "physical_boundary", "known_inventory", "inventory_provider_capabilities", "current_blueprint_summary_or_affected_slice"],
        "required_outputs": ["preflight_status", "understanding_record", "blueprint_summary_inputs", "first_useful_layer", "access_gaps", "next_route"],
        "post_runtime_section": "## Blueprint slice\n\nEstablish the exact target identity, boundary fingerprint, independent inventory source, provider capabilities, and the first useful understanding layer. Consume only the current summary for ordinary preflight or the affected slice for a named boundary/inventory gap. This route does not author or fully review the blueprint; hand that work to `physicsguard-candidate-model-blueprint`. Missing or stale projection identity blocks without a full-scan fallback.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_summary_required", "blueprint_affected_boundary_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_preflight_projection"],
        "workflow": [
            "Freeze the symptom, external authority, physical boundary, and required inventory.",
            "Load the native route protocol and review subsystems, signals, parameters, assumptions, uncertainty, and prediction access.",
            "Proceed only inside the passed planning boundary; send unresolved mappings or files to their direct owners.",
        ],
    },
    "physicsguard-project-adoption": {
        "title": "PhysicsGuard Project Adoption",
        "description": "Use directly to audit, adopt, or upgrade a target repository's PhysicsGuard workflow records and current toolchain/artifact identity before non-trivial PhysicsGuard work; adoption is workflow evidence only, not physical validation or closure.",
        "display_name": "PhysicsGuard Project Adoption",
        "short_description": "Audit PhysicsGuard project workflow readiness",
        "role": "direct",
        "accept_when": [
            "The task is to check, create, or upgrade PhysicsGuard repository adoption records.",
            "Current toolchain, artifact inventory, blockers, or affected revalidation must be established.",
        ],
        "reject_handoffs": [
            ("The project is adopted and the task is to map its files and evidence gaps.", "physicsguard-project-evidence-registry"),
            ("The user asks whether a model result is validated or complete.", "physicsguard-audit-closure"),
        ],
        "minimum_inputs": ["project_root", "project_record", "runtime_identity", "current_blueprint_identity_when_present"],
        "required_outputs": ["adoption_status", "toolchain_status", "blueprint_identity", "adoption_boundary", "blockers", "required_revalidation"],
        "post_runtime_section": "## Blueprint adoption record\n\nRecord the current blueprint identity when one exists: canonical path, blueprint/review fingerprint, target revision and scope, artifact-root meaning, native authority identities, and whether the available projection is summary, affected, or full. This route does not author or fully review the blueprint. Adoption never derives completeness or physical truth. A missing or stale blueprint is reported as an adoption gap; this route does not create an alternate blueprint or silently scan the repository.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_adoption_identity_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_adoption_boundary"],
        "workflow": [
            "Run the read-only project audit first and compare current runtime and repository records.",
            "Load the native route protocol; adopt or upgrade only when authorized and necessary.",
            "Report workflow readiness separately from physical execution, validation, installation, and release.",
        ],
    },
    "physicsguard-project-evidence-registry": {
        "title": "PhysicsGuard Project Evidence Registry",
        "description": "Use directly to create, audit, or navigate one PhysicsGuard project's evidence registry, profile, artifact map, binding expectations, evidence bundles, physical facts, critical gaps, and closure handoffs without replacing file contracts or model validation.",
        "display_name": "PhysicsGuard Evidence Registry",
        "short_description": "Map one project's PhysicsGuard evidence",
        "role": "direct",
        "accept_when": [
            "One project's files, facts, bindings, bundles, and evidence gaps must be discovered or reconciled.",
            "An AI onboarding map or project-level evidence handoff is required.",
        ],
        "reject_handoffs": [
            ("One concrete test file needs its field contract checked.", "physicsguard-test-file-contract-review"),
            ("The request is cross-project historical or database-ledger search.", "none"),
        ],
        "minimum_inputs": ["project_root", "declared_artifacts", "binding_expectations", "project_profile", "current_blueprint_summary_or_affected_slice"],
        "required_outputs": ["reconciled_inventory", "binding_map", "affected_slice_fingerprint", "blueprint_binding_gaps", "critical_gaps", "closure_handoff"],
        "post_runtime_section": "## Blueprint slice\n\nConsume the summary for navigation and the exact affected slice when an evidence or resource identity changes. Bind each current artifact, resource, oracle, receipt, and freshness result to its exact blueprint element/semantic/obligation; return missing or stale bindings as explicit gaps, never as a project-wide pass. This route does not author or fully review the blueprint. Full blueprint loading is reserved for a whole-boundary handoff or closure. Projection fingerprints and target revision must be current; no source-scan fallback is allowed.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_summary_required", "blueprint_affected_evidence_slice_required", "whole_boundary_handoff_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_evidence_binding_projection"],
        "workflow": [
            "Discover and reconcile the current project profile, artifacts, facts, and binding expectations.",
            "Load the native route protocol and preserve required, critical, exempt, unknown, and unresolved rows explicitly.",
            "Return the navigation map and gaps; send proof claims to their direct validation or closure owner.",
        ],
    },
    "physicsguard-signal-mapping-review": {
        "title": "PhysicsGuard Signal Mapping Review",
        "description": "Use directly when external signals or parameters are mapped into PhysicsGuard variables and target identity, units, conversion, revision, confidence, reviewer state, temporal depth, interval bounds, or stale conditions must be checked before residual claims.",
        "display_name": "PhysicsGuard Signal Mapping",
        "short_description": "Review exact signal and parameter mappings",
        "role": "direct",
        "accept_when": [
            "The task concerns external-signal or parameter mapping identity, unit, conversion, confidence, review, timing, or staleness.",
            "Mapping evidence must be resolved before residual, adequacy, or predictive checks can use it.",
        ],
        "reject_handoffs": [
            ("A concrete many-field test file first needs a complete field contract.", "physicsguard-test-file-contract-review"),
            ("Mappings are current and the task is exact model/dataset validation.", "physicsguard-model-dataset-validation"),
        ],
        "minimum_inputs": ["governed_signal_or_parameter", "target_variable", "unit_and_conversion_evidence", "revision_identity", "current_affected_interface_projection"],
        "required_outputs": ["mapping_status", "review_gaps", "affected_slice_fingerprint", "downstream_blueprint_consumers", "temporal_boundary", "safe_mapping_claim"],
        "post_runtime_section": "## Blueprint slice\n\nConsume only the exact affected interface projection and its downstream consumers. Check source/target identity, unit, reference frame, sign convention, conversion semantic, time basis, revision, evidence fingerprint, and every selected consumer. This route does not author or fully review the blueprint. Omitted branches are outside scope, not passed. A missing/stale/ambiguous projection blocks and never triggers a full-blueprint or repository scan.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_affected_interface_slice_required", "blueprint_reverse_trace_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_interface_mapping_projection"],
        "workflow": [
            "Bind every governed external object to its exact target, unit, conversion, revision, and evidence.",
            "Load the native route protocol and check confidence, review, time coverage, intervals, and stale conditions.",
            "Keep unresolved mappings visible and do not mutate observed values.",
        ],
    },
    "physicsguard-test-file-contract-review": {
        "title": "PhysicsGuard Test File Contract Review",
        "description": "Use directly when concrete testbench or test-data files require deterministic file/field identity, units, timing, testbench version, parameter roles, mapping evidence, model binding, temporal depth, and project-gap coverage before AI analysis or validation.",
        "display_name": "PhysicsGuard Test File Contract",
        "short_description": "Check concrete test-file coverage contracts",
        "role": "direct",
        "accept_when": [
            "One or more concrete testbench, test-data, log, sensor, command, measurement, calibration, or fixture files are in scope.",
            "File and field contracts must pass before broad AI analysis or dataset validation.",
        ],
        "reject_handoffs": [
            ("No concrete test-data file is in scope.", "physicsguard-model-understanding-preflight"),
            ("Current file contracts pass and model/dataset consistency is now the request.", "physicsguard-model-dataset-validation"),
        ],
        "minimum_inputs": ["test_file", "testbench_profile", "field_inventory", "model_binding", "current_affected_blueprint_slice"],
        "required_outputs": ["contract_status", "field_dispositions", "blueprint_interface_bindings", "affected_slice_fingerprint", "mapping_gaps", "safe_analysis_boundary"],
        "post_runtime_section": "## Blueprint slice\n\nConsume the affected slice for the concrete file/dataset/testbench path. Bind deterministic files and fields to exact blueprint input/output/state/effect ports, physical obligations, expected evidence, units, frames, and time semantics. The contract does not author or qualify the full blueprint. A missing, stale, foreign, or ambiguous slice blocks without broadening to all fields, all models, or the full blueprint.",
        "native_route_load_when": ["route_selected_and_domain_execution_required", "blueprint_affected_file_slice_required"],
        "native_route_required_for": ["target_native_domain_workflow", "blueprint_test_file_contract_projection"],
        "workflow": [
            "Generate deterministic file and field identity before AI mapping judgment.",
            "Load the native route protocol and reconcile every field, role, unit, timing, mapping, and model binding.",
            "Block broad analysis until the exact contract passes; hand validation to the dataset route afterward.",
        ],
    },
}


OPENAI_DEFAULT_PROMPTS: dict[str, str] = {
    "physicsguard-candidate-model-blueprint": "Use $physicsguard-candidate-model-blueprint as the sole PhysicalModelBlueprint author/full reviewer; resolve blueprint_directory versus explicit_material_root and --material-root, run the canonical review, and compose only an in-memory selector when explicitly requested while keeping identity gaps and native execution separate.",
    "physicsguard-model-understanding-preflight": "Use $physicsguard-model-understanding-preflight directly to freeze target identity, boundary, inventory providers, capabilities, and the first useful blueprint layer; consume only the current summary or affected slice and do not claim full blueprint qualification.",
    "physicsguard-project-evidence-registry": "Use $physicsguard-project-evidence-registry directly; bind current evidence/resource identities and freshness to exact blueprint elements in the summary or affected slice, and return missing or stale gaps without a project-wide pass.",
    "physicsguard-test-file-contract-review": "Use $physicsguard-test-file-contract-review directly; bind deterministic files, fields, datasets, and testbench I/O to the exact affected blueprint interfaces, state, obligations, and evidence, with no full-blueprint fallback.",
    "physicsguard-signal-mapping-review": "Use $physicsguard-signal-mapping-review directly on the exact affected interface slice; validate source/target identity, units, frames, conversion, time semantics, revision, evidence, and downstream blueprint consumers.",
    "physicsguard-model-dataset-validation": "Use $physicsguard-model-dataset-validation directly; consume the current affected or whole blueprint projection and report per-element obligations, validation modes, validity, residual/oracle, evidence fingerprints, and unsupported claims.",
    "physicsguard-model-library": "Use $physicsguard-model-library directly; index or select assets by current blueprint fingerprint, obligation, profile, validity boundary, testbench, receipt, and verified reuse limits, never by loose similarity.",
    "physicsguard-project-adoption": "Use $physicsguard-project-adoption directly; record the current blueprint identity, target scope, artifact-root meaning, native authorities, and projection kind while keeping adoption separate from completeness or physical truth.",
    "physicsguard-audit-closure": "Use $physicsguard-audit-closure directly; consume the exact whole or affected review and any in-memory projection status, preserve identity-only gaps, and keep interpretation separate from current native execution and closure.",
    "physicsguard-ai-debugging": "Use $physicsguard-ai-debugging only for genuinely mixed routing; consume current blueprint summary/affected/reverse trace, delegate to the minimum direct owners, and never become a second blueprint author or reviewer.",
}


BLUEPRINT_RUNTIME_INPUTS = (
    "src/physicsguard/schema/physical_model_blueprint.py",
    "src/physicsguard/core/physical_model_blueprint.py",
    "src/physicsguard/core/physical_blueprint_trace.py",
    "src/physicsguard/core/target_inventory_authority.py",
    "src/physicsguard/io/physical_model_blueprint_loader.py",
)
BLUEPRINT_TEST_INPUTS = (
    "tests/fixtures/physicsguard_skill_execution_cases.json",
    "tests/test_physicsguard_skill_blueprint_contracts.py",
    "tests/test_skill_execution_depth.py",
)
BLUEPRINT_ROUTE_INPUTS: dict[str, tuple[str, ...]] = {
    "physicsguard-candidate-model-blueprint": (
        "src/physicsguard/core/physical_model_blueprint_adapters.py",
        "src/physicsguard/schema/fmi_observation.py",
        "src/physicsguard/core/fmi_observation.py",
        "templates/physical_model_blueprint.yaml",
        "tests/fixtures/physical_model_blueprint/canonical_minimal.json",
        "tests/fixtures/physical_model_blueprint/canonical_minimal.yaml",
        "examples/testfile_contracts/pump_loop/pump_loop_physical_blueprint.yaml",
        "examples/testfile_contracts/pump_loop/pump_loop_target_material.json",
        "tests/test_physical_blueprint_impact_trace.py",
        "tests/test_physical_model_blueprint_bad_cases.py",
        "tests/test_physical_model_blueprint_cli.py",
        "tests/test_physical_model_blueprint_external_target.py",
        "tests/test_physical_model_blueprint_native_authorities.py",
        "tests/test_physical_model_blueprint_provider_neutral.py",
        "tests/test_physical_model_blueprint_review.py",
        "tests/test_physical_model_blueprint_schema.py",
        "tests/test_physical_model_blueprint_target_authority.py",
        "tests/test_fmi_observation.py",
        "tests/test_reference_fmus_bouncing_ball_example.py",
    ),
    "physicsguard-signal-mapping-review": (
        "src/physicsguard/schema/signal_mapping.py",
        "src/physicsguard/core/signal_mapping.py",
        "templates/parameter_mapping_edges.yaml",
        "examples/testfile_contracts/pump_loop/coverage/pump_loop_mapping_edges.yaml",
        "tests/test_signal_mapping_ledger.py",
    ),
    "physicsguard-project-evidence-registry": (
        "src/physicsguard/schema/project_evidence.py",
        "src/physicsguard/core/project_evidence.py",
        "templates/project_evidence_registry.yaml",
        "examples/testfile_contracts/pump_loop/evidence/project_evidence_registry.yaml",
        "tests/test_project_evidence_registry.py",
    ),
    "physicsguard-model-dataset-validation": (
        "src/physicsguard/schema/model_dataset_validation.py",
        "src/physicsguard/core/model_dataset_validation.py",
        "src/physicsguard/schema/validation_adequacy.py",
        "src/physicsguard/core/validation_adequacy.py",
        "src/physicsguard/schema/validation_depth.py",
        "src/physicsguard/core/validation_depth.py",
        "src/physicsguard/schema/evidence_mesh.py",
        "src/physicsguard/core/evidence_mesh.py",
        "tests/test_model_dataset_validation.py",
        "tests/test_validation_adequacy.py",
        "tests/test_validation_depth_receipts.py",
        "tests/test_evidence_mesh.py",
        "tests/test_predictive_rollout_validation.py",
    ),
    "physicsguard-audit-closure": (
        "tests/test_reference_fmus_bouncing_ball_example.py",
        "tests/test_validation_blueprint_coverage.py",
    ),
}


def blueprint_contract(
    *,
    authority_mode: str,
    projection_kinds: tuple[str, ...],
    required_operation_ids: tuple[str, ...],
    required_obligation_ids: tuple[str, ...],
    claim_boundary: str,
    additional_block_on: tuple[tuple[str, str], ...] = (),
) -> dict[str, Any]:
    if authority_mode not in {"sole_author_full_reviewer", "consumer_only"}:
        raise ValueError(f"unsupported blueprint authority mode: {authority_mode}")
    return {
        "schema_version": "physicsguard.skill_blueprint_route_contract.v1",
        "authority_mode": authority_mode,
        "projection_kinds": list(projection_kinds),
        "required_operation_ids": list(required_operation_ids),
        "required_obligation_ids": list(required_obligation_ids),
        "block_on": [
            {
                "finding_code": "blueprint_projection_missing_stale_foreign_or_ambiguous",
                "condition": "a required blueprint projection or its blueprint, review, relation-set, recipe, target-revision, or evidence fingerprint is missing, stale, foreign, ambiguous, or caller-rehashed",
            },
            {
                "finding_code": "blueprint_authority_boundary_violated",
                "condition": (
                    "any route other than the sole author/full reviewer authors or fully reviews the blueprint"
                    if authority_mode == "consumer_only"
                    else "the canonical author/full-review route is replaced, bypassed, or duplicated"
                ),
            },
            {
                "finding_code": "blueprint_required_obligation_unproved",
                "condition": "any route-specific blueprint obligation lacks current target-native evidence or is replaced by AI prose or a self-declared pass",
            },
            {
                "finding_code": "blueprint_gap_or_claim_boundary_unreconciled",
                "condition": "the first gap, outside-scope branch, unsupported claim, closure handoff, or bounded claim required by this route is omitted or promoted to pass",
            },
            *(
                {"finding_code": finding_code, "condition": condition}
                for finding_code, condition in additional_block_on
            ),
        ],
        "self_reported_status_allowed": False,
        "missing_projection_behavior": "block_visible_no_fallback",
        "claim_boundary": claim_boundary,
    }


BLUEPRINT_ROUTE_GUARD_CONTRACTS: dict[str, dict[str, Any]] = {
    "physicsguard-ai-debugging": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("summary", "affected", "reverse_trace"),
        required_operation_ids=(
            "api:physicsguard.summary_physical_blueprint_projection",
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.reverse_trace_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_summary_affected_reverse_consumption",
            "blueprint_minimum_owner_handoff",
            "blueprint_gap_handoff",
        ),
        claim_boundary="This mixed coordinator may consume only current summary, affected, and reverse-trace projections to select and hand off to the minimum direct owners; it cannot author, fully review, or close the blueprint.",
    ),
    "physicsguard-audit-closure": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("affected", "full"),
        required_operation_ids=(
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.full_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_whole_or_affected_review_consumption",
            "blueprint_denominator_depth_first_gap",
            "blueprint_closure_and_gap_accounting",
            "blueprint_in_memory_projection_identity_consumption",
            "blueprint_identity_only_terminal_accounting",
            "blueprint_in_memory_execution_claim_boundary",
        ),
        claim_boundary="Closure is limited to the exact current affected or full review denominator, achieved depth, first gap, native evidence, outside-scope rows, and safe claim. An in-memory projection is frozen interpretation content with execution unlicensed; it cannot author, requalify, refresh, or prove current native execution.",
        additional_block_on=(
            (
                "blueprint_projection_promoted_to_closure",
                "an in-memory interpretation projection or an AI answer is treated as current evidence, native execution, high-fidelity reconstruction, or closure",
            ),
            (
                "blueprint_identity_only_terminal_promoted",
                "an identity-only source, test, resource, or oracle gap is omitted, repaired by scanning, or promoted to resolved content",
            ),
        ),
    ),
    "physicsguard-candidate-model-blueprint": blueprint_contract(
        authority_mode="sole_author_full_reviewer",
        projection_kinds=("summary", "affected", "reverse_trace", "full"),
        required_operation_ids=(
            "command:python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --pretty",
            "command:python -m physicsguard.cli blueprint review BLUEPRINT --target-authority AUTHORITY --material-root ROOT --pretty",
            "schema:physicsguard.fmi-observation-request.v1",
            "api:physicsguard.summary_physical_blueprint_projection",
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.reverse_trace_physical_blueprint_projection",
            "api:physicsguard.full_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_author_and_full_review",
            "blueprint_canonical_review",
            "blueprint_impact_and_reverse_trace",
            "blueprint_projection_identity_current",
            "blueprint_depth_first_gap_and_safe_claim",
            "blueprint_material_root_resolution",
            "blueprint_external_resource_not_run_boundary",
            "blueprint_generic_fmi_observation_and_independent_oracle",
            "blueprint_native_directory_dna_identity",
            "blueprint_in_memory_compact_or_single_selector",
            "blueprint_in_memory_execution_claim_boundary",
        ),
        claim_boundary="This is the sole PhysicsGuard author/full-review authority for the declared physical target and inventory. Explicit external material is never inferred, FMI observations remain bound to a restricted independent oracle, and the native-directory/in-memory projection status remains frozen interpretation with execution_claim_licensed=false; none proves fresh native execution or unsupported high-fidelity truth.",
        additional_block_on=(
            (
                "blueprint_material_root_boundary_violated",
                "explicit_material_root is treated as the blueprint directory, searched, downloaded, or reviewed without the caller-selected --material-root, or external_resource_not_run is promoted",
            ),
            (
                "blueprint_fmi_oracle_independence_violated",
                "FMI caller expectations or native outputs replace the restricted source-independent oracle or are conflated with its result",
            ),
            (
                "blueprint_projection_execution_promoted",
                "an in-memory projection or an AI answer is promoted to current native execution, fresh evidence, or high-fidelity reconstruction",
            ),
        ),
    ),
    "physicsguard-model-dataset-validation": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("affected", "full"),
        required_operation_ids=(
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.full_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_affected_or_whole_validation_consumption",
            "blueprint_per_element_coverage",
            "blueprint_unsupported_claim_gap_accounting",
        ),
        claim_boundary="Validation covers only the exact affected or whole projection and reports evidence per blueprint element and obligation; aggregate counts cannot authorize an uncovered element or unsupported claim.",
    ),
    "physicsguard-model-library": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("summary", "affected", "full"),
        required_operation_ids=(
            "api:physicsguard.summary_physical_blueprint_projection",
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.full_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_fingerprint_and_projection_consumption",
            "blueprint_asset_reuse_limit",
            "blueprint_compatibility_gap_accounting",
        ),
        claim_boundary="Library reuse is limited to exact current blueprint fingerprints, physical obligations, profiles, validity boundaries, testbenches, receipts, and verified reuse limits; similarity is not compatibility.",
    ),
    "physicsguard-model-understanding-preflight": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("summary", "affected"),
        required_operation_ids=(
            "api:physicsguard.summary_physical_blueprint_projection",
            "api:physicsguard.affected_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_target_boundary_and_inventory_consumption",
            "blueprint_first_useful_layer",
            "blueprint_access_gap_handoff",
        ),
        claim_boundary="Preflight may establish target identity, boundary, independent inventory authority, provider capability, and the first useful layer from a current summary or affected slice; it does not qualify the whole blueprint.",
    ),
    "physicsguard-project-adoption": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("summary",),
        required_operation_ids=(
            "api:physicsguard.summary_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_identity_and_scope_recorded",
            "blueprint_adoption_not_completeness",
            "blueprint_adoption_gap_and_revalidation",
        ),
        claim_boundary="Adoption records the current blueprint identity, scope, artifact-root meaning, native authorities, and projection kind; adoption is never a completeness, physical-truth, or full-review verdict.",
    ),
    "physicsguard-project-evidence-registry": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("summary", "affected", "full"),
        required_operation_ids=(
            "api:physicsguard.summary_physical_blueprint_projection",
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.full_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_evidence_and_resource_binding",
            "blueprint_binding_freshness",
            "blueprint_missing_stale_gap_and_closure_handoff",
        ),
        claim_boundary="Registry results bind exact current evidence, resources, oracles, receipts, freshness, and gaps to blueprint elements; they do not convert missing or stale evidence into a project-wide pass.",
    ),
    "physicsguard-signal-mapping-review": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("affected", "reverse_trace"),
        required_operation_ids=(
            "api:physicsguard.affected_physical_blueprint_projection",
            "api:physicsguard.reverse_trace_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_affected_interface_consumption",
            "blueprint_downstream_reverse_consumers",
            "blueprint_mapping_gap_and_safe_claim",
        ),
        claim_boundary="Mapping review covers only the exact affected interface and reverse-traced downstream consumers with current identity, units, frames, conversion, time, revision, and evidence; omitted branches are outside scope, not passed.",
    ),
    "physicsguard-test-file-contract-review": blueprint_contract(
        authority_mode="consumer_only",
        projection_kinds=("affected",),
        required_operation_ids=(
            "api:physicsguard.affected_physical_blueprint_projection",
        ),
        required_obligation_ids=(
            "blueprint_consumer_boundary",
            "blueprint_file_field_interface_binding",
            "blueprint_affected_file_slice_consumption",
            "blueprint_mapping_gap_and_safe_boundary",
        ),
        claim_boundary="The contract binds only the concrete file, field, dataset, and testbench slice to exact blueprint ports, state, obligations, units, frames, time, and evidence; it cannot qualify the full blueprint.",
    ),
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
    blueprint_route_contract = dict(BLUEPRINT_ROUTE_GUARD_CONTRACTS[skill_id])
    blueprint_contract_fingerprint = canonical_fingerprint(
        blueprint_route_contract
    )
    blueprint_oracles = [
        {
            "oracle_id": f"oracle:{skill_id}:{obligation_id}",
            "obligation_id": obligation_id,
            "predicate_kind": "native_blueprint_obligation_must_pass",
            "predicate": (
                "The exact route-owned blueprint operation and projection evidence "
                f"for {obligation_id!r} must be current and pass; AI prose, a "
                "self-declared status, or a caller-rehashed projection cannot pass."
            ),
            "expected_finding_code": "blueprint_required_obligation_unproved",
        }
        for obligation_id in blueprint_route_contract["required_obligation_ids"]
    ]
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
        "blueprint_route_contract": blueprint_route_contract,
        "blueprint_route_contract_fingerprint": blueprint_contract_fingerprint,
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
        "blueprint_route_contract_fingerprint": blueprint_contract_fingerprint,
        "blueprint_oracles": blueprint_oracles,
    }
    known_good = {
        "schema_version": "physicsguard.family_baseline_known_good.v1",
        "artifact_role": "family_baseline_regression",
        "case_id": f"known-good:{skill_id}:complete-native-route",
        "target_skill_id": skill_id,
        "covered_obligation_ids": obligations,
        "blueprint_route_contract_fingerprint": blueprint_contract_fingerprint,
        "covered_blueprint_obligation_ids": list(
            blueprint_route_contract["required_obligation_ids"]
        ),
        "covered_blueprint_projection_kinds": list(
            blueprint_route_contract["projection_kinds"]
        ),
        "executed_blueprint_operation_ids": list(
            blueprint_route_contract["required_operation_ids"]
        ),
        "expected_blueprint_status": "pass",
        "expected_native_status": "pass",
        "self_reported_outcome_allowed": False,
    }
    known_bad = {
        "schema_version": "physicsguard.family_baseline_known_bad_set.v1",
        "artifact_role": "family_baseline_regression",
        "target_skill_id": skill_id,
        "blueprint_route_contract_fingerprint": blueprint_contract_fingerprint,
        "blueprint_cases": [
            {
                "case_id": f"known-bad:{skill_id}:{row['finding_code']}",
                "trigger_condition": row["condition"],
                "expected_native_status": "blocked",
                "expected_finding_code": row["finding_code"],
                "self_reported_outcome_allowed": False,
            }
            for row in blueprint_route_contract["block_on"]
        ],
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
        "blueprint_route_contract_fingerprint": blueprint_contract_fingerprint,
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
        "blueprint_route_contract_fingerprint": blueprint_contract_fingerprint,
        "blueprint_projection_contract": {
            "authority_mode": blueprint_route_contract["authority_mode"],
            "projection_kinds": list(blueprint_route_contract["projection_kinds"]),
            "required_operation_ids": list(
                blueprint_route_contract["required_operation_ids"]
            ),
            "required_obligation_ids": list(
                blueprint_route_contract["required_obligation_ids"]
            ),
            "claim_boundary": blueprint_route_contract["claim_boundary"],
        },
        "candidate_definition": candidate_definition,
        "authoring_events": [purpose_event, candidate_event],
    }
    return guard_contract, candidate, oracle_set, known_good, known_bad


def _flowguard_export(
    skill_id: str,
    owner: str,
    route: str,
    guard_contract: dict[str, Any],
    toolchain_identity: Mapping[str, str],
) -> dict[str, Any]:
    purpose_step = f"step:{skill_id}:family-baseline-contract"
    candidate_step = f"step:{skill_id}:family-baseline-candidate"
    good_step = f"step:{skill_id}:family-baseline-good"
    bad_steps = [
        f"step:{skill_id}:family-baseline-bad:{row['failure_id'].rsplit(':', 1)[-1]}"
        for row in guard_contract["prevented_failure_classes"]
    ]
    task_model_step = f"step:{skill_id}:task-local-model-deepening"
    family_maintenance_step = "step:physicsguard-family:distribution-authority"
    owns_family_maintenance = skill_id == FAMILY_MAINTENANCE_MEMBER_ID
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
        {"step_id": task_model_step, "route_id": route, "owner_id": owner, "action_kind": "native", "terminal_kind": "", "prerequisite_step_ids": [good_step]},
        *(
            [
                {
                    "step_id": family_maintenance_step,
                    "route_id": route,
                    "owner_id": FAMILY_MAINTENANCE_OWNER_ID,
                    "action_kind": "development_process",
                    "terminal_kind": "",
                    "prerequisite_step_ids": [purpose_step],
                }
            ]
            if owns_family_maintenance
            else []
        ),
        {"step_id": terminal, "route_id": route, "owner_id": owner, "action_kind": "terminal", "terminal_kind": "success", "prerequisite_step_ids": [*bad_steps, task_model_step, *([family_maintenance_step] if owns_family_maintenance else [])]},
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
        {
            "obligation_id": f"obligation:{skill_id}:task-local-model-deepening",
            "invariant_id": f"invariant:{skill_id}:task-local-model-deepening",
            "owner_step_ids": [task_model_step],
            "required": True,
        },
        *(
            [
                {
                    "obligation_id": FAMILY_MAINTENANCE_OBLIGATION_ID,
                    "invariant_id": (
                        "invariant:physicsguard-family:distribution-authority"
                    ),
                    "owner_step_ids": [family_maintenance_step],
                    "required": True,
                }
            ]
            if owns_family_maintenance
            else []
        ),
    ]
    return {
        "schema_version": "skillguard.flowguard_model_export.v2",
        "flowguard_schema_version": toolchain_identity[
            "flowguard_schema_version"
        ],
        "toolchain_identity": dict(toolchain_identity),
        "model_id": f"{skill_id}.family-baseline-regression.current",
        "parent_model_id": "physicsguard.guard-family.family-baseline-regression.current",
        "functions": [{"function_id": f"function:{skill_id}:guard-model", "business_intent": "Prove the maintained family baseline checker capability only: " + guard_contract["prevented_failure_purpose"], "owner_id": owner, "route_ids": [route]}],
        "routes": [{"route_id": route, "function_id": f"function:{skill_id}:guard-model", "owner_id": owner, "step_ids": [row["step_id"] for row in steps], "success_terminal_step_id": terminal, "blocked_terminal_step_id": blocked, "handoffs": []}],
        "steps": steps,
        "obligations": obligations,
        "invariant_ids": [row["invariant_id"] for row in obligations],
        "claim_boundary": (
            "This model proves maintained family baseline regression and the presence "
            "of the strict task-local model-deepening check. The audit-closure member "
            "also carries the one family-level distribution authority owner; that "
            "process evidence never proves a PhysicsGuard domain result. A concrete "
            "PhysicsGuard model still requires target-owned current native receipts "
            "and exact candidate-bound evidence."
        ),
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


def _native_depth_reference(
    config: dict[str, Any],
    guard_contract: dict[str, Any],
    obligations: list[str],
    physicsguard_version: str,
) -> str:
    skill_id = str(guard_contract["target_skill_id"])
    owner = str(guard_contract["native_owner_id"])
    route = str(guard_contract["native_route_id"])
    task_model_check = f"check:{skill_id}:task-local-model-deepening"
    failures = "\n".join(
        f"- `{row['title']}` ({row['proof_strength']}): block when {row['block_when']}. "
        f"Claim boundary: {row['claim_boundary']}"
        for row in guard_contract["prevented_failure_classes"]
    )
    obligation_rows = "\n".join(f"- `{value}`" for value in obligations)
    return (
        "# Native Depth and Purpose\n\n"
        "Load this reference only when the selected route creates, materially deepens, revises, or closes a task-local model. Ordinary bounded route execution does not eagerly load it.\n\n"
        "## PhysicsGuard dynamic model-purpose and family baseline\n\n"
        f"Family capability baseline purpose: {config['purpose']}\n\n"
        f"Family route bounded claim: {config['claim_boundary']}\n\n"
        f"Family baseline proof boundary: {guard_contract['claim_boundary']}\n\n"
        f"Shared simulator prerequisite: install the current `physicsguard=={physicsguard_version}` package in the active Python environment. Before executing this skill, run `python -c \"import physicsguard; print(physicsguard.__version__)\"`; a missing package is a visible blocker and there is no bundled fallback.\n\n"
        "Issue target-owned execution-depth receipts with `python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`. The package module is the sole editable depth implementation shared by all ten skills.\n\n"
        "The bundled `guard-model/` files declare these maintained family baseline regression classes:\n\n"
        f"{failures}\n\n"
        "The target-native obligation inventory for this route is:\n\n"
        f"{obligation_rows}\n\n"
        "Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal ranges are not per-obligation evidence. Every satisfied obligation must retain its exact target-native semantic object, `evidence_ref`, and lowercase content hash; missing, renamed, overlapping, mechanically generated, or summary-only mappings block broad closure.\n\n"
        "These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.\n\n"
        "For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.\n\n"
        "### Strict task-local model deepening\n\n"
        f"This skill's task-local owner is `{owner}` on `{route}`; its declared closure check is `{task_model_check}`. The shared PhysicsGuard schema and evaluator provide the envelope, while this native owner keeps the route-specific physical/evidence judgment.\n\n"
        "For every non-trivial task, use the existing `task-model plan -> observe -> revision` route with the strict current schema. The plan must declare a non-empty task purpose, an independently owned coverage-universe id and SHA-256, explicit assumptions and unknowns (empty is allowed only when written explicitly), iteration, an exact predecessor receipt after iteration zero, and a current `physicsguard_task_native_depth_receipt` bound to the plan model. Retired optional fields and compatibility shapes are invalid.\n\n"
        "The native depth receipt must account for exactly six families: execution depth, mapping, residual, uncertainty, diagnosability, and predictive rollout. Open gaps, resolution classes, external input ids, and next actions come from that target-owned receipt; AI prose, `resolved=true`, caller-written gap lists, and self-reported understanding have no closure authority.\n\n"
        "Freeze the prediction before observation and bind the observation to the exact plan fingerprint, selected probe, producer, source, independence group, and evidence SHA-256. If the observation contradicts every declared hypothesis, return `model_miss` and revise the hypothesis/model universe; never select a physical cause by elimination outside the declared space.\n\n"
        "A candidate revision must preserve distinct base/candidate identities and consume base/candidate native-depth receipts plus exactly one typed regression receipt, one independent holdout receipt, and one predictive-rollout receipt. All three must bind the same task, plan, revision, coverage fingerprint, and candidate SHA-256; the holdout must be independent from candidate construction. PhysicsGuard derives resolved, persisted, and introduced gaps by comparing the two native receipts. Renaming or deleting a caller gap is not progress.\n\n"
        "`model_closed_for_task` is legal only when the candidate identity is current, every typed check passes, and the candidate native receipt has zero open gaps. Otherwise preserve the exact non-success boundary: `continue_iteration`, `external_input_required`, `progress_stalled`, `iteration_limit`, `scope_excluded`, or `model_miss`. A passing regression with any native gap is continuation, not closure.\n\n"
        "Use `python -m physicsguard.guard_model_contract check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.\n\n"
        "`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.\n\n"
        "`physicsguard.guard_model_contract` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.\n"
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _template_pack_reference() -> str:
    return """# Validated Template Pack Routing

Load this reference only when the selected PhysicsGuard route needs target-owned template selection, preview, instantiation, validation, or harvest. A preview is planning evidence, never domain proof.

- Target families: `physicsguard`; native owner: `physicsguard.purpose-pack-selector.v1`.
- Current catalogs: `physicsguard.purpose-template-packs` revision `1`.
- Resolve the task through this skill's native route first, then ask the target-owned adapter for a current neutral projection; never infer a template from wording or a skill name.
- Preserve the adapter's complete candidate and rejection accounting. Zero candidates may use only the declared validated base; one candidate gets a read-only preview; many candidates require complete dependencies, pairwise compatibility, one field owner, and target-authored dominance or must block as ambiguous.
- Recompute the projection immediately before applying a preview. A stale request, catalog, route, builder, validator, or content identity blocks all writes.
- Hand the selected preview to the target-declared builder and consume every target-native validator receipt. Template structure is not domain validity, completion, installation, release, or publication evidence.
- Record a harvest disposition after creating or materially deepening a reusable model, and keep no-match evidence visible.
- Declared validated bases: `physicsguard.base.audit-work-package`.
- Template inventory: `physicsguard.base.audit-work-package`, `physicsguard.dataset-validation-basic`, `physicsguard.dataset-validation-comprehensive`, `physicsguard.model-understanding-preflight`, `physicsguard.signal-mapping-core`, `physicsguard.signal-mapping-evidence`.
- Native validator inventory: `physicsguard.template-pack-instance-validator.v1`, `physicsguard.template-pack-manifest-validator.v1`, `physicsguard.template-pack-selection-validator.v1`.
- Claim boundary: the catalog supports deterministic workflow-pack selection and structural native validation only; physical truth, dataset adequacy, `audit_pass`, installation, and release require separate current PhysicsGuard evidence.
"""


def _render_compact_skill(
    skill_id: str,
    entry: dict[str, Any],
    guard_contract: dict[str, Any],
) -> str:
    accept_rows = "\n".join(f"- {value}" for value in entry["accept_when"])
    reject_rows = "\n".join(
        f"- {condition} Handoff: `{target}`."
        for condition, target in entry["reject_handoffs"]
    )
    workflow_rows = "\n".join(
        f"{index}. {value}" for index, value in enumerate(entry["workflow"], 1)
    )
    output_rows = "\n".join(f"- `{value}`" for value in entry["required_outputs"])
    role_label = "mixed/unclear coordinator" if entry["role"] == "composite" else "independent direct route"
    return (
        "---\n"
        f"name: {skill_id}\n"
        f"description: {json.dumps(entry['description'], ensure_ascii=False)}\n"
        "---\n\n"
        f"# {entry['title']}\n\n"
        "## Entry boundary\n\n"
        f"Route: `{guard_contract['native_route_id']}`; native owner: `{guard_contract['native_owner_id']}`; role: `{role_label}`. Read `references/route-capsule.json` to confirm this exact identity and the machine-checkable decision boundary.\n\n"
        "Accept this route only when:\n\n"
        f"{accept_rows}\n\n"
        "Reject or hand off when:\n\n"
        f"{reject_rows}\n\n"
        "## Minimum workflow\n\n"
        f"{workflow_rows}\n\n"
        "Before executing a native command, verify the installed `physicsguard` version against `runtime-requirements.json`; a missing or mismatched runtime is a visible blocker with no fallback.\n\n"
        f"{entry['post_runtime_section']}\n\n"
        "## Conditional detail loading\n\n"
        f"- Load `{NATIVE_ROUTE_REFERENCE}` after route selection when domain execution needs the detailed workflow.\n"
        f"- Load `{NATIVE_DEPTH_REFERENCE}` before creating, materially deepening, revising, or closing a task-local model. Do not load it for an ordinary bounded action.\n"
        f"- Load `{TEMPLATE_PACK_REFERENCE}` only for target-owned template selection, preview, instantiation, validation, or harvest. Preview is not proof.\n"
        "- Do not load another PhysicsGuard skill's references merely because the skills are related. Use an explicit typed handoff.\n\n"
        "## Hard gates\n\n"
        "- Preserve the target's native judgment, exact evidence identities, explicit unknowns, and non-pass states.\n"
        "- Never treat AI self-report, prose completeness, progress, an inventory, or a template preview as native execution evidence.\n"
        "- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.\n"
        "- Do not add a compatibility route, alias, fallback, copied runtime, or alternate success owner.\n\n"
        "## Required outputs\n\n"
        f"{output_rows}\n\n"
        f"Claim boundary: {TARGETS[skill_id]['claim_boundary']}\n"
    )


def _render_openai_yaml(skill_id: str, entry: dict[str, Any]) -> str:
    short_description = str(entry["short_description"])
    if not 25 <= len(short_description) <= 64:
        raise ValueError(f"{skill_id}: short_description must be 25-64 characters")
    prompt = OPENAI_DEFAULT_PROMPTS[skill_id]
    return (
        "interface:\n"
        f"  display_name: {json.dumps(entry['display_name'], ensure_ascii=False)}\n"
        f"  short_description: {json.dumps(short_description, ensure_ascii=False)}\n"
        f"  default_prompt: {json.dumps(prompt, ensure_ascii=False)}\n"
    )


def _route_capsule(
    skill_root: Path,
    skill_id: str,
    entry: dict[str, Any],
    guard_contract: dict[str, Any],
) -> dict[str, Any]:
    reference_rows = [
        {
            "path": NATIVE_ROUTE_REFERENCE,
            "load_when": list(entry["native_route_load_when"]),
            "required_for": list(entry["native_route_required_for"]),
        },
        {
            "path": NATIVE_DEPTH_REFERENCE,
            "load_when": [
                "create_task_local_model",
                "materially_deepen_model",
                "revise_candidate_model",
                "claim_model_closure",
            ],
            "required_for": DEEP_CAPABILITIES,
        },
        {
            "path": TEMPLATE_PACK_REFERENCE,
            "load_when": [
                "select_template_pack",
                "preview_template_pack",
                "instantiate_template_pack",
                "validate_template_pack",
                "harvest_reusable_model",
            ],
            "required_for": ["validated_template_pack_routing"],
        },
    ]
    for row in reference_rows:
        path = skill_root / str(row["path"])
        if not path.is_file():
            raise ValueError(f"{skill_id}: conditional reference missing: {row['path']}")
        row["sha256"] = _file_sha256(path)
    prompt_path = skill_root / "SKILL.md"
    return {
        "schema_version": ROUTE_CAPSULE_SCHEMA,
        "target_skill_id": skill_id,
        "native_owner_id": guard_contract["native_owner_id"],
        "native_route_id": guard_contract["native_route_id"],
        "route_role": entry["role"],
        "broad_route_prerequisite": False,
        "accept_when": list(entry["accept_when"]),
        "reject_handoffs": [
            {"condition": condition, "target_skill_id": target}
            for condition, target in entry["reject_handoffs"]
        ],
        "minimum_inputs": list(entry["minimum_inputs"]),
        "required_outputs": list(entry["required_outputs"]),
        "initial_load": ["agents/openai.yaml", "SKILL.md", ROUTE_CAPSULE_REFERENCE],
        "conditional_references": reference_rows,
        "maximum_reference_depth": 1,
        "cross_skill_reference_loading": "typed_handoff_only",
        "entry_prompt_sha256": _file_sha256(prompt_path),
        "claim_boundary": TARGETS[skill_id]["claim_boundary"],
    }


def _write_entry_projection(
    skill_id: str,
    config: dict[str, Any],
    entry: dict[str, Any],
    guard_contract: dict[str, Any],
    obligations: list[str],
    toolchain_identity: Mapping[str, str],
) -> None:
    skill_root = SKILL_ROOT / skill_id
    references_root = skill_root / "references"
    references_root.mkdir(parents=True, exist_ok=True)
    route_protocol = references_root / "native-route-protocol.md"
    if not route_protocol.is_file():
        raise ValueError(f"{skill_id}: native route protocol must be preserved before contraction")
    (references_root / "native-depth-and-purpose.md").write_text(
        _native_depth_reference(
            config,
            guard_contract,
            obligations,
            toolchain_identity["physicsguard_version"],
        ),
        encoding="utf-8",
    )
    (references_root / "template-pack-routing.md").write_text(
        _template_pack_reference(), encoding="utf-8"
    )
    prompt = _render_compact_skill(skill_id, entry, guard_contract)
    if len(prompt.encode("utf-8")) > MAX_SKILL_ENTRY_BYTES:
        raise ValueError(f"{skill_id}: compact SKILL.md exceeds {MAX_SKILL_ENTRY_BYTES} bytes")
    (skill_root / "SKILL.md").write_text(prompt, encoding="utf-8")
    agents_root = skill_root / "agents"
    agents_root.mkdir(parents=True, exist_ok=True)
    (agents_root / "openai.yaml").write_text(
        _render_openai_yaml(skill_id, entry), encoding="utf-8"
    )
    (references_root / "route-capsule.json").write_text(
        stable_json(_route_capsule(skill_root, skill_id, entry, guard_contract)),
        encoding="utf-8",
    )


def _write_prompt_load_graph(toolchain_identity: Mapping[str, str]) -> None:
    nodes: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    for skill_id in sorted(TARGETS):
        skill_root = SKILL_ROOT / skill_id
        capsule = json.loads(
            (skill_root / ROUTE_CAPSULE_REFERENCE).read_text(encoding="utf-8")
        )
        initial_paths = [
            f"skill/{skill_id}/agents/openai.yaml",
            f"skill/{skill_id}/SKILL.md",
            f"skill/{skill_id}/{ROUTE_CAPSULE_REFERENCE}",
        ]
        conditional_paths = [
            f"skill/{skill_id}/{row['path']}"
            for row in capsule["conditional_references"]
        ]
        for path, phase in [
            *[(value, "initial") for value in initial_paths],
            *[(value, "conditional") for value in conditional_paths],
        ]:
            file_path = ROOT / path
            nodes.append(
                {
                    "node_id": f"artifact:{path}",
                    "skill_id": skill_id,
                    "path": path,
                    "load_phase": phase,
                    "bytes": file_path.stat().st_size,
                    "sha256": _file_sha256(file_path),
                }
            )
        routes.append(
            {
                "target_skill_id": skill_id,
                "native_owner_id": capsule["native_owner_id"],
                "native_route_id": capsule["native_route_id"],
                "route_role": capsule["route_role"],
                "broad_route_prerequisite": capsule["broad_route_prerequisite"],
                "initial_paths": initial_paths,
                "initial_bytes": sum((ROOT / path).stat().st_size for path in initial_paths),
                "conditional_references": capsule["conditional_references"],
                "selection_fixture": {
                    "request_shape": ROUTE_ENTRIES[skill_id]["accept_when"][0],
                    "expected_skill_id": skill_id,
                },
                "deep_capabilities": list(DEEP_CAPABILITIES),
            }
        )
    graph = {
        "schema_version": PROMPT_LOAD_GRAPH_SCHEMA,
        "suite_version": toolchain_identity["physicsguard_version"],
        "toolchain_identity": dict(toolchain_identity),
        "route_count": len(routes),
        "initial_loading_rule": "selected_metadata_plus_compact_skill_plus_route_capsule_only",
        "all_reference_loading_forbidden": True,
        "cross_skill_loading_rule": "typed_handoff_only",
        "maximum_reference_depth": 1,
        "max_skill_entry_bytes": MAX_SKILL_ENTRY_BYTES,
        "max_initial_route_bytes": MAX_INITIAL_ROUTE_BYTES,
        "required_deep_capabilities": list(DEEP_CAPABILITIES),
        "nodes": nodes,
        "routes": routes,
        "known_bad_cases": [
            "wrong_route_owner",
            "broad_route_captures_direct_request",
            "eager_all_references",
            "conditional_reference_missing",
            "undeclared_or_cross_skill_reference",
            "reference_hash_stale",
            "deep_capability_unreachable",
            "toolchain_identity_stale",
        ],
        "claim_boundary": "This graph proves current author prompt identities, direct-route ownership, bounded initial loading, and conditional deep-capability reachability. It does not prove future AI behavior or target-domain execution.",
    }
    PROMPT_LOAD_GRAPH_PATH.write_text(stable_json(graph), encoding="utf-8")


def _update_suite_mesh(toolchain_identity: Mapping[str, str]) -> None:
    path = ROOT / ".flowguard" / "physicsguard_skill_suite_mesh.json"
    mesh = json.loads(path.read_text(encoding="utf-8"))
    mesh["mesh_version"] = "4.1"
    mesh["canonical_simulator"]["consumer_dependency"] = (
        f"physicsguard=={toolchain_identity['physicsguard_version']}"
    )
    mesh["toolchain_identity"] = dict(toolchain_identity)
    check_counts: dict[str, int] = {}
    for skill_id in sorted(TARGETS):
        source = json.loads(
            (
                SKILL_ROOT
                / skill_id
                / ".skillguard"
                / "contract-source.json"
            ).read_text(encoding="utf-8")
        )
        check_counts[skill_id] = len(source.get("checks", []))
    for child in mesh.get("children", []):
        target_skill_id = str(child.get("target_skill_id", ""))
        if target_skill_id in check_counts:
            child["declared_check_count"] = check_counts[target_skill_id]
    total_check_count = sum(check_counts.values())
    test_mesh = mesh["test_mesh"]
    test_mesh.update(
        {
            "inventory_revision": (
                f"ten-members-{total_check_count}-exact-check-owners"
            ),
            "planned": total_check_count,
            "executed": 0,
            "failed": 0,
            "not_run": total_check_count,
            "not_run_reason": (
                "Current generated source defines the owner topology only; no "
                "frozen SkillGuard owner execution receipt is embedded as source."
            ),
            "parent_gate": (
                "ten frozen same-unit member plans; no suite-parent receipt"
            ),
            "supervisor_run_count": 10,
            "read_only_reuse_review": {
                "selected_owner_count": total_check_count,
                "reusable_owner_count": 0,
                "would_execute_owner_count": total_check_count,
            },
        }
    )
    mesh["entry_loading"] = {
        "route_count": 10,
        "direct_route_count": 9,
        "composite_route_count": 1,
        "composite_route_id": "route:physicsguard-ai-debugging:audit",
        "composite_is_parent": False,
        "route_capsule_schema": ROUTE_CAPSULE_SCHEMA,
        "prompt_load_graph": PROMPT_LOAD_GRAPH_PATH.relative_to(ROOT).as_posix(),
        "initial_loading_rule": "selected_metadata_plus_compact_skill_plus_route_capsule_only",
        "conditional_reference_paths": [
            NATIVE_ROUTE_REFERENCE,
            NATIVE_DEPTH_REFERENCE,
            TEMPLATE_PACK_REFERENCE,
        ],
        "maximum_reference_depth": 1,
        "required_deep_capabilities": list(DEEP_CAPABILITIES),
    }
    architecture = mesh["architecture_reduction"]
    architecture["observable_contract"] = (
        "Ten target-owned semantic inventories, direct route identities, and deep native capabilities remain reachable while initial entry loading contracts to one selected prompt and capsule; no suite-level closure is promised."
    )
    candidates = architecture["candidates"]
    if not any(row.get("candidate_id") == "contract-eager-skill-entry-prompts" for row in candidates):
        candidates.append(
            {
                "candidate_id": "contract-eager-skill-entry-prompts",
                "candidate_type": "collapse_adapter",
                "proof_status": "safe_by_equivalence",
                "target_action": "collapse",
                "compatibility_disposition": "direct_current_replacement",
            }
        )
    path.write_text(stable_json(mesh), encoding="utf-8")


def _append_missing(values: list[str], required: tuple[str, ...]) -> None:
    for value in required:
        if value not in values:
            values.append(value)


def _update_model_regression_manifest(
    toolchain_identity: Mapping[str, str],
) -> None:
    manifest = json.loads(
        MODEL_REGRESSION_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    governed = manifest.get("governed_input_globs")
    if not isinstance(governed, list):
        raise ValueError("model regression governed_input_globs must be a list")
    _append_missing(governed, ENTRY_SHARED_GOVERNED_INPUTS)

    models = manifest.get("models")
    if not isinstance(models, list):
        raise ValueError("model regression models must be a list")
    for entry in models:
        if not isinstance(entry, dict):
            raise ValueError("model regression entries must be objects")
        model_id = str(entry["model_id"])
        if model_id == "task_local_model_deepening":
            input_globs = entry.get("input_globs")
            if not isinstance(input_globs, list):
                raise ValueError(f"{model_id}: input_globs must be a list")
            _append_missing(input_globs, ENTRY_SHARED_GOVERNED_INPUTS)

        purpose = entry.get("purpose_closure")
        if not isinstance(purpose, dict):
            raise ValueError(f"{model_id}: purpose_closure must be an object")
        runner = entry.get("runner")
        if not isinstance(runner, list) or len(runner) < 2:
            raise ValueError(f"{model_id}: runner must name the native script")
        closure = build_model_purpose_closure(
            model_instance_id=(
                f"regression:{model_id}:{toolchain_identity['physicsguard_version']}"
            ),
            reusable_model_type_id=str(purpose["reusable_model_type_id"]),
            task_intent_id=str(purpose["task_intent_id"]),
            guarded_purpose=str(purpose["guarded_purpose"]),
            protected_failure_ids=tuple(
                map(str, purpose["protected_failure_ids"])
            ),
            known_good_case_id=str(purpose["known_good_case_id"]),
            failure_bindings=tuple(purpose["failure_bindings"]),
            claim_boundary=str(purpose["claim_boundary"]),
            evidence_check_ids=tuple(map(str, purpose["evidence_check_ids"])),
            model_sha256=file_fingerprint(ROOT / str(entry["model_path"])),
            runner_sha256=file_fingerprint(ROOT / str(runner[1])),
        )
        entry["purpose_closure"] = closure.to_dict()

    MODEL_REGRESSION_MANIFEST_PATH.write_text(
        stable_json(manifest), encoding="utf-8"
    )


def _content_role_overrides(skill_id: str) -> list[dict[str, str]]:
    return [
        {
            "path": f"skill/{skill_id}/.skillguard",
            "role": "contract_schema",
            "install_disposition": "source_only",
            "reason": "author_control_source_only",
        },
        {
            "path": f"skill/{skill_id}/guard-model",
            "role": "test_dev",
            "install_disposition": "source_only",
            "reason": "author_only_guard_contract",
        }
    ]


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


def _write_runtime_requirement(
    skill_root: Path,
    skill_id: str,
    toolchain_identity: Mapping[str, str],
) -> None:
    requirement = {
        "schema_version": RUNTIME_REQUIREMENT_SCHEMA,
        "target_skill_id": skill_id,
        "package_name": "physicsguard",
        "package_version": toolchain_identity["physicsguard_version"],
        "toolchain_identity": dict(toolchain_identity),
        "entrypoints": [
            "physicsguard.cli",
            "physicsguard.guard_model_contract",
            "physicsguard.skill_execution_depth",
        ],
        "missing_dependency_behavior": "fail_visible",
        "fallback": False,
        "claim_boundary": (
            "This declares only the shared simulator required to execute the skill. "
            "It does not prove a domain check ran or authorize a result."
        ),
    }
    (skill_root / "runtime-requirements.json").write_text(
        stable_json(requirement), encoding="utf-8"
    )


def _remove_copied_runtime(skill_root: Path) -> None:
    copied_verifier = skill_root / "guard-model" / "verify.py"
    if copied_verifier.exists():
        copied_verifier.unlink()
    runtime_root = skill_root / "runtime"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)


def upgrade_target_current(
    skill_id: str,
    config: dict[str, Any],
    toolchain_identity: Mapping[str, str],
) -> None:
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
    _remove_copied_runtime(skill_root)
    _write_runtime_requirement(skill_root, skill_id, toolchain_identity)

    export = _flowguard_export(
        skill_id, owner, route, guard_contract, toolchain_identity
    )
    model_path = skill_root / ".skillguard" / "contract_model.py"
    model_path.write_text(_model_source(export), encoding="utf-8")

    contract_obligation = f"obligation:{skill_id}:family-baseline-contract"
    candidate_obligation = f"obligation:{skill_id}:family-baseline-candidate-bound"
    good_obligation = f"obligation:{skill_id}:family-baseline-good"
    contract_check = f"check:{skill_id}:family-baseline-contract"
    candidate_check = f"check:{skill_id}:family-baseline-candidate"
    good_check = f"check:{skill_id}:family-baseline-good"
    task_model_obligation = f"obligation:{skill_id}:task-local-model-deepening"
    task_model_check = f"check:{skill_id}:task-local-model-deepening"
    task_model_pytest_id = skill_id.replace("-", "_")
    route_blueprint_inputs = BLUEPRINT_ROUTE_INPUTS.get(skill_id, ())
    route_blueprint_pytest_inputs = tuple(
        path
        for path in route_blueprint_inputs
        if path.startswith("tests/") and path.endswith(".py")
    )
    task_model_pytest_expression = " or ".join(
        (
            "test_task_local_revision",
            task_model_pytest_id,
            *(Path(path).stem for path in route_blueprint_pytest_inputs),
        )
    )
    owns_family_maintenance = skill_id == FAMILY_MAINTENANCE_MEMBER_ID
    repository_prefix = f"skill/{skill_id}"
    contract_selectors = [
        {"kind": "path", "path": f"{repository_prefix}/guard-model/contract.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/oracles.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/known-good.json"},
        {"kind": "path", "path": f"{repository_prefix}/guard-model/known-bad.json"},
        {"kind": "path", "path": f"{repository_prefix}/runtime-requirements.json"},
        *({"kind": "path", "path": path} for path in CANONICAL_RUNTIME_INPUTS),
        *({"kind": "path", "path": path} for path in BLUEPRINT_RUNTIME_INPUTS),
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
            "args": [
                "-m",
                "physicsguard.guard_model_contract",
                "check-baseline-contract",
                "--skill-root",
                repository_prefix,
            ],
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
            "args": [
                "-m",
                "physicsguard.guard_model_contract",
                "check-baseline-candidate",
                "--skill-root",
                repository_prefix,
            ],
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
            "args": [
                "-m",
                "physicsguard.guard_model_contract",
                "prove-baseline-good",
                "--skill-root",
                repository_prefix,
            ],
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
                "args": [
                    "-m",
                    "physicsguard.guard_model_contract",
                    "prove-baseline-bad",
                    "--skill-root",
                    repository_prefix,
                    "--failure-id",
                    failure_id,
                ],
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
    checks.append(
        {
            "check_id": task_model_check,
            "semantic_check_id": f"semantic:{skill_id}:task-local-model-deepening",
            "kind": "command",
            "command": "python",
            "args": [
                "-m",
                "pytest",
                "tests/test_task_local_revision.py",
                "tests/test_physicsguard_skill_prompts.py",
                "tests/test_physicsguard_skill_entry_loading.py",
                "tests/test_skill_execution_depth.py",
                "tests/test_physicsguard_skill_blueprint_contracts.py",
                *route_blueprint_pytest_inputs,
                "-q",
                "-k",
                task_model_pytest_expression,
            ],
            "cwd_token": "target_root",
            "expected": {"exit_code": 0},
            "timeout_seconds": 240,
            "evidence_class": "hard",
            "evidence_domain_id": f"{skill_id}:task-local-model-deepening",
            "execution_owner_id": f"owner:{skill_id}:task-local-model-deepening",
            "covers_obligation_ids": [task_model_obligation],
            "depends_on_check_ids": [good_check],
            "input_selectors": [
                {"kind": "path", "path": f"{repository_prefix}/SKILL.md"},
                {"kind": "path", "path": f"{repository_prefix}/agents/openai.yaml"},
                {"kind": "path", "path": f"{repository_prefix}/{ROUTE_CAPSULE_REFERENCE}"},
                {"kind": "path", "path": f"{repository_prefix}/{NATIVE_ROUTE_REFERENCE}"},
                {"kind": "path", "path": f"{repository_prefix}/{NATIVE_DEPTH_REFERENCE}"},
                {"kind": "path", "path": f"{repository_prefix}/{TEMPLATE_PACK_REFERENCE}"},
                {"kind": "path", "path": f"{repository_prefix}/.skillguard/contract-source.json"},
                *(
                    {"kind": "path", "path": path}
                    for path in ENTRY_SHARED_GOVERNED_INPUTS
                ),
                {"kind": "path", "path": "src/physicsguard/schema/task_local_revision.py"},
                {"kind": "path", "path": "src/physicsguard/core/task_local_revision.py"},
                {"kind": "path", "path": "src/physicsguard/cli.py"},
                {"kind": "path", "path": "tests/test_task_local_revision.py"},
                {"kind": "path", "path": "tests/test_physicsguard_skill_prompts.py"},
                {"kind": "path", "path": "tests/test_physicsguard_skill_entry_loading.py"},
                *(
                    {"kind": "path", "path": path}
                    for path in BLUEPRINT_RUNTIME_INPUTS
                ),
                *(
                    {"kind": "path", "path": path}
                    for path in BLUEPRINT_TEST_INPUTS
                ),
                *(
                    {"kind": "path", "path": path}
                    for path in route_blueprint_inputs
                ),
            ],
        }
    )
    if owns_family_maintenance:
        checks.append(
            {
                "check_id": FAMILY_MAINTENANCE_CHECK_ID,
                "semantic_check_id": (
                    "semantic:physicsguard-family:distribution-authority"
                ),
                "kind": "command",
                "command": "python",
                "args": [
                    "-m",
                    "pytest",
                    "tests/test_physicsguard_family_maintenance.py",
                    "tests/test_physicsguard_skill_install_authority.py",
                    "tests/test_install_physicsguard_skills.py",
                    "tests/test_installed_skill_sync.py",
                    "tests/test_guard_skill_mesh.py",
                    "tests/test_post_archive_retirement_authority.py",
                    "tests/test_skillguard_v2_runtime_authority_audit.py::test_readiness_declares_the_generator_frozen_toolchain_identity",
                    "tests/test_skillguard_v2_runtime_authority_audit.py::test_readiness_accepts_the_complete_generator_identity_schema",
                    "tests/test_skillguard_v2_runtime_authority_audit.py::test_readiness_rejects_missing_or_unknown_identity_fields",
                    "tests/test_skillguard_v2_runtime_authority_audit.py::test_readiness_blocks_project_import_drift_without_fallback",
                    "tests/test_skillguard_v2_runtime_authority_audit.py::test_readiness_package_exception_is_one_canonical_blocked_result",
                    "tests/test_skillguard_v2_runtime_authority_audit.py::test_readiness_shared_audit_exception_is_one_canonical_blocked_result",
                    "tests/test_version_consistency.py",
                    "-q",
                ],
                "cwd_token": "target_root",
                "expected": {"exit_code": 0},
                "timeout_seconds": 600,
                "evidence_class": "hard",
                "evidence_domain_id": (
                    "physicsguard-family:distribution-authority"
                ),
                "execution_owner_id": FAMILY_MAINTENANCE_OWNER_ID,
                "covers_obligation_ids": [FAMILY_MAINTENANCE_OBLIGATION_ID],
                "depends_on_check_ids": [],
                "input_selectors": [
                    {"kind": "path", "path": path}
                    for path in FAMILY_MAINTENANCE_INPUTS
                ],
                "coverage_rationale": (
                    "One family process owner proves current generator authority, "
                    "atomic staged contract generation, exact-ten prepare/verify/activate "
                    "and reverse rollback, read-only installed currentness, readiness "
                    "failure projection, source-only author controls, and the single "
                    "unit TestMesh topology without duplicating PhysicsGuard domain owners."
                ),
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
        task_model_obligation,
        *([FAMILY_MAINTENANCE_OBLIGATION_ID] if owns_family_maintenance else []),
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
                "evidence_source": (
                    "physicsguard.family_distribution_authority"
                    if str(check["check_id"]) == FAMILY_MAINTENANCE_CHECK_ID
                    else (
                        "physicsguard.task_local_revision"
                        if str(check["check_id"]) == task_model_check
                        else "physicsguard.guard_model_contract"
                    )
                ),
                "native_check_id": str(check["check_id"]),
                "required": True,
            }
            for check in checks
        ],
        "depth_profile": {
            "schema_version": "skillguard.depth_profile.v2",
            "profile_id": f"profile:{skill_id}:current-closure",
            "target_skill_id": skill_id,
            "integration_mode": "native-integrated",
            "native_owner_id": owner,
            "native_route_ids": [route],
            "native_check_ids": check_ids,
            "model_deepening_check_id": task_model_check,
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
            {
                "step_id": f"step:{skill_id}:task-local-model-deepening",
                "check_ids": [task_model_check],
                "output_artifact_ids": [],
                "action": {
                    "kind": "native",
                    "summary": "Execute the target-declared strict task-local model-deepening closure checks.",
                },
            },
            *(
                [
                    {
                        "step_id": (
                            "step:physicsguard-family:distribution-authority"
                        ),
                        "check_ids": [FAMILY_MAINTENANCE_CHECK_ID],
                        "output_artifact_ids": [],
                        "action": {
                            "kind": "development_process",
                            "summary": (
                                "Execute the sole family-level generation, "
                                "distribution, installation, and readiness boundary."
                            ),
                        },
                    }
                ]
                if owns_family_maintenance
                else []
            ),
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

    _write_entry_projection(
        skill_id,
        config,
        ROUTE_ENTRIES[skill_id],
        guard_contract,
        obligations,
        toolchain_identity,
    )

    source_contract["implementation_paths"] = sorted(
        {
            *_implementation_paths(skill_root),
            *CANONICAL_RUNTIME_INPUTS,
            *BLUEPRINT_RUNTIME_INPUTS,
            *BLUEPRINT_TEST_INPUTS,
            *route_blueprint_inputs,
            *ENTRY_GOVERNED_IMPLEMENTATION_PATHS,
            *(
                FAMILY_MAINTENANCE_INPUTS
                if owns_family_maintenance
                else ()
            ),
        }
    )
    source_contract["projection_consumers"] = (
        [
            {
                "consumer_id": FAMILY_MAINTENANCE_PROJECTION_ID,
                "kind": "source_maintenance",
                "input_selectors": [
                    {"kind": "path", "path": path}
                    for path in FAMILY_MAINTENANCE_INPUTS
                ],
            }
        ]
        if owns_family_maintenance
        else []
    )
    source_path.write_text(stable_json(source_contract), encoding="utf-8")


@contextmanager
def _repository_generation_context(repository_root: Path) -> Iterator[None]:
    """Point every generator-owned repository path at one staging checkout."""

    global ROOT
    global SKILL_ROOT
    global FLOWGUARD_PROJECT_PATH
    global CANONICAL_SATELLITE
    global PRIMARY_RUNTIME
    global PROMPT_LOAD_GRAPH_PATH
    global MODEL_REGRESSION_MANIFEST_PATH
    global UNIT_TEST_MESH_PATH

    previous = (
        ROOT,
        SKILL_ROOT,
        FLOWGUARD_PROJECT_PATH,
        CANONICAL_SATELLITE,
        PRIMARY_RUNTIME,
        PROMPT_LOAD_GRAPH_PATH,
        MODEL_REGRESSION_MANIFEST_PATH,
        UNIT_TEST_MESH_PATH,
    )
    root = Path(repository_root).resolve(strict=True)
    ROOT = root
    SKILL_ROOT = root / "skill"
    FLOWGUARD_PROJECT_PATH = root / ".flowguard" / "project.toml"
    CANONICAL_SATELLITE = (
        SKILL_ROOT / "physicsguard-ai-debugging" / ".skillguard" / "runtime"
    )
    PRIMARY_RUNTIME = (
        SKILL_ROOT
        / "physicsguard-model-dataset-validation"
        / ".skillguard"
        / "runtime"
        / "physicsguard"
    )
    PROMPT_LOAD_GRAPH_PATH = (
        root / ".flowguard" / "physicsguard_skill_prompt_load_graph.json"
    )
    MODEL_REGRESSION_MANIFEST_PATH = (
        root / ".flowguard" / "model-regression-manifest.json"
    )
    UNIT_TEST_MESH_PATH = root / ".skillguard" / "test-mesh.json"
    try:
        yield
    finally:
        (
            ROOT,
            SKILL_ROOT,
            FLOWGUARD_PROJECT_PATH,
            CANONICAL_SATELLITE,
            PRIMARY_RUNTIME,
            PROMPT_LOAD_GRAPH_PATH,
            MODEL_REGRESSION_MANIFEST_PATH,
            UNIT_TEST_MESH_PATH,
        ) = previous


def _managed_output_exact_paths() -> frozenset[str]:
    shared = {
        ".flowguard/model-regression-manifest.json",
        ".flowguard/physicsguard_skill_prompt_load_graph.json",
        ".flowguard/physicsguard_skill_suite_mesh.json",
        ".skillguard/test-mesh.json",
    }
    member_paths: set[str] = set()
    for skill_id in TARGETS:
        prefix = f"skill/{skill_id}"
        member_paths.update(
            {
                f"{prefix}/.skillguard/contract-source.json",
                f"{prefix}/.skillguard/contract_model.py",
                f"{prefix}/SKILL.md",
                f"{prefix}/agents/openai.yaml",
                f"{prefix}/guard-model/candidate.json",
                f"{prefix}/guard-model/contract.json",
                f"{prefix}/guard-model/known-bad.json",
                f"{prefix}/guard-model/known-good.json",
                f"{prefix}/guard-model/oracles.json",
                f"{prefix}/guard-model/verify.py",
                f"{prefix}/references/native-depth-and-purpose.md",
                f"{prefix}/references/route-capsule.json",
                f"{prefix}/references/template-pack-routing.md",
                f"{prefix}/runtime-requirements.json",
            }
        )
    return frozenset(shared | member_paths)


def _managed_output_prefixes() -> tuple[str, ...]:
    return tuple(f"skill/{skill_id}/runtime/" for skill_id in sorted(TARGETS))


def _is_managed_output(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    return normalized in _managed_output_exact_paths() or normalized.startswith(
        _managed_output_prefixes()
    )


def _required_generated_output_paths() -> frozenset[str]:
    return frozenset(
        path
        for path in _managed_output_exact_paths()
        if not path.endswith("/guard-model/verify.py")
    )


def _stage_copy_ignore(source_root: Path):
    source = Path(source_root).resolve(strict=True)

    def ignore(directory: str, names: list[str]) -> set[str]:
        current = Path(directory).resolve(strict=True)
        try:
            relative = current.relative_to(source).as_posix()
        except ValueError:
            relative = ""
        ignored = {
            name
            for name in names
            if name in {".git", ".pytest_cache", "__pycache__", "work"}
            or name.endswith((".pyc", ".pyo"))
        }
        if relative == ".flowguard" and "evidence" in names:
            ignored.add("evidence")
        if current.name == ".skillguard" and "runs" in names:
            ignored.add("runs")
        return ignored

    return ignore


def _repository_byte_manifest(repository_root: Path) -> dict[str, str]:
    root = Path(repository_root).resolve(strict=True)
    manifest: dict[str, str] = {}
    for current_text, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(current_text)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            path = current / name
            # The transaction stages from a source snapshot while other
            # maintenance workers may create/remove ephemeral work trees.
            # These directories are deliberately excluded from the staged
            # source manifest, so they must not participate in the commit
            # race either.
            if name in {"__pycache__", "work"}:
                continue
            if path.is_symlink():
                manifest[path.relative_to(root).as_posix() + "/"] = (
                    "symlink:" + os.readlink(path)
                )
                continue
            kept_directories.append(name)
        directory_names[:] = kept_directories
        for name in sorted(file_names):
            path = current / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                manifest[relative] = "symlink:" + os.readlink(path)
            else:
                manifest[relative] = _sha256_bytes(path.read_bytes())
    return manifest


def _changed_manifest_paths(
    before: Mapping[str, str], after: Mapping[str, str]
) -> frozenset[str]:
    return frozenset(
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )


def _contract_model_export(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "EXPORT"
            for target in node.targets
        ):
            continue
        call = node.value
        if (
            not isinstance(call, ast.Call)
            or not isinstance(call.func, ast.Attribute)
            or not isinstance(call.func.value, ast.Name)
            or call.func.value.id != "json"
            or call.func.attr != "loads"
            or len(call.args) != 1
            or not isinstance(call.args[0], ast.Constant)
            or not isinstance(call.args[0].value, str)
        ):
            break
        value = json.loads(call.args[0].value)
        if isinstance(value, dict):
            return value
        break
    raise ValueError(f"generated_contract_model_export_invalid:{path}")


def _validate_staged_generation(
    staging_root: Path,
    *,
    toolchain_identity: Mapping[str, str],
    before: Mapping[str, str],
    after: Mapping[str, str],
) -> frozenset[str]:
    changed = _changed_manifest_paths(before, after)
    unexpected = sorted(path for path in changed if not _is_managed_output(path))
    if unexpected:
        raise RuntimeError(f"generator_unmanaged_stage_writes:{unexpected}")
    missing = sorted(
        path
        for path in _required_generated_output_paths()
        if not (staging_root / path).is_file()
    )
    if missing:
        raise RuntimeError(f"generator_required_outputs_missing:{missing}")

    expected_identity = dict(toolchain_identity)
    graph = json.loads(
        (staging_root / ".flowguard/physicsguard_skill_prompt_load_graph.json").read_text(
            encoding="utf-8"
        )
    )
    mesh = json.loads(
        (staging_root / ".flowguard/physicsguard_skill_suite_mesh.json").read_text(
            encoding="utf-8"
        )
    )
    if graph.get("toolchain_identity") != expected_identity:
        raise RuntimeError("generator_prompt_graph_toolchain_identity_mismatch")
    if mesh.get("toolchain_identity") != expected_identity:
        raise RuntimeError("generator_suite_mesh_toolchain_identity_mismatch")
    expected_version = expected_identity["physicsguard_version"]
    if graph.get("suite_version") != expected_version:
        raise RuntimeError("generator_prompt_graph_physicsguard_version_mismatch")
    if (
        (mesh.get("canonical_simulator") or {}).get("consumer_dependency")
        != f"physicsguard=={expected_version}"
    ):
        raise RuntimeError("generator_suite_mesh_physicsguard_version_mismatch")

    for skill_id in sorted(TARGETS):
        skill_root = staging_root / "skill" / skill_id
        requirement = json.loads(
            (skill_root / "runtime-requirements.json").read_text(encoding="utf-8")
        )
        if requirement.get("package_version") != expected_version:
            raise RuntimeError(
                f"generator_runtime_requirement_version_mismatch:{skill_id}"
            )
        if requirement.get("toolchain_identity") != expected_identity:
            raise RuntimeError(
                f"generator_runtime_requirement_toolchain_identity_mismatch:{skill_id}"
            )
        export = _contract_model_export(
            skill_root / ".skillguard" / "contract_model.py"
        )
        if export.get("toolchain_identity") != expected_identity:
            raise RuntimeError(
                f"generator_contract_model_toolchain_identity_mismatch:{skill_id}"
            )
        if (
            export.get("flowguard_schema_version")
            != expected_identity["flowguard_schema_version"]
        ):
            raise RuntimeError(
                f"generator_contract_model_flowguard_schema_mismatch:{skill_id}"
            )
    return changed


def _managed_byte_snapshot(repository_root: Path) -> dict[str, bytes]:
    root = Path(repository_root).resolve(strict=True)
    snapshot: dict[str, bytes] = {}
    for relative in _repository_byte_manifest(root):
        if not _is_managed_output(relative):
            continue
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"generator_managed_output_unsafe:{relative}")
        snapshot[relative] = path.read_bytes()
    return snapshot


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_text = tempfile.mkstemp(
        prefix=f".{path.name}.physicsguard-stage-", dir=str(path.parent)
    )
    temporary = Path(temporary_text)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _restore_managed_snapshot(
    repository_root: Path, snapshot: Mapping[str, bytes]
) -> None:
    root = Path(repository_root).resolve(strict=True)
    current_paths = {
        relative
        for relative in _repository_byte_manifest(root)
        if _is_managed_output(relative)
    }
    for relative in sorted(current_paths - set(snapshot), reverse=True):
        path = root / relative
        if path.is_file() or path.is_symlink():
            path.unlink()
    for relative, payload in sorted(snapshot.items()):
        _atomic_write_bytes(root / relative, payload)
    for prefix in _managed_output_prefixes():
        path = root / prefix.rstrip("/")
        if path.exists() and not any(path.rglob("*")):
            path.rmdir()


def _commit_staged_generation(
    repository_root: Path,
    staging_root: Path,
    *,
    baseline_manifest: Mapping[str, str],
    changed_paths: frozenset[str],
) -> None:
    root = Path(repository_root).resolve(strict=True)
    stage = Path(staging_root).resolve(strict=True)
    baseline_managed = {
        path: digest
        for path, digest in baseline_manifest.items()
        if _is_managed_output(path)
    }
    current_manifest = _repository_byte_manifest(root)
    current_managed = {
        path: digest
        for path, digest in current_manifest.items()
        if _is_managed_output(path)
    }
    if current_managed != baseline_managed:
        raise RuntimeError("generator_managed_outputs_changed_during_stage")

    snapshot = _managed_byte_snapshot(root)
    try:
        for relative in sorted(changed_paths):
            if not _is_managed_output(relative):
                raise RuntimeError(f"generator_commit_path_not_managed:{relative}")
            source = stage / relative
            target = root / relative
            if source.is_file() and not source.is_symlink():
                _atomic_write_bytes(target, source.read_bytes())
            elif source.exists():
                raise RuntimeError(f"generator_staged_output_unsafe:{relative}")
            elif target.is_file() or target.is_symlink():
                target.unlink()
        for prefix in _managed_output_prefixes():
            staged_prefix = stage / prefix.rstrip("/")
            target_prefix = root / prefix.rstrip("/")
            if not staged_prefix.exists() and target_prefix.exists():
                shutil.rmtree(target_prefix)
    except BaseException as exc:
        try:
            _restore_managed_snapshot(root, snapshot)
        except BaseException as rollback_exc:
            raise RuntimeError(
                "generator_commit_failed_and_rollback_failed:"
                f"commit={type(exc).__name__}:{exc}:"
                f"rollback={type(rollback_exc).__name__}:{rollback_exc}"
            ) from rollback_exc
        raise


def _generate_all(toolchain_identity: Mapping[str, str]) -> None:
    _write_unit_test_mesh_manifest()
    for skill_id in sorted(TARGETS):
        upgrade_target_current(skill_id, TARGETS[skill_id], toolchain_identity)
    _write_prompt_load_graph(toolchain_identity)
    _update_suite_mesh(toolchain_identity)
    _update_model_regression_manifest(toolchain_identity)


def _run_generation_transaction(
    repository_root: Path, toolchain_identity: Mapping[str, str]
) -> None:
    root = Path(repository_root).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="physicsguard-purpose-generator-", dir=str(root.parent)
    ) as temporary_root_text:
        staging_root = Path(temporary_root_text) / "repository"
        shutil.copytree(
            root,
            staging_root,
            symlinks=True,
            ignore=_stage_copy_ignore(root),
        )
        before = _repository_byte_manifest(staging_root)
        with _repository_generation_context(staging_root):
            _generate_all(toolchain_identity)
        after = _repository_byte_manifest(staging_root)
        changed = _validate_staged_generation(
            staging_root,
            toolchain_identity=toolchain_identity,
            before=before,
            after=after,
        )
        _commit_staged_generation(
            root,
            staging_root,
            baseline_manifest=before,
            changed_paths=changed,
        )


def main(
    repository_root: Path | None = None,
    argv: list[str] | None = None,
) -> int:
    if argv is not None:
        parser = argparse.ArgumentParser(
            description=(
                "Regenerate all PhysicsGuard maintained-skill artifacts in one "
                "authority-frozen staging transaction."
            )
        )
        parser.add_argument(
            "--repository-root",
            type=Path,
            help="PhysicsGuard repository root (defaults to this script's repository).",
        )
        parsed = parser.parse_args(argv)
        if repository_root is not None and parsed.repository_root is not None:
            parser.error("repository_root was supplied twice")
        if parsed.repository_root is not None:
            repository_root = parsed.repository_root
    repository = Path(repository_root if repository_root is not None else ROOT).resolve(
        strict=True
    )
    skill_root = repository / "skill"
    discovered = {
        path.parent.parent.name
        for path in skill_root.glob("physicsguard*/.skillguard/contract-source.json")
    }
    if discovered != set(TARGETS):
        raise SystemExit(
            f"PhysicsGuard target inventory mismatch: missing={sorted(discovered - set(TARGETS))}; extra={sorted(set(TARGETS) - discovered)}"
        )
    if set(ROUTE_ENTRIES) != set(TARGETS):
        raise SystemExit(
            "PhysicsGuard route-entry inventory mismatch: "
            f"missing={sorted(set(TARGETS) - set(ROUTE_ENTRIES))}; "
            f"extra={sorted(set(ROUTE_ENTRIES) - set(TARGETS))}"
        )
    if set(OPENAI_DEFAULT_PROMPTS) != set(TARGETS):
        raise SystemExit(
            "PhysicsGuard OpenAI prompt inventory mismatch: "
            f"missing={sorted(set(TARGETS) - set(OPENAI_DEFAULT_PROMPTS))}; "
            f"extra={sorted(set(OPENAI_DEFAULT_PROMPTS) - set(TARGETS))}"
        )
    if set(BLUEPRINT_ROUTE_GUARD_CONTRACTS) != set(TARGETS):
        raise SystemExit(
            "PhysicsGuard blueprint guard-contract inventory mismatch: "
            f"missing={sorted(set(TARGETS) - set(BLUEPRINT_ROUTE_GUARD_CONTRACTS))}; "
            f"extra={sorted(set(BLUEPRINT_ROUTE_GUARD_CONTRACTS) - set(TARGETS))}"
        )
    toolchain_identity = current_toolchain_identity(
        repository_root=repository,
        flowguard_project_path=repository / ".flowguard" / "project.toml",
        skillguard_root=DEFAULT_SKILLGUARD_ROOT,
    )
    _run_generation_transaction(repository, toolchain_identity)
    print(stable_json({"status": "pass", "updated_targets": sorted(TARGETS)}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
