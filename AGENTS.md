## PhysicsGuard Core Repository Rules

- This project is PhysicsGuard Core.
- Do not implement real physical component models unless explicitly requested.
- Use SI units internally.
- Residuals must be normalized before solving.
- Optimizer convergence is not the same as audit pass. Use `optimization_success` for numerical optimizer convergence and `audit_pass` for residual-threshold plausibility.
- All solver variables must have finite bounds, finite initial guesses inside bounds, and positive finite scales.
- Variable scales must be passed to the solver before solving.
- Diagnostics must be JSON-serializable and suitable for AI consumption.
- All core classes require tests.
- Use Python 3.11+, type hints, pydantic, numpy, scipy, pyyaml, pytest.
- Do not reverse engineer commercial simulation tools.
- Do not add external simulation-tool dependencies.
- DummyResidualModule is for framework tests only and has no physical meaning.
- Generic mathematical audit modules are framework validation utilities only; do not treat them as real physical modules.
- Real physical, foundation, control/signal, thermodynamic, humidity, rotating-machine, mechanical, electrochemical, component and engineering-component modules, and hierarchical audit features, are added only when explicitly requested.
- Keep every physical module low-fidelity, documented, tested, and explicit about validity.
- Never add undocumented equations.
- Never imply equivalence with commercial solver internals.
- Do not let observed evaluation modify observed values.
- Do not confuse reference solve with observed audit.
- CSV and commercial-tool adapters remain future work.
- Observed values are assumed to be SI unless unit conversion is explicitly implemented later.
- Every physical, component and engineering module must document assumptions, limitations, SI units, residual equations, validity range, and diagnostic keys.
- Prefer simple first-principles algebraic residuals.
- Do not add empirical correlations unless the source and validity range are documented.
- Do not add complex, detailed or commercial-equivalent models without explicit request: no compressor maps or surge/choke models, detailed pump maps, fuel-cell polarization physics, detailed electrolyzer or heat-exchanger maps, combustion/emissions models, thermal derating models, or detailed GT/Simulink/Modelica/Amesim-equivalent models.
- Piecewise diagnostic checks should default to post_check unless they are intended to define the solved reference model.
- Lookup-table modules must document extrapolation behavior.
- Rate-limiter modules must be single-step checks unless a real time-series evaluator is explicitly requested.
- Do not add saturation vapor pressure correlations unless explicitly requested.
- Map-based modules must document axis units, output units, and extrapolation behavior.
- Prefer low-fidelity explicit residuals over complex empirical correlations.
- Prefer simple first-principles algebraic residuals and single-step audit relations over hidden stateful solvers.
- Do not add hidden unit conversion tables; conversion audit modules must use explicit user-provided factors and offsets.
- Every new engineering component module must include tests and at least one example.
- Hierarchical audit should support coarse-to-fine debugging with machine-readable reports.
- Hierarchical observed evaluation should substitute external values directly and must not move or solve observed values.
- Use `hierarchy evaluate` for AI-guided debugging of mapped external simulation snapshots; use `hierarchy compare` only when a solved low-fidelity reference is intentionally needed.
- Do not auto-refine or auto-execute next templates unless explicitly requested.
- Refinement rules should recommend next steps, not silently change the model.
- Block scores are diagnostic heuristics, not mathematical proof.
- Confidence scores are heuristic and must not be presented as statistical certainty.
- Do not use hierarchy features to imply commercial solver equivalence.
- Keep hierarchical reports JSON-serializable, machine-readable, and AI-consumable.
- PhysicsGuard is an AI debugging tool, not a universal automatic bug finder; AI agents may propose signal mappings and audit templates, but uncertain mappings must be recorded explicitly.
- AI agents may add narrowly scoped low-fidelity audit modules only when the relation is explicit, documented, tested, SI-based, and not a high-fidelity or commercial-tool model.
- Bug localization should proceed coarse-to-fine: visible symptom, coarse balance or relation, suspicious block, next required signals or parameters, then deeper template.
- All assumptions must be explicit Assumption Cards.
- Do not silently invent assumptions.
- Do not silently apply assumptions.
- Do not use assumptions as free optimization variables.
- Proposed assumptions must not be applied.
- Rejected assumptions must not be applied.
- High-impact assumptions must produce warnings.
- Every diagnostic report should expose assumptions.
- Do not build complex scenario or probabilistic assumption logic unless explicitly requested.
- Prefer transparency over cleverness.

<!-- BEGIN FLOWGUARD PROJECT RULES -->

## FlowGuard map and model maintenance

1. Start each session with `python -m flowguard read` before opening source.
2. Before adding behavior, use `python -m flowguard read --find WORDS`; extend its existing owner.
3. Open only the affected component's files (`python -m flowguard read --component ID`).
4. After editing, run `python -m flowguard change`, fix errors, and run the affected tests and models it selects.
5. Re-read each REVIEW component, update its description if behavior changed, then `python -m flowguard map confirm ID`.
6. At final release, freeze the source and run the full suite and `python -m flowguard release` once on that revision (same-SHA CI may provide this); report failures and unrun checks honestly.

Maintenance needs FlowGuard at or above the tag in the `test` extra of `pyproject.toml` (install with `python -m pip install -e ".[test]"`).

<!-- END FLOWGUARD PROJECT RULES -->
