# PhysicsGuard Candidate Model Blueprint

Use this route when the user asks to build a candidate model from PhysicsGuard evidence.

## Workflow

1. Start from a passed model-understanding preflight.
2. Use validated low-fidelity hierarchy blocks, interfaces, units, assumptions, and examples.
3. Generate candidate model artifacts only through official APIs, documented exchange formats, or user-owned editable templates.
4. Run the candidate model and map outputs back into PhysicsGuard observed values.
5. Use residuals, quantitative adequacy, and closure to decide whether the
   blueprint is good enough or needs refinement. Do not validate only a small
   convenient subset when the claim covers a larger time/signal/parameter
   universe. Source-classify every parameter as static or time-varying, and
   require each time-varying parameter's own adequate history.
6. Declare whether the candidate is `pointwise` or `stateful_dynamic`.
   Pointwise relations cannot support simulation or prediction claims. For a
   stateful predictive claim, execute the candidate through the official
   target interface, preserve the initial state, step size, horizon, producer
   receipt, and exact trajectory identity, and validate it against a disjoint
   future holdout with the native predictive-rollout gate.
7. Keep the base task model and candidate model as separate content-addressed
   artifacts. Record the triggering hypothesis mismatch and the exact
   regression and holdout inventory. A stateful candidate additionally
   consumes the existing native predictive-rollout receipt:

   ```powershell
   python -m physicsguard.cli task-model revision CANDIDATE_REVISION.yaml --pretty
   ```

8. Accept the candidate only when every declared check passes. Reject an
   unapplied failed candidate. If an applied candidate fails, roll back only to
   the exact still-current base identity. Never overwrite or delete v1 during
   candidate evaluation.

A candidate model is a new engineering artifact, not a recovered commercial-model copy.
Even a passing predictive rollout is bounded to its checked horizon, signals,
thresholds, initial state, and future-holdout cases.
This loop revises only the current task model. It does not modify PhysicsGuard,
its default thresholds, its reusable model library, or an installed skill.
