"""Map CSV measurements into the coarse and coupled heated-tank audit snapshots.

Only unit conversion is performed here; connected endpoints and physical intermediate
quantities are deliberately left for the model to evaluate.
"""

import csv
from pathlib import Path
import sys

import yaml


BOUNDARY = "Low-fidelity SI-unit residual audit or blueprint only; not a high-fidelity solver, commercial-tool adapter, or reverse-engineered model."


def value(number, unit, signal, *, factor=None, offset=None, confidence="high", note=None):
    item = {"value": float(number), "unit": unit, "source": "tank_run.csv",
            "external_signal": signal, "mapping_confidence": confidence}
    if factor is not None:
        item["conversion_factor"] = factor
    if offset is not None:
        item["conversion_offset"] = offset
    if note:
        item["conversion_note"] = note
    return item


def snapshots(csv_path: Path, target: Path) -> None:
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    target.mkdir(parents=True, exist_ok=True)
    for step in (30, 70):
        a, b = rows[step], rows[step + 1]
        variables = {
            "lvl_prev.level_m": value(a["level_m"], "m", "level_m@k"),
            "lvl_cur.level_m": value(b["level_m"], "m", "level_m@k+1"),
            "vol.V_dot_out_m3_s": value(a["outflow_m3s"], "m^3/s", "outflow_m3s@k"),
            "inflow_mass.V_dot_m3_s": value(float(a["inflow_Lps"]) * 0.001, "m^3/s", "inflow_Lps@k", factor=0.001, note="L/s to m^3/s"),
            "heat.T_previous_K": value(float(a["T_tank_C"]) + 273.15, "K", "T_tank_C@k", offset=273.15, note="degC to K"),
            "heat.T_current_K": value(float(b["T_tank_C"]) + 273.15, "K", "T_tank_C@k+1", offset=273.15, note="degC to K"),
            "heat.Q_in_W": value(float(a["P_heater_cmd_kW"]) * 1000.0, "W", "P_heater_cmd_kW@k", factor=1000.0, confidence="low", note="kW to W; command, may not be delivered heat"),
            "through.T_in_K": value(float(a["T_in_C"]) + 273.15, "K", "T_in_C@k", offset=273.15, note="degC to K"),
            "loss.T_ambient_K": value(float(a["T_amb_C"]) + 273.15, "K", "T_amb_C@k", offset=273.15, note="degC to K"),
        }
        coupled = dict(variables)
        coupled.pop("heat.Q_in_W")
        coupled["heater_cmd.x"] = value(float(a["P_heater_cmd_kW"]) * 1000.0, "W", "P_heater_cmd_kW@k", factor=1000.0, note="kW to W; measured command, not delivered heat")
        coupled["heater_el.V_V"] = value(a["U_heater_V"], "V", "U_heater_V@k")
        coupled["heater_el.current_A"] = value(a["I_heater_A"], "A", "I_heater_A@k")
        for prefix, selected, model in (("first_step_measured", variables, "first_step_level0.yaml"), ("measured", coupled, "heated_tank.yaml")):
            name = f"{prefix}_k{step}.yaml"
            header = ("# PhysicsGuard observed-values snapshot\n"
                      f"# Purpose: Measured heated-tank signals for CSV rows {step}->{step + 1}.\n"
                      "# Repository: https://github.com/liuyingxuvka/PhysicsGuard\n"
                      f"# Use with: python -m physicsguard.cli hierarchy evaluate {model} {name} --pretty\n"
                      f"# Boundary: {BOUNDARY}\n")
            data = {"observation_name": f"tank_step_{step}", "description": f"tank_run.csv rows {step}->{step + 1}", "variables": selected}
            (target / name).write_text(header + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: map_measured.py CSV OUTPUT_DIRECTORY")
    snapshots(Path(sys.argv[1]), Path(sys.argv[2]))
