## Why

PhysicsGuard's ten maintained skills already own independent native checks, but the repository also carries a separate SkillGuard "suite parent" maintenance unit that reads those child receipts and attempts to authorize family closure. SkillGuard 0.4 correctly rejects that cross-unit authority, while duplicated runtime/verifier projections and unbounded historical evidence make the author workspace much larger and harder to keep current than the actual skill logic requires.

## What Changes

- **BREAKING**: retire the separate `unit:physicsguard-skill-suite-parent` contract, generated parent control tree, parent receipt inventory, and cross-unit replay commands. No replacement parent receipt or compatibility path remains.
- Keep exactly the ten existing members in `unit:physicsguard-family`, with each skill retaining its declared PhysicsGuard owner, semantic checks, evidence subjects, and independent receipts.
- Replace parent authorization with a read-only, non-authoritative suite structure report that checks inventory and ownership shape but cannot execute checks, consume receipts, or close any member.
- Update author adoption, the managed author block, and all ten current contract trios for SkillGuard 0.4 without adding target-domain criteria or changing PhysicsGuard's declared failure/oracle standards.
- Establish `src/physicsguard/skill_execution_depth.py` and `src/physicsguard/guard_model_contract.py` as the only editable simulator sources. Consumer-facing commands use the installed PhysicsGuard package, while any retained bundled runtime is a generated projection with explicit parity evidence rather than an independent authority.
- Remove the dataset skill's bundled package only if an isolated-machine simulation proves package installation, CLI routing, native verifier routing, and representative dataset commands remain equivalent; otherwise retain and document the projection.
- Add explicit evidence lifecycle classification and read-only GC planning so generated receipts, streams, temporary captures, and historical runs do not become source authority or accumulate without a current/release pin policy.
- Bring the repository's FlowGuard project record to the installed 0.59.0 rule set and update the existing suite model/TestMesh boundaries before implementation confidence is claimed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `physicsguard-skill-suite-runtime-authority`: remove cross-unit parent authorization, define the ten-member same-unit/non-authoritative summary boundary, establish one simulator source authority with verified consumer entrypoints, and require bounded evidence lifecycle handling.

## Impact

Affected surfaces include `.skillguard/author-project.json`, the managed SkillGuard/FlowGuard sections of `AGENTS.md`, all ten `skill/physicsguard-*/.skillguard` contract trios, the PhysicsGuard suite FlowGuard model and checks, runtime-generation scripts, native runtime entrypoints, focused suite/runtime tests, and ignored author evidence stores. No PhysicsGuard physical equations, target-owned failure classes, native oracles, public domain semantics, global installations, Git publication, or external repositories are changed.
