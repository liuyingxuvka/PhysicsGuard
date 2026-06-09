from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def _load_ledger_script() -> ModuleType:
    path = ROOT / "scripts" / "check_module_equation_ledger.py"
    spec = importlib.util.spec_from_file_location("check_module_equation_ledger", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_module_equation_ledger_is_valid() -> None:
    checker = _load_ledger_script()

    errors = checker.validate_ledger(ROOT, ROOT / ".physicsguard" / "module_equation_ledger.yaml")

    assert errors == []


def test_module_equation_ledger_reports_unregistered_module(tmp_path: Path) -> None:
    checker = _load_ledger_script()
    ledger = tmp_path / "bad_ledger.yaml"
    ledger.write_text(
        """
ledger_version: 1
evidence_level: navigation
entries:
  - id: bad.module
    module_types: [DefinitelyMissingModule]
    equation_summary: Example equation summary.
    si_units: [SI units.]
    assumptions: [Explicit assumptions.]
    validity: [Validity boundary.]
    diagnostic_keys: [example_mismatch]
    tests: [tests/test_dummy.py]
    examples: [examples/dummy_system.yaml]
    stale_when: [Module registry changes.]
""".strip(),
        encoding="utf-8",
    )

    errors = checker.validate_ledger(ROOT, ledger)

    assert any("DefinitelyMissingModule" in error for error in errors)


def test_module_equation_ledger_reports_missing_required_fields(tmp_path: Path) -> None:
    checker = _load_ledger_script()
    ledger = tmp_path / "bad_ledger.yaml"
    ledger.write_text(
        """
ledger_version: 1
evidence_level: navigation
entries:
  - id: bad.fields
    module_types: [DummyResidualModule]
""".strip(),
        encoding="utf-8",
    )

    errors = checker.validate_ledger(ROOT, ledger)

    assert any("equation_summary" in error for error in errors)
