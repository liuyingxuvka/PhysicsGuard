## Context

PhysicsGuard already owns task-local hypothesis revision and next-observation ranking. The missing layer is an explicit distinction between a measurement interval that robustly supports/falsifies a hypothesis and one that leaves multiple candidates indistinguishable.

## Goals / Non-Goals

**Goals**

- Preserve interval, unit, provenance, and execution state for every relevant observation.
- Compute fault signatures and equivalence classes over declared discriminators.
- Return robust typed terminals and select a useful next signal.

**Non-Goals**

- No new hypothesis engine or ExperimentGuard.
- No default-zero fill for missing data.
- No invented probability distribution or physical law.

## Decisions

1. `IntervalObservation` holds lower/upper bounds, inclusivity, unit, source, and `observed|missing|not_run|invalid`.
2. A discriminator evaluates a hypothesis to a predicted interval or explicit unavailable result.
3. Pairwise overlap across all current discriminators forms an indistinguishability relation; connected identical-signature candidates form a reported class.
4. Terminal status is `robust_pass`, `robust_fail`, `indeterminate`, or `not_run`.
5. Next-signal ranking uses declared partition gain first, then risk and acquisition cost. Ties remain visible.
6. Existing task-local revision consumes the diagnostic report; it is not replaced.

## Risks / Trade-offs

- Interval arithmetic can be conservative. Conservative `indeterminate` is preferred over false precision.
- Units must be compatible before comparison; incompatible units block rather than coerce.

## Migration Plan

Implement two semantic stages in one current release: first preserve bounded
uncertainty and robust residual status, then derive task-local fault
signatures, pairwise diagnosability, and next-signal evidence. Integrate both
with the existing hypothesis route, update prompts/reports, and refresh
FlowGuard/SkillGuard evidence and version to v0.13.0.
