from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKILL_ROOT = ROOT / "skill"

EXPECTED_SKILLS = {
    "physicsguard-ai-debugging",
    "physicsguard-model-dataset-validation",
    "physicsguard-model-understanding-preflight",
    "physicsguard-signal-mapping-review",
    "physicsguard-test-file-contract-review",
}

def test_exact_physicsguard_skill_inventory() -> None:
    actual = {path.parent.name for path in SKILL_ROOT.glob("*/SKILL.md")}
    assert actual == EXPECTED_SKILLS
