"""Explicit adapters from native PhysicsGuard artifacts into blueprint evidence.

Adapters validate the native owner's schema and identity.  They do not copy the
native result, recompute its physical meaning, or promote its status.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.test_file_contract_loader import load_spec
from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.dataset_identity import LogicalDatasetRecordSpec
from physicsguard.schema.evidence_mesh import EvidenceMeshSpec
from physicsguard.schema.fmi_observation import FmiObservationRequest
from physicsguard.schema.model_dataset_validation import (
    ModelDatasetValidationReportSpec,
    ModelValidationPlanSpec,
)
from physicsguard.schema.model_library import ModelLibraryIndexSpec
from physicsguard.schema.physical_model_blueprint import (
    NativeBinding,
    NativeExecutionEvidence,
    ProviderResult,
    canonical_blueprint_fingerprint,
)
from physicsguard.schema.project_evidence import (
    ProjectEvidenceRegistrySpec,
    ProjectProfileAuthoritySpec,
)
from physicsguard.schema.signal_mapping import SignalMappingLedgerSpec
from physicsguard.schema.task_local_revision import (
    CandidateModelRevisionSpec,
    NativeDepthReceiptSpec,
)
from physicsguard.schema.test_file_contract import TestFileContractSpec, TestFileProjectIndexSpec
from physicsguard.schema.validation_depth import ValidationDepthReceiptSpec
from physicsguard.schema.validation_adequacy import ValidationAdequacyReceiptSpec


@dataclass(frozen=True)
class NativeAuthorityObservation:
    binding_id: str
    adapter_id: str
    status: str
    expected_sha256: str
    actual_sha256: str | None
    native_identity: str | None
    findings: tuple[str, ...]
    content_verified: bool
    subject_identity_verified: bool
    semantic_binding_verified: bool
    replayable: bool = False
    native_owner_executed: bool = False
    execution_identity_verified: bool = False
    terminal_receipt_verified: bool = False
    terminal_receipt_fingerprint: str | None = None
    source_census: tuple[dict[str, object], ...] = ()
    source_census_fingerprint: str | None = None
    native_case_results: tuple[dict[str, object], ...] = ()
    native_case_universe: tuple[dict[str, object], ...] = ()
    native_case_universe_fingerprint: str | None = None
    object_dna_contract_kind: str | None = None
    object_dna_contract_verified: bool = False

    @property
    def current(self) -> bool:
        return self.status == "current"

    @property
    def qualifies_native_execution(self) -> bool:
        return (
            self.current
            and self.replayable
            and self.native_owner_executed
            and self.execution_identity_verified
            and self.terminal_receipt_verified
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "adapter_id": self.adapter_id,
            "status": self.status,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "native_identity": self.native_identity,
            "findings": list(self.findings),
            "content_verified": self.content_verified,
            "subject_identity_verified": self.subject_identity_verified,
            "semantic_binding_verified": self.semantic_binding_verified,
            "replayable": self.replayable,
            "native_owner_executed": self.native_owner_executed,
            "execution_identity_verified": self.execution_identity_verified,
            "terminal_receipt_verified": self.terminal_receipt_verified,
            "terminal_receipt_fingerprint": self.terminal_receipt_fingerprint,
            "source_census": [dict(item) for item in self.source_census],
            "source_census_fingerprint": self.source_census_fingerprint,
            "native_case_results": [dict(item) for item in self.native_case_results],
            "native_case_universe": [dict(item) for item in self.native_case_universe],
            "native_case_universe_fingerprint": self.native_case_universe_fingerprint,
            "object_dna_contract_kind": self.object_dna_contract_kind,
            "object_dna_contract_verified": self.object_dna_contract_verified,
        }


REPLAYABLE_NATIVE_OPERATIONS: dict[str, tuple[str, str]] = {
    "fmi_observation_request": (
        "physicsguard.fmi-observation",
        "fmi_observation.review",
    ),
    "project_evidence_registry": (
        "physicsguard.project-evidence-registry",
        "project_evidence_registry.check",
    ),
    "project_profile": (
        "physicsguard.project-profile",
        "project_profile.review",
    ),
    "signal_mapping_ledger": (
        "physicsguard.signal-mapping-review",
        "signal_mapping.review",
    ),
    "logical_dataset_record": (
        "physicsguard.test-file-contract-review",
        "logical_dataset.check",
    ),
    "test_file_contract": (
        "physicsguard.test-file-contract-review",
        "test_file_contract.check",
    ),
    "test_file_project_index": (
        "physicsguard.test-file-contract-review",
        "test_file_project_index.check",
    ),
    "model_validation_plan": (
        "physicsguard-model-dataset-validation",
        "model_dataset_validation.validate",
    ),
    "model_library_index": (
        "physicsguard.model-library",
        "model_library.check",
    ),
    "candidate_model_revision": (
        "physicsguard.candidate-model-blueprint",
        "task_local_revision.evaluate",
    ),
    "evidence_mesh": (
        "physicsguard.audit-closure",
        "evidence_mesh.check",
    ),
}


def observe_native_binding(
    binding: NativeBinding,
    *,
    base_dir: Path | None,
    providers: dict[str, ProviderResult],
    target_system_id: str,
    subject_revision: str,
    executions: dict[str, NativeExecutionEvidence],
) -> NativeAuthorityObservation:
    """Validate one exact binding through its declared native adapter."""

    adapter_id = f"physicsguard.native-authority.{binding.native_schema}.v1"
    if binding.status != "current":
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status=binding.status,
            expected_sha256=binding.artifact.sha256,
            actual_sha256=None,
            native_identity=None,
            findings=(f"binding declares {binding.status} native status",),
            content_verified=False,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    if binding.artifact.external_uri is not None:
        provider = providers.get(binding.provider_id or "")
        external_failures: list[str] = []
        if binding.provider_id is None:
            external_failures.append("external artifact has no explicit provider owner")
        elif provider is None:
            external_failures.append("external artifact references an unknown provider owner")
        else:
            if provider.status != "current":
                external_failures.append(f"external artifact provider status is {provider.status}")
            if (
                provider.target_system_id != target_system_id
                or provider.subject_revision != subject_revision
            ):
                external_failures.append("external artifact provider targets another subject identity")
            if "native_binding_observation" not in provider.capability_ids:
                external_failures.append(
                    "external artifact provider does not advertise native_binding_observation"
                )
            exact_observations = [
                item
                for item in provider.binding_observations
                if item.subject_id == binding.subject_id
                and item.subject_revision == binding.subject_revision
                and item.artifact_sha256 == binding.artifact.sha256
            ]
            if len(exact_observations) != 1:
                external_failures.append(
                    "external provider has no unique exact subject/revision/artifact observation"
                )
            else:
                observed = exact_observations[0]
                if observed.status != "current":
                    external_failures.append(
                        f"external subject observation status is {observed.status}"
                    )
                if observed.binding_kind != binding.binding_kind:
                    external_failures.append("external subject observation binding kind differs")
                if observed.native_schema != binding.native_schema:
                    external_failures.append("external subject observation native schema differs")
                if set(observed.semantic_ids) != set(binding.semantic_ids):
                    external_failures.append("external subject observation semantic ids differ")
                if set(observed.obligation_ids) != set(binding.obligation_ids):
                    external_failures.append("external subject observation obligation ids differ")
        if external_failures:
            return NativeAuthorityObservation(
                binding_id=binding.binding_id,
                adapter_id=adapter_id,
                status=("stale" if provider is not None and provider.status == "stale" else "blocked"),
                expected_sha256=binding.artifact.sha256,
                actual_sha256=None,
                native_identity=None,
                findings=tuple(external_failures),
                content_verified=False,
                subject_identity_verified=False,
                semantic_binding_verified=False,
            )
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="unverified",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=None,
            native_identity=binding.subject_id,
            findings=(
                "current provider binds the exact external subject envelope, but the native owner cannot be replayed from this external reference",
            ),
            content_verified=False,
            subject_identity_verified=True,
            semantic_binding_verified=True,
        )
    if base_dir is None:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=None,
            native_identity=None,
            findings=("local binding verification requires an explicit blueprint base directory",),
            content_verified=False,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )

    root = base_dir.resolve()
    path = (root / str(binding.artifact.repo_path)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=None,
            native_identity=None,
            findings=("resolved artifact path escapes the declared blueprint boundary",),
            content_verified=False,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    if not path.is_file():
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=None,
            native_identity=None,
            findings=(f"native artifact does not exist: {binding.artifact.repo_path}",),
            content_verified=False,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha256 != binding.artifact.sha256:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="stale",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=actual_sha256,
            native_identity=None,
            findings=("native artifact fingerprint differs from the bound fingerprint",),
            content_verified=False,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    try:
        native = _load_declared_native_schema(binding, path)
    except (OSError, ValueError) as exc:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=actual_sha256,
            native_identity=None,
            findings=(f"native schema validation failed: {exc}",),
            content_verified=False,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    native_identity = _native_identity(native, binding.native_schema)
    if native is not None and native_identity is None:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=actual_sha256,
            native_identity=None,
            findings=("native adapter exposes no stable primary subject identity",),
            content_verified=True,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    if native_identity is not None and native_identity != binding.subject_id:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=actual_sha256,
            native_identity=native_identity,
            findings=(
                f"native subject identity {native_identity} does not match declared subject {binding.subject_id}",
            ),
            content_verified=True,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    if native is None:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=adapter_id,
            status="current",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=actual_sha256,
            native_identity=f"sha256:{actual_sha256}",
            findings=(
                "generic artifact verifies exact bytes only; it does not verify the declared subject or semantic binding",
            ),
            content_verified=True,
            subject_identity_verified=False,
            semantic_binding_verified=False,
        )
    replay = _replay_native_owner(
        binding,
        path,
        executions=executions,
        target_system_id=target_system_id,
        subject_revision=subject_revision,
    )
    if replay is not None:
        return replay
    return NativeAuthorityObservation(
        binding_id=binding.binding_id,
        adapter_id=adapter_id,
        status="current",
        expected_sha256=binding.artifact.sha256,
        actual_sha256=actual_sha256,
        native_identity=native_identity,
        content_verified=True,
        subject_identity_verified=True,
        semantic_binding_verified=True,
        replayable=binding.native_schema in REPLAYABLE_NATIVE_OPERATIONS,
        findings=(
            "native schema and subject identity are current, but this authority has no executable native replay owner",
        ),
    )


def observe_native_bindings(
    bindings: list[NativeBinding],
    *,
    base_dir: Path | None,
    providers: dict[str, ProviderResult],
    target_system_id: str,
    subject_revision: str,
    executions: dict[str, NativeExecutionEvidence],
) -> dict[str, NativeAuthorityObservation]:
    observations: dict[str, NativeAuthorityObservation] = {}
    replay_cache: dict[tuple[str, str, str, str, str], NativeAuthorityObservation] = {}
    for binding in bindings:
        cache_key = (
            binding.native_schema,
            binding.subject_id,
            binding.artifact.sha256,
            binding.native_execution_id or "",
            binding.provider_id or "",
        )
        cached = replay_cache.get(cache_key) if binding.native_schema in REPLAYABLE_NATIVE_OPERATIONS else None
        if cached is not None:
            observations[binding.binding_id] = replace(cached, binding_id=binding.binding_id)
            continue
        observation = observe_native_binding(
            binding,
            base_dir=base_dir,
            providers=providers,
            target_system_id=target_system_id,
            subject_revision=subject_revision,
            executions=executions,
        )
        observations[binding.binding_id] = observation
        if binding.native_schema in REPLAYABLE_NATIVE_OPERATIONS:
            replay_cache[cache_key] = observation
    return observations


def _load_declared_native_schema(binding: NativeBinding, path: Path) -> BaseModel | None:
    if binding.native_schema == "generic_artifact":
        return None
    if binding.native_schema == "hierarchical_audit":
        return load_hierarchical_audit_spec(path)
    loaders: dict[str, tuple[type[BaseModel], Callable[[Path, type[BaseModel]], BaseModel]]] = {
        "fmi_observation_request": (FmiObservationRequest, load_spec),
        "project_evidence_registry": (ProjectEvidenceRegistrySpec, load_spec),
        "project_profile": (ProjectProfileAuthoritySpec, load_spec),
        "signal_mapping_ledger": (SignalMappingLedgerSpec, load_spec),
        "data_file_manifest": (DataFileManifestSpec, load_spec),
        "logical_dataset_record": (LogicalDatasetRecordSpec, load_spec),
        "test_file_contract": (TestFileContractSpec, load_spec),
        "test_file_project_index": (TestFileProjectIndexSpec, load_spec),
        "validation_depth_receipt": (ValidationDepthReceiptSpec, load_spec),
        "validation_adequacy_receipt": (ValidationAdequacyReceiptSpec, load_spec),
        "model_validation_plan": (ModelValidationPlanSpec, load_spec),
        "model_dataset_validation_report": (ModelDatasetValidationReportSpec, load_spec),
        "model_library_index": (ModelLibraryIndexSpec, load_spec),
        "native_depth_receipt": (NativeDepthReceiptSpec, load_spec),
        "candidate_model_revision": (CandidateModelRevisionSpec, load_spec),
        "evidence_mesh": (EvidenceMeshSpec, load_spec),
    }
    spec_type, loader = loaders[binding.native_schema]
    return loader(path, spec_type)


def _native_identity(native: BaseModel | None, native_schema: str) -> str | None:
    if native is None:
        return None
    values = native.model_dump(mode="json", exclude_none=True)
    identity_key = {
        "fmi_observation_request": "observation_id",
        "hierarchical_audit": "audit_name",
        "project_evidence_registry": "registry_id",
        "project_profile": "profile_id",
        "signal_mapping_ledger": "ledger_id",
        "data_file_manifest": "manifest_id",
        "logical_dataset_record": "logical_dataset_id",
        "test_file_contract": "contract_id",
        "test_file_project_index": "project_id",
        "validation_depth_receipt": "validation_id",
        "validation_adequacy_receipt": "blueprint_coverage.coverage_id",
        "model_validation_plan": "validation_id",
        "model_dataset_validation_report": "validation_id",
        "model_library_index": "library_id",
        "native_depth_receipt": "task_id",
        "candidate_model_revision": "revision_id",
        "evidence_mesh": "mesh_id",
    }.get(native_schema)
    if identity_key is None:
        return None
    value = values.get(identity_key)
    if identity_key and "." in identity_key:
        value = values
        for part in identity_key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
    return value if isinstance(value, str) and value else None


def _replay_native_owner(
    binding: NativeBinding,
    path: Path,
    *,
    executions: dict[str, NativeExecutionEvidence],
    target_system_id: str,
    subject_revision: str,
) -> NativeAuthorityObservation | None:
    operation = REPLAYABLE_NATIVE_OPERATIONS.get(binding.native_schema)
    if operation is None:
        return None
    execution = executions.get(binding.native_execution_id or "")
    if execution is None:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=f"physicsguard.native-authority.{binding.native_schema}.v1",
            status="unverified",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=binding.artifact.sha256,
            native_identity=binding.subject_id,
            findings=(
                "replayable native authority has no exact native_execution_id and terminal receipt expectation",
            ),
            content_verified=True,
            subject_identity_verified=True,
            semantic_binding_verified=True,
            replayable=True,
        )
    native_owner_id, operation_id = operation
    from physicsguard import __version__ as physicsguard_version

    identity_failures: list[str] = []
    if execution.native_owner_id != native_owner_id:
        identity_failures.append("native execution owner identity differs")
    if execution.operation_id != operation_id:
        identity_failures.append("native execution operation identity differs")
    if execution.input_artifact_sha256 != binding.artifact.sha256:
        identity_failures.append("native execution input fingerprint differs")
    if execution.target_system_id != target_system_id:
        identity_failures.append("native execution target identity differs")
    if execution.subject_revision != subject_revision:
        identity_failures.append("native execution subject revision differs")
    if execution.tool_version != physicsguard_version:
        identity_failures.append("native execution tool version is stale")
    if identity_failures:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=f"physicsguard.native-authority.{binding.native_schema}.v1",
            status="stale",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=binding.artifact.sha256,
            native_identity=binding.subject_id,
            findings=tuple(identity_failures),
            content_verified=True,
            subject_identity_verified=True,
            semantic_binding_verified=True,
            replayable=True,
        )
    try:
        payload = _execute_native_operation(binding.native_schema, path)
    except Exception as exc:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=f"physicsguard.native-authority.{binding.native_schema}.v1",
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=binding.artifact.sha256,
            native_identity=binding.subject_id,
            findings=(f"native owner replay failed: {exc}",),
            content_verified=True,
            subject_identity_verified=True,
            semantic_binding_verified=True,
            replayable=True,
            execution_identity_verified=True,
        )
    actual_status = str(payload.get("status", ""))
    terminal_fingerprint = canonical_blueprint_fingerprint(payload)
    terminal_failures: list[str] = []
    if actual_status != execution.expected_terminal_status:
        terminal_failures.append(
            f"native replay status {actual_status!r} differs from expected terminal status {execution.expected_terminal_status!r}"
        )
    if terminal_fingerprint != execution.terminal_receipt_fingerprint:
        terminal_failures.append("native replay terminal receipt fingerprint differs")
    if terminal_failures:
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=f"physicsguard.native-authority.{binding.native_schema}.v1",
            status="stale",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=binding.artifact.sha256,
            native_identity=binding.subject_id,
            findings=tuple(terminal_failures),
            content_verified=True,
            subject_identity_verified=True,
            semantic_binding_verified=True,
            replayable=True,
            native_owner_executed=True,
            execution_identity_verified=True,
            terminal_receipt_fingerprint=terminal_fingerprint,
        )
    if actual_status != "pass":
        return NativeAuthorityObservation(
            binding_id=binding.binding_id,
            adapter_id=f"physicsguard.native-authority.{binding.native_schema}.v1",
            status="blocked",
            expected_sha256=binding.artifact.sha256,
            actual_sha256=binding.artifact.sha256,
            native_identity=binding.subject_id,
            findings=(f"native owner replay reached terminal non-pass status {actual_status}",),
            content_verified=True,
            subject_identity_verified=True,
            semantic_binding_verified=True,
            replayable=True,
            native_owner_executed=True,
            execution_identity_verified=True,
            terminal_receipt_verified=True,
            terminal_receipt_fingerprint=terminal_fingerprint,
        )
    verified_fmi_object_dna_contract = (
        binding.native_schema == "fmi_observation_request"
        and payload.get("schema_version") == "physicsguard.fmi-observation-result.v1"
        and bool(payload.get("source_census"))
        and bool(payload.get("source_census_fingerprint"))
        and bool(payload.get("behavior_case_universe"))
        and bool(payload.get("behavior_case_universe_fingerprint"))
    )
    return NativeAuthorityObservation(
        binding_id=binding.binding_id,
        adapter_id=f"physicsguard.native-authority.{binding.native_schema}.v1",
        status="current",
        expected_sha256=binding.artifact.sha256,
        actual_sha256=binding.artifact.sha256,
        native_identity=binding.subject_id,
        findings=(),
        content_verified=True,
        subject_identity_verified=True,
        semantic_binding_verified=True,
        replayable=True,
        native_owner_executed=True,
        execution_identity_verified=True,
        terminal_receipt_verified=True,
        terminal_receipt_fingerprint=terminal_fingerprint,
        source_census=tuple(
            dict(item)
            for item in payload.get("source_census", [])
            if isinstance(item, dict)
        ),
        source_census_fingerprint=(
            str(payload["source_census_fingerprint"])
            if payload.get("source_census_fingerprint") is not None
            else None
        ),
        native_case_results=tuple(
            dict(item)
            for item in payload.get("behavior_case_results", [])
            if isinstance(item, dict)
        ),
        native_case_universe=tuple(
            dict(item)
            for item in payload.get("behavior_case_universe", [])
            if isinstance(item, dict)
        ),
        native_case_universe_fingerprint=(
            str(payload["behavior_case_universe_fingerprint"])
            if payload.get("behavior_case_universe_fingerprint") is not None
            else None
        ),
        object_dna_contract_kind=("fmi.v1" if binding.native_schema == "fmi_observation_request" else None),
        object_dna_contract_verified=verified_fmi_object_dna_contract,
    )


def _execute_native_operation(native_schema: str, path: Path) -> dict[str, object]:
    if native_schema == "fmi_observation_request":
        from physicsguard.core.fmi_observation import review_fmi_observation_request

        return review_fmi_observation_request(path).model_dump(mode="json", exclude_none=False)
    if native_schema == "project_evidence_registry":
        from physicsguard.core.project_evidence import check_project_evidence_registry

        return check_project_evidence_registry(path).to_dict()
    if native_schema == "project_profile":
        from physicsguard.core.project_evidence import review_project_profile_authority

        return review_project_profile_authority(path).to_dict()
    if native_schema == "signal_mapping_ledger":
        from physicsguard.core.signal_mapping import review_signal_mapping_ledger

        return review_signal_mapping_ledger(path).to_dict()
    if native_schema == "logical_dataset_record":
        from physicsguard.core.dataset_identity import check_logical_dataset_record

        return check_logical_dataset_record(path).to_dict()
    if native_schema == "test_file_contract":
        from physicsguard.core.test_file_contract import check_test_file_contract

        return check_test_file_contract(path).to_dict()
    if native_schema == "test_file_project_index":
        from physicsguard.core.test_file_contract import check_test_file_project_index

        return check_test_file_project_index(path).to_dict()
    if native_schema == "model_validation_plan":
        from physicsguard.core.model_dataset_validation import validate_model_dataset

        return validate_model_dataset(path).to_dict()
    if native_schema == "model_library_index":
        from physicsguard.core.model_library import check_model_library_index

        return check_model_library_index(path).to_dict()
    if native_schema == "candidate_model_revision":
        from physicsguard.core.task_local_revision import evaluate_candidate_model_revision

        revision = load_spec(path, CandidateModelRevisionSpec)
        return evaluate_candidate_model_revision(revision, base_dir=path.parent)
    if native_schema == "evidence_mesh":
        from physicsguard.core.evidence_mesh import check_evidence_mesh

        return check_evidence_mesh(path).to_dict()
    raise ValueError(f"native schema has no executable replay owner: {native_schema}")


__all__ = [
    "NativeAuthorityObservation",
    "REPLAYABLE_NATIVE_OPERATIONS",
    "observe_native_binding",
    "observe_native_bindings",
]
