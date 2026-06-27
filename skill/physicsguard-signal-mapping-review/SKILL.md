---
name: physicsguard-signal-mapping-review
description: Use when external simulation signals are mapped into PhysicsGuard variables and confidence, unit evidence, review state, or stale conditions need inspection before residuals can support fault claims.
---

# PhysicsGuard Signal Mapping Review

Use this route when external model outputs are mapped into PhysicsGuard observed values.
When the source is a concrete test data file with many fields, use
`physicsguard-test-file-contract-review` first or in parallel so every file
field has a catalog row, role/disposition, and evidence-backed mapping.

## Workflow

1. Create or review an intake file based on templates/external_model_intake.yaml.
2. Run:

   ```powershell
   python -m physicsguard.cli intake review INTAKE.yaml --pretty
   ```

3. If mappings are low confidence, missing conversion notes, review-required, or stale, review signal names, units, sign conventions, timing, and neighboring balance signals before blaming a physical parameter.

Intake metadata does not convert or mutate observed values.
Test-file contract mapping edges likewise record evidence only; they must not
invent conversions or silently relabel observed values.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Purpose
Bind each physicsguard run to the declared integration mode, evidence, blockers, residual_risk, and claim_boundary.
## Entrypoint Scope
Covers physicsguard-signal-mapping-review plus explicitly routed local materials; no unrelated repos, private files, external services, publication, or release claims unless requested and routed.
## Local Material Routing
Use workspace, skill directory, user files, or configured project paths; keep private machine paths local and public instructions portable.
## Entrypoint Acceptance Map
Use SkillGuard as the runtime contract executor attached to the native route/check owner: PhysicsGuard skill family and local PhysicsGuard model/test workflow. It enforces contract gates through that native owner before progress or closure; duplicate SkillGuard-owned execution paths are invalid. Declared gates/routes: model understanding, evidence mapping, validation, closure.
## Use When
Use when the request matches physicsguard-signal-mapping-review and needs this governed workflow, materials, checks, or handoff behavior.
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
