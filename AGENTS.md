## PhysicsGuard Core Repository Rules

Read these model contracts before changes:

- Audit setup: model `core`, rules `no_solve_without_valid_registry`, `no_solve_without_normalized_residuals`, `hierarchy_describe_does_not_solve`.
- Observed work: model `observed_derivation`, rules `observed_evaluation_does_not_solve`, `unobserved_variables_stay_listed`, `no_residual_from_unobserved_guess`, `derived_relations_are_not_checks`, `comparison_requires_reference_and_observed`, `hierarchy_run_requires_solve`, `diagnostics_after_solver_or_failure`.
- Assumption cards: model `assumptions`, rules `assumptions_are_reported_in_diagnostics`, `assumption_overrides_are_warned`, `variable_assumptions_are_fixed_residuals`.
- Solver/audit distinction: model `solver_audit`, rules `audit_pass_and_failure_are_disjoint`, `post_checks_never_block_valid_solver_selection`.
- Refinement and readback: model `tree_verdicts`, rules `parent_fails_with_child`, `coarse_failure_with_passing_children_is_inconsistent`, `planned_template_is_reported_not_executed`, `tree_view_shows_every_block_verdict`, `verdict_lines_omit_structure`, `hint_shown_in_tree`, `resolution_shown`.
- CLI: model `cli_exit`, rules `exit_code_follows_audit_pass`, `default_view_is_the_tree`. Installation, generated CSV and native descriptions: models `skill_install`, `heated_tank_generator`, `module_descriptions`.

Policies:

- Real modules require an explicit request. Keep them low-fidelity; document equations, SI units, assumptions, limits, validity and diagnostic keys; provide tests and an example. Test all core classes.
- Prefer explicit first-principles algebraic residuals or single-step relations. No undocumented equations/correlations, hidden stateful physics, high-fidelity or commercial-equivalent models. DummyResidualModule and generic math audits are framework utilities, not physical models.
- Stack: Python 3.11+, type hints, pydantic, numpy, scipy, pyyaml, pytest; JSON diagnostics/reports.
- Use SI internally. The sole unit table is `src/physicsguard/core/units.py`. A change of quantity (L/min to kg/s) is computed from the table and a declared property, never taken from a recorded factor; units outside the table use explicit factors/offsets, which are reported as unchecked; never silent conversion during evaluation.
- Do not invent or silently apply assumptions, mappings, units or parameters. Record uncertainty explicitly; confidence and block scores are heuristics, not probability or proof. Never present a solved reference as an external observation.
- No commercial reverse engineering or external simulation-tool dependencies. Use documented, official or user-provided interfaces; keep adapters future work unless explicitly requested.
- Lookup/map modules document axes, units and extrapolation. Piecewise diagnostic checks default to post_check unless they intentionally define the solved reference; rate limits remain single-step without an explicit series request.
- One route per function: when a step fails, the error reaches the caller. An exception handler that does not re-raise is listed with its reason in `tests/test_error_handlers.py`, and a test may never end skipped (`tests/no_skips.py` turns a skip into a failure).
- Proceed coarse-to-fine from a visible symptom to the next discriminating signals. Recommend refinement; no silent template execution/auto-refinement, universal bug-finding or commercial equivalence claims.

Releases:

- Version numbers: a release that adds features raises the second number (0.16.0 -> 0.17.0); a release with only small fixes raises the third (0.17.0 -> 0.17.1); never skip a number.
- Maintenance needs FlowGuard at or above the tag in the `test` extra of `pyproject.toml` (install with `python -m pip install -e ".[test]"`; the PyPI package named `flowguard` is a different project). Raise that tag only when this repository starts using a newer FlowGuard feature; a FlowGuard release alone is no reason to change it or to release this repository.

# FlowGuard rules for the project agent

1. At the start of a session and after any loss of context, run `python -m flowguard status` before anything else.
2. When the owner asks for something, store the owner's own words once, as received: `python -m flowguard req add <file|-> --id <id>`. It stores only words the owner wrote, byte for byte: never a plan, a list or text an AI wrote. When a new owner message replaces an earlier one, add `--supersedes <old id>`; never edit `.flowguard/requests/`.
3. Find code with `python -m flowguard where NAME`; change code and its tests together; run the project's own test command (for example `python -m pytest -q`) and report exactly what you ran and the result.
4. Commit code and tests together in one commit with a message in your own words; add a line `Request: R<n>` when the change answers a stored owner request. The legacy map, `.flowguard/models/` and the target commands need no upkeep.
