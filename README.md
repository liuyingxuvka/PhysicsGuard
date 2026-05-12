# PhysicsGuard

<!-- README HERO START -->
<p align="center">
  <img src="./assets/readme-hero/hero.png" alt="PhysicsGuard concept hero image" width="100%" />
</p>

<p align="center">
  <strong>AI-guided audits and model-building blueprints for physical simulation workflows.</strong>
</p>
<!-- README HERO END -->

**Version:** v0.2.0
**Language note:** English comes first; the second half is a full Chinese mirror.  
**中文说明：** 英文在前，后半部分是完整中文镜像。

PhysicsGuard is a Python core and Codex skill for AI-assisted debugging and model-building around physical simulation workflows. It helps an AI agent build low-fidelity audit models, evaluate mapped external signals, rank suspicious blocks, recommend the next signals or parameters to inspect, and use validated PhysicsGuard hierarchies as blueprints for candidate models.

It is useful around large engineering models built in tools such as **MATLAB/Simulink**, **GT-SUITE**, Modelica-like tools, Python simulations, and other physical simulation workflows. PhysicsGuard does **not** parse those models, does **not** reverse engineer commercial tools, and does **not** replace the original solver. It checks exported or mapped values with explicit residual equations. When an official scripting interface is available, such as MATLAB/Simulink scripting, an AI agent can also use a validated PhysicsGuard blueprint to generate a separate candidate model.

## What It Is

- A residual-audit framework for low-fidelity physics and control checks.
- A YAML-driven system specification format.
- A bounded solver for reference low-fidelity audits.
- A direct observed-value evaluator for external simulation snapshots.
- A hierarchical/progressive audit report that ranks suspicious blocks.
- An Assumption Card layer that makes every assumption visible.
- A model-building blueprint layer for progressively assembling candidate engineering models from validated low-fidelity blocks.
- A local Codex skill that guides AI agents through coarse-to-fine simulation debugging and candidate-model construction.

## What It Can Help Diagnose

- Unit and scale mistakes: bar vs Pa, rpm vs rad/s, g/s vs kg/s.
- Sign reversals in feedback, force, torque, pressure, or flow.
- Broken power, heat, mass, species, or electrical-bus balances.
- Bad signal mappings between an external model and an audit variable.
- Physically impossible pressure, flow, current, voltage, temperature, or power combinations.
- Wrong map-axis usage, interpolation inputs, or extrapolation behavior.
- Inconsistent controller, actuator, sensor, saturation, clamp, or delay logic.
- Fuel-cell, electrolyzer, battery/HV, drivetrain, engine, pump, compressor, radiator, and thermal-management scaling errors.

## What It Is Not

PhysicsGuard is not a GT-SUITE, Simulink, Simscape, Modelica, Amesim, FMI, CSV, MATLAB, PyBaMM, or OpenFCST adapter. It does not claim equivalence with commercial solver internals. It does not perform automatic repair, natural-language report generation, CFD, 1D gas dynamics, high-fidelity electrochemistry, combustion, or detailed thermal-fluid simulation.

The intended audit use is: keep the original complex model as the source of truth, export or map selected signals, and let PhysicsGuard run transparent low-fidelity checks that help an AI decide where to look next.

The intended model-building use is: start from a simple PhysicsGuard hierarchy, validate each block with explicit residuals, then let AI translate the checked blueprint into a separate candidate model through official scripting interfaces such as MATLAB/Simulink APIs. Generated target models should be treated as candidate engineering models, not recovered copies of existing commercial models.

## Core Audit Workflow

1. Start from the visible failure: wrong final value, unstable response, impossible heat rejection, bad stack balance, etc.
2. Build a coarse Level 0 audit with simple balances or signal relations.
3. Map external simulation results into `ObservedValuesSpec`.
4. Run direct hierarchical evaluation:

   ```powershell
   python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
   ```

5. Inspect `top_blocks`, `top_residuals`, and `recommended_refinements`.
6. Export the next variables or parameters requested by the recommendation.
7. Refine only the suspicious block.
8. Repeat until the issue is localized to a subsystem, component, signal chain, map, parameter, unit conversion, or boundary.

Use compare mode when you also want a solved low-fidelity reference:

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

## Candidate Model-Building Workflow

PhysicsGuard can also be used as a structured blueprint before AI generates a target model.

1. Define the target system and the minimum useful fidelity for each block.
2. Build the lowest-fidelity PhysicsGuard hierarchy first: balances, interfaces, units, simple components, and assumptions.
3. Validate each block with PhysicsGuard examples, observed data, or conflict tests.
4. Refine one block at a time until the blueprint is detailed enough.
5. For MATLAB/Simulink, generate a separate candidate model through documented MATLAB/Simulink scripting APIs.
6. Run the generated candidate model and map its outputs back into PhysicsGuard.
7. Use residuals to decide whether to refine, reconnect, or correct the generated block.
8. Assemble larger subsystems only after their child blocks pass the relevant checks.

For GT-SUITE, Modelica, Amesim, FMI, or similar tools, this workflow requires official APIs, documented exchange formats, user-provided templates, or user-owned editable files. PhysicsGuard does not reverse engineer proprietary formats.

## Quick Start

```powershell
python -m pip install -e .[test]
python -m pytest

python -m physicsguard.cli run examples/dummy_system.yaml --pretty
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml examples/hierarchical/observed_debugging/pitch_feedback_observed_fault.yaml --pretty
```

The observed debugging example represents a mapped controller feedback signal. The fault case has a reversed sign; PhysicsGuard ranks `pitch_rate_feedback` as the top suspicious block and recommends reviewing the actual gain, sign convention, and signal mapping.

## Install The Codex Skill Locally

The simplest install path is to give this GitHub repository URL to your AI agent and ask it to install the included Codex skill:

```text
Please install the PhysicsGuard Codex skill from https://github.com/liuyingxuvka/PhysicsGuard.
The skill folder is skill/physicsguard-ai-debugging.
```

The repository includes the skill source folder here:

```text
skill/physicsguard-ai-debugging/
```

If you want to do it manually, copy it into your local Codex skills directory:

```powershell
Copy-Item -Recurse skill\physicsguard-ai-debugging $env:USERPROFILE\.codex\skills\physicsguard-ai-debugging
```

After Codex reloads its skill list, ask for tasks such as:

```text
Use PhysicsGuard to audit this Simulink result snapshot and tell me which subsystem is suspicious.
```

```text
Use PhysicsGuard to design a low-fidelity blueprint for this coolant loop, validate each block, then generate a candidate Simulink model with MATLAB scripting.
```

The skill tells Codex to use observed-value evaluation first, keep assumptions explicit, and request only the next useful signals instead of trying to model the whole external system.
For model-building tasks, the skill tells Codex to validate the PhysicsGuard hierarchy first, then generate target-model scripts only for blocks with explicit interfaces, units, and assumptions.

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

## Library Coverage

PhysicsGuard v0.2.0 includes low-fidelity modules for:

- aggregate power, heat, mass, species, and electrical-bus balances;
- control error, PID algebraic checks, PID step checks, saturation, hysteresis, threshold checks, delay, sample-and-hold, and actuator/sensor relations;
- thermodynamic conversion, ideal-gas density, humidity, heat exchanger, radiation, ambient heat loss, compressor sanity checks, rotating-machine affinity;
- component-level motor, inverter, DC/DC converter, compressor, pump, radiator, humidifier, intercooler, engine, fuel-cell stack, electrolyzer stack, and map-based checks;
- engineering components for fluid networks, thermal management, electrochemical BOP, battery/HV, drivetrain/vehicle, engine/aftertreatment, and control/sensor/actuator checks.

All modules are low-fidelity audit relations. They are intended to detect obvious mismatch, not to simulate full hardware or commercial solver behavior.

The repository also includes domain starter-pack guidance plus runnable hierarchy templates for wastewater, renewable microgrids, HVAC, power distribution, process industry, drainage, utilities, data centers, mobility, agriculture/food/bioprocess, and expanded scenarios such as cross-domain audit primitives, oil/gas, water supply, manufacturing, mining/metallurgy, combustion boiler/furnace, geothermal wells, cold-chain logistics, robotics/mechatronics, satellite thermal, and medical/bioprocess equipment. See `docs/domain_starter_packs.md` and the corresponding folders under `examples/hierarchical/`.

## Assumptions

PhysicsGuard uses explicit Assumption Cards. There are no hidden assumptions. Active assumptions appear in diagnostic JSON, proposed and rejected assumptions are visible but not applied, and high-impact assumptions produce warnings.

## Repository Map

```text
src/physicsguard/                 Python package
tests/                            Test suite
examples/                         YAML examples
docs/                             Workflow and schema documentation
scripts/                          Repository maintenance scripts
skill/physicsguard-ai-debugging/  Local Codex skill source
assets/readme-hero/               README hero image assets
```

## Public Boundary

This repository intentionally excludes local private data, local knowledge-base history, generated MATLAB/Simulink copied-model artifacts, and machine-specific outputs. The included Simulink-related material is workflow guidance and local experiment scaffolding, not a bundled adapter or redistributed commercial example model.

## License

MIT License. See [LICENSE](LICENSE).

---

# PhysicsGuard 中文说明

**版本：** v0.2.0

PhysicsGuard 是一个 Python 核心库加 Codex skill，用来让 AI 辅助调试物理仿真结果，并围绕物理仿真工作流搭建候选模型。它帮助 AI 构建低保真审计模型，检查外部仿真导出的信号，排序最可疑的系统块，推荐下一步应该查看哪些信号或参数，并把验证过的 PhysicsGuard 分层模型作为候选模型的蓝图。

它适合围绕 **MATLAB/Simulink**、**GT-SUITE**、Modelica 类工具、Python 仿真以及其他物理仿真流程使用。PhysicsGuard **不会**解析这些模型，**不会**逆向商业工具，**不会**替代原始求解器。它做的是：把导出或映射好的数值放进显式残差方程里检查。当目标工具有官方脚本接口时，例如 MATLAB/Simulink 脚本接口，AI 也可以用验证过的 PhysicsGuard 蓝图生成一个独立的候选模型。

## 它是什么

- 一个低保真物理和控制残差审计框架。
- 一个 YAML 驱动的系统规格格式。
- 一个用于低保真参考审计的有界求解器。
- 一个直接检查外部仿真快照的 observed-value evaluator。
- 一个分层/渐进式审计报告，可以排序可疑 block。
- 一个 Assumption Card 层，让每个假设都显式可见。
- 一个模型搭建蓝图层，可以从验证过的低保真 block 逐步组装候选工程模型。
- 一个本地 Codex skill，用来指导 AI 粗到细地调试仿真问题，并搭建候选模型。

## 它可以帮助诊断什么

- 单位和尺度错误：bar vs Pa、rpm vs rad/s、g/s vs kg/s。
- 反馈、力、扭矩、压力或流量方向写反。
- 功率、热、质量、物种或高压电气母线守恒关系断裂。
- 外部模型信号和审计变量之间的映射错误。
- 压力、流量、电流、电压、温度或功率出现物理上不可能的组合。
- map 轴、插值输入或外推行为使用错误。
- 控制器、执行器、传感器、饱和、限幅、延迟逻辑不一致。
- 燃料电池、电解槽、电池/HV、传动系统、发动机、泵、压缩机、散热器和热管理系统中的缩放错误。

## 它不是什么

PhysicsGuard 不是 GT-SUITE、Simulink、Simscape、Modelica、Amesim、FMI、CSV、MATLAB、PyBaMM 或 OpenFCST adapter。它不声称等价于商业求解器内部逻辑。它不做自动修复，不生成自然语言报告，不做 CFD、一维气体动力学、高保真电化学、燃烧或详细热流体仿真。

正确的审计用法是：原复杂模型仍然是真实来源，用户或 AI 只导出/映射一小部分信号，PhysicsGuard 用透明的低保真关系检查这些信号，帮助 AI 判断下一步该看哪里。

正确的模型搭建用法是：先从简单 PhysicsGuard 分层模型开始，用显式残差验证每个 block，再让 AI 通过官方脚本接口把这个蓝图翻译成独立的候选模型。生成出来的目标模型应该被看作候选工程模型，而不是对现有商业模型的还原。

## 核心审计流程

1. 从可见故障开始：最终值错误、响应发散、散热不可能、stack balance 不对等。
2. 建一个粗粒度 Level 0 审计，只检查简单守恒或信号关系。
3. 把外部仿真结果映射成 `ObservedValuesSpec`。
4. 运行直接分层评估：

   ```powershell
   python -m physicsguard.cli hierarchy evaluate AUDIT.yaml OBSERVED.yaml --pretty
   ```

5. 查看 `top_blocks`、`top_residuals` 和 `recommended_refinements`。
6. 只导出推荐里要求的下一批信号或参数。
7. 只细化最可疑的 block。
8. 重复，直到问题缩小到子系统、组件、信号链、map、参数、单位转换或边界条件。

如果还想和一个低保真参考解比较，可以运行：

```powershell
python -m physicsguard.cli hierarchy compare AUDIT.yaml OBSERVED.yaml --pretty
```

## 候选模型搭建流程

PhysicsGuard 也可以作为 AI 生成目标模型之前的结构化蓝图。

1. 先定义目标系统，以及每个 block 最低需要达到什么精度。
2. 从最低保真 PhysicsGuard 分层模型开始：守恒、接口、单位、简单组件和显式假设。
3. 用 PhysicsGuard 示例、外部 observed data 或 conflict tests 验证每个 block。
4. 一次只细化一个 block，直到蓝图足够详细。
5. 对 MATLAB/Simulink，可以通过官方 MATLAB/Simulink 脚本接口生成独立候选模型。
6. 运行生成的候选模型，把输出再映射回 PhysicsGuard。
7. 用残差判断应该细化、重连还是修正哪个生成 block。
8. 子 block 通过检查之后，再逐步拼装更大的 subsystem。

对 GT-SUITE、Modelica、Amesim、FMI 或类似工具，这个流程需要官方 API、文档化交换格式、用户提供的模板或用户自己拥有的可编辑文件。PhysicsGuard 不逆向专有格式。

## 快速开始

```powershell
python -m pip install -e .[test]
python -m pytest

python -m physicsguard.cli run examples/dummy_system.yaml --pretty
python -m physicsguard.cli hierarchy evaluate examples/hierarchical/observed_debugging/pitch_feedback_level_0.yaml examples/hierarchical/observed_debugging/pitch_feedback_observed_fault.yaml --pretty
```

这个 observed debugging 例子代表一个映射好的控制反馈信号。故障版本把符号反了；PhysicsGuard 会把 `pitch_rate_feedback` 排为最可疑 block，并建议检查实际 gain、符号约定和信号映射。

## 安装本地 Codex Skill

最简单的方法是把这个 GitHub 仓库地址交给你的 AI agent，然后让它安装里面的 Codex skill：

```text
Please install the PhysicsGuard Codex skill from https://github.com/liuyingxuvka/PhysicsGuard.
The skill folder is skill/physicsguard-ai-debugging.
```

仓库里也包含 skill 源文件：

```text
skill/physicsguard-ai-debugging/
```

如果你想手动安装，可以把它复制到本机 Codex skill 目录：

```powershell
Copy-Item -Recurse skill\physicsguard-ai-debugging $env:USERPROFILE\.codex\skills\physicsguard-ai-debugging
```

Codex 重新加载 skill 后，可以这样提问：

```text
Use PhysicsGuard to audit this Simulink result snapshot and tell me which subsystem is suspicious.
```

```text
Use PhysicsGuard to design a low-fidelity blueprint for this coolant loop, validate each block, then generate a candidate Simulink model with MATLAB scripting.
```

这个 skill 会指导 Codex 优先使用 observed-value evaluation，显式记录假设，并且每轮只请求下一批最有用的信号，而不是试图一次性建完整外部模型。
对于模型搭建任务，这个 skill 会要求 Codex 先验证 PhysicsGuard 分层蓝图，再只为接口、单位和假设都明确的 block 生成目标模型脚本。

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

## 模块覆盖

PhysicsGuard v0.2.0 包含低保真模块：

- 总体功率、热、质量、物种和电气母线守恒；
- 控制误差、PID、饱和、迟滞、阈值、延迟、sample-and-hold、执行器和传感器关系；
- 热力学转换、理想气体密度、湿度、换热器、辐射、环境热损失、压缩机 sanity check、旋转机械相似律；
- 电机、逆变器、DC/DC、压缩机、泵、散热器、加湿器、中冷器、发动机、燃料电池 stack、电解槽 stack 和 map 检查；
- 流体网络、热管理、电化学 BOP、电池/HV、车辆/传动、发动机/后处理、控制/传感器/执行器工程组件。

所有模块都是低保真审计关系。它们用于发现明显不一致，不用于完整模拟硬件或商业求解器。

仓库也加入了行业 starter pack 指南，以及可运行的分层模板，覆盖污水处理、可再生能源微电网、建筑 HVAC、配电/DER、过程工业、雨洪/污水管网/排水系统、工业公用工程、数据中心/电子冷却、移动/交通扩展、农业/食品/生物过程，以及扩展场景：通用底层审计 primitives、油气、水务供水、制造、矿冶、燃烧锅炉/炉膛、地热井、冷链物流、机器人/机电、卫星热控和医疗/生物过程设备。详见 `docs/domain_starter_packs.md` 和 `examples/hierarchical/` 下的对应目录。

## 假设

PhysicsGuard 使用显式 Assumption Cards。没有隐藏假设。启用的假设会出现在诊断 JSON 中；proposed 和 rejected 假设可见但不应用；high-impact 假设会产生 warning。

## 仓库结构

```text
src/physicsguard/                 Python 包
tests/                            测试
examples/                         YAML 示例
docs/                             工作流和 schema 文档
scripts/                          仓库维护脚本
skill/physicsguard-ai-debugging/  本地 Codex skill 源文件
assets/readme-hero/               README 顶部图像
```

## 公开边界

这个公开仓库刻意排除了本地私有数据、本地知识库历史、生成的 MATLAB/Simulink 复制模型文件以及机器相关输出。仓库里的 Simulink 相关内容是流程说明和本地实验脚手架，不是 adapter，也不包含重新分发的商业示例模型。

## 许可证

MIT License。见 [LICENSE](LICENSE)。
