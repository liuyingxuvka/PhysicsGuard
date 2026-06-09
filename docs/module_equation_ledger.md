# Module Equation Ledger

PhysicsGuard keeps a module/equation ledger at `.physicsguard/module_equation_ledger.yaml`. It helps AI agents understand what each module family checks before they use a residual as evidence.

The ledger records:

- module types covered by the entry;
- low-fidelity equation summary;
- SI unit expectations;
- assumptions and validity boundaries;
- diagnostic keys;
- representative tests and examples;
- stale-evidence conditions.

Run:

```powershell
python scripts/check_module_equation_ledger.py --json
```

The ledger is navigation and review evidence. Passing the ledger check does not prove physical correctness. Runtime confidence still needs PhysicsGuard CLI reports, FlowGuard checks, focused tests, examples, and closure evidence.
