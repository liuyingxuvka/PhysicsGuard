from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys

import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"








@pytest.mark.parametrize(
    ("source", "exception_name"),
    [
        ("def broken(:\n", "SyntaxError"),
        ("raise RuntimeError('partial package')\n", "RuntimeError"),
        ("raise TypeError('invalid package initialization')\n", "TypeError"),
    ],
)
def test_readiness_import_failure_is_one_blocked_json(
    tmp_path: Path, source: str, exception_name: str
) -> None:
    package = tmp_path / "physicsguard"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/verify_guard_simulation_readiness.py"),
            "--repository-root", str(ROOT),
            "--installed-root", str(tmp_path / "missing-skills"),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "blocked"
    assert report["ok"] is False
    assert report["package"]["ok"] is False
    assert any(finding.startswith(f"{exception_name}:") for finding in report["package"]["findings"])
    assert "Traceback" not in result.stderr
