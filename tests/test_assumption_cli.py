from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "assumptions"


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "physicsguard.cli", *args],
        cwd=ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_assumptions_inspect_returns_valid_json() -> None:
    result = run_cli("assumptions", "inspect", str(EXAMPLES / "variable_assumption.yaml"), "--pretty")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["active_count"] == 1
    assert data["cards"][0]["application"] == "boundary_residual"


def test_normal_run_on_assumption_example_includes_assumptions_section() -> None:
    result = run_cli("hierarchy", "run", str(EXAMPLES / "variable_assumption.yaml"), "--pretty", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["assumptions"]["cards"][0]["id"] == "assume_coolant_inlet_temperature"
    assert any(residual["role"] == "assumption" for residual in data["top_residuals"])


def test_invalid_assumption_yaml_returns_nonzero(tmp_path: Path) -> None:
    path = tmp_path / "invalid_assumption.yaml"
    path.write_text(
        """
system_name: invalid_assumption
components:
  - id: d
    type: DummyResidualModule
    parameters:
      target: 0.0
assumptions:
  - id: bad
    target_type: variable
    target: d.x
    value: 0.0
    reason: ""
""",
        encoding="utf-8",
    )
    result = run_cli("assumptions", "inspect", str(path), "--pretty")
    assert result.returncode != 0


def test_assumptions_inspect_wrapped_system_preserves_the_same_card(tmp_path: Path) -> None:
    source = EXAMPLES / "parameter_assumption.yaml"
    system = yaml.safe_load(source.read_text(encoding="utf-8"))
    wrapped = {"audit_name": "wrapped_assumptions", "system": system,
               "hierarchy": {"blocks": [{"id": "conductor", "level": 0, "components": ["conductor"]}]}}
    path = tmp_path / "wrapped.yaml"
    path.write_text(yaml.safe_dump(wrapped), encoding="utf-8")
    direct = run_cli("assumptions", "inspect", str(source))
    hierarchical = run_cli("assumptions", "inspect", str(path))
    assert direct.returncode == hierarchical.returncode == 0, direct.stderr + hierarchical.stderr
    before, after = json.loads(direct.stdout), json.loads(hierarchical.stdout)
    assert after["cards"] == before["cards"]
    assert after["active_count"] == before["active_count"] == 1


def test_assumptions_inspect_heated_tank_lists_nameplate_efficiency() -> None:
    path = ROOT / "examples/hierarchical/heated_tank/heated_tank.yaml"
    result = run_cli("assumptions", "inspect", str(path))
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    card = next(item for item in data["cards"] if item["id"] == "heater_nameplate_efficiency")
    assert card["target"] == "heater_eff.efficiency"
    assert card["application"] == "boundary_residual"
    assert data["active_count"] == 1
