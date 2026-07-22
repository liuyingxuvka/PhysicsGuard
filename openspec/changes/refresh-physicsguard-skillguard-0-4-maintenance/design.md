## Context

The repository maintains ten PhysicsGuard skills in one declared unit, `unit:physicsguard-family`. Each member owns its PhysicsGuard route and between seven and eight distinct semantic checks. A later migration added `.flowguard/skillguard-parent` as an eleventh pseudo-skill in a different maintenance unit, then froze paths to the ten child supervisor and installation receipts. SkillGuard 0.4 forbids that cross-unit receipt consumption and its compiler now rejects the parent contract. The parent tree is therefore stale authority, not useful redundancy.

The repository also tracks ten byte-identical copies of `skill_execution_depth.py`, ten byte-identical guard-model verifiers, and a complete copy of the `physicsguard` package inside the dataset-validation skill. `scripts/upgrade_purpose_contracts.py` already copies these files from `src/physicsguard`, but each projection is still named and hashed as if it were an independently edited runtime. Historical owner evidence and parent runs are ignored by Git but have no current/release pin lifecycle.

The installed FlowGuard engine is 0.59.0 while the project record is 0.58.1. The upgrade dry-run has no artifact migration blockers; it adds the missing agent-skill surface rule and synchronizes the project version records.

## Goals / Non-Goals

**Goals:**

- Remove every executable or receipt-bearing authority belonging to the separate suite-parent maintenance unit.
- Keep exactly ten same-unit PhysicsGuard members, their current native owners, declared semantic checks, evidence subjects, and independent receipts.
- Preserve a small suite-level structural view for inventory/ownership diagnostics without allowing it to execute, consume, aggregate, or authorize receipts.
- Make the installed `physicsguard` package the normal single simulator/code authority for the shared execution-depth and guard-model verifier entrypoints.
- Regenerate the ten SkillGuard contract trios with the installed 0.4 compiler while keeping target-domain declarations unchanged.
- Prove runtime relocation and, if sufficient, dataset bundle removal in an isolated environment that does not import the repository source tree.
- Make evidence outputs explicitly non-source and produce a current read-only audit/GC plan; do not quarantine or purge without separate authorization.
- Synchronize the repo-local FlowGuard record and update executable model/TestMesh checks for the new boundary.

**Non-Goals:**

- Do not change physical equations, route-specific obligations, prevented failure classes, native oracles, or the meaning/depth of any target-owned check.
- Do not let SkillGuard invent a domain check or reinterpret a PhysicsGuard result.
- Do not install globally, update installed consumer skills, publish, tag, commit, push, or modify FlowGuard/SkillGuard source repositories.
- Do not preserve the rejected suite-parent contract through an alias, reader, converter, fallback, or archived executable copy.
- Do not apply or purge an evidence GC plan in this change.

## Decisions

1. **Delete the suite-parent maintenance unit instead of moving it into the family unit.** Adding the pseudo-skill to `unit:physicsguard-family` would still create an eleventh closure authority and duplicate the unit's own aggregation. The replacement is a FlowGuard-owned structural report with `authoritative=false`, no `.skillguard` contract, no receipt identifiers, no run root, no installation identity, and no execution command.

2. **Use one closed ten-member inventory.** The existing suite mesh will represent all ten members uniformly; dataset validation stops being a special `affected_sibling`. Every row names one native owner/route and its own declared-check count, while suite checks reject missing, duplicate, foreign-unit, or parent-authority rows.

3. **Use the installed PhysicsGuard package as the shared simulator.** The only editable implementations are `src/physicsguard/skill_execution_depth.py` and `src/physicsguard/guard_model_contract.py`. Author checks invoke them as Python modules and include those canonical files in their exact input graph. Removing a per-skill copy changes storage and launch location only; semantic check ids, owners, dependencies, fixtures, and expected results remain unchanged.

4. **Make dataset bundle removal evidence-gated.** Before deletion, record that every bundled `.py` byte matches the canonical source inventory. After switching its launcher to the installed package, build/install the package into an isolated environment, stage a clean consumer tree, run representative CLI/depth/verifier entrypoints from outside the repository, and compare the command/result boundary. Only a current pass permits removing `runtime/physicsguard`, its top-level depth copy, and native-runtime manifest. A failed or incomplete proof keeps that generated bundle and records the reduction as blocked rather than weakening the entrypoint.

5. **Keep contract generation deterministic and target-neutral.** `scripts/upgrade_purpose_contracts.py` remains the sole generator for the ten current source contracts and guard artifacts, but it will generate package-module commands and canonical source selectors instead of copied Python implementations. It will preserve the existing target configuration, native checks, owner ids, failure ids, obligation ids, fixtures, and claim boundaries. SkillGuard 0.4 then compiles each source into the only generated `compiled-contract.json` and `check-manifest.json` pair.

6. **Separate source, consumer projection, evidence, and release identities.** Contract-source and canonical simulator files are source inputs. Compiled contracts/manifests are generated author control. Supervisor receipts, compressed streams, run roots, reports, and GC plans are evidence outputs and never input selectors. Consumer trees contain no `.skillguard` state and declare the PhysicsGuard package prerequisite. No installation transaction is performed in this change.

7. **Use read-only evidence lifecycle operations only.** Audit the canonical family evidence root and the retired parent evidence root, identify current/release pins, and generate exact GC plans. Retired parent evidence may be unreachable, but it remains on disk until a separately authorized quarantine and later purge. This avoids treating cleanup as validation or deleting the only historical proof before new current evidence exists.

8. **Update FlowGuard before broad implementation confidence.** Apply the 0.59.0 project-record delta, then update the suite model, StructureMesh, TestMesh, and focused checks. DevelopmentProcessFlow treats OpenSpec artifacts as read-only planning context and keeps native checks, SkillGuard compilation, isolated runtime parity, and evidence lifecycle as separate freshness domains.

## Risks / Trade-offs

- [A consumer machine lacks the PhysicsGuard package] → Commands fail visibly with an explicit package/version prerequisite; isolated validation proves the supported package-installed path and no bundled fallback is retained.
- [Package relocation accidentally changes a native check] → Keep semantic ids/owners/fixtures fixed and compare all ten generated check inventories before and after; run every affected native owner under one frozen unit plan.
- [Dataset bundle deletion removes a working offline route] → Delete it only after isolated package/entrypoint parity; otherwise retain it as a generated, hash-checked projection and report the unresolved size cost.
- [The structural summary is mistaken for closure evidence] → Give it no receipt fields or status capable of authorizing work, assert `authoritative=false`, and test that no `.flowguard/skillguard-parent`, parent unit id, or parent receipt replay command remains.
- [Regeneration overwrites peer work] → Recheck Git status and source hashes immediately before generation, preserve unknown changes, and stop on overlapping paths.
- [Historical evidence continues to occupy disk] → Produce current audit and GC plans now, but leave quarantine/purge for a separately authorized lifecycle action after current/release pins exist.

## Migration Plan

1. Synchronize the FlowGuard project record and add/update suite development-process, structure, and test models for the new authority boundary.
2. Replace the suite-parent control tree, frozen receipt inventory, generator, and replay verifier with a non-authoritative static inventory/structure check; update focused tests and remove all references to the parent unit.
3. Update the current ten-contract generator for canonical package module entrypoints, runtime prerequisite metadata, and unchanged per-member semantic inventories; regenerate source artifacts and compile all ten trios with SkillGuard 0.4.
4. Run pre-deletion byte-parity capture, isolated package/consumer entrypoint checks, and choose the dataset reduction disposition from that evidence.
5. Run the affected FlowGuard model checks, native PhysicsGuard tests, OpenSpec validation, SkillGuard maintainer audit, frozen unit validation, clean consumer projection audit, and read-only evidence audit/GC planning.
6. Record actual passes, failures, skipped checks, current evidence, and remaining cleanup authorization. Do not install, release, or archive the OpenSpec change in this task.

Rollback is a source-level revert before publication. There is no live compatibility route: restoring the deleted suite-parent authority would require a new design that satisfies current same-unit ownership, not replaying the retired files.

