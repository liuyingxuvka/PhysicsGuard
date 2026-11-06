# Development contracts

FlowGuard 2 is a development-only dependency in the `test` extra. Ordinary PhysicsGuard
use does not need it. Run `python -m pytest -q` for the full native suite and the intent
items, use `python -m flowguard check` to recheck affected rules and tests. CI uses
`python -m flowguard check --all` to run the complete suite once against the
same triggering source on Python 3.11 and 3.13 and verifies installation only in a scratch directory.

Each physical claim stays with its native owner and real input. The 12 former migration
families now call production code directly in `tests/native_contracts`; the original
72 production-test bindings retain their independent assertions in the existing test files.
The copied State/expected predicates, Cartesian fact enumerators, model DSL and native
adapter are retired. Their 47 deliberately bad abstract facts were never production
source mutations. The one abstract `no_data` policy made no native data claim and is retired.

| Contract family | Native test support |
| --- | --- |
| Audit setup, solver calls and child reports | `core.py`, `_audit_cases.py` |
| Observed values, derivation and bounded unit probes | `observed_derivation.py` |
| Assumption cards and diagnostics | `assumptions.py`, `test_assumption_lifecycle.py` |
| Audit/solver separation | `solver_audit.py` |
| Refinement, verdicts, hints and resolution | `tree_verdicts.py` |
| CLI codes and views | `cli_exit.py` |
| Fault variants, masking and unavailable evidence | `fault_variants.py` |
| Dataset depth, holdout and adequacy | `model_dataset_validation.py` |
| Test-file roles, mappings and freshness | `file_contract.py` |
| Scratch installation, CSV reproduction and descriptions | The three matching native files |
| Five original ownership/existence routes | `test_routes.py`, using the shared Map |

Only the shared map-mode decision uses an intent rule in `tests/intent/policies.py`:
Maps accept error or hold; only LookupTable1D explicitly accepts linear.
One production predicate, `components._common.extrapolation_allowed`, supplies the
constructor checks and the bilinear helper. The numerical interpolation paths remain
distinct. The component 1D helper intentionally validates an invalid mode only when the
value is outside its table; constructor validation already guards its real callers.

The scalar fallback already has one owner; it needs direct native cases rather than a
second model of the whole dynamic file-reading path. With `plan.depth is None`,
`evaluate_validation_depth` calls `_legacy_snapshot_depth` only when audit and observed
inputs are both present; either missing input returns blocked. The fallback preserves
scalar commands but only makes a partial snapshot claim, never a declared-depth pass.
`tests/native_contracts/test_snapshot_scope.py` directly checks all four literal input
pairs, the fixed-None precondition, status, covered scope, warning, snapshot flag and
missing-input not-run payload. The experimental SCALAR_SNAPSHOT intent is retired;
its complete input/output obligations remain in these ordinary native tests.

The unchanged baseline full-suite trace found five actual fallback calls in four tests:
`tests/flow_migration/test_native_contracts.py::test_native_contract[model_dataset_validation]`
(now the corresponding `tests/native_contracts` topic), and the three existing tests in
`tests/test_model_dataset_validation.py`: conservative calibration cannot turn direct
failure into pass; coarse-grid calibration keeps the claim boundary; a calibration
parameter must exist in the model. Their original assertions remain. These observations
justify keeping the live production route; they do not claim all declared-depth paths
were checked by the scalar cases. The separate existing dataset/depth tests own that domain.

The sole automatic unit table remains `core/units.py`. Its `unit_error_hypotheses` computes
14 finite scale/offset trials from named unit pairs in that table. These are diagnostic
counterfactuals: they do not infer a source unit or change observations. Observation byte/
value preservation, partial snapshots, hint visibility and programming-error propagation
remain independently exercised by the existing native tests.

`tests/test_error_handlers.py` keeps every allowed handler's count and reason. Shared
`Map.handlers` supplies source/control-flow facts; actual injected errors still exercise
native behavior. The shared `no_skip` policy in `pyproject.toml` preserves PhysicsGuard's
rule that runtime or collection skips (including xfail) fail the run. XPASS retains its
ordinary passed behavior. Static skip declarations and import aliases remain prohibited.

These finite contracts do not certify physical truth beyond their inputs. Static route
checks establish target existence, not call order. No artificial execution order or second
physical simulator is introduced. The modules/core dependency cycle is not claimed repaired.

Source inlet roles are native physical metadata, not a second formula: FlowMergeTemperatureModule
declares its two flow/temperature groups. The source owner binds each to a unique explicit
`Inlet <id> brings/carries/supplies ... at ...` clause or a verified pipe-table row. Different
entities in one port, or counting one entity as two ports, is red; unsupported/ambiguous roles
stay grey while numerical evaluation remains available. Whole-pair port swaps remain valid.
Block `source_coverage` lists actual backed reads, other variable reads and parameters not
source-verified; unquoted output values need no external quotation. Free-form question links
are labelled `question_reference`, not evaluated answer predicates. The finite 40 C control
uses the existing native ThresholdStateCheckModule instead of a question-language engine.
