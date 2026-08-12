# Native Depth and Purpose

Load this reference only when the selected route creates, materially deepens, revises, or closes a task-local model. Ordinary bounded route execution does not eagerly load it.

## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Prevent a model/dataset consistency or predictive claim unless exact model, dataset, mapping, signal, parameter, time, scenario, physical-envelope, and claim-scope obligations pass the native evaluator.

Family route bounded claim: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.

Family baseline proof boundary: A pass licenses only the exact low-fidelity model, dataset identities, mappings, sampled universe, operating envelope, semantics, and claim scope in the receipt.

Shared simulator prerequisite: install the current `physicsguard==0.15.9` package in the active Python environment. Before executing this skill, run `python -c "import physicsguard; print(physicsguard.__version__)"`; a missing package is a visible blocker and there is no bundled fallback.

Issue target-owned execution-depth receipts with `python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`. The package module is the sole editable depth implementation shared by all ten skills.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Validation identity is wrong` (native_semantic_detection): block when the model, dataset, plan, mapping, split, or receipt identity is missing, stale, or mismatched. Claim boundary: Native semantic detection is limited to tests/test_validation_depth_receipts.py::test_changed_dataset_content_makes_receipt_stale and its asserted observation 'dataset_identity_stale'.
- `Coverage universe is shallow` (native_semantic_detection): block when signals, parameters, timepoints, events, scenarios, or families are missing or inadequately sampled. Claim boundary: Native semantic detection is limited to tests/test_validation_adequacy.py::test_10000_signals_with_only_two_selected_are_blocked and its asserted observation 'signal_coverage_ratio_not_met'.
- `Physical relation or envelope is violated` (native_semantic_detection): block when native residual, unit, sign, balance, constitutive, or physical-envelope checks fail. Claim boundary: Native semantic detection is limited to tests/test_model_dataset_validation.py::test_conservative_calibration_does_not_turn_direct_failure_into_pass and its asserted observation 'direct_validation_audit_failed'.
- `Prediction semantics are overclaimed` (native_semantic_detection): block when pointwise evidence or a stale/partial rollout is used to authorize prediction. Claim boundary: Native semantic detection is limited to tests/test_predictive_rollout_validation.py::test_pointwise_prediction_is_forbidden and its asserted observation 'pointwise_prediction_forbidden'.
- `Validation scope is overreached` (native_semantic_detection): block when the requested claim exceeds the native receipt's covered scope. Claim boundary: Native semantic detection is limited to tests/test_validation_adequacy.py::test_snapshot_receipt_cannot_satisfy_validation_ready_closure and its asserted observation 'snapshot_scope_incompatible'.

The target-native obligation inventory for this route is:

- `obligation:claim-scope-compatible`
- `obligation:coverage-universe-adequate`
- `obligation:exact-validation-inputs`
- `obligation:native-depth-receipt-current`
- `obligation:per-parameter-depth-adequate`
- `obligation:per-signal-depth-adequate`
- `obligation:predictive-semantics-honest`

Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal ranges are not per-obligation evidence. Every satisfied obligation must retain its exact target-native semantic object, `evidence_ref`, and lowercase content hash; missing, renamed, overlapping, mechanically generated, or summary-only mappings block broad closure.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

### Strict task-local model deepening

This skill's task-local owner is `physicsguard-model-dataset-validation` on `route:physicsguard-model-dataset-validation`; its declared closure check is `check:physicsguard-model-dataset-validation:task-local-model-deepening`. The shared PhysicsGuard schema and evaluator provide the envelope, while this native owner keeps the route-specific physical/evidence judgment.

For every non-trivial task, use the existing `task-model plan -> observe -> revision` route with the strict current schema. The plan must declare a non-empty task purpose, an independently owned coverage-universe id and SHA-256, explicit assumptions and unknowns (empty is allowed only when written explicitly), iteration, an exact predecessor receipt after iteration zero, and a current `physicsguard_task_native_depth_receipt` bound to the plan model. Retired optional fields and compatibility shapes are invalid.

The native depth receipt must account for exactly six families: execution depth, mapping, residual, uncertainty, diagnosability, and predictive rollout. Open gaps, resolution classes, external input ids, and next actions come from that target-owned receipt; AI prose, `resolved=true`, caller-written gap lists, and self-reported understanding have no closure authority.

Freeze the prediction before observation and bind the observation to the exact plan fingerprint, selected probe, producer, source, independence group, and evidence SHA-256. If the observation contradicts every declared hypothesis, return `model_miss` and revise the hypothesis/model universe; never select a physical cause by elimination outside the declared space.

A candidate revision must preserve distinct base/candidate identities and consume base/candidate native-depth receipts plus exactly one typed regression receipt, one independent holdout receipt, and one predictive-rollout receipt. All three must bind the same task, plan, revision, coverage fingerprint, and candidate SHA-256; the holdout must be independent from candidate construction. PhysicsGuard derives resolved, persisted, and introduced gaps by comparing the two native receipts. Renaming or deleting a caller gap is not progress.

`model_closed_for_task` is legal only when the candidate identity is current, every typed check passes, and the candidate native receipt has zero open gaps. Otherwise preserve the exact non-success boundary: `continue_iteration`, `external_input_required`, `progress_stalled`, `iteration_limit`, `scope_excluded`, or `model_miss`. A passing regression with any native gap is continuation, not closure.

Use `python -m physicsguard.guard_model_contract check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`physicsguard.guard_model_contract` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
