from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    PhysicalModelBlueprintReview,
)


def test_complete_blueprint_derives_static_closure_without_claiming_physical_truth(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()

    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)

    assert review.status == "pass"
    assert review.deepest_licensed_layer == "static_blueprint"
    assert review.first_gap_id is None
    assert review.coverage.uncovered_member_ids == []
    assert review.understanding_target == "declared_consistency"
    assert review.declared_consistency_status == "pass"
    assert review.object_dna_readiness == "not_requested"
    assert "passed static physical-blueprint closure" in review.safe_claim
    assert "does not by itself prove physical truth" in review.unsafe_claim_boundary


def test_missing_child_input_mapping_stops_at_typed_interfaces(complete_physical_blueprint) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = blueprint.model_dump(mode="json")
    refinement = data["refinements"][0]
    refinement["port_mappings"] = [
        item for item in refinement["port_mappings"] if item["target_port_id"] != "port.pump.voltage"
    ]
    incomplete = PhysicalModelBlueprint.model_validate(data)

    review = complete_physical_blueprint.review(incomplete, base_dir=base_dir)

    assert review.status == "incomplete"
    assert review.deepest_licensed_layer == "hierarchy_ownership"
    assert review.first_gap_id is not None
    assert any(gap.code == "required_child_input_unmapped" for gap in review.gaps)


def test_stale_native_binding_invalidates_only_bound_layers(complete_physical_blueprint) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = blueprint.model_dump(mode="json")
    data["bindings"][0]["status"] = "stale"
    stale = PhysicalModelBlueprint.model_validate(data)

    review = complete_physical_blueprint.review(stale, base_dir=base_dir)

    assert review.status == "stale"
    assert any(gap.code == "native_binding_not_current" for gap in review.gaps)
    assert any(layer.layer == "target_inventory" and layer.status == "pass" for layer in review.layer_results)


def test_review_is_deterministic(complete_physical_blueprint) -> None:
    blueprint, base_dir = complete_physical_blueprint()

    first = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    second = complete_physical_blueprint.review(blueprint, base_dir=base_dir)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.logical_report_fingerprint == second.logical_report_fingerprint


def test_caller_cannot_self_sign_or_rewrite_blueprint_review_receipt(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    rewritten = review.model_dump(mode="json")
    rewritten["deepest_licensed_layer"] = "target_inventory"

    with pytest.raises(ValidationError, match="logical_report_fingerprint"):
        PhysicalModelBlueprintReview.model_validate(rewritten)

    self_declared = review.model_dump(mode="json")
    self_declared["caller_declared_complete"] = True

    with pytest.raises(ValidationError):
        PhysicalModelBlueprintReview.model_validate(self_declared)
