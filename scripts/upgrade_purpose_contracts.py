"""Generate the ten PhysicsGuard consumer skills from their native route table.

Generation needs Python and this source tree only. Domain execution remains in
PhysicsGuard; author contracts, supervisor receipts and old toolchains are not
consumer prerequisites. All outputs are staged before replacing source files.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NATIVE_ROUTE_REFERENCE = "references/native-route-protocol.md"
NATIVE_DEPTH_REFERENCE = "references/native-depth-and-purpose.md"
TEMPLATE_PACK_REFERENCE = "references/template-pack-routing.md"
ROUTE_CAPSULE_REFERENCE = "references/route-capsule.json"
ROUTE_CAPSULE_SCHEMA = "physicsguard.skill_route_capsule.v1"
PROMPT_LOAD_GRAPH_SCHEMA = "physicsguard.skill_prompt_load_graph.v1"
MAX_SKILL_ENTRY_BYTES = 6000
MAX_INITIAL_ROUTE_BYTES = 12000


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

TARGETS = {'physicsguard-ai-debugging': {'native_owner_id': 'physicsguard.ai-debugging', 'native_route_id': 'route:physicsguard-ai-debugging:audit', 'claim_boundary': 'This route can license only a low-fidelity, evidence-bounded fault localization. It does not prove high-fidelity model truth or behavior outside the checked operating envelope.'}, 'physicsguard-audit-closure': {'native_owner_id': 'physicsguard.audit-closure', 'native_route_id': 'route:physicsguard-audit-closure:close', 'claim_boundary': 'Closure proves only the exact requested audit scope represented by current native receipts; skipped, stale, partial, and predictive gaps remain non-pass.'}, 'physicsguard-candidate-model-blueprint': {'native_owner_id': 'physicsguard.candidate-model-blueprint', 'native_route_id': 'route:physicsguard-candidate-model-blueprint:build', 'claim_boundary': 'Generation eligibility covers only a candidate low-fidelity blueprint for the declared target and interfaces; it is not an implemented or validated high-fidelity model.'}, 'physicsguard-model-dataset-validation': {'native_owner_id': 'physicsguard-model-dataset-validation', 'native_route_id': 'route:physicsguard-model-dataset-validation', 'claim_boundary': 'A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.'}, 'physicsguard-model-library': {'native_owner_id': 'physicsguard.model-library', 'native_route_id': 'route:physicsguard-model-library:reuse', 'claim_boundary': 'Library readiness licenses only the selected asset/profile/testbench combination and exact bounded reuse scope; it does not validate a new project automatically.'}, 'physicsguard-model-understanding-preflight': {'native_owner_id': 'physicsguard.model-understanding-preflight', 'native_route_id': 'route:physicsguard-model-understanding-preflight:review', 'claim_boundary': 'Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.'}, 'physicsguard-project-adoption': {'native_owner_id': 'physicsguard.project-adoption', 'native_route_id': 'route:physicsguard-project-adoption:audit', 'claim_boundary': 'Adoption proves only current workflow records and toolchain/artifact readiness; it never substitutes for model execution, validation, closure, installation, or release evidence.'}, 'physicsguard-project-evidence-registry': {'native_owner_id': 'physicsguard.project-evidence-registry', 'native_route_id': 'route:physicsguard-project-evidence-registry:check', 'claim_boundary': 'Registry closure covers only the exact current project evidence bundle and declared roles/bindings; unresolved critical gaps or out-of-scope files remain blocking.'}, 'physicsguard-signal-mapping-review': {'native_owner_id': 'physicsguard.signal-mapping-review', 'native_route_id': 'route:physicsguard-signal-mapping-review:review', 'claim_boundary': 'A mapping pass licenses only the exact external signal, target variable, conversion, revision, temporal range, and reviewed confidence in the receipt.'}, 'physicsguard-test-file-contract-review': {'native_owner_id': 'physicsguard.test-file-contract-review', 'native_route_id': 'route:physicsguard-test-file-contract-review:check', 'claim_boundary': 'A pass covers only the exact test files, fields, units, timing, model/testbench versions, signal mappings, and depth represented in the receipt.'}}

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

def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"

def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

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

STRICT_TASK_PROTOCOL = '### Strict task-local model deepening\n\nThe selected native route keeps its physical/evidence judgment. The shared task-local schema and evaluator bind its model, observations, revisions and current evidence.\n\nFor every non-trivial task, use the existing `task-model plan -> observe -> revision` route with the strict current schema. The plan must declare a non-empty task purpose, an independently owned coverage-universe id and SHA-256, explicit assumptions and unknowns (empty is allowed only when written explicitly), iteration, an exact predecessor receipt after iteration zero, and a current `physicsguard_task_native_depth_receipt` bound to the plan model. Retired optional fields and compatibility shapes are invalid.\n\nThe native depth receipt must account for exactly six families: execution depth, mapping, residual, uncertainty, diagnosability, and predictive rollout. Open gaps, resolution classes, external input ids, and next actions come from that target-owned receipt; AI prose, `resolved=true`, caller-written gap lists, and self-reported understanding have no closure authority.\n\nFreeze the prediction before observation and bind the observation to the exact plan fingerprint, selected probe, producer, source, independence group, and evidence SHA-256. If the observation contradicts every declared hypothesis, return `model_miss` and revise the hypothesis/model universe; never select a physical cause by elimination outside the declared space.\n\nA candidate revision must preserve distinct base/candidate identities and consume base/candidate native-depth receipts plus exactly one typed regression receipt, one independent holdout receipt, and one predictive-rollout receipt. All three must bind the same task, plan, revision, coverage fingerprint, and candidate SHA-256; the holdout must be independent from candidate construction. PhysicsGuard derives resolved, persisted, and introduced gaps by comparing the two native receipts. Renaming or deleting a caller gap is not progress.\n\n`model_closed_for_task` is legal only when the candidate identity is current, every typed check passes, and the candidate native receipt has zero open gaps. Otherwise preserve the exact non-success boundary: `continue_iteration`, `external_input_required`, `progress_stalled`, `iteration_limit`, `scope_excluded`, or `model_miss`. A passing regression with any native gap is continuation, not closure.\n\nUse `python -m physicsguard.guard_model_contract check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.\n\n'

TEMPLATE_PROTOCOL = "# Validated Template Pack Routing\n\nLoad this reference only when the selected PhysicsGuard route needs target-owned template selection, preview, instantiation, validation, or harvest. A preview is planning evidence, never domain proof.\n\n- Target families: `physicsguard`; native owner: `physicsguard.purpose-pack-selector.v1`.\n- Current catalogs: `physicsguard.purpose-template-packs` revision `1`.\n- Resolve the task through this skill's native route first, then use `physicsguard.template_packs.select_templates` and `validate_selection` for the exact native request; never infer a template from wording or a skill name.\n- Preserve the selector's complete candidate and rejection accounting. Zero candidates may use only the declared validated base; one candidate gets a read-only preview; many candidates require complete dependencies, pairwise compatibility, one field owner, and target-authored dominance or must block as ambiguous.\n- Recompute the projection immediately before applying a preview. A stale request, catalog, route, builder, validator, or content identity blocks all writes.\n- Hand the selected preview to the target-declared builder and consume every target-native validator receipt. Template structure is not domain validity, completion, installation, release, or publication evidence.\n- Record a harvest disposition after creating or materially deepening a reusable model, and keep no-match evidence visible.\n- Declared validated bases: `physicsguard.base.audit-work-package`.\n- Template inventory: `physicsguard.base.audit-work-package`, `physicsguard.dataset-validation-basic`, `physicsguard.dataset-validation-comprehensive`, `physicsguard.model-understanding-preflight`, `physicsguard.signal-mapping-core`, `physicsguard.signal-mapping-evidence`.\n- Native validator inventory: `physicsguard.template-pack-instance-validator.v1`, `physicsguard.template-pack-manifest-validator.v1`, `physicsguard.template-pack-selection-validator.v1`.\n- Claim boundary: the catalog supports deterministic workflow-pack selection and structural native validation only; physical truth, dataset adequacy, `audit_pass`, installation, and release require separate current PhysicsGuard evidence.\n"

def current_toolchain_identity(*, repository_root: Path = ROOT) -> dict[str, str]:
    """Check the three local PhysicsGuard version sources; no other tool is loaded."""
    root = Path(repository_root)
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    source = ast.parse((root / "src/physicsguard/__init__.py").read_text(encoding="utf-8"))
    declared = [node.value.value for node in source.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
                and isinstance(node.value, ast.Constant)]
    if declared != [version] or (root / "VERSION").read_text().strip() != version:
        raise ValueError("physicsguard_version_authority_mismatch")
    return {"physicsguard_version": version}


def upgrade_target_current(skill_id: str, *, repository_root: Path, version: str) -> None:
    """Write one member into the transaction's staging directory."""
    member = repository_root / "skill" / skill_id
    entry, config = ROUTE_ENTRIES[skill_id], TARGETS[skill_id]
    refs = member / "references"
    if not (refs / "native-route-protocol.md").is_file():
        raise ValueError(f"native route protocol missing: {skill_id}")
    depth = ("# Native Depth and Purpose\n\n"
             "Load only for creating, materially deepening, revising or closing a task-local model. "
             "Ordinary bounded route execution does not load this reference.\n\n" + STRICT_TASK_PROTOCOL)
    (refs / "native-depth-and-purpose.md").write_text(depth.rstrip() + "\n", encoding="utf-8")
    (refs / "template-pack-routing.md").write_text(TEMPLATE_PROTOCOL, encoding="utf-8")
    prompt = _render_compact_skill(skill_id, entry, config)
    if len(prompt.encode()) > MAX_SKILL_ENTRY_BYTES:
        raise ValueError(f"compact skill too large: {skill_id}")
    (member / "SKILL.md").write_text(prompt, encoding="utf-8")
    (member / "agents").mkdir(exist_ok=True)
    (member / "agents/openai.yaml").write_text(_render_openai_yaml(skill_id, entry), encoding="utf-8")
    capsule = _route_capsule(member, skill_id, entry, config)
    (member / ROUTE_CAPSULE_REFERENCE).write_text(stable_json(capsule), encoding="utf-8")
    requirement = {"schema_version": "physicsguard.skill_runtime_requirement.v1", "target_skill_id": skill_id,
                   "package_name": "physicsguard", "package_version": version,
                   "entrypoints": ["physicsguard.cli", "physicsguard.guard_model_contract", "physicsguard.skill_execution_depth"],
                   "missing_dependency_behavior": "fail_visible", "fallback": False,
                   "claim_boundary": "This declares the domain runtime; it does not prove a domain check ran."}
    (member / "runtime-requirements.json").write_text(stable_json(requirement), encoding="utf-8")


MEMBER_OUTPUTS = ("SKILL.md", "agents/openai.yaml", NATIVE_DEPTH_REFERENCE,
                  TEMPLATE_PACK_REFERENCE, ROUTE_CAPSULE_REFERENCE, "runtime-requirements.json")
SHARED_OUTPUTS = (".flowguard/physicsguard_skill_prompt_load_graph.json", ".flowguard/physicsguard_skill_suite_mesh.json")


def _generate_all(root: Path, version: str) -> None:
    routes, nodes = [], []
    for skill_id in sorted(TARGETS):
        upgrade_target_current(skill_id, repository_root=root, version=version)
        member = root / "skill" / skill_id
        capsule = json.loads((member / ROUTE_CAPSULE_REFERENCE).read_text())
        initial = [f"skill/{skill_id}/{path}" for path in capsule["initial_load"]]
        size = sum((root / path).stat().st_size for path in initial)
        if size > MAX_INITIAL_ROUTE_BYTES:
            raise ValueError(f"initial route too large: {skill_id}")
        routes.append({"target_skill_id": skill_id, "native_owner_id": capsule["native_owner_id"],
                       "native_route_id": capsule["native_route_id"], "route_role": capsule["route_role"],
                       "broad_route_prerequisite": False, "initial_paths": initial, "initial_bytes": size,
                       "conditional_references": capsule["conditional_references"], "deep_capabilities": list(DEEP_CAPABILITIES)})
        for path in initial + [f"skill/{skill_id}/{row['path']}" for row in capsule["conditional_references"]]:
            nodes.append({"path": path, "skill_id": skill_id, "sha256": _file_sha256(root / path), "bytes": (root / path).stat().st_size})
    graph = {"schema_version": PROMPT_LOAD_GRAPH_SCHEMA, "suite_version": version, "route_count": len(routes),
             "initial_loading_rule": "selected_metadata_plus_compact_skill_plus_route_capsule_only",
             "cross_skill_loading_rule": "typed_handoff_only", "maximum_reference_depth": 1,
             "max_skill_entry_bytes": MAX_SKILL_ENTRY_BYTES, "max_initial_route_bytes": MAX_INITIAL_ROUTE_BYTES,
             "required_deep_capabilities": list(DEEP_CAPABILITIES), "nodes": nodes, "routes": routes,
             "claim_boundary": "Route identities and bounded reference loading only; no domain execution is inferred."}
    directory = root / ".flowguard"; directory.mkdir(exist_ok=True)
    (root / SHARED_OUTPUTS[0]).write_text(stable_json(graph), encoding="utf-8")
    mesh = {"schema_version": "physicsguard.skill_routes.v1", "version": version,
            "children": [{key: row[key] for key in ("target_skill_id", "native_owner_id", "native_route_id", "route_role")} for row in routes],
            "claim_boundary": "Ten native routes; this navigation list executes no checks and grants no domain pass."}
    (root / SHARED_OUTPUTS[1]).write_text(stable_json(mesh), encoding="utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".physicsguard-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _run_generation_transaction(root: Path, identity: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory(prefix="physicsguard-generate-") as temporary:
        staging = Path(temporary)
        shutil.copytree(root / "skill", staging / "skill", ignore=shutil.ignore_patterns(".skillguard", "guard-model", "__pycache__"))
        _generate_all(staging, identity["physicsguard_version"])
        paths = [f"skill/{skill}/{relative}" for skill in sorted(TARGETS) for relative in MEMBER_OUTPUTS] + list(SHARED_OUTPUTS)
        before = {path: (root / path).read_bytes() if (root / path).exists() else None for path in paths}
        try:
            for path in paths:
                _atomic_write(root / path, (staging / path).read_bytes())
        except Exception:
            for path, content in before.items():
                if content is None:
                    (root / path).unlink(missing_ok=True)
                else:
                    _atomic_write(root / path, content)
            raise


def main(repository_root: Path | None = None, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path)
    args = parser.parse_args(argv)
    root = Path(repository_root or args.repository_root or ROOT).resolve()
    discovered = {path.parent.name for path in (root / "skill").glob("physicsguard-*/SKILL.md")}
    if discovered != set(TARGETS):
        raise ValueError("PhysicsGuard ten-route inventory mismatch")
    identity = current_toolchain_identity(repository_root=root)
    _run_generation_transaction(root, identity)
    print(stable_json({"status": "pass", "updated_targets": sorted(TARGETS)}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=sys.argv[1:]))
