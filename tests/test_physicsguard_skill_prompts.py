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
    labels = re.findall(r"^- (Node|Parent|Known-bad|Real binding|Test binding|Readback|Current vs target):", text, re.M)
    assert labels == ["Node", "Parent", "Known-bad", "Real binding", "Test binding", "Readback", "Current vs target"]
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


def test_skill_files_name_only_existing_commands():
    import argparse
    from physicsguard.cli import build_parser
    skill=SKILL_ROOT/'physicsguard'
    text=(skill/'references/routes/ai-debugging.md').read_text()
    assert len(text.splitlines())<=130
    assert text.count('Do not learn by modifying PhysicsGuard itself')==1
    assert not (skill/'references/protocol.md').exists()
    assert '## Minimum workflow' not in text and '## Workflow A' not in text
    def choices(parser):
        return next((action.choices for action in parser._actions if isinstance(action, argparse._SubParsersAction)), {})
    parsers = choices(build_parser())
    files = [skill / 'SKILL.md', ROOT / 'README.md', *sorted((skill / 'references').rglob('*.md'))]
    seen = 0
    for path in files:
        commands = re.findall(r'physicsguard\.cli ([a-z][a-z-]*)(?: ([a-z][a-z-]*))?', path.read_text())
        for command, subcommand in commands:
            seen += 1
            assert command in parsers, (path, command)
            nested = choices(parsers[command])
            if nested:
                assert subcommand in nested, (path, command, subcommand)
    assert seen
