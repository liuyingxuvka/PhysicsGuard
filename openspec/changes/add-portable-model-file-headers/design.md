## Context

PhysicsGuard already explains its repository and safety boundary in README and skill files, but most retained YAML models do not carry that context with them. Existing committed examples are plain YAML documents, so adding YAML comment headers is the lowest-risk way to make them portable without changing schema validation or runtime behavior.

The release also needs synchronized version and package metadata because the user requested a GitHub release after the documentation/provenance fix.

## Goals / Non-Goals

**Goals:**

- Add a concise, uniform header to every committed PhysicsGuard YAML model under `examples/`.
- Make the header useful without any installed Codex skill: purpose, repository, likely command, SI-unit expectation, and safety boundary.
- Keep all headers YAML comments so existing loaders ignore them.
- Update future-generation guidance and package metadata so this remains the default for new files.
- Validate that headers do not break YAML parsing, CLI examples, FlowGuard lifecycle checks, tests, local editable install, and release version alignment.

**Non-Goals:**

- Do not change residual equations, physical module behavior, solver behavior, schema fields, or CLI output contracts.
- Do not add high-fidelity model logic, commercial-tool adapters, or external simulation dependencies.
- Do not add provenance metadata fields to schemas solely for this header.
- Do not publish ignored local artifacts such as local KB history, local FlowGuard adoption logs, generated Simulink outputs, or copied model binaries.

## Decisions

1. Use YAML comments, not schema metadata.
   - Rationale: comments are visible in raw files, portable across machines, and ignored by current YAML parsing.
   - Alternative considered: add metadata fields. Rejected because flat `SystemSpec` examples do not all currently carry metadata and schema-level provenance would create unnecessary behavior/API surface.

2. Generate purpose text from existing YAML fields and filenames.
   - Rationale: many files already have `description`, `audit_name`, `observation_name`, or `system_name`. Falling back to the filename avoids hand-editing hundreds of files while keeping each header specific enough.
   - Alternative considered: one generic identical header. Rejected because the user specifically wants a quick explanation of what each file is for.

3. Use command hints based on file kind.
   - Rationale: readers can immediately try the file without knowing the CLI mode. Hierarchy templates point to `hierarchy run`; observed snapshots point to `evaluate` or `hierarchy evaluate` pairing; flat systems point to `run`.
   - Alternative considered: no command hint. Rejected because repository-only context is less useful on an unprepared machine.

4. Treat this as a patch release.
   - Rationale: it is a documentation/provenance and packaging metadata improvement with no runtime behavior change.

## Risks / Trade-offs

- Header generation could accidentally alter YAML content → Mitigate by only prepending comments and re-parsing every YAML file.
- Long purpose lines could become noisy → Mitigate by deriving concise one-line purpose strings and wrapping only when needed.
- Existing files without descriptions may receive weaker filename-derived purpose → Mitigate by preferring existing descriptions where present and preserving runtime examples unchanged.
- Release evidence can stale if peer agents write after validation → Mitigate with final `git status`, focused parse checks, full tests, install verification, version alignment, and remote/tag verification immediately before publication.
