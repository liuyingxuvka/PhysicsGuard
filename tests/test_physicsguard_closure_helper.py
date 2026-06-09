from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def _load_closure_script() -> ModuleType:
    path = ROOT / "skill" / "physicsguard-ai-debugging" / "scripts" / "physicsguard_closure_check.py"
    spec = importlib.util.spec_from_file_location("physicsguard_closure_check", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_closure_flags_signal_mapping_issue_codes(tmp_path: Path) -> None:
    closure = _load_closure_script()
    ledger = tmp_path / "ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "signal_mapping_ledger": [
                    {
                        "physics_variable": "controller_q_gain.x",
                        "issue_codes": ["low_confidence", "missing_conversion"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = closure.check(argparse.Namespace(ledger=ledger, audit=None, observed=None))

    assert result["closure_status"] == "partial"
    assert any(item["type"] == "signal_mapping_review_required" for item in result["findings"])
    assert any(item["action"] == "review_signal_mapping_confidence_units_and_staleness" for item in result["next_actions"])


def test_closure_flags_skipped_checks(tmp_path: Path) -> None:
    closure = _load_closure_script()
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"skipped_checks": ["same-family unit review"]}), encoding="utf-8")

    result = closure.check(argparse.Namespace(ledger=ledger, audit=None, observed=None))

    assert any(item["type"] == "skipped_physicsguard_checks" for item in result["findings"])
    assert any(item["action"] == "run_or_scope_skipped_physicsguard_checks" for item in result["next_actions"])
