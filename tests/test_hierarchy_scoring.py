from __future__ import annotations

import pytest

from physicsguard.core.diagnostics import ResidualDiagnostic
from physicsguard.core.hierarchy import BlockScorer, ConfidenceScorer
from physicsguard.schema.hierarchy_spec import AuditBlockSpec, BlockScoringSpec, ConfidenceScoringSpec


@pytest.mark.parametrize(("coarse", "fine", "consistent"), [(2., 0., False), (0., 2., True), (None, 0., None)])
def test_refinement_consistency_uses_own_checked_coarse_relations(coarse, fine, consistent) -> None:
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
    from physicsguard.schema.observation_spec import ObservedValuesSpec

    spec = HierarchicalAuditSpec.model_validate({"audit_name": "refinement", "system": {"system_name": "refinement", "components": [
        {"id": name, "type": "DummyResidualModule", "parameters": {"target": 0.}} for name in ("coarse", "fine")
    ]}, "hierarchy": {"blocks": [
        {"id": "parent", "components": ["coarse"]},
        {"id": "child", "parent_id": "parent", "level": 1, "components": ["fine"], "refines": ["coarse"]},
    ]}})
    values = {"fine.x": {"value": fine}}
    if coarse is not None:
        values["coarse.x"] = {"value": coarse}
    report = HierarchicalAuditRunner(spec).evaluate_observed(ObservedValuesSpec(variables=values))
    check = report.refinement_checks[0]
    assert check["parent"] == "parent" and check["coarse_components"] == ["coarse"]
    assert check["child_blocks"] == ["child"]
    assert check["consistent"] is consistent
    assert check["coarse_pass"] is (None if coarse is None else coarse <= 1)
    assert check["children_pass"] is (fine <= 1)
    assert ("refinement_inconsistent: parent" in report.warnings) is (consistent is False)
    blocks = {block.block_id: block for block in report.top_blocks}
    assert blocks["parent"].own_audit_pass is (coarse is None or coarse <= 1)
    assert blocks["parent"].audit_pass is (fine <= 1 and (coarse is None or coarse <= 1))
    assert blocks["parent"].score == (coarse or 0.)
    assert blocks["parent"].subtree_score == max(coarse or 0., fine)
    if coarse is None:
        assert check["reason"] == "all coarse residuals were used for derivation"


def test_real_heater_failure_propagates_through_two_ancestors_without_changing_own_scores() -> None:
    from pathlib import Path
    from physicsguard.core.hierarchy import HierarchicalAuditRunner
    from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
    from physicsguard.io.observation_loader import load_observed_values

    example = Path(__file__).resolve().parents[1] / "examples/hierarchical/heated_tank"
    report = HierarchicalAuditRunner(load_hierarchical_audit_spec(example / "heated_tank.yaml")).evaluate_observed(
        load_observed_values(example / "measured_k70.yaml"))
    blocks = {block.block_id: block for block in report.top_blocks}
    assert report.top_blocks[0].block_id == "heater" and report.audit_pass is False
    assert all(blocks[name].audit_pass is False for name in ("heater", "thermal", "tank"))
    assert blocks["thermal"].own_audit_pass is blocks["tank"].own_audit_pass is True
    assert blocks["hydraulics"].audit_pass is True
    assert blocks["tank"].score == 0 and blocks["tank"].subtree_score == blocks["heater"].score == 25


def residual(name: str, value: float, role: str = "equation", key: str = "k") -> ResidualDiagnostic:
    return ResidualDiagnostic(
        name=name,
        source="s",
        role=role,
        raw_value=value,
        scale=1.0,
        normalized_value=value,
        abs_normalized_value=abs(value),
        diagnostic_key=key,
        description=None,
    )


def test_max_score_works() -> None:
    score = BlockScorer().score_block(AuditBlockSpec(id="b"), [residual("a", 2.0), residual("b", -5.0)], BlockScoringSpec())
    assert score == pytest.approx(5.0)


def test_rms_score_works() -> None:
    score = BlockScorer().score_block(
        AuditBlockSpec(id="b"),
        [residual("a", 3.0), residual("b", 4.0)],
        BlockScoringSpec(method="rms"),
    )
    assert score == pytest.approx((12.5) ** 0.5)


def test_top_k_mean_score_works() -> None:
    score = BlockScorer().score_block(
        AuditBlockSpec(id="b"),
        [residual("a", 1.0), residual("b", 3.0), residual("c", 5.0)],
        BlockScoringSpec(method="top_k_mean", top_k=2),
    )
    assert score == pytest.approx(4.0)


def test_post_check_excluded_by_default() -> None:
    score = BlockScorer().score_block(
        AuditBlockSpec(id="b"),
        [residual("a", 1.0), residual("post", 100.0, role="post_check")],
        BlockScoringSpec(),
    )
    assert score == pytest.approx(1.0)


def test_role_filtering_and_weighted_sum_work() -> None:
    score = BlockScorer().score_block(
        AuditBlockSpec(id="b"),
        [residual("a", 2.0, key="important"), residual("b", 5.0, role="boundary")],
        BlockScoringSpec(
            method="weighted_sum",
            include_roles=["equation"],
            exclude_roles=[],
            diagnostic_key_weights={"important": 3.0},
        ),
    )
    assert score == pytest.approx(6.0)


def test_confidence_full_information_is_high() -> None:
    confidence = ConfidenceScorer().score(
        AuditBlockSpec(id="b"),
        [],
        [],
        [residual("a", 1.0)],
        ConfidenceScoringSpec(),
    )
    assert confidence == pytest.approx(1.0)


def test_confidence_penalties_and_clipping() -> None:
    confidence = ConfidenceScorer().score(
        AuditBlockSpec(id="b", level=2),
        ["a.x", "b.x"],
        ["a.parameter"],
        [],
        ConfidenceScoringSpec(coarse_level_penalty_per_level_above_zero=0.2, min_confidence=0.0, max_confidence=1.0),
    )
    assert 0.0 <= confidence <= 1.0
    assert confidence == pytest.approx(0.15)
