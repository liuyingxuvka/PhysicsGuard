from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from physicsguard.core.physical_blueprint_trace import (
    affected_physical_blueprint_projection,
)
from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.core.validation_adequacy import (
    _blueprint_element_obligation_ids,
    _blueprint_validation_coverage,
)
from physicsguard.schema.physical_model_blueprint import fingerprint_blueprint
from physicsguard.schema.validation_adequacy import ValidationAdequacyPlanSpec


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _adequacy_with_blueprint(blueprint, root: Path, *, omit_last_element: bool = False):
    blueprint_path = root / "physical_blueprint.yaml"
    blueprint_path.write_text(
        yaml.safe_dump(
            blueprint.model_dump(mode="json", exclude_none=True),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    evidence_path = root / "artifacts" / "evidence.yaml"
    element_rows = []
    for element in sorted(blueprint.elements, key=lambda item: item.element_id):
        obligations = _blueprint_element_obligation_ids(blueprint, element.element_id)
        element_rows.append(
            {
                "element_id": element.element_id,
                "obligations": [
                    {
                        "obligation_id": obligation_id,
                        "evidence": [
                            {
                                "evidence_id": f"evidence:{element.element_id}:{index}",
                                "path": str(evidence_path.relative_to(root)),
                                "sha256": _sha256(evidence_path),
                                "freshness_revision": blueprint.target.subject_revision,
                                "native_owner_id": "physicsguard-test-owner",
                                "native_operation_id": "replay-blueprint-obligation",
                            }
                        ],
                    }
                    for index, obligation_id in enumerate(obligations)
                ],
            }
        )
    if omit_last_element:
        element_rows.pop()
    return ValidationAdequacyPlanSpec.model_validate(
        {
            "threshold_source": "target validation policy",
            "selection_policy_id": "policy.blueprint.coverage.v1",
            "selection_rationale": "bind every blueprint leaf independently",
            "maximum_time_gap": 1.0,
            "blueprint_validation": {
                "blueprint_path": blueprint_path.name,
                "blueprint_sha256": _sha256(blueprint_path),
                "blueprint_fingerprint": fingerprint_blueprint(blueprint),
                "scope": "whole",
                "elements": element_rows,
            },
        }
    )


def test_blueprint_coverage_uses_every_current_element_and_leaf_obligation(
    complete_physical_blueprint,
) -> None:
    blueprint, root = complete_physical_blueprint()
    adequacy = _adequacy_with_blueprint(blueprint, root)
    findings: list[dict[str, object]] = []

    receipt = _blueprint_validation_coverage(
        adequacy,
        base_dir=root,
        findings=findings,
    )

    assert findings == []
    assert receipt["status"] == "pass"
    assert receipt["governed_element_ids"] == sorted(
        item.element_id for item in blueprint.elements
    )
    assert receipt["unresolved_element_ids"] == []
    assert all(row["status"] == "pass" for row in receipt["element_results"])
    assert all(
        set(row["tested_obligation_ids"]) == set(row["governed_obligation_ids"])
        for row in receipt["element_results"]
    )


def test_blueprint_coverage_cannot_hide_a_stale_leaf_evidence(
    complete_physical_blueprint,
) -> None:
    blueprint, root = complete_physical_blueprint()
    adequacy = _adequacy_with_blueprint(blueprint, root)
    payload = adequacy.model_dump(mode="python")
    payload["blueprint_validation"]["elements"][0]["obligations"][0]["evidence"][0][
        "sha256"
    ] = "0" * 64
    stale = ValidationAdequacyPlanSpec.model_validate(payload)
    findings: list[dict[str, object]] = []

    receipt = _blueprint_validation_coverage(stale, base_dir=root, findings=findings)

    assert receipt["status"] == "blocked"
    assert receipt["first_unresolved_id"] == receipt["element_results"][0]["element_id"]
    assert receipt["element_results"][0]["unresolved_obligation_ids"]
    assert "blueprint_validation_evidence_stale" in {
        item["type"] for item in findings
    }


def test_blueprint_coverage_denominator_is_not_shrunk_by_caller_rows(
    complete_physical_blueprint,
) -> None:
    blueprint, root = complete_physical_blueprint()
    adequacy = _adequacy_with_blueprint(
        blueprint,
        root,
        omit_last_element=True,
    )
    findings: list[dict[str, object]] = []

    receipt = _blueprint_validation_coverage(
        adequacy,
        base_dir=root,
        findings=findings,
    )

    assert receipt["status"] == "blocked"
    assert len(receipt["governed_element_ids"]) == len(blueprint.elements)
    assert receipt["unresolved_element_ids"]
    assert "blueprint_validation_element_denominator_mismatch" in {
        item["type"] for item in findings
    }


def test_affected_blueprint_coverage_uses_exact_current_projection_denominator(
    complete_physical_blueprint,
) -> None:
    blueprint, root = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=root)
    projection = affected_physical_blueprint_projection(
        blueprint,
        review,
        ["sem.pump.pressure_rise"],
        target_inventory_authority=(
            complete_physical_blueprint.target_inventory_authority
        ),
        blueprint_base_dir=root,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )
    projection_path = root / "affected_projection.yaml"
    projection_path.write_text(
        yaml.safe_dump(
            projection.model_dump(mode="json", exclude_none=True),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    selected_ids = sorted(
        {
            node.owner_element_id
            for node in projection.nodes
            if node.owner_element_id is not None
        }
    )
    whole = _adequacy_with_blueprint(blueprint, root).model_dump(mode="python")
    whole["blueprint_validation"].update(
        {
            "scope": "affected",
            "affected_projection_path": projection_path.name,
            "affected_projection_sha256": _sha256(projection_path),
            "affected_slice_fingerprint": projection.projection_fingerprint,
            "elements": [
                item
                for item in whole["blueprint_validation"]["elements"]
                if item["element_id"] in selected_ids
            ],
        }
    )
    adequacy = ValidationAdequacyPlanSpec.model_validate(whole)
    findings: list[dict[str, object]] = []

    receipt = _blueprint_validation_coverage(
        adequacy,
        base_dir=root,
        findings=findings,
    )

    assert findings == []
    assert receipt["status"] == "pass"
    assert receipt["scope"] == "affected"
    assert receipt["affected_slice_fingerprint"] == projection.projection_fingerprint
    assert receipt["governed_element_ids"] == selected_ids
