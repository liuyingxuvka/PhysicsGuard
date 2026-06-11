# PhysicsGuard

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="PhysicsGuard concept hero image" width="100%" />
</p>

<p align="center">
  <strong>Low-fidelity physical understanding, residual audits, and candidate-model blueprints for AI simulation debugging.</strong>
</p>
<!-- README HERO END -->

- **Version:** `v0.8.0`
- **Runtime:** Python 3.11+ with `pydantic`, `numpy`, `scipy`, and `PyYAML`
- **License:** MIT
**Language note:** English comes first; the second half is a full Chinese mirror.

PhysicsGuard is a Python core and Codex skill for AI-guided debugging around physical simulation workflows. It helps an AI agent build a low-fidelity physical understanding map before it tries to debug or generate anything: visible symptom, subsystem hierarchy, interfaces, SI units, conservation relations, signal mappings, assumptions, and residual checks.

From that map, PhysicsGuard can evaluate exported or user-mapped values directly, rank suspicious blocks, expose assumptions, recommend the next signals or parameters to inspect, and produce a candidate-model blueprint. Hierarchy observed reports now also include a `signal_mapping_ledger` and `bug_family_followups`, so each mapped variable can point back to its external signal, unit evidence, confidence/review state, and same-family checks such as sign, gain, unit conversion, or sibling balance issues. The generated model path stays separate: an AI agent may translate checked interfaces, units, assumptions, and block relations into official APIs or user-owned editable templates, then map the candidate outputs back into PhysicsGuard for residual checks.

PhysicsGuard does **not** parse commercial tools, reverse engineer solver formats, replace the original solver, or claim high-fidelity equivalence. It checks mapped values against explicit low-fidelity residual equations and keeps the original engineering model as the source of truth.

## What You Can Build And Check

PhysicsGuard is not just a residual score table. It gives the AI a disciplined way to build physical understanding first, then use that understanding to choose the next debugging or model-building action.

| Goal | Model-first output | What keeps it trustworthy | Boundary |
| --- | --- | --- | --- |
| Understand a simulation failure | A Level 0 physical map: visible symptom, subsystem boundary, expected conservation relation, key signals, SI units, assumptions, and first residuals | The map is written as YAML hierarchy/spec objects and can be inspected before more signals are exported | It is a low-fidelity audit map, not a replacement for the original solver |
| Localize a likely bug | Hierarchy reports with `top_blocks`, `top_residuals`, assumption cards, and `recommended_refinements` | Observed values are substituted directly into explicit residual equations; suspicious blocks are ranked rather than guessed from prose | Block scores are diagnostic heuristics, not proof of the only possible fault |
| Decide what to export next | A targeted signal/parameter request tied to the residual that failed | The report asks for the next useful variables, units, bounds, maps, or parameters instead of asking for the whole external model | Missing data stays explicit; PhysicsGuard should not invent mappings or assumptions |
| Build a candidate model | A blueprint of interfaces, units, assumptions, block relations, examples, and refinement order | Each block can be validated against PhysicsGuard examples, observed data, or conflict cases before larger assembly | Candidate models are new engineering artifacts, not recovered commercial-model copies |
| Keep AI physics honest | Active/proposed/rejected/high-impact Assumption Cards | Assumptions appear in diagnostic JSON and rejected/proposed assumptions are visible but not applied | Assumptions are not free optimization variables |

## Why It Is Worth Trying

- It lets an AI agent build a coarse physical map first instead of trying to recreate an entire external simulation.
- It turns "something is physically wrong" into a localizable chain: symptom -> boundary -> residual -> suspicious block -> next signal or parameter.
- It ranks suspicious blocks and residuals so the next export, signal check, or parameter review is targeted.
- It gives AI agents a visual audit language for topology, residual localization, signal mappings, assumptions, refinement paths, and candidate blueprints.
- It makes assumptions visible through Assumption Cards instead of letting the agent silently invent missing physics.
- It can turn a validated low-fidelity audit hierarchy into a blueprint for a separate candidate model without claiming to recover the original solver.

## What It Is

PhysicsGuard is a transparent audit layer with four pieces:

- YAML system and hierarchy specs;
- low-fidelity residual modules for physics, controls, and engineering sanity checks;
- direct observed-value evaluation for mapped external simulation snapshots;
- hierarchical reports that rank suspicious blocks, show assumption cards, and recommend the next useful refinement.

The original engineering model remains the source of truth. PhysicsGuard is the AI-facing audit lens that helps decide where to look next before exporting more signals, refining a block, or building a candidate model.

## Visual Audit Communication

For non-trivial AI debugging conversations, PhysicsGuard agents should choose a compact Mermaid diagram or table by intent:

- physical topology maps for boundaries, subsystems, interfaces, and mass, energy, heat, power, or signal flow;
- residual localization overlays for `top_blocks`, `top_residuals`, normalized residuals, and pass/fail status;
- observed signal mapping views for external signal names, PhysicsGuard variables, units, confidence, and review requirements;
- assumption boundary overlays for active, proposed, and rejected assumptions and the variables, parameters, blocks, or residuals they affect;
- coarse-to-fine refinement paths for suspicious blocks, deeper templates, required variables, required parameters, and rationale;
- candidate-model blueprints for validated low-fidelity blocks, interfaces, units, assumptions, examples, and generation boundaries.

The visual is an explanation layer, not validation evidence. PhysicsGuard still relies on explicit residual reports, FlowGuard checks, pytest, CLI regressions, and examples for release or correctness claims. Diagrams show low-fidelity audit topology only; they are not recovered commercial-model internals.

## Portable YAML Files

Committed PhysicsGuard YAML audits, hierarchy templates, observed snapshots, and model-blueprint files start with a short comment header. The header states the file purpose, points back to `https://github.com/liuyingxuvka/PhysicsGuard`, gives a likely CLI entry point, and repeats the low-fidelity SI-unit safety boundary. This keeps copied model files understandable even on machines that do not have the Codex skill installed.

## Model-Code Traceability

PhysicsGuard keeps a FlowGuard model-code ledger at `.flowguard/model_code_ledger.yaml`. It maps core model blocks to source symbols, tests, examples, boundaries, stale-evidence conditions, and validation commands so future AI agents can find the right code before changing model-backed behavior. The ledger is navigation and evidence indexing; runtime claims still require FlowGuard checks, pytest, and relevant CLI regressions.

## AI Workflow Governance

PhysicsGuard keeps a project workflow record at `.physicsguard/project.yaml` and a module/equation ledger at `.physicsguard/module_equation_ledger.yaml`. These files help an AI agent answer four practical questions before it makes a debugging claim:

- Which PhysicsGuard repository, package version, and skill routes am I using?
- What is the visible physical symptom, system boundary, unit basis, first audit level, and stop condition?
- Which external signals were mapped into PhysicsGuard variables, and which mappings still need review?
- Which low-fidelity module family, equation summary, tests, examples, and closure checks support this claim?

The workflow commands are:

```powershell
python -m physicsguard.cli project audit --pretty
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
python -m physicsguard.cli project closure templates/project_closure_plan.yaml --pretty
python scripts/check_module_equation_ledger.py --json
```

These checks do not prove the external model is correct. They keep the AI grounded in the current PhysicsGuard version, explicit physical boundaries, reviewable signal mappings, and fresh closure evidence.

## Test File Contract Route

For projects with concrete testbench data files, PhysicsGuard includes an
optional file-contract route. It is a sibling workflow, not a requirement for
model-only audits.

The route creates one resolved contract per test data file:

```text
test data file -> DataFileManifest -> TestFileContract -> coverage/model-binding check
```

The manifest records script-generated file facts: hash, format, fields, row
count, time range, sample rate, continuity, field types, units, and extractor
identity. The contract then binds those fields to a testbench profile, model
binding, parameter catalog, role matrix, and evidence-backed mapping edges.

Use:

```powershell
python -m physicsguard.cli testfile manifest DATA.csv --profile PROFILE.yaml --out MANIFEST.yaml
python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
python -m physicsguard.cli coverage check CONTRACT.yaml --pretty
python -m physicsguard.cli testfile project-check INDEX.yaml --pretty
python -m physicsguard.cli testfile diff OLD_CONTRACT.yaml NEW_CONTRACT.yaml --pretty
```

AI-proposed field bindings must include evidence such as field names, labels,
units, P&ID or testbench topology, code references, formulas, datasheets, or
human-provided mapping records. Unknown field meaning, unknown targets, or model
coverage gaps must remain explicit instead of being marked covered. A passing
contract proves file coverage discipline only; physical correctness still needs
residual reports and closure evidence.

## Model-Dataset Validation And Reuse

After a test-file contract passes, PhysicsGuard can validate the low-fidelity
model against the contracted dataset boundary:

```text
contract pass -> direct validation -> optional bounded calibration -> holdout validation -> confidence feedback
```

Use:

```powershell
python -m physicsguard.cli dataset logical-check DATASET.yaml --pretty
python -m physicsguard.cli dataset relation-check RELATIONS.yaml --pretty
python -m physicsguard.cli validation run VALIDATION_PLAN.yaml --pretty
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

The first calibration backend is deliberately conservative: no Adam or SPSA in
this version. `coarse_grid_then_least_squares` only chooses a small bounded
starting point before least squares. Calibration may adjust only explicit
bounded parameters, never observed values, and `optimization_success` is
reported separately from validation pass. Model-library entries store model and
validation-report references; they do not store large raw datasets or prove
validity outside the checked boundary.

## Project Evidence Registry And Map

For multi-file projects, PhysicsGuard can keep a project-level evidence
registry. It is the local map that tells another AI agent what project this is,
where the important files are, what basic project facts are known, which facts
or test fields bind to model targets, which items are explicitly exempted from
model binding, and which gaps still need work.

Use:

```powershell
python -m physicsguard.cli evidence check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence scan PROJECT_OR_FOLDER --registry EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence bundle-check EVIDENCE.yaml BUNDLE_ID --pretty
python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
```

The registry stores `project_profile` fields such as project name, objective,
run period, locations, and source references. If those basics are unknown, AI
should record an unknown reason instead of inventing values; gap-check keeps the
missing profile item visible. It also stores file artifacts, engineering facts,
evidence bindings, binding expectations, context cards, and evidence bundles.

The Project Evidence Map is an onboarding/navigation report, not validation
proof. Validation and reuse claims still require test-file contracts, residual
validation reports, and model-library checks. Blocking project evidence gaps
prevent validation pass or validated reuse claims; review and optional gaps must
remain visible in the claim boundary.

## Project Closure Gate

For final project-level claims, run project closure after the route-specific
checks have current evidence:

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

The closure plan declares the intended claim scope, project evidence registry,
evidence bundles, test contracts, validation plans, model-library indexes, and
optional hierarchy audit pairs. The report returns `passed`, `partial`,
`downgraded`, or `blocked` plus safe claim wording, unsafe claim boundaries,
skipped checks, and next actions.

The evidence map remains navigation only. A successful map cannot prove project
readiness if gap-check, test-file contract, validation, model-library, or
required closure evidence is missing or blocked.

## Database Catalog And Cross-Project Map

For a database or folder that contains many PhysicsGuard projects, PhysicsGuard
now treats the database as an explicit local root. The root has a policy,
catalog, history log, maintenance report, model-template index, and AI handoff
files. It is not a hidden global database, and it does not copy raw datasets.

Create the database root only with explicit intent:

```powershell
python -m physicsguard.cli database init DATABASE_ROOT --database-id local_database --pretty
python -m physicsguard.cli database init DATABASE_ROOT --database-id local_database --apply --pretty
```

Add projects through an intake plan, then admit them after review:

```powershell
python -m physicsguard.cli database intake-plan DATABASE_ROOT PROJECT_ROOT --requested-state candidate --pretty
python -m physicsguard.cli database admit DATABASE_PROJECT_INTAKE_PLAN.yaml --apply --pretty
```

Use:

```powershell
python -m physicsguard.cli database policy-check DATABASE_ROOT/database_policy.yaml --pretty
python -m physicsguard.cli database template-index-check DATABASE_ROOT/model_template_index.yaml --pretty
python -m physicsguard.cli database audit DATABASE_ROOT --pretty
python -m physicsguard.cli database render-handoff DATABASE_ROOT --apply --pretty
python -m physicsguard.cli database check CATALOG.yaml --pretty
python -m physicsguard.cli database scan ROOT --catalog CATALOG.yaml --pretty
python -m physicsguard.cli database refresh CATALOG.yaml --pretty
python -m physicsguard.cli database gap-check CATALOG.yaml --pretty
python -m physicsguard.cli database map CATALOG.yaml --pretty
python -m physicsguard.cli database query CATALOG.yaml --quantity pump.flow_readback --pretty
python -m physicsguard.cli database archive CATALOG.yaml PROJECT_ID --reason "reason" --archive-state archived --apply --pretty
```

Database maps and queries are navigation outputs. They can find related
projects, historical tests, reusable model candidates, active/inactive
lifecycle states, and missing maintenance work, but they do not prove direct
comparability. Broad cross-project claims still require project evidence maps,
validation reports, model-library checks, project closure, and explicit
comparison scope.

## The Core Contract

PhysicsGuard is strongest when the boundary is explicit:

| Input | Check | Output |
| --- | --- | --- |
| mapped observed values from an external model | residual equations, assumptions, bounds, units, and hierarchy rollups | suspicious blocks, residual diagnostics, assumptions, and next signals to inspect |
| target model-building goal | low-fidelity hierarchy, interfaces, units, assumptions, and validation examples | candidate-model blueprint and refinement plan |

That boundary matters because PhysicsGuard's result is a scoped debugging signal, not a replacement for the original model.

## What It Can Help Diagnose

- unit and scale mistakes such as bar vs Pa, rpm vs rad/s, g/s vs kg/s;
- sign reversals in feedback, force, torque, pressure, flow, current, or voltage;
- broken power, heat, mass, species, or electrical-bus balances;
- bad signal mappings between external models and audit variables;
- physically impossible pressure, flow, current, voltage, temperature, or power combinations;
- map-axis misuse, wrong interpolation inputs, or unsafe extrapolation assumptions;
- inconsistent controller, actuator, sensor, saturation, clamp, delay, or sample-and-hold logic;
- scaling errors in pumps, compressors, heat exchangers, motors, inverters, fuel-cell stacks, electrolyzers, batteries, drivetrains, engines, radiators, and thermal-management loops.

## What It Is Not

PhysicsGuard is not a GT-SUITE, Simulink, Simscape, Modelica, Amesim, FMI, CSV, MATLAB, PyBaMM, or OpenFCST adapter. It does not claim equivalence with commercial solver internals. It does not perform automatic repair, CFD, 1D gas dynamics, high-fidelity electrochemistry, detailed combustion, detailed thermal-fluid simulation, or natural-language report generation.

Generated target models should be treated as candidate engineering models, not recovered copies of existing commercial models.

## Core Audit Workflow

1. Run `python -m physicsguard.cli project audit --pretty` so the AI knows the active PhysicsGuard repository, package version, skill routes, and local adoption record.
2. Complete or review a model-understanding preflight: visible failure, physical boundary, unit basis, subsystem blocks, known assumptions, uncertain mappings, and stop conditions.
3. Build a coarse Level 0 audit with simple balances, signal relations, units, and assumptions.
4. Map external simulation results into `ObservedValuesSpec` and review the external-model intake before making fault-localization claims.
5. Run direct hierarchical evaluation:

```powershell
python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
```

6. Inspect `top_blocks`, `top_residuals`, assumptions, `signal_mapping_ledger`, `bug_family_followups`, and `recommended_refinements`.
7. Export only the next variables or parameters that the report actually asks for.
8. Refine the suspicious block rather than modeling the entire external system.
9. Before a final localization claim, run the closure helper or record why closure is partial, downgraded, blocked, stale, or skipped.
10. Repeat until the issue is localized to a subsystem, component, signal chain, map, parameter, unit conversion, or boundary condition.

Use compare mode only when you intentionally want a solved low-fidelity reference:

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

## Candidate Model-Building Workflow

1. Define the target system and the minimum useful fidelity for each block.
2. Build the lowest-fidelity PhysicsGuard hierarchy first: balances, interfaces, units, simple components, and explicit assumptions.
3. Validate each block with PhysicsGuard examples, observed data, or conflict tests.
4. Refine one block at a time until the blueprint is detailed enough.
5. Generate a separate target model only through official APIs, documented exchange formats, or user-owned editable templates.
6. Run the generated candidate model and map its outputs back into PhysicsGuard.
7. Use residuals to decide whether to refine, reconnect, or correct the generated block.
8. Assemble larger subsystems only after their child blocks pass the relevant checks.

## Assumption Cards

PhysicsGuard uses explicit Assumption Cards. Assumptions are not silent defaults:

- active assumptions appear in diagnostic JSON;
- proposed and rejected assumptions are visible but not applied;
- high-impact assumptions produce warnings;
- assumptions are not free optimization variables;
- AI agents should ask for missing assumptions instead of inventing them.

## Quick Start

```powershell
python -m pip install -e .[test]
python -m pytest
```

Run a simple system:

```powershell
python -m physicsguard.cli run examples/dummy_system.yaml --pretty
```

Run an observed debugging hierarchy:

```powershell
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml examples/hierarchical/observed_debugging/pitch_feedback_observed_fault.yaml --pretty
```

That example represents a mapped controller feedback signal. The fault case has a reversed sign; PhysicsGuard ranks `pitch_rate_feedback` as the top suspicious block, emits a signal-mapping ledger for the mapped variables, and recommends reviewing the actual gain, sign convention, mapping confidence, unit conversion, and related signal-chain mappings.

## Main CLI Modes

```powershell
python -m physicsguard.cli run SYSTEM.yaml --pretty
python -m physicsguard.cli evaluate SYSTEM.yaml OBSERVED.yaml --pretty
python -m physicsguard.cli compare SYSTEM.yaml OBSERVED.yaml --pretty

python -m physicsguard.cli hierarchy run HIERARCHY.yaml --pretty
python -m physicsguard.cli hierarchy inspect HIERARCHY.yaml --pretty
python -m physicsguard.cli hierarchy plan HIERARCHY.yaml --pretty
python -m physicsguard.cli hierarchy evaluate HIERARCHY.yaml OBSERVED.yaml --pretty
python -m physicsguard.cli hierarchy compare HIERARCHY.yaml OBSERVED.yaml --pretty

python -m physicsguard.cli assumptions inspect SYSTEM.yaml --pretty

python -m physicsguard.cli project audit --pretty
python -m physicsguard.cli project adopt --pretty
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
```

## Install The Codex Skill

Ask a Codex-compatible agent:

```text
Please install the PhysicsGuard Codex skill from https://github.com/liuyingxuvka/PhysicsGuard.
The skill folder is skill/physicsguard-ai-debugging.
```

Manual local copy:

```powershell
Copy-Item -Recurse skill\physicsguard-ai-debugging $env:USERPROFILE\.codex\skills\physicsguard-ai-debugging
Copy-Item -Recurse skill\physicsguard-project-adoption $env:USERPROFILE\.codex\skills\physicsguard-project-adoption
Copy-Item -Recurse skill\physicsguard-model-understanding-preflight $env:USERPROFILE\.codex\skills\physicsguard-model-understanding-preflight
Copy-Item -Recurse skill\physicsguard-test-file-contract-review $env:USERPROFILE\.codex\skills\physicsguard-test-file-contract-review
Copy-Item -Recurse skill\physicsguard-project-evidence-registry $env:USERPROFILE\.codex\skills\physicsguard-project-evidence-registry
Copy-Item -Recurse skill\physicsguard-model-dataset-validation $env:USERPROFILE\.codex\skills\physicsguard-model-dataset-validation
Copy-Item -Recurse skill\physicsguard-database-catalog $env:USERPROFILE\.codex\skills\physicsguard-database-catalog
Copy-Item -Recurse skill\physicsguard-database-adoption $env:USERPROFILE\.codex\skills\physicsguard-database-adoption
Copy-Item -Recurse skill\physicsguard-database-project-intake $env:USERPROFILE\.codex\skills\physicsguard-database-project-intake
Copy-Item -Recurse skill\physicsguard-database-maintenance $env:USERPROFILE\.codex\skills\physicsguard-database-maintenance
Copy-Item -Recurse skill\physicsguard-model-library $env:USERPROFILE\.codex\skills\physicsguard-model-library
Copy-Item -Recurse skill\physicsguard-signal-mapping-review $env:USERPROFILE\.codex\skills\physicsguard-signal-mapping-review
Copy-Item -Recurse skill\physicsguard-audit-closure $env:USERPROFILE\.codex\skills\physicsguard-audit-closure
Copy-Item -Recurse skill\physicsguard-candidate-model-blueprint $env:USERPROFILE\.codex\skills\physicsguard-candidate-model-blueprint
```

After reload, use requests such as:

```text
Use PhysicsGuard to audit this simulation snapshot and tell me which subsystem is suspicious.
```

```text
Use PhysicsGuard to design a low-fidelity blueprint for this coolant loop, validate each block, then generate a candidate Simulink model with MATLAB scripting.
```

## Library Coverage

PhysicsGuard `v0.8.0` includes low-fidelity audit relations for:

- aggregate power, heat, mass, species, and electrical-bus balances;
- control error, PID algebraic checks, PID step checks, saturation, hysteresis, thresholds, delay, sample-and-hold, actuator/sensor relations;
- thermodynamic conversion, ideal-gas density, humidity, heat exchanger, radiation, ambient heat loss, compressor sanity checks, rotating-machine affinity;
- component-level motor, inverter, DC/DC converter, compressor, pump, radiator, humidifier, intercooler, engine, fuel-cell stack, electrolyzer stack, and map checks;
- engineering components for fluid networks, thermal management, electrochemical BOP, battery/HV, drivetrain/vehicle, engine/aftertreatment, and control/sensor/actuator checks.

All modules are low-fidelity audit relations. They are intended to expose obvious mismatch, not to simulate full hardware or commercial solver behavior.

## Documentation Map

- [AI-guided debugging protocol](docs/ai_guided_debugging_protocol.md)
- [Hierarchical audit workflow](docs/hierarchical_audit_workflow.md)
- [Hierarchical YAML reference](docs/hierarchical_yaml_reference.md)
- [Assumption cards](docs/assumption_cards.md)
- [Bug playbooks](docs/bug_playbooks.md)
- [Domain starter packs](docs/domain_starter_packs.md)
- [Module spec template](docs/module_spec_template.md)
- [Model-understanding preflight](docs/model_understanding_preflight.md)
- [External-model intake](docs/external_model_intake.md)
- [Module equation ledger](docs/module_equation_ledger.md)
- [Model-code traceability](docs/model_code_traceability.md)
- [Database lifecycle and catalog](docs/database_catalog.md)

## Repository Map

```text
src/physicsguard/                 Python package
tests/                            Test suite
examples/                         YAML examples and hierarchy templates
docs/                             Workflow and schema documentation
.flowguard/                       FlowGuard lifecycle models and traceability ledger
.physicsguard/                    PhysicsGuard project record and module/equation ledger
scripts/                          Repository maintenance scripts
skill/                            Local Codex skill sources
assets/readme-hero/               README hero image assets
```

## Public Boundary

This repository intentionally excludes local private data, local knowledge-base history, generated MATLAB/Simulink copied-model artifacts, and machine-specific outputs. Simulink-related material in this repository is workflow guidance or local experiment scaffolding, not a bundled adapter or redistributed commercial model.

## License

MIT License. See [LICENSE](LICENSE).

---

# PhysicsGuard 中文说明

- **版本：** `v0.8.0`
- **运行环境：** Python 3.11+，依赖 `pydantic`、`numpy`、`scipy`、`PyYAML`
- **许可证：** MIT

PhysicsGuard 是一个 Python 核心库和 Codex skill，用于 AI 辅助物理仿真调试。它帮助 AI agent 在调试或生成模型之前，先搭出一个低保真的物理理解图：可见故障、子系统层级、接口、SI 单位、守恒关系、信号映射、假设和 residual 检查。

基于这张图，PhysicsGuard 可以直接检查导出或用户映射好的 observed values，排序可疑 block，暴露 assumption，推荐下一步应该查看的信号或参数，并产出候选模型蓝图。层级 observed 报告现在还会包含 `signal_mapping_ledger` 和 `bug_family_followups`，让每个映射变量指回外部信号、单位证据、置信度/复核状态，以及同类问题追查方向，比如符号、增益、单位转换或相邻平衡项。模型生成路径保持独立：AI agent 可以把已检查的接口、单位、假设和 block 关系，通过官方 API 或用户自己可编辑的模板翻译成独立候选模型，再把候选模型输出映射回 PhysicsGuard 做 residual 检查。

PhysicsGuard **不会**解析商业工具，**不会**逆向求解器格式，**不会**替代原始求解器，也**不会**声称高保真等价。它只把映射好的数值放进显式低保真残差方程里检查，并把原始工程模型保留为真实来源。

## 它能搭出并检查什么

PhysicsGuard 的输出不是一张孤立的 residual 分数表，而是一条受约束的 AI 工作路径：先建立物理理解，再用这个理解选择下一步调试或模型搭建动作。

| 目标 | 模型先行输出 | 什么让它可信 | 边界 |
| --- | --- | --- | --- |
| 理解一个仿真故障 | Level 0 物理图：可见 symptom、子系统边界、预期守恒关系、关键信号、SI 单位、assumption、第一批 residual | 这张图写成可检查的 YAML hierarchy/spec object，可以在继续导出信号前先被审阅 | 它是低保真审计图，不是原始求解器替代品 |
| 定位可疑物理或信号错误 | 带有 `top_blocks`、`top_residuals`、assumption cards 和 `recommended_refinements` 的 hierarchy report | observed values 被直接代入显式 residual equation；可疑 block 是按残差排序，不是靠自然语言猜 | block score 是诊断启发式，不证明唯一故障原因 |
| 决定下一批导出什么 | 与失败 residual 绑定的信号/参数请求 | 报告要求下一批有用变量、单位、bounds、maps 或参数，而不是要求整个外部模型 | 缺失数据保持显式；PhysicsGuard 不应该发明 mapping 或 assumption |
| 搭建候选模型 | interface、unit、assumption、block relation、example、refinement order 蓝图 | 每个 block 可以先用 PhysicsGuard example、observed data 或 conflict case 验证，再组装更大系统 | 候选模型是新的工程 artifact，不是还原商业模型 |
| 约束 AI 的物理假设 | active/proposed/rejected/high-impact Assumption Cards | assumption 出现在 diagnostic JSON；rejected/proposed assumption 可见但不被应用 | assumption 不是自由 optimization variable |

## 为什么值得一试

- 它让 AI agent 先搭粗粒度物理图，而不是一上来就试图重建整个外部仿真。
- 它把“物理上不对劲”拆成可定位链条：symptom -> boundary -> residual -> suspicious block -> 下一批信号或参数。
- 它会排序可疑 block 和 residual，让下一次导出信号、检查映射或审参数更有目标。
- 它给 AI agent 一套可视化审计语言，用来表达拓扑、残差定位、信号映射、假设、refinement 路径和候选模型蓝图。
- 它用 Assumption Cards 暴露假设，避免 agent 默默补物理假设。
- 它可以把验证过的低保真审计 hierarchy 变成独立候选模型蓝图，同时不声称还原原始求解器。

## 它是什么

PhysicsGuard 是一个透明审计层，包含四个部分：

- YAML system 和 hierarchy spec；
- 低保真物理、控制和工程 sanity-check 残差模块；
- 对外部仿真快照的 observed-value evaluation；
- 可以排序可疑 block、显示 assumption cards 并推荐下一步 refinement 的分层报告。

原始复杂工程模型仍然是真实来源。PhysicsGuard 是面向 AI 的审计视角，用来在继续导出信号、细化 block 或搭建候选模型之前判断下一步应该看哪里。

## 可视化审计沟通

在非平凡的 AI 调试对话里，PhysicsGuard agent 应该按意图选择一张紧凑 Mermaid 图或一个小表：

- 物理拓扑图：展示边界、子系统、接口，以及 mass、energy、heat、power 或 signal flow；
- residual localization overlay：展示 `top_blocks`、`top_residuals`、归一化 residual 和 pass/fail 状态；
- observed signal mapping view：展示外部信号名、PhysicsGuard 变量、单位、confidence 和是否需要 review；
- assumption boundary overlay：展示 active、proposed、rejected assumption 影响了哪些变量、参数、block 或 residual；
- coarse-to-fine refinement path：展示可疑 block、下一层模板、required variables、required parameters 和 rationale；
- candidate-model blueprint：展示已验证的低保真 block、接口、单位、assumption、examples 和生成边界。

这类图只是解释层，不是验证证据。PhysicsGuard 的正确性和发布结论仍然依赖显式 residual report、FlowGuard checks、pytest、CLI regressions 和 examples。图里展示的是低保真审计拓扑，不是商业模型内部结构的还原。

## 可携带 YAML 文件

仓库里保留的 PhysicsGuard YAML 审计、hierarchy 模板、observed snapshot 和候选模型蓝图文件，开头都会有一段很短的注释头。这个头会说明该文件的用途，指向 `https://github.com/liuyingxuvka/PhysicsGuard`，给出可能的 CLI 入口，并重复低保真、SI 单位和安全边界。这样文件被复制到没有安装 Codex skill 的机器上时，也能快速看懂它是什么、从哪里来、应该怎么用。

## AI 工作流治理

PhysicsGuard 现在会保留项目工作流记录 `.physicsguard/project.yaml`，以及模块/方程台账 `.physicsguard/module_equation_ledger.yaml`。这些文件帮助 AI agent 在下调试结论前先回答四个问题：

- 我正在用哪个 PhysicsGuard 仓库、包版本和 skill 路线？
- 可见物理症状、系统边界、单位基础、第一层审计和停止条件是什么？
- 哪些外部信号被映射到了 PhysicsGuard 变量，哪些 mapping 还需要 review？
- 这个结论依赖哪个低保真模块族、方程摘要、测试、示例和 closure 证据？

常用治理命令：

```powershell
python -m physicsguard.cli project audit --pretty
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
python -m physicsguard.cli project closure templates/project_closure_plan.yaml --pretty
python scripts/check_module_equation_ledger.py --json
```

这些检查不证明外部模型正确。它们的作用是让 AI 站在当前 PhysicsGuard 版本、明确物理边界、可复核信号映射和新鲜 closure 证据上说话。

## 测试文件合同路线

对于带有具体测试台数据文件的项目，PhysicsGuard 现在有一条可选的测试文件合同路线。它是一条平行工作流，不是普通模型审计的必选项。

这条路线的核心是每个测试数据文件都有一个 resolved contract：

```text
测试数据文件 -> DataFileManifest -> TestFileContract -> coverage/model-binding check
```

Manifest 由脚本生成，记录文件 hash、格式、字段、行数、时间范围、采样率、连续性、字段类型、单位和 extractor 身份。Contract 再把这些字段绑定到测试台 profile、模型 binding、参数 catalog、role matrix 和带证据的 mapping edges。

常用命令：

```powershell
python -m physicsguard.cli testfile manifest DATA.csv --profile PROFILE.yaml --out MANIFEST.yaml
python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
python -m physicsguard.cli coverage check CONTRACT.yaml --pretty
python -m physicsguard.cli testfile project-check INDEX.yaml --pretty
python -m physicsguard.cli testfile diff OLD_CONTRACT.yaml NEW_CONTRACT.yaml --pretty
```

AI 提出的字段绑定必须留下证据，例如字段名、标签、单位、P&ID 或测试台拓扑、代码引用、公式、datasheet，或者人类提供的映射记录。如果 AI 不知道字段含义、目标变量，或者当前模型还不能覆盖这个字段，就必须显式标成 review-required、模型缺口或合同失败，不能假装 covered。合同通过只证明字段覆盖纪律，不证明物理正确；物理结论仍然要靠 residual report 和 closure 证据。

## 模型-数据校验和复用

测试文件合同通过之后，PhysicsGuard 可以继续检查低保真模型和这批测试数据是否一致：

```text
合同通过 -> 直接不拟合校验 -> 可选有界校准 -> holdout 再校验 -> 置信度反馈
```

常用命令：

```powershell
python -m physicsguard.cli dataset logical-check DATASET.yaml --pretty
python -m physicsguard.cli dataset relation-check RELATIONS.yaml --pretty
python -m physicsguard.cli validation run VALIDATION_PLAN.yaml --pretty
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

第一版校准刻意保守：不实现 Adam 或 SPSA。`coarse_grid_then_least_squares` 只是在边界内选一个很粗的初始点，再交给 least squares。校准只允许显式列出的有界参数被小规模调整，不能修改观测值。`optimization_success` 只表示优化器收敛，不等于 validation pass。模型复用库只保存模型和验证报告引用，不保存大型原始数据，也不证明模型在未验证边界外有效。

## 项目证据登记和项目地图

对于多文件项目，PhysicsGuard 可以维护一个项目级证据登记表。它像本地地图一样告诉新的 AI agent：这是什么项目，重要文件在哪里，项目基础信息是否已知，哪些事实或测试字段已经绑定到模型目标，哪些字段明确不需要绑定，以及还有哪些缺口要维护。

常用命令：

```powershell
python -m physicsguard.cli evidence check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence scan PROJECT_OR_FOLDER --registry EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence gap-check EVIDENCE.yaml --pretty
python -m physicsguard.cli evidence bundle-check EVIDENCE.yaml BUNDLE_ID --pretty
python -m physicsguard.cli evidence map EVIDENCE.yaml --pretty
```

登记表里的 `project_profile` 用来记录项目名称、目标、运行时间、地点和来源引用。如果这些基础信息暂时不知道，AI 应该写明 unknown reason，而不是编一个值；gap-check 会把这个缺口继续暴露出来。登记表还记录文件 artifact、工程事实、证据绑定、绑定期望、context card 和 evidence bundle。

Project Evidence Map 是给 AI 入场和导航用的报告，不是验证证明。验证和复用结论仍然需要测试文件合同、残差校验报告和模型库检查。blocking 的项目证据缺口会阻止 validation pass 或 validated reuse；review/optional 缺口必须继续写在结论边界里。

## 项目最终收口门禁

如果要下项目级最终结论，先跑 route 自己的检查，再跑项目收口：

```powershell
python -m physicsguard.cli project closure PROJECT_CLOSURE_PLAN.yaml --pretty
```

closure plan 会声明这次要支持哪种结论、项目证据登记表、evidence bundle、测试文件合同、validation plan、模型库索引，以及可选的 hierarchy audit。closure report 会给出 `passed`、`partial`、`downgraded` 或 `blocked`，同时写清楚 safe claim、unsafe claim boundary、跳过的检查和下一步动作。

Evidence map 仍然只是导航。就算 map 生成成功，只要 gap-check、测试文件合同、validation、模型库或必需 closure 证据缺失/失败，也不能说项目已经 ready。

## 数据库目录和跨项目地图

如果一个文件夹或数据库里包含很多 PhysicsGuard 项目，PhysicsGuard 现在把数据库当成一个显式的本地根目录。这个根目录里有 policy、catalog、history log、maintenance report、model-template index，以及给其他 AI 看的 README/status 交接文件。它不是隐藏的全局数据库，也不会复制原始测试数据。

只有明确要建库时才初始化数据库：

```powershell
python -m physicsguard.cli database init DATABASE_ROOT --database-id local_database --pretty
python -m physicsguard.cli database init DATABASE_ROOT --database-id local_database --apply --pretty
```

项目进入数据库要先生成 intake plan，再审核后写入：

```powershell
python -m physicsguard.cli database intake-plan DATABASE_ROOT PROJECT_ROOT --requested-state candidate --pretty
python -m physicsguard.cli database admit DATABASE_PROJECT_INTAKE_PLAN.yaml --apply --pretty
```

常用命令：

```powershell
python -m physicsguard.cli database policy-check DATABASE_ROOT/database_policy.yaml --pretty
python -m physicsguard.cli database template-index-check DATABASE_ROOT/model_template_index.yaml --pretty
python -m physicsguard.cli database audit DATABASE_ROOT --pretty
python -m physicsguard.cli database render-handoff DATABASE_ROOT --apply --pretty
python -m physicsguard.cli database check CATALOG.yaml --pretty
python -m physicsguard.cli database scan ROOT --catalog CATALOG.yaml --pretty
python -m physicsguard.cli database refresh CATALOG.yaml --pretty
python -m physicsguard.cli database gap-check CATALOG.yaml --pretty
python -m physicsguard.cli database map CATALOG.yaml --pretty
python -m physicsguard.cli database query CATALOG.yaml --quantity pump.flow_readback --pretty
python -m physicsguard.cli database archive CATALOG.yaml PROJECT_ID --reason "reason" --archive-state archived --apply --pretty
```

数据库地图和查询结果只是导航输出。它可以帮助 AI 找到相关项目、历史测试、可复用模型候选、active/inactive 生命周期状态和缺少维护的地方，但它不能单独证明两个项目可以直接比较。跨项目结论仍然要回到项目证据地图、验证报告、模型库检查、项目收口和明确的比较范围。

## 核心合同

PhysicsGuard 最适合边界明确的场景：

| 输入 | 检查 | 输出 |
| --- | --- | --- |
| 外部模型映射出的 observed values | residual equation、assumption、bounds、units、hierarchy rollup | 可疑 block、residual diagnostic、assumption、下一批要看的信号 |
| 目标模型搭建需求 | 低保真 hierarchy、接口、单位、假设和验证例子 | 候选模型蓝图和 refinement plan |

这个边界很重要：PhysicsGuard 的结果是有范围的调试信号，不是原始模型的替代品。

## 它可以帮助诊断什么

- 单位和尺度错误，例如 bar vs Pa、rpm vs rad/s、g/s vs kg/s；
- feedback、force、torque、pressure、flow、current、voltage 方向反了；
- power、heat、mass、species、电气母线平衡断裂；
- 外部模型信号和审计变量之间映射错误；
- pressure、flow、current、voltage、temperature、power 组合物理上不可能；
- map 轴使用错误、插值输入错误或外推假设不安全；
- controller、actuator、sensor、saturation、clamp、delay、sample-and-hold 逻辑不一致；
- pump、compressor、heat exchanger、motor、inverter、fuel-cell stack、electrolyzer、battery、drivetrain、engine、radiator、thermal-management loop 缩放错误。

## 它不是什么

PhysicsGuard 不是 GT-SUITE、Simulink、Simscape、Modelica、Amesim、FMI、CSV、MATLAB、PyBaMM 或 OpenFCST adapter。它不声称等价于商业求解器内部逻辑，不做自动修复、CFD、一维气体动力学、高保真电化学、详细燃烧、详细热流体仿真或自然语言报告生成。

生成出来的目标模型应该被视为候选工程模型，而不是现有商业模型的还原。

## 核心审计流程

1. 先运行 `python -m physicsguard.cli project audit --pretty`，让 AI 知道当前 PhysicsGuard 仓库、包版本、skill 路线和本地 adoption 记录。
2. 完成或 review model-understanding preflight：可见故障、物理边界、单位基础、子系统 blocks、已知假设、不确定映射和停止条件。
3. 建一个粗粒度 Level 0 审计，只包含简单守恒、信号关系、单位和假设。
4. 把外部仿真结果映射成 `ObservedValuesSpec`，并在下故障定位结论前 review external-model intake。
5. 运行直接分层评估：

```powershell
python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
```

6. 查看 `top_blocks`、`top_residuals`、assumptions、`signal_mapping_ledger`、`bug_family_followups` 和 `recommended_refinements`。
7. 只导出报告真正要求的下一批变量或参数。
8. 只细化最可疑 block，而不是建模整个外部系统。
9. 在最终定位结论前运行 closure helper，或者记录为什么 closure 只能是 partial、downgraded、blocked、stale 或 skipped。
10. 重复，直到问题收敛到子系统、组件、信号链、map、参数、单位转换或边界条件。

只有当你确实需要一个低保真参考解时，才使用 compare mode：

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

## 候选模型搭建流程

1. 定义目标系统，以及每个 block 最低需要达到的 fidelity。
2. 先建最低保真 PhysicsGuard hierarchy：守恒、接口、单位、简单组件、显式假设。
3. 用 PhysicsGuard 示例、observed data 或 conflict tests 验证每个 block。
4. 一次只细化一个 block，直到蓝图足够详细。
5. 只通过官方 API、文档化交换格式或用户自有可编辑模板生成独立目标模型。
6. 运行生成的候选模型，把输出重新映射回 PhysicsGuard。
7. 用残差决定是细化、重连还是修正生成的 block。
8. 只有 child block 通过相关检查后，才组装更大的 subsystem。

## 假设卡片

PhysicsGuard 使用显式 Assumption Cards。假设不是静默默认值：

- active assumptions 会出现在 diagnostic JSON；
- proposed / rejected assumptions 可见但不被应用；
- high-impact assumption 会产生 warning；
- assumption 不是自由 optimization variable；
- AI agent 应该询问缺失假设，而不是自己发明。

## 快速开始

```powershell
python -m pip install -e .[test]
python -m pytest
```

运行简单系统：

```powershell
python -m physicsguard.cli run examples/dummy_system.yaml --pretty
```

运行 observed debugging hierarchy：

```powershell
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml examples/hierarchical/observed_debugging/pitch_feedback_observed_fault.yaml --pretty
```

这个例子表示一个映射后的 controller feedback 信号。fault case 符号反了；PhysicsGuard 会把 `pitch_rate_feedback` 排为最可疑 block，并建议检查实际 gain、符号约定和信号映射。

## 主要 CLI 模式

```powershell
python -m physicsguard.cli run SYSTEM.yaml --pretty
python -m physicsguard.cli evaluate SYSTEM.yaml OBSERVED.yaml --pretty
python -m physicsguard.cli compare SYSTEM.yaml OBSERVED.yaml --pretty

python -m physicsguard.cli hierarchy run HIERARCHY.yaml --pretty
python -m physicsguard.cli hierarchy inspect HIERARCHY.yaml --pretty
python -m physicsguard.cli hierarchy plan HIERARCHY.yaml --pretty
python -m physicsguard.cli hierarchy evaluate HIERARCHY.yaml OBSERVED.yaml --pretty
python -m physicsguard.cli hierarchy compare HIERARCHY.yaml OBSERVED.yaml --pretty

python -m physicsguard.cli assumptions inspect SYSTEM.yaml --pretty

python -m physicsguard.cli project audit --pretty
python -m physicsguard.cli project adopt --pretty
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
```

## 安装 Codex Skill

让 Codex-compatible agent 执行：

```text
Please install the PhysicsGuard Codex skill from https://github.com/liuyingxuvka/PhysicsGuard.
The skill folder is skill/physicsguard-ai-debugging.
```

手动本地复制：

```powershell
Copy-Item -Recurse skill\physicsguard-ai-debugging $env:USERPROFILE\.codex\skills\physicsguard-ai-debugging
Copy-Item -Recurse skill\physicsguard-project-adoption $env:USERPROFILE\.codex\skills\physicsguard-project-adoption
Copy-Item -Recurse skill\physicsguard-model-understanding-preflight $env:USERPROFILE\.codex\skills\physicsguard-model-understanding-preflight
Copy-Item -Recurse skill\physicsguard-test-file-contract-review $env:USERPROFILE\.codex\skills\physicsguard-test-file-contract-review
Copy-Item -Recurse skill\physicsguard-project-evidence-registry $env:USERPROFILE\.codex\skills\physicsguard-project-evidence-registry
Copy-Item -Recurse skill\physicsguard-model-dataset-validation $env:USERPROFILE\.codex\skills\physicsguard-model-dataset-validation
Copy-Item -Recurse skill\physicsguard-database-catalog $env:USERPROFILE\.codex\skills\physicsguard-database-catalog
Copy-Item -Recurse skill\physicsguard-database-adoption $env:USERPROFILE\.codex\skills\physicsguard-database-adoption
Copy-Item -Recurse skill\physicsguard-database-project-intake $env:USERPROFILE\.codex\skills\physicsguard-database-project-intake
Copy-Item -Recurse skill\physicsguard-database-maintenance $env:USERPROFILE\.codex\skills\physicsguard-database-maintenance
Copy-Item -Recurse skill\physicsguard-model-library $env:USERPROFILE\.codex\skills\physicsguard-model-library
Copy-Item -Recurse skill\physicsguard-signal-mapping-review $env:USERPROFILE\.codex\skills\physicsguard-signal-mapping-review
Copy-Item -Recurse skill\physicsguard-audit-closure $env:USERPROFILE\.codex\skills\physicsguard-audit-closure
Copy-Item -Recurse skill\physicsguard-candidate-model-blueprint $env:USERPROFILE\.codex\skills\physicsguard-candidate-model-blueprint
```

重载后可以这样请求：

```text
Use PhysicsGuard to audit this simulation snapshot and tell me which subsystem is suspicious.
```

```text
Use PhysicsGuard to design a low-fidelity blueprint for this coolant loop, validate each block, then generate a candidate Simulink model with MATLAB scripting.
```

## 模块覆盖

PhysicsGuard `v0.8.0` 包含这些低保真审计关系：

- aggregate power、heat、mass、species、电气母线平衡；
- control error、PID algebraic checks、PID step checks、saturation、hysteresis、threshold、delay、sample-and-hold、actuator/sensor 关系；
- thermodynamic conversion、ideal-gas density、humidity、heat exchanger、radiation、ambient heat loss、compressor sanity checks、rotating-machine affinity；
- component-level motor、inverter、DC/DC converter、compressor、pump、radiator、humidifier、intercooler、engine、fuel-cell stack、electrolyzer stack、map checks；
- fluid networks、thermal management、electrochemical BOP、battery/HV、drivetrain/vehicle、engine/aftertreatment、control/sensor/actuator 工程组件。

所有模块都是低保真审计关系，用来暴露明显 mismatch，不模拟完整硬件或商业求解器行为。

## 文档入口

- [AI-guided debugging protocol](docs/ai_guided_debugging_protocol.md)
- [Hierarchical audit workflow](docs/hierarchical_audit_workflow.md)
- [Hierarchical YAML reference](docs/hierarchical_yaml_reference.md)
- [Assumption cards](docs/assumption_cards.md)
- [Bug playbooks](docs/bug_playbooks.md)
- [Domain starter packs](docs/domain_starter_packs.md)
- [Module spec template](docs/module_spec_template.md)
- [Model-understanding preflight](docs/model_understanding_preflight.md)
- [External-model intake](docs/external_model_intake.md)
- [Module equation ledger](docs/module_equation_ledger.md)
- [Model-code traceability](docs/model_code_traceability.md)
- [Database lifecycle and catalog](docs/database_catalog.md)

## 仓库结构

```text
src/physicsguard/                 Python package
tests/                            测试
examples/                         YAML 示例和 hierarchy templates
docs/                             工作流和 schema 文档
.flowguard/                       FlowGuard lifecycle models 和 traceability ledger
.physicsguard/                    PhysicsGuard project record 和 module/equation ledger
scripts/                          仓库维护脚本
skill/                            本地 Codex skill 源码
assets/readme-hero/               README hero 图资产
```

## 公开边界

这个仓库有意排除本地私人数据、本地知识库历史、生成的 MATLAB/Simulink copied-model artifacts 和机器特定输出。仓库里的 Simulink 相关内容是工作流指导或本地实验脚手架，不是 bundled adapter，也不是重新分发的商业模型。

## 许可证

MIT License。见 [LICENSE](LICENSE)。
