---
name: physicsguard-audit-closure
description: Use before claiming PhysicsGuard localized a fault or completed an audit; checks audit pass/fail, missing inputs, mapping review, stale evidence, skipped checks, refinements, and same-family follow-ups.
---

# PhysicsGuard Audit Closure

Use this route before final localization or completion claims.

For project-level completion, validation, reuse, or localization claims, prefer
the project closure gate first:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

Do not treat a project evidence map as proof. The map is navigation; the
project closure report decides whether current route evidence supports a
`passed`, `partial`, `downgraded`, or `blocked` claim.

Run:

```powershell
python %USERPROFILE%\.codex\skills\physicsguard-ai-debugging\scripts\physicsguard_closure_check.py --ledger CLOSURE.json --audit AUDIT.yaml --observed OBSERVED.yaml --json
```

Blocking or downgrading evidence includes failed audit, missing variables or parameters, review-required mappings, stale evidence, skipped checks, open refinements, and same-family follow-ups.
For workflows that include concrete test data files, also treat missing,
partial, stale, or failing test-file contracts as blocking or downgrading
evidence. A residual report cannot make a broad claim from a file whose fields
are not fully cataloged, classified, and evidence-mapped.

For project-level workflows, also read the project evidence map or gap report.
Missing project profile basics, unregistered important files, unresolved
blocking evidence gaps, missing binding summaries, unreviewed physical
parameter bindings, or test-field binding expectations without bindings or
exemptions downgrade or block broad claims.
If a project closure report exists, carry its `closure_status`, `safe_claim`,
`unsafe_claim_boundary`, skipped checks, and next actions into the final answer.
If no report exists for a broad project claim, run it or explicitly downgrade
the claim.

For workflows that validate a model against contracted test data, also read the
model-dataset validation report. Missing, partial, failed, stale, or blocked
validation reports downgrade or block broad model-data consistency claims. Treat
`optimization_success` as numerical optimizer evidence only; it is not
`audit_pass`, holdout pass, or final validation pass. Parameter-at-bound
warnings, low validation confidence, failed physical envelopes, redundant-sensor
mismatches, and review-required confidence updates must remain visible in the
final claim boundary.

For database-level or cross-project claims, do not answer from this closure
route alone. Missing project registries, stale external summaries, propagated
project evidence blocking gaps, or unknown comparison scope block broad
historical, reuse, or direct-comparison conclusions.

Closure pass supports only a scoped low-fidelity claim inside the checked audit
or project closure boundary.
