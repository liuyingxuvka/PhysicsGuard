---
name: physicsguard-project-adoption
description: Use when adopting, auditing, upgrading, or checking a target repository's PhysicsGuard workflow records before AI-guided physical simulation debugging.
---

# PhysicsGuard Project Adoption

Use this route before non-trivial PhysicsGuard debugging or model-building work in a repository.

## Workflow

1. Run a read-only audit first:

   ```powershell
   python -m physicsguard.cli project audit --pretty
   ```

2. If the project is not adopted and the user authorized repository setup, run:

   ```powershell
   python -m physicsguard.cli project adopt --pretty
   ```

3. If the installed package version is newer than the record, run:

   ```powershell
   python -m physicsguard.cli project upgrade --pretty
   ```

4. Treat project adoption as workflow evidence only. It does not prove residual behavior, physical correctness, or localization.
5. If the project contains test data, source documents, reusable model assets,
   or multi-file evidence, also route through
   `physicsguard-project-evidence-registry` so the AI can inspect the project
   profile, file map, binding expectations, evidence bundles, and open gaps.
6. If the user asks for multi-project history, reusable model discovery,
   database-level maps, or cross-project comparison, do not answer from project
   adoption alone. Project adoption only says the current repository has a
   workflow record; it does not index or maintain a surrounding database.
7. If the user asks whether the project is ready, complete, validated,
   reusable, or safe for handoff, run or inspect project closure:

   ```powershell
   python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
   ```

   Adoption pass only says the workflow record exists; it is not project
   readiness.

## Claim Boundary

Safe claim: the project has a discoverable PhysicsGuard workflow record.

Unsafe claim: the model is physically correct, the fault is localized, or a commercial model has been reconstructed.

<!-- BEGIN SKILLGUARD CONTRACT LAYER -->
## Purpose
Bind each physicsguard run to the declared integration mode, evidence, blockers, residual_risk, and claim_boundary.
## Entrypoint Scope
Covers physicsguard-project-adoption plus explicitly routed local materials; no unrelated repos, private files, external services, publication, or release claims unless requested and routed.
## Local Material Routing
Use workspace, skill directory, user files, or configured project paths; keep private machine paths local and public instructions portable.
## Entrypoint Acceptance Map
Use SkillGuard as the runtime contract executor attached to the native route/check owner: PhysicsGuard skill family and local PhysicsGuard model/test workflow. It enforces contract gates through that native owner before progress or closure; duplicate SkillGuard-owned execution paths are invalid. Declared gates/routes: model understanding, evidence mapping, validation, closure.
## Use When
Use when the request matches physicsguard-project-adoption and needs this governed workflow, materials, checks, or handoff behavior.
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
