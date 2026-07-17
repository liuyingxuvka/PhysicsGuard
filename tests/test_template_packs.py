from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from physicsguard.template_packs import (
    AMBIGUOUS_TEMPLATE_SELECTION,
    ManifestValidationError,
    TemplateInstantiationError,
    TemplateRequest,
    canonical_digest,
    instantiate_template_pack,
    load_default_manifest,
    manifest_from_data,
    seal_manifest_data,
    select_templates,
    validate_manifest,
    validate_selection,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "purpose_packs" / "physicsguard-purpose-packs.yaml"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "template_packs"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def request_from_data(data: dict) -> TemplateRequest:
    return TemplateRequest(
        data["request_id"],
        data["native_family_id"],
        data["native_route_id"],
        tuple(data.get("purpose_tags", ())),
        data.get("inputs", {}),
        tuple(data.get("requested_template_ids", ())),
    )


def apply_catalog_mutation(raw: dict, mutation: dict) -> dict:
    updated = deepcopy(raw)
    updated["base_template_id"] = mutation.get("base_template_id", updated["base_template_id"])
    remove_ids = set(mutation.get("remove_template_ids", ()))
    updated["templates"] = [
        template for template in updated["templates"] if template["template_id"] not in remove_ids
    ]
    template_updates = mutation.get("template_updates", {})
    for template in updated["templates"]:
        patch_data = template_updates.get(template["template_id"])
        if patch_data:
            template.update(deepcopy(patch_data))
    return seal_manifest_data(updated)


@pytest.mark.parametrize(
    "case",
    load_yaml(FIXTURE_ROOT / "known-good.yaml")["cases"],
    ids=lambda case: case["case_id"],
)
def test_known_good_template_pack_cases_are_current_and_deterministic(case: dict) -> None:
    manifest = load_default_manifest()
    request = request_from_data(case["request"])

    first_decision = select_templates(manifest, request)
    second_decision = select_templates(manifest, request)

    assert first_decision.disposition == case["expected_disposition"]
    assert first_decision.selected_template_ids == tuple(case["expected_template_ids"])
    assert first_decision.selection_fingerprint == second_decision.selection_fingerprint
    assert len(first_decision.candidate_accounting) == len(manifest.templates)
    assert all(row.status in {"selected", "rejected"} for row in first_decision.candidate_accounting)
    assert all(row.status == "selected" or row.reasons for row in first_decision.candidate_accounting)

    first_instance = instantiate_template_pack(
        manifest,
        request,
        first_decision,
        parameters=case.get("parameters", {}),
    )
    second_instance = instantiate_template_pack(
        manifest,
        request,
        second_decision,
        parameters=case.get("parameters", {}),
    )

    assert first_instance.artifact_fingerprint == second_instance.artifact_fingerprint
    assert first_instance.instance_fingerprint == second_instance.instance_fingerprint
    assert [receipt.status for receipt in first_instance.validator_receipts] == ["passed", "passed", "passed"]
    assert first_instance.artifact["safety"]["native_validation_required"] is True
    assert "audit_pass" in first_instance.artifact["safety"]["unproven_claims"]


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in load_yaml(FIXTURE_ROOT / "known-bad.yaml")["cases"]
        if case["kind"] == "blocked_decision"
    ],
    ids=lambda case: case["case_id"],
)
def test_known_bad_selection_cases_block_without_alternate_success(case: dict) -> None:
    raw = load_yaml(MANIFEST_PATH)
    manifest = manifest_from_data(
        apply_catalog_mutation(raw, case["mutation"]),
        repository_root=ROOT,
    )
    request = request_from_data(case["request"])

    decision = select_templates(manifest, request)

    assert decision.disposition == case["expected_disposition"] == AMBIGUOUS_TEMPLATE_SELECTION
    assert decision.blocked is True
    assert decision.selected_template_ids == ()
    assert any(reason.startswith(case["expected_reason_prefix"]) for reason in decision.reasons)
    with pytest.raises(TemplateInstantiationError) as exc_info:
        instantiate_template_pack(manifest, request, decision)
    assert exc_info.value.code == "selection_blocked"


def test_stale_manifest_fixture_is_rejected_before_selection() -> None:
    case = next(
        case
        for case in load_yaml(FIXTURE_ROOT / "known-bad.yaml")["cases"]
        if case["kind"] == "stale_manifest"
    )
    raw = load_yaml(MANIFEST_PATH)
    target = next(
        template for template in raw["templates"] if template["template_id"] == case["mutation"]["template_id"]
    )
    target["body"].update(case["mutation"]["body_update"])

    with pytest.raises(ManifestValidationError) as exc_info:
        manifest_from_data(raw, repository_root=ROOT)

    assert case["expected_finding_code"] in {finding.code for finding in exc_info.value.findings}


def test_unresolved_placeholder_fixture_is_rejected_before_instance_receipt() -> None:
    case = next(
        case
        for case in load_yaml(FIXTURE_ROOT / "known-bad.yaml")["cases"]
        if case["kind"] == "instantiation_error"
    )
    raw = load_yaml(MANIFEST_PATH)
    manifest = manifest_from_data(
        apply_catalog_mutation(raw, case["mutation"]),
        repository_root=ROOT,
    )
    request = request_from_data(case["request"])
    decision = select_templates(manifest, request)

    with pytest.raises(TemplateInstantiationError) as exc_info:
        instantiate_template_pack(
            manifest,
            request,
            decision,
            parameters=case.get("parameters", {}),
        )

    assert exc_info.value.code == case["expected_error_code"]


def test_manifest_reload_and_canonical_identity_are_stable() -> None:
    raw = load_yaml(MANIFEST_PATH)
    manifest = load_default_manifest()
    reloaded = manifest_from_data(deepcopy(raw), repository_root=ROOT)

    assert manifest.as_dict() == reloaded.as_dict()
    assert manifest.digest == reloaded.digest
    assert seal_manifest_data(raw) == raw
    assert validate_manifest(manifest, repository_root=ROOT).ok is True


def test_changed_request_stales_selection_receipt() -> None:
    manifest = load_default_manifest()
    original = TemplateRequest(
        "same-request-id",
        "physicsguard",
        "route:physicsguard-model-understanding-preflight:review",
        ("model-understanding",),
        {"model_id": "model-a"},
    )
    changed = TemplateRequest(
        "same-request-id",
        "physicsguard",
        "route:physicsguard-model-understanding-preflight:review",
        ("model-understanding",),
        {"model_id": "model-b"},
    )
    decision = select_templates(manifest, original)

    report = validate_selection(manifest, changed, decision)

    assert report.ok is False
    assert {finding.code for finding in report.findings} >= {
        "request_fingerprint_mismatch",
        "selection_receipt_stale",
    }
    with pytest.raises(TemplateInstantiationError) as exc_info:
        instantiate_template_pack(manifest, changed, decision)
    assert exc_info.value.code == "selection_validation_failed"


def test_adapter_does_not_write_or_invoke_existing_asset_paths() -> None:
    manifest = load_default_manifest()
    request = TemplateRequest(
        "no-write",
        "physicsguard",
        "route:physicsguard-model-understanding-preflight:review",
        ("model-understanding",),
        {"model_id": "model-no-write"},
    )

    with (
        patch.object(Path, "write_text", side_effect=AssertionError("adapter attempted write_text")),
        patch.object(Path, "write_bytes", side_effect=AssertionError("adapter attempted write_bytes")),
        patch.object(Path, "mkdir", side_effect=AssertionError("adapter attempted mkdir")),
    ):
        decision = select_templates(manifest, request)
        instance = instantiate_template_pack(
            manifest,
            request,
            decision,
            parameters={"detail_level": "coarse-to-fine"},
        )

    assert instance.artifact["fields"]["workflow_kind"] == "physicsguard_model_understanding_preflight"
    assert canonical_digest(instance.artifact) == instance.artifact_fingerprint


def test_parameter_type_mismatch_fails_closed() -> None:
    manifest = load_default_manifest()
    request = TemplateRequest(
        "bad-parameter",
        "physicsguard",
        "route:physicsguard-model-understanding-preflight:review",
        ("model-understanding",),
        {"model_id": "model-parameter"},
    )
    decision = select_templates(manifest, request)

    with pytest.raises(TemplateInstantiationError) as exc_info:
        instantiate_template_pack(
            manifest,
            request,
            decision,
            parameters={"detail_level": 3},
        )

    assert exc_info.value.code == "parameter_type_mismatch"
