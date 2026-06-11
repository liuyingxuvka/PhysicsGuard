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
   database-level maps, or cross-project comparison, route through
   `physicsguard-database-catalog` before answering. Project adoption only
   says the current repository has a workflow record; it does not index the
   surrounding database.
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
