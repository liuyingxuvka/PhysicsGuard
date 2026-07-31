## Context

The package is current but observed model authority is absent. Historical maintenance tasks must remain historically honest while one new baseline proves current owner and toolchain identities.

## Goals / Non-Goals

**Goals**

- Establish auditable observed authority and one green current maintenance baseline.
- Preserve unrun historical checks as superseded or blocked, never silently checked.

**Non-Goals**

- No interval residuals, fault signatures, or diagnosability behavior.

## Decisions

1. Current baseline checks run under FlowGuard 0.65.1 and the exact v0.11.3 source.
2. Remaining historical tasks receive explicit superseded-by or completed-with-current-receipt disposition.
3. Snapshot bootstrap consumes fresh focused evidence, then model-system audit must pass.
4. Publish v0.11.4 as the behavior-neutral baseline.

## Risks / Trade-offs

Current audits may expose more stale owners; these remain blockers until classified.

## Migration Plan

Reconcile maintenance history, run current checks, bootstrap/audit authority, and release v0.11.4 before feature changes.
