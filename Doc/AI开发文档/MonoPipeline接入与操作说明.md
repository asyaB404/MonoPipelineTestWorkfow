# Mono Pipeline 接入与操作说明

<!-- 创建日期：2026-11-13（Asia/Shanghai）；创建人：Codex；功能：说明 Mono Pipeline 功能测试技能的部署、项目接入、执行与收尾；适用参数：Windows、Python 3.10+、已有 Mono Development PC 包及经确认的测试用例和操作授权。 -->

Mono Development PC 包 = 使用 Mono 脚本后端并带 Development 能力的 Windows 测试包。Player = 正在运行的游戏进程。目标记录 = 将实际 Player、构建身份、许可和允许操作范围绑定到本轮的本地配置。本文说明如何部署和使用仓库中的 `mono-pipeline-functiontest` 技能；它不替代原测试用例，也不承诺特定 passed 数或运行耗时。

技能目录：`.agents/skills/mono-pipeline-functiontest`。父 Workflow `functiontest-workflow` 及其公共子技能可继续使用，但父 Workflow 文件不需要修改；Mono PC 执行适配只放在本技能。

## 接入方式

### 已有可用测试包

1. 将整个 `.agents/skills/mono-pipeline-functiontest` 目录复制到目标项目的 `.agents/skills/` 下，不要挑选或重排技能目录内文件。
2. 如需从父 Workflow 启动，按项目现状部署父 Workflow 和实际会用到的公共子技能；不要用本仓库中的参考副本覆盖项目现有版本。
3. 在技能根目录执行交付核验：

```powershell
& ".\.agents\skills\mono-pipeline-functiontest\mono-pipeline-test.bat" --compact delivery-verify
```

交付核验失败时先诊断缺失、额外或摘要变化的成员。普通使用者不要运行 `delivery-refresh`，也不要手工改 `delivery-manifest.json`。清单刷新是维护者操作，必须经过维护者明确批准。

只修改 Skill、计划或报告文档时，不需要重新构建 PC 包。已有包满足运行要求时，可直接进入操作流程。

### 新项目首次接入或需要新增包能力

首次接入前确认目标 Unity 工程、备份目录及接入批准。优先使用 `unity-preview` 生成只读差异计划；审阅文件路径、GUID、现有依赖和冲突后，才可使用 `unity-apply`。应用操作要求计划摘要、单独批准和项目/工具目录之外的新备份。复制成功只证明文件写入，不代表 Unity 编译、资源管线或 Player 验收成功。

仅同 GameClient/GameFramework 框架按现有迁移说明合并构建菜单及依赖；逐文件比较，不覆盖目标工程的 `Packages/manifest.json`、锁文件、业务源码或已有 `.meta` 身份。菜单依赖及运行时边界见[编辑器依赖与迁移说明](MonoPipeline编辑器依赖与迁移.md)。其他 Unity 框架不能直接套用这组适配源码。

只有以下情况才考虑重新构建 PC 包：首次接入公共运行时源码；修改构建菜单或 GameFramework 构建依赖；修改运行时预加载逻辑；或测试确实依赖当前包不具备的新能力。仅修改技能脚本、测试计划、执行说明或报告流程不需要重打包。运行时源码变更须进入目标工程原有程序集和资源构建流程，并用新构建重新验收。

## 前置条件

- Windows 环境及 Python 3.10+。`mono-pipeline-test.bat` 使用本机 `py -3`，也可通过 `MONO_PIPELINE_PYTHON` 指向现有 Python；技能不携带解释器，不负责安装环境。
- 已构建的 Windows Mono Development PC 包、真实 EXE/PID、完整测试用例和明确的测试范围。运行现有包不要求 Unity Editor、Unity CLI 或 Unity MCP。
- 实际授权必须覆盖本轮会执行的行为。包内迁移许可不是 Player 操作许可；启动/附加、只读脚本、业务动作、日志和截图等权限应按真实授权记录，不推定、不自动扩大。
- 输出目录应是本轮新目录，不能与 Skill、游戏安装目录或原始用例混用。路径长度由 `output-check` 和 `init` 检查。

与父 Workflow 协作时，沿用父流程已经选定的来源、完整用例、范围、授权和真实计时，不重复生成或另建父上下文。由父流程传入的 `workflow-timing`、父/子 ID 和功能编号必须保持原值；直接调用则不传父绑定参数，也不补造父记录。

## 执行流程

### 1. 核验技能和准备本轮输入

先执行 `delivery-verify`。准备完整原用例、真实 PC 包及测试授权；Agent 根据原始材料整理内部输入文件，用户不需要手写底层 JSON。已有完整用例时不重复生成。确认输出位置后先运行 `output-check`，不通过时调整新输出根目录，不要改动已创建或冻结的旧轮。

### 2. 准备 Player 并初始化

明确本轮要使用的 EXE 和进程。默认复用已运行的明确目标；未运行时由执行 Agent 按授权启动，不默认杀进程、重启或另开第二实例。启动就绪采用只读轮询，默认总预算 30 秒：立即检查，已就绪即继续；超时不自动延长或重启。该预算仅用于启动就绪判断，不改变业务动作和连接超时。

由 Agent 根据真实许可准备权限记录，并调用 `target-prepare` 生成目标记录。该命令只核对身份和公开配置，不连接 Player，也不代表附加或测试成功。随后以完整用例、目标记录和新输出根调用 `init`，再用其返回的本轮根目录执行一次 `attach`。附加失败时先检查 EXE/PID、构建身份、端口、描述符和许可，不伪造 PID 或绕过权限核验。

### 3. 登录与业务可达检查

同框架中台登录固定点击路径为：

```text
GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame/LoginBtns/LoginButton
```

按已有授权点击一次该按钮；新帧确认 `UI_LoginGame` 不存在或不再激活，即视为登录完成。不重复探查协议开关、SDK 或主界面。登录成功不等于目标业务功能已开放，仍须通过共享准备链路确认本轮主要被测功能可达。

共享链路按需执行 `chain-start`、必要的真实准备与独立比较，确认业务能力门禁通过后执行 `chain-end`。入口点击必须真实执行并在动作后新帧验证；GM、资源到账或大厅入口可点不能单独证明目标功能可达。资源准备遵循原用例和授权，优先保留零资源、边界及计次初态，再按实测差额最少补充。只有用户明确授权换号且提供下一个账号 ID/顺序时，才可在初始化前换号；不默认每例换号，不把旧轮状态迁移到新账号。

### 4. 预检并执行用例

按原用例索引、前置条件、步骤和预期生成单例或多例计划。执行前用 `plan-check` 做本地静态检查，并审阅 `planning_summary`、原文绑定、动作覆盖和未验证路径；它不连接 Player，也不代表业务通过。

稳定批次优先一次 `run-suite`，单个用例使用 `run-case`。这样可复用一次连接，避免每个只读/比较步骤都重新启动 CLI。每例仍需独立开始、按原步骤执行并唯一收尾。现场探索完成后将已验证计划纳入批次，不另造执行器或功能专用通过规则。

动作执行遵循“最新 before → 单次动作 → 新帧读取 → 独立比较”。不同阶段不能用最终快照证明早期状态；必要的完成等待应在到达该状态的动作之后进行。只读描述不自动要求动作，明确要求点击、导航或业务操作时则必须执行并验证。

`status` 用于查询本轮和剩余用例。批次等待超时先查原 run 状态；仅当本轮未冻结、无未决动作且用例从未开始时，才继续 `remaining_case_ids`。同一 Case ID 不重放；发生错误时新建请求文件并使用新 ID，已登记来源、计划和请求保持不变。

### 5. 收尾与报告

按本轮真实状态执行 `close`，再运行 `audit`，通过后生成唯一 `report`。报告来自本轮 journal；缺 final 的用例必须保留真实中断原因和未执行步骤，不补假结果。父 Workflow 模式按原父子计时约定收尾。统计转换、用量读取和上传由对应公共子技能按本轮授权处理；Mono 宿主不自动上传，也不重复生成报告。

结果状态按证据判定：`passed` 要覆盖全部原前置、步骤和预期；`failed` 必须有有效反例；`blocked` 仅用于真实权限、环境、关键前置缺失或用户停止；`test_inconclusive` 用于已尝试但证据不足。未执行不能伪装成 blocked 或 passed。

## 常用命令

以下为直接 CLI 调用示例。请将变量替换成当前机器的真实路径；运行 Agent 通常会负责生成内部配置和请求文件。`--compact` 放在子命令之前，仅减少重复标准输出，不删减 journal、末样本、错误或退出码。

```powershell
$SkillRoot = 'D:\Project\.agents\skills\mono-pipeline-functiontest'
$OutputRoot = 'D:\FunctionTest\feature-run'
$Cases = 'D:\FunctionTest\input\cases.json'
$Target = 'D:\FunctionTest\private\target.json'
$PlayerExe = 'D:\Build\Game.exe'
$ProcessId = 12345
$Permission = 'D:\FunctionTest\private\permission.json'

& "$SkillRoot\mono-pipeline-test.bat" --compact delivery-verify
& "$SkillRoot\mono-pipeline-test.bat" --compact output-check --output $OutputRoot
& "$SkillRoot\mono-pipeline-test.bat" --compact target-prepare --exe $PlayerExe --pid $ProcessId --permission-record $Permission --output $Target
& "$SkillRoot\mono-pipeline-test.bat" --compact init --cases $Cases --target $Target --output $OutputRoot
```

`init` 返回本轮根目录后，后续命令都使用该根目录：

```powershell
$RunRoot = 'D:\FunctionTest\feature-run\<init返回的本轮根目录>'
$Plan = 'D:\FunctionTest\input\suite-plan.json'

& "$SkillRoot\mono-pipeline-test.bat" --compact attach --run $RunRoot
& "$SkillRoot\mono-pipeline-test.bat" --compact plan-check --run $RunRoot --plan $Plan
& "$SkillRoot\mono-pipeline-test.bat" --compact run-suite --run $RunRoot --plan $Plan
& "$SkillRoot\mono-pipeline-test.bat" --compact status --run $RunRoot
```

正式收尾的 `close` 可不带请求文件；只有需要记录本次关闭原因或中断事实时，才传本轮新建且未登记过的请求文件。实际测试应由 Agent 按命令帮助和技能契约生成，不能复制旧请求重放：

```powershell
& "$SkillRoot\mono-pipeline-test.bat" --compact close --run $RunRoot --request 'D:\FunctionTest\private\close-request.json'
& "$SkillRoot\mono-pipeline-test.bat" --compact audit --run $RunRoot
& "$SkillRoot\mono-pipeline-test.bat" --compact report --run $RunRoot
```

各命令字段以 `mono-pipeline-test.bat --help` 和对应子命令的 `--help` 为准。手工直接调用前应先阅读技能的 `SKILL.md` 及相应 references；不要仅凭本页命令示例生成授权或业务动作。

## 常见问题处理

| 现象 | 处理 |
| --- | --- |
| `delivery-verify` 报成员不一致 | 停止运行，核对变化来源并保存差异。普通使用者不要刷新清单或回退本地改动。 |
| Player 30 秒内未就绪 | 如实记录并检查启动状态；不自动延长、不重启、不执行后续业务动作。 |
| `target-prepare` 或 `attach` 失败 | 核对实际 EXE/PID、构建身份、许可及连接信息；不伪造目标、不重用旧轮目标。 |
| 功能入口或账号状态不满足 | 检查真实功能门禁。仅按明确授权和账号顺序换号；否则停止受影响用例并记录真实状态。 |
| 已登记用例或请求内容有误 | 保留原文件；创建新文件并使用新 ID。不得改写已登记内容以解冻或重放。 |
| 批次中断或命令等待超时 | 先查 `status` 和活动用例；不得重放已开始用例或未知结果的动作。 |
| 只做 Skill/文档调整 | 不需要重打 PC 包；交付核验和离线隔离测试不能替代 CyouCode 实机验收。 |

## 修改记录

2026-11-13，Codex：新增 Mono Pipeline 技能接入、现有包执行、首次工程迁移、登录、计划执行、报告收尾和常见问题说明；未修改父 Workflow、Skill 执行代码、游戏业务源码或 PC 包。
