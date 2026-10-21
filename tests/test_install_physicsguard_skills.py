from __future__ import annotations

from pathlib import Path

from scripts import install_physicsguard_skills as installer


def _skill_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository" / "skill"
    for skill_id in installer.PHYSICSGUARD_SKILL_IDS:
        source = root / skill_id
        (source / "references").mkdir(parents=True)
        (source / "SKILL.md").write_text(f"# {skill_id}\n", encoding="utf-8")
        (source / "references" / "protocol.md").write_text("Native protocol.\n", encoding="utf-8")
        (source / ".author-tools").mkdir()
        (source / ".author-tools" / "author.json").write_text("{}\n", encoding="utf-8")
        (source / "guard-model").mkdir()
        (source / "guard-model" / "candidate.json").write_text("{}\n", encoding="utf-8")
    return root


def test_install_replaces_old_copies_with_only_the_consumer_files(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    target = tmp_path / "home" / "skills"
    for skill_id in installer.PHYSICSGUARD_SKILL_IDS:
        (target / skill_id).mkdir(parents=True)
        (target / skill_id / "old.txt").write_text("old", encoding="utf-8")
    assert installer.pending_changes(root, target)
    installer.install(root, target)
    for skill_id in installer.PHYSICSGUARD_SKILL_IDS:
        installed = sorted(p.relative_to(target / skill_id).as_posix() for p in (target / skill_id).rglob("*") if p.is_file())
        assert installed == ["SKILL.md", "references/protocol.md"]
    assert installer.pending_changes(root, target) == []


def test_check_reports_an_edited_copy_and_a_retired_directory(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    target = tmp_path / "skills"
    installer.install(root, target)
    first = installer.PHYSICSGUARD_SKILL_IDS[0]
    (target / first / "SKILL.md").write_text("edited\n", encoding="utf-8")
    (target / installer.RETIRED_SKILL_IDS[0]).mkdir()
    assert installer.pending_changes(root, target) == [
        f"{first}: differs: SKILL.md",
        f"{installer.RETIRED_SKILL_IDS[0]}: retired skill still installed",
    ]


def test_install_removes_retired_skill_dirs_and_check_passes(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    target = tmp_path / "codex-home" / "skills"
    retired = target / installer.RETIRED_SKILL_IDS[0]
    retired.mkdir(parents=True)
    (retired / "SKILL.md").write_text("# retired\n", encoding="utf-8")
    done = installer.install(root, target)
    assert f"removed retired {retired}" in done
    assert not retired.exists()
    assert installer.pending_changes(root, target) == []


def test_install_accepts_a_symlinked_parent_directory(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    (tmp_path / "real-home").mkdir()
    (tmp_path / "linked-home").symlink_to(tmp_path / "real-home", target_is_directory=True)
    installer.install(root, tmp_path / "linked-home" / "skills")
    first = installer.PHYSICSGUARD_SKILL_IDS[0]
    assert (tmp_path / "real-home" / "skills" / first / "SKILL.md").exists()


def test_cli_dry_run_changes_nothing_and_check_fails_until_installed(tmp_path: Path, capsys) -> None:
    target = tmp_path / "skills"
    assert installer.main(["--target", str(target), "--dry-run"]) == 0
    assert not target.exists()
    assert "would change" in capsys.readouterr().out
    assert installer.main(["--target", str(target), "--check"]) == 1
    assert installer.main(["--target", str(target)]) == 0
    assert installer.main(["--target", str(target), "--check"]) == 0
    assert capsys.readouterr().out.endswith("installed skills are current\n")


def test_check_detects_same_stat_content_rewrites_in_one_process(tmp_path: Path, monkeypatch) -> None:
    import os

    root = _skill_root(tmp_path)
    monkeypatch.setattr(installer, "SKILL_ROOT", root)
    target = tmp_path / "skills"
    assert installer.main(["--target", str(target)]) == 0
    assert installer.main(["--target", str(target), "--check"]) == 0
    first = installer.PHYSICSGUARD_SKILL_IDS[0]
    installed = target / first / "SKILL.md"
    original = installed.read_bytes()
    stat = installed.stat()
    installed.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    os.utime(installed, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert (installed.stat().st_size, installed.stat().st_mtime_ns) == (stat.st_size, stat.st_mtime_ns)
    assert installer.pending_changes(root, target) == [f"{first}: differs: SKILL.md"]
    assert installer.main(["--target", str(target), "--check"]) == 1
    installed.write_bytes(original)
    os.utime(installed, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert installer.pending_changes(root, target) == []
    assert installer.main(["--target", str(target), "--check"]) == 0
