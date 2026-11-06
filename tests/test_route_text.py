"""Check route content for repeated material, dead references and unknown names."""
from __future__ import annotations

import argparse
from pathlib import Path

from flowguard.testing import CODES, LINKS, check_route_texts, local_link as _destination

from physicsguard.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill/physicsguard"


def _options(parser):
    result = set()
    for action in parser._actions:
        result.update(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                result.update(_options(child))
    return result


def _references(origin, text):
    result = set()
    for code in CODES.findall(text):
        if code.startswith("references/") and Path(code.split("#", 1)[0]).suffix == ".md":
            result.add((SKILL / code.split("#", 1)[0]).resolve())
    for link in LINKS.findall(text):
        resolved = _destination(origin, link)
        if resolved and resolved[0].suffix == ".md":
            result.add(resolved[0])
    return result


def _check(route, texts, flags):
    check_route_texts(route, texts, flags, skill_root=SKILL, project_root=ROOT,
                      project_prefixes=('src/', 'tests/', 'examples/'))


def test_route_texts_have_no_repeats_dead_links_or_missing_names():
    entry_path = SKILL / "SKILL.md"
    entry = entry_path.read_text(encoding='utf-8')
    common = entry.split("## Rules for every route", 1)[1].split("\n## ", 1)[0]
    flags = _options(build_parser())
    errors = []
    for route in sorted((SKILL / "references/routes").glob("*.md")):
        route_text = route.read_text(encoding='utf-8')
        files = (
            {entry_path, route} | _references(entry_path, common) | _references(route, route_text)
        )
        try:
            for path in files:
                assert path.is_file(), f"{route.name}: missing reference: {path}"
            texts = {path: path.read_text(encoding='utf-8') for path in sorted(files)}
            _check(route.name, texts, flags)
        except AssertionError as error:
            errors.append(str(error))
        print(
            f"route {route.name}: {sum(len(path.read_text(encoding='utf-8')) for path in files if path.is_file())} characters"
        )
    assert not errors, "\n".join(errors)
