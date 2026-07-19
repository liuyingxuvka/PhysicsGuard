# PhysicsGuard

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="PhysicsGuard concept hero image" width="100%" />
</p>

<p align="center">
  <strong>Low-fidelity residual audits for mapped physical-simulation signals and AI debugging plans.</strong>
</p>
<!-- README HERO END -->

| Version | Runtime | Package | License |
| --- | --- | --- | --- |
| `v0.11.2` | Python 3.11+ | `physicsguard` | MIT |

English comes first. A Chinese mirror follows below.

## What PhysicsGuard Is

PhysicsGuard is a Python toolkit and Codex skill for AI-guided debugging of physical simulation workflows.

It helps an agent build a low-fidelity physical understanding map before it tries to fix, explain, or generate anything. That map names the visible symptom, subsystem boundary, interfaces, SI units, conservation relations, mapped signals, assumptions, residual checks, and stop condition.

From that map, PhysicsGuard can evaluate observed or user-mapped values, rank suspicious blocks, expose assumptions, recommend the next signals or parameters to inspect, and produce a candidate-model blueprint for a separate user-owned model.

It does not parse commercial solver formats, reverse engineer proprietary models, replace the original solver, or claim high-fidelity equivalence. The original engineering model remains the source of truth.

## The Problem

Large simulation models often fail in ways that are easy for an AI agent to misread:

1. A signal has the wrong sign.
2. A unit conversion is silently off.
3. A lookup map is outside its valid range.
4. A mass, energy, heat, torque, pressure, voltage, or signal balance no longer closes.
5. A mapped external signal is only a guess, but the agent treats it as verified.
6. The agent asks for every possible signal instead of the next signal that would actually reduce uncertainty.

PhysicsGuard turns those failures into a low-fidelity residual audit that an engineer can inspect.

## How It Works

The practical route is:

```text
visible symptom
-> subsystem boundary
-> mapped signals and units
-> low-fidelity residual hierarchy
-> suspicious blocks and assumptions
-> next-signal recommendations
-> optional candidate-model blueprint
```

The important design choice is modesty. PhysicsGuard does not try to recreate a full solver. It checks explicit, reviewable relations such as balances, gains, signs, map bounds, controller steps, flow splits, and sanity envelopes.

## What It Can Build And Check

| Goal | PhysicsGuard output | Boundary |
| --- | --- | --- |
| Understand a simulation failure | Level 0 physical map with symptom, subsystem, expected relation, key signals, SI units, assumptions, and first residuals | Low-fidelity understanding, not solver reconstruction |
| Localize a likely bug | Hierarchy report with suspicious blocks, top residuals, assumption cards, and recommended refinements | Ranking is diagnostic evidence, not proof of the only fault |
| Decide what to export next | Targeted signal, parameter, unit, bound, map, or topology request | Missing data stays explicit |
| Validate mapped data files | Test-file manifests, contracts, coverage checks, and model binding rows | File coverage is not physical correctness |
| Compare model and dataset | Logical checks, relation checks, validation reports, and optional bounded calibration | Calibration is conservative and bounded |
| Close project evidence claims | Evidence meshes and project closure reports | Claim-readiness proof, not physical correctness proof |
| Build a candidate model | Interfaces, units, assumptions, block relations, examples, and validation order | Candidate models are new artifacts, not recovered commercial models |

## Quick Start

Install the package in editable mode:

```powershell
python -m pip install -e .
```

Run the public example:

```powershell
python examples/run_pitch_residual_audit.py
```

The example represents a mapped controller feedback signal. The fault case has a reversed sign, so PhysicsGuard ranks `pitch_rate_feedback` as suspicious and recommends checking sign convention, gain, mapping confidence, unit conversion, and related signal-chain mappings.

## Main CLI Paths

Project and model-understanding checks:

```powershell
python -m physicsguard.cli project audit --pretty
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
python -m physicsguard.cli evidence mesh-check examples/testfile_contracts/pump_loop/evidence_mesh.yaml --pretty
python -m physicsguard.cli project closure templates/project_closure_plan.yaml --pretty
python scripts/check_module_equation_ledger.py --json
```

Test-file and dataset checks:

```powershell
python -m physicsguard.cli testfile manifest DATA.csv --profile PROFILE.yaml --out MANIFEST.yaml
python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
python -m physicsguard.cli coverage check CONTRACT.yaml --pretty
python -m physicsguard.cli dataset logical-check DATASET.yaml --pretty
python -m physicsguard.cli dataset relation-check RELATIONS.yaml --pretty
python -m physicsguard.cli validation run VALIDATION_PLAN.yaml --pretty
```

Candidate model and reusable-library checks:

```powershell
python -m physicsguard.cli blueprint review BLUEPRINT.yaml --pretty
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

## Assumption Cards

PhysicsGuard treats assumptions as first-class audit objects. Assumptions can be active, proposed, rejected, high-impact, or under review.

This matters because an AI agent can otherwise hide a missing signal or parameter behind a plausible sentence. In PhysicsGuard, a missing coolant flow, uncertain gain, unverified unit, or proposed map simplification must remain visible until it is supported, rejected, or scoped out.

## Visual Audit Communication

PhysicsGuard can use compact diagrams and tables to explain:

- subsystem topology and interfaces;
- residual localization;
- observed signal mappings;
- active, proposed, and rejected assumptions;
- coarse-to-fine refinement paths;
- candidate-model blueprints.

Those visuals are explanation aids. Validation still comes from residual reports, explicit mappings, closure evidence, tests, and examples.

## When To Use It

Use PhysicsGuard when:

- an AI agent is debugging a physical simulation or controller-like workflow;
- the issue could involve units, signs, gains, maps, balances, or signal mappings;
- you need to decide which signal or parameter to export next;
- a low-fidelity candidate model would help explain or test the suspected subsystem;
- you need an audit record that keeps assumptions and missing evidence visible.

Do not use it when:

- the task only needs a full-fidelity solver run;
- you need proprietary model extraction;
- no physical boundary, signal, unit, or residual relation is available;
- a statistical or business claim is being evaluated rather than a physical relation.

## Library Coverage

PhysicsGuard `v0.11.2` includes low-fidelity audit relations for:

- controls, sensors, actuators, delays, saturation, maps, and PID-like steps;
- drivetrain, vehicle, brake, wheel, gearbox, and road-load relations;
- electric motor, inverter, DC/DC, battery, charger, and HV bus checks;
- fuel cell, electrolyzer, gas production, recirculation, cooling, and balance checks;
- engine, turbo, aftertreatment, thermal, humidifier, heat exchanger, radiator, and compressor sanity checks;
- fluid networks, pumps, valves, pressure drops, split/merge relations, and lumped volumes.

Each relation is low fidelity by design. The value is not that it replaces the target model; the value is that it gives the AI a checkable physics boundary before it changes the target workflow.

## Documentation Map

| File | Purpose |
| --- | --- |
| [`docs/model_understanding_preflight.md`](./docs/model_understanding_preflight.md) | visible symptom, subsystem boundary, units, assumptions, and stop condition |
| [`docs/external_model_intake.md`](./docs/external_model_intake.md) | safe intake of external model facts without claiming parser support |
| [`docs/hierarchical_audit_workflow.md`](./docs/hierarchical_audit_workflow.md) | hierarchy and residual audit route |
| [`docs/test_file_contracts.md`](./docs/test_file_contracts.md) | concrete test-file manifests and binding contracts |
| [`docs/model_dataset_validation.md`](./docs/model_dataset_validation.md) | dataset validation and bounded calibration |
| [`docs/project_evidence_registry.md`](./docs/project_evidence_registry.md) | project-level evidence registry |
| [`docs/evidence_mesh.md`](./docs/evidence_mesh.md) | strong parent-child evidence mesh before broad claims |
| [`docs/project_closure_gate.md`](./docs/project_closure_gate.md) | closure gate before final debugging claims |
| [`docs/assumption_cards.md`](./docs/assumption_cards.md) | assumption-card lifecycle |
| [`docs/model_library.md`](./docs/model_library.md) | reusable low-fidelity model library |
| [`docs/model_code_traceability.md`](./docs/model_code_traceability.md) | model-to-code ledger and evidence freshness |

## Repository Layout

```text
src/physicsguard/       Core package
examples/               Low-fidelity relation and conflict examples
templates/              Project, closure, intake, and model templates
docs/                   Protocol and route documentation
skill/                  Codex skill material
scripts/                Validation and release checks
assets/readme-hero/     README hero image assets
VERSION                 Current public version
CHANGELOG.md            Release history
```

## Public Boundary

This public repository contains the low-fidelity audit framework, examples, docs, templates, and skill material.

It does not contain proprietary model files, customer simulation data, confidential signal exports, production calibration data, or recovered commercial-model internals. A PhysicsGuard pass means the declared low-fidelity checks passed for the mapped evidence. It does not mean the original engineering model is correct.

## License

MIT. See [`LICENSE`](./LICENSE).

---

# PhysicsGuard 中文说明

| 版本 | 运行环境 | 包名 | 许可证 |
| --- | --- | --- | --- |
| `v0.11.2` | Python 3.11+ | `physicsguard` | MIT |

## 它是什么

PhysicsGuard 是一个用于 AI 辅助物理仿真调试的 Python 工具包和 Codex skill。

它让 agent 在修模型、解释问题或生成候选模型之前，先建立一个低保真的物理理解图：可见症状、子系统边界、接口、SI 单位、守恒关系、映射信号、假设、residual 检查和停止条件。

基于这个图，PhysicsGuard 可以代入 observed / user-mapped values，排序可疑 block，暴露假设，推荐下一步该检查的信号或参数，并产出一个独立候选模型的 blueprint。

它不解析商业 solver 格式，不逆向专有模型，不替代原始 solver，也不声称高保真等价。原始工程模型仍然是事实来源。

## 为什么需要它

大型仿真模型常见错误很容易被 AI 误读：

1. 信号符号反了。
2. 单位转换悄悄错了。
3. lookup map 超出有效范围。
4. 质量、能量、热量、扭矩、压力、电压或信号 balance 不闭合。
5. 外部信号映射只是猜测，但 agent 当成 verified。
6. agent 要求导出所有信号，而不是问真正能减少不确定性的下一个信号。

PhysicsGuard 把这些问题变成工程师可以检查的低保真 residual audit。

## 它怎么工作

实际路线是：

```text
visible symptom
-> subsystem boundary
-> mapped signals and units
-> low-fidelity residual hierarchy
-> suspicious blocks and assumptions
-> next-signal recommendations
-> optional candidate-model blueprint
```

关键是克制。PhysicsGuard 不试图重建完整 solver，只检查明确、可审阅的关系，比如 balance、gain、sign、map bounds、controller step、flow split 和 sanity envelope。

## 它能搭出并检查什么

| 目标 | PhysicsGuard 产出 | 边界 |
| --- | --- | --- |
| 理解仿真故障 | Level 0 physical map | 低保真理解，不是 solver 重建 |
| 定位可能 bug | suspicious blocks、top residuals、assumption cards、refinements | 排名是诊断证据，不是唯一故障证明 |
| 决定下一步导出什么 | 有针对性的 signal / parameter / unit / map 请求 | 缺失数据保持显式 |
| 校验 mapped data files | manifest、contract、coverage、model binding | 文件覆盖不等于物理正确 |
| 对比模型和数据 | logical check、relation check、validation report、bounded calibration | calibration 是保守有界的 |
| 闭合项目证据 claim | evidence mesh 和 project closure report | claim-readiness 证明，不是物理正确证明 |
| 生成候选模型 | interface、unit、assumption、block relation、example、validation order | 候选模型是新工件，不是恢复商业模型 |

## 快速开始

以 editable 模式安装：

```powershell
python -m pip install -e .
```

运行公开示例：

```powershell
python examples/run_pitch_residual_audit.py
```

这个例子表示一个映射过的 controller feedback signal。故障 case 的符号反了，所以 PhysicsGuard 会把 `pitch_rate_feedback` 排为可疑项，并建议检查 sign convention、gain、mapping confidence、unit conversion 和相关 signal-chain mapping。

## 主要 CLI 路线

项目和模型理解检查：

```powershell
python -m physicsguard.cli project audit --pretty
python -m physicsguard.cli preflight review templates/model_understanding_preflight.yaml --pretty
python -m physicsguard.cli intake review templates/external_model_intake.yaml --pretty
python -m physicsguard.cli evidence mesh-check examples/testfile_contracts/pump_loop/evidence_mesh.yaml --pretty
python -m physicsguard.cli project closure templates/project_closure_plan.yaml --pretty
python scripts/check_module_equation_ledger.py --json
```

测试文件和数据集检查：

```powershell
python -m physicsguard.cli testfile manifest DATA.csv --profile PROFILE.yaml --out MANIFEST.yaml
python -m physicsguard.cli testfile contract-check CONTRACT.yaml --pretty
python -m physicsguard.cli coverage check CONTRACT.yaml --pretty
python -m physicsguard.cli dataset logical-check DATASET.yaml --pretty
python -m physicsguard.cli dataset relation-check RELATIONS.yaml --pretty
python -m physicsguard.cli validation run VALIDATION_PLAN.yaml --pretty
```

候选模型和复用库检查：

```powershell
python -m physicsguard.cli blueprint review BLUEPRINT.yaml --pretty
python -m physicsguard.cli model-library check MODEL_LIBRARY.yaml --pretty
```

## 假设卡片

PhysicsGuard 把假设当成一等审计对象。假设可以是 active、proposed、rejected、high-impact 或 under review。

这很重要，因为 AI 容易用一句合理的话掩盖缺失信号或参数。在 PhysicsGuard 里，缺失 coolant flow、不确定 gain、未验证单位或 proposed map simplification 都必须保持可见，直到被支持、拒绝或明确排除。

## 可视化审计沟通

PhysicsGuard 可以用紧凑图表解释：

- subsystem topology 和 interface；
- residual localization；
- observed signal mapping；
- active / proposed / rejected assumptions；
- coarse-to-fine refinement path；
- candidate-model blueprint。

这些图是解释辅助。真正验证仍然来自 residual report、显式 mapping、closure evidence、tests 和 examples。

## 什么时候用

适合：

- AI agent 正在调试物理仿真或 controller-like workflow；
- 问题可能来自单位、符号、gain、map、balance 或 signal mapping；
- 需要决定下一步导出哪个信号或参数；
- 低保真候选模型能帮助解释或测试可疑子系统；
- 需要把假设和缺失证据保持可见的审计记录。

不适合：

- 只需要跑完整高保真 solver；
- 需要提取专有模型；
- 没有物理边界、信号、单位或 residual relation；
- 要评估的是统计或业务 claim，而不是物理关系。

## 模块覆盖

PhysicsGuard `v0.11.2` 包含这些低保真审计关系：

- controls、sensors、actuators、delays、saturation、maps、PID-like steps；
- drivetrain、vehicle、brake、wheel、gearbox、road-load；
- electric motor、inverter、DC/DC、battery、charger、HV bus；
- fuel cell、electrolyzer、gas production、recirculation、cooling、balance；
- engine、turbo、aftertreatment、thermal、humidifier、heat exchanger、radiator、compressor sanity；
- fluid networks、pumps、valves、pressure drops、split/merge、lumped volumes。

每个关系都是低保真的。价值不在于替代目标模型，而在于让 AI 在改目标 workflow 之前先有一个可检查的物理边界。

## 文档入口

| 文件 | 作用 |
| --- | --- |
| [`docs/model_understanding_preflight.md`](./docs/model_understanding_preflight.md) | 症状、边界、单位、假设和停止条件 |
| [`docs/external_model_intake.md`](./docs/external_model_intake.md) | 安全记录外部模型事实，不声称 parser 支持 |
| [`docs/hierarchical_audit_workflow.md`](./docs/hierarchical_audit_workflow.md) | hierarchy 和 residual audit 路线 |
| [`docs/test_file_contracts.md`](./docs/test_file_contracts.md) | 测试文件 manifest 和 binding contract |
| [`docs/model_dataset_validation.md`](./docs/model_dataset_validation.md) | 数据集验证和有界 calibration |
| [`docs/project_evidence_registry.md`](./docs/project_evidence_registry.md) | 项目级 evidence registry |
| [`docs/evidence_mesh.md`](./docs/evidence_mesh.md) | broad claim 前的父子证据网格 |
| [`docs/project_closure_gate.md`](./docs/project_closure_gate.md) | 最终 debugging claim 前的 closure gate |
| [`docs/assumption_cards.md`](./docs/assumption_cards.md) | assumption card 生命周期 |
| [`docs/model_library.md`](./docs/model_library.md) | 可复用低保真模型库 |
| [`docs/model_code_traceability.md`](./docs/model_code_traceability.md) | model-to-code ledger 和 evidence freshness |

## 仓库结构

```text
src/physicsguard/       核心包
examples/               低保真关系和 conflict 示例
templates/              项目、closure、intake 和 model 模板
docs/                   协议和路线文档
skill/                  Codex skill material
scripts/                验证和发布检查
assets/readme-hero/     README hero 素材
VERSION                 当前公开版本
CHANGELOG.md            发布历史
```

## 公开边界

这个公开仓库包含低保真审计框架、示例、文档、模板和 skill material。

它不包含专有模型文件、客户仿真数据、机密信号导出、生产 calibration 数据或恢复出来的商业模型内部结构。PhysicsGuard 通过，只表示声明的低保真检查在映射证据上通过，不表示原始工程模型正确。

## 许可证

MIT. See [`LICENSE`](./LICENSE).
