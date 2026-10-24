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


def test_refines_requires_a_parent_owned_component_and_describe_exposes_it(monkeypatch) -> None:
    from physicsguard.core.hierarchy import describe_hierarchy
    from physicsguard.core.solver import BoundedSolver

    def no_solve(*args, **kwargs):
        pytest.fail("describe must not solve")

    monkeypatch.setattr(BoundedSolver, "solve", no_solve)

    data = audit_data()
    data["system"]["components"].append({"id": "coarse", "type": "DummyResidualModule", "parameters": {"target": 0.}})
    data["hierarchy"]["blocks"][0]["components"] = ["coarse"]
    data["hierarchy"]["blocks"][1]["refines"] = ["coarse"]
    spec = HierarchicalAuditSpec.model_validate(data)
    assert describe_hierarchy(spec)["blocks"][1]["refines"] == ["coarse"]
    data["hierarchy"]["blocks"][1]["refines"] = ["a"]
    with pytest.raises(ValidationError, match="child.*not owned by its parent: a"):
        HierarchicalAuditSpec.model_validate(data)


def test_retired_expected_residual_keys_is_not_silently_accepted() -> None:
    data = hierarchy_data()
    data["blocks"][0]["expected_residual_keys"] = ["old_unused_key"]
    with pytest.raises(ValidationError, match="expected_residual_keys.*|Extra inputs are not permitted"):
        HierarchySpec.model_validate(data)


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


def test_retired_refinement_template_ids_names_the_single_rule_owner() -> None:
    data = hierarchy_data()
    # Presence is retired even when the former optional list was empty.
    data["blocks"][0]["refinement_template_ids"] = []
    with pytest.raises(ValidationError) as error:
        HierarchySpec.model_validate(data)
    assert error.value.errors()[0]["msg"] == (
        "Value error, refinement_template_ids is retired; "
        "list next templates in hierarchy.refinement_rules[].next_template_ids"
    )
