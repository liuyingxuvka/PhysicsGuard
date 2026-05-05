from __future__ import annotations

import pytest

from physicsguard.core.diagnostics import ResidualDiagnostic
from physicsguard.core.hierarchy import BlockScorer, ConfidenceScorer
from physicsguard.schema.hierarchy_spec import AuditBlockSpec, BlockScoringSpec, ConfidenceScoringSpec


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
