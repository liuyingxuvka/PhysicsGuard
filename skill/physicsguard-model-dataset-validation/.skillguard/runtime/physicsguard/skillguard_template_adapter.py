"""PhysicsGuard-owned projection into SkillGuard's neutral template protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .template_packs import (
    INSTANCE_VALIDATOR_ID,
    MANIFEST_VALIDATOR_ID,
    NATIVE_FAMILY_ID,
    SELECTION_VALIDATOR_ID,
    TemplateManifest,
    TemplatePack,
    TemplateRequest,
    _applicability_reasons,
    canonical_digest,
    load_default_manifest,
    select_templates,
    validate_selection,
)


PROJECTION_SCHEMA = "skillguard.target_template_projection.v1"
NATIVE_OWNER_ID = "physicsguard.purpose-pack-selector.v1"


def _json_parameter_schema(template: TemplatePack) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, raw in template.parameter_schema.items():
        spec = dict(raw)
        property_spec: dict[str, Any] = {"type": spec["type"]}
        if "default" in spec:
            property_spec["default"] = spec["default"]
        properties[str(name)] = property_spec
        if spec.get("required") is True:
            required.append(str(name))
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
        "additionalProperties": False,
    }


def _predicate_ids(template: TemplatePack) -> list[str]:
    rows = [f"predicate:physicsguard:family:{template.native_family_id}"]
    rows.extend(f"predicate:physicsguard:all-tag:{tag}" for tag in template.applicability.all_tags)
    if template.applicability.any_tags:
        rows.append("predicate:physicsguard:any-tag:" + ",".join(template.applicability.any_tags))
    rows.extend(
        f"predicate:physicsguard:required-input:{field}"
        for field in template.applicability.required_inputs
    )
    rows.extend(
        f"predicate:physicsguard:input-equals:{field}:{canonical_digest(value)}"
        for field, value in template.applicability.input_equals.items()
    )
    return rows


def _dependency_template_ids(manifest: TemplateManifest, template: TemplatePack) -> list[str]:
    providers = {
        fragment: candidate.template_id
        for candidate in manifest.templates
        for fragment in candidate.provides_fragments
    }
    return sorted({providers[fragment] for fragment in template.requires_fragments})


def build_skillguard_template_projection(
    request: TemplateRequest,
    *,
    target_id: str,
    manifest: TemplateManifest | None = None,
) -> dict[str, Any]:
    """Use the current native selector, then project complete applicability."""

    if not isinstance(target_id, str) or not target_id.strip():
        raise ValueError("target_id must be a non-empty string")
    current = manifest or load_default_manifest()
    decision = select_templates(current, request)
    selection_validation = validate_selection(current, request, decision)
    if not selection_validation.ok:
        raise ValueError("PhysicsGuard native selection is not current")
    source_identity = canonical_digest(
        {
            "adapter": Path(__file__).read_text(encoding="utf-8"),
            "native_catalog_digest": current.digest,
        }
    )
    templates: list[dict[str, Any]] = []
    applicability: list[dict[str, Any]] = []
    for order, template in enumerate(current.templates):
        is_base = template.is_base
        predicate_ids = _predicate_ids(template)
        forbidden_ids = [
            f"forbidden:physicsguard:tag:{tag}"
            for tag in template.applicability.forbidden_tags
        ]
        domain_reasons = _applicability_reasons(
            template,
            request,
            domain_candidate=not is_base,
        )
        eligible = not domain_reasons
        failure_ids = tuple(
            f"failure:{template.template_id}:{validator_id}"
            for validator_id in template.native_validator_ids
        )
        templates.append(
            {
                "schema_version": "skillguard.template_manifest.v1",
                "template_id": template.template_id,
                "revision": template.revision,
                "template_kind": "base" if is_base else ("fragment" if template.role == "fragment" else "profile"),
                "native_owner_id": NATIVE_OWNER_ID,
                "family_id": NATIVE_FAMILY_ID,
                "route_ids": sorted(
                    set(template.native_route_ids)
                    if "*" not in template.native_route_ids
                    else {request.native_route_id}
                ),
                "applicability_predicate_ids": predicate_ids,
                "forbidden_condition_ids": forbidden_ids,
                "dependencies": _dependency_template_ids(current, template),
                "compatible_with": list(template.compatible_with),
                "conflicts_with": list(template.conflicts_with),
                "dominates_template_ids": list(template.dominates),
                "composable": bool(template.role == "fragment"),
                "composition_order": order,
                "is_validated_base": is_base,
                "field_ownership": list(template.owned_surfaces),
                "parameter_schema": _json_parameter_schema(template),
                "artifacts": [
                    {
                        "artifact_id": f"artifact:{template.template_id}:{index}",
                        "path_template": path,
                        "content_template_hash": template.digest,
                    }
                    for index, path in enumerate(template.generated_artifacts, start=1)
                ],
                "builder": {
                    "builder_id": template.native_builder_id,
                    "entrypoint": "physicsguard.template_packs:instantiate_template_pack",
                    "content_hash": source_identity,
                },
                "validators": [
                    {
                        "validator_id": validator_id,
                        "check_id": f"check:physicsguard:{validator_id}",
                        "evidence_domain": "physicsguard-template-pack",
                        "content_hash": source_identity,
                    }
                    for validator_id in template.native_validator_ids
                ],
                "prompt_fragments": [],
                "protected_failure_ids": list(failure_ids),
                "fixtures": {
                    "known_good_ids": list(template.fixture_ids),
                    "known_bad_by_failure": {
                        failure_id: [f"fixture:physicsguard:bad:{failure_id}"]
                        for failure_id in failure_ids
                    },
                    "ambiguity_ids": ["fixture:physicsguard:ambiguous-selection"],
                    "stale_ids": ["fixture:physicsguard:stale-catalog"],
                },
                "claim_boundary": template.claim_boundary,
            }
        )
        applicability.append(
            {
                "template_id": template.template_id,
                "eligible": eligible,
                "predicate_evidence_ids": (
                    [
                        f"evidence:physicsguard:predicate:{decision.selection_fingerprint}:{index}"
                        for index, _item in enumerate(predicate_ids, start=1)
                    ]
                    if eligible
                    else []
                ),
                "forbidden_clearance_evidence_ids": (
                    [
                        f"evidence:physicsguard:forbidden-clear:{decision.selection_fingerprint}:{index}"
                        for index, _item in enumerate(forbidden_ids, start=1)
                    ]
                    if eligible
                    else []
                ),
                "reasons": [] if eligible else list(domain_reasons),
            }
        )
    return {
        "schema_version": PROJECTION_SCHEMA,
        "target_id": target_id.strip(),
        "native_owner_id": NATIVE_OWNER_ID,
        "family_id": NATIVE_FAMILY_ID,
        "route_id": request.native_route_id,
        "request_fingerprint": request.fingerprint,
        "catalog": {
            "schema_version": "skillguard.template_catalog.v1",
            "catalog_id": current.catalog_id,
            "revision": current.revision,
            "native_owner_id": NATIVE_OWNER_ID,
            "family_id": NATIVE_FAMILY_ID,
            "base_template_id": current.base_template_id,
            "templates": templates,
            "harvest_policy": {
                "required": True,
                "allowed_dispositions": ["reused", "created", "not_harvestable"],
            },
            "claim_boundary": current.claim_boundary,
        },
        "applicability_results": applicability,
        "claim_boundary": (
            "PhysicsGuard owns physical-purpose routing, applicability, builders, and validators. "
            "SkillGuard may seal and supervise this projection but cannot establish physical truth, "
            "dataset adequacy, audit_pass, installation, or release."
        ),
    }


__all__ = [
    "NATIVE_OWNER_ID",
    "PROJECTION_SCHEMA",
    "build_skillguard_template_projection",
]
