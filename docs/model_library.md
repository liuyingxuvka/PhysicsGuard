# Model Library

PhysicsGuard model libraries are lightweight indexes for reusable low-fidelity
model assets and validation evidence.

They store model paths, hashes, compatible testbench profiles, validation report
references, known limits, and reuse status. They do not store large raw test
data and do not claim validity outside recorded validation boundaries.

For cross-project or historical discovery, treat this file as provider
evidence only. The model library remains the owner of model-reuse evidence and
known limits, while any external database ledger owns indexing, freshness,
query, and cross-project closure.

## Command

```powershell
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

Entries with `validated` or `partial` reuse status must reference validation
evidence.

Entries may also reference a project evidence registry, model context, and
evidence bundle. Blocking project evidence gaps prevent validated reuse claims;
review gaps remain visible as reuse limitations.

A broad `validated` reuse claim additionally needs a current native depth
receipt with compatible covered scope and passing quantitative adequacy over
the artifact-derived universe. Snapshot or shallow receipts support only
explicitly bounded partial reuse. Record predictive capability only when a
`stateful_dynamic` rollout has a passing disjoint future-holdout receipt and a
declared checked horizon; pointwise validation is not predictive evidence.
