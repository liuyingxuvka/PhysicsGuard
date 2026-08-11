from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.physical_model_blueprint_adapters import _normalize_object_dna_payload
from physicsguard.schema.native_object_dna import (
    build_native_object_dna_observation,
    fingerprint_native_object_dna_observation,
)


def _structured_payload() -> dict[str, object]:
    return {
        "observation_id": "obs.structured",
        "provider_id": "provider.structured",
        "provider_kind": "structured-document",
        "provider_version": "1",
        "profile": "structured-object.v1",
        "target_system_id": "target.example",
        "subject_revision": "rev.1",
        "object_id": "object.example",
        "boundary_fingerprint": "0" * 64,
        "source_census": [],
        "behavior_case_universe": [],
        "behavior_case_results": [],
        "status": "pass",
        "findings": [],
        "safe_claim": "Only this exact structured object document was observed.",
        "claim_boundary": "No inaccessible external material is covered.",
    }


def test_structured_object_profile_is_provider_neutral_and_strict() -> None:
    observation = build_native_object_dna_observation(_structured_payload())

    assert observation.profile == "structured-object.v1"
    assert observation.schema_version == "physicsguard.native-object-dna-observation.v1"
    assert observation.observation_fingerprint == fingerprint_native_object_dna_observation(observation)
    normalized = _normalize_object_dna_payload(
        "native_object_dna_observation",
        observation.model_dump(mode="json", exclude_none=False),
    )
    assert normalized is not None
    assert normalized["profile"] == "structured-object.v1"

    with pytest.raises(ValueError):
        build_native_object_dna_observation({**_structured_payload(), "unexpected": True})


def test_native_object_dna_loader_does_not_accept_fmi_result_shape_as_neutral() -> None:
    payload = _structured_payload()
    payload["schema_version"] = "physicsguard.fmi-observation-result.v1"
    assert _normalize_object_dna_payload("native_object_dna_observation", payload) is None
