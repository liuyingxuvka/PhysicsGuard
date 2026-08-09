from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import physicsguard
import physicsguard.core.physical_model_blueprint_adapters as adapter_module
from physicsguard.core.fmi_observation import review_fmi_observation_request
from physicsguard.core.physical_model_blueprint_adapters import (
    _execute_native_operation,
    observe_native_binding,
    observe_native_bindings,
)
from physicsguard.schema.fmi_observation import build_fmi_observation_request
from physicsguard.schema.physical_model_blueprint import (
    NativeBinding,
    NativeExecutionEvidence,
    canonical_blueprint_fingerprint,
    fingerprint_native_execution_evidence,
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _generic_fmi_request(tmp_path: Path):
    model_description = b"""<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription fmiVersion="3.0" modelName="GenericOscillator" instantiationToken="generic-token">
  <ModelExchange modelIdentifier="GenericOscillator"/>
  <TypeDefinitions><Float64Type name="Position" unit="m"/></TypeDefinitions>
  <ModelVariables>
    <Float64 name="x" valueReference="1" causality="output" variability="continuous" declaredType="Position" start="1" reinit="true"/>
    <Float64 name="der(x)" valueReference="2" causality="local" variability="continuous" derivative="1"/>
  </ModelVariables>
</fmiModelDescription>
"""
    fmu_buffer = io.BytesIO()
    with zipfile.ZipFile(fmu_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("modelDescription.xml", model_description)
        archive.writestr("sources/equation.c", b"double dx(double x) { return -x; }\n")
        archive.writestr("resources/reference.csv", b"time,x\n0,1\n")
    fmu_bytes = fmu_buffer.getvalue()
    license_bytes = b"Synthetic test license\n"
    release_buffer = io.BytesIO()
    with zipfile.ZipFile(release_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("3.0/GenericOscillator.fmu", fmu_bytes)
        archive.writestr("LICENSE.txt", license_bytes)
    release_bytes = release_buffer.getvalue()

    (tmp_path / "GenericOscillator.fmu").write_bytes(fmu_bytes)
    (tmp_path / "Reference-Package.zip").write_bytes(release_bytes)
    (tmp_path / "LICENSE.txt").write_bytes(license_bytes)
    request = build_fmi_observation_request(
        {
            "schema_version": "physicsguard.fmi-observation-request.v1",
            "observation_id": "generic-oscillator.fmi3.observation",
            "target_system_id": "generic-oscillator",
            "subject_revision": "r1",
            "source": {
                "provider_id": "example.fmi.publisher",
                "source_uri": "https://example.invalid/generic-oscillator",
                "release_uri": "https://example.invalid/generic-oscillator/releases/r1",
                "release_version": "r1",
                "license_id": "Synthetic-Test",
                "claim_boundary": "The test supplies source labels independently; only exact local bytes are observed.",
            },
            "fmi_version": "3.0",
            "interface_kind": "model_exchange",
            "expected_model_name": "GenericOscillator",
            "expected_model_identifier": "GenericOscillator",
            "artifacts": [
                {
                    "artifact_id": "release",
                    "role": "release_archive",
                    "relative_path": "Reference-Package.zip",
                    "sha256": _sha256(release_bytes),
                    "size_bytes": len(release_bytes),
                },
                {
                    "artifact_id": "fmu",
                    "role": "fmu",
                    "relative_path": "GenericOscillator.fmu",
                    "sha256": _sha256(fmu_bytes),
                    "size_bytes": len(fmu_bytes),
                    "container_artifact_id": "release",
                    "container_member_path": "3.0/GenericOscillator.fmu",
                },
                {
                    "artifact_id": "license",
                    "role": "license",
                    "relative_path": "LICENSE.txt",
                    "sha256": _sha256(license_bytes),
                    "size_bytes": len(license_bytes),
                    "container_artifact_id": "release",
                    "container_member_path": "LICENSE.txt",
                },
            ],
            "fmu_artifact_id": "fmu",
            "expected_members": [
                {
                    "member_id": "model-description",
                    "role": "model_description",
                    "member_path": "modelDescription.xml",
                    "sha256": _sha256(model_description),
                    "size_bytes": len(model_description),
                },
                {
                    "member_id": "equation-source",
                    "role": "source",
                    "member_path": "sources/equation.c",
                    "sha256": _sha256(b"double dx(double x) { return -x; }\n"),
                    "size_bytes": len(b"double dx(double x) { return -x; }\n"),
                },
            ],
            "expected_variables": [
                {
                    "variable_name": "x",
                    "value_reference": 1,
                    "variable_type": "Float64",
                    "causality": "output",
                    "variability": "continuous",
                    "unit": "m",
                    "start": 1.0,
                    "reinit": True,
                    "physical_quantity_id": "position",
                    "source_state_role": "continuous_state",
                },
                {
                    "variable_name": "der(x)",
                    "value_reference": 2,
                    "variable_type": "Float64",
                    "causality": "local",
                    "variability": "continuous",
                    "derivative_of_value_reference": 1,
                    "physical_quantity_id": "position_derivative",
                    "source_state_role": "continuous_derivative",
                },
            ],
            "semantic_selectors": [
                {
                    "selector_id": "selector.generic.derivative",
                    "source_member_id": "equation-source",
                    "function_name": "dx",
                    "source_fragment": "return -x;",
                    "semantic_kind": "equation",
                    "semantic_statement": "Derivative equals negative position.",
                    "semantic_expression": "dx_dt = -x",
                    "claim_boundary": "Verified only for this exact synthetic source function and fragment.",
                }
            ],
            "behavior_cases": [],
        }
    )
    request_path = tmp_path / "fmi_observation_request.yaml"
    request_path.write_text(
        yaml.safe_dump(request.model_dump(mode="json", exclude_none=False), sort_keys=False),
        encoding="utf-8",
    )
    return request, request_path


def test_generic_fmi_observer_uses_one_provider_neutral_path(tmp_path: Path) -> None:
    request, request_path = _generic_fmi_request(tmp_path)

    result = review_fmi_observation_request(request_path)

    assert result.status == "pass"
    assert result.observation_id == request.observation_id
    assert result.model_name == "GenericOscillator"
    assert result.model_identifier == "GenericOscillator"
    assert result.supported_interface_kinds == ["model_exchange"]
    assert [item.variable_name for item in result.variable_observations] == ["x", "der(x)"]
    assert result.variable_observations[0].unit == "m"
    variable_member = next(
        item for item in result.source_census if item.source_member_id == "fmi.variable:x"
    )
    assert variable_member.fmi_variable_contract is not None
    assert variable_member.fmi_variable_contract.physical_quantity_id == "position"
    source_member = next(
        item
        for item in result.source_census
        if item.source_member_id == "fmi.member:sources/equation.c"
    )
    assert [item.selector_id for item in source_member.semantic_selectors] == [
        "selector.generic.derivative"
    ]
    assert source_member.semantic_selectors[0].status == "verified"
    serialized = json.dumps(result.model_dump(mode="json", exclude_none=False))
    assert str(tmp_path) not in serialized
    assert "BouncingBall" not in serialized


def test_native_source_census_cannot_be_shrunk_by_expected_subsets(tmp_path: Path) -> None:
    request, request_path = _generic_fmi_request(tmp_path)
    payload = request.model_dump(mode="json", exclude_none=False)
    payload["expected_variables"] = [
        item for item in payload["expected_variables"] if item["variable_name"] == "x"
    ]
    reduced = build_fmi_observation_request(payload)
    request_path.write_text(
        yaml.safe_dump(reduced.model_dump(mode="json", exclude_none=False), sort_keys=False),
        encoding="utf-8",
    )

    result = review_fmi_observation_request(request_path)

    assert result.status == "pass"
    assert [item.variable_name for item in result.variable_observations] == ["x"]
    source_ids = {item.source_member_id for item in result.source_census}
    assert {
        "fmi.member:modelDescription.xml",
        "fmi.member:sources/equation.c",
        "fmi.member:resources/reference.csv",
        "fmi.variable:x",
        "fmi.variable:der(x)",
    }.issubset(source_ids)
    assert result.source_census_fingerprint


def test_semantic_selector_is_unresolved_when_exact_source_fragment_is_absent(
    tmp_path: Path,
) -> None:
    request, request_path = _generic_fmi_request(tmp_path)
    payload = request.model_dump(mode="json", exclude_none=False)
    payload["semantic_selectors"][0]["source_fragment"] = "return x;"
    changed = build_fmi_observation_request(payload)
    request_path.write_text(
        yaml.safe_dump(changed.model_dump(mode="json", exclude_none=False), sort_keys=False),
        encoding="utf-8",
    )

    result = review_fmi_observation_request(request_path)

    assert result.status == "blocked"
    assert result.first_gap_code == "fmi_semantic_selector_unresolved"
    source_member = next(
        item
        for item in result.source_census
        if item.source_member_id == "fmi.member:sources/equation.c"
    )
    assert source_member.semantic_selectors[0].status == "unresolved"
    assert source_member.semantic_selectors[0].first_gap_code == (
        "fmi_semantic_selector_fragment_unresolved"
    )


def test_fmi_observation_is_a_replayable_native_binding_not_hash_only(tmp_path: Path) -> None:
    request, request_path = _generic_fmi_request(tmp_path)
    terminal_payload = _execute_native_operation("fmi_observation_request", request_path)
    request_sha256 = hashlib.sha256(request_path.read_bytes()).hexdigest()
    execution_payload = {
        "execution_id": "execution.generic-fmi-observation.r1",
        "native_owner_id": "physicsguard.fmi-observation",
        "operation_id": "fmi_observation.review",
        "native_schema": "fmi_observation_request",
        "input_artifact_sha256": request_sha256,
        "target_system_id": request.target_system_id,
        "subject_revision": request.subject_revision,
        "tool_id": "physicsguard",
        "tool_version": physicsguard.__version__,
        "expected_terminal_status": "pass",
        "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(terminal_payload),
    }
    execution_payload["execution_fingerprint"] = fingerprint_native_execution_evidence(
        execution_payload
    )
    execution = NativeExecutionEvidence.model_validate(execution_payload)
    binding = NativeBinding.model_validate(
        {
            "binding_id": "binding.generic-fmi-observation",
            "owner_element_id": "generic-oscillator",
            "binding_kind": "evidence",
            "native_schema": "fmi_observation_request",
            "subject_id": request.observation_id,
            "subject_revision": request.subject_revision,
            "artifact": {
                "repo_path": request_path.name,
                "sha256": request_sha256,
            },
            "native_execution_id": execution.execution_id,
            "status": "current",
        }
    )

    observed = observe_native_binding(
        binding,
        base_dir=tmp_path,
        providers={},
        target_system_id=request.target_system_id,
        subject_revision=request.subject_revision,
        executions={execution.execution_id: execution},
    )

    assert observed.native_identity == request.observation_id
    assert observed.qualifies_native_execution
    assert observed.terminal_receipt_fingerprint == execution.terminal_receipt_fingerprint


def test_identical_native_requests_are_replayed_once_for_multiple_model_bindings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    request, request_path = _generic_fmi_request(tmp_path)
    terminal_payload = _execute_native_operation("fmi_observation_request", request_path)
    request_sha256 = hashlib.sha256(request_path.read_bytes()).hexdigest()
    execution_payload = {
        "execution_id": "execution.shared-fmi-observation.r1",
        "native_owner_id": "physicsguard.fmi-observation",
        "operation_id": "fmi_observation.review",
        "native_schema": "fmi_observation_request",
        "input_artifact_sha256": request_sha256,
        "target_system_id": request.target_system_id,
        "subject_revision": request.subject_revision,
        "tool_id": "physicsguard",
        "tool_version": physicsguard.__version__,
        "expected_terminal_status": "pass",
        "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(terminal_payload),
    }
    execution_payload["execution_fingerprint"] = fingerprint_native_execution_evidence(
        execution_payload
    )
    execution = NativeExecutionEvidence.model_validate(execution_payload)
    bindings = [
        NativeBinding.model_validate(
            {
                "binding_id": f"binding.shared-fmi-observation.{index}",
                "owner_element_id": f"element-{index}",
                "binding_kind": "test",
                "native_schema": "fmi_observation_request",
                "subject_id": request.observation_id,
                "subject_revision": request.subject_revision,
                "artifact": {"repo_path": request_path.name, "sha256": request_sha256},
                "native_execution_id": execution.execution_id,
                "status": "current",
            }
        )
        for index in range(2)
    ]
    actual_execute = adapter_module._execute_native_operation
    calls = []

    def counted_execute(native_schema, path):
        calls.append((native_schema, path))
        return actual_execute(native_schema, path)

    monkeypatch.setattr(adapter_module, "_execute_native_operation", counted_execute)

    observations = observe_native_bindings(
        bindings,
        base_dir=tmp_path,
        providers={},
        target_system_id=request.target_system_id,
        subject_revision=request.subject_revision,
        executions={execution.execution_id: execution},
    )

    assert len(calls) == 1
    assert set(observations) == {item.binding_id for item in bindings}
    assert all(item.qualifies_native_execution for item in observations.values())
    assert all(item.source_census for item in observations.values())


def test_rebound_terminal_result_and_execution_fingerprints_do_not_replace_fresh_replay(
    tmp_path: Path,
) -> None:
    request, request_path = _generic_fmi_request(tmp_path)
    actual_terminal = _execute_native_operation("fmi_observation_request", request_path)
    fabricated_terminal = dict(actual_terminal)
    fabricated_terminal["safe_claim"] = "fabricated broader terminal claim"
    request_sha256 = hashlib.sha256(request_path.read_bytes()).hexdigest()
    execution_payload = {
        "execution_id": "execution.fabricated-fmi-observation.r1",
        "native_owner_id": "physicsguard.fmi-observation",
        "operation_id": "fmi_observation.review",
        "native_schema": "fmi_observation_request",
        "input_artifact_sha256": request_sha256,
        "target_system_id": request.target_system_id,
        "subject_revision": request.subject_revision,
        "tool_id": "physicsguard",
        "tool_version": physicsguard.__version__,
        "expected_terminal_status": "pass",
        "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(
            fabricated_terminal
        ),
    }
    execution_payload["execution_fingerprint"] = fingerprint_native_execution_evidence(
        execution_payload
    )
    execution = NativeExecutionEvidence.model_validate(execution_payload)
    binding = NativeBinding.model_validate(
        {
            "binding_id": "binding.fabricated-fmi-observation",
            "owner_element_id": "generic-oscillator",
            "binding_kind": "evidence",
            "native_schema": "fmi_observation_request",
            "subject_id": request.observation_id,
            "subject_revision": request.subject_revision,
            "artifact": {"repo_path": request_path.name, "sha256": request_sha256},
            "native_execution_id": execution.execution_id,
            "status": "current",
        }
    )

    observed = observe_native_binding(
        binding,
        base_dir=tmp_path,
        providers={},
        target_system_id=request.target_system_id,
        subject_revision=request.subject_revision,
        executions={execution.execution_id: execution},
    )

    assert observed.status == "stale"
    assert not observed.qualifies_native_execution
    assert "terminal receipt fingerprint differs" in observed.findings[0]


def test_fmi_observer_blocks_changed_bytes_and_absolute_paths(tmp_path: Path) -> None:
    _, request_path = _generic_fmi_request(tmp_path)
    (tmp_path / "GenericOscillator.fmu").write_bytes(b"changed")

    result = review_fmi_observation_request(request_path)

    assert result.status == "blocked"
    assert result.first_gap_code == "fmi_artifact_integrity_mismatch"

    request_payload = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    request_payload["artifacts"][0]["relative_path"] = str(tmp_path / "Reference-Package.zip")
    request_payload["request_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="forward-relative"):
        build_fmi_observation_request(request_payload)


def test_recomputed_request_fingerprint_cannot_replace_restricted_oracle(
    tmp_path: Path,
) -> None:
    request, request_path = _generic_fmi_request(tmp_path)
    payload = request.model_dump(mode="json", exclude_none=False)
    payload["oracles"] = [
        {
            "oracle_id": "oracle.generic-double",
            "purpose": "Independently derive twice the frozen initial value.",
            "input_names": ["x"],
            "expressions": [
                {"result_name": "x_twice", "expression": "2.0 * x"}
            ],
            "source_member_ids": ["model-description"],
            "claim_boundary": "Restricted arithmetic covers this synthetic relation only.",
        }
    ]
    payload["behavior_cases"] = [
        {
            "case_id": "tampered-expected",
            "operation": "read_after_initialization",
            "independent_oracle_id": "oracle.generic-double",
            "oracle_input_bindings": {"x": "x"},
            "oracle_output_bindings": {"x": "x_twice"},
            "purpose": "A caller changes the expected literal and recomputes the request identity.",
            "start_time": 0.0,
            "assignments": [],
            "read_variable_names": ["x"],
            "expected_values": [
                {
                    "variable_name": "x",
                    "value": 999.0,
                    "absolute_tolerance": 0.0,
                }
            ],
            "expected_terminal_status": "ok",
        }
    ]
    tampered = build_fmi_observation_request(payload)
    request_path.write_text(
        yaml.safe_dump(tampered.model_dump(mode="json", exclude_none=False), sort_keys=False),
        encoding="utf-8",
    )

    result = review_fmi_observation_request(request_path)

    assert result.status == "blocked"
    assert result.first_gap_code == "fmi_oracle_expectation_mismatch"
    assert any("restricted independent oracle" in finding for finding in result.findings)
    assert [item.native_case_id for item in result.behavior_case_universe] == [
        "tampered-expected"
    ]
    assert result.behavior_case_universe[0].disposition == "required"
    assert result.behavior_case_universe_fingerprint
