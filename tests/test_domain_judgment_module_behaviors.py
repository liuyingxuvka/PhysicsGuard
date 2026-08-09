from __future__ import annotations

import pytest

from physicsguard.core.registry import VariableRegistry
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.schema.system_spec import SystemSpec


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": module_type,
            "components": [
                {"id": "m", "type": module_type, "parameters": parameters}
            ],
        }
    )


def registry_for(spec: SystemSpec) -> VariableRegistry:
    return ResidualBuilder(spec).build_registry()


def records_for(spec: SystemSpec, values: dict[str, float]) -> list[ResidualRecord]:
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    return builder.diagnostic_residual_records(registry.dict_to_vector(values))


def assert_contract(
    records: list[ResidualRecord],
    expected: list[tuple[str, float, float, str, str]],
) -> None:
    assert len(records) == len(expected)
    for record, (local_name, value, scale, role, diagnostic_key) in zip(
        records, expected, strict=True
    ):
        assert record.name == f"m.{local_name}"
        assert record.value == pytest.approx(value)
        assert record.scale == pytest.approx(scale)
        assert record.role == role
        assert record.diagnostic_key == diagnostic_key


def by_key(records: list[ResidualRecord], diagnostic_key: str) -> ResidualRecord:
    return next(record for record in records if record.diagnostic_key == diagnostic_key)


def test_actuator_position_feedback_behavior_and_failure() -> None:
    spec = one_module(
        "ActuatorPositionFeedbackModule",
        {
            "command_to_position_gain": 2.0,
            "feedback_gain": 1.5,
            "feedback_offset": 0.2,
            "residual_scale_position": 0.1,
            "residual_scale_feedback": 0.2,
        },
    )
    good_values = {
        "m.command": 3.0,
        "m.actual_position": 6.0,
        "m.feedback_position": 9.2,
    }
    assert_contract(
        records_for(spec, good_values),
        [
            (
                "actuator_command_position",
                0.0,
                0.1,
                "equation",
                "actuator_command_position_mismatch",
            ),
            (
                "actuator_feedback_position",
                0.0,
                0.2,
                "equation",
                "actuator_feedback_position_mismatch",
            ),
        ],
    )
    bad = records_for(spec, {**good_values, "m.feedback_position": 8.2})
    assert by_key(bad, "actuator_feedback_position_mismatch").value == pytest.approx(
        -1.0
    )
    with pytest.raises(ValueError, match="residual_scale_position"):
        registry_for(
            one_module(
                "ActuatorPositionFeedbackModule",
                {"residual_scale_position": 0.0},
            )
        )


def test_battery_internal_resistance_behavior_and_failure() -> None:
    parameters = {
        "sign_convention": "discharge_positive",
        "residual_scale_V": 0.5,
        "residual_scale_heat_W": 10.0,
    }
    values = {
        "m.OCV_V": 400.0,
        "m.current_A": 10.0,
        "m.terminal_voltage_V": 398.0,
        "m.R_ohm": 0.2,
        "m.heat_generation_W": 20.0,
    }
    assert_contract(
        records_for(one_module("BatteryInternalResistanceModule", parameters), values),
        [
            (
                "battery_terminal_voltage",
                0.0,
                0.5,
                "equation",
                "battery_terminal_voltage_mismatch",
            ),
            (
                "battery_internal_resistance_heat",
                0.0,
                10.0,
                "equation",
                "battery_internal_resistance_heat_mismatch",
            ),
        ],
    )
    charge = records_for(
        one_module(
            "BatteryInternalResistanceModule",
            {**parameters, "sign_convention": "charge_positive"},
        ),
        {**values, "m.terminal_voltage_V": 402.0},
    )
    assert all(record.value == pytest.approx(0.0) for record in charge)
    bad = records_for(
        one_module("BatteryInternalResistanceModule", parameters),
        {**values, "m.heat_generation_W": 25.0},
    )
    assert by_key(bad, "battery_internal_resistance_heat_mismatch").value == pytest.approx(
        5.0
    )
    with pytest.raises(ValueError, match="sign_convention"):
        registry_for(
            one_module(
                "BatteryInternalResistanceModule",
                {"sign_convention": "unsigned"},
            )
        )


def test_battery_pack_power_behavior_sign_convention_and_failure() -> None:
    discharge_spec = one_module(
        "BatteryPackPowerModule",
        {"sign_convention": "discharge_positive", "residual_scale_W": 50.0},
    )
    discharge_values = {
        "m.terminal_voltage_V": 400.0,
        "m.current_A": 10.0,
        "m.power_W": 4000.0,
    }
    assert_contract(
        records_for(discharge_spec, discharge_values),
        [
            (
                "battery_pack_power",
                0.0,
                50.0,
                "equation",
                "battery_pack_power_mismatch",
            )
        ],
    )
    charge = records_for(
        one_module(
            "BatteryPackPowerModule",
            {"sign_convention": "charge_positive", "residual_scale_W": 50.0},
        ),
        {**discharge_values, "m.power_W": -4000.0},
    )[0]
    assert charge.value == pytest.approx(0.0)
    bad = records_for(
        discharge_spec, {**discharge_values, "m.power_W": 3500.0}
    )[0]
    assert bad.value == pytest.approx(-500.0)
    assert bad.normalized_value == pytest.approx(-10.0)
    with pytest.raises(ValueError, match="sign_convention"):
        registry_for(
            one_module("BatteryPackPowerModule", {"sign_convention": "unsigned"})
        )


def test_brake_simple_behavior_and_failure() -> None:
    spec = one_module("BrakeSimpleModule", {"residual_scale_W": 100.0})
    values = {
        "m.brake_force_N": 1000.0,
        "m.vehicle_speed_m_s": 20.0,
        "m.brake_power_W": 20000.0,
    }
    assert_contract(
        records_for(spec, values),
        [("brake_power", 0.0, 100.0, "equation", "brake_power_mismatch")],
    )
    assert records_for(spec, {**values, "m.brake_power_W": 19000.0})[
        0
    ].value == pytest.approx(-1000.0)
    with pytest.raises(ValueError, match="residual_scale_W"):
        registry_for(one_module("BrakeSimpleModule", {"residual_scale_W": 0.0}))


def test_charger_simple_behavior_and_failure() -> None:
    spec = one_module("ChargerSimpleModule", {"residual_scale_W": 100.0})
    values = {
        "m.P_grid_W": 10000.0,
        "m.P_battery_W": 9000.0,
        "m.efficiency": 0.9,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "charger_efficiency_power",
                0.0,
                100.0,
                "equation",
                "charger_efficiency_power_mismatch",
            )
        ],
    )
    assert records_for(spec, {**values, "m.P_battery_W": 8500.0})[
        0
    ].value == pytest.approx(-500.0)
    with pytest.raises(ValueError, match="residual_scale_W"):
        registry_for(one_module("ChargerSimpleModule", {"residual_scale_W": 0.0}))


def test_chiller_simple_behavior_and_failure() -> None:
    spec = one_module("ChillerSimpleModule", {"residual_scale_W": 250.0})
    values = {
        "m.Q_cooling_W": 5000.0,
        "m.P_electric_W": 1000.0,
        "m.COP": 5.0,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "chiller_cop_power",
                0.0,
                250.0,
                "equation",
                "chiller_cop_power_mismatch",
            )
        ],
    )
    assert records_for(spec, {**values, "m.Q_cooling_W": 4500.0})[
        0
    ].value == pytest.approx(-500.0)
    with pytest.raises(ValueError, match="residual_scale_W"):
        registry_for(one_module("ChillerSimpleModule", {"residual_scale_W": 0.0}))


def test_electrolyzer_cooling_interface_behavior_and_failure() -> None:
    spec = one_module(
        "ElectrolyzerCoolingInterfaceModule",
        {"cp_coolant_J_kgK": 4000.0, "residual_scale_W": 100.0},
    )
    values = {
        "m.Q_stack_heat_W": 8000.0,
        "m.m_dot_coolant_kg_s": 2.0,
        "m.T_coolant_in_K": 300.0,
        "m.T_coolant_out_K": 301.0,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "electrolyzer_coolant_heat_interface",
                0.0,
                100.0,
                "equation",
                "electrolyzer_coolant_heat_interface_mismatch",
            )
        ],
    )
    bad = records_for(spec, {**values, "m.T_coolant_out_K": 301.5})[0]
    assert bad.value == pytest.approx(-4000.0)
    with pytest.raises(ValueError, match="cp_coolant_J_kgK"):
        registry_for(
            one_module(
                "ElectrolyzerCoolingInterfaceModule",
                {"cp_coolant_J_kgK": 0.0},
            )
        )


def test_expansion_tank_simple_behavior_and_failure() -> None:
    spec = one_module("ExpansionTankSimpleModule", {"residual_scale_m3": 0.01})
    values = {
        "m.volume_liquid_m3": 0.6,
        "m.volume_total_m3": 1.5,
        "m.fill_fraction": 0.4,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "expansion_tank_fill_fraction",
                0.0,
                0.01,
                "equation",
                "expansion_tank_fill_fraction_mismatch",
            )
        ],
    )
    assert records_for(spec, {**values, "m.volume_liquid_m3": 0.7})[
        0
    ].value == pytest.approx(0.1)
    with pytest.raises(ValueError, match="residual_scale_m3"):
        registry_for(
            one_module("ExpansionTankSimpleModule", {"residual_scale_m3": 0.0})
        )


def test_flow_merge_temperature_behavior_and_failure() -> None:
    spec = one_module(
        "FlowMergeTemperatureModule",
        {
            "mass_residual_scale_kg_s": 0.05,
            "energy_residual_scale_kgK_s": 2.0,
        },
    )
    values = {
        "m.m_dot_1_kg_s": 0.4,
        "m.T_1_K": 300.0,
        "m.m_dot_2_kg_s": 0.6,
        "m.T_2_K": 320.0,
        "m.m_dot_out_kg_s": 1.0,
        "m.T_out_K": 312.0,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "flow_merge_mass_balance",
                0.0,
                0.05,
                "equation",
                "flow_merge_mass_balance_mismatch",
            ),
            (
                "flow_merge_temperature_balance",
                0.0,
                2.0,
                "equation",
                "flow_merge_temperature_balance_mismatch",
            ),
        ],
    )
    bad = records_for(spec, {**values, "m.T_out_K": 310.0})
    assert by_key(bad, "flow_merge_temperature_balance_mismatch").value == pytest.approx(
        -2.0
    )
    with pytest.raises(ValueError, match="energy_residual_scale_kgK_s"):
        registry_for(
            one_module(
                "FlowMergeTemperatureModule",
                {"energy_residual_scale_kgK_s": 0.0},
            )
        )


def test_flow_split_behavior_and_failure() -> None:
    spec = one_module("FlowSplitModule", {"residual_scale_kg_s": 0.2})
    values = {
        "m.m_dot_in_kg_s": 10.0,
        "m.m_dot_out_1_kg_s": 3.0,
        "m.m_dot_out_2_kg_s": 7.0,
        "m.split_fraction": 0.3,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "flow_split_branch_1",
                0.0,
                0.2,
                "equation",
                "flow_split_branch_1_mismatch",
            ),
            (
                "flow_split_branch_2",
                0.0,
                0.2,
                "equation",
                "flow_split_branch_2_mismatch",
            ),
            (
                "flow_split_mass_balance",
                0.0,
                0.2,
                "equation",
                "flow_split_mass_balance_mismatch",
            ),
        ],
    )
    bad = records_for(
        spec,
        {
            **values,
            "m.m_dot_out_1_kg_s": 4.0,
            "m.m_dot_out_2_kg_s": 7.0,
        },
    )
    assert by_key(bad, "flow_split_branch_1_mismatch").value == pytest.approx(1.0)
    assert by_key(bad, "flow_split_mass_balance_mismatch").value == pytest.approx(-1.0)
    with pytest.raises(ValueError, match="residual_scale_kg_s"):
        registry_for(one_module("FlowSplitModule", {"residual_scale_kg_s": 0.0}))


def test_fuel_cell_anode_recirculation_behavior_and_failure() -> None:
    spec = one_module(
        "FuelCellAnodeRecirculationModule",
        {"residual_scale_kg_s": 1.0e-5},
    )
    values = {
        "m.m_dot_fresh_H2_kg_s": 0.002,
        "m.m_dot_recirculation_kg_s": 0.006,
        "m.recirculation_ratio": 3.0,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "fc_anode_recirculation_ratio",
                0.0,
                1.0e-5,
                "equation",
                "fc_anode_recirculation_ratio_mismatch",
            )
        ],
    )
    bad = records_for(spec, {**values, "m.m_dot_recirculation_kg_s": 0.005})[0]
    assert bad.value == pytest.approx(-0.001)
    assert bad.normalized_value == pytest.approx(-100.0)
    with pytest.raises(ValueError, match="residual_scale_kg_s"):
        registry_for(
            one_module(
                "FuelCellAnodeRecirculationModule",
                {"residual_scale_kg_s": 0.0},
            )
        )


def test_fuel_cell_system_efficiency_behavior_and_denominator_failure() -> None:
    spec = one_module(
        "FuelCellSystemEfficiencyModule",
        {
            "residual_scale_power_W": 100.0,
            "residual_scale_efficiency": 0.01,
            "denominator_min_abs": 1.0,
        },
    )
    values = {
        "m.P_stack_W": 50000.0,
        "m.P_aux_W": 5000.0,
        "m.P_net_W": 45000.0,
        "m.m_dot_H2_kg_s": 0.001,
        "m.LHV_H2_J_kg": 120000000.0,
        "m.efficiency": 0.375,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "fc_system_net_power",
                0.0,
                100.0,
                "equation",
                "fc_system_net_power_mismatch",
            ),
            (
                "fc_system_efficiency",
                0.0,
                0.01,
                "equation",
                "fc_system_efficiency_mismatch",
            ),
        ],
    )
    bad = records_for(spec, {**values, "m.efficiency": 0.3})
    assert by_key(bad, "fc_system_efficiency_mismatch").value == pytest.approx(-0.075)
    with pytest.raises(ValueError, match="denominator is too small"):
        records_for(spec, {**values, "m.m_dot_H2_kg_s": 0.0})


def test_gas_separator_simple_behavior_and_failure() -> None:
    spec = one_module("GasSeparatorSimpleModule", {"residual_scale_kg_s": 0.1})
    values = {
        "m.m_dot_in_kg_s": 10.0,
        "m.m_dot_gas_out_kg_s": 1.0,
        "m.m_dot_liquid_out_kg_s": 9.0,
        "m.gas_mass_fraction_in": 0.2,
        "m.separation_efficiency": 0.5,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "gas_separator_gas_outlet",
                0.0,
                0.1,
                "equation",
                "gas_separator_gas_outlet_mismatch",
            ),
            (
                "gas_separator_liquid_outlet",
                0.0,
                0.1,
                "equation",
                "gas_separator_liquid_outlet_mismatch",
            ),
        ],
    )
    bad = records_for(
        spec,
        {
            **values,
            "m.m_dot_gas_out_kg_s": 0.5,
            "m.m_dot_liquid_out_kg_s": 9.5,
        },
    )
    assert by_key(bad, "gas_separator_gas_outlet_mismatch").value == pytest.approx(-0.5)
    assert by_key(bad, "gas_separator_liquid_outlet_mismatch").value == pytest.approx(0.0)
    with pytest.raises(ValueError, match="residual_scale_kg_s"):
        registry_for(
            one_module("GasSeparatorSimpleModule", {"residual_scale_kg_s": 0.0})
        )


def test_pressure_relief_valve_check_behavior_and_bad_branches() -> None:
    spec = one_module(
        "PressureReliefValveCheckModule",
        {
            "flow_tolerance_kg_s": 0.01,
            "pressure_tolerance_Pa": 100.0,
            "residual_scale": 2.0,
        },
    )
    base = {
        "m.p_upstream_Pa": 100000.0,
        "m.p_set_Pa": 120000.0,
        "m.m_dot_relief_kg_s": 0.0,
    }
    assert_contract(
        records_for(spec, base),
        [
            (
                "pressure_relief_valve_state",
                0.0,
                2.0,
                "post_check",
                "pressure_relief_valve_state_violation",
            )
        ],
    )
    premature_flow = records_for(
        spec, {**base, "m.m_dot_relief_kg_s": 0.03}
    )[0]
    assert premature_flow.value == pytest.approx(3.0)
    assert not premature_flow.participates_in_solver
    missing_flow = records_for(
        spec,
        {
            **base,
            "m.p_upstream_Pa": 120500.0,
            "m.m_dot_relief_kg_s": 0.0,
        },
    )[0]
    assert missing_flow.value == pytest.approx(5.0)
    with pytest.raises(ValueError, match="pressure_tolerance_Pa"):
        registry_for(
            one_module(
                "PressureReliefValveCheckModule",
                {"pressure_tolerance_Pa": 0.0},
            )
        )


def test_signal_delay_step_behavior_state_and_failure() -> None:
    spec = one_module("SignalDelayStepModule", {"residual_scale": 0.25})
    values = {"m.input_previous": 4.0, "m.output_current": 4.0}
    assert registry_for(spec).names() == ["m.input_previous", "m.output_current"]
    assert_contract(
        records_for(spec, values),
        [
            (
                "signal_delay_step",
                0.0,
                0.25,
                "equation",
                "signal_delay_step_mismatch",
            )
        ],
    )
    assert records_for(spec, {**values, "m.output_current": 5.0})[
        0
    ].value == pytest.approx(1.0)
    with pytest.raises(ValueError, match="residual_scale"):
        registry_for(one_module("SignalDelayStepModule", {"residual_scale": 0.0}))


def test_three_way_valve_mixing_behavior_and_failure() -> None:
    spec = one_module(
        "ThreeWayValveMixingModule",
        {
            "mass_residual_scale_kg_s": 0.2,
            "energy_residual_scale_kgK_s": 5.0,
        },
    )
    values = {
        "m.m_dot_in_1_kg_s": 3.0,
        "m.T_in_1_K": 300.0,
        "m.m_dot_in_2_kg_s": 7.0,
        "m.T_in_2_K": 330.0,
        "m.m_dot_out_kg_s": 10.0,
        "m.T_out_K": 321.0,
        "m.split_fraction": 0.3,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "three_way_valve_branch_1_flow",
                0.0,
                0.2,
                "equation",
                "three_way_valve_branch_1_flow_mismatch",
            ),
            (
                "three_way_valve_branch_2_flow",
                0.0,
                0.2,
                "equation",
                "three_way_valve_branch_2_flow_mismatch",
            ),
            (
                "three_way_valve_mixing_temperature",
                0.0,
                5.0,
                "equation",
                "three_way_valve_mixing_temperature_mismatch",
            ),
        ],
    )
    bad = records_for(spec, {**values, "m.T_out_K": 320.0})
    assert by_key(bad, "three_way_valve_mixing_temperature_mismatch").value == pytest.approx(
        -10.0
    )
    with pytest.raises(ValueError, match="energy_residual_scale_kgK_s"):
        registry_for(
            one_module(
                "ThreeWayValveMixingModule",
                {"energy_residual_scale_kgK_s": 0.0},
            )
        )


def test_turbo_power_balance_behavior_and_failure() -> None:
    spec = one_module("TurboPowerBalanceModule", {"residual_scale_W": 100.0})
    values = {
        "m.P_turbine_W": 10000.0,
        "m.P_compressor_W": 9000.0,
        "m.mechanical_efficiency": 0.9,
    }
    assert_contract(
        records_for(spec, values),
        [
            (
                "turbo_power_balance",
                0.0,
                100.0,
                "equation",
                "turbo_power_balance_mismatch",
            )
        ],
    )
    assert records_for(spec, {**values, "m.P_compressor_W": 8500.0})[
        0
    ].value == pytest.approx(-500.0)
    with pytest.raises(ValueError, match="residual_scale_W"):
        registry_for(
            one_module("TurboPowerBalanceModule", {"residual_scale_W": 0.0})
        )


def test_electric_motor_efficiency_scale_has_runtime_effect() -> None:
    spec = one_module(
        "ElectricMotorSimpleModule",
        {
            "residual_scale_power_W": 2000.0,
            "residual_scale_efficiency": 0.02,
        },
    )
    values = {
        "m.voltage_V": 400.0,
        "m.current_A": 10.0,
        "m.electrical_power_W": 4000.0,
        "m.torque_Nm": 30.0,
        "m.omega_rad_s": 100.0,
        "m.mechanical_power_W": 3000.0,
        "m.efficiency": 0.75,
    }
    good = records_for(spec, values)
    assert_contract(
        good,
        [
            (
                "motor_electrical_power",
                0.0,
                2000.0,
                "equation",
                "motor_electrical_power_mismatch",
            ),
            (
                "motor_mechanical_power",
                0.0,
                2000.0,
                "equation",
                "motor_mechanical_power_mismatch",
            ),
            (
                "motor_efficiency_power",
                0.0,
                40.0,
                "equation",
                "motor_efficiency_power_mismatch",
            ),
        ],
    )
    bad = records_for(spec, {**values, "m.efficiency": 0.7})
    efficiency_record = by_key(bad, "motor_efficiency_power_mismatch")
    assert efficiency_record.value == pytest.approx(200.0)
    assert efficiency_record.normalized_value == pytest.approx(5.0)
    with pytest.raises(ValueError, match="residual_scale_efficiency"):
        registry_for(
            one_module(
                "ElectricMotorSimpleModule",
                {"residual_scale_efficiency": 0.0},
            )
        )


def test_radiator_simple_retires_unbound_fan_power_path() -> None:
    parameters = {
        "cp_coolant_J_kgK": 1000.0,
        "UA_W_K": 333.3333333333333,
        "residual_scale_heat_W": 100.0,
    }
    values = {
        "m.m_dot_coolant_kg_s": 1.0,
        "m.T_coolant_in_K": 330.0,
        "m.T_coolant_out_K": 320.0,
        "m.T_air_in_K": 300.0,
        "m.Q_rejected_W": 10000.0,
    }
    optional_spec = one_module("RadiatorSimpleModule", parameters)
    assert "m.fan_power_W" not in registry_for(optional_spec).names()
    assert all(
        record.value == pytest.approx(0.0)
        for record in records_for(optional_spec, values)
    )
    with pytest.raises(ValueError, match="use RadiatorFanSimpleModule"):
        registry_for(
            one_module(
                "RadiatorSimpleModule",
                {**parameters, "fan_power_optional": False},
            )
        )


def test_threshold_state_tolerance_controls_post_check_deadband() -> None:
    spec = one_module(
        "ThresholdStateCheckModule",
        {
            "threshold": 5.0,
            "state_tolerance": 0.2,
            "residual_scale": 2.0,
        },
    )
    within = records_for(spec, {"m.input": 6.0, "m.state": 0.85})
    assert_contract(
        within,
        [
            (
                "threshold_state_check",
                0.0,
                0.4,
                "post_check",
                "threshold_state_violation",
            )
        ],
    )
    bad_on = records_for(spec, {"m.input": 6.0, "m.state": 0.0})[0]
    assert bad_on.value == pytest.approx(-0.8)
    assert bad_on.scale == pytest.approx(0.4)
    assert bad_on.normalized_value == pytest.approx(-2.0)
    assert not bad_on.participates_in_solver
    bad_off = records_for(spec, {"m.input": 4.0, "m.state": 0.5})[0]
    assert bad_off.value == pytest.approx(0.3)
    with pytest.raises(ValueError, match="state_tolerance"):
        registry_for(
            one_module(
                "ThresholdStateCheckModule",
                {"threshold": 5.0, "state_tolerance": 0.0},
            )
        )
