"""Schemas for hierarchical and progressive PhysicsGuard audits."""

from __future__ import annotations

import json
import math
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from physicsguard.schema.system_spec import SystemSpec
from physicsguard.schema.variable import ensure_non_empty, is_qualified_variable_name


SUPPORTED_RESIDUAL_ROLES = frozenset(
    {"equation", "connection", "boundary", "assumption", "soft_check", "post_check"}
)


class AuditBlockSpec(BaseModel):
    """Logical subsystem or block used for hierarchical residual roll-up."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: Optional[str] = None
    level: int = 0
    parent_id: Optional[str] = None
    description: Optional[str] = None
    components: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    required_variables: list[str] = Field(default_factory=list)
    optional_variables: list[str] = Field(default_factory=list)
    required_parameters: list[str] = Field(default_factory=list)
    optional_parameters: list[str] = Field(default_factory=list)
    expected_residual_keys: list[str] = Field(default_factory=list)
    refinement_template_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_valid(cls, value: str) -> str:
        ensure_non_empty(value, "block id")
        if any(character.isspace() for character in value):
            raise ValueError("block id cannot contain whitespace")
        return value

    @field_validator("parent_id")
    @classmethod
    def _parent_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            ensure_non_empty(value, "parent_id")
            if any(character.isspace() for character in value):
                raise ValueError("parent_id cannot contain whitespace")
        return value

    @field_validator("level")
    @classmethod
    def _level_valid(cls, value: int) -> int:
        if value < 0:
            raise ValueError("block level must be nonnegative")
        return value

    @field_validator("components", "tags", "expected_residual_keys", "refinement_template_ids")
    @classmethod
    def _non_empty_string_list(cls, values: list[str], info) -> list[str]:
        normalized: list[str] = []
        for item in values:
            ensure_non_empty(item, info.field_name)
            normalized.append(item.strip() if info.field_name == "tags" else item)
        return normalized

    @field_validator("required_variables", "optional_variables")
    @classmethod
    def _variable_names_valid(cls, values: list[str]) -> list[str]:
        for item in values:
            ensure_non_empty(item, "variable name")
            if "." in item and not is_qualified_variable_name(item):
                raise ValueError("qualified variable names must use component.variable format")
        return values

    @field_validator("required_parameters", "optional_parameters")
    @classmethod
    def _parameter_names_valid(cls, values: list[str]) -> list[str]:
        for item in values:
            ensure_non_empty(item, "parameter name")
        return values

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "AuditBlockSpec":
        _ensure_json_serializable(self.metadata, "metadata")
        return self


class RefinementRuleSpec(BaseModel):
    """Rule that recommends deeper templates for suspicious blocks."""

    model_config = ConfigDict(extra="forbid")

    id: str
    block_id: Optional[str] = None
    trigger_diagnostic_keys: list[str] = Field(default_factory=list)
    trigger_roles: list[str] = Field(default_factory=list)
    score_threshold: float = 1.0
    confidence_min: Optional[float] = None
    next_template_ids: list[str] = Field(default_factory=list)
    next_required_variables: list[str] = Field(default_factory=list)
    next_required_parameters: list[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    priority: int = 0

    @field_validator("id")
    @classmethod
    def _id_valid(cls, value: str) -> str:
        return ensure_non_empty(value, "refinement rule id")

    @field_validator("block_id")
    @classmethod
    def _block_id_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            ensure_non_empty(value, "block_id")
        return value

    @field_validator("trigger_roles")
    @classmethod
    def _roles_valid(cls, values: list[str]) -> list[str]:
        for item in values:
            if item not in SUPPORTED_RESIDUAL_ROLES:
                raise ValueError(f"trigger role must be one of {sorted(SUPPORTED_RESIDUAL_ROLES)}")
        return values

    @field_validator("trigger_diagnostic_keys", "next_template_ids", "next_required_variables", "next_required_parameters")
    @classmethod
    def _strings_valid(cls, values: list[str], info) -> list[str]:
        for item in values:
            ensure_non_empty(item, info.field_name)
        return values

    @model_validator(mode="after")
    def _thresholds_valid(self) -> "RefinementRuleSpec":
        if not math.isfinite(self.score_threshold) or self.score_threshold < 0:
            raise ValueError("score_threshold must be finite and nonnegative")
        if self.confidence_min is not None and not math.isfinite(self.confidence_min):
            raise ValueError("confidence_min must be finite")
        return self


class BlockScoringSpec(BaseModel):
    """Configuration for block suspicion scoring."""

    model_config = ConfigDict(extra="forbid")

    method: str = "max"
    top_k: int = 3
    include_roles: list[str] = Field(default_factory=lambda: ["equation", "connection", "boundary", "assumption", "soft_check"])
    exclude_roles: list[str] = Field(default_factory=lambda: ["post_check"])
    diagnostic_key_weights: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_scoring(self) -> "BlockScoringSpec":
        if self.method not in {"max", "rms", "top_k_mean", "weighted_sum"}:
            raise ValueError("scoring method must be max, rms, top_k_mean, or weighted_sum")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        for role in [*self.include_roles, *self.exclude_roles]:
            if role not in SUPPORTED_RESIDUAL_ROLES:
                raise ValueError(f"scoring role must be one of {sorted(SUPPORTED_RESIDUAL_ROLES)}")
        for key, weight in self.diagnostic_key_weights.items():
            ensure_non_empty(key, "diagnostic key")
            if not math.isfinite(weight):
                raise ValueError("diagnostic key weights must be finite")
        return self


class ConfidenceScoringSpec(BaseModel):
    """Heuristic confidence configuration for block suspicion quality."""

    model_config = ConfigDict(extra="forbid")

    base_confidence: float = 1.0
    missing_required_variable_penalty: float = 0.15
    missing_required_parameter_penalty: float = 0.10
    unassigned_residual_penalty: float = 0.05
    default_parameter_penalty: float = 0.10
    coarse_level_penalty_per_level_above_zero: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 1.0

    @model_validator(mode="after")
    def _validate_confidence(self) -> "ConfidenceScoringSpec":
        for field_name in (
            "base_confidence",
            "missing_required_variable_penalty",
            "missing_required_parameter_penalty",
            "unassigned_residual_penalty",
            "default_parameter_penalty",
            "coarse_level_penalty_per_level_above_zero",
            "min_confidence",
            "max_confidence",
        ):
            value = getattr(self, field_name)
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        if self.min_confidence > self.max_confidence:
            raise ValueError("min_confidence must be <= max_confidence")
        if not self.min_confidence <= self.base_confidence <= self.max_confidence:
            raise ValueError("base_confidence must be inside min/max confidence bounds")
        return self


class HierarchySpec(BaseModel):
    """Block hierarchy plus scoring and refinement configuration."""

    model_config = ConfigDict(extra="forbid")

    blocks: list[AuditBlockSpec]
    refinement_rules: list[RefinementRuleSpec] = Field(default_factory=list)
    scoring: BlockScoringSpec = Field(default_factory=BlockScoringSpec)
    confidence: ConfidenceScoringSpec = Field(default_factory=ConfidenceScoringSpec)

    @model_validator(mode="after")
    def _validate_hierarchy(self) -> "HierarchySpec":
        if not self.blocks:
            raise ValueError("hierarchy requires at least one block")
        blocks_by_id = {block.id: block for block in self.blocks}
        if len(blocks_by_id) != len(self.blocks):
            raise ValueError("block ids must be unique")
        roots = [block for block in self.blocks if block.parent_id is None]
        if not roots:
            raise ValueError("hierarchy requires at least one root block")
        for block in self.blocks:
            if block.parent_id is not None:
                if block.parent_id not in blocks_by_id:
                    raise ValueError(f"parent_id references unknown block: {block.parent_id}")
                parent = blocks_by_id[block.parent_id]
                if block.level <= parent.level:
                    raise ValueError("child block level must be greater than parent level")
        for block in self.blocks:
            visited: set[str] = set()
            current = block
            while current.parent_id is not None:
                if current.id in visited:
                    raise ValueError("block hierarchy cannot contain cycles")
                visited.add(current.id)
                current = blocks_by_id[current.parent_id]
            if current.id in visited:
                raise ValueError("block hierarchy cannot contain cycles")
        component_owners: dict[str, str] = {}
        for block in self.blocks:
            for component in block.components:
                owner = component_owners.get(component)
                if owner is not None:
                    raise ValueError(
                        f"component '{component}' is assigned to multiple blocks: {owner}, {block.id}"
                    )
                component_owners[component] = block.id
        for rule in self.refinement_rules:
            if rule.block_id is not None and rule.block_id not in blocks_by_id:
                raise ValueError(f"refinement rule references unknown block: {rule.block_id}")
        return self


class HierarchicalAuditSpec(BaseModel):
    """Top-level spec for a hierarchical PhysicsGuard audit."""

    model_config = ConfigDict(extra="forbid")

    audit_name: str
    description: Optional[str] = None
    system: SystemSpec
    hierarchy: HierarchySpec
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("audit_name")
    @classmethod
    def _audit_name_not_empty(cls, value: str) -> str:
        return ensure_non_empty(value, "audit_name")

    @model_validator(mode="after")
    def _metadata_json_serializable(self) -> "HierarchicalAuditSpec":
        _ensure_json_serializable(self.metadata, "metadata")
        return self


def _ensure_json_serializable(value: Any, field_name: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON-serializable") from exc


__all__ = [
    "AuditBlockSpec",
    "BlockScoringSpec",
    "ConfidenceScoringSpec",
    "HierarchicalAuditSpec",
    "HierarchySpec",
    "RefinementRuleSpec",
]
