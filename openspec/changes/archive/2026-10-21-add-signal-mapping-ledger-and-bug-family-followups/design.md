## Overview

The change adds a small provenance layer for external signals used in observed-value debugging. It makes the AI's mapping assumptions visible before residuals are interpreted as physical faults. It also records same-family follow-ups so a unit, sign, mapping, or missing-term issue in one block prompts review of related signals or blocks.

## Design Decisions

### Mapping ledger is additive

Existing observed YAML files with `value`, `unit`, `source`, and `description` must continue to validate. New optional fields and a top-level mapping ledger should provide richer provenance where available.

### Review-required mapping changes report confidence

Hierarchy evaluation should include mapping warnings and review-required summaries. A high residual with low-confidence mapping should recommend mapping review before model blame.

### Bug-family follow-ups are deterministic suggestions

Add data classes for bug-family records and derive simple follow-ups from mapping warnings, residual diagnostics, and existing recommended refinements. This is not automatic repair.

### Keep FlowGuard traceability current

The existing model-code ledger should gain entries or stale conditions for the new signal mapping and bug-family behavior so future FlowGuard-backed edits can find the schema, reports, tests, and examples.

## Validation

- Existing PhysicsGuard YAML and hierarchy examples must remain valid.
- New tests should cover schema parsing, report keys, review-required mapping output, bug-family follow-up derivation, model-code ledger checks, and public exports.
- OpenSpec validation, FlowGuard lifecycle checks, model-code ledger check, pytest, hierarchy evaluate regressions, editable install/version checks, and installed skill sync are required before completion.
