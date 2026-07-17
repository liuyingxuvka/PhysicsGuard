"""PhysicsGuard-owned validated purpose-template-pack adapter.

This module selects and materializes reviewed workflow work packages. It does
not create physical equations, run a solver, validate datasets, or issue
``audit_pass``. Existing starter-pack generators and templates remain the sole
owners of their physical content and filesystem writes.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

import yaml


MANIFEST_SCHEMA_ID = "physicsguard.purpose-template-pack-manifest.v1"
INSTANCE_SCHEMA_ID = "physicsguard.purpose-template-pack-instance.v1"
NATIVE_FAMILY_ID = "physicsguard"
BUILDER_ID = "physicsguard.purpose-pack-builder.v1"
MANIFEST_VALIDATOR_ID = "physicsguard.template-pack-manifest-validator.v1"
SELECTION_VALIDATOR_ID = "physicsguard.template-pack-selection-validator.v1"
INSTANCE_VALIDATOR_ID = "physicsguard.template-pack-instance-validator.v1"
REQUIRED_VALIDATOR_IDS = (
    MANIFEST_VALIDATOR_ID,
    SELECTION_VALIDATOR_ID,
    INSTANCE_VALIDATOR_ID,
)

BASE_NO_MATCH = "base_no_match"
SINGLE_SELECTED = "single_selected"
COMPOSED = "composed"
STRICTLY_DOMINATED_SELECTION = "strictly_dominated_selection"
AMBIGUOUS_TEMPLATE_SELECTION = "ambiguous_template_selection"
DECISION_DISPOSITIONS = (
    BASE_NO_MATCH,
    SINGLE_SELECTED,
    COMPOSED,
    STRICTLY_DOMINATED_SELECTION,
    AMBIGUOUS_TEMPLATE_SELECTION,
)

UNPROVEN_CLAIMS = (
    "physical_model_validity",
    "dataset_validity",
    "optimizer_convergence",
    "audit_pass",
    "installation_parity",
    "release_readiness",
)

_PLACEHOLDER = re.compile(r"^\{\{(input|param)\.([A-Za-z0-9_.-]+)\}\}$")
_PLACEHOLDER_FRAGMENT = re.compile(r"\{\{(?:input|param)\.[^{}]+\}\}")

_MANIFEST_KEYS = {
    "schema_id",
    "catalog_id",
    "revision",
    "digest",
    "native_family_id",
    "base_template_id",
    "templates",
    "claim_boundary",
}
_TEMPLATE_KEYS = {
    "template_id",
    "revision",
    "digest",
    "role",
    "native_family_id",
    "native_route_ids",
    "applicability",
    "provides_fragments",
    "requires_fragments",
    "owned_fields",
    "compatible_with",
    "conflicts_with",
    "dominates",
    "parameter_schema",
    "generated_artifacts",
    "referenced_assets",
    "native_builder_id",
    "native_validator_ids",
    "fixture_ids",
    "body",
    "claim_boundary",
}
_APPLICABILITY_KEYS = {
    "all_tags",
    "any_tags",
    "forbidden_tags",
    "required_inputs",
    "input_equals",
}
_PARAMETER_SPEC_KEYS = {"type", "required", "default"}
_PARAMETER_TYPES = {"string", "integer", "number", "boolean", "array", "object"}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Return the portable canonical JSON representation used for identities."""

    return json.dumps(
        _thaw(value),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return f"sha256:{sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def template_digest_from_data(data: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(data))
    payload.pop("digest", None)
    return canonical_digest(payload)


def manifest_digest_from_data(data: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(data))
    payload.pop("digest", None)
    return canonical_digest(payload)


def seal_manifest_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with deterministic template and catalog digests filled in."""

    sealed = deepcopy(dict(data))
    templates = sealed.get("templates")
    if not isinstance(templates, list):
        raise ValueError("manifest templates must be a list before sealing")
    for template in templates:
        if not isinstance(template, dict):
            raise ValueError("every manifest template must be an object before sealing")
        template["digest"] = template_digest_from_data(template)
    sealed["digest"] = manifest_digest_from_data(sealed)
    return sealed


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    message: str
    template_ids: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "template_ids": list(self.template_ids),
            "surfaces": list(self.surfaces),
        }


@dataclass(frozen=True)
class ValidationReport:
    validator_id: str
    ok: bool
    findings: tuple[ValidationFinding, ...] = ()
    claim_boundary: str = ""

    @property
    def fingerprint(self) -> str:
        return canonical_digest(
            {
                "validator_id": self.validator_id,
                "ok": self.ok,
                "findings": [finding.as_dict() for finding in self.findings],
                "claim_boundary": self.claim_boundary,
            }
        )


class TemplatePackError(ValueError):
    """Base class for deterministic template-pack rejection."""

    def __init__(
        self,
        code: str,
        message: str,
        findings: Sequence[ValidationFinding] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.findings = tuple(findings)


class ManifestValidationError(TemplatePackError):
    pass


class TemplateInstantiationError(TemplatePackError):
    pass


@dataclass(frozen=True)
class Applicability:
    all_tags: tuple[str, ...]
    any_tags: tuple[str, ...]
    forbidden_tags: tuple[str, ...]
    required_inputs: tuple[str, ...]
    input_equals: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_equals", _freeze(self.input_equals))

    def as_dict(self) -> dict[str, Any]:
        return {
            "all_tags": list(self.all_tags),
            "any_tags": list(self.any_tags),
            "forbidden_tags": list(self.forbidden_tags),
            "required_inputs": list(self.required_inputs),
            "input_equals": _thaw(self.input_equals),
        }


@dataclass(frozen=True)
class TemplatePack:
    template_id: str
    revision: str
    digest: str
    role: str
    native_family_id: str
    native_route_ids: tuple[str, ...]
    applicability: Applicability
    provides_fragments: tuple[str, ...]
    requires_fragments: tuple[str, ...]
    owned_fields: tuple[str, ...]
    compatible_with: tuple[str, ...]
    conflicts_with: tuple[str, ...]
    dominates: tuple[str, ...]
    parameter_schema: Mapping[str, Any]
    generated_artifacts: tuple[str, ...]
    referenced_assets: tuple[str, ...]
    native_builder_id: str
    native_validator_ids: tuple[str, ...]
    fixture_ids: tuple[str, ...]
    body: Mapping[str, Any]
    claim_boundary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameter_schema", _freeze(self.parameter_schema))
        object.__setattr__(self, "body", _freeze(self.body))

    @property
    def is_base(self) -> bool:
        return self.role == "base"

    @property
    def owned_surfaces(self) -> tuple[str, ...]:
        fields = (f"field:{field_id}" for field_id in self.owned_fields)
        artifacts = (f"artifact:{artifact_id}" for artifact_id in self.generated_artifacts)
        return tuple((*fields, *artifacts))

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "revision": self.revision,
            "digest": self.digest,
            "role": self.role,
            "native_family_id": self.native_family_id,
            "native_route_ids": list(self.native_route_ids),
            "applicability": self.applicability.as_dict(),
            "provides_fragments": list(self.provides_fragments),
            "requires_fragments": list(self.requires_fragments),
            "owned_fields": list(self.owned_fields),
            "compatible_with": list(self.compatible_with),
            "conflicts_with": list(self.conflicts_with),
            "dominates": list(self.dominates),
            "parameter_schema": _thaw(self.parameter_schema),
            "generated_artifacts": list(self.generated_artifacts),
            "referenced_assets": list(self.referenced_assets),
            "native_builder_id": self.native_builder_id,
            "native_validator_ids": list(self.native_validator_ids),
            "fixture_ids": list(self.fixture_ids),
            "body": _thaw(self.body),
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True)
class TemplateManifest:
    schema_id: str
    catalog_id: str
    revision: str
    digest: str
    native_family_id: str
    base_template_id: str | None
    templates: tuple[TemplatePack, ...]
    claim_boundary: str

    @property
    def by_id(self) -> Mapping[str, TemplatePack]:
        return MappingProxyType({template.template_id: template for template in self.templates})

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "catalog_id": self.catalog_id,
            "revision": self.revision,
            "digest": self.digest,
            "native_family_id": self.native_family_id,
            "base_template_id": self.base_template_id,
            "templates": [template.as_dict() for template in self.templates],
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True)
class TemplateRequest:
    request_id: str
    native_family_id: str
    native_route_id: str
    purpose_tags: tuple[str, ...] = ()
    inputs: Mapping[str, Any] = MappingProxyType({})
    requested_template_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "purpose_tags", tuple(sorted(set(self.purpose_tags))))
        object.__setattr__(self, "requested_template_ids", tuple(sorted(set(self.requested_template_ids))))
        object.__setattr__(self, "inputs", _freeze(self.inputs))

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "native_family_id": self.native_family_id,
            "native_route_id": self.native_route_id,
            "purpose_tags": list(self.purpose_tags),
            "inputs": _thaw(self.inputs),
            "requested_template_ids": list(self.requested_template_ids),
        }


@dataclass(frozen=True)
class CandidateAccounting:
    template_id: str
    status: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "status": self.status,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class TemplateDecision:
    request_fingerprint: str
    catalog_id: str
    catalog_revision: str
    catalog_digest: str
    native_route_id: str
    disposition: str
    selected_template_ids: tuple[str, ...]
    composition_order: tuple[str, ...]
    field_owner_map: tuple[tuple[str, str], ...]
    candidate_accounting: tuple[CandidateAccounting, ...]
    reasons: tuple[str, ...]
    harvest_required: bool
    blocked: bool
    selection_fingerprint: str

    @property
    def is_instantiable(self) -> bool:
        return not self.blocked and self.disposition != AMBIGUOUS_TEMPLATE_SELECTION

    def payload(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        result = {
            "request_fingerprint": self.request_fingerprint,
            "catalog_id": self.catalog_id,
            "catalog_revision": self.catalog_revision,
            "catalog_digest": self.catalog_digest,
            "native_route_id": self.native_route_id,
            "disposition": self.disposition,
            "selected_template_ids": list(self.selected_template_ids),
            "composition_order": list(self.composition_order),
            "field_owner_map": [list(item) for item in self.field_owner_map],
            "candidate_accounting": [item.as_dict() for item in self.candidate_accounting],
            "reasons": list(self.reasons),
            "harvest_required": self.harvest_required,
            "blocked": self.blocked,
        }
        if include_fingerprint:
            result["selection_fingerprint"] = self.selection_fingerprint
        return result


@dataclass(frozen=True)
class ValidationReceipt:
    validator_id: str
    status: str
    input_fingerprint: str
    finding_codes: tuple[str, ...]
    claim_boundary: str
    receipt_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "status": self.status,
            "input_fingerprint": self.input_fingerprint,
            "finding_codes": list(self.finding_codes),
            "claim_boundary": self.claim_boundary,
            "receipt_fingerprint": self.receipt_fingerprint,
        }


@dataclass(frozen=True)
class TemplateInstance:
    selection_fingerprint: str
    selected_template_ids: tuple[str, ...]
    native_builder_id: str
    parameters: Mapping[str, Any]
    artifact: Mapping[str, Any]
    artifact_fingerprint: str
    validator_receipts: tuple[ValidationReceipt, ...]
    instance_fingerprint: str
    claim_boundary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _freeze(self.parameters))
        object.__setattr__(self, "artifact", _freeze(self.artifact))

    def as_dict(self) -> dict[str, Any]:
        return {
            "selection_fingerprint": self.selection_fingerprint,
            "selected_template_ids": list(self.selected_template_ids),
            "native_builder_id": self.native_builder_id,
            "parameters": _thaw(self.parameters),
            "artifact": _thaw(self.artifact),
            "artifact_fingerprint": self.artifact_fingerprint,
            "validator_receipts": [receipt.as_dict() for receipt in self.validator_receipts],
            "instance_fingerprint": self.instance_fingerprint,
            "claim_boundary": self.claim_boundary,
        }


def _string(value: Any, field: str, findings: list[ValidationFinding]) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    findings.append(ValidationFinding("invalid_string", f"{field} must be a non-empty string"))
    return ""


def _string_tuple(value: Any, field: str, findings: list[ValidationFinding]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        findings.append(ValidationFinding("invalid_string_list", f"{field} must be a list of non-empty strings"))
        return ()
    normalized = tuple(item.strip() for item in value)
    if len(normalized) != len(set(normalized)):
        findings.append(ValidationFinding("duplicate_list_item", f"{field} contains duplicate values"))
    return normalized


def _unknown_and_missing_keys(
    data: Mapping[str, Any],
    expected: set[str],
    location: str,
    findings: list[ValidationFinding],
) -> None:
    unknown = sorted(set(data) - expected)
    missing = sorted(expected - set(data))
    if unknown:
        findings.append(ValidationFinding("unknown_fields", f"{location} has unknown fields: {', '.join(unknown)}"))
    if missing:
        findings.append(ValidationFinding("missing_fields", f"{location} is missing fields: {', '.join(missing)}"))


def _parse_applicability(data: Any, findings: list[ValidationFinding], template_id: str) -> Applicability:
    if not isinstance(data, Mapping):
        findings.append(ValidationFinding("invalid_applicability", f"{template_id} applicability must be an object"))
        data = {}
    _unknown_and_missing_keys(data, _APPLICABILITY_KEYS, f"{template_id}.applicability", findings)
    input_equals = data.get("input_equals", {})
    if not isinstance(input_equals, Mapping):
        findings.append(ValidationFinding("invalid_input_equals", f"{template_id}.input_equals must be an object"))
        input_equals = {}
    return Applicability(
        _string_tuple(data.get("all_tags", []), f"{template_id}.all_tags", findings),
        _string_tuple(data.get("any_tags", []), f"{template_id}.any_tags", findings),
        _string_tuple(data.get("forbidden_tags", []), f"{template_id}.forbidden_tags", findings),
        _string_tuple(data.get("required_inputs", []), f"{template_id}.required_inputs", findings),
        input_equals,
    )


def _parse_parameter_schema(data: Any, findings: list[ValidationFinding], template_id: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        findings.append(ValidationFinding("invalid_parameter_schema", f"{template_id}.parameter_schema must be an object"))
        return {}
    result: dict[str, Any] = {}
    for parameter_id, raw_spec in data.items():
        if not isinstance(parameter_id, str) or not parameter_id.strip() or not isinstance(raw_spec, Mapping):
            findings.append(ValidationFinding("invalid_parameter_spec", f"{template_id} has an invalid parameter declaration"))
            continue
        _unknown_and_missing_keys(raw_spec, _PARAMETER_SPEC_KEYS, f"{template_id}.parameter_schema.{parameter_id}", findings)
        parameter_type = raw_spec.get("type")
        required = raw_spec.get("required")
        if parameter_type not in _PARAMETER_TYPES:
            findings.append(ValidationFinding("invalid_parameter_type", f"{template_id}.{parameter_id} has unsupported type"))
        if not isinstance(required, bool):
            findings.append(ValidationFinding("invalid_parameter_required", f"{template_id}.{parameter_id}.required must be boolean"))
        result[parameter_id.strip()] = {
            "type": parameter_type,
            "required": required,
            "default": deepcopy(raw_spec.get("default")),
        }
    return result


def _parse_template(data: Any, index: int, findings: list[ValidationFinding]) -> TemplatePack:
    if not isinstance(data, Mapping):
        findings.append(ValidationFinding("invalid_template", f"template at index {index} must be an object"))
        data = {}
    template_id = str(data.get("template_id", f"invalid-template-{index}"))
    _unknown_and_missing_keys(data, _TEMPLATE_KEYS, template_id, findings)
    body = data.get("body", {})
    if not isinstance(body, Mapping):
        findings.append(ValidationFinding("invalid_template_body", f"{template_id}.body must be an object"))
        body = {}
    role = data.get("role")
    if role not in {"base", "template", "fragment"}:
        findings.append(ValidationFinding("invalid_template_role", f"{template_id}.role is invalid"))
        role = "template"
    return TemplatePack(
        _string(data.get("template_id"), f"template[{index}].template_id", findings),
        _string(data.get("revision"), f"{template_id}.revision", findings),
        _string(data.get("digest"), f"{template_id}.digest", findings),
        role,
        _string(data.get("native_family_id"), f"{template_id}.native_family_id", findings),
        _string_tuple(data.get("native_route_ids", []), f"{template_id}.native_route_ids", findings),
        _parse_applicability(data.get("applicability"), findings, template_id),
        _string_tuple(data.get("provides_fragments", []), f"{template_id}.provides_fragments", findings),
        _string_tuple(data.get("requires_fragments", []), f"{template_id}.requires_fragments", findings),
        _string_tuple(data.get("owned_fields", []), f"{template_id}.owned_fields", findings),
        _string_tuple(data.get("compatible_with", []), f"{template_id}.compatible_with", findings),
        _string_tuple(data.get("conflicts_with", []), f"{template_id}.conflicts_with", findings),
        _string_tuple(data.get("dominates", []), f"{template_id}.dominates", findings),
        _parse_parameter_schema(data.get("parameter_schema"), findings, template_id),
        _string_tuple(data.get("generated_artifacts", []), f"{template_id}.generated_artifacts", findings),
        _string_tuple(data.get("referenced_assets", []), f"{template_id}.referenced_assets", findings),
        _string(data.get("native_builder_id"), f"{template_id}.native_builder_id", findings),
        _string_tuple(data.get("native_validator_ids", []), f"{template_id}.native_validator_ids", findings),
        _string_tuple(data.get("fixture_ids", []), f"{template_id}.fixture_ids", findings),
        body,
        _string(data.get("claim_boundary"), f"{template_id}.claim_boundary", findings),
    )


def manifest_from_data(
    data: Mapping[str, Any],
    *,
    repository_root: Path | None = None,
    validate: bool = True,
) -> TemplateManifest:
    findings: list[ValidationFinding] = []
    if not isinstance(data, Mapping):
        raise ManifestValidationError("invalid_manifest", "manifest root must be an object")
    _unknown_and_missing_keys(data, _MANIFEST_KEYS, "manifest", findings)
    raw_templates = data.get("templates", [])
    if not isinstance(raw_templates, list):
        findings.append(ValidationFinding("invalid_templates", "manifest.templates must be a list"))
        raw_templates = []
    templates = tuple(_parse_template(item, index, findings) for index, item in enumerate(raw_templates))
    base_template_id = data.get("base_template_id")
    if base_template_id is not None and (not isinstance(base_template_id, str) or not base_template_id.strip()):
        findings.append(ValidationFinding("invalid_base_template_id", "base_template_id must be null or a non-empty string"))
        base_template_id = None
    manifest = TemplateManifest(
        _string(data.get("schema_id"), "manifest.schema_id", findings),
        _string(data.get("catalog_id"), "manifest.catalog_id", findings),
        _string(data.get("revision"), "manifest.revision", findings),
        _string(data.get("digest"), "manifest.digest", findings),
        _string(data.get("native_family_id"), "manifest.native_family_id", findings),
        base_template_id.strip() if isinstance(base_template_id, str) else None,
        templates,
        _string(data.get("claim_boundary"), "manifest.claim_boundary", findings),
    )
    if findings:
        raise ManifestValidationError("manifest_shape_invalid", "manifest shape is invalid", findings)
    if validate:
        report = validate_manifest(manifest, repository_root=repository_root)
        if not report.ok:
            raise ManifestValidationError("manifest_validation_failed", "manifest validation failed", report.findings)
    return manifest


def load_manifest(path: Path | str, *, repository_root: Path | None = None) -> TemplateManifest:
    manifest_path = Path(path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if repository_root is None:
        repository_root = manifest_path.resolve().parent.parent
    return manifest_from_data(data, repository_root=repository_root)


def default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "purpose_packs" / "physicsguard-purpose-packs.yaml"


def load_default_manifest() -> TemplateManifest:
    root = Path(__file__).resolve().parents[2]
    return load_manifest(default_manifest_path(), repository_root=root)


def validate_manifest(
    manifest: TemplateManifest,
    *,
    repository_root: Path | None = None,
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    data = manifest.as_dict()
    if manifest.schema_id != MANIFEST_SCHEMA_ID:
        findings.append(ValidationFinding("schema_id_mismatch", "manifest schema_id is not current"))
    if manifest.native_family_id != NATIVE_FAMILY_ID:
        findings.append(ValidationFinding("native_family_mismatch", "manifest native family is not PhysicsGuard"))
    if manifest.digest != manifest_digest_from_data(data):
        findings.append(ValidationFinding("catalog_digest_mismatch", "manifest digest does not match canonical content"))

    ids = tuple(template.template_id for template in manifest.templates)
    if not ids:
        findings.append(ValidationFinding("empty_catalog", "manifest has no templates"))
    if len(ids) != len(set(ids)):
        findings.append(ValidationFinding("duplicate_template_id", "manifest has duplicate template ids"))
    id_set = set(ids)
    base_templates = tuple(template.template_id for template in manifest.templates if template.is_base)
    if manifest.base_template_id is None:
        if base_templates:
            findings.append(ValidationFinding("undeclared_base_template", "base-role template exists but base_template_id is null"))
    elif manifest.base_template_id not in id_set:
        findings.append(ValidationFinding("base_template_missing", "base_template_id does not resolve"))
    elif manifest.base_template_id not in base_templates:
        findings.append(ValidationFinding("base_template_role_mismatch", "base_template_id does not identify a base-role template"))
    if len(base_templates) > 1:
        findings.append(ValidationFinding("multiple_base_templates", "manifest declares more than one base-role template"))

    for template in manifest.templates:
        raw = template.as_dict()
        if template.digest != template_digest_from_data(raw):
            findings.append(
                ValidationFinding(
                    "template_digest_mismatch",
                    f"{template.template_id} digest does not match canonical content",
                    (template.template_id,),
                )
            )
        if template.native_family_id != manifest.native_family_id:
            findings.append(
                ValidationFinding("template_family_mismatch", f"{template.template_id} family differs from catalog", (template.template_id,))
            )
        if not template.native_route_ids:
            findings.append(ValidationFinding("native_routes_missing", f"{template.template_id} has no native routes", (template.template_id,)))
        if template.native_builder_id != BUILDER_ID:
            findings.append(ValidationFinding("builder_id_mismatch", f"{template.template_id} builder id is not current", (template.template_id,)))
        if tuple(template.native_validator_ids) != REQUIRED_VALIDATOR_IDS:
            findings.append(
                ValidationFinding("validator_inventory_mismatch", f"{template.template_id} validator inventory is not exact/current", (template.template_id,))
            )
        if not template.fixture_ids:
            findings.append(ValidationFinding("fixtures_missing", f"{template.template_id} has no declared fixtures", (template.template_id,)))
        if not template.generated_artifacts:
            findings.append(
                ValidationFinding("generated_artifacts_missing", f"{template.template_id} declares no generated surfaces", (template.template_id,))
            )
        if set(template.owned_fields) != set(template.body):
            findings.append(
                ValidationFinding(
                    "owned_field_body_mismatch",
                    f"{template.template_id} owned_fields must equal its body fields",
                    (template.template_id,),
                    tuple(sorted(set(template.owned_fields) ^ set(template.body))),
                )
            )
        references = set(template.compatible_with) | set(template.conflicts_with) | set(template.dominates)
        unresolved = tuple(sorted(references - id_set))
        if unresolved:
            findings.append(
                ValidationFinding(
                    "template_reference_missing",
                    f"{template.template_id} references unknown templates",
                    (template.template_id, *unresolved),
                )
            )
        if template.template_id in references:
            findings.append(ValidationFinding("self_template_reference", f"{template.template_id} references itself", (template.template_id,)))
        if set(template.compatible_with) & set(template.conflicts_with):
            findings.append(
                ValidationFinding("compatibility_conflict_overlap", f"{template.template_id} both allows and conflicts with a peer", (template.template_id,))
            )
        if repository_root is not None:
            root = repository_root.resolve()
            for relative in template.referenced_assets:
                candidate = (root / relative).resolve()
                try:
                    candidate.relative_to(root)
                except ValueError:
                    findings.append(
                        ValidationFinding("asset_outside_repository", f"{template.template_id} asset escapes repository", (template.template_id,), (relative,))
                    )
                    continue
                if not candidate.is_file():
                    findings.append(
                        ValidationFinding("referenced_asset_missing", f"{template.template_id} asset does not exist", (template.template_id,), (relative,))
                    )

    return ValidationReport(
        MANIFEST_VALIDATOR_ID,
        not findings,
        tuple(findings),
        (
            "Validates current PhysicsGuard template manifest identity and structural/native bindings only; "
            "it does not validate physical equations, datasets, audit pass, installation, or release."
        ),
    )


def _lookup(mapping: Mapping[str, Any], dotted_key: str) -> tuple[bool, Any]:
    if dotted_key in mapping:
        return True, mapping[dotted_key]
    current: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _applicability_reasons(
    template: TemplatePack,
    request: TemplateRequest,
    *,
    domain_candidate: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    tags = set(request.purpose_tags)
    if template.native_family_id != request.native_family_id:
        reasons.append("native_family_mismatch")
    if "*" not in template.native_route_ids and request.native_route_id not in template.native_route_ids:
        reasons.append("native_route_mismatch")
    if request.requested_template_ids and template.template_id not in request.requested_template_ids:
        reasons.append("not_requested")
    if domain_candidate and template.is_base:
        reasons.append("base_reserved_for_zero_match")
    for tag in template.applicability.all_tags:
        if tag not in tags:
            reasons.append(f"missing_required_tag:{tag}")
    if template.applicability.any_tags and not tags.intersection(template.applicability.any_tags):
        reasons.append("missing_any_tag")
    for tag in template.applicability.forbidden_tags:
        if tag in tags:
            reasons.append(f"forbidden_tag:{tag}")
    for input_id in template.applicability.required_inputs:
        exists, _value = _lookup(request.inputs, input_id)
        if not exists:
            reasons.append(f"missing_required_input:{input_id}")
    for input_id, expected in template.applicability.input_equals.items():
        exists, actual = _lookup(request.inputs, input_id)
        if not exists or actual != expected:
            reasons.append(f"input_mismatch:{input_id}")
    return tuple(sorted(set(reasons)))


def _surface_owner_map(templates: Iterable[TemplatePack]) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (surface, template.template_id)
            for template in templates
            for surface in template.owned_surfaces
        )
    )


def _composition_analysis(templates: Sequence[TemplatePack]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    errors: list[str] = []
    by_id = {template.template_id: template for template in templates}
    ids = tuple(sorted(by_id))
    for index, left_id in enumerate(ids):
        left = by_id[left_id]
        for right_id in ids[index + 1 :]:
            right = by_id[right_id]
            if right_id in left.conflicts_with or left_id in right.conflicts_with:
                errors.append(f"declared_conflict:{left_id}:{right_id}")
            if right_id not in left.compatible_with or left_id not in right.compatible_with:
                errors.append(f"compatibility_missing:{left_id}:{right_id}")

    providers: dict[str, list[str]] = {}
    for template in templates:
        for fragment in template.provides_fragments:
            providers.setdefault(fragment, []).append(template.template_id)
    for fragment, provider_ids in providers.items():
        if len(provider_ids) > 1:
            errors.append(f"fragment_multiple_providers:{fragment}:{','.join(sorted(provider_ids))}")
    for template in templates:
        for fragment in template.requires_fragments:
            if fragment not in providers:
                errors.append(f"fragment_dependency_missing:{template.template_id}:{fragment}")

    surface_owners: dict[str, list[str]] = {}
    for template in templates:
        for surface in template.owned_surfaces:
            surface_owners.setdefault(surface, []).append(template.template_id)
    for surface, owner_ids in surface_owners.items():
        if len(owner_ids) > 1:
            errors.append(f"field_owner_conflict:{surface}:{','.join(sorted(owner_ids))}")

    dependencies: dict[str, set[str]] = {template_id: set() for template_id in ids}
    for template in templates:
        for fragment in template.requires_fragments:
            for provider_id in providers.get(fragment, []):
                if provider_id != template.template_id:
                    dependencies[template.template_id].add(provider_id)
    order: list[str] = []
    remaining = {template_id: set(values) for template_id, values in dependencies.items()}
    while remaining:
        ready = sorted(template_id for template_id, values in remaining.items() if not values)
        if not ready:
            errors.append(f"fragment_dependency_cycle:{','.join(sorted(remaining))}")
            break
        for template_id in ready:
            order.append(template_id)
            remaining.pop(template_id)
        for values in remaining.values():
            values.difference_update(ready)
    return tuple(order), tuple(sorted(set(errors)))


def _candidate_accounting(
    manifest: TemplateManifest,
    initial_reasons: Mapping[str, tuple[str, ...]],
    selected: Sequence[str],
    eligible_unselected_reasons: Mapping[str, tuple[str, ...]],
) -> tuple[CandidateAccounting, ...]:
    selected_set = set(selected)
    rows: list[CandidateAccounting] = []
    for template in sorted(manifest.templates, key=lambda item: item.template_id):
        if template.template_id in selected_set:
            rows.append(CandidateAccounting(template.template_id, "selected", ()))
            continue
        reasons = initial_reasons.get(template.template_id, ())
        if not reasons:
            reasons = eligible_unselected_reasons.get(template.template_id, ("not_selected",))
        rows.append(CandidateAccounting(template.template_id, "rejected", tuple(sorted(set(reasons)))))
    return tuple(rows)


def _build_decision(
    manifest: TemplateManifest,
    request: TemplateRequest,
    *,
    disposition: str,
    selected: tuple[str, ...],
    order: tuple[str, ...],
    owner_map: tuple[tuple[str, str], ...],
    accounting: tuple[CandidateAccounting, ...],
    reasons: tuple[str, ...] = (),
    harvest_required: bool = False,
    blocked: bool = False,
) -> TemplateDecision:
    base_payload = {
        "request_fingerprint": request.fingerprint,
        "catalog_id": manifest.catalog_id,
        "catalog_revision": manifest.revision,
        "catalog_digest": manifest.digest,
        "native_route_id": request.native_route_id,
        "disposition": disposition,
        "selected_template_ids": list(selected),
        "composition_order": list(order),
        "field_owner_map": [list(item) for item in owner_map],
        "candidate_accounting": [item.as_dict() for item in accounting],
        "reasons": list(reasons),
        "harvest_required": harvest_required,
        "blocked": blocked,
    }
    return TemplateDecision(
        request.fingerprint,
        manifest.catalog_id,
        manifest.revision,
        manifest.digest,
        request.native_route_id,
        disposition,
        selected,
        order,
        owner_map,
        accounting,
        reasons,
        harvest_required,
        blocked,
        canonical_digest(base_payload),
    )


def select_templates(manifest: TemplateManifest, request: TemplateRequest) -> TemplateDecision:
    """Resolve the complete frozen catalog into one finite target-owned decision."""

    report = validate_manifest(manifest)
    if not report.ok:
        raise ManifestValidationError("manifest_validation_failed", "manifest validation failed", report.findings)

    initial_reasons = {
        template.template_id: _applicability_reasons(template, request, domain_candidate=True)
        for template in manifest.templates
    }
    eligible = tuple(
        template
        for template in manifest.templates
        if not template.is_base and not initial_reasons[template.template_id]
    )

    if not eligible:
        base = manifest.by_id.get(manifest.base_template_id or "")
        base_reasons = (
            _applicability_reasons(base, request, domain_candidate=False)
            if base is not None
            else ("no_approved_base",)
        )
        if base is not None and not base_reasons:
            initial_reasons = dict(initial_reasons)
            initial_reasons[base.template_id] = ()
            accounting = _candidate_accounting(manifest, initial_reasons, (base.template_id,), {})
            return _build_decision(
                manifest,
                request,
                disposition=BASE_NO_MATCH,
                selected=(base.template_id,),
                order=(base.template_id,),
                owner_map=_surface_owner_map((base,)),
                accounting=accounting,
                reasons=("no_domain_match", "harvest_review_required"),
                harvest_required=True,
            )
        reasons = tuple(sorted(set(("no_domain_match", *base_reasons))))
        accounting = _candidate_accounting(
            manifest,
            initial_reasons,
            (),
            {template.template_id: reasons for template in manifest.templates if not initial_reasons[template.template_id]},
        )
        return _build_decision(
            manifest,
            request,
            disposition=AMBIGUOUS_TEMPLATE_SELECTION,
            selected=(),
            order=(),
            owner_map=(),
            accounting=accounting,
            reasons=reasons,
            harvest_required=True,
            blocked=True,
        )

    if len(eligible) == 1:
        selected_template = eligible[0]
        selected = (selected_template.template_id,)
        accounting = _candidate_accounting(manifest, initial_reasons, selected, {})
        return _build_decision(
            manifest,
            request,
            disposition=SINGLE_SELECTED,
            selected=selected,
            order=selected,
            owner_map=_surface_owner_map(eligible),
            accounting=accounting,
        )

    eligible_ids = {template.template_id for template in eligible}
    dominators = tuple(
        template
        for template in eligible
        if eligible_ids - {template.template_id} <= set(template.dominates)
    )
    if len(dominators) == 1:
        dominator = dominators[0]
        selected = (dominator.template_id,)
        unselected_reasons = {
            template.template_id: (f"strictly_dominated_by:{dominator.template_id}",)
            for template in eligible
            if template.template_id != dominator.template_id
        }
        accounting = _candidate_accounting(manifest, initial_reasons, selected, unselected_reasons)
        return _build_decision(
            manifest,
            request,
            disposition=STRICTLY_DOMINATED_SELECTION,
            selected=selected,
            order=selected,
            owner_map=_surface_owner_map((dominator,)),
            accounting=accounting,
            reasons=("target_authored_strict_dominance",),
        )

    order, composition_errors = _composition_analysis(eligible)
    if not composition_errors:
        selected = tuple(order)
        accounting = _candidate_accounting(manifest, initial_reasons, selected, {})
        return _build_decision(
            manifest,
            request,
            disposition=COMPOSED,
            selected=selected,
            order=selected,
            owner_map=_surface_owner_map(manifest.by_id[template_id] for template_id in selected),
            accounting=accounting,
        )

    ambiguous_reasons = tuple(sorted(set(("ambiguous_template_selection", *composition_errors))))
    accounting = _candidate_accounting(
        manifest,
        initial_reasons,
        (),
        {template.template_id: ambiguous_reasons for template in eligible},
    )
    return _build_decision(
        manifest,
        request,
        disposition=AMBIGUOUS_TEMPLATE_SELECTION,
        selected=(),
        order=(),
        owner_map=(),
        accounting=accounting,
        reasons=ambiguous_reasons,
        blocked=True,
    )


def validate_selection(
    manifest: TemplateManifest,
    request: TemplateRequest,
    decision: TemplateDecision,
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    if decision.disposition not in DECISION_DISPOSITIONS:
        findings.append(ValidationFinding("unknown_disposition", "selection disposition is not current"))
    if decision.request_fingerprint != request.fingerprint:
        findings.append(ValidationFinding("request_fingerprint_mismatch", "selection does not bind the current request"))
    if decision.catalog_digest != manifest.digest:
        findings.append(ValidationFinding("catalog_fingerprint_mismatch", "selection does not bind the current catalog"))
    ids = tuple(row.template_id for row in decision.candidate_accounting)
    expected_ids = tuple(sorted(template.template_id for template in manifest.templates))
    if ids != expected_ids:
        findings.append(ValidationFinding("candidate_accounting_incomplete", "selection does not account for the complete catalog"))
    if any(row.status not in {"selected", "rejected"} for row in decision.candidate_accounting):
        findings.append(ValidationFinding("candidate_status_invalid", "candidate status must be selected or rejected"))
    if any(row.status == "rejected" and not row.reasons for row in decision.candidate_accounting):
        findings.append(ValidationFinding("candidate_rejection_reason_missing", "every rejected candidate needs a reason"))
    if decision.blocked and decision.is_instantiable:
        findings.append(ValidationFinding("blocked_selection_instantiable", "blocked decision appears instantiable"))
    if not decision.blocked and not decision.selected_template_ids:
        findings.append(ValidationFinding("successful_selection_empty", "successful decision has no selected templates"))
    surfaces = tuple(surface for surface, _owner in decision.field_owner_map)
    if len(surfaces) != len(set(surfaces)):
        findings.append(ValidationFinding("field_owner_collision", "selection field-owner map has duplicate surfaces", surfaces=surfaces))
    expected = select_templates(manifest, request)
    if decision.selection_fingerprint != expected.selection_fingerprint or decision.payload() != expected.payload():
        findings.append(ValidationFinding("selection_receipt_stale", "selection receipt differs from current deterministic decision"))
    return ValidationReport(
        SELECTION_VALIDATOR_ID,
        not findings,
        tuple(findings),
        (
            "Validates complete deterministic candidate accounting and ownership only; it does not validate "
            "physical semantics, generated model correctness, audit pass, installation, or release."
        ),
    )


def _parameter_value_matches(value: Any, type_id: str) -> bool:
    if type_id == "string":
        return isinstance(value, str)
    if type_id == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_id == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_id == "boolean":
        return isinstance(value, bool)
    if type_id == "array":
        return isinstance(value, (list, tuple))
    if type_id == "object":
        return isinstance(value, Mapping)
    return False


def _resolve_parameters(
    templates: Sequence[TemplatePack],
    supplied: Mapping[str, Any],
) -> Mapping[str, Any]:
    schemas: dict[str, Mapping[str, Any]] = {}
    for template in templates:
        for parameter_id, spec in template.parameter_schema.items():
            if parameter_id in schemas:
                raise TemplateInstantiationError(
                    "parameter_owner_conflict",
                    f"parameter {parameter_id} is declared by more than one selected template",
                )
            schemas[parameter_id] = spec
    extra = sorted(set(supplied) - set(schemas))
    if extra:
        raise TemplateInstantiationError("undeclared_parameters", f"undeclared parameters: {', '.join(extra)}")
    resolved: dict[str, Any] = {}
    for parameter_id, spec in schemas.items():
        if parameter_id in supplied:
            value = supplied[parameter_id]
        else:
            value = spec.get("default")
            if spec.get("required") and value is None:
                raise TemplateInstantiationError("required_parameter_missing", f"required parameter missing: {parameter_id}")
        if not _parameter_value_matches(value, str(spec.get("type"))):
            raise TemplateInstantiationError("parameter_type_mismatch", f"parameter {parameter_id} has the wrong type")
        resolved[parameter_id] = _thaw(value)
    return _freeze(resolved)


def _render(value: Any, inputs: Mapping[str, Any], parameters: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _render(item, inputs, parameters) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_render(item, inputs, parameters) for item in value]
    if isinstance(value, str):
        match = _PLACEHOLDER.fullmatch(value)
        if match:
            source, key = match.groups()
            exists, resolved = _lookup(inputs if source == "input" else parameters, key)
            return deepcopy(_thaw(resolved)) if exists else value
    return deepcopy(value)


def scan_unresolved_placeholders(value: Any, *, path: str = "$") -> tuple[str, ...]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            findings.extend(scan_unresolved_placeholders(item, path=f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(scan_unresolved_placeholders(item, path=f"{path}[{index}]"))
    elif isinstance(value, str) and _PLACEHOLDER_FRAGMENT.search(value):
        findings.append(path)
    return tuple(findings)


def _validation_receipt(report: ValidationReport, input_fingerprint: str) -> ValidationReceipt:
    payload = {
        "validator_id": report.validator_id,
        "status": "passed" if report.ok else "failed",
        "input_fingerprint": input_fingerprint,
        "finding_codes": [finding.code for finding in report.findings],
        "claim_boundary": report.claim_boundary,
        "report_fingerprint": report.fingerprint,
    }
    return ValidationReceipt(
        report.validator_id,
        "passed" if report.ok else "failed",
        input_fingerprint,
        tuple(finding.code for finding in report.findings),
        report.claim_boundary,
        canonical_digest(payload),
    )


def validate_instance_artifact(
    manifest: TemplateManifest,
    request: TemplateRequest,
    decision: TemplateDecision,
    artifact: Mapping[str, Any],
    artifact_fingerprint: str,
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    if artifact_fingerprint != canonical_digest(artifact):
        findings.append(ValidationFinding("artifact_fingerprint_mismatch", "artifact fingerprint is stale"))
    if artifact.get("schema_id") != INSTANCE_SCHEMA_ID:
        findings.append(ValidationFinding("instance_schema_mismatch", "instance schema id is not current"))
    if artifact.get("selection_fingerprint") != decision.selection_fingerprint:
        findings.append(ValidationFinding("instance_selection_mismatch", "instance does not bind the selection receipt"))
    if tuple(artifact.get("selected_template_ids", ())) != decision.selected_template_ids:
        findings.append(ValidationFinding("instance_template_mismatch", "instance selected ids differ from decision"))
    if artifact.get("native_family_id") != request.native_family_id or artifact.get("native_route_id") != request.native_route_id:
        findings.append(ValidationFinding("instance_native_route_mismatch", "instance does not bind the native family/route"))
    if scan_unresolved_placeholders(artifact):
        findings.append(ValidationFinding("unresolved_placeholders", "instance contains unresolved placeholders"))
    safety = artifact.get("safety")
    if not isinstance(safety, Mapping):
        findings.append(ValidationFinding("safety_contract_missing", "instance safety contract is missing"))
    else:
        for field_id in ("si_units_required", "assumptions_required", "native_validation_required"):
            if safety.get(field_id) is not True:
                findings.append(ValidationFinding("safety_flag_missing", f"instance safety flag is not true: {field_id}"))
        boundaries = safety.get("claim_boundaries")
        if not isinstance(boundaries, Mapping) or set(boundaries) != set(decision.selected_template_ids):
            findings.append(ValidationFinding("claim_boundaries_incomplete", "instance claim boundaries do not cover selected templates"))
        elif any(not isinstance(value, str) or not value.strip() for value in boundaries.values()):
            findings.append(ValidationFinding("claim_boundary_empty", "instance contains an empty claim boundary"))
        if tuple(safety.get("unproven_claims", ())) != UNPROVEN_CLAIMS:
            findings.append(ValidationFinding("unproven_claims_mismatch", "instance does not preserve the explicit non-proof boundary"))
    expected_surfaces = tuple(surface for surface, _owner in decision.field_owner_map)
    if tuple(artifact.get("owned_surfaces", ())) != expected_surfaces:
        findings.append(ValidationFinding("instance_owner_map_mismatch", "instance surfaces differ from selection owner map"))
    return ValidationReport(
        INSTANCE_VALIDATOR_ID,
        not findings,
        tuple(findings),
        (
            "Validates rendered work-package structure, fingerprints, placeholders, and PhysicsGuard safety flags only; "
            "physical truth, dataset adequacy, optimizer convergence, audit pass, installation, and release remain unproven."
        ),
    )


def instantiate_template_pack(
    manifest: TemplateManifest,
    request: TemplateRequest,
    decision: TemplateDecision,
    *,
    parameters: Mapping[str, Any] | None = None,
) -> TemplateInstance:
    """Materialize one validated in-memory work package from a current decision."""

    manifest_report = validate_manifest(manifest)
    if not manifest_report.ok:
        raise ManifestValidationError("manifest_validation_failed", "manifest validation failed", manifest_report.findings)
    selection_report = validate_selection(manifest, request, decision)
    if not selection_report.ok:
        raise TemplateInstantiationError("selection_validation_failed", "selection receipt is not current", selection_report.findings)
    if not decision.is_instantiable:
        raise TemplateInstantiationError("selection_blocked", "ambiguous or blocked selection cannot instantiate")

    templates = tuple(manifest.by_id[template_id] for template_id in decision.composition_order)
    resolved_parameters = _resolve_parameters(templates, parameters or {})
    fields: dict[str, Any] = {}
    for template in templates:
        rendered = _render(template.body, request.inputs, resolved_parameters)
        for field_id, value in rendered.items():
            if field_id in fields:
                raise TemplateInstantiationError("field_owner_conflict", f"field {field_id} was rendered twice")
            fields[field_id] = value

    artifact = {
        "schema_id": INSTANCE_SCHEMA_ID,
        "request_id": request.request_id,
        "request_fingerprint": request.fingerprint,
        "native_family_id": request.native_family_id,
        "native_route_id": request.native_route_id,
        "selection_fingerprint": decision.selection_fingerprint,
        "selected_template_ids": list(decision.selected_template_ids),
        "composition_order": list(decision.composition_order),
        "owned_surfaces": [surface for surface, _owner in decision.field_owner_map],
        "field_owner_map": [list(item) for item in decision.field_owner_map],
        "fields": fields,
        "referenced_assets": sorted({asset for template in templates for asset in template.referenced_assets}),
        "generated_artifacts": sorted({surface for template in templates for surface in template.generated_artifacts}),
        "safety": {
            "si_units_required": True,
            "assumptions_required": True,
            "native_validation_required": True,
            "claim_boundaries": {template.template_id: template.claim_boundary for template in templates},
            "unproven_claims": list(UNPROVEN_CLAIMS),
        },
    }
    unresolved = scan_unresolved_placeholders(artifact)
    if unresolved:
        raise TemplateInstantiationError(
            "unresolved_placeholders",
            f"unresolved placeholders remain at: {', '.join(unresolved)}",
        )
    artifact_fingerprint = canonical_digest(artifact)
    instance_report = validate_instance_artifact(
        manifest,
        request,
        decision,
        artifact,
        artifact_fingerprint,
    )
    if not instance_report.ok:
        raise TemplateInstantiationError("instance_validation_failed", "instance validation failed", instance_report.findings)

    receipts = (
        _validation_receipt(manifest_report, manifest.digest),
        _validation_receipt(selection_report, decision.selection_fingerprint),
        _validation_receipt(instance_report, artifact_fingerprint),
    )
    fingerprint_payload = {
        "selection_fingerprint": decision.selection_fingerprint,
        "selected_template_ids": list(decision.selected_template_ids),
        "native_builder_id": BUILDER_ID,
        "parameters": _thaw(resolved_parameters),
        "artifact_fingerprint": artifact_fingerprint,
        "validator_receipts": [receipt.as_dict() for receipt in receipts],
    }
    return TemplateInstance(
        decision.selection_fingerprint,
        decision.selected_template_ids,
        BUILDER_ID,
        resolved_parameters,
        artifact,
        artifact_fingerprint,
        receipts,
        canonical_digest(fingerprint_payload),
        (
            "A valid instance proves only current deterministic selection, rendering, and PhysicsGuard adapter validation. "
            "It does not prove physical model validity, dataset adequacy, optimizer convergence, audit_pass, installation, or release."
        ),
    )


__all__ = [
    "AMBIGUOUS_TEMPLATE_SELECTION",
    "BASE_NO_MATCH",
    "BUILDER_ID",
    "COMPOSED",
    "INSTANCE_SCHEMA_ID",
    "ManifestValidationError",
    "SINGLE_SELECTED",
    "STRICTLY_DOMINATED_SELECTION",
    "TemplateDecision",
    "TemplateInstance",
    "TemplateInstantiationError",
    "TemplateManifest",
    "TemplatePack",
    "TemplateRequest",
    "ValidationFinding",
    "ValidationReport",
    "canonical_digest",
    "canonical_json",
    "default_manifest_path",
    "instantiate_template_pack",
    "load_default_manifest",
    "load_manifest",
    "manifest_digest_from_data",
    "manifest_from_data",
    "scan_unresolved_placeholders",
    "seal_manifest_data",
    "select_templates",
    "template_digest_from_data",
    "validate_instance_artifact",
    "validate_manifest",
    "validate_selection",
]
