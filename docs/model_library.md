# Model Library

PhysicsGuard model libraries are lightweight indexes for reusable low-fidelity
model assets and validation evidence.

They store model paths, hashes, compatible testbench profiles, validation report
references, known limits, and reuse status. They do not store large raw test
data and do not claim validity outside recorded validation boundaries.

## Command

```powershell
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

Entries with `validated` or `partial` reuse status must reference validation
evidence.
