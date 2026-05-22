from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def _load_ledger_script() -> ModuleType:
    path = ROOT / "scripts" / "check_model_code_ledger.py"
    spec = importlib.util.spec_from_file_location("check_model_code_ledger", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_model_code_ledger_is_valid() -> None:
    checker = _load_ledger_script()

    errors = checker.validate_ledger(ROOT, ROOT / ".flowguard" / "model_code_ledger.yaml")

    assert errors == []


def test_model_code_ledger_reports_missing_symbol(tmp_path: Path) -> None:
    checker = _load_ledger_script()
    ledger = tmp_path / "bad_ledger.yaml"
    ledger.write_text(
        """
ledger_version: 1
entries:
  - id: bad.symbol
    model_file: .flowguard/physicsguard_core_model.py
    model_blocks: [ValidateSystem]
    responsibility: Demonstrate stale symbol detection.
    code_symbols:
      - src/physicsguard/core/residual.py::DefinitelyMissingSymbol
    tests:
      - tests/test_residual_builder.py
    examples:
      - examples/dummy_system.yaml
    validation_commands:
      - command: python scripts/check_model_code_ledger.py
    boundaries:
      - Example boundary.
    stale_when:
      - Example stale condition.
""".strip(),
        encoding="utf-8",
    )

    errors = checker.validate_ledger(ROOT, ledger)

    assert any("DefinitelyMissingSymbol" in error for error in errors)


def test_model_code_ledger_reports_missing_file(tmp_path: Path) -> None:
    checker = _load_ledger_script()
    ledger = tmp_path / "bad_ledger.yaml"
    ledger.write_text(
        """
ledger_version: 1
entries:
  - id: bad.file
    model_file: .flowguard/physicsguard_core_model.py
    model_blocks: [ValidateSystem]
    responsibility: Demonstrate stale file detection.
    code_symbols:
      - src/physicsguard/core/residual.py::ResidualBuilder
    tests:
      - tests/definitely_missing_test_file.py
    examples:
      - examples/dummy_system.yaml
    validation_commands:
      - command: python scripts/check_model_code_ledger.py
    boundaries:
      - Example boundary.
    stale_when:
      - Example stale condition.
""".strip(),
        encoding="utf-8",
    )

    errors = checker.validate_ledger(ROOT, ledger)

    assert any("definitely_missing_test_file.py" in error for error in errors)
