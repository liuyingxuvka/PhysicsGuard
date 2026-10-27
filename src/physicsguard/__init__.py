"""PhysicsGuard Core framework package, with public APIs loaded on demand."""
from __future__ import annotations

import importlib
from typing import Any

__version__ = "0.15.24"

__all__ = [
    "BOUND_HIT_TOLERANCE",
    "BugFamilyFollowUp",
    "BoundHitDiagnostic",
    "DiagnosticReport",
    "DiagnosticReporter",
    "ResidualDiagnostic",
    "SignalMappingRecord",
    "build_signal_mapping_ledger",
    "check_test_file_contract",
    "derive_bug_family_followups",
    "field_signature_hash",
    "generate_delimited_manifest",
    "mapping_warnings",
    "sha256_file",
    "validate_model_dataset",
]

_PUBLIC_EXPORTS = {
    'BOUND_HIT_TOLERANCE': 'physicsguard.core.model_dataset_validation',
    'BugFamilyFollowUp': 'physicsguard.core.signal_mapping',
    'BoundHitDiagnostic': 'physicsguard.core.diagnostics',
    'DiagnosticReport': 'physicsguard.core.diagnostics',
    'DiagnosticReporter': 'physicsguard.core.diagnostics',
    'ResidualDiagnostic': 'physicsguard.core.diagnostics',
    'SignalMappingRecord': 'physicsguard.core.signal_mapping',
    'build_signal_mapping_ledger': 'physicsguard.core.signal_mapping',
    'check_test_file_contract': 'physicsguard.core.test_file_contract',
    'derive_bug_family_followups': 'physicsguard.core.signal_mapping',
    'field_signature_hash': 'physicsguard.core.data_file_manifest',
    'generate_delimited_manifest': 'physicsguard.core.data_file_manifest',
    'mapping_warnings': 'physicsguard.core.signal_mapping',
    'sha256_file': 'physicsguard.core.data_file_manifest',
    'validate_model_dataset': 'physicsguard.core.model_dataset_validation',
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
