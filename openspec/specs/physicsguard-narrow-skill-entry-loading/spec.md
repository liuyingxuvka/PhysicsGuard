# physicsguard-narrow-skill-entry-loading Specification

## Purpose
Keep the always-loaded PhysicsGuard entry small: one `physicsguard` skill whose SKILL.md is a route table, and each route's workflow loaded only when that route is chosen.

## Requirements
### Requirement: One skill entry with a route table
PhysicsGuard SHALL ship exactly one consumer skill, `physicsguard`, whose SKILL.md lists every route with the route file to load.

#### Scenario: A simulation result looks wrong
- **WHEN** an agent is asked to debug an engineering-simulation result
- **THEN** it SHALL choose the `ai-debugging` route in the table and load only `references/routes/ai-debugging.md`

### Requirement: Each route is one file
Each former PhysicsGuard skill SHALL be one file `references/routes/<route>.md` that holds its entry boundary, minimum workflow, required outputs, claim boundary and detailed workflow.

#### Scenario: A route hands off
- **WHEN** a route's entry boundary names another route
- **THEN** the agent SHALL load that route file and SHALL NOT look for a second PhysicsGuard skill

### Requirement: Short description
The skill description SHALL stay at or below 300 characters, say what the skill is for, and name the sibling skill to use instead.

#### Scenario: The description grows
- **WHEN** the description exceeds 300 characters
- **THEN** `tests/test_physicsguard_skill_prompts.py` SHALL fail

### Requirement: Reinstall removes retired skill directories
The installer SHALL replace the installed `physicsguard` copy and remove every directory named in `RETIRED_SKILL_IDS`.

#### Scenario: Reinstall over the old multi-skill layout
- **WHEN** `python scripts/install_physicsguard_skills.py --target <skills directory>` runs where old `physicsguard-*` directories exist
- **THEN** only `physicsguard` SHALL remain of them and `--check` SHALL print `installed skills are current`
