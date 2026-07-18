from __future__ import annotations

import json
from pathlib import Path
import sys

from scripts.check_installed_physicsguard_skills import check_installed_skills


ROOT = Path(__file__).resolve().parents[1]
REPO_SKILLS = ROOT / "skill"
SKILLGUARD_SCRIPTS = Path.home() / ".codex" / "skills" / "skillguard" / "scripts"
if str(SKILLGUARD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILLGUARD_SCRIPTS))

from skillguard_v2.consumer_distribution import build_consumer_distribution


def test_installed_skill_sync_check_passes_matching_copy(tmp_path: Path) -> None:
    installed_root = tmp_path / "skills"
    installed_root.mkdir()
    for skill_dir in REPO_SKILLS.iterdir():
        if skill_dir.is_dir():
            contract = json.loads(
                (skill_dir / ".skillguard" / "compiled-contract.json").read_text(
                    encoding="utf-8"
                )
            )
            result = build_consumer_distribution(
                skill_dir,
                installed_root / skill_dir.name,
                contract,
            )
            assert result["status"] == "passed"

    result = check_installed_skills(installed_root)

    assert result["ok"]
    assert result["status"] == "pass"


def test_installed_skill_sync_check_reports_missing_skill(tmp_path: Path) -> None:
    installed_root = tmp_path / "skills"
    installed_root.mkdir()

    result = check_installed_skills(installed_root)

    assert not result["ok"]
    assert any(finding["type"] == "installed_skill_missing" for finding in result["findings"])
