"""PhysicsGuard Core framework package."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

__version__ = "0.8.0"

from physicsguard.core.signal_mapping import (
    BugFamilyFollowUp,
    SignalMappingRecord,
    build_signal_mapping_ledger,
    derive_bug_family_followups,
    mapping_warnings,
)
from physicsguard.core.data_file_manifest import (
    field_signature_hash,
    generate_delimited_manifest,
    sha256_file,
)
from physicsguard.core.database_catalog import (
    admit_database_project,
    archive_database_project,
    audit_database_maintenance,
    build_database_map,
    check_database_catalog,
    check_database_catalog_gaps,
    check_database_model_template_index,
    check_database_policy,
    initialize_database_root,
    plan_database_project_intake,
    query_database_catalog,
    refresh_database_catalog,
    render_database_handoff,
    scan_database_catalog_candidates,
)
from physicsguard.core.test_file_contract import (
    check_test_file_contract,
    check_test_file_parameter_coverage,
    check_test_file_project_index,
)
from physicsguard.core.dataset_identity import check_logical_dataset_record, check_test_file_relation_index
from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.model_library import check_model_library_index
from physicsguard.core.project_closure import run_project_closure
from physicsguard.core.project_evidence import (
    build_project_evidence_map,
    check_evidence_bundle,
    check_evidence_gaps,
    check_project_evidence_registry,
    scan_project_evidence_candidates,
)

__all__ = [
    "BOUND_HIT_TOLERANCE",
    "BugFamilyFollowUp",
    "BoundHitDiagnostic",
    "DiagnosticReport",
    "DiagnosticReporter",
    "ResidualDiagnostic",
    "SignalMappingRecord",
    "admit_database_project",
    "archive_database_project",
    "audit_database_maintenance",
    "build_database_map",
    "build_signal_mapping_ledger",
    "build_project_evidence_map",
    "check_database_catalog",
    "check_database_catalog_gaps",
    "check_database_model_template_index",
    "check_database_policy",
    "check_test_file_contract",
    "check_test_file_parameter_coverage",
    "check_test_file_project_index",
    "check_logical_dataset_record",
    "check_model_library_index",
    "check_evidence_bundle",
    "check_evidence_gaps",
    "check_project_evidence_registry",
    "check_test_file_relation_index",
    "derive_bug_family_followups",
    "field_signature_hash",
    "generate_delimited_manifest",
    "mapping_warnings",
    "initialize_database_root",
    "plan_database_project_intake",
    "query_database_catalog",
    "refresh_database_catalog",
    "render_database_handoff",
    "run_project_closure",
    "sha256_file",
    "scan_database_catalog_candidates",
    "scan_project_evidence_candidates",
    "validate_model_dataset",
]

_DIAGNOSTIC_EXPORTS = set(__all__)


def __getattr__(name: str) -> Any:
    if name in _DIAGNOSTIC_EXPORTS:
        module = _load_diagnostics_module()
        return getattr(module, name)
    raise AttributeError(f"module 'physicsguard' has no attribute {name!r}")


def _load_diagnostics_module() -> Any:
    module_name = "_physicsguard_diagnostics_standalone"
    if module_name in sys.modules:
        return sys.modules[module_name]
    module_path = Path(__file__).with_name("core") / "diagnostics.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load diagnostics module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
