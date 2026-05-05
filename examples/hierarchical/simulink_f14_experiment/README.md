# Local Simulink F14 Hierarchical Audit Experiment

This directory is a local-only experiment for validating PhysicsGuard against a copied
MATLAB/Simulink example model.

The experiment uses MATLAB's built-in `f14` aircraft longitudinal flight-control example,
copies it into this directory, changes the copied model only, runs both clean and faulted
copies, and generates PhysicsGuard hierarchical audit YAML from logged signal values.

It is not a Simulink adapter. It does not parse arbitrary Simulink models and should not be
treated as redistributable MathWorks example content.

Workflow:

1. Run `run_f14_local_experiment.m` from MATLAB or with `matlab -batch`.
2. Run `build_physicsguard_audits.py`.
3. Run the generated YAML files with `physicsguard hierarchy run ... --pretty` or
   `python -m physicsguard.cli hierarchy run ... --pretty`.

The generated files in this directory were created before direct hierarchical observed-value
evaluation existed, so they encode logged values as explicit boundaries. For new AI-guided
debugging experiments, prefer the newer pattern:

`physicsguard hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty`

The observed-value pattern keeps external simulation results as evidence and prevents the
solver from moving them. See `examples/hierarchical/observed_debugging/`.

The injected fault reverses the sign of the pitch-rate feedback gain block in the copied
model:

`f14/Controller/Gain2`

The progressive audit is intentionally staged:

1. Level 0 sees only final aircraft response signals.
2. Level 1 sees major subsystem boundary signals.
3. Level 2 sees a controller internal signal relation.

Only Level 2 checks the internal relation:

`q_gain_output = Kq_nominal * q_gain_input`

The clean level-0 run should pass. The faulted run should first mark the flight-control
loop suspicious, then rank the controller block as suspicious, and finally point to the
pitch-rate feedback path.
