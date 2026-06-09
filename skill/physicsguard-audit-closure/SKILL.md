---
name: physicsguard-audit-closure
description: Use before claiming PhysicsGuard localized a fault or completed an audit; checks audit pass/fail, missing inputs, mapping review, stale evidence, skipped checks, refinements, and same-family follow-ups.
---

# PhysicsGuard Audit Closure

Use this route before final localization or completion claims.

Run:

```powershell
python %USERPROFILE%\.codex\skills\physicsguard-ai-debugging\scripts\physicsguard_closure_check.py --ledger CLOSURE.json --audit AUDIT.yaml --observed OBSERVED.yaml --json
```

Blocking or downgrading evidence includes failed audit, missing variables or parameters, review-required mappings, stale evidence, skipped checks, open refinements, and same-family follow-ups.

Closure pass supports only a scoped low-fidelity claim inside the checked audit boundary.
