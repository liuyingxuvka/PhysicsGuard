## Context

PhysicsGuard is already a Python package and Codex skill for low-fidelity physical residual audits. It has hierarchy evaluation, signal mapping ledger output, assumption cards, portable YAML headers, a FlowGuard model-code ledger, and a skill-level closure helper. FlowGuard is stronger at project-level adoption and evidence governance: it records installed versions, project manifests, model ownership, route-specific templates, stale evidence, maintenance obligations, and closure boundaries.

This design upgrades PhysicsGuard in that direction while preserving the core runtime contract. The solver, observed-value evaluation, residual normalization, and hierarchy semantics remain unchanged. The new work adds workflow records, validators, templates, skill routes, and evidence checks around the existing runtime.

## Goals / Non-Goals

**Goals:**
- Make PhysicsGuard discoverable inside a target project through a project adoption record and audit command.
- Require AI agents to capture physical understanding before interpreting residuals.
- Make external signal mapping reviewable and stale-aware before residuals are treated as model faults.
- Add a module/equation ledger so future AI agents can find what a module checks, which equations it uses, and which tests/examples support it.
- Strengthen closure so partial, stale, mapping-uncertain, or missing-input audits cannot support broad localization claims.
- Split prompts into smaller route-oriented skill folders and synchronize installed copies.

**Non-Goals:**
- No new physical component models or empirical correlations.
- No GT-SUITE, Simulink, Modelica, FMI, Amesim, MATLAB, CSV, or commercial-tool adapter.
- No automatic repair of external models.
- No claim that PhysicsGuard recovers high-fidelity or commercial solver internals.
- No runtime behavior change for existing `run`, `solve`, `evaluate`, `compare`, or `hierarchy` commands.

## Decisions

### Decision: Store project adoption under `.physicsguard/project.yaml`

PhysicsGuard needs its own target-project manifest rather than overloading `.flowguard/project.toml`. The manifest records PhysicsGuard repository URL, package version, schema version, rules path, workflow policy, adoption log path, module ledger path, and skill route names.

Alternative considered: only document project adoption in README. Rejected because AI agents need a machine-readable entry point.

### Decision: Add validators for workflow files rather than changing the core solver schema

Model-understanding and external-model-intake files are workflow artifacts. They guide AI behavior and evidence freshness, but they are not solver inputs. Keeping them separate avoids destabilizing existing `SystemSpec`, `ObservedValuesSpec`, and `HierarchicalAuditSpec`.

Alternative considered: embed all preflight/intake metadata into existing YAML schemas. Rejected because it would blur runtime audit data with planning evidence and make older examples noisier.

### Decision: Start the module ledger as a curated machine-checkable YAML index

The first ledger will cover core module families and representative module types with their equation summary, units, assumptions, diagnostic keys, tests, and examples. The check script verifies file/test/example references and catches empty required fields. It does not attempt symbolic physics proof.

Alternative considered: generate the entire ledger from Python class introspection. Rejected because documentation quality, assumptions, and validity boundaries need human-readable review, not only class names.

### Decision: Closure remains evidence routing, not proof of physical truth

The closure helper will report `passed`, `partial`, or `blocked` based on audit pass/fail, missing inputs, mapping review, bug-family follow-ups, recommended refinements, stale evidence, skipped checks, and declared closure state. Passing closure supports only a scoped low-fidelity claim.

Alternative considered: treat top residual ranking as localization proof. Rejected because a high residual can also mean bad mapping, missing data, or invalid assumptions.

### Decision: Split skill routes but keep the main skill as the default entry

The main `physicsguard-ai-debugging` skill remains the user-facing entry. New subskills mirror the route split so direct agent routing does not bypass project adoption, preflight, mapping review, closure, or candidate blueprint boundaries.

Alternative considered: keep one very large skill file. Rejected because a long prompt becomes harder to apply consistently and harder to sync safely.

## Risks / Trade-offs

- Extra workflow files could feel heavy for tiny examples -> Validators and docs should frame them as required for non-trivial external-model debugging, not every toy YAML.
- AI agents could mistake workflow ledger checks for physics proof -> All docs and closure output must state the safe claim boundary.
- Skill-route split could drift from the main skill -> Add installed-copy sync checks and focused tests that compare repository and installed skill files.
- Module ledger could go stale as modules change -> Add a check script and release validation command; include stale rules in the ledger.
- Background/full regression evidence can be invalidated by later writes -> Use FlowGuard development-process evidence freshness before final confidence.

## Migration Plan

1. Upgrade FlowGuard project adoption records to the installed version and validate the project audit.
2. Add OpenSpec requirements and implementation tasks for the workflow upgrade.
3. Implement project adoption helpers and CLI commands.
4. Add preflight/intake templates, validators, docs, and tests.
5. Add module/equation ledger, validator, docs, and tests.
6. Strengthen closure helper semantics and skill guidance.
7. Add route-oriented subskill folders and sync them to local installed skills.
8. Bump PhysicsGuard version surfaces and reinstall editable local package.
9. Run OpenSpec validation, FlowGuard checks, ledger checks, focused tests, full pytest, CLI smoke checks, installed skill diff checks, and git diff hygiene.

## Open Questions

- No blocking open questions. Future work may add deterministic diagram generation from hierarchy JSON after these workflow records are stable.
