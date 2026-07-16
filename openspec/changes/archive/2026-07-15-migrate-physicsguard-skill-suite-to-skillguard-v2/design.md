## Context

PhysicsGuard has one deeply integrated primary skill (`physicsguard-model-dataset-validation`) and nine maintained satellites. Earlier migration work removed the former V1 surface and added valuable route-specific depth logic, but its contracts still depend on retired SkillGuard calibration and integration-mode fields. Each target already has a real PhysicsGuard route, so this change upgrades those routes in place: PhysicsGuard owns what each model prevents and how that is proven; current SkillGuard generically supervises the checks PhysicsGuard declares.

## Goals / Non-Goals

**Goals:**

- Give every maintained PhysicsGuard skill exactly one current runtime authority and one stable target-native owner.
- Require route-specific current-run PhysicsGuard receipts, complete relevant object inventories, quantitative depth where the route has data/time axes, and visible bounded claim scope.
- Freeze a PhysicsGuard-native prevented-failure contract before candidate construction and prove every declared blockable failure with mandatory known-good/known-bad checks.
- Keep SkillGuard target-neutral and free of PhysicsGuard semantics, target categories, and selectable modes.
- Reattach all ten maintained skills through a parent suite mesh before family-wide confidence.
- Delete former V1 authority and generated runtime outputs after current V2 source/install parity is proven.

**Non-Goals:**

- Do not move physical equations, signal mapping, file contracts, project evidence, model-library judgment, blueprint generation, or audit closure into SkillGuard.
- Do not require project-level numerical precision from every low-fidelity audit; enforce the target's declared accuracy boundary and anti-degeneracy floor.
- Do not remove ordinary PhysicsGuard snapshot/data compatibility when its product contract still requires bounded use.
- Do not modify the canonical FlowGuard or SkillGuard repositories from this change.

## Decisions

1. Treat the suite as a parent mesh with ten fixed child ids. The parent inventory is closed: `physicsguard-ai-debugging`, `physicsguard-audit-closure`, `physicsguard-candidate-model-blueprint`, `physicsguard-model-dataset-validation`, `physicsguard-model-library`, `physicsguard-model-understanding-preflight`, `physicsguard-project-adoption`, `physicsguard-project-evidence-registry`, `physicsguard-signal-mapping-review`, and `physicsguard-test-file-contract-review`. A missing, duplicate, foreign, or unconsumed child blocks suite closure.
2. Assign a route-specific native owner rather than reusing a generic SkillGuard owner: `physicsguard.ai-debugging`, `physicsguard.audit-closure`, `physicsguard.candidate-model-blueprint`, `physicsguard.model-dataset-validation`, `physicsguard.model-library`, `physicsguard.model-understanding-preflight`, `physicsguard.project-adoption`, `physicsguard.project-evidence-registry`, `physicsguard.signal-mapping-review`, and `physicsguard.test-file-contract-review`.
3. Reuse the existing native commands, depth evaluator, receipt builders, route policies, and suite mesh. Replace only the obsolete SkillGuard-specific wire. The target adapter serializes the exact PhysicsGuard result, inputs, scope, findings, missing items, and claim boundary; it does not ask SkillGuard to interpret physical meaning.
4. Before candidate construction, every governed model/route freezes a PhysicsGuard-native contract containing: model/route identity, prevented failure classes, input and physical/evidence boundary, native oracle identity and predicate, expected finding code, proof strength, known limit, and bounded claim. Candidate, purpose, universe, and proof inputs remain distinct.
5. Route-specific depth is not one global numeric formula. Data/time-bearing routes use complete denominators, per-object dynamic floors, early/middle/late distribution, maximum-hole checks, and any stricter project policy. Inventory/decision routes require complete declared/discovered/required/excluded reconciliation and one row per critical object/obligation. All routes preserve bounded or blocked native outcomes.
6. Each target owns one known-good case covering every required obligation and at least one known-bad case for every declared prevented failure class. Each bad case must execute the target's native evaluator, be blocked, identify the exact failure class, and emit its declared finding code. A declaration without proof, a proof without a declaration, or a generic expected-status label is invalid.
7. The generic SkillGuard source contract contains only declared checks, owners, dependency edges, input selectors, and closure obligations. `depth_profile`, `calibration`, `integration_mode`, target classification, and Guard-family policy are forbidden. Source-only proof checks and scheduled project evidence remain distinct. The parent suite consumes child terminal-success receipts and never reruns children as a receipt consumer.
8. V1 retirement is destructive and last. After child V2 closure, parent mesh closure, transactional install parity, and current installation receipt replay pass, remove former manifests, work contracts, generic V1 checkers, mutable reports/evidence/ledgers, caches, and fallback instructions. Store the deterministic retirement receipt at project level under `.flowguard/retirement-receipts/`, never as a live or historical artifact inside a skill's `.skillguard` authority root.
9. Rollback is a source revert of the migration change and a new explicit installation transaction. No dormant V1 runtime is retained as an in-place rollback mechanism.
10. The `physicsguard-model-dataset-validation` primary is the tenth maintained child rather than a satellite. The parent mesh consumes its current exact receipt together with the nine satellite receipts because they share its validation-depth and receipt kernel. A stale, missing, relabeled, or merely locally green primary receipt blocks family closure.
11. The former narrow retirement receipt is not accepted as proof for the expanded retirement inventory. Generic V1 checkers, policy files, mutable reports/evidence/ledgers, caches, and target-local runtime outputs are part of the retirement denominator. A project-level deterministic source-retirement receipt is issued only after the full source scan is clean; actual installed absence, installation currentness, and parent replay remain separate mandatory gates.
12. There is no selectable PhysicsGuard or SkillGuard operating mode. Contract validation, known-good proof, every declared known-bad proof, native route execution, and closure are a fixed dependency chain. A route may have a bounded claim, but it cannot bypass a mandatory proof by selecting a lighter mode.

## Risks / Trade-offs

- [Ten maintained routes expose different evidence shapes] → Use one identity envelope with route-specific target-owned payloads and obligations; never flatten domain semantics into generic counts.
- [A known-good/bad proof fixture can be mistaken for real project proof] → Mark capability proof as source-only and require current target-owned project evidence for a real project claim; reject every cross-domain projection.
- [Batch generation can overwrite a peer change] → Freeze the exact child file inventory, edit only owned target paths, re-read hashes before generation, and use one migration writer.
- [Retirement deletes familiar reports] → Keep historical proof in OpenSpec/verification receipts while removing executable or mutable legacy authority from the live skill roots.
- [Final checks become stale while SkillGuard changes] → Do not compile, supervise, install, or run the parent full mesh until the shared SkillGuard source/install identity freezes.

## Migration Plan

1. Freeze the ten-child inventory and parent partition/reattachment map.
2. Preserve the existing native route policies and convert the current purpose/calibration material into PhysicsGuard-owned guard-model contracts and per-failure known-good/known-bad proofs.
3. Author each generic `contract-source.json`; compile the exact current contract/check manifest and run focused native/known-bad checks.
4. Run one fixed-input parent suite mesh that consumes current child receipts and proves all children reattach without overlap or stale evidence.
5. Transactionally install all ten skills, verify source/install hashes and installation currentness replay, then remove every former V1 authority/residual in source and installed copies.
6. Refresh global routing only after all managed prompts and installed skill hashes freeze.

## Open Questions

None. Exact shared SkillGuard schema versions and installation identity values are resolved from the downstream freeze receipt rather than precommitted here.
