## ADDED Requirements

### Requirement: PhysicsGuard agents choose diagrams through an intent gate
PhysicsGuard agents SHALL decide the relationship a visual explanation must communicate before showing a diagram or table for non-trivial audit, debugging, refinement, or candidate-model blueprint work.

#### Scenario: Non-trivial audit explanation needs a visual
- **WHEN** an agent explains a non-trivial PhysicsGuard audit path, residual localization, signal mapping, assumption boundary, refinement decision, or candidate-model blueprint
- **THEN** the agent identifies the diagram intent before choosing a diagram or table

#### Scenario: Tiny answer does not need a diagram
- **WHEN** a PhysicsGuard response is a tiny status update, direct command answer, or low-stakes explanation where a visual adds no clarity
- **THEN** the agent may answer concisely without a diagram

### Requirement: PhysicsGuard visual modes are domain-specific
PhysicsGuard agents SHALL choose from PhysicsGuard-specific visual modes rather than reusing generic LogicGuard or FlowGuard graph semantics.

#### Scenario: Physical topology is the main relationship
- **WHEN** the agent needs to explain the system boundary, subsystems, interfaces, or physical flow
- **THEN** the agent uses a physical topology map whose edges identify physical flow, energy flow, mass flow, power flow, heat flow, or signal flow as appropriate

#### Scenario: Residual localization is the main relationship
- **WHEN** audit results identify suspicious blocks or residuals
- **THEN** the agent uses a residual localization overlay or table tied to `top_blocks`, `top_residuals`, normalized residuals, and `audit_pass` or `audit_fail` status

#### Scenario: Signal mapping is the main relationship
- **WHEN** external model signals are mapped into PhysicsGuard variables
- **THEN** the agent uses an observed-signal mapping view that shows external signal, PhysicsGuard variable, units, mapping confidence, and review requirement when relevant

#### Scenario: Assumption boundary is the main relationship
- **WHEN** assumptions materially affect the audit interpretation
- **THEN** the agent uses an assumption boundary overlay or table that distinguishes active, proposed, and rejected assumptions and identifies the affected variable, parameter, block, or residual

#### Scenario: Refinement is the main relationship
- **WHEN** the agent recommends the next debugging step
- **THEN** the agent uses a coarse-to-fine refinement path that connects the suspicious block to recommended templates, required variables, required parameters, and rationale

#### Scenario: Candidate model blueprint is the main relationship
- **WHEN** the user asks to build a candidate target model from a PhysicsGuard hierarchy
- **THEN** the agent uses a candidate blueprint view that shows validated low-fidelity blocks, interfaces, units, assumptions, and validation examples before target-model generation

### Requirement: PhysicsGuard diagrams preserve explicit edge semantics
PhysicsGuard agents SHALL make diagram edge meanings clear and SHALL NOT collapse physical flow, mapping, residual checking, assumptions, refinement, and required-signal dependencies into one unlabeled generic flow.

#### Scenario: Diagram includes multiple relationship types
- **WHEN** a diagram contains more than one kind of relationship
- **THEN** the agent labels the relationship types or splits the explanation into a diagram plus table so users can distinguish the meanings

### Requirement: PhysicsGuard diagrams do not replace validation evidence
PhysicsGuard agents SHALL state or preserve the boundary that diagrams and tables explain the audit path but do not count as PhysicsGuard, FlowGuard, pytest, CLI, or release validation evidence.

#### Scenario: Diagram is shown after a report
- **WHEN** the agent shows a diagram based on a PhysicsGuard report
- **THEN** validation claims remain grounded in the actual report output, FlowGuard checks, tests, examples, or release evidence rather than the diagram itself

#### Scenario: Diagram could imply high-fidelity equivalence
- **WHEN** a diagram might be mistaken for a recovered external or commercial model topology
- **THEN** the agent states that the diagram is a low-fidelity PhysicsGuard audit map, not a high-fidelity solver, commercial-tool adapter, or reverse-engineered model
