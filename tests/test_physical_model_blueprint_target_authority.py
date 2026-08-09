from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.core.target_inventory_authority import (
    derive_target_inventory,
    observe_target_inventory_authority,
)
from physicsguard.schema.physical_model_blueprint import (
    TargetInventoryAuthority,
    TargetMaterialDocument,
    canonical_blueprint_fingerprint,
    fingerprint_inventory,
    fingerprint_target_material_revision,
    fingerprint_target_inventory_authority,
    fingerprint_target_inventory_execution,
    target_material_request_id,
)


def _resign_authority(data: dict) -> TargetInventoryAuthority:
    data["inventory"]["inventory_fingerprint"] = fingerprint_inventory(
        data["inventory"]
    )
    execution = data["execution"]
    execution["result_fingerprint"] = data["inventory"]["inventory_fingerprint"]
    input_fingerprints = {
        item["reference_id"]: item["artifact"]["sha256"]
        for item in data["input_references"]
    }
    execution["terminal_receipt_fingerprint"] = canonical_blueprint_fingerprint(
        {
            "execution_id": execution["execution_id"],
            "owner_id": execution["owner_id"],
            "request_id": execution["request_id"],
            "input_fingerprints": input_fingerprints,
            "target_system_id": execution["target_system_id"],
            "subject_revision": execution["subject_revision"],
            "adapter_tool_id": execution["adapter_tool_id"],
            "adapter_tool_version": execution["adapter_tool_version"],
            "result_status": execution["result_status"],
            "terminal_status": execution["terminal_status"],
            "result_fingerprint": execution["result_fingerprint"],
        }
    )
    execution["execution_fingerprint"] = fingerprint_target_inventory_execution(
        execution
    )
    data["authority_fingerprint"] = fingerprint_target_inventory_authority(data)
    return TargetInventoryAuthority.model_validate(data)


def test_reviewer_requires_authority_but_has_no_caller_registry_argument(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()

    with pytest.raises(TypeError, match="target_inventory_authority"):
        review_physical_model_blueprint(blueprint, base_dir=base_dir)
    with pytest.raises(TypeError, match="provider_registry"):
        review_physical_model_blueprint(
            blueprint,
            target_inventory_authority=(
                complete_physical_blueprint.target_inventory_authority
            ),
            provider_registry=object(),
            base_dir=base_dir,
        )


def test_local_target_material_is_replayed_and_detects_stale_input(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    material_path = complete_physical_blueprint.target_material_path
    material_path.write_text(
        material_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)

    assert review.status == "stale"
    assert any(
        gap.code == "target_inventory_authority_not_verified"
        and gap.status == "stale"
        and "content fingerprint is stale" in gap.message
        for gap in review.gaps
    )
    assert review.coverage.governed_member_ids == []


def test_acceptance_denominator_is_derived_from_the_live_target_material(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    material = TargetMaterialDocument.model_validate(
        json.loads(
            complete_physical_blueprint.target_material_path.read_text(
                encoding="utf-8"
            )
        )
    )
    expected_inventory = derive_target_inventory(material)

    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)

    assert review.status == "pass"
    assert review.coverage.governed_member_ids == sorted(
        member.member_id for member in expected_inventory.members
    )
    assert len(review.coverage.governed_member_ids) == len(
        expected_inventory.members
    )


@pytest.mark.parametrize("tampered_field", ["request_id", "subject_revision"])
def test_self_signed_request_or_revision_change_is_stale(
    complete_physical_blueprint,
    tampered_field: str,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(
        complete_physical_blueprint.target_inventory_authority.model_dump(mode="json")
    )
    if tampered_field == "request_id":
        data["request_id"] = "request.external-pump-loop.target-inventory.attacker"
        data["execution"]["request_id"] = data["request_id"]
    else:
        data["subject_revision"] = "bench-r2"
        data["inventory"]["subject_revision"] = "bench-r2"
        data["execution"]["subject_revision"] = "bench-r2"
    authority = _resign_authority(data)

    review = review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )

    assert review.status == "stale"
    assert any(
        gap.code == "target_inventory_authority_not_verified"
        and "derived target-material request" in gap.message
        for gap in review.gaps
    )
    assert len(review.coverage.governed_member_ids) == len(
        blueprint.inventory.members
    )


def test_unregistered_external_adapter_is_unverified(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(
        complete_physical_blueprint.target_inventory_authority.model_dump(mode="json")
    )
    data["execution"]["adapter_tool_id"] = "external.vendor.inventory"
    authority = _resign_authority(data)

    observation = observe_target_inventory_authority(
        authority,
        base_dir=complete_physical_blueprint.authority_base_dir,
    )

    review = review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )

    assert review.status == "blocked"
    assert observation.status == "unverified"
    assert any(
        gap.code == "target_inventory_authority_not_verified"
        and "no runtime-owned current adapter capability" in gap.message
        for gap in review.gaps
    )
    assert review.coverage.governed_member_ids == []


def test_runtime_adapter_accepts_a_new_explicit_non_fixture_target_snapshot(
    complete_physical_blueprint,
    tmp_path,
) -> None:
    complete_physical_blueprint()
    material_data = json.loads(
        complete_physical_blueprint.target_material_path.read_text(encoding="utf-8")
    )
    material_data.update(
        {
            "inventory_id": "inventory.arbitrary-experiment.r2",
            "provider_id": "provider.arbitrary-experiment",
            "target_system_id": "arbitrary-non-code-experiment",
            "subject_revision": "experiment-r2",
            "boundary_fingerprint": hashlib.sha256(
                b"arbitrary-non-code-experiment-boundary-r2"
            ).hexdigest(),
        }
    )
    material_data.pop("request_id", None)
    material_data.pop("material_revision_fingerprint", None)
    material_data["material_revision_fingerprint"] = (
        fingerprint_target_material_revision(material_data)
    )
    material_data["request_id"] = target_material_request_id(
        material_data["material_revision_fingerprint"]
    )
    material = TargetMaterialDocument.model_validate(material_data)
    material_bytes = json.dumps(
        material.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    material_path = tmp_path / "arbitrary_target_material.json"
    material_path.write_bytes(material_bytes)

    authority_data = deepcopy(
        complete_physical_blueprint.target_inventory_authority.model_dump(mode="json")
    )
    authority_data.update(
        {
            "provider_id": material.provider_id,
            "request_id": material.request_id,
            "target_system_id": material.target_system_id,
            "subject_revision": material.subject_revision,
            "boundary_fingerprint": material.boundary_fingerprint,
            "inventory": derive_target_inventory(material).model_dump(mode="json"),
        }
    )
    authority_data["input_references"][0]["artifact"] = {
        "repo_path": material_path.name,
        "sha256": hashlib.sha256(material_bytes).hexdigest(),
    }
    authority_data["execution"].update(
        {
            "request_id": material.request_id,
            "target_system_id": material.target_system_id,
            "subject_revision": material.subject_revision,
        }
    )
    authority = _resign_authority(authority_data)

    observation = observe_target_inventory_authority(authority, base_dir=tmp_path)

    assert observation.status == "pass"
    assert observation.inventory is not None
    assert observation.inventory.target_system_id == "arbitrary-non-code-experiment"
