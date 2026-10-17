from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from scripts import upgrade_purpose_contracts as generator
ROOT = Path(__file__).resolve().parents[1]

def _source(tmp_path: Path) -> Path:
    target = tmp_path / "source"
    target.mkdir()
    for name in ("VERSION", "pyproject.toml"):
        shutil.copyfile(ROOT / name, target / name)
    (target / "src/physicsguard").mkdir(parents=True)
    shutil.copyfile(ROOT / "src/physicsguard/__init__.py", target / "src/physicsguard/__init__.py")
    shutil.copytree(ROOT / "skill", target / "skill")
    return target

def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}

def test_generator_help_is_read_only(tmp_path: Path) -> None:
    source = _source(tmp_path)
    before = _snapshot(source)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/upgrade_purpose_contracts.py"), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert before == _snapshot(source)

def test_generator_blocks_physicsguard_version_drift_before_transaction(tmp_path: Path) -> None:
    source = _source(tmp_path)
    (source / "VERSION").write_text("0.0.0\n")
    before = _snapshot(source)
    with pytest.raises(ValueError, match="version_authority_mismatch"):
        generator.main(repository_root=source, argv=[])
    assert before == _snapshot(source)

def test_generation_stage_failure_on_sixth_member_leaves_managed_bytes_unchanged(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    before = _snapshot(source)
    original = generator.upgrade_target_current
    calls = []
    def fail_sixth(skill_id, **kwargs):
        calls.append(skill_id)
        if len(calls) == 6:
            raise OSError("fixture staging failure")
        return original(skill_id, **kwargs)
    monkeypatch.setattr(generator, "upgrade_target_current", fail_sixth)
    with pytest.raises(OSError, match="staging failure"):
        generator.main(repository_root=source, argv=[])
    assert len(calls) == 6
    assert before == _snapshot(source)
