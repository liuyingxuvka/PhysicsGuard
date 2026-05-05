from __future__ import annotations

import pytest
from pydantic import ValidationError

from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec, HierarchySpec


def hierarchy_data() -> dict:
    return {
        "blocks": [
            {"id": "root", "level": 0},
            {"id": "child", "level": 1, "parent_id": "root", "components": ["a"]},
        ],
        "refinement_rules": [{"id": "refine_child", "block_id": "child", "trigger_roles": ["equation"]}],
    }


def audit_data() -> dict:
    return {
        "audit_name": "hierarchy_valid",
        "system": {
            "system_name": "hierarchy_valid_system",
            "components": [{"id": "a", "type": "DummyResidualModule", "parameters": {"target": 1.0}}],
        },
        "hierarchy": hierarchy_data(),
    }


def test_valid_hierarchical_audit_spec_passes() -> None:
    spec = HierarchicalAuditSpec.model_validate(audit_data())
    assert spec.audit_name == "hierarchy_valid"
    assert spec.hierarchy.blocks[1].parent_id == "root"


def test_duplicate_block_id_fails() -> None:
    data = hierarchy_data()
    data["blocks"].append({"id": "child", "level": 0})
    with pytest.raises(ValidationError, match="block ids"):
        HierarchySpec.model_validate(data)


def test_unknown_parent_fails() -> None:
    data = hierarchy_data()
    data["blocks"][1]["parent_id"] = "missing"
    with pytest.raises(ValidationError, match="parent_id"):
        HierarchySpec.model_validate(data)


def test_cycle_fails() -> None:
    data = {
        "blocks": [
            {"id": "a", "level": 2, "parent_id": "b"},
            {"id": "b", "level": 1, "parent_id": "a"},
        ]
    }
    with pytest.raises(ValidationError):
        HierarchySpec.model_validate(data)


def test_invalid_residual_role_in_scoring_fails() -> None:
    data = hierarchy_data()
    data["scoring"] = {"include_roles": ["bad_role"]}
    with pytest.raises(ValidationError, match="scoring role"):
        HierarchySpec.model_validate(data)


def test_invalid_refinement_rule_role_fails() -> None:
    data = hierarchy_data()
    data["refinement_rules"][0]["trigger_roles"] = ["bad_role"]
    with pytest.raises(ValidationError, match="trigger role"):
        HierarchySpec.model_validate(data)


def test_negative_level_fails() -> None:
    data = hierarchy_data()
    data["blocks"][0]["level"] = -1
    with pytest.raises(ValidationError, match="level"):
        HierarchySpec.model_validate(data)


def test_invalid_score_method_fails() -> None:
    data = hierarchy_data()
    data["scoring"] = {"method": "median"}
    with pytest.raises(ValidationError, match="scoring method"):
        HierarchySpec.model_validate(data)
