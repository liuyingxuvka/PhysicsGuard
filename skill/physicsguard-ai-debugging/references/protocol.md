# PhysicsGuard AI Debugging Protocol

Run PhysicsGuard as a coarse-to-fine diagnostic tool:

1. Start from the symptom, not from a guessed bad parameter.
2. Use Level 0 checks for whole-system plausibility.
3. Use `hierarchy evaluate` for external observed results so the solver cannot move evidence.
4. Rank suspicious blocks using `top_blocks`.
5. Read `signal_mapping_ledger` for external signal names, unit evidence, confidence, review requirements, stale mappings, and missing conversions.
   If the source is a concrete testbench data file, run the
   `physicsguard-test-file-contract-review` route and require a passing
   `TestFileContract` before broad AI analysis claims.
6. Read `bug_family_followups` so sign/gain, unit-conversion, signal-mapping, or balance siblings are checked before the first failed residual is treated as fully localized.
7. Follow `recommended_refinements` to decide the next signals or parameters to request.
8. Mark uncertain signal mappings with per-variable observed fields when possible; metadata or Assumption Cards must be labeled as lower-confidence evidence.
9. Refine only the suspicious block.

Reports are machine-readable first. `optimization_success` is numerical status; `audit_pass` is residual-threshold plausibility. `confidence` is a heuristic, not probability.

Good next requests are small and targeted:

- upstream/downstream pressure around one component;
- command/actual/feedback around one actuator;
- map input axes plus map output around one calibration table;
- source/load/loss/storage powers around one bus;
- current/cell count/gas flows around one electrochemical stack.

Do not use this workflow to imply equivalence with external solver internals.
