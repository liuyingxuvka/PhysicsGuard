from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import install_physicsguard_skills as installer
from scripts.install_physicsguard_skills import (
    build_suite_plan,
    coordinate_suite_install,
)
from scripts.physicsguard_skill_install_authority import (
    PHYSICSGUARD_SKILL_IDS,
    SkillGuardConsumerApi,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeSkillGuard:
    def __init__(
        self,
        *,
        prepare_failure: str | None = None,
        verify_failure: str | None = None,
        activation_failure: str | None = None,
        rollback_failure: str | None = None,
    ) -> None:
        self.events: list[tuple[str, str]] = []
        self.prepare_failure = prepare_failure
        self.verify_failure = verify_failure
        self.activation_failure = activation_failure
        self.rollback_failure = rollback_failure

    def plan(self, member_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
        skill_id = str(contract["skill_id"])
        self.events.append(("plan", skill_id))
        return {
            "schema_version": "consumer.skill_distribution.current",
            "status": "passed",
            "skill_id": skill_id,
            "projection_id": "projection:consumer-distribution",
            "release_id": f"release:{skill_id}",
            "release_manifest_path": "consumer-release.json",
            "files": [
                {"path": "SKILL.md", "content_hash": f"sha256:{skill_id}"}
            ],
            "findings": [],
        }

    def audit(self, root: Path) -> dict[str, Any]:
        raise AssertionError("suite installation coordinator must not audit here")

    def prepare(
        self,
        repository_root: Path,
        member_root: Path,
        stage_root: Path,
    ) -> dict[str, Any]:
        skill_id = member_root.name
        self.events.append(("prepare", skill_id))
        if skill_id == self.prepare_failure:
            return {"status": "blocked", "blockers": ["fixture_prepare_failure"]}
        return {"status": "passed", "skill_id": skill_id}

    def verify(
        self,
        repository_root: Path,
        member_root: Path,
        stage_root: Path,
    ) -> dict[str, Any]:
        skill_id = member_root.name
        self.events.append(("verify", skill_id))
        if skill_id == self.verify_failure:
            return {"status": "blocked", "blockers": ["fixture_verify_failure"]}
        return {
            "status": "passed",
            "skill_id": skill_id,
            "stage_verification_hash": f"verification:{skill_id}",
            "canonical_projection": {"release_id": f"release:{skill_id}"},
        }

    def activate(
        self,
        repository_root: Path,
        member_root: Path,
        stage_root: Path,
        codex_home: Path,
        *,
        stage_verification: dict[str, Any],
    ) -> dict[str, Any]:
        skill_id = member_root.name
        self.events.append(("activate", skill_id))
        assert stage_verification["skill_id"] == skill_id
        if skill_id == self.activation_failure:
            return {"status": "blocked", "blockers": ["fixture_activation_failure"]}
        transaction_id = (
            "target-install-"
            f"{PHYSICSGUARD_SKILL_IDS.index(skill_id) + 1:032x}"
        )
        receipt_hash = f"{PHYSICSGUARD_SKILL_IDS.index(skill_id) + 1:064X}"
        return {
            "status": "passed",
            "skill_id": skill_id,
            "transaction_id": transaction_id,
            "receipt": {
                "status": "committed",
                "skill_id": skill_id,
                "transaction_id": transaction_id,
                "receipt_hash": receipt_hash,
                "canonical_projection": {"release_id": f"release:{skill_id}"},
            },
            "head": {
                "skill_id": skill_id,
                "transaction_id": transaction_id,
                "receipt_hash": receipt_hash,
                "generation": 1,
            },
        }

    def rollback(
        self,
        codex_home: Path,
        skill_id: str,
        transaction_id: str,
    ) -> dict[str, Any]:
        self.events.append(("rollback", skill_id))
        assert transaction_id == (
            "target-install-"
            f"{PHYSICSGUARD_SKILL_IDS.index(skill_id) + 1:032x}"
        )
        if skill_id == self.rollback_failure:
            return {"status": "blocked", "blockers": ["fixture_rollback_failure"]}
        return {
            "status": "passed",
            "skill_id": skill_id,
            "transaction_id": transaction_id,
            "restored_status": "manually_rolled_back",
        }


def _api(fake: FakeSkillGuard, *, include_install: bool = True) -> SkillGuardConsumerApi:
    return SkillGuardConsumerApi(
        skillguard_root=Path("skillguard"),
        scripts_root=Path("skillguard/scripts"),
        consumer_module_path=Path("skillguard/scripts/consumer_distribution.py"),
        consumer_module_sha256="sha256:fixture",
        consumer_distribution_plan=fake.plan,
        audit_consumer_distribution=fake.audit,
        prepare_target_stage=fake.prepare if include_install else None,
        verify_target_stage=fake.verify if include_install else None,
        activate_target_stage=fake.activate if include_install else None,
        rollback_target_install=fake.rollback if include_install else None,
    )


def test_suite_plan_is_exact_ten_and_creates_no_stage(tmp_path: Path) -> None:
    fake = FakeSkillGuard()
    stage = tmp_path / "stage"

    result = build_suite_plan(ROOT, _api(fake, include_install=False))

    assert result["status"] == "passed"
    assert result["member_ids"] == list(PHYSICSGUARD_SKILL_IDS)
    assert fake.events == [("plan", skill_id) for skill_id in PHYSICSGUARD_SKILL_IDS]
    assert not stage.exists()


def test_all_members_are_prepared_then_all_verified_before_any_activation(
    tmp_path: Path,
) -> None:
    fake = FakeSkillGuard()

    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "passed"
    assert result["suite_state"] == "committed_pending_final_audit"
    phases = [phase for phase, _skill_id in fake.events]
    assert phases == (
        ["plan"] * 10
        + ["prepare"] * 10
        + ["verify"] * 10
        + ["activate"] * 10
    )


@pytest.mark.parametrize("failure_phase", ["prepare", "verify"])
def test_pre_activation_failure_never_activates(
    tmp_path: Path,
    failure_phase: str,
) -> None:
    failed_skill = PHYSICSGUARD_SKILL_IDS[4]
    fake = FakeSkillGuard(
        prepare_failure=failed_skill if failure_phase == "prepare" else None,
        verify_failure=failed_skill if failure_phase == "verify" else None,
    )

    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    assert result["phase"] == failure_phase
    assert all(phase != "activate" for phase, _skill_id in fake.events)


def test_activation_failure_rolls_prior_activations_back_in_reverse(
    tmp_path: Path,
) -> None:
    failed_skill = PHYSICSGUARD_SKILL_IDS[3]
    fake = FakeSkillGuard(activation_failure=failed_skill)

    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    assert result["phase"] == "activate"
    rollback_ids = [
        skill_id for phase, skill_id in fake.events if phase == "rollback"
    ]
    assert rollback_ids == list(reversed(PHYSICSGUARD_SKILL_IDS[:3]))
    assert [row["skill_id"] for row in result["rollbacks"]] == rollback_ids
    assert result["suite_state"] == "rolled_back_clean"


def test_rollback_failure_remains_a_visible_suite_blocker(tmp_path: Path) -> None:
    fake = FakeSkillGuard(
        activation_failure=PHYSICSGUARD_SKILL_IDS[3],
        rollback_failure=PHYSICSGUARD_SKILL_IDS[1],
    )

    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    assert f"member_rollback_blocked:{PHYSICSGUARD_SKILL_IDS[1]}" in result[
        "blockers"
    ]
    assert result["suite_state"] == "cleanup_unconfirmed"
    assert "cleanup_unconfirmed" in result["blockers"]


def test_passed_activation_with_wrong_identity_is_also_rolled_back(
    tmp_path: Path,
) -> None:
    fake = FakeSkillGuard()
    mismatched_skill = PHYSICSGUARD_SKILL_IDS[2]
    original_activate = fake.activate

    def activate_with_identity_drift(*args, **kwargs):
        report = original_activate(*args, **kwargs)
        if report.get("skill_id") == mismatched_skill:
            report["skill_id"] = "foreign-skill"
        return report

    fake.activate = activate_with_identity_drift  # type: ignore[method-assign]

    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    rollback_ids = [
        skill_id for phase, skill_id in fake.events if phase == "rollback"
    ]
    assert rollback_ids == list(reversed(PHYSICSGUARD_SKILL_IDS[:3]))


@pytest.mark.parametrize(
    "drift",
    ["skill_id", "transaction_id", "restored_status"],
)
def test_passed_rollback_requires_exact_terminal_identity(
    tmp_path: Path,
    drift: str,
) -> None:
    fake = FakeSkillGuard(activation_failure=PHYSICSGUARD_SKILL_IDS[2])
    original_rollback = fake.rollback

    def rollback_with_identity_drift(*args, **kwargs):
        report = original_rollback(*args, **kwargs)
        if report.get("skill_id") == PHYSICSGUARD_SKILL_IDS[1]:
            report[drift] = "foreign-value"
        return report

    fake.rollback = rollback_with_identity_drift  # type: ignore[method-assign]
    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    assert result["suite_state"] == "cleanup_unconfirmed"
    row = next(
        item
        for item in result["rollbacks"]
        if item["skill_id"] == PHYSICSGUARD_SKILL_IDS[1]
    )
    assert row["report"]["blockers"] == ["rollback_identity_mismatch"]


def test_current_activation_internal_rollback_failure_marks_cleanup_unconfirmed(
    tmp_path: Path,
) -> None:
    fake = FakeSkillGuard()
    failed_skill = PHYSICSGUARD_SKILL_IDS[2]
    original_activate = fake.activate

    def activate_with_cleanup_failure(*args, **kwargs):
        report = original_activate(*args, **kwargs)
        if report.get("skill_id") == failed_skill:
            return {
                "status": "blocked",
                "skill_id": failed_skill,
                "blockers": ["target_rollback_failed"],
            }
        return report

    fake.activate = activate_with_cleanup_failure  # type: ignore[method-assign]
    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    assert result["suite_state"] == "cleanup_unconfirmed"
    assert "cleanup_unconfirmed" in result["blockers"]


def test_rollback_exception_does_not_stop_remaining_reverse_cleanup(
    tmp_path: Path,
) -> None:
    fake = FakeSkillGuard(activation_failure=PHYSICSGUARD_SKILL_IDS[4])
    original_rollback = fake.rollback

    def rollback_with_exception(codex_home, skill_id, transaction_id):
        if skill_id == PHYSICSGUARD_SKILL_IDS[2]:
            fake.events.append(("rollback", skill_id))
            raise RuntimeError("fixture rollback exception")
        return original_rollback(codex_home, skill_id, transaction_id)

    fake.rollback = rollback_with_exception  # type: ignore[method-assign]
    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake),
    )

    assert result["status"] == "blocked"
    assert result["suite_state"] == "cleanup_unconfirmed"
    rollback_ids = [
        skill_id for phase, skill_id in fake.events if phase == "rollback"
    ]
    assert rollback_ids == list(reversed(PHYSICSGUARD_SKILL_IDS[:4]))


def test_malformed_skillguard_results_block_without_crashing(tmp_path: Path) -> None:
    fake = FakeSkillGuard()
    fake.plan = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    plan = build_suite_plan(ROOT, _api(fake, include_install=False))
    assert plan["status"] == "blocked"
    assert any("consumer_distribution_plan_not_object" in item for item in plan["blockers"])

    fake = FakeSkillGuard()
    fake.prepare = lambda *_args, **_kwargs: []  # type: ignore[method-assign]
    install = coordinate_suite_install(
        ROOT,
        tmp_path / "stage-2",
        tmp_path / "codex-home-2",
        _api(fake),
    )
    assert install["status"] == "blocked"
    assert install["phase"] == "prepare"


def test_missing_skillguard_install_api_blocks_without_fallback(tmp_path: Path) -> None:
    fake = FakeSkillGuard()

    result = coordinate_suite_install(
        ROOT,
        tmp_path / "stage",
        tmp_path / "codex-home",
        _api(fake, include_install=False),
    )

    assert result["status"] == "blocked"
    assert result["phase"] == "api_preflight"
    assert len(result["blockers"]) == 4
    assert fake.events == []


def test_main_projects_unexpected_failure_as_one_blocked_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class BrokenApi:
        def authority_record(self):
            return {"raw": object()}

    monkeypatch.setattr(
        installer,
        "load_skillguard_consumer_api",
        lambda *_args, **_kwargs: BrokenApi(),
    )
    monkeypatch.setattr(
        installer,
        "build_suite_plan",
        lambda *_args, **_kwargs: {"status": "passed"},
    )

    exit_code = installer.main(["--plan", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert captured.err == ""
    assert captured.out.count("\n") == 1
    assert payload["status"] == "blocked"
    assert payload["phase"] == "machine_output"
