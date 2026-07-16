"""Module registry for PhysicsGuard component factories."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from physicsguard.modules.base import BaseModule

ModuleFactory = Callable[[str, dict[str, Any]], BaseModule]


class ModuleRegistry:
    """Maps module type names to module factories."""

    def __init__(self) -> None:
        self._factories: dict[str, ModuleFactory] = {}

    def register(self, module_type: str, factory: ModuleFactory) -> None:
        if not module_type.strip():
            raise ValueError("module_type cannot be empty")
        if module_type in self._factories:
            raise ValueError(f"module type already registered: {module_type}")
        self._factories[module_type] = factory

    def create(
        self,
        module_type: str,
        component_id: str,
        parameters: dict[str, Any],
    ) -> BaseModule:
        try:
            factory = self._factories[module_type]
        except KeyError as exc:
            known = ", ".join(sorted(self._factories)) or "<none>"
            raise ValueError(
                f"unknown module type '{module_type}'. Registered module types: {known}"
            ) from exc
        return factory(component_id, parameters)

    def registered_types(self) -> list[str]:
        return sorted(self._factories)


def default_module_registry() -> ModuleRegistry:
    from physicsguard.modules.aggregate import (
        AggregateElectricalBusBalanceModule,
        AggregateEfficiencyModule,
        AggregateMassBalanceModule,
        AggregatePowerBalanceModule,
        AggregateSpeciesBalanceModule,
        AggregateThermalBalanceModule,
    )
    from physicsguard.modules.components import (
        ActuatorDeadZoneModule,
        ActuatorFirstOrderSaturationModule,
        ActuatorPositionFeedbackModule,
        AftertreatmentPressureDropModule,
        AntiWindupClampModule,
        BatteryInternalResistanceModule,
        BatteryOCVMapModule,
        BatteryPackPowerModule,
        BatteryPowerLimitCheckModule,
        BatterySOCStepModule,
        BrakeSimpleModule,
        CatalystThermalMassStepModule,
        ChargerSimpleModule,
        CheckValveSimpleModule,
        ChillerSimpleModule,
        ColdPlateSimpleModule,
        CompressorMapSimpleModule,
        CompressorSimpleModule,
        DCDCConverterSimpleModule,
        DuctSegmentSimpleModule,
        EfficiencyMap2DModule,
        ElectricMotorMapModule,
        ElectricMotorSimpleModule,
        EGRMixingModule,
        ElectrolyzerCoolingInterfaceModule,
        ElectrolyzerGasProductionModule,
        ElectrolyzerPolarizationMapModule,
        ElectrolyzerStackBalanceModule,
        ElectrolyzerWaterFeedModule,
        EngineBSFCMapModule,
        EngineAirFuelRatioModule,
        EngineExhaustHeatFlowModule,
        EngineSimpleEfficiencyModule,
        EngineTorqueMapModule,
        EngineVolumetricEfficiencyModule,
        ExpansionTankSimpleModule,
        FlowMergeTemperatureModule,
        FlowSplitModule,
        FuelCellAnodeHydrogenSupplyModule,
        FuelCellAnodeRecirculationModule,
        FuelCellCathodeAirSupplyModule,
        FuelCellCoolantInterfaceModule,
        FuelCellPolarizationMapModule,
        FuelCellStackBalanceModule,
        FuelCellSystemEfficiencyModule,
        GainScheduledPIDModule,
        GasSeparatorSimpleModule,
        GearboxSimpleModule,
        HVBusPowerBalanceModule,
        HumidifierEffectivenessModule,
        IntercoolerSimpleModule,
        InverterSimpleModule,
        LeakOrBypassLinearModule,
        LookupTable2DModule,
        LumpedGasVolumeStepModule,
        LumpedLiquidVolumeStepModule,
        MapAxisBoundsCheckModule,
        MapMonotonicityCheckModule,
        PIDControllerStepModule,
        PipeSegmentSimpleModule,
        PressureReliefValveCheckModule,
        PumpMapSimpleModule,
        PumpSimpleModule,
        RadiatorFanSimpleModule,
        RadiatorSimpleModule,
        RegenerativeBrakeSplitModule,
        SampleAndHoldModule,
        SensorLowPassFilterStepModule,
        SignalDelayStepModule,
        ThermalMassStepModule,
        ThermostatValveModule,
        ThrottleValveSimpleModule,
        ThreeWayValveMixingModule,
        TurboPowerBalanceModule,
        UnitConversionAuditModule,
        VehicleLongitudinalDynamicsStepModule,
        VehicleRoadLoadModule,
        WheelTorqueForceModule,
    )
    from physicsguard.modules.control import (
        BooleanSwitchModule,
        ControlErrorModule,
        DiscreteIntegratorModule,
        FirstOrderLagModule,
        HysteresisStateCheckModule,
        LookupTable1DModule,
        MapBoundsCheckModule,
        PIDAlgebraicModule,
        RateLimiterModule,
        SaturationModule,
        ThresholdStateCheckModule,
    )
    from physicsguard.modules.generic import (
        ConservationSumModule,
        LinearRelationModule,
        RangeCheckModule,
    )
    from physicsguard.modules.dummy import DummyResidualModule
    from physicsguard.modules.physical import (
        AirOxygenMolarFlowModule,
        AmbientHeatLossModule,
        CellVoltageStackVoltageModule,
        ChemicalPowerLHVModule,
        CompressibleIsentropicCompressorPowerModule,
        ConvectiveHeatTransferModule,
        CoolantHeatBalanceModule,
        CurrentDensityModule,
        DensityMassVolumeModule,
        ElectricalPowerModule,
        ElectrochemicalFaradayRateModule,
        ElectrochemicalStackPowerModule,
        EfficiencyModule,
        ForceVelocityPowerModule,
        HeatExchangerEffectivenessModule,
        HumidityRatioFromPartialPressureModule,
        IdealGasStateModule,
        IdealGasDensityModule,
        IncompressibleOrificeModule,
        IncompressiblePressureDropModule,
        IsentropicGasTemperatureRiseModule,
        LinearSpringForceModule,
        MassMolarFlowConversionModule,
        MassBalanceRateModule,
        MixerEnergyBalanceModule,
        MoleFractionFlowModule,
        OhmicRelationModule,
        PressureRatioModule,
        PumpHydraulicPowerModule,
        RadiativeHeatTransferModule,
        RelativeHumidityFromPartialPressureModule,
        RotatingMachineAffinityModule,
        RotationalInertiaTorqueModule,
        SpecificEnthalpyFlowModule,
        StackChemicalEfficiencyModule,
        StoichiometryModule,
        TankLevelVolumeModule,
        TankVolumeRateModule,
        ThermalCapacitanceRateModule,
        ThermalConductorModule,
        TorqueSpeedPowerModule,
        TranslationalInertiaForceModule,
        ViscousDamperForceModule,
        VolumetricMassFlowConversionModule,
        WaterProductionFaradayModule,
        WaterVaporMoleFractionModule,
    )
    from physicsguard.modules.signal import (
        GainBiasModule,
        MappedSignalModule,
        ProductModule,
        RatioModule,
        SensorScaleOffsetModule,
        SumModule,
        UnitScaleModule,
    )

    registry = ModuleRegistry()
    for module_class in (
        AggregatePowerBalanceModule,
        AggregateThermalBalanceModule,
        AggregateMassBalanceModule,
        AggregateSpeciesBalanceModule,
        AggregateElectricalBusBalanceModule,
        AggregateEfficiencyModule,
        LookupTable2DModule,
        EfficiencyMap2DModule,
        PIDControllerStepModule,
        ActuatorFirstOrderSaturationModule,
        PipeSegmentSimpleModule,
        DuctSegmentSimpleModule,
        LumpedGasVolumeStepModule,
        LumpedLiquidVolumeStepModule,
        FlowSplitModule,
        FlowMergeTemperatureModule,
        CheckValveSimpleModule,
        ThrottleValveSimpleModule,
        PressureReliefValveCheckModule,
        LeakOrBypassLinearModule,
        ColdPlateSimpleModule,
        ThermalMassStepModule,
        ThermostatValveModule,
        ThreeWayValveMixingModule,
        ChillerSimpleModule,
        ExpansionTankSimpleModule,
        FuelCellCathodeAirSupplyModule,
        FuelCellAnodeHydrogenSupplyModule,
        FuelCellAnodeRecirculationModule,
        FuelCellCoolantInterfaceModule,
        FuelCellSystemEfficiencyModule,
        ElectrolyzerWaterFeedModule,
        ElectrolyzerGasProductionModule,
        ElectrolyzerCoolingInterfaceModule,
        GasSeparatorSimpleModule,
        BatterySOCStepModule,
        BatteryOCVMapModule,
        BatteryInternalResistanceModule,
        BatteryPackPowerModule,
        BatteryPowerLimitCheckModule,
        HVBusPowerBalanceModule,
        ChargerSimpleModule,
        GearboxSimpleModule,
        WheelTorqueForceModule,
        VehicleRoadLoadModule,
        VehicleLongitudinalDynamicsStepModule,
        BrakeSimpleModule,
        RegenerativeBrakeSplitModule,
        EngineTorqueMapModule,
        EngineAirFuelRatioModule,
        EngineVolumetricEfficiencyModule,
        EngineExhaustHeatFlowModule,
        EGRMixingModule,
        TurboPowerBalanceModule,
        CatalystThermalMassStepModule,
        AftertreatmentPressureDropModule,
        GainScheduledPIDModule,
        AntiWindupClampModule,
        MapAxisBoundsCheckModule,
        MapMonotonicityCheckModule,
        SensorLowPassFilterStepModule,
        ActuatorDeadZoneModule,
        ActuatorPositionFeedbackModule,
        SignalDelayStepModule,
        SampleAndHoldModule,
        UnitConversionAuditModule,
        ElectricMotorSimpleModule,
        ElectricMotorMapModule,
        DCDCConverterSimpleModule,
        InverterSimpleModule,
        CompressorSimpleModule,
        CompressorMapSimpleModule,
        PumpSimpleModule,
        PumpMapSimpleModule,
        RadiatorSimpleModule,
        RadiatorFanSimpleModule,
        HumidifierEffectivenessModule,
        IntercoolerSimpleModule,
        FuelCellStackBalanceModule,
        FuelCellPolarizationMapModule,
        ElectrolyzerStackBalanceModule,
        ElectrolyzerPolarizationMapModule,
        EngineSimpleEfficiencyModule,
        EngineBSFCMapModule,
    ):
        registry.register(
            module_class.__name__,
            lambda component_id, parameters, module_class=module_class: module_class(
                component_id,
                parameters,
            ),
        )
    registry.register(
        "DummyResidualModule",
        lambda component_id, parameters: DummyResidualModule(component_id, parameters),
    )
    registry.register(
        "LinearRelationModule",
        lambda component_id, parameters: LinearRelationModule(component_id, parameters),
    )
    registry.register(
        "ConservationSumModule",
        lambda component_id, parameters: ConservationSumModule(component_id, parameters),
    )
    registry.register(
        "RangeCheckModule",
        lambda component_id, parameters: RangeCheckModule(component_id, parameters),
    )
    registry.register(
        "CoolantHeatBalanceModule",
        lambda component_id, parameters: CoolantHeatBalanceModule(component_id, parameters),
    )
    registry.register(
        "IdealGasStateModule",
        lambda component_id, parameters: IdealGasStateModule(component_id, parameters),
    )
    registry.register(
        "ElectrochemicalFaradayRateModule",
        lambda component_id, parameters: ElectrochemicalFaradayRateModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "ThermalConductorModule",
        lambda component_id, parameters: ThermalConductorModule(component_id, parameters),
    )
    registry.register(
        "ConvectiveHeatTransferModule",
        lambda component_id, parameters: ConvectiveHeatTransferModule(component_id, parameters),
    )
    registry.register(
        "ThermalCapacitanceRateModule",
        lambda component_id, parameters: ThermalCapacitanceRateModule(component_id, parameters),
    )
    registry.register(
        "IncompressiblePressureDropModule",
        lambda component_id, parameters: IncompressiblePressureDropModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "IncompressibleOrificeModule",
        lambda component_id, parameters: IncompressibleOrificeModule(component_id, parameters),
    )
    registry.register(
        "MassBalanceRateModule",
        lambda component_id, parameters: MassBalanceRateModule(component_id, parameters),
    )
    registry.register(
        "MixerEnergyBalanceModule",
        lambda component_id, parameters: MixerEnergyBalanceModule(component_id, parameters),
    )
    registry.register(
        "PumpHydraulicPowerModule",
        lambda component_id, parameters: PumpHydraulicPowerModule(component_id, parameters),
    )
    registry.register(
        "OhmicRelationModule",
        lambda component_id, parameters: OhmicRelationModule(component_id, parameters),
    )
    registry.register(
        "ElectricalPowerModule",
        lambda component_id, parameters: ElectricalPowerModule(component_id, parameters),
    )
    registry.register(
        "StoichiometryModule",
        lambda component_id, parameters: StoichiometryModule(component_id, parameters),
    )
    registry.register(
        "ElectrochemicalStackPowerModule",
        lambda component_id, parameters: ElectrochemicalStackPowerModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "GainBiasModule",
        lambda component_id, parameters: GainBiasModule(component_id, parameters),
    )
    registry.register(
        "SumModule",
        lambda component_id, parameters: SumModule(component_id, parameters),
    )
    registry.register(
        "ProductModule",
        lambda component_id, parameters: ProductModule(component_id, parameters),
    )
    registry.register(
        "RatioModule",
        lambda component_id, parameters: RatioModule(component_id, parameters),
    )
    registry.register(
        "UnitScaleModule",
        lambda component_id, parameters: UnitScaleModule(component_id, parameters),
    )
    registry.register(
        "SaturationModule",
        lambda component_id, parameters: SaturationModule(component_id, parameters),
    )
    registry.register(
        "RateLimiterModule",
        lambda component_id, parameters: RateLimiterModule(component_id, parameters),
    )
    registry.register(
        "FirstOrderLagModule",
        lambda component_id, parameters: FirstOrderLagModule(component_id, parameters),
    )
    registry.register(
        "SensorScaleOffsetModule",
        lambda component_id, parameters: SensorScaleOffsetModule(component_id, parameters),
    )
    registry.register(
        "MappedSignalModule",
        lambda component_id, parameters: MappedSignalModule(component_id, parameters),
    )
    registry.register(
        "LookupTable1DModule",
        lambda component_id, parameters: LookupTable1DModule(component_id, parameters),
    )
    registry.register(
        "MapBoundsCheckModule",
        lambda component_id, parameters: MapBoundsCheckModule(component_id, parameters),
    )
    registry.register(
        "PressureRatioModule",
        lambda component_id, parameters: PressureRatioModule(component_id, parameters),
    )
    registry.register(
        "EfficiencyModule",
        lambda component_id, parameters: EfficiencyModule(component_id, parameters),
    )
    registry.register(
        "TorqueSpeedPowerModule",
        lambda component_id, parameters: TorqueSpeedPowerModule(component_id, parameters),
    )
    registry.register(
        "CellVoltageStackVoltageModule",
        lambda component_id, parameters: CellVoltageStackVoltageModule(component_id, parameters),
    )
    registry.register(
        "CurrentDensityModule",
        lambda component_id, parameters: CurrentDensityModule(component_id, parameters),
    )
    registry.register(
        "ControlErrorModule",
        lambda component_id, parameters: ControlErrorModule(component_id, parameters),
    )
    registry.register(
        "PIDAlgebraicModule",
        lambda component_id, parameters: PIDAlgebraicModule(component_id, parameters),
    )
    registry.register(
        "DiscreteIntegratorModule",
        lambda component_id, parameters: DiscreteIntegratorModule(component_id, parameters),
    )
    registry.register(
        "HysteresisStateCheckModule",
        lambda component_id, parameters: HysteresisStateCheckModule(component_id, parameters),
    )
    registry.register(
        "BooleanSwitchModule",
        lambda component_id, parameters: BooleanSwitchModule(component_id, parameters),
    )
    registry.register(
        "ThresholdStateCheckModule",
        lambda component_id, parameters: ThresholdStateCheckModule(component_id, parameters),
    )
    registry.register(
        "MassMolarFlowConversionModule",
        lambda component_id, parameters: MassMolarFlowConversionModule(component_id, parameters),
    )
    registry.register(
        "MoleFractionFlowModule",
        lambda component_id, parameters: MoleFractionFlowModule(component_id, parameters),
    )
    registry.register(
        "VolumetricMassFlowConversionModule",
        lambda component_id, parameters: VolumetricMassFlowConversionModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "DensityMassVolumeModule",
        lambda component_id, parameters: DensityMassVolumeModule(component_id, parameters),
    )
    registry.register(
        "IdealGasDensityModule",
        lambda component_id, parameters: IdealGasDensityModule(component_id, parameters),
    )
    registry.register(
        "SpecificEnthalpyFlowModule",
        lambda component_id, parameters: SpecificEnthalpyFlowModule(component_id, parameters),
    )
    registry.register(
        "RelativeHumidityFromPartialPressureModule",
        lambda component_id, parameters: RelativeHumidityFromPartialPressureModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "HumidityRatioFromPartialPressureModule",
        lambda component_id, parameters: HumidityRatioFromPartialPressureModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "WaterVaporMoleFractionModule",
        lambda component_id, parameters: WaterVaporMoleFractionModule(component_id, parameters),
    )
    registry.register(
        "HeatExchangerEffectivenessModule",
        lambda component_id, parameters: HeatExchangerEffectivenessModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "RadiativeHeatTransferModule",
        lambda component_id, parameters: RadiativeHeatTransferModule(component_id, parameters),
    )
    registry.register(
        "AmbientHeatLossModule",
        lambda component_id, parameters: AmbientHeatLossModule(component_id, parameters),
    )
    registry.register(
        "CompressibleIsentropicCompressorPowerModule",
        lambda component_id, parameters: CompressibleIsentropicCompressorPowerModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "IsentropicGasTemperatureRiseModule",
        lambda component_id, parameters: IsentropicGasTemperatureRiseModule(
            component_id,
            parameters,
        ),
    )
    registry.register(
        "RotatingMachineAffinityModule",
        lambda component_id, parameters: RotatingMachineAffinityModule(component_id, parameters),
    )
    registry.register(
        "TankLevelVolumeModule",
        lambda component_id, parameters: TankLevelVolumeModule(component_id, parameters),
    )
    registry.register(
        "TankVolumeRateModule",
        lambda component_id, parameters: TankVolumeRateModule(component_id, parameters),
    )
    registry.register(
        "ForceVelocityPowerModule",
        lambda component_id, parameters: ForceVelocityPowerModule(component_id, parameters),
    )
    registry.register(
        "LinearSpringForceModule",
        lambda component_id, parameters: LinearSpringForceModule(component_id, parameters),
    )
    registry.register(
        "ViscousDamperForceModule",
        lambda component_id, parameters: ViscousDamperForceModule(component_id, parameters),
    )
    registry.register(
        "TranslationalInertiaForceModule",
        lambda component_id, parameters: TranslationalInertiaForceModule(component_id, parameters),
    )
    registry.register(
        "RotationalInertiaTorqueModule",
        lambda component_id, parameters: RotationalInertiaTorqueModule(component_id, parameters),
    )
    registry.register(
        "ChemicalPowerLHVModule",
        lambda component_id, parameters: ChemicalPowerLHVModule(component_id, parameters),
    )
    registry.register(
        "StackChemicalEfficiencyModule",
        lambda component_id, parameters: StackChemicalEfficiencyModule(component_id, parameters),
    )
    registry.register(
        "AirOxygenMolarFlowModule",
        lambda component_id, parameters: AirOxygenMolarFlowModule(component_id, parameters),
    )
    registry.register(
        "WaterProductionFaradayModule",
        lambda component_id, parameters: WaterProductionFaradayModule(component_id, parameters),
    )
    return registry
