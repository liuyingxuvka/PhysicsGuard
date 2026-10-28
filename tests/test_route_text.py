"""Check route content for repeated material, dead references and unknown names."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from physicsguard.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill/physicsguard"
LINKS = re.compile(r"\[[^\]]*\]\(([^\s)]+)\)")
CODES = re.compile(r"`([^`\n]+)`")


def _options(parser):
    result = set()
    for action in parser._actions:
        result.update(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                result.update(_options(child))
    return result


def _slug(heading):
    return re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")


def _destination(origin, link):
    value = urlsplit(link)
    if value.scheme or value.netloc:
        return None
    path = (origin.parent / unquote(value.path)).resolve() if value.path else origin
    return path, unquote(value.fragment)


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
    paragraphs = Counter(
        " ".join(part.split())
        for text in texts.values()
        for part in re.split(r"\n\s*\n", text)
        if len(part.split()) >= 8
    )
    for paragraph, count in paragraphs.items():
        assert count == 1, f"{route}: repeated paragraph: {paragraph}"
    for origin, text in texts.items():
        for link in LINKS.findall(text):
            resolved = _destination(origin, link)
            if resolved is None:
                continue
            target, fragment = resolved
            assert target.exists(), f"{route}: dead link: {link} in {origin}"
            if fragment:
                headings = re.findall(r"^#+ (.+)$", target.read_text(), re.M)
                assert fragment in {
                    _slug(heading) for heading in headings
                }, f"{route}: missing heading: {link} in {origin}"
        for code in CODES.findall(text):
            if code.startswith(
                ("grep ", "git ", "pip ", "python -m pytest", "python -m flowguard")
            ):
                continue
            for option in re.findall(r"--[a-z0-9][\w-]*", code):
                assert option in flags, f"{route}: unknown option: {code}"
            if code.startswith(("references/", "assets/", "scripts/", "agents/")):
                target = SKILL / code.split()[0].split("#", 1)[0]
            elif code.startswith(("src/", "tests/", "examples/")):
                target = ROOT / code.split()[0].split("#", 1)[0]
            else:
                continue
            if "<" in code or "*" in code:
                continue
            assert target.exists(), f"{route}: missing path: {code}"


def test_route_texts_have_no_repeats_dead_links_or_missing_names():
    entry_path = SKILL / "SKILL.md"
    entry = entry_path.read_text()
    common = entry.split("## Rules for every route", 1)[1].split("\n## ", 1)[0]
    flags = _options(build_parser())
    errors = []
    for route in sorted((SKILL / "references/routes").glob("*.md")):
        route_text = route.read_text()
        files = (
            {entry_path, route} | _references(entry_path, common) | _references(route, route_text)
        )
        try:
            for path in files:
                assert path.is_file(), f"{route.name}: missing reference: {path}"
            texts = {path: path.read_text() for path in sorted(files)}
            _check(route.name, texts, flags)
        except AssertionError as error:
            errors.append(str(error))
        print(
            f"route {route.name}: {sum(len(path.read_text()) for path in files if path.is_file())} characters"
        )
    assert not errors, "\n".join(errors)
