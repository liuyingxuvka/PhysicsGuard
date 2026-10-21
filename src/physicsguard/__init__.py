"""PhysicsGuard Core framework package, with public APIs loaded on demand."""
from __future__ import annotations

import importlib
from typing import Any

__version__ = "0.15.15"

__all__ = [
    "BOUND_HIT_TOLERANCE",
    "BugFamilyFollowUp",
    "BoundHitDiagnostic",
    "DiagnosticReport",
    "DiagnosticReporter",
    "ResidualDiagnostic",
    "SignalMappingRecord",
    "TargetInventoryAuthority",
    "build_signal_mapping_ledger",
    # These are bounded in-memory projections for domain review only. Disk
    # materialization/loading is retired by the native-directory boundary.
    "build_physical_blueprint_export_bundle",
    "affected_physical_blueprint_projection",
    "build_project_evidence_map",
    "check_test_file_contract",
    "check_test_file_parameter_coverage",
    "check_test_file_project_index",
    "check_logical_dataset_record",
    "check_model_library_index",
    "check_evidence_bundle",
    "check_evidence_gaps",
    "check_evidence_mesh",
    "check_project_evidence_registry",
    "check_test_file_relation_index",
    "derive_bug_family_followups",
    "field_signature_hash",
    "full_physical_blueprint_projection",
    "generate_delimited_manifest",
    "mapping_warnings",
    "review_signal_mapping_ledger",
    "PhysicalModelBlueprint",
    "PhysicalModelBlueprintReview",
    "sha256_file",
    "scan_project_evidence_candidates",
    "review_project_profile_authority",
    "validate_model_dataset",
    "evaluate_candidate_model_revision",
    "evaluate_hypothesis_observation",
    "evaluate_diagnosability",
    "evaluate_interval_residual",
    "freeze_hypothesis_plan",
    "rank_observation_candidates",
    "reverse_trace_physical_blueprint_projection",
    "review_physical_model_blueprint",
    "summary_physical_blueprint_projection",
    "query_physical_blueprint_export_bundle",
]

_PUBLIC_EXPORTS = {
    'BOUND_HIT_TOLERANCE': 'physicsguard.core.model_dataset_validation',
    'BugFamilyFollowUp': 'physicsguard.core.signal_mapping',
    'BoundHitDiagnostic': 'physicsguard.core.diagnostics',
    'DiagnosticReport': 'physicsguard.core.diagnostics',
    'DiagnosticReporter': 'physicsguard.core.diagnostics',
    'ResidualDiagnostic': 'physicsguard.core.diagnostics',
    'SignalMappingRecord': 'physicsguard.core.signal_mapping',
    'TargetInventoryAuthority': 'physicsguard.schema.physical_model_blueprint',
    'build_signal_mapping_ledger': 'physicsguard.core.signal_mapping',
    'build_physical_blueprint_export_bundle': 'physicsguard.core.physical_blueprint_bundle',
    'affected_physical_blueprint_projection': 'physicsguard.core.physical_blueprint_trace',
    'build_project_evidence_map': 'physicsguard.core.project_evidence',
    'check_test_file_contract': 'physicsguard.core.test_file_contract',
    'check_test_file_parameter_coverage': 'physicsguard.core.test_file_contract',
    'check_test_file_project_index': 'physicsguard.core.test_file_contract',
    'check_logical_dataset_record': 'physicsguard.core.dataset_identity',
    'check_model_library_index': 'physicsguard.core.model_library',
    'check_evidence_bundle': 'physicsguard.core.project_evidence',
    'check_evidence_gaps': 'physicsguard.core.project_evidence',
    'check_evidence_mesh': 'physicsguard.core.evidence_mesh',
    'check_project_evidence_registry': 'physicsguard.core.project_evidence',
    'check_test_file_relation_index': 'physicsguard.core.dataset_identity',
    'derive_bug_family_followups': 'physicsguard.core.signal_mapping',
    'field_signature_hash': 'physicsguard.core.data_file_manifest',
    'full_physical_blueprint_projection': 'physicsguard.core.physical_blueprint_trace',
    'generate_delimited_manifest': 'physicsguard.core.data_file_manifest',
    'mapping_warnings': 'physicsguard.core.signal_mapping',
    'review_signal_mapping_ledger': 'physicsguard.core.signal_mapping',
    'PhysicalModelBlueprint': 'physicsguard.schema.physical_model_blueprint',
    'PhysicalModelBlueprintReview': 'physicsguard.schema.physical_model_blueprint',
    'sha256_file': 'physicsguard.core.data_file_manifest',
    'scan_project_evidence_candidates': 'physicsguard.core.project_evidence',
    'review_project_profile_authority': 'physicsguard.core.project_evidence',
    'validate_model_dataset': 'physicsguard.core.model_dataset_validation',
    'evaluate_candidate_model_revision': 'physicsguard.core.task_local_revision',
    'evaluate_hypothesis_observation': 'physicsguard.core.task_local_revision',
    'evaluate_diagnosability': 'physicsguard.core.diagnosability',
    'evaluate_interval_residual': 'physicsguard.core.diagnosability',
    'freeze_hypothesis_plan': 'physicsguard.core.task_local_revision',
    'rank_observation_candidates': 'physicsguard.core.task_local_revision',
    'reverse_trace_physical_blueprint_projection': 'physicsguard.core.physical_blueprint_trace',
    'review_physical_model_blueprint': 'physicsguard.core.physical_model_blueprint',
    'summary_physical_blueprint_projection': 'physicsguard.core.physical_blueprint_trace',
    'query_physical_blueprint_export_bundle': 'physicsguard.core.physical_blueprint_bundle',
}


def __getattr__(name: str) -> Any:
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module 'physicsguard' has no attribute {name!r}")
    module = (
        _load_diagnostics_module()
        if module_name == "physicsguard.core.diagnostics"
        else importlib.import_module(module_name)
    )
    value = getattr(module, name)
    globals()[name] = value
    return value


def _load_diagnostics_module() -> Any:
    # Use the canonical module registry so public diagnostic classes keep identity.
    return importlib.import_module("physicsguard.core.diagnostics")
