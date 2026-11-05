# Development contracts

FlowGuard 1.0 is the development-only dependency in the test extra. `python -m pytest -q`
runs every production test and the independent migration contracts. `python -m flowguard release`
checks the model but reports `UNKNOWN: native conformance unavailable: assumption_lifecycle` and exits 0;
that command does not establish native conformance. Real assumption-card apply/reset calls through the shared
native adapter are checked by `tests/flow_migration/test_native_lifecycle.py`. Neither the model nor those
finite tests are a physical correctness certificate outside their declared cases.

The former twelve legacy models' 48 independent predicates and 72 production-test bindings
are retained in `tests/flow_migration/coverage.json`. It names a destination for every rule,
original bad version and generated system route. This is structural configuration, not an
execution receipt. The existing production tests retain their independent assertions.

| Contract family | Current owner |
| --- | --- |
| Audit setup and stage obligations | `core.py` |
| Observation, derivation and unit probes | `observed_derivation.py` |
| Assumption reporting and fixed residuals | `assumptions.py` |
| Audit/solver separation | `solver_audit.py` |
| Refinement, verdicts, hints and resolution | `tree_verdicts.py` |
| CLI codes and views | `cli_exit.py` |
| Fault variants, masking, separation and model misses | `fault_variants.py` |
| Dataset depth, holdout and adequacy | `model_dataset_validation.py` |
| Test-file roles, mappings and freshness | `test_file_contract.py` |
| Installation, CSV reproduction and module descriptions | The three matching unit-contract files |

These owners are under `tests/flow_migration`. Their predicates are independent of the
production implementation. Original bad variants corrupt abstract facts deliberately;
47 cases include the nine fault-variant versions previously created dynamically. They
are labelled **ABSTRACT bad facts**, not production source mutations. Real code is checked
separately on the original finite fixtures, and ordinary production tests are unchanged.
The model-only `no_data` case licenses no physical data claim and is labelled as such.

The assumption-card model covers actual apply, repeat, fresh or repeated reset, and reapply behavior.
Its small fixture delegates to the real AssumptionManager; it is neither a validator nor
a copied model executor. The native lifecycle test uses FlowGuard's shared capture/adapter owner.
Reset constructs a new manager even when the previous one is fresh; the model adds no artificial
refusal. Its postcondition checks the fresh card, unapplied flag and empty override warning.
Invalid schema and parameter refusals remain in the independent production unit contracts.
The generated map system's five routes retain static target-existence assertions and native
functional destinations; no artificial call order was invented. The old map wrapper is removed.

The old large-model diagnostic ends when that model is replaced by direct contracts. The
map-only dependency-cycle diagnostic also retires with the map; the actual modules/core import
cycle is not claimed repaired. Its production ownership and tests remain in place. Migration
changes development tooling only and does not require a PhysicsGuard release.
