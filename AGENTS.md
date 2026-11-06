## PhysicsGuard Core Repository Rules

Read `docs/development/flow-contracts.md` for the affected rule and its production test before changing code.
The former model DSL is retired. Real apply/reset chains, reports, schemas, CLI boundaries and
installation obligations live in `tests/native_contracts`; one shared cross-session decision
uses `tests/intent/policies.py`. Recheck affected intent and real tests with `python -m flowguard check`.

Policies:

- Real modules require an explicit request. Keep them low-fidelity; document equations, SI units, assumptions, limits, validity and diagnostic keys; provide tests and an example. Test all core classes.
- Prefer explicit first-principles algebraic residuals or single-step relations. No undocumented equations/correlations, hidden stateful physics, high-fidelity or commercial-equivalent models. DummyResidualModule and generic math audits are framework utilities, not physical models.
- Stack: Python 3.11+, type hints, pydantic, numpy, scipy, pyyaml, pytest; JSON diagnostics/reports.
- Use SI internally. The sole unit table is `src/physicsguard/core/units.py`. A change of quantity (L/min to kg/s) is computed from the table and a declared property, never taken from a recorded factor; a unit the table cannot read is refused, except a transducer output (V, mV, A, mA, ohm), whose explicit calibration is applied and reported as unchecked; never silent conversion during evaluation.
- Do not invent or silently apply assumptions, mappings, units or parameters. Record uncertainty explicitly; confidence and block scores are heuristics, not probability or proof. Never present a solved reference as an external observation.
- No commercial reverse engineering or external simulation-tool dependencies. Use documented, official or user-provided interfaces; keep adapters future work unless explicitly requested.
- Lookup/map modules document axes, units and extrapolation. Piecewise diagnostic checks default to post_check unless they intentionally define the solved reference; rate limits remain single-step without an explicit series request.
- One route per function: when a step fails, the error reaches the caller. A relation refuses a value only by raising `DomainRefusal`, and the tool's probes skip that refusal. Bounded root samples also treat division by zero and overflow as undefined points and claim no unique root; other errors reach the caller. An exception handler that can finish without raising is listed with its reason in `tests/test_error_handlers.py`, and no test or test file may end skipped (`skip_policy = "no_skip"` in pyproject.toml turns skips into failures; XPASS stays passed).
- Proceed coarse-to-fine from a visible symptom to the next discriminating signals. Recommend refinement; no silent template execution/auto-refinement, universal bug-finding or commercial equivalence claims.

Releases:

Version numbers are independent for each project; use the same MAJOR.MINOR.PATCH rules:

- At 1.0 and later, incompatible changes to a supported public CLI, skill id, SDK or saved input format raise MAJOR; backward-compatible features raise MINOR; corrections within the existing contract raise PATCH. Internal code volume or a dependency's version is not a version criterion. Never skip a number.
- Before 1.0, keep the unstable status explicit: incompatible public changes raise MINOR and describe migration. Publish 1.0 when declaring a stable contract, not merely because the implementation changed.
- A format consumed by a documented command remains a contract even when generated. Distinguish it from disposable caches. A new required field or changed supported meaning needs a compatibility decision; do not silently reinterpret old material.
- For a changed public surface, retain a small existing valid example and a real counterexample. Explain a corrected old bug separately from a new requirement. Give rejected old material a rebuild path from original inputs; never invent verified results, source digests or evidence fields to make it load.
- Record the release classification and migration in the existing CHANGELOG. Preserve historical commits, tags and releases; append corrections instead of renumbering them. Changes limited to repository policy or maintenance tooling do not by themselves require a product release. Raise a maintenance dependency only for a capability actually used or an evidenced correctness fix required by that workflow, not merely because a new tag exists.

Public saved inputs include documented physical models, observations, source references, units and declared properties. Audit and rollout reports are results for the inputs and scope they name; reading an old report never proves a new model execution.
- Maintenance needs FlowGuard at or above the tag in the `test` extra of `pyproject.toml` (install with `python -m pip install -e ".[test]"`; the PyPI package named `flowguard` is a different project). Raise that tag only when this repository uses a newer FlowGuard capability or needs a demonstrated correctness fix in its maintenance workflow; a FlowGuard release alone is no reason to change it or to release this repository.

CI runs the full pytest suite on Python 3.11 and 3.13, checks the current intent evidence,
and checks a scratch skill installation byte for byte. Migration of development tooling
alone does not require a PhysicsGuard release.

# FlowGuard for maintenance

- Save only the owner's own words once with `python -m flowguard req add <file|-> --id <id>`;
  never replace words in `.flowguard/requests/` with an AI's interpretation.
- Use `python -m flowguard show TEXT` when they help locate
  an existing decision. Keep one production owner for the same judgment. Use a small rule
  only for a necessary copy or an important correction worth preserving across sessions.
- Change code and its real tests together; run affected tests during development and report actual results.
  Before a product release, freeze the source and run the complete native suite once through
  `python -m flowguard check --all` from an environment outside the project; it includes pytest.
  Require complete CI on the exact main commit being published. `python -m flowguard check` rechecks affected rules and tests. Commit messages cite the saved
  request with `Request: <id>` when the change answers it.
