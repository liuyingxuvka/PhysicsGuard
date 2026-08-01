## Context

See `proposal.md` for motivation. The current ten skills already own distinct native routes and strong deepening contracts, but each `SKILL.md` eagerly repeats the full generated purpose/depth block and validated-template-pack block. The repository is a SkillGuard author source; PhysicsGuard 0.15.1, FlowGuard 0.68.2, and SkillGuard 0.7.2 are the current source/toolchain identities. Other agents' FlowGuard adoption edits plus untracked `.flowguard/evidence/` must be preserved.

## Goals / Non-Goals

**Goals:**

- Make one route decision from compact, explicit, machine-checkable facts.
- Keep all ten skills direct and preserve every current native route/check owner.
- Move detail behind one-level conditional references without reducing model depth.
- Make prompt loading and preserved deep capability executable regression surfaces.

**Non-Goals:**

- Change physical equations, native evaluation semantics, or target-owned evidence judgment.
- Add a universal PhysicsGuard router, compatibility reader, fallback, or second authority.
- Run the frozen final full SkillGuard gate, install consumers, or publish 0.15.1.

## Decisions

### 1. Use one target-local route capsule per skill

Each `references/route-capsule.json` is generated from the same reviewed target table that already owns route purpose and failure classes. It declares exact identity, `direct` or `composite` role, positive triggers, reject/handoff cases, minimum inputs, outputs, conditional reference triggers, and claim boundary. JSON is chosen over prose-only routing because tests can compare it with guard contracts, OpenAI metadata, and load graphs. A central runtime router was rejected because it would recreate a parent and make the ten consumer skills interdependent.

### 2. Keep `SKILL.md` as a compact entry map

Each entry contains only identity, accept/reject rules, the smallest executable workflow, hard claim boundaries, and conditional pointers. Existing detailed target workflows move to `references/native-route-protocol.md`; this is a one-level reference and remains target-owned. The frontmatter description carries the full trigger boundary because it is the only material available before invocation.

### 3. Generate depth/purpose and template routing separately

`scripts/upgrade_purpose_contracts.py` remains the sole reviewed generator. It writes `references/native-depth-and-purpose.md`, including target purpose/failures and all shared strict deepening rules, and writes the complete current VTP protocol to `references/template-pack-routing.md`. The compact entry contains conditional pointers only. A shared cross-skill reference was rejected because a clean installed skill must remain independently usable.

### 4. Model prompt loading as an author-side FlowGuard graph

The author-only load graph records `metadata -> SKILL -> capsule`, then conditional edges to native route, depth, and template references. The checker validates identities, paths, triggers, hashes, prompt bounds, reachability of deep obligations, and known-bad mutations. This graph is author evidence only; it is not copied into consumers and does not claim future model behavior.

### 5. Preserve affected-only SkillGuard ownership

The generator adds the new generated artifacts and prompt/load tests to exact component selectors. We regenerate and compile all ten current contract trios because the shared generator and every entry projection change. We run focused target-owned checks and model regressions, but leave the one frozen full maintenance-unit gate to the integration owner as requested.

## Risks / Trade-offs

- [A compact entry can hide an essential gate] → Require route-capsule reachability and known-bad tests for every deepening family, holdout, rollout, `model_miss`, and terminal boundary.
- [Moving prose can create stale duplicates] → Make generated depth and VTP references single-source outputs and reject managed blocks remaining in `SKILL.md`.
- [The broad route may still win from metadata wording] → Narrow its frontmatter/OpenAI prompt to mixed or ambiguous work and add concrete direct-route fixtures for all ten skills.
- [All ten contracts become stale together] → Recompile the ten same-unit contracts after source freeze and run only their declared affected checks; do not claim final parent closure.
- [Other agents may update FlowGuard adoption evidence concurrently] → Never modify `.flowguard/evidence/`; re-read tracked peer changes before touching overlapping model files.

## Migration Plan

1. Freeze current route/check identities and copy existing detailed route protocols into target-local references.
2. Extend the generator and regenerate compact prompts, capsules, depth/purpose references, VTP references, runtime metadata, guard models, and contract sources.
3. Update the author-only FlowGuard load graph/checker and focused prompt/known-bad tests.
4. Compile the ten contract trios with the installed SkillGuard author toolchain, then run affected native checks and model regressions.
5. Update 0.15.1 source metadata and mark OpenSpec tasks complete. Do not install, commit, push, tag, release, or run the final full unit gate in this task.
