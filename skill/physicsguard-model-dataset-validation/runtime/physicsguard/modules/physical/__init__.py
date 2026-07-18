"""Low-fidelity physical audit modules."""

from physicsguard.modules.physical.additional import (
    CellVoltageStackVoltageModule,
    CurrentDensityModule,
    EfficiencyModule,
    PressureRatioModule,
    TorqueSpeedPowerModule,
)
from physicsguard.modules.physical.electrochemical_extra import (
    AirOxygenMolarFlowModule,
    ChemicalPowerLHVModule,
    StackChemicalEfficiencyModule,
    WaterProductionFaradayModule,
)
from physicsguard.modules.physical.electrical import ElectricalPowerModule, OhmicRelationModule
from physicsguard.modules.physical.electrochemical import (
    ElectrochemicalFaradayRateModule,
    ElectrochemicalStackPowerModule,
    StoichiometryModule,
)
from physicsguard.modules.physical.fluid import (
    IncompressibleOrificeModule,
    IncompressiblePressureDropModule,
    MassBalanceRateModule,
    MixerEnergyBalanceModule,
    PumpHydraulicPowerModule,
)
from physicsguard.modules.physical.gas import IdealGasStateModule
from physicsguard.modules.physical.humidity import (
    HumidityRatioFromPartialPressureModule,
    RelativeHumidityFromPartialPressureModule,
    WaterVaporMoleFractionModule,
)
from physicsguard.modules.physical.mechanical import (
    ForceVelocityPowerModule,
    LinearSpringForceModule,
    RotationalInertiaTorqueModule,
    TranslationalInertiaForceModule,
    ViscousDamperForceModule,
)
from physicsguard.modules.physical.rotating import (
    CompressibleIsentropicCompressorPowerModule,
    IsentropicGasTemperatureRiseModule,
    RotatingMachineAffinityModule,
)
from physicsguard.modules.physical.tank import TankLevelVolumeModule, TankVolumeRateModule
from physicsguard.modules.physical.thermal import (
    ConvectiveHeatTransferModule,
    CoolantHeatBalanceModule,
    ThermalCapacitanceRateModule,
    ThermalConductorModule,
)
from physicsguard.modules.physical.thermodynamics import (
    AmbientHeatLossModule,
    DensityMassVolumeModule,
    HeatExchangerEffectivenessModule,
    IdealGasDensityModule,
    MassMolarFlowConversionModule,
    MoleFractionFlowModule,
    RadiativeHeatTransferModule,
    SpecificEnthalpyFlowModule,
    VolumetricMassFlowConversionModule,
)

__all__ = [
    "AirOxygenMolarFlowModule",
    "AmbientHeatLossModule",
    "ChemicalPowerLHVModule",
    "CompressibleIsentropicCompressorPowerModule",
    "ConvectiveHeatTransferModule",
    "CellVoltageStackVoltageModule",
    "CoolantHeatBalanceModule",
    "CurrentDensityModule",
    "DensityMassVolumeModule",
    "ElectricalPowerModule",
    "ElectrochemicalFaradayRateModule",
    "ElectrochemicalStackPowerModule",
    "EfficiencyModule",
    "ForceVelocityPowerModule",
    "HeatExchangerEffectivenessModule",
    "HumidityRatioFromPartialPressureModule",
    "IdealGasStateModule",
    "IdealGasDensityModule",
    "IncompressibleOrificeModule",
    "IncompressiblePressureDropModule",
    "IsentropicGasTemperatureRiseModule",
    "LinearSpringForceModule",
    "MassMolarFlowConversionModule",
    "MassBalanceRateModule",
    "MixerEnergyBalanceModule",
    "MoleFractionFlowModule",
    "OhmicRelationModule",
    "PressureRatioModule",
    "PumpHydraulicPowerModule",
    "RadiativeHeatTransferModule",
    "RelativeHumidityFromPartialPressureModule",
    "RotatingMachineAffinityModule",
    "RotationalInertiaTorqueModule",
    "SpecificEnthalpyFlowModule",
    "StackChemicalEfficiencyModule",
    "StoichiometryModule",
    "TankLevelVolumeModule",
    "TankVolumeRateModule",
    "ThermalCapacitanceRateModule",
    "ThermalConductorModule",
    "TorqueSpeedPowerModule",
    "TranslationalInertiaForceModule",
    "ViscousDamperForceModule",
    "VolumetricMassFlowConversionModule",
    "WaterProductionFaradayModule",
    "WaterVaporMoleFractionModule",
]
