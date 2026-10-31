# physicsguard-narrow-skill-entry-loading Specification

## Purpose
Keep the always-loaded PhysicsGuard entry small: one `physicsguard` skill whose SKILL.md is a route table, and each route's workflow loaded only when that route is chosen.

## Requirements
### Requirement: One skill entry that starts from the model, then a route table
PhysicsGuard SHALL ship exactly one consumer skill, `physicsguard`, whose SKILL.md first section `## Start from the model` reads the existing audit tree (or builds a coarse one) and whose route table then lists every route with the route file to load.

#### Scenario: A simulation result looks wrong
- **WHEN** an agent is asked to debug an engineering-simulation result
- **THEN** it SHALL first `hierarchy describe` the existing audit and name the blocks concerned
- **AND** it SHALL then choose the `ai-debugging` route in the table and load only `references/routes/ai-debugging.md`

### Requirement: Each route is one file
Each former PhysicsGuard skill SHALL be one file `references/routes/<route>.md` that holds its entry boundary, ordered workflow, required outputs and claim boundary.

#### Scenario: A route hands off
- **WHEN** a route's entry boundary names another route
- **THEN** the agent SHALL load that route file and SHALL NOT look for a second PhysicsGuard skill

### Requirement: Clear skill description
The skill description SHALL say what the skill is for, include the agent's own physics or engineering calculations, and name flowguard for software code behavior, including simulation code.

### Requirement: Reinstall removes retired skill directories
The installer SHALL replace the installed `physicsguard` copy and remove every directory named in `RETIRED_SKILL_IDS`.

#### Scenario: Reinstall over the old multi-skill layout
- **WHEN** `python scripts/install_physicsguard_skills.py --target <skills directory>` runs where old `physicsguard-*` directories exist
- **THEN** only `physicsguard` SHALL remain of them and `--check` SHALL print `installed skills are current`

### Requirement: AI debugging preserves four hard boundaries
The selected AI-debugging route SHALL reject one-value coverage of a time-varying parameter, distinguish pointwise evaluation from state-propagating prediction with an exact disjoint future holdout, keep episode hypotheses and revisions task-local without changing PhysicsGuard thresholds/code/library defaults/installed skills, and use only official, user-provided or documented external-tool interfaces.

#### Scenario: The episode proposes changing the audit tool itself
- **WHEN** a diagnosis proposes changing PhysicsGuard thresholds, Guard code, reusable defaults or installed skills
- **THEN** the route SHALL keep that proposal outside the diagnostic episode and retain task-local revisions instead

#### Scenario: The external interface is unavailable
- **WHEN** no official, user-provided or documented tool interface is available
- **THEN** the route SHALL stop at the PhysicsGuard audit and name the missing interface

#### Scenario: Pointwise or one-value evidence is offered as deep prediction
- **WHEN** one value covers a time-varying parameter or a pointwise evaluation is presented as prediction
- **THEN** the route SHALL retain the coverage gap and require state propagation plus an exact disjoint future holdout for a prediction claim

### Requirement: one compact debugging workflow
The AI debugging route SHALL contain one ordered workflow and retain every hard
boundary and YAML header rule.
There SHALL be no second protocol file to load. Every documented CLI command
SHALL exist in the current parser.
