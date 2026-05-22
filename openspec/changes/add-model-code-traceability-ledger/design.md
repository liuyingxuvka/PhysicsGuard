## Context

PhysicsGuard's core lifecycle is already represented by `.flowguard/physicsguard_core_model.py`, and release work is recorded in `.flowguard/adoption_log.jsonl` plus `docs/flowguard_adoption_log.md`. Those artifacts preserve model intent and validation history, but they do not give a stable map from each modeled responsibility to the source symbols, tests, examples, and stale-evidence conditions that future AI agents should inspect before modifying code.

This change adds a small repository-governance layer. It does not change the runtime solver, CLI, YAML schema, or audit semantics.

## Goals / Non-Goals

**Goals:**
- Create a human-readable and machine-checkable ledger from FlowGuard model blocks to code, tests, examples, assumptions, and validation commands.
- Cover the core PhysicsGuard lifecycle first: validation, registry construction, residual assembly, solve/evaluate/compare, hierarchy modes, assumptions, and diagnostics.
- Add documentation that explains how AI agents and maintainers should use the ledger before edits and releases.
- Add a focused script and tests that catch stale file/symbol/test/example references.
- Include the ledger check in release validation evidence.

**Non-Goals:**
- No new physical modules, empirical equations, commercial-tool adapters, or high-fidelity models.
- No broad refactor of existing source modules.
- No replacement for FlowGuard checks, pytest, CLI examples, or adoption logs.
- No deep static analysis beyond verifying that declared files and symbols are present.

## Decisions

### Decision: Store the ledger as YAML under `.flowguard/`

The ledger belongs next to FlowGuard model artifacts because it maps model responsibilities to implementation evidence. YAML keeps it readable to humans and easy to validate with the project's existing PyYAML dependency.

Alternative considered: store the ledger as Markdown only. Rejected because Markdown is good for explanation but weak for automated stale-reference checks.

### Decision: Use file plus symbol ownership instead of line-number ownership

Ledger entries identify source files and symbols such as `src/physicsguard/core/residual.py::ResidualBuilder`. Line numbers can be helpful in review output, but they are too fragile to use as the primary contract.

Alternative considered: record exact line numbers. Rejected because small edits would make the ledger noisy and stale even when ownership has not changed.

### Decision: Keep the first validator simple

The check script verifies that files exist, symbols are present in Python files, and each ledger entry names evidence such as tests or examples. It does not try to prove semantic equivalence between the model and code.

Alternative considered: import all symbols and perform deeper runtime introspection. Rejected for the first version because imports can have side effects and would make a governance check more brittle than useful.

### Decision: Treat the ledger as navigation plus evidence index, not proof

The ledger tells future AI agents where to look and which validations must be refreshed. Passing the ledger check does not mean the model, code, or physics is correct; FlowGuard model checks, pytest, CLI examples, and release validation remain the proof surface.

Alternative considered: merge the ledger into the adoption log. Rejected because adoption logs are historical events, while the ledger is a current ownership map.

## Risks / Trade-offs

- Stale ledger entries could mislead future agents -> Mitigated by a validation script, tests, and release checklist language.
- Overly detailed ledger entries could become maintenance burden -> Mitigated by covering core lifecycle boundaries first and using symbol-level ownership.
- AI agents could mistake ledger presence for validated behavior -> Mitigated by explicit documentation and `evidence_level: navigation`, plus required validation commands.
- Peer agents may write concurrently and stale validation evidence -> Mitigated by final git status checks and release-time reruns after all owned edits are complete.

## Migration Plan

1. Add `.flowguard/model_code_ledger.yaml` with core lifecycle entries.
2. Add `scripts/check_model_code_ledger.py`.
3. Add tests for the script and current ledger.
4. Add `docs/model_code_traceability.md`.
5. Record the change in FlowGuard adoption logs.
6. Run FlowGuard checks, ledger checks, pytest, editable install verification, and release/version checks.
7. Bump patch version and publish a new GitHub release.
