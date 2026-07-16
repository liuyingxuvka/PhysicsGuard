from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = (
    ROOT
    / "openspec"
    / "changes"
    / "enforce-validation-adequacy-and-predictive-rollout"
    / "verification-contract.yaml",
)


def test_active_openspec_changes_only_consume_one_external_parent_receipt() -> None:
    assert CONTRACTS
    for path in CONTRACTS:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        checks = payload["checks"]
        assert len(checks) == 1
        check = checks[0]
        assert check["kind"] == "receipt"
        assert "command" not in check
        assert "execution_owner" not in check
        assert check["semantic_check_id"]
        assert check["execution_id"]
        assert check["semantic_check_id"] != check["execution_id"]
        assert set(check["receipt_ref"]) == {"provider_id", "work_package_id", "adapter", "ref_path"}
        assert check["receipt_ref"]["provider_id"] == "skillguard"
        assert check["receipt_ref"]["adapter"] == "portable-receipt.v1"
        assert check["receipt_ref"]["work_package_id"] == payload["change"]
        assert check["receipt_ref"]["ref_path"].startswith(f"work/verification/{payload['change']}/")
        assert "--resume" not in path.read_text(encoding="utf-8")
