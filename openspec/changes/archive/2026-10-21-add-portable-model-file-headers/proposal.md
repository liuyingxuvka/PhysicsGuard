## Why

PhysicsGuard YAML audit files can be copied to machines that do not have the Codex skill, current README, or local chat context. Each retained model file should identify itself as a PhysicsGuard low-fidelity audit or blueprint, point back to the public repository, and warn readers not to treat it as a high-fidelity solver or commercial-tool adapter.

## What Changes

- Add portable comment headers to existing committed PhysicsGuard YAML model files.
- Keep headers schema-neutral by using YAML comments only.
- Update model-generation guidance so future YAML audit, hierarchy, observed snapshot, and blueprint files receive the same header.
- Add package repository metadata so installed and published package metadata points back to GitHub.
- Release the change as a patch version because it improves documentation/provenance without changing runtime behavior.

## Capabilities

### New Capabilities

- `portable-model-file-headers`: PhysicsGuard model files carry enough local context for readers on another machine to understand purpose, repository, basic command entry point, SI-unit expectation, and safety boundary.

### Modified Capabilities

- None.

## Impact

- Affects committed YAML examples and hierarchy templates under `examples/`.
- Affects documentation and skill guidance under `docs/`, `skill/`, and `README.md`.
- Affects package metadata and visible version files.
- Does not change solver behavior, module equations, schema parsing, or external dependencies.
