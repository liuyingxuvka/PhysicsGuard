## ADDED Requirements

### Requirement: Portable PhysicsGuard model headers
Every committed PhysicsGuard YAML audit, hierarchy, observed snapshot, or model-blueprint file SHALL begin with a YAML comment header that identifies the file as a PhysicsGuard artifact, states a concise purpose, points to the public PhysicsGuard GitHub repository, gives a relevant command/use hint, and states the low-fidelity SI-unit safety boundary.

#### Scenario: Reader opens a model file without installed skill context
- **WHEN** a user opens a committed PhysicsGuard YAML model file on a machine that does not have the PhysicsGuard Codex skill installed
- **THEN** the first lines explain that the file is a PhysicsGuard low-fidelity audit or blueprint, what the specific file is for, where the GitHub repository lives, how to start using it, and what not to treat it as

#### Scenario: Existing YAML parsing remains unchanged
- **WHEN** PhysicsGuard loads a header-bearing YAML file through the existing loaders or CLI commands
- **THEN** the header is ignored as comments and the parsed model content remains valid

### Requirement: Future model generation guidance
PhysicsGuard documentation and skill guidance SHALL instruct future agents to add the same portable header to newly created audit YAML, hierarchy templates, observed snapshots, and candidate-model blueprints without adding schema metadata solely for the header.

#### Scenario: Agent creates a new model file
- **WHEN** an agent follows the PhysicsGuard skill or documentation to create a new YAML model artifact
- **THEN** the created file includes the portable comment header before YAML content

### Requirement: Public repository provenance in package metadata
PhysicsGuard package metadata SHALL point to the public GitHub repository so installed package metadata and release pages preserve the source location.

#### Scenario: Package metadata is inspected
- **WHEN** a user or package index reads PhysicsGuard project metadata
- **THEN** the metadata includes repository and homepage URLs for the public GitHub project
