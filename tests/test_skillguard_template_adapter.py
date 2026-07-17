from copy import deepcopy

import pytest

from physicsguard.skillguard_template_adapter import (
    PROJECTION_SCHEMA,
    build_skillguard_template_projection,
)
from physicsguard.template_packs import TemplateRequest, load_default_manifest


def request(**overrides):
    values = {
        "request_id": "request:adapter-test",
        "native_family_id": "physicsguard",
        "native_route_id": "route:physicsguard-model-dataset-validation",
        "purpose_tags": ("dataset-validation",),
        "inputs": {"dataset_id": "dataset:test"},
    }
    values.update(overrides)
    return TemplateRequest(**values)


def test_projection_preserves_exact_native_candidate_inventory_and_selection_inputs():
    projection = build_skillguard_template_projection(
        request(),
        target_id="target:physicsguard-test",
    )
    assert projection["schema_version"] == PROJECTION_SCHEMA
    template_ids = {row["template_id"] for row in projection["catalog"]["templates"]}
    result_ids = {row["template_id"] for row in projection["applicability_results"]}
    assert template_ids == result_ids
    eligible = {row["template_id"] for row in projection["applicability_results"] if row["eligible"]}
    assert "physicsguard.dataset-validation-basic" in eligible
    assert "physicsguard.dataset-validation-comprehensive" in eligible


def test_wrong_route_uses_native_rejections_and_current_base_only():
    projection = build_skillguard_template_projection(
        request(
            native_route_id="route:physicsguard-model-understanding-preflight:review",
            purpose_tags=(),
            inputs={},
        ),
        target_id="target:physicsguard-test",
    )
    eligible = {row["template_id"] for row in projection["applicability_results"] if row["eligible"]}
    assert eligible == {projection["catalog"]["base_template_id"]}


def test_stale_native_manifest_blocks_before_projection():
    manifest = load_default_manifest()
    stale_data = manifest.as_dict()
    stale_data["templates"][0]["claim_boundary"] = "changed after sealing"
    from physicsguard.template_packs import manifest_from_data

    stale = manifest_from_data(stale_data, validate=False)
    with pytest.raises(Exception) as caught:
        build_skillguard_template_projection(
            request(),
            target_id="target:physicsguard-test",
            manifest=stale,
        )
    assert "manifest validation failed" in str(caught.value)


def test_adapter_does_not_accept_an_empty_target_identity():
    with pytest.raises(ValueError, match="target_id"):
        build_skillguard_template_projection(request(), target_id="")
