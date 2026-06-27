---
name: physicsguard-model-understanding-preflight
description: Use before PhysicsGuard audits of external models to capture visible symptom, physical boundary, subsystem blocks, units, assumptions, uncertain mappings, and stop conditions.
---

# PhysicsGuard Model Understanding Preflight

Use this route before interpreting residuals for a non-trivial external model.
If a concrete testbench data file is part of the work, record the file/bench
boundary and route to `physicsguard-test-file-contract-review` before broad
analysis claims.

## Workflow

1. Create or review a preflight file based on templates/model_understanding_preflight.yaml.
2. Run:

   ```powershell
   python -m physicsguard.cli preflight review PREFLIGHT.yaml --pretty
   ```

3. If missing inputs or uncertain mappings are reported, complete them or route to signal mapping review before fault claims.

Preflight pass is planning evidence only. It is not residual validation.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Purpose
Bind each physicsguard run to the declared integration mode, evidence, blockers, residual_risk, and claim_boundary.
## Entrypoint Scope
Covers physicsguard-model-understanding-preflight plus explicitly routed local materials; no unrelated repos, private files, external services, publication, or release claims unless requested and routed.
## Local Material Routing
Use workspace, skill directory, user files, or configured project paths; keep private machine paths local and public instructions portable.
## Entrypoint Acceptance Map
Use SkillGuard as the runtime contract executor attached to the native route/check owner: PhysicsGuard skill family and local PhysicsGuard model/test workflow. It enforces contract gates through that native owner before progress or closure; duplicate SkillGuard-owned execution paths are invalid. Declared gates/routes: model understanding, evidence mapping, validation, closure.
## Use When
Use when the request matches physicsguard-model-understanding-preflight and needs this governed workflow, materials, checks, or handoff behavior.
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
