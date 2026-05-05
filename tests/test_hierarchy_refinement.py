from __future__ import annotations

from physicsguard.core.diagnostics import ResidualDiagnostic
from physicsguard.core.hierarchy import BlockDiagnostic, RefinementPlanner
from physicsguard.schema.hierarchy_spec import HierarchySpec


def residual(key: str, role: str = "equation") -> ResidualDiagnostic:
    return ResidualDiagnostic(
        name=f"r.{key}",
        source="r",
        role=role,
        raw_value=2.0,
        scale=1.0,
        normalized_value=2.0,
        abs_normalized_value=2.0,
        diagnostic_key=key,
        description=None,
    )


def block(score: float = 2.0, key: str = "bad_key", role: str = "equation") -> BlockDiagnostic:
    return BlockDiagnostic(
        block_id="b",
        name=None,
        level=0,
        parent_id=None,
        tags=[],
        score=score,
        confidence=0.9,
        audit_pass=score <= 1.0,
        max_abs_normalized_residual=score,
        residual_norm=score,
        top_residuals=[residual(key, role)],
        post_check_residuals=[],
        missing_required_variables=[],
        missing_required_parameters=[],
        recommended_refinements=[],
    )


def hierarchy() -> HierarchySpec:
    return HierarchySpec.model_validate(
        {
            "blocks": [{"id": "b", "level": 0}],
            "refinement_rules": [
                {
                    "id": "low_priority",
                    "block_id": "b",
                    "trigger_diagnostic_keys": ["bad_key"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["detail_low"],
                    "priority": 1,
                },
                {
                    "id": "high_priority",
                    "block_id": "b",
                    "trigger_roles": ["equation"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["detail_high"],
                    "priority": 10,
                },
            ],
        }
    )


def test_rule_triggers_when_score_threshold_exceeded() -> None:
    recs = RefinementPlanner().recommended_refinements(block(), hierarchy())
    assert {rec.rule_id for rec in recs} == {"low_priority", "high_priority"}


def test_no_trigger_when_score_below_threshold() -> None:
    recs = RefinementPlanner().recommended_refinements(block(score=0.5), hierarchy())
    assert recs == []


def test_diagnostic_key_trigger_works() -> None:
    recs = RefinementPlanner().recommended_refinements(block(key="other"), hierarchy())
    assert [rec.rule_id for rec in recs] == ["high_priority"]


def test_role_trigger_works() -> None:
    recs = RefinementPlanner().recommended_refinements(block(role="boundary"), hierarchy())
    assert [rec.rule_id for rec in recs] == ["low_priority"]


def test_priority_ordering_works() -> None:
    recs = RefinementPlanner().recommended_refinements(block(), hierarchy())
    assert [rec.rule_id for rec in recs] == ["high_priority", "low_priority"]
