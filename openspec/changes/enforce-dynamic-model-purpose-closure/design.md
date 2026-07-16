## Context

The maintained ten-skill suite already has a useful proof chain: contract, candidate binding, known-good, every known-bad, and native receipt. The defect is authority placement. The generator writes route-wide fixed declarations into each skill's bundled `guard-model/` directory, and the verifier always reads those bundled files. A real model can therefore reuse a capability fixture without declaring its own purpose or demonstrating that its own candidate blocks the failures selected for that modeling instance.

The current SkillGuard V2 layer is intentionally generic and must remain so. PhysicsGuard owns physical/evidence semantics and native pass/block decisions; SkillGuard owns only declared check execution, receipts, projections, and closure.

## Goals / Non-Goals

**Goals:**

- Preserve existing family failure catalogs and tests as immutable baseline regression.
- Add one mandatory target-local authority chain for every concrete model/task.
- Make contract, candidate, oracle, fixture, and proof identity changes stale by construction.
- Reject accidental use of bundled family baselines as current-task evidence.
- Keep the ten generated skills consistent through the existing generator.

**Non-Goals:**

- Do not prescribe one fixed failure for a PhysicsGuard skill or family.
- Do not require SkillGuard to understand physical semantics or invent failure classes.
- Do not install, publish, release, or redesign the broader validation-depth system.
- Do not claim that finite fixtures prove all future physical operating points.

## Decisions

### 1. Separate artifact roles instead of deleting the fixed suite

Bundled `guard-model/` artifacts will be renamed semantically as `family_baseline_regression`. Their checks remain mandatory capability regression for maintained-skill closure, but their receipts explicitly cannot satisfy a real target model.

Alternative considered: delete fixed contracts. Rejected because they already test route capability and preserve valuable regression coverage.

### 2. Put current authority under the explicit target root

Each modeling instance will use `.physicsguard/model-purpose/<model-id>/` containing `contract.json`, `candidate.json`, `oracles.json`, `known-good.json`, `known-bad.json`, and `proofs.json`. Current-instance CLI actions require `--target-root` plus explicit artifact paths. Paths must resolve inside that root and cannot point into an installed/source skill's bundled `guard-model/`.

Alternative considered: infer the current directory and conventional paths. Rejected because implicit roots can silently bind the wrong repository or baseline.

### 3. Freeze purpose before candidate and bind the actual model artifact

The dynamic contract records one concrete purpose, one or more AI-selected prevented failures, physical/evidence and claim boundaries, and native owner/route. Every failure owns a native oracle and at least one good and bad case. The candidate records the exact contract fingerprint, full failure-id set, actual candidate artifact path and SHA-256, and a hash-linked two-event authoring chain whose sequence is purpose freeze then candidate build.

### 4. Proof closure is exhaustive over the declared dynamic failure set

The final proof set binds the contract and candidate fingerprints. It must contain a passing known-good result and a blocking result for every declared failure. Each result binds the exact oracle, case id, fixture artifact hash, finding code, and PhysicsGuard-native execution owner. Self-reported status is forbidden. Missing or extra mappings block closure.

### 5. Keep SkillGuard generic

Generated SkillGuard authorities continue to run baseline capability checks only. The skill prompt directs real work to the PhysicsGuard current-instance verifier. SkillGuard may supervise that target-declared command later, but it never supplies the purpose, failure set, oracle, or physical verdict.

### 6. Model the new distinction in FlowGuard

The FlowGuard export and preflight distinguish `family_baseline_regression` from `current_model_purpose`. The success terminal for a real model requires dynamic contract freeze, candidate binding, good proof, exhaustive bad proof, and current proof-set closure. Baseline-only evidence reaches a blocked terminal.

## Risks / Trade-offs

- [Risk] More artifacts per real model increase authoring work. → Provide a strict, small schema and clear CLI diagnostics; preserve templates only as examples, never as authority.
- [Risk] An AI could write arbitrary `pass`/`blocked` JSON. → Require exact native owner/oracle identities, fixture hashes, finding codes, and proof-set binding; fixtures still need target-native execution.
- [Risk] Fixed baseline checks may be misunderstood as model proof. → Add explicit artifact role and claim boundary in schemas, prompts, FlowGuard export, and verifier errors.
- [Risk] Existing dirty worktree contains earlier upgrades. → Modify only generator-owned blocks and focused source/tests; avoid installation and broad unrelated cleanup.

## Migration Plan

1. Add the dynamic current-instance schemas and verifier actions while reclassifying existing bundled schemas as baseline regression.
2. Update the generator, regenerate all ten maintained skills, and verify exact inventory/parity locally.
3. Add focused positive and adversarial tests for dynamic purpose selection, candidate ordering/binding, proof exhaustion, path isolation, and baseline rejection.
4. Update FlowGuard model/preflight and run affected checks.
5. Leave source changes uninstalled for parent integration.

Rollback is limited to this OpenSpec change's files and generator-owned outputs; the prior validation-depth upgrade remains untouched.

## Open Questions

None. This change intentionally leaves the actual failure selection to the AI and PhysicsGuard task context rather than fixing it in the family skill.
