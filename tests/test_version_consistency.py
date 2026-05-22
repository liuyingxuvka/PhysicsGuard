from __future__ import annotations

import tomllib
from pathlib import Path

import physicsguard


ROOT = Path(__file__).resolve().parents[1]


def test_version_sources_match() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_version = pyproject["project"]["version"]
    file_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert physicsguard.__version__ == package_version == file_version
