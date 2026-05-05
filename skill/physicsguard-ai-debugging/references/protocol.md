# PhysicsGuard AI Debugging Protocol

Run PhysicsGuard as a coarse-to-fine diagnostic tool:

1. Start from the symptom, not from a guessed bad parameter.
2. Use Level 0 checks for whole-system plausibility.
3. Use `hierarchy evaluate` for external observed results so the solver cannot move evidence.
4. Rank suspicious blocks using `top_blocks`.
5. Follow `recommended_refinements` to decide the next signals or parameters to request.
6. Mark uncertain signal mappings in metadata or Assumption Cards.
7. Refine only the suspicious block.

Reports are machine-readable first. `optimization_success` is numerical status; `audit_pass` is residual-threshold plausibility. `confidence` is a heuristic, not probability.

Good next requests are small and targeted:

- upstream/downstream pressure around one component;
- command/actual/feedback around one actuator;
- map input axes plus map output around one calibration table;
- source/load/loss/storage powers around one bus;
- current/cell count/gas flows around one electrochemical stack.

Do not use this workflow to imply equivalence with external solver internals.

