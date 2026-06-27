---
name: physicsguard-candidate-model-blueprint
description: Use when turning a validated PhysicsGuard hierarchy into a candidate model blueprint for MATLAB/Simulink or another official target-model interface without claiming recovered commercial-model equivalence.
---

# PhysicsGuard Candidate Model Blueprint

Use this route when the user asks to build a candidate model from PhysicsGuard evidence.

## Workflow

1. Start from a passed model-understanding preflight.
2. Use validated low-fidelity hierarchy blocks, interfaces, units, assumptions, and examples.
3. Generate candidate model artifacts only through official APIs, documented exchange formats, or user-owned editable templates.
4. Run the candidate model and map outputs back into PhysicsGuard observed values.
5. Use residuals and closure to decide whether the blueprint is good enough or needs refinement.

A candidate model is a new engineering artifact, not a recovered commercial-model copy.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Purpose
Bind each physicsguard run to the declared integration mode, evidence, blockers, residual_risk, and claim_boundary.
## Entrypoint Scope
Covers physicsguard-candidate-model-blueprint plus explicitly routed local materials; no unrelated repos, private files, external services, publication, or release claims unless requested and routed.
## Local Material Routing
Use workspace, skill directory, user files, or configured project paths; keep private machine paths local and public instructions portable.
## Entrypoint Acceptance Map
Use SkillGuard as the runtime contract executor attached to the native route/check owner: PhysicsGuard skill family and local PhysicsGuard model/test workflow. It enforces contract gates through that native owner before progress or closure; duplicate SkillGuard-owned execution paths are invalid. Declared gates/routes: model understanding, evidence mapping, validation, closure.
## Use When
Use when the request matches physicsguard-candidate-model-blueprint and needs this governed workflow, materials, checks, or handoff behavior.
## Do Not Use When
Do not use outside the domain, without required materials, when a more specific skill owns the work, or for tiny direct answers.
## Required Workflow
Select the target-owned native route/check surface, run the SkillGuard contract gates around the native workflow, collect evidence, run checks, fix failures, then report.
## Hard Gates
Do not skip phases, do not replace required evidence with prose, do not treat stale reports as current, do not weaken validation to pass, and do not claim completion when blockers remain.
## Output Requirements
Report evidence, failures, blockers, skipped_checks with reasons, residual_risk, and claim_boundary; distinguish checked, unchecked, blocked, and uncertain.
## SkillGuard Maintenance
Keep `.skillguard` contracts, checks, evidence, and ledger current; rerun SkillGuard after entrypoint, route, evidence, or closure changes.
<!-- END SKILLGUARD CONTRACT LAYER -->
