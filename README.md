# PhysicsGuard

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="PhysicsGuard concept hero image" width="100%" />
</p>

<p align="center">
  <strong>Low-fidelity physical understanding, residual audits, and candidate-model blueprints for AI simulation debugging.</strong>
</p>
<!-- README HERO END -->

**Version:** `v0.2.1`  
**Runtime:** Python 3.11+ with `pydantic`, `numpy`, `scipy`, and `PyYAML`  
**License:** MIT  
**Language note:** English comes first; the second half is a full Chinese mirror.

PhysicsGuard is a Python core and Codex skill for AI-guided debugging around physical simulation workflows. It helps an AI agent build a low-fidelity physical understanding map before it tries to debug or generate anything: visible symptom, subsystem hierarchy, interfaces, SI units, conservation relations, signal mappings, assumptions, and residual checks.

From that map, PhysicsGuard can evaluate exported or user-mapped values directly, rank suspicious blocks, expose assumptions, recommend the next signals or parameters to inspect, and produce a candidate-model blueprint. The generated model path stays separate: an AI agent may translate checked interfaces, units, assumptions, and block relations into official APIs or user-owned editable templates, then map the candidate outputs back into PhysicsGuard for residual checks.

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
- It makes assumptions visible through Assumption Cards instead of letting the agent silently invent missing physics.
- It can turn a validated low-fidelity audit hierarchy into a blueprint for a separate candidate model without claiming to recover the original solver.

## What It Is

PhysicsGuard is a transparent audit layer with four pieces:

- YAML system and hierarchy specs;
- low-fidelity residual modules for physics, controls, and engineering sanity checks;
- direct observed-value evaluation for mapped external simulation snapshots;
- hierarchical reports that rank suspicious blocks, show assumption cards, and recommend the next useful refinement.

The original engineering model remains the source of truth. PhysicsGuard is the AI-facing audit lens that helps decide where to look next before exporting more signals, refining a block, or building a candidate model.

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

1. Start from a visible failure: wrong final value, unstable response, impossible heat rejection, broken stack balance, or suspicious subsystem behavior.
2. Build a coarse Level 0 audit with simple balances, signal relations, units, and assumptions.
3. Map external simulation results into `ObservedValuesSpec`.
4. Run direct hierarchical evaluation:

```powershell
python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
```

5. Inspect `top_blocks`, `top_residuals`, assumptions, and `recommended_refinements`.
6. Export only the next variables or parameters that the report actually asks for.
7. Refine the suspicious block rather than modeling the entire external system.
8. Repeat until the issue is localized to a subsystem, component, signal chain, map, parameter, unit conversion, or boundary condition.

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

That example represents a mapped controller feedback signal. The fault case has a reversed sign; PhysicsGuard ranks `pitch_rate_feedback` as the top suspicious block and recommends reviewing the actual gain, sign convention, and signal mapping.

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
```

After reload, use requests such as:

```text
Use PhysicsGuard to audit this simulation snapshot and tell me which subsystem is suspicious.
```

```text
Use PhysicsGuard to design a low-fidelity blueprint for this coolant loop, validate each block, then generate a candidate Simulink model with MATLAB scripting.
```

## Library Coverage

PhysicsGuard `v0.2.1` includes low-fidelity audit relations for:

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

## Repository Map

```text
src/physicsguard/                 Python package
tests/                            Test suite
examples/                         YAML examples and hierarchy templates
docs/                             Workflow and schema documentation
scripts/                          Repository maintenance scripts
skill/physicsguard-ai-debugging/  Local Codex skill source
assets/readme-hero/               README hero image assets
```

## Public Boundary

This repository intentionally excludes local private data, local knowledge-base history, generated MATLAB/Simulink copied-model artifacts, and machine-specific outputs. Simulink-related material in this repository is workflow guidance or local experiment scaffolding, not a bundled adapter or redistributed commercial model.

## License

MIT License. See [LICENSE](LICENSE).

---

# PhysicsGuard 中文说明

**版本：** `v0.2.1`  
**运行环境：** Python 3.11+，依赖 `pydantic`、`numpy`、`scipy`、`PyYAML`  
**许可证：** MIT

PhysicsGuard 是一个 Python 核心库和 Codex skill，用于 AI 辅助物理仿真调试。它帮助 AI agent 在调试或生成模型之前，先搭出一个低保真的物理理解图：可见故障、子系统层级、接口、SI 单位、守恒关系、信号映射、假设和 residual 检查。

基于这张图，PhysicsGuard 可以直接检查导出或用户映射好的 observed values，排序可疑 block，暴露 assumption，推荐下一步应该查看的信号或参数，并产出候选模型蓝图。模型生成路径保持独立：AI agent 可以把已检查的接口、单位、假设和 block 关系，通过官方 API 或用户自己可编辑的模板翻译成独立候选模型，再把候选模型输出映射回 PhysicsGuard 做 residual 检查。

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
- 它用 Assumption Cards 暴露假设，避免 agent 默默补物理假设。
- 它可以把验证过的低保真审计 hierarchy 变成独立候选模型蓝图，同时不声称还原原始求解器。

## 它是什么

PhysicsGuard 是一个透明审计层，包含四个部分：

- YAML system 和 hierarchy spec；
- 低保真物理、控制和工程 sanity-check 残差模块；
- 对外部仿真快照的 observed-value evaluation；
- 可以排序可疑 block、显示 assumption cards 并推荐下一步 refinement 的分层报告。

原始复杂工程模型仍然是真实来源。PhysicsGuard 是面向 AI 的审计视角，用来在继续导出信号、细化 block 或搭建候选模型之前判断下一步应该看哪里。

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

1. 从可见故障开始：最终值错误、响应发散、散热不可能、stack balance 断裂或某个子系统异常。
2. 建一个粗粒度 Level 0 审计，只包含简单守恒、信号关系、单位和假设。
3. 把外部仿真结果映射成 `ObservedValuesSpec`。
4. 运行直接分层评估：

```powershell
python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
```

5. 查看 `top_blocks`、`top_residuals`、assumptions 和 `recommended_refinements`。
6. 只导出报告真正要求的下一批变量或参数。
7. 只细化最可疑 block，而不是建模整个外部系统。
8. 重复，直到问题收敛到子系统、组件、信号链、map、参数、单位转换或边界条件。

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
```

重载后可以这样请求：

```text
Use PhysicsGuard to audit this simulation snapshot and tell me which subsystem is suspicious.
```

```text
Use PhysicsGuard to design a low-fidelity blueprint for this coolant loop, validate each block, then generate a candidate Simulink model with MATLAB scripting.
```

## 模块覆盖

PhysicsGuard `v0.2.1` 包含这些低保真审计关系：

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

## 仓库结构

```text
src/physicsguard/                 Python package
tests/                            测试
examples/                         YAML 示例和 hierarchy templates
docs/                             工作流和 schema 文档
scripts/                          仓库维护脚本
skill/physicsguard-ai-debugging/  本地 Codex skill 源码
assets/readme-hero/               README hero 图资产
```

## 公开边界

这个仓库有意排除本地私人数据、本地知识库历史、生成的 MATLAB/Simulink copied-model artifacts 和机器特定输出。仓库里的 Simulink 相关内容是工作流指导或本地实验脚手架，不是 bundled adapter，也不是重新分发的商业模型。

## 许可证

MIT License。见 [LICENSE](LICENSE)。
