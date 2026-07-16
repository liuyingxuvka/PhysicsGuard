## Context

PhysicsGuard already checks test-file contracts, signal mapping, evidence registry, direct residual validation, bounded calibration, holdout, and closure. The current model does not distinguish scalar snapshot coverage from time-series or scenario coverage strongly enough for downstream execution-depth claims.

## Goals / Non-Goals

**Goals:** bind validation to exact datasets, mappings, time windows, scenarios, splits, residual series, physical envelopes, and report identity; prevent snapshot extrapolation.

**Non-Goals:** recover commercial solver internals, add high-fidelity models, or let SkillGuard interpret physics.

## Decisions

- Extend existing project evidence registry and model-dataset validation owners; do not add a second validator.
- Create typed receipts for dataset identity, mapping review, time coverage, scenario coverage, train/holdout split, residual series, envelopes, and final report.
- Add a bounded time-series evaluator that applies existing low-fidelity residual relations pointwise and summarizes missing, invalid, and envelope-breaking intervals.
- Require disjoint train/holdout identity when calibration is enabled and expose any overlap.
- Make claim scope explicit: snapshot, window, scenario set, or bounded dataset only.

## Risks / Trade-offs

- [Large series increase runtime] -> Stream or batch evaluation and route full suites through TestMesh/background execution.
- [Bad mappings dominate results] -> Mapping review is a hard predecessor and uncertainty stays visible.
- [Holdout labels hide overlap] -> Compare content/file/case identities, not labels alone.
- [Residual fit is overclaimed] -> Keep physical envelopes, assumptions, and low-fidelity boundary in the receipt.

## Migration Plan

Add optional receipt models and validation APIs, preserve scalar commands, add time-series fixtures and negative overlap/mapping cases, then update skill contracts and installed copies.
