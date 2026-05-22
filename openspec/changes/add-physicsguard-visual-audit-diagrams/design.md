## Context

PhysicsGuard's README and protocols already describe a low-fidelity physical understanding map: visible symptom, subsystem hierarchy, interfaces, SI units, conservation relations, signal mappings, assumptions, residual checks, suspicious blocks, and next refinements. The Codex skill currently tells agents how to build and evaluate those audits, but it does not give the same visual communication contract that LogicGuard and FlowGuard now use.

This change is a skill and documentation upgrade. The existing runtime FlowGuard model remains the owner for schema validation, residual assembly, solver/evaluator modes, hierarchy modes, assumption handling, and diagnostics. No runtime lifecycle or physical module behavior changes are planned.

## Goals / Non-Goals

**Goals:**
- Add a PhysicsGuard diagram intent gate so agents decide what relationship a visual explanation must communicate before drawing it.
- Define PhysicsGuard-owned diagram modes for physical topology, residual localization, observed-signal mapping, assumption boundaries, coarse-to-fine refinement, and candidate-model blueprints.
- Require explicit edge semantics so physical flow, signal mapping, residual checks, assumptions, refinements, and required signals are not collapsed into one generic flowchart.
- Keep diagrams compact, selective, and tied to `top_blocks`, `top_residuals`, `recommended_refinements`, assumptions, and signal mapping confidence when those exist.
- Make clear that diagrams and tables explain the audit path but do not count as validation evidence.
- Sync the installed Codex skill copy after updating the repository skill source.

**Non-Goals:**
- No new CLI command, YAML schema, solver behavior, residual module, physical equation, external-tool adapter, or automatic visual renderer.
- No claim that diagrams reproduce a Simulink, GT-SUITE, Modelica, Amesim, FMI, MATLAB, or commercial model topology.
- No high-fidelity physical modeling, automatic repair, probabilistic confidence, or hidden assumption inference.
- No requirement to show a diagram for tiny answers where it adds no clarity.

## Decisions

### Decision: Reuse the LogicGuard/FlowGuard rule shape, not their graph semantics

PhysicsGuard will follow the same communication pattern: run an intent gate, choose from a domain-specific toolbox, clarify edge meanings, skip trivial cases, and treat diagrams as explanatory only. The toolbox is PhysicsGuard-specific because physical flow, residual localization, signal mapping, and assumption boundaries are different from argument support or behavior-state transitions.

Alternative considered: copy FlowGuard's behavior/state snapshots directly. Rejected because it would blur physical topology and observed-value residual evidence into software workflow semantics.

### Decision: Default to topology plus overlays

For most debugging conversations, the clearest default is a physical topology map with overlays for residuals, assumptions, and next refinement. Formulae remain local labels or companion tables rather than the primary visual.

Alternative considered: show residual equations first. Rejected because users need to see the suspicious block, boundary, and next signal request before detailed algebra is useful.

### Decision: Use Mermaid diagrams or small tables in chat, not generated raster images

The skill guidance should prefer Mermaid and tables because they are inspectable, compact, easy to edit, and suitable for technical audit semantics. Raster images may still be used for public README visuals, but they are not required for routine debugging explanation.

Alternative considered: add an image generation step. Rejected because the skill needs deterministic semantics and should not introduce visual assets into routine model debugging.

### Decision: Keep validation evidence separate

The new guidance will explicitly say that a diagram does not prove audit correctness. Validation still comes from PhysicsGuard CLI reports, FlowGuard checks, pytest, example regressions, version checks, and release evidence.

Alternative considered: allow a complete diagram to count as audit evidence. Rejected because diagrams can omit residual roles, missing signals, stale data, and assumptions.

## Risks / Trade-offs

- Diagram overuse could slow simple conversations -> Mitigated by allowing tiny answers and low-stakes status replies to stay concise.
- Generic flowcharts could hide edge meaning -> Mitigated by requiring a named diagram mode and explicit edge semantics.
- Users might read topology diagrams as commercial-model internals -> Mitigated by boundary language that diagrams show low-fidelity audit topology only.
- Formulas could be under-shown -> Mitigated by requiring local residual labels or companion tables when the residual math is the point of the explanation.
- Installed skill drift could leave agents using old behavior -> Mitigated by syncing the repository skill into the local Codex skills directory and verifying the installed copy.

## Migration Plan

1. Add OpenSpec requirements and tasks for visual audit communication.
2. Update `skill/physicsguard-ai-debugging/SKILL.md` with the diagram intent gate and toolbox.
3. Update protocol and README guidance so public docs match the skill behavior.
4. Sync the installed local skill copy.
5. Bump the minor version and changelog for the user-facing skill/workflow capability.
6. Run FlowGuard checks, focused docs/skill inspections, pytest, CLI regressions, installed-version checks, and release hygiene checks.
7. Commit, tag, push, and publish the new GitHub release.

## Open Questions

- None for the first implementation. Future work could add a deterministic `diagram` CLI/report helper if users want rendered diagrams generated from hierarchy JSON.
