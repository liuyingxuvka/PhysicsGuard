# PhysicsGuard Project Adoption

## Reuse within one read-only task

Pass an already qualified exact current summary, affected projection or reverse trace to the next native owner when its source, material, authority, revision and selector identities remain unchanged. Combine all affected seed ids for the requested scope into one affected API call. Inspect the existing returned slice before asking for another projection of the same scope. If inputs or raw target material change, run the existing canonical qualification gate again; a prior review, summary or hash label does not bypass it. Unknown or invalid seeds block the whole request; never join separately accepted fragments to hide a rejected seed. This is task-local reuse of an actual result, without a persistent cache or new receipt.

Use this route before non-trivial PhysicsGuard debugging or model-building work in a repository.

## Blueprint adoption identity

When a canonical blueprint exists, record its path, target id/revision and scope, `artifact_root: blueprint_directory`, blueprint/review fingerprint, available summary/affected/full projection identity, and exact native authority owners. Adoption reports missing or stale blueprint data as a workflow gap; it does not author an alternate blueprint, derive completeness, or scan the repository as fallback.

Executable projection entry (when a canonical blueprint exists): call `physicsguard.summary_physical_blueprint_projection(blueprint, review)` to record the current adoption identity. Record an already requested affected or full projection fingerprint when present; adoption itself does not broaden the requested scope.

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
   Also distinguish repository source capability from the active installed
   runtime: do not claim adequacy or predictive gates are available on the
   machine until the invoked CLI exposes and executes them. Upgrade through
   the repository's declared adoption route when authorized; do not replace it
   with copied prompt text or a temporary checker.
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
8. For non-snapshot validation, require current repository artifacts and the
   native quantitative adequacy receipt. For prediction readiness, require the
   stateful future-rollout route and its native receipt. An older adoption
   record, a generated template, or maintenance-contract text cannot substitute
   for those runtime checks.

## Claim Boundary

Safe claim: the project has a discoverable PhysicsGuard workflow record.

Unsafe claim: the model is physically correct, the fault is localized, or a commercial model has been reconstructed.
