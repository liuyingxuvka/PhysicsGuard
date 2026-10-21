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
