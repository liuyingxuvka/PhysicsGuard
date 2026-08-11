# Native Depth and Purpose

Load this reference only when the selected route creates, materially deepens, revises, or closes a task-local model. Ordinary bounded route execution does not eagerly load it.

## PhysicsGuard dynamic model-purpose and family baseline

Family capability baseline purpose: Prevent physical audit or modeling work from starting with an unclear symptom, physical boundary, subsystem, signal, parameter, assumption, or access universe.

Family route bounded claim: Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.

Family baseline proof boundary: This guard-model proof blocks only candidate admission when declared target-native obligation evidence is missing or native-failed. It does not independently detect the underlying physical, mapping, topology, workflow, or evidence defect and does not certify upstream truth.

Shared simulator prerequisite: install the current `physicsguard==0.15.8` package in the active Python environment. Before executing this skill, run `python -c "import physicsguard; print(physicsguard.__version__)"`; a missing package is a visible blocker and there is no bundled fallback.

Issue target-owned execution-depth receipts with `python -m physicsguard.skill_execution_depth PACKAGE.json --output RECEIPT.json`. The package module is the sole editable depth implementation shared by all ten skills.

The bundled `guard-model/` files declare these maintained family baseline regression classes:

- `Candidate is not proven against symptom or physical boundary is unclear` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: the visible symptom, units, operating boundary, or subsystem scope is missing. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against required model inventory is missing` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: required subsystems, signals, or parameters are absent from the discovered universe. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against assumption is hidden` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: a material model or operating assumption is missing or unresolved. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.
- `Candidate is not proven against access gap is suppressed` (native_obligation_admission_gate): block when the candidate lacks current passing target-native obligation evidence for this bounded route condition: unavailable model, signal, parameter, or evidence access is not reported. Claim boundary: This failure row licenses only rejection of a candidate that lacks current passing target-native obligation proof; it does not license a claim that the underlying domain defect was detected.

The target-native obligation inventory for this route is:

- `visible_symptom`
- `physical_boundary`
- `subsystem_inventory`
- `signal_inventory`
- `parameter_inventory`
- `assumption_inventory`
- `access_gaps`

Counts, object-name lists, catalog expansion, whole-receipt hashes, and ordinal ranges are not per-obligation evidence. Every satisfied obligation must retain its exact target-native semantic object, `evidence_ref`, and lowercase content hash; missing, renamed, overlapping, mechanically generated, or summary-only mappings block broad closure.

These fixed files prove only that the maintained skill can exercise its baseline checks. They are examples and mandatory family regression; they never state what a concrete model being built now is intended to prevent and can never close that real modeling task.

For every real model or route result, AI must choose the purpose and one or more concrete prevented physical/evidence failures for this modeling instance before it builds the candidate. It must freeze them under the target project at `.physicsguard/model-purpose/<model-id>/contract.json`, with the current physical/evidence boundary, native owner/route, one PhysicsGuard-native semantic oracle per failure, finding code, known limit, and bounded claim. It must then bind the actual candidate model file and exact failure universe in `candidate.json`; run every target-local known-good and known-bad case through those native oracles; write `proofs.json`; and pass current closure. Missing, stale, outside-root, baseline-only, mismatched, candidate-before-purpose, self-reported, or non-blocking evidence keeps the real model non-pass. There is one mandatory route and no selectable mode.

### Strict task-local model deepening

This skill's task-local owner is `physicsguard.model-understanding-preflight` on `route:physicsguard-model-understanding-preflight:review`; its declared closure check is `check:physicsguard-model-understanding-preflight:task-local-model-deepening`. The shared PhysicsGuard schema and evaluator provide the envelope, while this native owner keeps the route-specific physical/evidence judgment.

For every non-trivial task, use the existing `task-model plan -> observe -> revision` route with the strict current schema. The plan must declare a non-empty task purpose, an independently owned coverage-universe id and SHA-256, explicit assumptions and unknowns (empty is allowed only when written explicitly), iteration, an exact predecessor receipt after iteration zero, and a current `physicsguard_task_native_depth_receipt` bound to the plan model. Retired optional fields and compatibility shapes are invalid.

The native depth receipt must account for exactly six families: execution depth, mapping, residual, uncertainty, diagnosability, and predictive rollout. Open gaps, resolution classes, external input ids, and next actions come from that target-owned receipt; AI prose, `resolved=true`, caller-written gap lists, and self-reported understanding have no closure authority.

Freeze the prediction before observation and bind the observation to the exact plan fingerprint, selected probe, producer, source, independence group, and evidence SHA-256. If the observation contradicts every declared hypothesis, return `model_miss` and revise the hypothesis/model universe; never select a physical cause by elimination outside the declared space.

A candidate revision must preserve distinct base/candidate identities and consume base/candidate native-depth receipts plus exactly one typed regression receipt, one independent holdout receipt, and one predictive-rollout receipt. All three must bind the same task, plan, revision, coverage fingerprint, and candidate SHA-256; the holdout must be independent from candidate construction. PhysicsGuard derives resolved, persisted, and introduced gaps by comparing the two native receipts. Renaming or deleting a caller gap is not progress.

`model_closed_for_task` is legal only when the candidate identity is current, every typed check passes, and the candidate native receipt has zero open gaps. Otherwise preserve the exact non-success boundary: `continue_iteration`, `external_input_required`, `progress_stalled`, `iteration_limit`, `scope_excluded`, or `model_miss`. A passing regression with any native gap is continuation, not closure.

Use `python -m physicsguard.guard_model_contract check-current-contract|check-current-candidate|prove-current|check-current-closure` with an explicit `--target-root` and explicit paths for `--contract`, `--candidate`, `--oracles`, `--known-good`, `--known-bad`, and `--proofs` as required. The verifier rejects implicit current directories and bundled baseline artifacts as current-model authority.

`native_semantic_detection` is allowed only with an exact target-native fixture and asserted observation. `native_obligation_admission_gate` means only that a candidate without current target-native obligation proof is rejected; the generic `missing_target_obligation` result must never be presented as detection of the underlying domain defect.

`physicsguard.guard_model_contract` is the PhysicsGuard-native verifier. It proves only the declared family baseline and never replaces current task evidence or PhysicsGuard domain judgment.
