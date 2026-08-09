from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

import physicsguard
from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.physical_model_blueprint_adapters import (
    _execute_native_operation,
    observe_native_binding,
)
from physicsguard.schema.physical_model_blueprint import (
    NativeBinding,
    NativeExecutionEvidence,
    canonical_blueprint_fingerprint,
    fingerprint_native_execution_evidence,
)
from physicsguard.schema.project_evidence import (
    ProjectProfileSpec,
    fingerprint_project_profile_authority,
)
from physicsguard.schema.signal_mapping import fingerprint_signal_mapping_ledger


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def _write_yaml(path: Path, payload: dict) -> str:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(
    *,
    native_schema: str,
    subject_id: str,
    path: Path,
    sha256: str,
    execution_id: str | None,
) -> NativeBinding:
    return NativeBinding.model_validate(
        {
            "binding_id": f"binding:{native_schema}",
            "owner_element_id": "element:bench",
            "binding_kind": "project_record",
            "native_schema": native_schema,
            "subject_id": subject_id,
            "subject_revision": "target-r1",
            "artifact": {"repo_path": path.name, "sha256": sha256},
            "native_execution_id": execution_id,
            "status": "current",
        }
    )


def _execution(
    *,
    execution_id: str,
    native_schema: str,
    native_owner_id: str,
    operation_id: str,
    input_sha256: str,
    terminal_payload: dict,
) -> NativeExecutionEvidence:
    payload = {
        "execution_id": execution_id,
        "native_owner_id": native_owner_id,
        "operation_id": operation_id,
        "native_schema": native_schema,
        "input_artifact_sha256": input_sha256,
        "target_system_id": "target-1",
        "subject_revision": "target-r1",
        "tool_id": "physicsguard",
        "tool_version": physicsguard.__version__,
        "expected_terminal_status": terminal_payload["status"],
        "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(
            terminal_payload
        ),
    }
    payload["execution_fingerprint"] = fingerprint_native_execution_evidence(payload)
    return NativeExecutionEvidence.model_validate(payload)


def _project_profile_payload() -> dict:
    profile = ProjectProfileSpec.model_validate(
        {
            "project_name": "External target bench",
            "run_period": {"coverage_period": "bounded bench campaign r1"},
            "locations": [
                {"location_id": "location:lab", "label": "bounded lab fixture"}
            ],
            "source_refs": [{"path": "source/project-profile.md"}],
        }
    ).model_dump(mode="json", exclude_none=True)
    payload = {
        "artifact_kind": "physicsguard_project_profile",
        "profile_version": "1.0",
        "profile_id": "profile:target-1:r1",
        "target_system_id": "target-1",
        "subject_revision": "target-r1",
        "profile": profile,
    }
    payload["profile_fingerprint"] = fingerprint_project_profile_authority(payload)
    return payload


def _signal_mapping_payload() -> dict:
    payload = {
        "artifact_kind": "physicsguard_signal_mapping_ledger",
        "ledger_version": "1.0",
        "ledger_id": "signal-map:target-1:r1",
        "target_system_id": "target-1",
        "subject_revision": "target-r1",
        "source_artifact_sha256": hashlib.sha256(b"source-signal-r1").hexdigest(),
        "entries": [
            {
                "mapping_id": "mapping:speed",
                "physics_variable": "bench.speed",
                "block_id": "bench",
                "external_signal": "sensor.speed_rpm",
                "expected_unit": "rpm",
                "observed_unit": "rpm",
                "mapping_confidence": 1.0,
                "mapping_status": "confirmed",
                "source_revision": "source-r1",
                "temporal_boundary": "campaign-r1",
                "issue_codes": [],
            }
        ],
        "status": "pass",
        "safe_mapping_claim": "exact speed signal mapping for target-r1 only",
    }
    payload["ledger_fingerprint"] = fingerprint_signal_mapping_ledger(payload)
    return payload


def test_standalone_project_profile_has_its_own_identity_and_native_replay(
    tmp_path: Path,
) -> None:
    path = tmp_path / "project_profile.yaml"
    sha256 = _write_yaml(path, _project_profile_payload())
    terminal = _execute_native_operation("project_profile", path)
    execution = _execution(
        execution_id="execution:project-profile",
        native_schema="project_profile",
        native_owner_id="physicsguard.project-profile",
        operation_id="project_profile.review",
        input_sha256=sha256,
        terminal_payload=terminal,
    )
    binding = _binding(
        native_schema="project_profile",
        subject_id="profile:target-1:r1",
        path=path,
        sha256=sha256,
        execution_id=execution.execution_id,
    )

    observed = observe_native_binding(
        binding,
        base_dir=tmp_path,
        providers={},
        target_system_id="target-1",
        subject_revision="target-r1",
        executions={execution.execution_id: execution},
    )

    assert observed.native_identity == "profile:target-1:r1"
    assert observed.qualifies_native_execution
    assert observed.terminal_receipt_fingerprint == execution.terminal_receipt_fingerprint


def test_signal_mapping_ledger_exposes_stable_identity_and_cannot_pass_on_hash_alone(
    tmp_path: Path,
) -> None:
    path = tmp_path / "signal_mapping.yaml"
    sha256 = _write_yaml(path, _signal_mapping_payload())
    binding = _binding(
        native_schema="signal_mapping_ledger",
        subject_id="signal-map:target-1:r1",
        path=path,
        sha256=sha256,
        execution_id=None,
    )

    hash_only = observe_native_binding(
        binding,
        base_dir=tmp_path,
        providers={},
        target_system_id="target-1",
        subject_revision="target-r1",
        executions={},
    )
    assert hash_only.status == "unverified"
    assert hash_only.native_identity == "signal-map:target-1:r1"
    assert not hash_only.qualifies_native_execution

    terminal = _execute_native_operation("signal_mapping_ledger", path)
    execution = _execution(
        execution_id="execution:signal-map",
        native_schema="signal_mapping_ledger",
        native_owner_id="physicsguard.signal-mapping-review",
        operation_id="signal_mapping.review",
        input_sha256=sha256,
        terminal_payload=terminal,
    )
    replay_binding = binding.model_copy(
        update={"native_execution_id": execution.execution_id}
    )
    replayed = observe_native_binding(
        replay_binding,
        base_dir=tmp_path,
        providers={},
        target_system_id="target-1",
        subject_revision="target-r1",
        executions={execution.execution_id: execution},
    )
    assert replayed.qualifies_native_execution


def test_stale_terminal_receipt_is_not_treated_as_native_execution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "signal_mapping.yaml"
    sha256 = _write_yaml(path, _signal_mapping_payload())
    terminal = _execute_native_operation("signal_mapping_ledger", path)
    execution = _execution(
        execution_id="execution:signal-map",
        native_schema="signal_mapping_ledger",
        native_owner_id="physicsguard.signal-mapping-review",
        operation_id="signal_mapping.review",
        input_sha256=sha256,
        terminal_payload=terminal,
    )
    stale_payload = execution.model_dump(mode="python")
    stale_payload["terminal_receipt_fingerprint"] = "0" * 64
    stale_payload["execution_fingerprint"] = fingerprint_native_execution_evidence(
        stale_payload
    )
    stale = NativeExecutionEvidence.model_validate(stale_payload)
    binding = _binding(
        native_schema="signal_mapping_ledger",
        subject_id="signal-map:target-1:r1",
        path=path,
        sha256=sha256,
        execution_id=stale.execution_id,
    )

    observed = observe_native_binding(
        binding,
        base_dir=tmp_path,
        providers={},
        target_system_id="target-1",
        subject_revision="target-r1",
        executions={stale.execution_id: stale},
    )

    assert observed.status == "stale"
    assert observed.native_owner_executed
    assert not observed.terminal_receipt_verified
    assert not observed.qualifies_native_execution


def test_model_dataset_report_adapter_uses_report_validation_id_not_plan_alias(
    tmp_path: Path,
) -> None:
    report = validate_model_dataset(
        PUMP / "validation" / "clean_validation_plan.yaml"
    ).to_dict()
    path = tmp_path / "model_dataset_report.yaml"
    sha256 = _write_yaml(path, report)
    binding = _binding(
        native_schema="model_dataset_validation_report",
        subject_id=report["validation_id"],
        path=path,
        sha256=sha256,
        execution_id=None,
    )

    observed = observe_native_binding(
        binding,
        base_dir=tmp_path,
        providers={},
        target_system_id="target-1",
        subject_revision="target-r1",
        executions={},
    )

    assert observed.status == "current"
    assert observed.native_identity == report["validation_id"]
    assert observed.content_verified
    assert not observed.replayable
    assert not observed.qualifies_native_execution
