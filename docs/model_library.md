# Model Library

PhysicsGuard model libraries are lightweight indexes for reusable low-fidelity
model assets and validation evidence.

They store model paths, hashes, compatible testbench profiles, validation report
references, known limits, and reuse status. They do not store large raw test
data and do not claim validity outside recorded validation boundaries.

For cross-project or historical discovery, use the database catalog. The
database catalog may reference model-library indexes, but the model library
remains the owner of model-reuse evidence and known limits.

## Command

```powershell
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

Entries with `validated` or `partial` reuse status must reference validation
evidence.

Entries may also reference a project evidence registry, model context, and
evidence bundle. Blocking project evidence gaps prevent validated reuse claims;
review gaps remain visible as reuse limitations.
