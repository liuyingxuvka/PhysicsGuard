## Context

PhysicsGuard already removed its Codex database skill routes, but the Python
package still exposes database catalog/lifecycle code and a `physicsguard
database` CLI. That leaves two database control paths once DataBank exists as a
standalone repository. The final boundary must be simpler: PhysicsGuard emits
physical provider evidence; DataBank owns the database ledger.

## Goals / Non-Goals

**Goals:**

- Remove the `physicsguard database` command group without replacement inside
  PhysicsGuard.
- Remove database catalog/lifecycle core modules, schemas, templates, tests,
  examples, docs, package exports, and skill guidance from PhysicsGuard.
- Keep project evidence registry, test-file contracts, model validation, model
  library, signal mapping, and project closure in PhysicsGuard.
- Keep old database names only in historical logs or forbidden-skill checks.
- Update version to `0.9.0` for the breaking CLI/API removal.

**Non-Goals:**

- Do not implement DataBank inside PhysicsGuard.
- Do not add compatibility aliases, bridge commands, or fallback text.
- Do not delete unrelated historical changelog/FlowGuard/OpenSpec records.
- Do not remove ordinary uses of the word "database" when they mean external
  exports, source systems, or historical audit logs rather than PhysicsGuard
  database ownership.

## Decisions

- Public command disposition: delete the `database` subparser and handlers
  rather than returning a help message that points to DataBank. A helper message
  would still be a live compatibility surface.
- Package API disposition: remove database exports from `physicsguard.__init__`
  and remove database loader helpers from runtime paths unless they are needed
  only by provider evidence types.
- Documentation disposition: README and current skills may mention that
  database-ledger work belongs outside PhysicsGuard, but must not include old
  `physicsguard database` commands.
- Test disposition: remove database-engine tests from PhysicsGuard; keep
  negative tests or checks that old skill routes and CLI routes are absent.
- Versioning: publish the next local package version as `0.9.0` because users
  who called the old CLI/API must change to DataBank.

## Risks / Trade-offs

- Removing schema exports can break code that imported database types ->
  acceptance requires no internal PhysicsGuard imports remain and package import
  succeeds.
- Old docs can keep teaching the removed route -> acceptance requires targeted
  search for old command forms and route names.
- Portable-header helpers may reference removed database commands -> update or
  delete those hints instead of leaving dead commands.
- Historical logs contain old command strings -> treat logs as audit history
  and do not use search rules that forbid historical evidence.

## Migration Plan

1. Confirm DataBank package CLI exists locally before deleting PhysicsGuard
   database engine.
2. Remove PhysicsGuard database CLI, core/schema modules, templates, tests,
   examples, docs, and package exports.
3. Update README, skills, package version, project adoption record, and
   installed skill sync.
4. Update FlowGuard model-code ledgers and remove or retire database-specific
   FlowGuard scripts from active validation.
5. Run negative CLI checks, OpenSpec validation, FlowGuard project audit,
   remaining FlowGuard checks, installed skill validation, and full pytest.
