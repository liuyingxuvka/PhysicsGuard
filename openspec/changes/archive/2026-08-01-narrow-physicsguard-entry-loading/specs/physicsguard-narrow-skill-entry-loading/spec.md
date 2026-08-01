## Purpose

Define a compact and machine-checkable entry boundary for every PhysicsGuard skill so an AI can select one direct native route without eagerly loading unrelated protocols, while retaining full deep-modeling capability on demand.

## ADDED Requirements

### Requirement: Ten independent direct route capsules
Each maintained PhysicsGuard skill SHALL expose one current machine-readable route capsule containing its exact skill id, native route id, native owner id, route role, acceptance conditions, rejection conditions, typed handoffs, minimum inputs, required outputs, conditional references, and bounded claim. The capsule SHALL be target-owned and SHALL NOT introduce a parent or alternate success route.

#### Scenario: Direct satellite request is clear
- **WHEN** a request satisfies one satellite capsule's acceptance conditions and no capsule ambiguity remains
- **THEN** the AI SHALL enter that satellite directly without first invoking `physicsguard-ai-debugging`

#### Scenario: Capsule owner differs from native contract
- **WHEN** a capsule's skill, route, or owner identity differs from the target's current native contract
- **THEN** route selection and author closure SHALL be blocked

### Requirement: Composite debugging is not a universal parent
`physicsguard-ai-debugging` SHALL accept only mixed, cross-route, or genuinely unclear physical-debugging requests and its capsule SHALL hand a clear specialized request to the matching direct skill. It SHALL NOT be a mandatory preflight, wrapper, alias, fallback, or closure owner for the other nine routes.

#### Scenario: Concrete test-file review request
- **WHEN** a request is specifically about file fields, units, timing, testbench identity, or model-binding coverage
- **THEN** `physicsguard-test-file-contract-review` SHALL be selected directly and the AI-debugging route SHALL remain not run

#### Scenario: Several route responsibilities are inseparable
- **WHEN** a debugging request materially spans several route responsibilities and cannot be assigned to one capsule without losing required work
- **THEN** `physicsguard-ai-debugging` MAY coordinate typed handoffs while each satellite retains its own domain judgment and evidence

### Requirement: Entry loading is bounded and conditional
Initial route use SHALL load only the selected skill's metadata, compact `SKILL.md`, and route capsule. The detailed native route protocol, native depth/purpose protocol, and template-pack protocol SHALL be loaded only when their capsule-declared trigger is present. Selection of one skill SHALL NOT authorize loading another skill's prompt or references.

#### Scenario: Ordinary bounded route use
- **WHEN** a selected task does not create or materially deepen a model and does not request template-pack selection or instantiation
- **THEN** neither `native-depth-and-purpose.md` nor `template-pack-routing.md` SHALL be required for initial execution

#### Scenario: Deep model work begins
- **WHEN** the selected route will create, materially revise, or claim closure for a task-local model
- **THEN** the AI SHALL load that selected skill's `native-depth-and-purpose.md` before candidate construction or closure

#### Scenario: Validated template pack is relevant
- **WHEN** target-owned template selection, preview, instantiation, validation, or harvest is requested or required
- **THEN** the AI SHALL load that selected skill's `template-pack-routing.md` and SHALL keep preview distinct from proof

### Requirement: Prompt load graph is fail-closed
The author source SHALL maintain a machine-checkable load graph derived from all ten capsules and current prompt artifacts. The graph SHALL reject eager all-reference loading, undeclared references, missing conditional targets, cross-skill reference loading, broad-route capture of a clear satellite request, and any route whose required deep capability is no longer reachable.

#### Scenario: Entry prompt requires every reference
- **WHEN** a `SKILL.md` makes the route protocol, depth protocol, and template protocol unconditional for every request
- **THEN** the load-graph check SHALL fail with an eager-loading finding

#### Scenario: Compact prompt hides the deep route
- **WHEN** contraction removes the conditional path to six-family depth, frozen prediction, independent holdout, predictive rollout, `model_miss`, or exact terminal boundaries
- **THEN** the load-graph check SHALL fail even if the compact prompt itself is smaller

### Requirement: Consumer entry metadata remains route-specific
Each `agents/openai.yaml` SHALL name its own skill with `$skill-id`, describe only its direct route, and use a default prompt that neither invokes the broad route first nor claims evidence before native checks run.

#### Scenario: Satellite metadata uses broad debugging prompt
- **WHEN** a satellite's UI metadata asks the AI to start from generic PhysicsGuard debugging or omits its `$skill-id`
- **THEN** prompt validation SHALL fail

