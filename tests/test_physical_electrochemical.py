from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.physical.constants import FARADAY_CONSTANT
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def make_system(parameters: dict | None = None) -> SystemSpec:
    params = {"n_cells": 400.0, "electrons_per_mole": 2.0}
    if parameters:
        params.update(parameters)
    return SystemSpec.model_validate(
        {
            "system_name": "faraday",
            "components": [
                {
                    "id": "faraday",
                    "type": "ElectrochemicalFaradayRateModule",
                    "parameters": params,
                }
            ],
        }
    )


def expected_rate(current: float = 100.0) -> float:
    return 400.0 * current / (2.0 * FARADAY_CONSTANT)


def test_faraday_rate_zero_residual() -> None:
    builder = ResidualBuilder(make_system())
    registry = builder.build_registry()
    x = registry.dict_to_vector(
        {
            "faraday.current_A": 100.0,
            "faraday.n_dot_mol_s": expected_rate(),
        }
    )
    record = builder.diagnostic_residual_records(x)[0]
    assert record.normalized_value == pytest.approx(0.0)
    assert record.role == "equation"
    assert record.diagnostic_key == "faraday_rate_mismatch"


def test_faraday_invalid_n_cells_fails() -> None:
    builder = ResidualBuilder(make_system({"n_cells": 0.0}))
    with pytest.raises(ValueError, match="n_cells"):
        builder.build_registry()


def test_faraday_invalid_electrons_per_mole_fails() -> None:
    builder = ResidualBuilder(make_system({"electrons_per_mole": 0.0}))
    with pytest.raises(ValueError, match="electrons_per_mole"):
        builder.build_registry()


def test_faraday_invalid_efficiency_fails() -> None:
    builder = ResidualBuilder(make_system({"faradaic_efficiency": 1.5}))
    with pytest.raises(ValueError, match="faradaic_efficiency"):
        builder.build_registry()


def test_faraday_yaml_example_solves_n_dot() -> None:
    spec = load_system_spec(ROOT / "examples" / "physical_faraday_rate.yaml")
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
    assert result.variables["faraday.n_dot_mol_s"] == pytest.approx(
        expected_rate(),
        rel=0,
        abs=1e-6,
    )


def test_faraday_solves_current_from_n_dot_boundary() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "faraday_current",
            "components": [
                {
                    "id": "faraday",
                    "type": "ElectrochemicalFaradayRateModule",
                    "parameters": {
                        "n_cells": 400.0,
                        "electrons_per_mole": 2.0,
                        "current_initial_guess": 10.0,
                    },
                }
            ],
            "boundaries": [{"variable": "faraday.n_dot_mol_s", "value": expected_rate()}],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
    assert result.variables["faraday.current_A"] == pytest.approx(100.0, rel=0, abs=1e-3)
