# PhysicsGuard AI Debugging

## Entry boundary
Use for engineering-simulation fault localization or a requested low-fidelity candidate model.
Hand off complete boundary/inventory work to `model-understanding-preflight`, mapping-only work to
`signal-mapping-review`, concrete file contracts to `test-file-contract-review`, and model/data
consistency claims to `model-dataset-validation`. Multi-project/database questions need their owner.

## Workflow
1. If the audit exists, run `python -m physicsguard.cli hierarchy describe AUDIT.yaml` first and say on which blocks the
   symptom lands. State the visible symptom, external source of truth, physical boundary and stop condition.
   Hand off if another route owns the complete request; start with the coarsest useful check.
2. When understanding is uncertain, use `references/templates/model_understanding_preflight.yaml`:
   `python -m physicsguard.cli preflight review PREFLIGHT.yaml --audit AUDIT.yaml`.
   Omit --audit until the model exists, then bind this review after step 3.
   Name blocks, conserved quantities, interfaces, SI units, assumptions and uncertain mappings.
3. Build or reuse the audit. Read `references/model-format.md`; start from `references/templates/audit_model.yaml`.
   Choose real relations with `python -m physicsguard.cli modules describe TYPE` (synthetic examples are introspection).
   Read `python -m physicsguard.cli hierarchy describe AUDIT.yaml`: default text, `--observed SNAPSHOT.yaml` for signal counts, `--json` for the full structure or `--mermaid` for a diagram; it never solves or evaluates.
4. Map signals. For CSV/TSV use one contract: `python -m physicsguard.cli testfile manifest DATA.csv --profile CONTRACT.yaml --out MANIFEST.yaml`,
   then `python -m physicsguard.cli testfile contract-check CONTRACT.yaml` and
   `python -m physicsguard.cli testfile snapshot CONTRACT.yaml --row 70 --out OBSERVED.yaml`.
   Use `python -m physicsguard.cli testfile series CONTRACT.yaml --out SERIES.yaml` for series.
   A hand-written snapshot retains source signal, unit, confidence, factor/offset and review state; optional `source_model` records tool/model context. Review mappings through the evaluation ledger and the tree's `mapping:` line.
   `stale_when` names reconfirmation conditions; when one occurs mark the mapping `stale`.
5. Run `python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml`.
   Read the failing block lines and the tail lines of the tree (`own FAIL`, `not checked: N inputs missing`, `no checks`,
   `refinement:`, `next:`, `mapping:`); add `--json` only when you need details. Connections propagate identity without overwriting measurements.
   Finite one-unknown equation/connection/boundary/assumption relations may derive an intermediate;
   ambiguous, flat, undefined or unsupported cases stay unknown. Producing relations are not checks.
   Supported per-residual value/control dependencies include zero products and flat branches;
   do not replace them with numerical probing or a whole-module read union. Custom missing inputs
   need supported dependencies; custom checks with every registered value supplied remain usable.
   With no independent check the command stops. CLI lists remaining gaps; strict library mode rejects them.
6. Compare competing causes declared as `fault_variants` in the audit tree:
   `python -m physicsguard.cli hierarchy variants AUDIT.yaml NOMINAL.yaml --pairs --observed OBSERVED.yaml`.
   Read `variants failing here:` on each block, then `masked:`, `indistinguishable … next signal`, `matches:` and `model miss:`.
   `masked:` lists nonempty proper-subset failures; undetected or outside-expected pairs fail the check (`--json`: `pairwise`).
   `matches:` is bounded signature agreement; `model miss: yes` means failing observed data matches no fault variant.
   Represent bounded sensor accuracy with a `kind: benign` measurement-offset variant that must remain neutral.
   Variants copy another device and rederive without changing the nominal model or measurements; unavailable rows keep reasons/null signatures.
   Exit 0 means checks pass without a model miss, 1 a failed/not-evaluable check or miss, and 2 invalid input.
7. Refine one suspicious block with `refines` and its recommended template. Request only the next
   discriminating signal: pressure upstream/downstream, command/actual/feedback, map axes/output,
   bus source/load/loss/storage power, or stack current/cell count/gas flow. Check same-family
   sign/gain, units, mapping and balance followups before declaring localization complete; repeat.
8. Report the required outputs below from the latest run. `optimization_success` is numerical status,
   `audit_pass` is threshold plausibility, and confidence is a heuristic, not probability.
   Use `python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml` only for an intentional
   solved low-fidelity reference. For temporal/model-data claims use
   `python -m physicsguard.cli validation run PLAN.yaml`; report intervals and all adequacy warnings.

## Required outputs
- `localized_findings`: suspicious blocks, supporting checked residuals and exact printed status.
- `next_required_evidence`: open refinements, family followups, mapping reviews and missing variables/parameters.
- `bounded_claim`: checked operating envelope; separate derived values from measurements and independent checks.

## Visual Audit Communication
Show one compact Mermaid diagram or table only when it clarifies localization or the next signal.
Label heat/mass/power/signal flow, maps_to/refines_to/requires_signal edges; never imply recovered topology.
Diagrams explain the audit; they are not validation evidence.
Audit command exit status follows `audit_pass`; comparison follows `observed_audit_pass`, not reference optimizer convergence. A successful structural inspection returns 0.

## Claim Boundary
Use the latest actual output. A matching signature does not prove cause or exhaust physical reality.
Do not count an own-passing ancestor as fault evidence; retain a direct own failure even with children.
Distinguish detection from isolation; an unmeasured next signal is ranked by scale-normalized differences.
Connection endpoints mean the same physical quantity: retain the tight default scale or state a small
positive finite tolerance. Use an explicit relation when endpoints can physically differ.
Inspect assumptions with `python -m physicsguard.cli assumptions inspect MODEL.yaml`; this does not solve.

## Workflow B: Build A Candidate Model From A PhysicsGuard Audit
Only when requested, define each block's required fidelity, validate its low-fidelity checks and interfaces,
then generate a candidate through documented APIs (for Simulink: new_system/add_block/set_param/add_line).
Run it, map its outputs back to PhysicsGuard and refine one block at a time. It is a candidate engineering
model, not a recovered commercial model. Read `references/model-generation.md` before generation.

## Required Header For New PhysicsGuard YAML
Use a specific one-layer comment header on audits, hierarchies, snapshots and candidate audits:
```yaml
# PhysicsGuard audit/model audit
# Purpose: Low-fidelity residual audit for <short model purpose>.
# Repository: https://github.com/liuyingxuvka/PhysicsGuard
# Use with: python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml
# Boundary: Low-fidelity SI-unit residual audit or audit only; not a high-fidelity solver, commercial-tool adapter, or reverse-engineered model.
```
Do not add provenance metadata solely for this header.

## Hard Boundaries
- Do not add or imply commercial-tool adapters unless explicitly requested; CSV/TSV ingestion uses test-file contracts only.
- Do not reverse engineer commercial model internals.
- Do not claim the generated candidate model is equivalent to a commercial or high-fidelity model.
- Do not add high-fidelity solvers, automatic repair, or natural-language report generation.
- Do not use assumptions as solver-tunable variables.
- Do not silently invent signal mappings, units, or parameters.
- Do not mark fields covered without evidence; unknown meanings or variables stay review-required, planned as model extensions or failing.
- Do not answer multi-project, historical-test or database questions from one project; this route does not own the database ledger.
- Do not treat signal_mapping_ledger as a conversion engine; it records evidence and review state, never changes observations.
- Do not claim a plausible parameter is wrong without residual evidence or an explicit design envelope.
- Do not generalize from hand-picked subsets; report every adequacy warning and narrow claims to the covered scope.
- Do not count one value as adequate coverage for a time-varying parameter, even when other signals are deep.
- Do not describe pointwise evaluation as simulation or prediction; prediction needs state propagation and a disjoint future holdout.
- Do not learn by modifying PhysicsGuard itself during a diagnostic episode. Hypotheses, predictions, observations, mismatches and revisions are task-local; core thresholds, Guard code, reusable defaults and installed skills stay unchanged.
- For GT-SUITE, Modelica, Amesim, FMI, or other external tools, use only official, user-provided, or documented interfaces; otherwise stop at the audit and name the missing interface.

## When To Create A New PhysicsGuard Relation
Only with authorized code changes when the library lacks the needed low-fidelity check: simple balances,
single-step dynamics, unit/map consistency, sign/gain/saturation logic or coarse physical relations.
Keep SI units, explicit assumptions/limits, finite bounds/scales, ModuleRegistry registration and tests/examples.
Read `references/bug-playbooks.md` for the next hypothesis; do not reproduce hidden high-fidelity internals.
