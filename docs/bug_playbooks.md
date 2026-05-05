# PhysicsGuard Bug Localization Playbooks

These playbooks are prompts for AI-guided debugging. They are not automatic rules. The AI should choose the smallest low-fidelity audit that can separate likely causes.

## Wrong Unit Or Scale

Typical symptom: a result is off by about `10`, `100`, `1000`, `3600`, `60`, `pi/30`, bar-to-Pa, rpm-to-rad/s, g/s-to-kg/s, or degrees-to-radians.

Start with a Level 0 balance. If one block dominates, refine to unit conversion checks around that block. Use `UnitConversionAuditModule`, power/flow/pressure balances, or map-axis checks. Ask for both raw external signal unit and PhysicsGuard SI target.

## Sign Reversal

Typical symptom: response diverges, feedback makes the plant move away from the target, or a relation has the right magnitude but opposite sign.

Start with control error, gain, actuator feedback, or torque/force direction checks. Refine around summing junctions, gains, feedback paths, and command-to-actual relations. Look for residuals that are roughly twice the expected magnitude with opposite sign.

## Implausible Parameter Magnitude

Typical symptom: a parameter is not just a little different, but impossible for the domain: a tiny object is `100 m`, a pressure is `1e9 Pa`, or a flow is many orders of magnitude too high.

Use range/post-check modules, aggregate balances, and simple physical relations. PhysicsGuard cannot know that `10 cm` should have been `5 cm` without a target or envelope, but it can flag values outside explicit physical or design ranges.

## Bad Signal Mapping

Typical symptom: a relation fails even though the expected physical relation is simple, or a signal has the right units but belongs to the wrong block/time/side of a component.

Run direct `hierarchy evaluate`, not solve. Refine by adding adjacent signals: upstream/downstream pressure, command/actual/feedback, input/output map axes, before/after unit conversion. Mark mapping confidence in metadata or Assumption Cards.

## Saturation, Clamp, Or State Logic Mismatch

Typical symptom: output is stuck, state is inconsistent with threshold, integrator keeps growing, or actuator command differs from feedback.

Use post-checks for state consistency and equation residuals for single-step actuator/controller relations. Refine around threshold, hysteresis, anti-windup, sample-and-hold, delay, and actuator position feedback.

## Map Axis Or Extrapolation Error

Typical symptom: efficiency, BSFC, compressor, pump, or calibration output is physically odd but algebraic balances downstream may still look plausible.

Start with map-axis bounds and monotonicity checks. Then check map interpolation with `LookupTable2DModule`, `EfficiencyMap2DModule`, or component map modules. Ask for map axis units, axis ordering, and extrapolation mode.

## Broken Power, Heat, Or Mass Balance

Typical symptom: energy disappears, generated heat does not match coolant/radiator rejection, source power does not equal load plus losses, or a tank inventory changes incorrectly.

Use aggregate balance modules at Level 0. If a balance fails, split into major blocks, then component checks. Ask for source/load/loss/storage signals first, not every internal signal.

## Electrochemical Stoichiometry Mismatch

Typical symptom: fuel-cell or electrolyzer power looks plausible but hydrogen, oxygen, water, or air flow scaling is wrong.

Start with stack balance and system efficiency. Refine into cathode supply, anode supply, water feed, gas production, coolant interface, and auxiliary power. Ask for current, cell count, stack voltage, gas flows, and stoichiometry.

## Vehicle Or Drivetrain Mismatch

Typical symptom: motor power, wheel force, vehicle acceleration, road load, or braking power do not line up.

Start with gearbox, wheel torque force, battery/motor power, and road-load checks. Refine around sign convention, gear ratio, wheel radius, regen split, and brake power.

