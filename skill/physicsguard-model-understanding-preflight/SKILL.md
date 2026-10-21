---
name: physicsguard-model-understanding-preflight
description: "Use directly before a non-trivial external-model audit to capture the visible symptom, physical boundary, subsystem, signal, parameter, unit, assumption, access, model-semantics, and stop-condition universe; preflight is planning evidence, not residual validation."
---

# PhysicsGuard Model Understanding Preflight

## Entry boundary

Accept this route only when:

- A non-trivial external model must be understood before residual interpretation or blueprint work.
- The physical boundary, inventory, assumptions, access gaps, semantics, or stop conditions need a current review.

Reject or hand off when:

- The request is only to resolve signal identity, unit, conversion, or confidence. Handoff: `physicsguard-signal-mapping-review`.
- A concrete test-data file needs field-level coverage first. Handoff: `physicsguard-test-file-contract-review`.

## Minimum workflow

1. Freeze the symptom, external authority, physical boundary, and required inventory.
2. Load the native route protocol and review subsystems, signals, parameters, assumptions, uncertainty, and prediction access.
3. Proceed only inside the passed planning boundary; send unresolved mappings or files to their direct owners.

If `python -m physicsguard.cli --help` fails, install the engine once with `python -m pip install -e <PhysicsGuard checkout>`; there is no version gate.

## Conditional detail loading

- Load `references/native-route-protocol.md` after route selection when domain execution needs the detailed workflow.
- Do not load another PhysicsGuard skill's references merely because the skills are related; hand off to that skill instead.

## Hard gates

- Keep non-pass states and unknowns visible.
- AI narration, inventories and template previews are not evidence; only PhysicsGuard command output is.
- Keep pointwise consistency distinct from stateful prediction and keep every claim inside the exact checked boundary.

## Required outputs

- `preflight_status`
- `understanding_record`
- `access_gaps`
- `next_route`

Claim boundary: Preflight licenses only that the declared low-fidelity audit boundary is sufficiently understood to proceed; unresolved access or inventory gaps remain visible blockers.
