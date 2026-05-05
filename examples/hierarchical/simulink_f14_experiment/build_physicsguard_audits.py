"""Generate PhysicsGuard hierarchical YAML for the local Simulink F14 bughunt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "outputs" / "f14_signal_snapshot.json"
OUT_DIR = ROOT / "generated"


def main() -> None:
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("f14_*.yaml"):
        old.unlink()

    clean = data["clean"]["signals"]
    fault = data["fault"]["signals"]
    nominal_kq = float(data["nominal_Kq"])

    writes = {
        "f14_bughunt_level0_clean.yaml": build_level0("clean", clean, clean),
        "f14_bughunt_level0_fault.yaml": build_level0("fault", clean, fault),
        "f14_bughunt_level1_fault.yaml": build_level1(clean, fault),
        "f14_bughunt_level2_controller_fault.yaml": build_level2_controller(fault, nominal_kq),
    }
    for name, payload in writes.items():
        path = OUT_DIR / name
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        print(f"Wrote {path}")


def build_level0(case_name: str, clean: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    audit_name = f"simulink_f14_bughunt_level0_{case_name}"
    checks = [
        dummy_check("alpha_response", clean["alpha_rad_final"], observed["alpha_rad_final"], 0.005, "rad"),
        dummy_check("nz_response", clean["nz_pilot_g_final"], observed["nz_pilot_g_final"], 0.05, "g"),
    ]
    return {
        "audit_name": audit_name,
        "description": "Level 0: only final-response checks from a copied Simulink f14 run.",
        "system": {
            "system_name": audit_name,
            "components": [item["component"] for item in checks],
            "boundaries": [item["boundary"] for item in checks],
            "solver": {"tolerance": 1.0e-8, "audit_threshold": 1.0, "max_iterations": 50},
        },
        "hierarchy": {
            "blocks": [
                {
                    "id": "f14_flight_control",
                    "name": "F14 flight-control loop",
                    "level": 0,
                    "components": [item["component"]["id"] for item in checks],
                    "required_variables": [f"{item['component']['id']}.x" for item in checks],
                    "refinement_template_ids": ["simulink_f14_experiment/f14_bughunt_level1_fault"],
                    "metadata": {
                        "audit_resolution": "final outputs only",
                        "observed_signals": ["alpha_rad_final", "nz_pilot_g_final"],
                    },
                }
            ],
            "refinement_rules": [
                {
                    "id": "refine_f14_on_final_response",
                    "block_id": "f14_flight_control",
                    "trigger_diagnostic_keys": ["dummy_target_mismatch"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["simulink_f14_experiment/f14_bughunt_level1_fault"],
                    "next_required_variables": [
                        "controller command",
                        "actuator deflection",
                        "aircraft alpha response",
                    ],
                    "rationale": "Final aircraft response differs from the clean target; inspect major subsystem signal boundaries.",
                    "priority": 10,
                }
            ],
        },
        "metadata": {"experiment": "simulink_f14_progressive_bughunt", "case": case_name},
    }


def build_level1(clean: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    audit_name = "simulink_f14_bughunt_level1_fault"
    specs = [
        ("controller_command", "controller", "controller_command_final", 0.01, "deg"),
        ("actuator_deflection", "actuator", "actuator_deflection_final", 0.02, "deg"),
        ("aircraft_alpha", "aircraft", "alpha_rad_final", 0.02, "rad"),
        ("aircraft_nz", "aircraft", "nz_pilot_g_final", 0.20, "g"),
    ]
    checks = [
        {
            "block": block,
            **dummy_check(name, clean[signal], observed[signal], tolerance, unit),
        }
        for name, block, signal, tolerance, unit in specs
    ]
    return {
        "audit_name": audit_name,
        "description": "Level 1: compare major f14 subsystem boundary signals before inspecting internals.",
        "system": {
            "system_name": audit_name,
            "components": [item["component"] for item in checks],
            "boundaries": [item["boundary"] for item in checks],
            "solver": {"tolerance": 1.0e-8, "audit_threshold": 1.0, "max_iterations": 50},
        },
        "hierarchy": {
            "blocks": [
                {
                    "id": "f14_flight_control",
                    "name": "F14 flight-control loop",
                    "level": 0,
                    "components": [],
                    "refinement_template_ids": ["simulink_f14_experiment/f14_bughunt_level2_controller_fault"],
                },
                {
                    "id": "controller",
                    "name": "Controller",
                    "level": 1,
                    "parent_id": "f14_flight_control",
                    "components": component_ids(checks, "controller"),
                    "required_variables": variables(checks, "controller"),
                    "refinement_template_ids": ["simulink_f14_experiment/f14_bughunt_level2_controller_fault"],
                },
                {
                    "id": "actuator",
                    "name": "Actuator",
                    "level": 1,
                    "parent_id": "f14_flight_control",
                    "components": component_ids(checks, "actuator"),
                    "required_variables": variables(checks, "actuator"),
                },
                {
                    "id": "aircraft",
                    "name": "Aircraft dynamics",
                    "level": 1,
                    "parent_id": "f14_flight_control",
                    "components": component_ids(checks, "aircraft"),
                    "required_variables": variables(checks, "aircraft"),
                },
            ],
            "refinement_rules": [
                {
                    "id": "refine_controller_boundary_mismatch",
                    "block_id": "controller",
                    "trigger_diagnostic_keys": ["dummy_target_mismatch"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["simulink_f14_experiment/f14_bughunt_level2_controller_fault"],
                    "next_required_variables": [
                        "Controller/Gain2 input",
                        "Controller/Gain2 output",
                        "controller command",
                    ],
                    "next_required_parameters": ["nominal pitch-rate feedback gain"],
                    "rationale": "Controller boundary signal is already inconsistent; inspect controller internal signal chain.",
                    "priority": 20,
                }
            ],
        },
        "metadata": {"experiment": "simulink_f14_progressive_bughunt", "case": "fault"},
    }


def build_level2_controller(observed: dict[str, Any], nominal_kq: float) -> dict[str, Any]:
    audit_name = "simulink_f14_bughunt_level2_controller_fault"
    component = linear_gain_component(observed, nominal_kq)
    return {
        "audit_name": audit_name,
        "description": "Level 2: inspect controller pitch-rate feedback signal relation.",
        "system": {
            "system_name": audit_name,
            "components": [component],
            "boundaries": gain_boundaries(observed),
            "solver": {"tolerance": 1.0e-8, "audit_threshold": 1.0, "max_iterations": 50},
        },
        "hierarchy": {
            "blocks": [
                {
                    "id": "controller",
                    "name": "Controller",
                    "level": 1,
                    "components": [],
                },
                {
                    "id": "pitch_rate_feedback",
                    "name": "Pitch-rate feedback path",
                    "level": 2,
                    "parent_id": "controller",
                    "components": ["controller_q_gain"],
                    "required_variables": ["controller_q_gain.x", "controller_q_gain.y"],
                    "required_parameters": ["controller_q_gain.a"],
                    "metadata": {
                        "simulink_block": "f14/Controller/Gain2",
                        "nominal_relation": "q_gain_output = Kq_nominal * q_gain_input",
                    },
                },
            ],
            "refinement_rules": [
                {
                    "id": "inspect_pitch_rate_feedback_gain",
                    "block_id": "pitch_rate_feedback",
                    "trigger_diagnostic_keys": ["linear_relation_mismatch"],
                    "score_threshold": 1.0,
                    "next_template_ids": ["simulink_f14_experiment/manual_parameter_or_unit_review"],
                    "next_required_variables": [
                        "Controller/Gain2 input time series",
                        "Controller/Gain2 output time series",
                    ],
                    "next_required_parameters": [
                        "actual Controller/Gain2 gain",
                        "controller sign convention",
                    ],
                    "rationale": "Pitch-rate feedback output is inconsistent with the nominal sign/gain relation.",
                    "priority": 30,
                }
            ],
        },
        "metadata": {"experiment": "simulink_f14_progressive_bughunt", "case": "fault"},
    }


def dummy_check(name: str, target: Any, observed: Any, tolerance: float, unit: str) -> dict[str, Any]:
    target_f = float(target)
    observed_f = float(observed)
    margin = max(10.0 * abs(target_f), 10.0 * abs(observed_f), 10.0, 100.0 * tolerance)
    component_id = f"{name}_target"
    return {
        "component": {
            "id": component_id,
            "type": "DummyResidualModule",
            "parameters": {
                "target": target_f,
                "lower_bound": min(target_f, observed_f) - margin,
                "upper_bound": max(target_f, observed_f) + margin,
                "initial_guess": observed_f,
                "scale": tolerance,
                "unit": unit,
            },
        },
        "boundary": {
            "variable": f"{component_id}.x",
            "value": observed_f,
            "scale": 1.0e-6,
            "description": f"Observed copied-Simulink final value for {name}.",
        },
    }


def component_ids(checks: list[dict[str, Any]], block_id: str) -> list[str]:
    return [item["component"]["id"] for item in checks if item["block"] == block_id]


def variables(checks: list[dict[str, Any]], block_id: str) -> list[str]:
    return [f"{item['component']['id']}.x" for item in checks if item["block"] == block_id]


def linear_gain_component(values: dict[str, Any], nominal_kq: float) -> dict[str, Any]:
    x = float(values["q_gain_input_final"])
    y = float(values["q_gain_output_final"])
    expected = nominal_kq * x
    margin = max(10.0 * abs(x), 10.0 * abs(y), 10.0 * abs(expected), 10.0)
    residual_scale = max(0.05 * abs(expected), 0.01)
    return {
        "id": "controller_q_gain",
        "type": "LinearRelationModule",
        "parameters": {
            "a": nominal_kq,
            "b": 0.0,
            "residual_scale": residual_scale,
            "x_lower_bound": min(x, 0.0) - margin,
            "x_upper_bound": max(x, 0.0) + margin,
            "x_initial_guess": x,
            "x_scale": max(abs(x), 1.0),
            "x_unit": "rad/s",
            "y_lower_bound": min(y, expected, 0.0) - margin,
            "y_upper_bound": max(y, expected, 0.0) + margin,
            "y_initial_guess": y,
            "y_scale": max(abs(y), abs(expected), 1.0),
            "y_unit": "controller command contribution",
        },
    }


def gain_boundaries(values: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "variable": "controller_q_gain.x",
            "value": float(values["q_gain_input_final"]),
            "scale": 1.0e-6,
            "description": "Logged final input to copied Simulink Controller/Gain2.",
        },
        {
            "variable": "controller_q_gain.y",
            "value": float(values["q_gain_output_final"]),
            "scale": 1.0e-6,
            "description": "Logged final output from copied Simulink Controller/Gain2.",
        },
    ]


if __name__ == "__main__":
    main()
