from __future__ import annotations

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"

EXPECTED_SKILLS = {"physicsguard"}
EXPECTED_ROUTES = {
    "ai-debugging.md",
    "model-dataset-validation.md",
    "model-understanding-preflight.md",
    "signal-mapping-review.md",
    "test-file-contract-review.md",
}


def test_exact_physicsguard_skill_inventory() -> None:
    actual = {path.parent.name for path in SKILL_ROOT.glob("*/SKILL.md")}
    assert actual == EXPECTED_SKILLS


def test_route_table_names_every_route_file_and_the_description_is_short() -> None:
    text = (SKILL_ROOT / "physicsguard" / "SKILL.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"`references/routes/([a-z-]+\.md)`", text))
    present = {path.name for path in (SKILL_ROOT / "physicsguard" / "references" / "routes").glob("*.md")}
    assert listed == present == EXPECTED_ROUTES
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == "physicsguard"
    assert len(front["description"]) <= 300


def test_one_model_tree_and_format_guide_are_available_from_the_skill() -> None:
    skill = SKILL_ROOT / "physicsguard"
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    paragraphs = [paragraph for paragraph in text.split("\n\n") if "five abilities" in paragraph]
    assert len(paragraphs) == 1 and len(paragraphs[0].splitlines()) <= 6
    assert "references/model-format.md" in text.split("## Rules for every route", 1)[1]
    guide = (skill / "references/model-format.md").read_text(encoding="utf-8")
    assert len(guide.splitlines()) <= 150
    for term in ("from_variable", "parent_id", "refines", "next_template_ids", "fault_variants", "stale_when", "synthetic", "assumptions"):
        assert term in guide
    route = (skill / "references/routes/ai-debugging.md").read_text(encoding="utf-8")
    assert "model-format.md" in route and "hierarchy describe" in route


def test_ai_debugging_keeps_four_hard_boundaries() -> None:
    text = (SKILL_ROOT / "physicsguard" / "references" / "routes" / "ai-debugging.md").read_text(encoding="utf-8")
    boundaries = text.split("## Hard Boundaries", 1)[1].split("\n## ", 1)[0]
    for rule in (
        "Do not count one value as adequate coverage for a time-varying parameter",
        "Do not describe pointwise evaluation as simulation or prediction",
        "Do not learn by modifying PhysicsGuard itself during a diagnostic episode",
        "For GT-SUITE, Modelica, Amesim, FMI, or other external tools, use only official, user-provided, or documented interfaces",
    ):
        assert boundaries.count(rule) == 1, rule
