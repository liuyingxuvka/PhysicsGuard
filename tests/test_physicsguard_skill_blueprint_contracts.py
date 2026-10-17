"""Native route policy and consumer capsule identify the same domain owner."""
from __future__ import annotations
import json
from pathlib import Path
from physicsguard.skill_execution_depth import ROUTE_POLICIES
ROOT = Path(__file__).resolve().parents[1]

def test_each_skill_guard_model_binds_its_native_blueprint_contract() -> None:
    capsules = {}
    for skill, policy in ROUTE_POLICIES.items():
        capsule = json.loads((ROOT / "skill" / skill / "references/route-capsule.json").read_text())
        assert capsule["native_owner_id"] == policy.native_owner_id
        assert capsule["native_route_id"] == policy.native_route_id
        assert capsule["broad_route_prerequisite"] is False
        capsules[skill] = capsule
    authors = [s for s, p in ROUTE_POLICIES.items() if p.blueprint_authority_mode == "sole_author_full_reviewer"]
    assert authors == ["physicsguard-candidate-model-blueprint"]
    assert len({r["native_owner_id"] for r in capsules.values()}) == 10

def test_blueprint_guard_contract_mutation_blocks_without_self_report_fallback() -> None:
    from physicsguard.skill_execution_depth import build_skill_execution_fixture, evaluate_skill_execution_package
    package = build_skill_execution_fixture("physicsguard-candidate-model-blueprint", evidence_domain="capability_validation", run_id="native-policy-negative")
    package["native_owner_id"] = "foreign-owner"
    report = evaluate_skill_execution_package(package)
    assert report["status"] == "blocked"
    assert "wrong_native_owner" in {r["code"] for r in report["errors"]}
