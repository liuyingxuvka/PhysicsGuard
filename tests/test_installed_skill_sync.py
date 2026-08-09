from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from scripts import check_installed_physicsguard_skills as installed_audit
from scripts.check_installed_physicsguard_skills import (
    _consumer_projection_status,
    check_installed_skills,
)
from scripts.physicsguard_skill_install_authority import (
    DEFAULT_SKILLGUARD_ROOT,
    PHYSICSGUARD_SKILL_IDS,
    load_member_contract,
    load_skillguard_consumer_api,
)


ROOT = Path(__file__).resolve().parents[1]
SKILLGUARD_ROOT = DEFAULT_SKILLGUARD_ROOT
SKILLGUARD_SCRIPTS = SKILLGUARD_ROOT / "scripts"
if str(SKILLGUARD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILLGUARD_SCRIPTS))

from skillguard_v2.consumer_distribution import build_consumer_distribution
from skillguard_v2.contract_compiler import canonical_hash


def _build_suite(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    shutil.copytree(ROOT / "skill", repository / "skill")
    installed_root = tmp_path / "installed-skills"
    installed_root.mkdir()
    for skill_id in PHYSICSGUARD_SKILL_IDS:
        skill_root = repository / "skill" / skill_id
        contract = json.loads(
            (skill_root / ".skillguard" / "compiled-contract.json").read_text(
                encoding="utf-8"
            )
        )
        result = build_consumer_distribution(
            skill_root,
            installed_root / skill_id,
            contract,
        )
        assert result["status"] == "passed"
    return repository, installed_root


def _check(repository: Path, installed_root: Path) -> dict:
    return check_installed_skills(
        installed_root,
        repository_root=repository,
        skillguard_root=SKILLGUARD_ROOT,
    )


def _tree_snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    snapshot: dict[str, tuple[int, int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            stat = path.stat()
            snapshot[path.relative_to(root).as_posix()] = (
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return snapshot


def _first_member(result: dict) -> dict:
    return next(
        row
        for row in result["member_results"]
        if row["skill_id"] == PHYSICSGUARD_SKILL_IDS[0]
    )


def _owner_results(
    repository: Path,
    installed_root: Path,
) -> tuple[Path, Path, dict, dict]:
    skill_id = PHYSICSGUARD_SKILL_IDS[0]
    source = repository / "skill" / skill_id
    installed = installed_root / skill_id
    api = load_skillguard_consumer_api(SKILLGUARD_ROOT)
    contract = load_member_contract(source, skill_id)
    plan = api.consumer_distribution_plan(source, contract)
    audit = api.audit_consumer_distribution(installed)
    assert plan["status"] == "passed"
    assert audit["status"] == "passed"
    return source, installed, plan, audit


def test_installed_skill_sync_check_passes_matching_copy_and_writes_nothing(
    tmp_path: Path,
) -> None:
    repository, installed_root = _build_suite(tmp_path)
    before_source = _tree_snapshot(repository)
    before_installed = _tree_snapshot(installed_root)

    result = _check(repository, installed_root)

    assert result["ok"]
    assert result["status"] == "pass"
    assert result["expected_skill_ids"] == list(PHYSICSGUARD_SKILL_IDS)
    assert _tree_snapshot(repository) == before_source
    assert _tree_snapshot(installed_root) == before_installed


def test_installed_skill_sync_check_reports_missing_skill(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    shutil.rmtree(installed_root / PHYSICSGUARD_SKILL_IDS[0])

    result = _check(repository, installed_root)

    assert not result["ok"]
    assert any(
        finding["type"] == "installed_skill_missing"
        for finding in result["findings"]
    )


def test_new_source_file_invalidates_installed_release_plan(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    source = repository / "skill" / PHYSICSGUARD_SKILL_IDS[0]
    source.joinpath("new-capability.md").write_text(
        "A newly governed consumer capability.\n", encoding="utf-8"
    )

    result = _check(repository, installed_root)

    member = _first_member(result)
    assert member["ok"] is False
    assert "installed_consumer_release_id_mismatch" in member["reasons"]


def test_rehashed_manifest_release_id_tamper_is_still_blocked(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    manifest_path = (
        installed_root / PHYSICSGUARD_SKILL_IDS[0] / "consumer-release.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release_id"] = "0" * 64
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    manifest["manifest_hash"] = canonical_hash(unsigned)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    result = _check(repository, installed_root)

    member = _first_member(result)
    assert member["ok"] is False
    assert "installed_consumer_release_id_mismatch" in member["reasons"]


def test_missing_manifest_is_blocked_by_skillguard_audit(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    (installed_root / PHYSICSGUARD_SKILL_IDS[0] / "consumer-release.json").unlink()

    result = _check(repository, installed_root)

    member = _first_member(result)
    assert member["ok"] is False
    assert "installed_consumer_audit_blocked" in member["reasons"]


def test_author_control_path_is_blocked_by_skillguard_audit(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    author_path = installed_root / PHYSICSGUARD_SKILL_IDS[0] / ".skillguard"
    author_path.mkdir()
    author_path.joinpath("author.json").write_text("{}\n", encoding="utf-8")

    result = _check(repository, installed_root)

    member = _first_member(result)
    assert member["ok"] is False
    assert any(
        reason.startswith("installed_audit_finding:consumer_author_control_path_present")
        for reason in member["reasons"]
    )


def test_unexpected_consumer_file_is_blocked_by_skillguard_audit(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    (installed_root / PHYSICSGUARD_SKILL_IDS[0] / "unexpected.txt").write_text(
        "unexpected\n", encoding="utf-8"
    )

    result = _check(repository, installed_root)

    member = _first_member(result)
    assert member["ok"] is False
    assert any(
        reason.startswith("installed_audit_finding:consumer_file_unexpected")
        for reason in member["reasons"]
    )


def test_installed_member_symlink_is_visibly_blocked(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    member = installed_root / PHYSICSGUARD_SKILL_IDS[0]
    external = tmp_path / "external-member"
    member.rename(external)
    try:
        os.symlink(external, member, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    result = _check(repository, installed_root)

    row = _first_member(result)
    assert row["ok"] is False
    assert row["reasons"] == ["installed_skill_root_unsafe"]


def test_unavailable_skillguard_authority_has_no_local_fallback(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)

    result = check_installed_skills(
        installed_root,
        repository_root=repository,
        skillguard_root=tmp_path / "missing-skillguard",
    )

    assert result["status"] == "blocked"
    assert result["skillguard_authority"] is None
    assert result["member_results"] == []
    assert result["findings"][0]["type"] == (
        "skillguard_consumer_authority_unavailable"
    )


def test_every_unexpected_physicsguard_prefixed_entry_is_a_residual(
    tmp_path: Path,
) -> None:
    repository, installed_root = _build_suite(tmp_path)
    (installed_root / "physicsguard-unregistered-route").mkdir()
    (installed_root / "physicsguard-database-catalog").write_text(
        "retired\n", encoding="utf-8"
    )

    result = _check(repository, installed_root)

    residuals = {
        row["skill"]: row
        for row in result["findings"]
        if row["type"] == "unexpected_installed_physicsguard_residual"
    }
    assert residuals["physicsguard-unregistered-route"]["entry_kind"] == "directory"
    assert residuals["physicsguard-unregistered-route"]["known_retired_id"] is False
    assert residuals["physicsguard-database-catalog"]["entry_kind"] == "file"
    assert residuals["physicsguard-database-catalog"]["known_retired_id"] is True


def test_unexpected_physicsguard_symlink_is_scanned_without_following(
    tmp_path: Path,
) -> None:
    repository, installed_root = _build_suite(tmp_path)
    external = tmp_path / "external-residual"
    external.mkdir()
    residual = installed_root / "physicsguard-unregistered-link"
    try:
        os.symlink(external, residual, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    result = _check(repository, installed_root)

    finding = next(
        row
        for row in result["findings"]
        if row.get("skill") == residual.name
    )
    assert finding["type"] == "unexpected_installed_physicsguard_residual"
    assert finding["entry_kind"] == "link_or_reparse"


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("member_count", "installed_consumer_member_count_invalid"),
        ("audit_findings", "installed_audit_findings_not_list"),
        ("plan_files", "source_consumer_files_not_list"),
        ("manifest_files", "installed_consumer_files_not_list"),
    ],
)
def test_malformed_skillguard_result_types_block_without_raising(
    tmp_path: Path,
    mutation: str,
    expected_reason: str,
) -> None:
    repository, installed_root = _build_suite(tmp_path)
    source, installed, raw_plan, raw_audit = _owner_results(
        repository, installed_root
    )
    plan = copy.deepcopy(raw_plan)
    audit = copy.deepcopy(raw_audit)
    if mutation == "member_count":
        audit["member_count"] = "not-an-integer"
    elif mutation == "audit_findings":
        audit["findings"] = {"code": "not-a-list"}
    elif mutation == "plan_files":
        plan["files"] = {"path": "not-a-list"}
    elif mutation == "manifest_files":
        audit["manifest"]["files"] = {"path": "not-a-list"}
    else:  # pragma: no cover - parameter list is closed above
        raise AssertionError(mutation)
    api = SimpleNamespace(
        consumer_distribution_plan=lambda *_args: plan,
        audit_consumer_distribution=lambda *_args: audit,
    )

    result = _consumer_projection_status(
        PHYSICSGUARD_SKILL_IDS[0], source, installed, api
    )

    assert result["ok"] is False
    assert expected_reason in result["reasons"]
    json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)


@pytest.mark.parametrize("owner", ["plan", "audit"])
def test_nonserializable_owner_result_is_replaced_by_canonical_block(
    tmp_path: Path,
    owner: str,
) -> None:
    repository, installed_root = _build_suite(tmp_path)
    source, installed, raw_plan, raw_audit = _owner_results(
        repository, installed_root
    )
    plan = copy.deepcopy(raw_plan)
    audit = copy.deepcopy(raw_audit)
    if owner == "plan":
        plan["raw"] = {object()}
    else:
        audit["raw"] = {object()}
    api = SimpleNamespace(
        consumer_distribution_plan=lambda *_args: plan,
        audit_consumer_distribution=lambda *_args: audit,
    )

    result = _consumer_projection_status(
        PHYSICSGUARD_SKILL_IDS[0], source, installed, api
    )

    assert result["ok"] is False
    assert any("not_json_serializable" in reason for reason in result["reasons"])
    json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)


@pytest.mark.parametrize("failure_mode", ["raise", "nonserializable"])
def test_checker_main_prints_one_canonical_blocked_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_mode: str,
) -> None:
    if failure_mode == "raise":
        def fail(*_args, **_kwargs):
            raise RuntimeError("fixture-check-failure")

        monkeypatch.setattr(installed_audit, "check_installed_skills", fail)
    else:
        monkeypatch.setattr(
            installed_audit,
            "check_installed_skills",
            lambda *_args, **_kwargs: {"ok": False, "raw": object()},
        )

    exit_code = installed_audit.main(["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert captured.out.count("\n") == 1
    assert captured.err == ""
    assert payload["schema_version"] == "physicsguard.installed_skill_audit.v1"
    assert payload["artifact_kind"] == "physicsguard_installed_skill_audit"
    assert payload["status"] == "blocked"
    assert payload["findings"][0]["type"] == (
        "installed_skill_audit_machine_output_blocked"
    )
