# Task-Local Competing Hypotheses

PhysicsGuard does not ask an AI whether it "understands" a model. It asks for
concrete predictions from more than one explanation, picks the observation that
best separates them, and compares that observation with the frozen predictions.

## Commands

1. `physicsguard task-model plan PLAN.yaml` checks a hypothesis plan: purpose,
   the hierarchy YAML the hypotheses are about (`model.path`, which must exist),
   assumptions, unknowns, at least two hypotheses for a non-trivial task, and at
   least one signal, residual, or timing expectation per hypothesis. It ranks the
   declared observation candidates by residual relevance and by how well they
   separate the hypotheses.
2. `physicsguard task-model observe PLAN.yaml OBSERVATION.yaml` compares a later
   observation (`observation_sequence` larger than the plan's
   `prediction_sequence`) with every expectation. Each hypothesis is reported as
   `supported`, `weakened`, or `undetermined`; missing targets stay open. When
   every hypothesis is contradicted the result is `model_miss`: revise the
   hypothesis list instead of inventing a cause.
3. `task-model interval-residual` and `task-model diagnose` keep interval
   uncertainty explicit and recommend the next signal from fault signatures.
   `interval-residual` exits 1 on `robust_fail`; `diagnose` exits 1 when the
   declared signatures cannot be separated (`indistinguishable`).
4. `physicsguard task-model variants AUDIT.yaml NOMINAL.yaml` derives fault
   signatures from the audit's declared device variants. Use `--pairs` to also
   evaluate pairs of faults, `--observed OBSERVED.yaml` to compare the actual
   observed signature, and `--write-diagnose DIAGNOSE.yaml` to write input for
   `task-model diagnose`. Add `--json` for the full result. Exit codes are 0 when
   the requested fault-detection, expected-block and benign checks pass, 1 when
   a check fails or a declared device case cannot be evaluated, and 2 for
   invalid input. Detection does
   not mean that all faults are distinguishable.

Templates for the first two inputs ship with the ai-debugging skill
(`references/templates/hypothesis_plan.yaml` and
`references/templates/diagnostic_observation.yaml`).

The results are task-local. They never identify the true physical cause and do
not change PhysicsGuard itself.

## Model-Derived Device Variants

An audit may declare top-level `fault_variants`. Each variant has a unique `id`,
`kind` (`fault` or `benign`), optional `description`, `parameters`, `changes`,
`rederive` and `expect_blocks`. Parameter overrides use `component.parameter`
keys. Each change names a variable and exactly one operation: `scale`, `offset`,
`set` or `flip_sign: true`. Multiple change operations in one entry are rejected.
Numeric edits must be finite. Changes and `rederive` must name registered
measurements present in the nominal snapshot. `expect_blocks` records which
blocks a fault is required to expose.

Parameter overrides can replace a valid module default even when the parameter
was omitted from the audit YAML. The component's native constructor retains its
parameter-value validation; this route does not introduce a separate exhaustive
parameter-name catalog.

A variant represents another device. PhysicsGuard copies the nominal snapshot,
applies the declared changes, removes the measured values named in `rederive`,
and uses the parameter-modified device model to derive their replacements under
the observed-evaluation rules. It then audits that device data with the original
nominal model. The supplied model and observations remain unchanged. Missing or
unsupported derivations stay explicit; this is not a reference optimization or
time-forward rollout.

The signature contains blocks with their own directly checked failure evidence
and the sign of each block's largest checked residual under the existing role
and threshold rules. It excludes an ancestor that fails only because a child
failed. A block such as `thermal` can have children and still contribute its own
failure; parent and child are both retained when both have direct evidence.
Producing or unchecked relations cannot create a fault signature.

For each variant, `detected` says whether a fault exposed a failing block,
`neutral` says whether a benign variant preserved the nominal conclusion, and
`expect_blocks_met` reports the declared block requirement. Faults with identical
signatures form `indistinguishable` groups. Each group's `next_signal` selects a
currently unmeasured variable whose device values differ most after normalizing
by its variable scale; it is null if no such separating signal is available.
An observed comparison reports matching fault ids in `matching_variants` by
signature equality; a match is a bounded explanation, not proof of the cause.

The result contains `nominal_audit_pass` and `nominal_signature`, single-variant
rows in `variants`, optional composed rows in `pairs`, and the overall `ok`.
Each evaluated row includes `id`, `variant_ids`, `kind`, `status: evaluated`, a
`signature` mapping block ids to `+`, `-` or `0`, `failed_blocks`, `audit_pass`, the three check flags above,
`expected_blocks` and its own `ok`. Pair rows also contribute to the requested
check verdict. Each indistinguishable group includes `variant_ids`, `signature`,
`next_signal` and `normalized_separation`. Without `--observed`,
`matching_variants` is null.

A valid device edit whose requested measurement cannot be generated has
`status: not_evaluable` and an explicit `reason`. Its `signature` and
`audit_pass` are null; `detected`, `neutral` and `ok` are false. Other cases remain
visible and the command exits 1. Unavailable signatures are excluded from
indistinguishable groups and observed matches. Schema errors or unknown ids
remain input errors with exit 2.

Full JSON also exposes `generated_values` (the generated snapshot),
`device_values` (known device values including intermediate derivations),
`rederived_variables`, `diagnose_request` and `claim_boundary`. The compact result
omits the two value maps and diagnosis payload. Generated data is marked as
counterfactual; it is not an additional real measurement.

`--write-diagnose` writes a `DiagnosabilityRequestSpec` YAML with a diagnosis id,
fault signatures, predicted intervals and available signal ids. Each interval
uses the variant's value plus or minus variable scale times the audit threshold.
Run `task-model diagnose` on that file to inspect discrimination; its native
0/1 verdict remains separate from variant detection. Fewer than two declared
fault hypotheses or no shared signal remains an input error. If valid fault
evaluation is unavailable, the command preserves all rows, exits 1 and reports
`diagnose_export.status: not_written` with the actual reasons in both full and
compact output. It does not create a partial diagnosis file; the request stays null.

Pair evaluation applies two declared fault variants to the same copied device.
Identical signatures, inherited parent failure or a missed hierarchy code are
not evidence of physical cancellation. Any feature-kit exclusion used for
maintenance must be justified by actual composed-device results, not by an
expected example output. The maintenance model uses the common FlowGuard kit
API available from 0.70.7; PhysicsGuard product runtime does not import or depend
on FlowGuard.

## Heated-Tank Reference

For `heated_tank.yaml` with the nominal `measured_k30.yaml` snapshot, the declared
single-device variants give these checked signatures. The nominal wall-loss
coefficient remains 20 W/K and the audit thresholds are unchanged.

| Variant | Device or measurement edit | Rederived measurement | Signature / result |
| --- | --- | --- | --- |
| `heater_half` | heater current × 0.5 | `heat.T_current_K` | `heater: -`, detected |
| `extra_wall_loss` | `loss.UA_W_K: 400` | `heat.T_current_K` | `thermal: -`, detected |
| `inlet_temp_offset` | inlet temperature + 2.4 K | none | `thermal: -`, detected |
| `outflow_unit_x1000` | measured volumetric outflow × 1000 | none | `hydraulics: +`, detected |
| `outflow_rounding` | measured volumetric outflow + 0.000001 m³/s | none | empty signature, neutral |

`extra_wall_loss` and `inlet_temp_offset` remain indistinguishable by their direct
checked signatures. Their next unmeasured signal is `heat.Q_out_W`, with a
scale-normalized device-value separation of about 11.40734 in this snapshot.
These results apply to the declared low-fidelity model, perturbations and audit
tolerance; they do not make every smaller fault detectable.

Comparing `measured_k70.yaml` reports `heater_half` in `matching_variants`.
The exported diagnosis request is accepted by `task-model diagnose`; for this
reference it reports `partially_isolable` with exit 0, preserving the distinction
between a runnable diagnosis and complete fault isolation.

With `--pairs`, all six fault pairs in this example are evaluated. Five meet
their expected block checks. `heater_half+inlet_temp_offset` exposes `heater: -`
but not the expected `thermal` failure, so `expect_blocks_met` is false and the
overall command exits 1. The combination uses the biased inlet temperature
while rederiving the current tank temperature, which closes the nominal thermal
relation. Keep that observed masking visible in the CLI results. A maintenance
feature model therefore treats `inlet_temp_offset` as singleton-only
(`exclusive=True`); it makes no pair-coverage claim for that feature. That limited
model scope does not skip pairs requested from the CLI or turn this result into
a pass. The small outflow-rounding edit remains benign without overwriting a
fault device's parameters.
