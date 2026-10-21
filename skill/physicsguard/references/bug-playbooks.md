# Bug Localization Playbooks

## Unit Or Scale Error

Look for factors near `10`, `100`, `1000`, `3600`, `60`, `pi/30`, bar-to-Pa, rpm-to-rad/s, g/s-to-kg/s, degrees-to-radians, or Celsius-to-Kelvin. Use unit conversion audits, map-axis bounds, and coarse balances.

## Sign Reversal

Look for right magnitude with opposite direction, unstable feedback, or residuals near twice the expected magnitude. Check summing junctions, feedback gains, torque/force directions, and actuator command-to-feedback relations.

## Bad Signal Mapping

If a simple relation fails, the signal may come from the wrong side, wrong time, wrong unit, or wrong component. Ask for adjacent input/output signals and record mapping confidence.

## Impossible Parameter Magnitude

PhysicsGuard cannot know that `10 cm` should be `5 cm` without an envelope, but it can flag values such as `100 m`, `1e9 Pa`, or flows many orders of magnitude outside explicit bounds.

## Saturation Or State Logic

Use post-checks for hysteresis, thresholds, clamps, anti-windup, map bounds, and relief/check-valve states. Use equation residuals for actual single-step actuator or controller relations.

## Map Misuse

Check axis units, axis order, interpolation inputs, extrapolation behavior, and monotonicity. Then check semantic map outputs such as efficiency, BSFC, compressor pressure ratio, or pump delta pressure.

## Broken Balance

For power, heat, mass, species, and electrical-bus issues, start with aggregate balances. If the block fails, split into source/load/loss/storage or inlet/outlet/production/consumption terms.

## Electrochemical Balance

For fuel-cell or electrolyzer systems, check current, cell count, stack voltage, gas flow, water flow, air or hydrogen stoichiometry, heat, and auxiliary power before detailed physics.

