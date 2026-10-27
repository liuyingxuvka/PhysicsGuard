## PhysicsGuard Core Repository Rules

Read these model contracts before changes:

- Audit setup: model `core`, rules `no_solve_without_valid_registry`, `no_solve_without_normalized_residuals`, `hierarchy_describe_does_not_solve`.
- Observed work: model `observed_derivation`, rules `observed_evaluation_does_not_solve`, `unobserved_variables_stay_listed`, `no_residual_from_unobserved_guess`, `derived_relations_are_not_checks`, `comparison_requires_reference_and_observed`, `hierarchy_run_requires_solve`, `diagnostics_after_solver_or_failure`.
- Assumption cards: model `assumptions`, rules `assumptions_are_reported_in_diagnostics`, `assumption_overrides_are_warned`, `variable_assumptions_are_fixed_residuals`.
- Solver/audit distinction: model `solver_audit`, rules `audit_pass_and_failure_are_disjoint`, `post_checks_never_block_valid_solver_selection`.
- Refinement and readback: model `tree_verdicts`, rules `parent_fails_with_child`, `coarse_failure_with_passing_children_is_inconsistent`, `planned_template_is_reported_not_executed`, `tree_view_shows_every_block_verdict`, `verdict_lines_omit_structure`.
- CLI: model `cli_exit`, rules `exit_code_follows_audit_pass`, `default_view_is_the_tree`. Installation, generated CSV and native descriptions: models `skill_install`, `heated_tank_generator`, `module_descriptions`.

Policies:

- Real modules require an explicit request. Keep them low-fidelity; document equations, SI units, assumptions, limits, validity and diagnostic keys; provide tests and an example. Test all core classes.
- Prefer explicit first-principles algebraic residuals or single-step relations. No undocumented equations/correlations, hidden stateful physics, high-fidelity or commercial-equivalent models. DummyResidualModule and generic math audits are framework utilities, not physical models.
- Stack: Python 3.11+, type hints, pydantic, numpy, scipy, pyyaml, pytest; JSON diagnostics/reports.
- Use SI internally. The sole unit table is `src/physicsguard/core/units.py`; else use explicit factors/offsets at `testfile snapshot|series`, never silent conversion during evaluation.
- Do not invent or silently apply assumptions, mappings, units or parameters. Record uncertainty explicitly; confidence and block scores are heuristics, not probability or proof. Never present a solved reference as an external observation.
- No commercial reverse engineering or external simulation-tool dependencies. Use documented, official or user-provided interfaces; keep adapters future work unless explicitly requested.
- Lookup/map modules document axes, units and extrapolation. Piecewise diagnostic checks default to post_check unless they intentionally define the solved reference; rate limits remain single-step without an explicit series request.
- Proceed coarse-to-fine from a visible symptom to the next discriminating signals. Recommend refinement; no silent template execution/auto-refinement, universal bug-finding or commercial equivalence claims.

<!-- BEGIN FLOWGUARD PROJECT RULES -->

## FlowGuard map and model maintenance

1. Start each session with `python -m flowguard read` before opening source.
2. Before changing behaviour or structure: locate the owner model with `python -m flowguard read --find WORDS` (or a path:function) and extend it (a separate aspect gets its own model), run `python -m flowguard target start "<goal>"` and `python -m flowguard target add <model>`, edit the copy in .flowguard/target/, run `python -m flowguard target check` until it shows EXPECTED GAP and no ERROR, change the code, then run `python -m flowguard target promote` and the map confirm it prints.
3. Open only the affected component's files (`python -m flowguard read --component ID`).
4. After editing, run `python -m flowguard change` and fix errors; for `port changed ... -> verify X`, run `python -m flowguard target add X` and make X receive the value; open each place a `consumes`, `produces`, `mentions` or `nothing produces` line names; restore what a `promises: -...` line lists or give the reason in the commit message; then run the affected tests and models it selects. Models, tests and code grow together: split a model or a test file that grows too big (map check warns at the soft limit and refuses at the hard one), keep them in correspondence where it makes functional sense, and give a reason where a model has no test or no code yet.
5. Re-read each REVIEW component, update its description if behavior changed, then `python -m flowguard map confirm ID`.
6. At final release, freeze the source and run the full suite and `python -m flowguard release` once on that revision (same-SHA CI may provide this); report failures and unrun checks honestly.

Maintenance needs FlowGuard at or above the tag in the `test` extra of `pyproject.toml` (install with `python -m pip install -e ".[test]"`; the PyPI package named `flowguard` is a different project).
Raise that tag only when this repository starts using a newer FlowGuard feature; a FlowGuard release alone is no reason to change it or to release this repository.

<!-- END FLOWGUARD PROJECT RULES -->
