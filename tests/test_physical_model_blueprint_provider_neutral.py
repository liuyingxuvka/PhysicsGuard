from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.core.physical_model_blueprint_adapters import observe_native_binding
from physicsguard.schema.physical_model_blueprint import (
    NativeBinding,
    PhysicalModelBlueprint,
    fingerprint_provider_binding_observation,
)


ROOT = Path(__file__).resolve().parents[1]


def _bind_external_observation(provider: dict, binding: dict, *, subject_id: str | None = None) -> None:
    observation = {
        "subject_id": subject_id or binding["subject_id"],
        "subject_revision": binding["subject_revision"],
        "binding_kind": binding["binding_kind"],
        "native_schema": binding["native_schema"],
        "artifact_sha256": binding["artifact"]["sha256"],
        "semantic_ids": binding["semantic_ids"],
        "obligation_ids": binding["obligation_ids"],
        "status": "current",
    }
    observation["observation_fingerprint"] = fingerprint_provider_binding_observation(
        observation
    )
    provider.setdefault("binding_observations", []).append(observation)
    provider["input_fingerprints"][
        f"binding_observation_{len(provider['binding_observations'])}"
    ] = observation["observation_fingerprint"]


def test_two_provider_kinds_share_one_canonical_contract(complete_physical_blueprint) -> None:
    blueprint, base_dir = complete_physical_blueprint(provider_kind="filesystem-manifest")
    data = deepcopy(blueprint.model_dump(mode="json"))
    boundary = data["target"]["boundary_fingerprint"]
    data["required_capability_ids"].append("experimental_observation")
    data["capability_owners"]["experimental_observation"] = "provider.testbench"
    data["providers"].append(
        {
            "provider_id": "provider.testbench",
            "provider_kind": "opc-ua-testbench-export",
            "provider_version": "2026.08",
            "target_system_id": data["target"]["target_system_id"],
            "subject_revision": data["target"]["subject_revision"],
            "capability_ids": ["experimental_observation"],
            "input_fingerprints": {"bench_boundary": boundary},
            "payload_fingerprint": boundary,
            "status": "current",
            "claim_boundary": "Observed testbench channels only; no source or equation authority.",
        }
    )

    neutral = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(neutral, base_dir=base_dir)

    assert {provider.provider_kind for provider in neutral.providers} == {
        "filesystem-manifest",
        "opc-ua-testbench-export",
    }
    assert review.status == "pass"


def test_non_python_modelica_target_keeps_external_content_addresses_bounded_without_replay(
    complete_physical_blueprint,
) -> None:
    blueprint, _ = complete_physical_blueprint(
        target_kind="simulation_model",
        provider_kind="modelica-fmu-manifest",
    )
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["target"]["purpose"] = "Qualify a bounded external Modelica pump-loop simulation model."
    for index, binding in enumerate(data["bindings"]):
        sha256 = binding["artifact"]["sha256"]
        binding["subject_id"] = f"modelica:{binding['binding_id']}"
        data["providers"][0]["input_fingerprints"][f"external_artifact_{index}"] = sha256
        binding["artifact"] = {
            "external_uri": f"provider://modelica-fmu/{binding['binding_id']}",
            "sha256": sha256,
        }
        _bind_external_observation(data["providers"][0], binding)

    modelica = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(modelica, base_dir=None)

    assert modelica.target.target_kind == "simulation_model"
    assert review.status == "blocked"
    assert review.deepest_licensed_layer == "parent_child_refinement"
    assert set(review.external_identity_only_binding_ids) == {
        binding.binding_id for binding in modelica.bindings
    }
    assert "content was not independently read or hashed" in review.unsafe_claim_boundary
    assert any(
        gap.code == "element_missing_native_owner_replay" for gap in review.gaps
    )


@pytest.mark.parametrize(
    ("case", "expected_text"),
    [
        ("missing_provider", "no explicit provider owner"),
        ("stale_provider", "provider status is stale"),
        ("cross_subject_reuse", "no unique exact subject"),
    ],
)
def test_external_artifact_identity_requires_exact_current_provider_evidence(
    complete_physical_blueprint,
    case: str,
    expected_text: str,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    binding = data["bindings"][0]
    sha256 = binding["artifact"]["sha256"]
    binding["artifact"] = {
        "external_uri": "provider://external-model/implementation",
        "sha256": sha256,
    }
    _bind_external_observation(
        data["providers"][0],
        binding,
        subject_id=("another.subject" if case == "cross_subject_reuse" else None),
    )
    if case == "missing_provider":
        binding["provider_id"] = None
    elif case == "stale_provider":
        data["providers"][0]["status"] = "stale"

    external = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(external, base_dir=base_dir)

    assert review.status != "pass"
    assert review.external_identity_only_binding_ids == []
    assert any(
        gap.code == "native_binding_not_current" and expected_text in gap.message
        for gap in review.gaps
    )


def test_provider_specific_required_fields_are_rejected(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["providers"][0]["python_module"] = "vendor.reader"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PhysicalModelBlueprint.model_validate(data)


def test_non_current_required_provider_capability_is_not_replaced_by_another_provider(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["providers"][0]["status"] = "unsupported"
    unsupported = PhysicalModelBlueprint.model_validate(data)

    review = complete_physical_blueprint.review(unsupported, base_dir=base_dir)

    assert review.status == "blocked"
    assert review.deepest_licensed_layer is None
    assert any(gap.code == "required_provider_capability_not_current" for gap in review.gaps)


@pytest.mark.parametrize(
    "external_uri",
    [
        "https://user:password@example.invalid/model",
        "https://example.invalid/model?access_token=abc",
    ],
)
def test_external_provider_reference_rejects_embedded_credentials(
    complete_physical_blueprint,
    external_uri: str,
) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["bindings"][0]["artifact"] = {
        "external_uri": external_uri,
        "sha256": data["bindings"][0]["artifact"]["sha256"],
    }

    with pytest.raises(ValidationError, match="credential"):
        PhysicalModelBlueprint.model_validate(data)


@pytest.mark.parametrize(
    ("native_schema", "repo_path", "expected_identity", "expected_status"),
    [
        ("data_file_manifest", "data/clean_manifest.yaml", "clean", "current"),
        (
            "logical_dataset_record",
            "datasets/clean_logical_dataset.yaml",
            "pump_loop_clean_dataset",
            "unverified",
        ),
    ],
)
def test_native_dataset_authorities_are_validated_by_explicit_adapters(
    complete_physical_blueprint,
    native_schema: str,
    repo_path: str,
    expected_identity: str,
    expected_status: str,
) -> None:
    blueprint, _ = complete_physical_blueprint()
    base_dir = ROOT / "examples" / "testfile_contracts" / "pump_loop"
    artifact_path = base_dir / repo_path
    binding = NativeBinding.model_validate(
        {
            "binding_id": f"binding.adapter.{native_schema}",
            "owner_element_id": "pump_loop",
            "binding_kind": "dataset",
            "native_schema": native_schema,
            "subject_id": expected_identity,
            "subject_revision": blueprint.target.subject_revision,
            "artifact": {
                "repo_path": repo_path,
                "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            },
            "provider_id": "provider.pump-loop",
            "status": "current",
            "semantic_ids": ["sem.loop.mass"],
            "obligation_ids": ["behavior.loop.mass-pressure-flow"],
        }
    )

    observation = observe_native_binding(
        binding,
        base_dir=base_dir,
        providers={item.provider_id: item for item in blueprint.providers},
        target_system_id=blueprint.target.target_system_id,
        subject_revision=blueprint.target.subject_revision,
        executions={},
    )

    assert observation.status == expected_status
    assert observation.content_verified is True
    assert observation.native_identity == expected_identity
    if native_schema == "logical_dataset_record":
        assert observation.replayable
        assert not observation.qualifies_native_execution


def test_typed_native_file_with_another_subject_identity_is_blocked(
    complete_physical_blueprint,
) -> None:
    blueprint, _ = complete_physical_blueprint()
    base_dir = ROOT / "examples" / "testfile_contracts" / "pump_loop"
    repo_path = "data/clean_manifest.yaml"
    artifact_path = base_dir / repo_path
    binding = NativeBinding.model_validate(
        {
            "binding_id": "binding.adapter.wrong-subject",
            "owner_element_id": "pump_loop",
            "binding_kind": "dataset",
            "native_schema": "data_file_manifest",
            "subject_id": "another_manifest",
            "subject_revision": blueprint.target.subject_revision,
            "artifact": {
                "repo_path": repo_path,
                "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            },
            "provider_id": "provider.pump-loop",
            "status": "current",
            "semantic_ids": ["sem.loop.mass"],
            "obligation_ids": ["behavior.loop.mass-pressure-flow"],
        }
    )

    observation = observe_native_binding(
        binding,
        base_dir=base_dir,
        providers={item.provider_id: item for item in blueprint.providers},
        target_system_id=blueprint.target.target_system_id,
        subject_revision=blueprint.target.subject_revision,
        executions={},
    )

    assert observation.status == "blocked"
    assert observation.native_identity == "clean"
    assert observation.subject_identity_verified is False
    assert "does not match declared subject" in observation.findings[0]


def test_generic_local_artifact_reports_bytes_only_not_subject_semantics(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)

    assert review.byte_identity_only_binding_ids
    assert "prove exact bytes only" in review.unsafe_claim_boundary
