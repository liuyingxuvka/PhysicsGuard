# PhysicsGuard AI Debugging

Localize simulation faults on the requested blocks. Other owners are in SKILL.md.

## Workflow

1. Run `python -m physicsguard.cli hierarchy describe AUDIT.yaml`. Name the visible
   symptom, source of truth, boundary, blocks and stop condition; start coarse.
2. If understanding is uncertain, use `references/templates/model_understanding_preflight.yaml`
   and `python -m physicsguard.cli preflight review PREFLIGHT.yaml --audit AUDIT.yaml`.
   Omit `--audit` before the model exists. Name interfaces, conserved quantities,
   SI units, assumptions and mapping uncertainties.
3. Build or reuse the audit using `references/model-format.md` and
   `references/templates/audit_model.yaml`. Inspect real relations with
   `python -m physicsguard.cli modules describe TYPE`; synthetic inputs are introspection.
   Read back before evaluation: `describe --observed SNAPSHOT.yaml` counts signals;
   `--json` gives structure, `--mermaid` a diagram. No solve.
4. Bind external data through one contract:
   `python -m physicsguard.cli testfile manifest DATA.csv --profile CONTRACT.yaml --out MANIFEST.yaml`,
   `python -m physicsguard.cli testfile contract-check CONTRACT.yaml`, then
   `python -m physicsguard.cli testfile snapshot CONTRACT.yaml --row 70 --out OBSERVED.yaml`.
   Use `python -m physicsguard.cli testfile series CONTRACT.yaml --out SERIES.yaml` for series.
   A hand-written snapshot retains source signal, unit, confidence, factor/offset
   and review state. Mark a mapping stale when its declared reconfirmation condition occurs.
5. Run `python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml`.
   Read `own FAIL`, `not checked`, `no checks`, `refinement:`, `next:`, `hint:` and
   `mapping:` on the tree. `--json` gives details; `--full` restores the declared structure.
6. Compare declared causes with
   `python -m physicsguard.cli hierarchy variants AUDIT.yaml NOMINAL.yaml --pairs --observed OBSERVED.yaml`.
   Read block signatures, `masked:`, `matches:`, `model miss:` and the next signal.
   A match is bounded agreement, not proof of cause. A `kind: benign` accuracy
   variant must remain neutral; unavailable comparisons keep their reasons.
7. Refine one suspicious block with `refines` and its recommended template. Ask only
   for the next discriminating signals or parameters. Review sign/gain, units,
   mapping and balance followups before declaring localization complete.
8. Report current findings. `optimization_success` is numerical convergence;
   `audit_pass` is threshold plausibility; confidence is a heuristic, not probability.
   Use `python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml` only
   for an intentional solved reference. For temporal/model-data claims run
   `python -m physicsguard.cli validation run PLAN.yaml`: read interval verdicts,
   holdout, adequacy and the safe claim on its tree; retain every warning.

## Required outputs

- `localized_findings`: blocks, checked residuals and printed status.
- `next_required_evidence`: refinements, family/mapping followups and missing inputs.
- `bounded_claim`: the checked envelope; distinguish measurements, derived values and independent checks.

## Claim boundary

Use current output. Detection is not isolation or exhaustive truth. An own-passing
ancestor is not fault evidence; retain direct own failures.
Inspect cards with `python -m physicsguard.cli assumptions inspect MODEL.yaml`.
Connection endpoints mean the same quantity; use an explicit relation when they can differ.

Use diagrams/tables only to clarify localization or next signals, never as evidence.

For a requested candidate model, read `references/model-generation.md`.
New YAML keeps this file-specific comment header; add no schema metadata for provenance:
```yaml
# PhysicsGuard hierarchical audit model
# Purpose: Low-fidelity residual audit for <short model purpose>.
# Repository: https://github.com/liuyingxuvka/PhysicsGuard
# Use with: python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml
# Boundary: Low-fidelity SI-unit residual audit only; not a high-fidelity solver, commercial-tool adapter, or reverse-engineered model.
```

## Hard Boundaries
- Do not count one value as adequate coverage for a time-varying parameter, even when other signals are deep.
- Do not describe pointwise evaluation as simulation or prediction; prediction needs state propagation and a disjoint future holdout.
- Do not learn by modifying PhysicsGuard itself during a diagnostic episode. Hypotheses, predictions, observations, mismatches and revisions are task-local; core thresholds, Guard code, reusable defaults and installed skills stay unchanged.
- For GT-SUITE, Modelica, Amesim, FMI, or other external tools, use only official, user-provided, or documented interfaces; otherwise stop at the audit and name the missing interface.
- Do not silently invent signal mappings, units, or parameters.
