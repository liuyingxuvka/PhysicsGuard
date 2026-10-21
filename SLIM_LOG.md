# PhysicsGuard slim/2026-10 执行记录

目标版本：0.15.16（用户覆盖交接文档的0.16.0）；新FlowGuard最低版本按协调者指定0.70.7，不改历史基线。

## 基线与准备

- 源码基线：`2011179e0f192109c15a95c0a3209f899d2ddf23`，与交接一致；分支 `slim/2026-10`。
- 按XR-01：新建本仓库`.venv`，先`.venv/bin/python -m pip install -e ".[test]"`，再`pip install -e <基线>/flowguard`；PG可编辑安装指向本仓库，FlowGuard为只读基线0.70.6。
- 环境偏差：系统Python3.13缺ensurepip，未安装系统包；重建这次新建的空环境为清单允许的Python3.12（实际3.12.14）。协调者确认PG特例：保留3.12完整基线一次，另对缓存3.11做PG-12相关收集边界窄复现。
- `PYTHONDONTWRITEBYTECODE=1`用于所有验证；只读基线允许editable产生ignored安装元数据，不改tracked业务源码。
- 已读AGENTS.md、当前地图、交接总则、PG介绍/规则/总验证和XR-01依赖表；尚未开始PG-01，等待LW-09依赖信号。

### 基线命令结果


- 静态库存：1268 tracked文件；.flowguard 283；openspec 204；10技能入口，技能文件76个/265554字节。
- Python3.11.17窄边界：单独环境直接导入旧模板选择模块（完整命令见仓库外PG-12相关基线证据），exit 1；精确复现`ValueError: mutable default <class 'mappingproxy'> ... inputs ... default_factory`。没有额外运行完整3.11基线；PG-12后再验证此边界。
- `full-pytest`：exit 0；526.563秒；输出1633字节；末行 `1426 passed in 524.00s (0:08:44)`。完整机器路径和输出保存在仓库外证据。
- `map-strict`：exit 0；0.42秒；输出40字节；末行 `check: 0 error(s), 0 warning(s), 0 info`。完整机器路径和输出保存在仓库外证据。
- `models`：exit 0；66.167秒；输出1890字节；末行 `models: 14 passed, 0 failed`。完整机器路径和输出保存在仓库外证据。
- `.venv/bin/python scripts/install_physicsguard_skills.py --plan --json`：exit 0；0.083秒；status passed，10个成员；完整输出在仓库外。
- `.venv/bin/python -m physicsguard.cli hierarchy evaluate <故障示例配置> <故障观测>`：exit 0；输出8875字节；audit_pass false，保留增益族后续建议并定位反馈块；完整输出在仓库外。

## 调度适配

协调者确认首批PG-01–05无LW-09实际源码依赖，且基线已冻结、依赖为隔离的FlowGuard基线；因此授权首批提前并行。PG-06及以后仍以LW-52与新版FlowGuard完成信号为硬屏障。

## 动作记录


### PG-01 修复用户项目路径造成的采用与闭包失败

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> native-probes`：exit 0；1.969秒；project adopt: status pass/errors []; copied user-project closure: passed; all exit 0。
- `python <本动作核验脚本> targeted-tests`：exit 0；3.714秒；19 passed in 2.17s。
- 适配：root授权首批提前，不再等LW09；无跨仓库实际源码依赖，仍使用基线FG隔离环境。

### PG-02 仅由超阈值残差触发增益和平衡后续建议

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> native-probes`：exit 0；2.637秒；clean: audit_pass true / empty followups; fault: audit_pass false / native gain-family followup preserved; both exit0。
- `python <本动作核验脚本> targeted-tests`：exit 0；20.3秒；34 passed in 18.34s。
- `python <本动作核验脚本> dependent-tests`：exit 0；24.394秒；23 passed in 22.00s。

### PG-03 修复快速开始命令

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> quick-start`：exit 0；1.723秒；README 两处命令正确，真实 CLI exit 0，保留 pitch_rate_feedback 诊断。

### PG-04 更新六条维护规则

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> rule-boundary`：exit 1；0.09秒；AssertionError。
- `python <本动作核验脚本> rule-boundary-corrected`：exit 0；0.058秒；六条维护规则已替换，物理规则保持，最低版本仅在 test extra 声明。
- `python <本动作核验脚本> map-read`：exit 0；0.521秒；  Explicit external-tool example helper scripts。
- `python <本动作核验脚本> map-change`：exit 0；0.606秒；run: python -m pytest -q tests/test_workflow_governance.py。
- `python <本动作核验脚本> workflow-tests`：exit 0；2.475秒；8 passed in 0.32s。
- 适配：首次仓库外格式断言误设 TOML 缩进而失败，修正核验脚本后重验，保留失败原日志。

### PG-05 合并重复物理规则

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> rule-deduplication`：exit 0；0.046秒；57 []；post_check=1；Map-based=1；假设卡片与维护块逐字保留。
- 提交后完整检查：`python -m pytest -q`：exit 0；1427 passed in 510.44s (0:08:30)；命令总耗时 512.682 秒。检查结束后仅补记本行，无业务源码变化。


### PG-06 删除重复模型代码账本

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> map-check`：exit 0；0.525秒；check: 0 error(s), 4 warning(s), 0 info。
- `python <本动作核验脚本> collect`：exit 0；3.002秒；1424 tests collected in 1.28s。
- `python <本动作核验脚本> reference-scan`：exit 0；0.056秒；仅剩保留到 PG38 的文档3行。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 适配：仓库外提交辅助器首次重复暂存已由 git rm 暂存的路径而停止；改为仅暂存本动作尚存文件并校验已暂存路径集合，无产品改动或检查失败。

### PG-07 删除永久阻断的语义账本并保留真实模块行为

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> map-check`：exit 0；0.469秒；check: 0 error(s), 4 warning(s), 0 info。
- `python <本动作核验脚本> physical-behavior`：exit 0；3.016秒；58 passed in 0.20s。
- `python <本动作核验脚本> maintenance-tests`：exit 0；5.342秒；11 passed in 3.85s。
- `python <本动作核验脚本> reference-scan`：exit 0；0.061秒；仅剩清单授权后续处理的三个历史/常量引用。
- `python <本动作核验脚本> collect`：exit 0；2.87秒；1181 tests collected in 1.20s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-08 移除路由胶囊与文本生成锁定

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> map-check`：exit 0；0.477秒；check: 0 error(s), 4 warning(s), 0 info。
- `python <本动作核验脚本> installer-plan`：exit 0；0.089秒；见同编号JSON/日志中的结构化结果。
- `python <本动作核验脚本> consumer-tests`：exit 0；3.637秒；19 passed in 1.63s。
- `python <本动作核验脚本> reference-scan`：exit 1；0.08秒；UnicodeDecodeError: 'utf-8' codec can't decode byte 0xcb in position 0: invalid continuation byte。
- `python <本动作核验脚本> reference-scan-binary-safe`：exit 0；0.083秒；技能、脚本、源码、地图和现行文档无胶囊/生成器残留。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 适配：外部残留扫描首次将既存缓存按文本解码失败，改为二进制安全搜索后重验；未删除缓存或改产品行为。

### PG-09 移除技能精确版本阻断门禁

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> native-install`：exit 0；0.367秒；CLI help、安装计划、临时HOME安装及复核全部通过；残留仅预定退役测试1行。
- `python <本动作核验脚本> installer-tests`：exit 0；2.562秒；15 passed in 0.87s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-10 移除契约与执行证据的精确版本降级

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> native-version-compatibility`：exit 0；2.31秒；旧版本标记与当前契约均 pass；无版本降级残留；示例字节未改。
- `python <本动作核验脚本> contract-tests`：exit 0；19.028秒；22 passed in 17.21s。
- `python <本动作核验脚本> blueprint-tests`：exit 0；31.742秒；108 passed in 29.97s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 提交后完整检查：`python -m pytest -q`：exit 0；1118 passed in 133.23s (0:02:13)；命令总耗时 135.071 秒。检查结束后仅补记本行，无业务源码变化。

### PG-11 删除十技能的重复深度与模板参考

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> references-plan`：exit 0；0.164秒；两份重复参考无残留，10成员真实安装计划 passed。
- `python <本动作核验脚本> consumer-tests`：exit 0；3.501秒；16 passed in 0.69s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-12 删除模板选择器与目的目录

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> exports-references-py311`：exit 0；2.391秒；残留扫描零命中；真实3.11包导入与单个版本测试通过；不宣称3.11全套已跑。
- `python <本动作核验脚本> map-check`：exit 0；0.653秒；check: 0 error(s), 5 warning(s), 0 info。
- `python <本动作核验脚本> collect`：exit 0；2.985秒；1105 tests collected in 0.98s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 适配：另用真实3.11做受影响导入边界复核及不加载无关conftest的单个版本测试；仅最小伴随环境，不声称3.11全套已通过。

### PG-13 删除纯目的证明模块并保留领域模型

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> map-check`：exit 0；0.509秒；check: 0 error(s), 5 warning(s), 0 info。
- `python <本动作核验脚本> collect`：exit 0；3.911秒；1070 tests collected in 1.47s。
- `python <本动作核验脚本> exports-references-flows`：exit 0；2.052秒；exports ok；残留零命中；仅保留三个功能流程。
- `python <本动作核验脚本> models`：exit 0；92.039秒；models: 13 passed, 0 failed。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-14 退役重复闭合技能并保留诊断结论边界

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> references-plan`：exit 0；0.127秒；技能无退役闭合步骤，9成员安装计划 passed；预测与开放缺口边界保留。
- `python <本动作核验脚本> map-check`：exit 0；0.534秒；check: 0 error(s), 6 warning(s), 0 info。
- `python <本动作核验脚本> consumer-tests`：exit 0；4.547秒；16 passed in 0.90s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-15 删除重跑所有门禁的项目闭合命令

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> map-check`：exit 0；0.706秒；check: 0 error(s), 9 warning(s), 0 info。
- `python <本动作核验脚本> exports-cli-references`：exit 0；2.144秒；exports ok；退役CLI exit2且明确invalid choice；剩余引用均为授权后续处理/数据取值。
- `python <本动作核验脚本> focused-tests`：exit 0；50.031秒；70 passed in 47.05s。
- `python <本动作核验脚本> collect`：exit 0；3.939秒；1043 tests collected in 1.55s。
- `python <本动作核验脚本> models`：exit 0；46.874秒；models: 11 passed, 0 failed。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 提交后完整检查：`python -m pytest -q`：exit 0；1043 passed in 105.43s (0:01:45)；命令总耗时 108.593 秒。检查结束后仅补记本行，无业务源码变化。

### PG-16 移除采用记录路线并保留预检与输入审查

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> exports-cli-plan-references`：exit 1；0.373秒；见同编号JSON/日志中的结构化结果。
- `python <本动作核验脚本> exports-cli-plan-references-corrected`：exit 0；1.584秒；exports ok；退役CLI exit2；preflight pass；8成员计划passed；仅剩授权后续文档2行。
- `python <本动作核验脚本> map-check`：exit 0；0.526秒；check: 0 error(s), 9 warning(s), 0 info。
- `python <本动作核验脚本> focused-tests`：exit 0；14.052秒；32 passed in 12.53s。
- `python <本动作核验脚本> collect`：exit 0；3.1秒；1040 tests collected in 1.09s。
- `python <本动作核验脚本> active-scan-journal-boundary`：exit 0；0.145秒；active仅2条授权后续文档引用；原始扫描另有1条SLIM历史，原文保留且已独立归档。
- `python <本动作核验脚本> models`：exit 0；42.813秒；models: 10 passed, 0 failed。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 适配：根代理统一规则：日志为历史，保留原命令摘要；现行产品残留扫描仅额外排除根SLIM_LOG.md，原始grep与日志单独命中保存外部，不扩大文档或目录豁免。

### PG-17 删除证据注册技能入口与重复登记步骤

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> references-plan`：exit 0；0.118秒；技能现行引用零命中；7目录与真实安装计划7成员一致且passed。
- `python <本动作核验脚本> consumer-tests`：exit 0；2.83秒；16 passed in 0.74s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-18 删除六条普通路线的强制蓝图投影要求

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> text-yaml-plan`：exit 0；0.192秒；yaml ok；6条普通路线无强制投影残留，原用途说明与安装计划均通过。
- `python <本动作核验脚本> consumer-tests`：exit 0；2.405秒；16 passed in 0.51s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-19 用普通移交文字替换路由身份术语

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> text-scan`：exit 0；0.039秒；仅AI路线保留PG26将重写的2处协调措辞；六条实际路线保留非通过/预测边界。
- `python <本动作核验脚本> consumer-tests`：exit 0；1.839秒；6 passed in 0.23s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。

### PG-20 删除单独重算收据命令并保留验证计算

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> native-cli-references`：exit 1；0.117秒；AssertionError。
- `python <本动作核验脚本> native-cli-references-py312`：exit 0；2.143秒；原生validation run pass；退役命令exit2；仅1条授权后续技能引用；workflow及三节边界正确。
- `python <本动作核验脚本> focused-tests`：exit 0；23.509秒；24 passed in 21.42s。
- `python <本动作核验脚本> collect`：exit 0；3.518秒；1039 tests collected in 1.42s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
- 适配：Python3.12 argparse单候选输出不带引号，外部核验改为检查退役receipt无效、唯一run和exit2；原失败输出保留，产品不改。
- 提交后完整检查：`python -m pytest -q`：exit 0；1039 passed in 144.18s (0:02:24)；命令总耗时 146.738 秒。检查结束后仅补记本行，无业务源码变化。

### PG-21 删除重复软件地图封装命令

- 按本动作参考目的完成；验证命令和完整输出保存在仓库外同编号证据（机器路径不写入产品记录）。
- `python <本动作核验脚本> native-cli-references`：exit 0；0.18秒；退役命令exit2且invalid choice；现行产品重复地图封装无残留，历史扫描另存。
- `python <本动作核验脚本> map-check`：exit 0；0.553秒；check: 0 error(s), 9 warning(s), 0 info。
- `python <本动作核验脚本> focused-tests`：exit 0；16.821秒；12 passed in 14.97s。
- `python <本动作核验脚本> collect`：exit 0；3.524秒；1036 tests collected in 1.45s。
- 适配：XR独立复核仅依赖隔离baseline工具链，root授权提前并行；PG63后暂停复核，不改变动作目的与验收。
