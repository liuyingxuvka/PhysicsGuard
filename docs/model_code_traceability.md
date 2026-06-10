# Model-Code Traceability

PhysicsGuard uses FlowGuard models to describe important lifecycle behavior, but a model is much more useful when it also points to the implementation it governs. The model-code ledger is the current map between modeled responsibilities, source symbols, tests, examples, boundaries, and validation commands.

The ledger lives at `.flowguard/model_code_ledger.yaml`.

## What The Ledger Is

The ledger is a navigation and evidence index. It answers:

- Which FlowGuard model block owns this behavior?
- Which source symbols implement it?
- Which tests and examples exercise it?
- Which assumptions, unit rules, and safety boundaries matter?
- Which checks must be rerun before claiming the evidence is fresh?
- What kind of code change makes the entry stale?

The ledger is not proof by itself. Passing the ledger check only proves that the map still points to real files and symbols. Runtime behavior still needs FlowGuard checks, pytest, and relevant CLI/example regressions.

## When To Use It

Use the ledger before model-backed work, especially changes to:

- schema validation or loaders;
- module registration and variable registry construction;
- residual assembly, normalization, and residual roles;
- solve, evaluate, compare, or hierarchy modes;
- diagnostic JSON output;
- assumptions and assumption reporting;
- project adoption, model-understanding preflight, external-model intake, module/equation ledger, installed skill sync, or closure workflow;
- test-file contract manifests, coverage policies, evidence-backed mappings, model bindings, contract diffing, or project index checks;
- release confidence claims involving FlowGuard evidence.

For a future AI agent, the default workflow is:

1. Find the ledger entry for the behavior being changed.
2. Read the model block and the listed source symbols.
3. Read the listed tests and examples before editing.
4. Update the ledger if ownership, boundaries, examples, or validation commands change.
5. Run the ledger check plus the listed validation commands.

## How To Check It

Run:

```powershell
python scripts/check_model_code_ledger.py
```

For release work, run it with the usual model and test checks:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python .flowguard/run_physicsguard_core_checks.py
python .flowguard/run_physicsguard_ai_workflow_checks.py
python .flowguard/run_physicsguard_test_file_contract_checks.py
python .flowguard/run_physicsguard_test_file_contract_development_checks.py
python scripts/check_model_code_ledger.py
python scripts/check_module_equation_ledger.py --json
python -m pytest
```

## How To Update It

Each ledger entry should stay small enough to review. Prefer stable source symbols over exact line numbers. A good entry includes:

- `id`: stable ownership id;
- `model_file`: FlowGuard model file;
- `model_blocks`: modeled FunctionBlock classes;
- `responsibility`: short description of what the entry owns;
- `code_symbols`: source file plus class/function name, such as `src/physicsguard/core/residual.py::ResidualBuilder`;
- `tests`: focused tests that prove the surface;
- `examples`: YAML examples or observed snapshots that demonstrate the path;
- `validation_commands`: commands that refresh evidence;
- `boundaries`: assumptions, units, residual semantics, or safety rules;
- `stale_when`: conditions that make earlier evidence outdated.

Do not add line numbers as the primary contract. They drift too easily. If a symbol moves, update the symbol path and rerun the ledger check.

## Stale Evidence Rules

Treat ledger evidence as stale when:

- a listed source symbol is renamed, moved, or deleted;
- a model block changes ownership or semantics;
- a CLI mode changes solve/no-solve behavior;
- residual role, normalization, or diagnostic JSON semantics change;
- assumption application or reporting changes;
- new public behavior is added without a ledger entry;
- project/preflight/intake/closure workflow behavior changes without updating the workflow ledger rows;
- installed skill prompts or route folders change without a fresh skill-sync comparison;
- peer-agent writes occur after validation.

When in doubt, rerun the ledger check, FlowGuard model checks, and the focused tests named in the ledger entry.

## Relationship To Adoption Logs

The adoption log records historical work and validation events. The ledger records the current ownership map. A release should keep both:

- ledger: where the model maps today;
- adoption log: what was validated for this change;
- tests and CLI regressions: current execution evidence.
