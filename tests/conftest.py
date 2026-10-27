from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import numpy as np
from physicsguard.core.registry import VariableRecord
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.registry import ModuleRegistry, default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


FC = ROOT / "examples" / "hierarchical" / "fuel_cell_system"


OBSERVED = ROOT / "examples" / "hierarchical" / "observed_debugging"


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


TANK = ROOT / "examples" / "hierarchical" / "heated_tank"


def _block_lines(text: str) -> dict[str, str]:
    return {line.split(" [L")[0].strip(): line for line in text.splitlines() if " [L" in line}


def system(data: dict) -> SystemSpec:
    return SystemSpec.model_validate(data)


def one_dummy_system(**parameters) -> SystemSpec:
    params = {
        "target": 5.0,
        "lower_bound": -100.0,
        "upper_bound": 100.0,
        "initial_guess": 0.0,
        "scale": 1.0,
    }
    params.update(parameters)
    return system(
        {
            "system_name": "one",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": params,
                }
            ],
        }
    )


class CustomModule(BaseModule):
    def declare_variables(self) -> list[VariableRecord]:
        return [
            VariableRecord(
                name=f"{self.component_id}.y",
                unit=None,
                lower_bound=-1.0,
                upper_bound=1.0,
                initial_guess=0.0,
                scale=1.0,
                source_component=self.component_id,
                local_name="y",
            )
        ]

    def residuals(self, x, registry):
        return []

    def metadata(self) -> dict:
        return {"module_type": self.module_type}


class DuplicateVariableModule(CustomModule):
    def declare_variables(self) -> list[VariableRecord]:
        name = f"{self.component_id}.y"
        return [
            VariableRecord(
                name=name,
                unit=None,
                lower_bound=-1.0,
                upper_bound=1.0,
                initial_guess=0.0,
                scale=1.0,
                source_component=self.component_id,
                local_name="y",
            ),
            VariableRecord(
                name=name,
                unit=None,
                lower_bound=-1.0,
                upper_bound=1.0,
                initial_guess=0.0,
                scale=1.0,
                source_component=self.component_id,
                local_name="y",
            )
        ]


def linear_parameters(**overrides) -> dict:
    parameters = {
        "a": 2.0,
        "b": 1.0,
        "x_lower_bound": -10.0,
        "x_upper_bound": 10.0,
        "x_initial_guess": 0.0,
        "x_scale": 1.0,
        "y_lower_bound": -20.0,
        "y_upper_bound": 20.0,
        "y_initial_guess": 0.0,
        "y_scale": 1.0,
        "residual_scale": 1.0,
    }
    parameters.update(overrides)
    return parameters
