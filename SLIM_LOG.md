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
