---
name: unity-functiontest
description: 当任务需要通过 MCP 工具驱动 Unity 功能测试时使用——包括 PlayMode 启动/停止、UI 页面打开/关闭、按钮点击、动画等待、场景流转、截图取证，并产出 `Doc/AI开发文档/output/{feature_id}/{run_dir}/` 下的 markdown 测试报告。采用纯 MCP 编排模式：不生成 C# 测试方法，每一步通过 MCP 工具调用完成。不用于纯逻辑/数据/公式验证——那属于 `unity-test`。
---

# Unity Function Test

## 概述
本 skill 用于执行本项目的 Unity 功能测试，运行模式是纯 MCP 编排：不生成 C# 测试脚本，而是直接通过 MCP 工具逐步完成功能流程验证。典型流程包括：从 `Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}/` 读取完整输入，进入 PlayMode、打开页面、等待状态就绪、定位 UI 元素、执行点击、读取状态、截图取证、查询日志、退出 PlayMode，并最终产出报告到 `Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-unity-functiontest-report.md`，其中 `run_dir={feature_id}-{sequence}`，例如 `hero-list-0001`。逐步执行多次 MCP 工具调用是本 skill 的正常工作方式，不是阻塞原因；不得因为“无法一次性连续执行完整 MCP 流程”“需要大量运行时查询/交互/记录”而要求用户选择处理方式或提前退出。

本 skill 是执行导向的，不负责代码的纯逻辑/数据测试，也不负责服务端或协议验证。

本 Skill 中未带项目根目录前缀的 `references/...` 和 `scripts/...` 均相对于本文件所在目录解析；跨 Skill 文件使用 `../{skill-name}/...`，不得把它们拼接到项目根目录后再读取。

## Skill 时间记录（强制）

本 Skill 必须遵守 `../functiontest-report-json/references/skill-timing-contract.md`。完整执行确定本轮 `run_dir` 后、编译和任何 PlayMode 操作前，立即调用 `../functiontest-report-json/scripts/skill_timing.py start`，使用 `{run_dir}-skill-timing.json` 保存返回的 `invocation_id`；测试失败、阻塞、用户中止或工具异常时也必须调用 `end`。workflow 调用的启动前置阶段 A/B 只复用 workflow 的 timing 上下文，不单独创建 timing 文件；完整执行的 `skill_end` 必须在退出 PlayMode、证据/覆盖扫描完成后写入，并且必须早于 Markdown 报告渲染。

本 Skill 的业务时间只来自自己的 `skill_start → skill_end` 记录。没有父级时，作为根 Skill 按统一规则在最终上报时扣除环境过滤时间；由 `functiontest-workflow` 调用时，使用 workflow 传入的 timing 文件和 `parent_invocation_id`，只保留本 Skill 的原始起止时间，不扣除会话环境变量，由父 Workflow 统一扣除，也不得单独转换或上传。PlayMode 实际启停不再额外写入开始/结束 run-log 记录，也不参与 Skill、Markdown 或 JSON 上报时长。

## 单独调用后的 JSON 上报

当用户直接调用 unity-functiontest，而不是由 functiontest-workflow 编排时，本 Skill 在本轮 Markdown 报告生成后必须继续完成 JSON 和用量收口，并按全量用例状态门禁决定是否上报：

1. 调用 check-cyoucode-spend 读取当前 Token 和消耗。
2. 调用 functiontest-report-json，将本轮明确的 Markdown 报告和 `{run_dir}-skill-timing.json` 转换为 JSON，并固定传入操作类型“独立Unity功能测试”、`--skill-name unity-functiontest` 和 `--timing-file`。
3. 将最终 JSON 交给 functiontest-json-upload；若全部用例为 `blocked` 或全部为 `test_inconclusive`，保留报告和 JSON 并跳过上传。

独立 Unity 功能测试必须保留本轮真实的 passed、failed、blocked 和 test_inconclusive 结果；不能使用 operation-only 模式，也不能把测试统计归零。若本 Skill 是由 functiontest-workflow 内部调用，则不在此处单独转换或上传，由 functiontest-workflow 统一使用“主动测试工作流”并按全量用例状态门禁决定是否上报。

## 适用场景
在以下情形使用本 skill：
- 用户提供了功能测试文档，并要求真正执行测试
- 任务需要验证 UI 页面、按钮交互、动画、场景切换、视图状态
- 任务需要通过 MCP 工具执行测试过程并保留证据
- 任务需要产出功能测试报告

以下情形不要使用本 skill：
- 代码的纯逻辑/数据/公式验证
- 只是讨论测试策略，不要求执行
- 输入不完整，无法形成功能测试步骤

## 所需输入
必须提供：
- 功能测试需求、测试用例文档，或测试文档路径

例外：当 `functiontest-workflow` 以启动前置阶段 A（`preflight_stage=vision`）或阶段 B（`preflight_stage=repair`）调用本 Skill 时，不需要测试文档，也不得执行测试；阶段 B 需要接收阶段 A 已返回的状态。正式执行阶段必须接收完整测试用例文件路径和已确认的启动前置状态。

可选提供：
- `feature_id`。若用户未显式提供，应根据任务标题、功能名或测试目标推断一个简短 kebab-case 标识（例如“角色升级功能测试”可推断为 `role-upgrade`），不要仅因缺少 `feature_id` 阻塞执行。

可接受的输入形式：
- 自由文本描述
- markdown 标题 + 步骤列表
- markdown 表格
- 纯文本编号步骤

可选辅助信息：
- 相关 UILogic / AutoGen 路径
- 已知 UIID 列表
- 原型图

## 启动前置交互（所有调用方式强制执行）

无论本 Skill 是被用户直接调用，还是由 `functiontest-workflow` 调用，识图能力、截图开关、效果图对比开关和修复模式的问题文本、判断规则及结果归属都由本 Skill 负责。所有启动前置都必须在编译和任何 PlayMode 操作前完成；workflow 的阶段性调用只执行指定的启动前置，不启动完整测试。

- 直接调用时：本 Skill 在记录 `skill_start` 后，按“识图能力/截图开关/效果图对比开关→修复模式”的顺序一次完成两个阶段的问题。
- 由 `functiontest-workflow` 调用时：workflow 先完成测试用例来源和路径确认，必要时完成用例生成；最终测试用例路径确认后，再依次调用本 Skill 的启动前置阶段 A/B——阶段 A 依次询问识图能力、截图开关和效果图对比开关，阶段 B 只询问修复模式；workflow 不复制问题文本。最终执行调用必须接收阶段 A/B 返回的状态，不能再次询问。
- 启动前置阶段 A/B 只负责询问和返回状态，不执行编译、PlayMode、用例测试、报告生成或日志上传，也不单独形成一次测试上报。

### 识图能力、截图开关与效果图对比开关（启动前置阶段 A）

1. **先进行实际识图探测，不得根据模型名称、模型自述或历史结论猜测。** 使用当前会话可用的图片读取/图片附件方式，将本 Skill 的 `assets/vision-probe.png` 作为图片内容传入；该方式必须与后续读取 Unity 截图的图片输入链路一致。只根据图片视觉内容回答其主色，不得把该 PNG 当原始数据读取、解析颜色值、根据文件名猜测，或通过脚本读取图片内容。
2. 图片确实进入当前 AI 上下文且能正确识别主色时，写入 `vision_capability=supported`；图片未能传入、当前会话没有图片读取入口、读取失败、回答错误或无法确认时，统一写入 `vision_capability=unknown`。只有运行环境提供明确且可验证的“不支持图片输入”能力标识时，才写入 `unsupported`。探测的目的是确认“当前会话可实际看图”，不是确认模型理论上是否具备视觉模型能力。
3. 本轮只保存一次 `vision_capability=supported|unsupported|unknown`、`screenshot_enabled=true|false` 和 `effect_diff_enabled=true|false`。`unknown` 与 `unsupported` 走“不具备识图能力”分支；探测图片本身不写入 run-log、报告或上报 JSON，也不计入功能测试截图。
4. 不具备或无法确认识图能力时，必须逐字使用以下固定询问（不得改写、缩减、摘要或省略）：

```text
当前选择AI模型不具备或无法确认识图能力，无法开启截图功能进行UI识别和截图取证。选择“继续”将关闭截图功能，普通功能测试仍会继续，但仅能通过图片确认的用例将无法判定；选择“停止”将结束本次测试，不生成报告、不上传日志。是否继续？
1. 继续
2. 停止
```

   - 选择“继续”时固定写入 `screenshot_enabled=false`，后续不得调用截图工具、读取截图或把截图作为本轮证据。
   - 选择“停止”时闭合本 Skill 的 `skill_end` 并保留中止原因；由 `functiontest-workflow` 调用时还必须通知 workflow 闭合根 timing，禁止补造报告、JSON 或上传记录。
5. 具备识图能力时，必须逐字使用以下固定询问（不得改写、缩减、摘要或省略）：

```text
当前选择AI模型具备识图能力，是否需要开启截图功能以增强测试能力？开启后会在关键测试状态采集截图，增强对UI状态、遮挡和显示异常的判断，但会增加截图文件、调用次数和测试耗时；不开启则不采集截图，普通功能测试仍通过运行时节点、业务状态、evaluate返回结果和日志进行，不影响普通功能测试，但仅能通过图片确认的用例将无法判定。
1. 开启
2. 不开启
```

   - 选择“开启”时固定写入 `screenshot_enabled=true`。
   - 选择“不开启”时固定写入 `screenshot_enabled=false`。

6. 截图功能选择完成后，只有在 `screenshot_enabled=true` 且 `vision_capability=supported` 时，才继续逐字使用以下固定询问（不得改写、缩减、摘要或省略）；否则固定写入 `effect_diff_enabled=false`，不询问、不读取 `UILogicManager.xlsx` 中的效果图路径、不调用 `ui-image-diff`：

```text
当前选择AI模型具备识图能力且已开启截图功能，是否开启效果图对比功能？开启后，测试会根据当前界面对应的基准效果图，将实际截图与基准图进行对比，帮助发现按钮、页签、文字、图标、布局、遮挡和截断等界面显示差异；但会增加图片分析调用次数和测试耗时，且基准图缺失或界面状态不一致时可能无法比较。不开启则不读取基准效果图、不执行效果图对比，不影响普通功能操作、状态断言和测试结论，但无法额外发现仅通过图片才能识别的界面显示问题。是否开启？
1. 开启
2. 不开启
```

   - 选择“开启”时固定写入 `effect_diff_enabled=true`；选择“不开启”时固定写入 `effect_diff_enabled=false`。
   - 该问题只询问一次。绝对路径失败、相对路径精确和模糊查找均未找到有效基准图时，提示检查路径，跳过本 UI 的效果图对比截图并记录原因，不改变普通功能测试 verdict。

### 修复模式选择（直接调用或启动前置阶段 B）

直接调用时完成上述截图和效果图对比分支后，必须继续逐字使用以下固定询问（不得改写、缩减、摘要或省略）；由 workflow 调用时，阶段 B 只使用以下固定询问，不重复询问识图能力、截图开关或效果图对比开关：

```text
发现 bug 时是否允许修改代码？
1. 允许：按本 Skill 自身规则边测试边修改，并在报告中记录修复内容和验证结果
2. 只读不修：不修改项目业务代码、业务资源、业务配置或项目中已有的测试代码；`Assets/.../Test` 下已有的 `TestHelper`、`FunctionTestLogWriter` 等文件不得改动。只允许 AI 本轮创建并在结束后删除的临时编排/辅助代码，以及 Skill 文档/reference 和本轮日志报告产物
```

选择“允许”时保存 `repair_mode=allow_fix`；选择“只读不修”时保存 `repair_mode=read_only`。直接调用时两个阶段的问题都完成后才能进入编译和 PlayMode；workflow 调用时，阶段 A 和 B 的结果都返回并合并后才能进入正式执行。后续测试阶段不得再次调用提问工具。

## 修复模式

本 Skill 的修复模式统一由上述启动前置确定，直接调用和 workflow 调用使用相同规则；workflow 只能传递本 Skill 已返回的结果，不能自行判断或覆盖：

- **允许修改代码**：沿用本 skill 的边测边修边复测规则。执行中出现 `failed` 用例或编译失败时，先定位根因并修复，再重新编译和复测；修复内容写入报告。
- **只读不修**：测试流程进行期间不修改项目业务代码、业务资源、业务配置，以及项目中已有的测试代码。`Assets/.../Test` 下已有的 `TestHelper`、`FunctionTestLogWriter` 等文件必须保持不变；测试结束后的代码修改属于后续工作，不作为本轮测试步骤。执行中如需临时编排、临时脚本或临时辅助代码，可由 AI 在本轮创建、使用并在结束后删除；Skill 文档/reference 和本轮产物仍可按规则更新。最终报告必须照常生成，并如实保留 `passed / failed / blocked / test_inconclusive`。
- 历史文案中的“只测不修/不允许修改代码”均按本条“只读不修”解释；只有只读不修模式禁止当前流程内修改业务代码，允许修改模式必须按本节的边测边修边复测链路执行。

只测不修模式下，本 skill 中所有“必须修复后再继续/再生成报告/再交付”的规则均改为“必须记录失败证据和建议修复方向后继续生成报告”。该模式不是补造通过结果，也不是跳过失败记录；失败用例仍然必须以真实证据写入 run-log 和 Markdown 报告。

## 四种用例 verdict

每条 functional 用例最终只能使用以下四种状态：

- `passed`：测试前置条件满足，操作完成，并有独立于操作返回值的运行时结果证据证明实际结果符合预期；证据可以是业务状态、UI 语义状态或能明确对应预期的最终截图。同步操作可以在同一次 `evaluate` 中完成操作和结果读取，异步操作仍需操作后独立轮询。
- `failed`：测试条件已经构建且可以执行，但实际结果明确违反预期；操作回执本身不能单独判定 passed。
- `blocked`：当前用例本应可测，但被环境不可用、关键前置条件不可用，或失败用例造成的强关联依赖阻断，无法继续执行。
- `test_inconclusive`：测试流程可以运行，但测试账号、客户端工具或当前服务环境无法合理构造目标条件，例如异常刷新、网络故障、并发竞争、服务端竞争条件等；该状态不是产品失败，也不是运行环境阻断。

分类边界固定为：上游根因用 `failed`，受其直接影响而无法执行的下游用例用 `blocked`；独立场景无法构造用 `test_inconclusive`。`test_inconclusive` 必须出现在 Markdown 报告和 run-log 中，并在日志上报 JSON 中计入 `invalid_case_count`；不计入 `failure_case_count`。

## 硬性约束
- **启动前必须做代码编译检查**：进入 PlayMode 前先调用 `scripts/focus_unity_window.ps1 -ProjectRoot <当前工作区目录>` 尝试定位、置前并验证当前项目的 Unity 窗口，然后按结果处理：脚本输出 `UNITY_FOCUSED`（退出码 0）时立即调用 `mcp__mymcp__execute_compile`；脚本输出 `UNITY_FOUND_FOCUS_FAILED` 或 `UNITY_FOUND_NO_WINDOW`（退出码 4/3）但已确认找到本项目 Unity 进程时，仍立即尝试调用一次 `execute_compile`，不得把前台失败直接当成编译失败；只有脚本输出 `PROJECT_ROOT_INVALID` 或 `UNITY_NOT_FOUND`（退出码 1/2）时才禁止调用编译。首次编译无响应或超时后，再执行一次“重新聚焦→`execute_compile`”重试；获得明确的编译成功或编译错误回执后不重复重试。编译失败时立即终止测试执行，直接生成报告并注明完整报错信息，不进入 PlayMode、不执行任何用例。修复后每次重新编译也必须重复这套“尝试聚焦→编译→无响应时一次重试”流程。
- 全部功能测试在 PlayMode 下执行
- 本 Skill 启动前置必须确定 `vision_capability`、`screenshot_enabled` 和 `effect_diff_enabled`。本条优先于本文件后续所有截图取证、截图识别、截图模拟点击和截图兜底条款：`screenshot_enabled=false` 时不得调用截图工具、读取截图进行 UI 识别或把截图路径作为本轮证据；应使用运行时节点、业务状态、evaluate 返回结果、scene snapshot 和日志等非图片证据。只有某条用例的核心验收条件只能通过图片确认时，才将该条用例记为 `test_inconclusive`，不得因此降低其他用例覆盖率。`screenshot_enabled=true` 时，按关键测试状态按需采集截图，截图只能作为辅助证据，仍必须满足独立操作和独立断言要求。`effect_diff_enabled=false` 时，不读取效果图配置、不调用 `ui-image-diff`；`effect_diff_enabled=true` 也必须在当前 UI 实时读取到有效基准图后才执行对比。
- 每条 functional 用例按需产出场景快照、evaluate 返回结果或日志作为方式一证据；在 `screenshot_enabled=true` 且使用方式二时，才产出截图、`simulate_click` 返回结果或点击前后截图作为证据
- 证据文件路径使用 MCP 工具原样返回的路径，不复制、不移动、不统一收口
- **本轮测试完成门禁**：新的独立测试只有同时满足三项才算完成：(1) 已按最大序号 +1 创建本轮新 `run_dir`（显式复测指定目录或已开启自测自修除外；自测自修始终使用当前 run_dir）；(2) 本轮 run-log 第一条是 `setup`，中间存在编译、进场和用例执行证据，最后一次日志查询 `query_logs` 已在实际停止 PlayMode 前写入；(3) 本轮 Markdown 报告由该 run-log 渲染生成。`setup` 必须在初始化 run-log 后、编译前写入；PlayMode 实际启停不额外写入 start/stop 生命周期记录。该门禁是执行结束后的验收条件；执行前必须先创建并初始化本轮 `run_dir`、run-log、visible-log 和 known-issues，读取 known-issues/reference 后再编译、进入 PlayMode或执行用例。
- **Skill 时间门禁**：本轮必须存在已闭合的 `{run_dir}-skill-timing.json` 业务记录；`skill_end` 必须发生在报告渲染前。缺少记录时不得手工补写时间，报告只能按回退规则标注并上报。
- **阶段结果不是完成条件**：源码确认、运行时路径确认、目标 UI 已进入、下一步方向明确、已发现正确入口、已完成进场校验、已完成初始态/编辑态验证、已完成某个分组，都只是中间状态，不得回复“任务完成”“本阶段完成”并停止，也不得要求用户确认“是否继续”或“选择接下来的执行策略”。只有本轮 functional 用例按覆盖基准完成执行、报告前扫描通过、正式 Markdown 报告生成后，才允许声明本 skill 完成。
- **逐步 MCP 执行不是阻塞**：本 skill 本来就要求通过多次 MCP 调用持续推进测试。已创建 `run_dir`、编译成功或进入 PlayMode 成功之后，必须继续执行进场、用例分组、交互、记录和报告生成；不得以“只能单次工具调用逐步推进”“后续步骤较多”“完整用例集规模较大”“逐条执行会非常耗时”“无法一次性跑完整流程”为由停止、询问用户最终处理方式或要求用户重新确定执行策略。只有 MCP 工具不可用、Unity 退出/崩溃、用户明确停止、缺少必须由用户提供的输入，才允许中断。
- **禁止测试阶段调用提问工具**：识图能力、截图开关、效果图对比开关和修复模式只能在本 Skill 启动前置阶段各询问一次，且必须发生在编译和 PlayMode 前；进入正式测试后不得再调用 `Ask user question` / `request_user_input`。不得用提问工具确认是否继续、执行策略、阶段诊断、截图路径异常、用例规模较大、是否生成报告、是否上传或是否收口。遇到可继续执行的问题，直接继续执行；遇到真实阻塞，按本 Skill 的失败/blocked 规则写入 run-log 并生成报告。
- **测试资料和临时辅助代码边界**：更新 `references/{feature_id}.md`、`{run_dir}-known-issues.json`、workflow 文档和本轮报告产物，在“只读不修”中均允许；AI 临时创建的编排代码、临时脚本和临时辅助代码可以在本轮使用后删除。项目中已有的 `TestHelper`、`FunctionTestLogWriter` 及其他测试基础设施代码在两种模式下均不得修改；允许修改模式可以修改已确认根因对应的业务代码，并必须记录 `action=fix`、重新编译和复测结果。
- **离线 reference 不由本 skill 正常生成**：`../ui-quick-reference/references/{feature_id}.md` 的缺失、无效或静态结构不一致由 `functiontest-workflow` 在 Unity 测试前或测试后缺陷回刷阶段调用 `ui-quick-reference` 处理。本 skill 只读取离线 reference，并在运行时记录 `query_reference` 缺陷，不直接调用离线扫描器。
- **reference 缺失不影响完整测试**：缺少、过期或暂时无法生成 reference 只增加本轮运行时探索成本，不得减少 functional 用例执行范围，不得提前结束，不得以此将未执行用例批量标记为 `blocked`。运行时 reference 缺失时，必须在确认目标 UI 后创建初版并在测试过程中增量更新；若测试在编译、PlayMode 或进场阶段阻塞而没有运行时证据，不得伪造 reference，只记录 `runtime_reference_gap` 并继续生成报告。
- **不使用 case-map 驱动执行**：本流程不生成、不读取 `{run_dir}-case-map.json`。测试用例 JSON 是唯一输入来源，当前运行中生成的 `CaseExecutionPlan` 只在内存中供本次分组执行使用；每条 Case 的 `source_steps`、操作回执、独立断言、expected/actual 和 verdict 直接写入该 Case 的 `run-log` final record。覆盖审计只读取本轮 `run-log`，不得从历史产物或中间映射恢复操作链。
- **不需要独立写文件 MCP 工具**：本 skill 的 run-log、known-issues 和运行时 reference 落盘方式不是调用“写文件 MCP 工具”，而是在当前步骤已有的 `evaluate` C# 代码中调用现有 `CyStarRoad.Test.FunctionTestLogWriter` 的 DTO/写入入口。禁止在 evaluate、PowerShell 或 Python 临时拼接 JSON；只读不修模式下不得为了新字段修改正式 DTO，必须复用现有字段或由本轮临时编排代码承载。known-issues 仍须在初始化阶段创建并读取。
- 无证据时不得标记为"通过"
- **禁止收尾批量补造用例结果**：不得在测试结束后使用 Python/PowerShell/临时脚本/Markdown 模板循环生成或改写 `{run_dir}-run-log.json` 中的 per-case 最终 verdict。每条 functional 用例的最终记录必须来自该用例执行当下的 MCP/evaluate/click/snapshot/verify 返回结果。缺少当时记录时，必须回到执行阶段继续执行该用例；不得把“缺少记录”“reference 未生成”或“本轮探索耗时较长”当作无法继续执行的依据，也不得批量补 `blocked`。只有确认 MCP/Unity 不可用、用户停止或确实无法恢复执行时，才允许异常补 `blocked`。补 `blocked` 只能作为异常兜底，不是正常执行方式；原因必须写明“执行时未产生实时证据”，不得补记为 `passed`。每批结束立即调用 `ValidateFinalCaseGroup` 或 `ValidateFinalCaseCoverage` 检查 `case_id` 唯一性；发现重复立即停止，不重跑已完成 case，只补明确缺失 case。
- **passed 证据门禁**：任一 functional 用例标记 `passed` 时，run-log 中必须存在该 `case_id` 对应的证据映射，至少满足其一：真实 MCP 返回的证据文件路径、截图路径、scene snapshot 路径、`RunTC` 返回的断言明细、动作前后状态差异、或可复核的运行时字段断言。展示/只读类用例允许共享同一次批量状态读取，但每条 case 必须写明自己验证的字段、目标或断言结果；交互/状态变化类用例必须有自己的操作序列或状态变化证据。仅有 group summary、相同 UI 根节点 active、相同截图复用说明，不能作为该用例 passed 证据。
- **自然语言步骤的部分可执行原则（强制）**：无法自动理解全部自然语言步骤，不等于无法执行任何业务操作。`OpMap`/`SetOpMap` 只是动作复用方式，不是业务前置条件；没有 OpMap 时，仍必须按当前 Skill 通过运行时路径探查、实时状态判断、已验证的直接调用或其他现有测试入口继续执行。必须以 Case 为单位拆解每个步骤，优先匹配当前已验证的 `SetOpMap`、运行时缓存路径、reference、Logic/AutoGen 候选和已发现控件；把能可靠映射的触发、输入、选择、导航、等待、观察和状态查询真实执行，并把 `mapped_steps`、`unmapped_steps` 写入该 Case 记录。禁止因为缺少 OpMap 或部分步骤暂时无法解析，就把所有 Case 统一替换为 `[Case]|snapshot` 加 `test_inconclusive`。
- **部分映射后的 verdict 规则（强制）**：放宽的是“自然语言全部还原”的要求，不放宽业务证据要求。若已执行的真实操作和独立断言已经覆盖该 Case 的核心 expected，允许判定 `passed` 或 `failed`，对不影响核心结论的附属描述步骤记录遗漏即可；若核心验收条件仍无法执行/验证，才判 `test_inconclusive`；若环境或强关联前置导致已映射操作都无法开始，才判 `blocked`。缺少 OpMap 只能说明某种复用路径不可用，不能直接作为 `test_inconclusive` 原因。`snapshot` 只能是显式观察步骤或辅助证据，不能成为全量默认计划。
- **代表性验证不得扩展为整组通过**：分组执行只允许共享“进入路径/前置状态准备/批量状态读取”，不允许共享或复制 case verdict。组内每个 functional case 必须由 `RunSuite` 内部独立调用 `RunTC`，并写入该 case 自己的操作序列、断言结果、证据路径或运行时断言明细、最终 verdict。展示/只读类 case 可以引用同一次批量读取结果，但必须映射到该 case 的检查目标；交互类 case 缺少操作链时，默认判定为“执行覆盖不足”，应回到组内继续执行该 case。不得因为同组其他 case passed 而继承 passed。只有确认该 case 无法继续执行或无法恢复执行时，才允许异常 `blocked`。
- **禁止硬编码最终 verdict**：最终报告中的 `passed`、`failed`、`blocked`、`test_inconclusive` 数量和每条用例 verdict 必须从 `{run_dir}-run-log.json` 的最终用例记录直接统计生成，禁止在报告脚本或 Markdown 模板中写死 `blocked = 0`、`failed = 0`、`全部 passed`、`最终 failed/blocked 用例：无` 等结论。报告生成前必须执行一致性校验：`run-log.json` 中存在 `failed`、`blocked`、`test_inconclusive` 或其他非 `passed` 状态时，Markdown 报告必须在总览、用例表、分组汇总和对应归因章节中保留对应状态或明确写出“后续复测通过”的覆盖证据；若校验不一致，禁止输出最终报告，必须先修正报告渲染逻辑或补充复测记录。
- 混合用例（功能流程 + 数据断言）应拆分为多个子用例分别归类
- **failed 用例处理取决于修复模式**：执行中出现 `failed` 用例（或编译失败）时先保留当前真实结论并记录证据。允许修改模式下，AI必须完成失败归因；确认可修复后修改业务代码，实时写入 `action=fix`、修改文件/行号和修复说明，重新编译并复测当前用例/相关依赖，本次测试全局最多3轮；每轮完整修复并复测通过后写入 `issue_action=fixed`、`fix_verified=true` 和新的 `passed` 结果，并只计一个修复轮次。只读不修模式下禁止修改业务代码和复测改码结果，只记录失败证据、根因判断和建议修复方向并生成正式报告。两种模式都不得修改既有 `TestHelper`、`FunctionTestLogWriter` 等测试基础设施。无法继续执行但属于环境/前置或强关联用例失败导致的用例标记为 `blocked`；测试流程可运行但无法构造异常刷新、网络故障、并发竞争等目标条件的用例标记为 `test_inconclusive`。不得为满足“全通过”而改写 verdict。
- **资源不足不得直接标记 blocked**：前置校验发现道具/货币/抽卡券等资源不足时，必须先通过 `GlobalMsgMgr.Inst.AISendGMAddMoney("")` 或 `GlobalMsgMgr.Inst.AISendGMAddAllItem()` 补充资源，等待服务器同步后再复测；补充后仍无法构造目标条件时标记 `test_inconclusive`，而不是 `blocked`。GM 指令定义见 [`GlobalMsgMgr.cs`](Assets/Scripts/CyStarRoad/Container/GlobalContainer/GlobalMsgMgr.cs:531)
- **允许并优先构造测试账号数据**：为完成 functional 用例，允许通过 GM 指令、测试服接口、UI 操作或可回滚的业务操作修改测试账号数据。不得因为“会改账号数据”“当前账号不是目标状态”就直接标记；必须先尝试构造前置状态、执行用例、验证结果，并记录数据改动与回滚结果。若测试账号/工具无法构造异常、边界或服务端竞争条件，标记 `test_inconclusive`；若因环境不可用或强关联前置用例失败导致当前用例根本无法执行，才标记 `blocked`。
- **UI 层级遮挡自动清理**：每个用例步骤轮询目标 UI 是否已打开/激活时，必须先检查 AdapterArea 下 Canvas 层级中是否存在其他激活的弹窗/界面遮挡了当前目标 UI。若存在遮挡弹窗（非目标 UI 且非常驻通用界面），必须自动关闭后再继续验证。常驻通用界面白名单：`UI_Test`、`UI_NoticeTipsUP`、`UI_CommonUIMask`、`UI_TouchBlock`。关闭方式优先调用 `GameUISystem.Inst.CloseUI(uiName)`，并短轮询确认已关闭（300ms/次，最长 5 秒）。遮挡检测与清理代码见"UI 遮挡检测与清理 helper"。
- **测试过程与代码修改分离，报告保留真实 verdict**：只读不修模式下，测试流程进行期间不修改已有业务代码或既有测试代码；遇到 `failed` 时只记录真实证据和根因判断。允许修改模式下，确认可修复后可以修改业务代码，但必须立即记录修复文件、行号和修复说明，重新编译并复测。临时编排/辅助代码可以在当前流程中创建和使用，但本轮结束后删除。无论哪种模式，最终报告必须生成并如实展示 `passed / failed / blocked`，不得把未通过或阻塞用例隐藏、删除或改写为 `passed`。

## Token 优化原则（核心约束，优先级最高）

**本 skill 在执行过程中单次 MCP 调用的 token 消耗是普通 Edit/Read 的 5-20 倍**（`capture_scene_snapshot` 全树可达 30k+ tokens、`Read` 加载 PNG 截图可达 5k+ tokens、单次反射 evaluate 返回 500-2000 tokens）。以下规则是**强约束**，违反会显著拉高整次会话成本：

### 0. 致命耗时黑名单（2026-07-16 chess-system 实测）

以下操作模式在测试中经实测验证会浪费 8-12s/次，**禁止在未查 `references/{feature_id}.md` 已知问题清单前直接执行**：

1. **GameButton 触发方式不能写死为单一全局结论** — 源码中 `GameButton.ExecuteButtonClick()` 会进入按钮自身点击流程并最终触发 `onClick` / `onClick2`，因此普通 `GameButton` 默认优先使用 `ExecuteButtonClick()`；`TestHelper.Click()` 在目标存在 `ExecuteButtonClick()` 时不得再额外反射调用 `onClick`，避免点击动画延迟回调与业务回调重复执行。仅当目标没有 `ExecuteButtonClick()` 时，才允许直接调用 `onClick` 委托；已知问题或本次运行验证命中 Action 委托、GameTabItem、长按/拖拽等特殊链路时，必须按对应有效方式触发（如调用 `onClick2?.Invoke(btn)` 或业务兜底），不得继续重复标准点击。无论使用哪种方式，返回 success 只代表触发已执行，必须继续验证页面或业务状态变化。

2. **`System.Type.GetType("HotFix_Project.*")` 找不到热更层类型** — HotFix 层 Assembly 不被 `Type.GetType(string)` 索引。对 `MainHomeController`、HotFix 层 Logic 等，必须遍历 assemblies：`foreach (var asm in AppDomain.CurrentDomain.GetAssemblies()) { t = asm.GetType("FullName"); }`。

3. **底部 Tab 切换走 `MainHomeController.OpenTab` 在 MCP 环境不可靠** — 热更层类型不可直接 GetType，且 `SwitchTab` 方法签名复杂。目标 UI 的进入方式统一为：登录后可见的真实导航入口、已验证按钮链路或业务入口；进入后再用独立状态查询确认目标 UI active。

4. **登录后不得只轮询单一 `UI_Main` 名称** — 登录按钮触发后，进入游戏的判定必须来自一次独立状态查询中的多信号结果：登录界面是否已隐藏或销毁、AdapterArea 下当前 active 的顶层 UI 名称、是否命中大厅/主界面候选（如 `UI_Main`、`UI_TDTab`、`UI_TowerDefence_Main`、`UI_ToyMainList` 或当前项目主界面）、以及业务数据是否已就绪。单独 `GameObject.Find("UI_Main")==null` 不能判定登录失败。

4b. **登录未完成时禁止进入功能测试轮询** — 非登录类功能测试的大厅前置优先调用项目现有 `CyStarRoad.Test.TestBoot.Boot()` / `MockLogin()`，不得用通用 `TestHelper.Click()` 点击 `UI_LoginGame` 登录按钮；只有测试目标本身是登录功能时，才走一次真实登录按钮点击。登录触发后，必须先确认“已进入游戏且业务数据已加载完毕”，才允许开始轮询目标功能 UI。判别标准不是固定 UI 名称，而是组合条件：`UI_LoginGame` 不再 active，且 active 顶层 UI 中出现本项目大厅/主界面候选，且目标业务字段、列表数量或账号数据至少有一项证明数据就绪。
   - `Boot()` 返回 `ready` 时，仍必须用一次独立状态查询确认上述语义条件后才能继续；返回 `login_triggered`、`loading:login` 或普通 `loading` 时，只表示登录异步流程仍在进行，必须继续等待，不得直接记为阻塞。
   - **登录前置不适用普通 UI 的 8 秒单步早停上限**。按 `TestBoot` 的状态机独立轮询，每 200-300ms 发起一次新的状态查询，最长等待 65 秒，以覆盖首次触发和最多 3 次、每次约 15 秒的登录重试；命中 `ready` 或最终语义条件立即结束。只有收到 `err:login_failed_after_3_retries`，或 65 秒后最终查询仍显示 `UI_LoginGame` active 且没有可交互大厅候选，才允许记 `environment_blocked:login_timeout`，并记录每次 Boot 返回值、最终 active UI 和候选状态。
   - 判定登录阻塞前必须确认本轮已完成编译检查和实际进入 PlayMode；run-log 只要求存在 `compile` 与后续进场/登录证据，不再记录 `enter_playmode` 事件。缺少这些证据时只能记为测试阶段记录不完整，不能仅凭 8 秒无变化生成登录阻塞。

5. **点击 ScrollView 列表项（item_*_Logic）时必须先校验业务数据** — 列表卡片（如 `item_toy_card_Logic`、`HeroItem_Logic`）的 `onClick` 是 Lambda 闭包，内部**可能有业务守卫 early-return**（如 `if (_toyData.OwnState != Owned) return`）。直接对首个列表项 `onClick?.Invoke()` 后可能不创建目标 UI，若再轮询 8s 就会浪费 8s。**必须先读取每项关键字段（如 `txt_suipian` 文字），只对满足守卫条件的项执行点击。**

6. **`CreateUIAsync` 异步时序——同次 evaluate 内禁止 action+poll** — `CreateUIAsync` 将 UI 创建调度到 Unity 主线程的下一帧才执行。在一次 evaluate 内**先触发 `CreateUIAsync` 或含 `CreateUIAsync` 的回调，再末尾用 `while+sleep` 轮询 `GameObject.Find(targetUI)`**，结果恒为 null（或 active=false），轮询 5-8s 超时。**2026-07-17 复测确认**：拆分"触发"和"轮询"为**两次独立 evaluate** 后，`UI_Formation` 0ms 即命中。此模式影响所有 `CreateUIAsync` 链路（登录→大厅→ToyMainList→ToyTrain/Formation 等全部入口）。

### 1. snapshot 必须用最小根路径
```csharp
// ❌ 反例：抓全树
capture_scene_snapshot(root_path="GameEntry/Builtin/UI/AdapterArea")  // 含所有 Canvas、登录界面、UI_Test，30k+ tokens

// ✅ 正例：直接定位目标 UI 子树
capture_scene_snapshot(root_path="{UI_ROOT}")           // 仅目标 UI，约 3k tokens
capture_scene_snapshot(root_path="{UI_ROOT}/tab_group")    // 进一步缩小到约 1k tokens
```
**首次进入一个 UI 时抓 1 次其根，之后所有步骤都基于该根的子路径，不再扩大范围。**

> 具体 UI 的根节点名、完整场景路径见 `references/{feature_id}.md`。

### 2. 一次性 Logic 缓存 + 后续直接读取
第一次 evaluate 用反射拿到 Logic 实例后，**必须**缓存到 PlayerPrefs：
```csharp
// 首次：完整探测并缓存（约 1.5k tokens）
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("{LogicFullName}");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
var root = GameObject.Find("{UI_ROOT}");
var baseUI = root.GetComponent("GameFramework.Logic.BaseUI");
var ad = baseUI.GetType().GetField("m_MonoInvocationAdapter",
    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(baseUI);
var lg = ad.GetType().GetField("m_Instance",
    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(ad);
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "{UI_ROOT}");
UnityEngine.PlayerPrefs.Save();

// 之后：缓存路径直接读取（约 400 tokens）
var t2 = System.Type.GetType(UnityEngine.PlayerPrefs.GetString("__test_logic_type__"));
var root2 = GameObject.Find(UnityEngine.PlayerPrefs.GetString("__test_logic_root__"));
var baseUI2 = root2.GetComponent("GameFramework.Logic.BaseUI");
var ad2 = baseUI2.GetType().GetField("m_MonoInvocationAdapter",
    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(baseUI2);
var lg2 = ad2.GetType().GetField("m_Instance",
    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(ad2);
```

> 具体 UI 的 Logic 全限定名和 UI 根节点名见 `references/{feature_id}.md`。

### 3. 状态读取必须批量合并
**禁止**为不同子状态发多个 evaluate：
```csharp
// ❌ 反例：3 次 evaluate
evaluate(读 slot 0 状态)        // 500 tokens
evaluate(读 slot 1 状态)        // 500 tokens
evaluate(读 list 状态)          // 800 tokens

// ✅ 正例：1 次 evaluate 返回所有状态
evaluate(返回批量综合摘要字符串)  // 600 tokens，但包含全部所需信息
```

> 批量状态读取的 C# 代码模式见 `references/{feature_id}.md` 中的「状态读取 helper」。

### 4. 截图必须严格收敛
**每条 functional 用例最多 2 张截图**（进入 UI 后 1 张 + 关键状态变化或结束时 1 张），中间步骤全部用 evaluate 节点状态判断。首次打开新功能界面的截图计入“进入 UI 后 1 张”，不得额外增加第三张：
```csharp
// ✅ 用例 TC-001
capture_screenshot(feature_id) → TC-001 入场证据
evaluate(读上阵区域状态) → 足够判断
// 不需要中途截图

// ✅ 用例 TC-007（进入编辑模式）
capture_screenshot(feature_id) → 入场证据
evaluate(btn_hecheng_0_btn click + m_IsEditMode check) → 1 次 evaluate 完成操作+验证
capture_screenshot(feature_id) → 编辑模式证据
```

> `capture_screenshot` 传入 `feature_id` 后截图写入 `Temp/UIParse/{feature_id}/` 目录，同功能首次调用自动清理旧截图。

首次界面截图用于功能入场证据。若同一 UI 根节点在本次运行中已完成首次截图，后续再次进入该 UI 不重复截图，只复用首次截图结果；只有发生关键状态变化、失败取证或节点状态无法证明预期时，才允许补充截图。存在可读取节点状态时，截图不得替代 evaluate 状态验证；对于纯视觉或布局类预期，清晰的最终截图可以作为结果证据，但必须在 `actual`/`reason` 中说明其与 `expected` 的对应关系。

### 5. 文件读取用 Grep 代替 Read
仅在满足“AutoGen/Logic 语义保底查询规则”的触发条件后，查找字段、按钮、事件时使用 Grep：
```bash
# ❌ 反例：读全文 700 行的 Logic.cs
Read(UI_XXX_Logic.cs)  # ~25k tokens

# ✅ 正例：grep 关键字段
Grep("{field_pattern}", UI_XXX_Logic.cs)  # ~500 tokens
Grep("{button_field}", UI_XXX_AutoGen.cs)  # 找到按钮运行时节点名 ~200 tokens
```

> 正常流程先使用 `references/{feature_id}.md`、本会话缓存和最小运行时查询。上述 Grep 只用于受控保底，不得成为每次点击前的默认步骤。

### 6. 失败信息截断
反射调用遇到 null 或类型错误时，**用 try-catch 转为简短字符串返回**，避免 stack trace 灌满返回：
```csharp
try {
    var t = asm.GetType("{FullLogicTypeName}");
    if (t == null) return "type_null";
    var instance = /* ... */;
    if (instance == null) return "instance_null";
    return "ok:" + instance.GetType().Name;
} catch (System.Exception e) {
    return "err:" + e.Message.Substring(0, System.Math.Min(80, e.Message.Length));
}
```

### 7. 已知 UI 结构时禁止走全树递归
```csharp
// ❌ 反例：递归遍历找 button
FindNode(root, "button_name")  // 全树遍历

// ✅ 正例：直接拼接路径（取自 references/{feature_id}.md 节点树速查）
var go = GameObject.Find("{UI_ROOT}/{panel_path}/{button_name}");  // O(1)
```

### 8. 一次性读取 helper，禁止在每次 evaluate 重复构造
**所有反射探测代码（找 Logic、找 type、找 adapter）必须封装成 helper 一次完成**：
```csharp
// helper 写在第一次 evaluate 末尾，返回值里记录 helper 位置
// 后续所有 evaluate 直接通过 GameObject.Find + helper 静态方法读取
```

### 9. 截图读取原则
- 用例失败 / 视觉布局 / 用例最终状态才 `Read` 截图
- 节点状态判断一律 `evaluate`，**禁止 Read PNG 仅用于"看一眼"**
- `Read PNG` 一次约 5k tokens，3 张就是 15k；通常 1 张足矣

### 10. 阶段性批量操作
**前置条件相同的多条用例应在一次 PlayMode 中连续执行**：
- TC-001/002/003 都只需读初始状态 → 1 次 evaluate 返回所有
- TC-007/008/009 都是同类操作 → 同组连续执行
- 不要在用例之间反复进出 UI

### 11. 实时记录不得增加调用次数
**"执行效率优化规则 #1"要求的逐步 JSON 记录，必须合并进本步骤已有的那次 evaluate 调用中完成落盘，禁止为写日志单独新增一次 MCP 调用。** 记录字段使用缩写键（`id/c/a/t/r/d/ts/te/ev/why`）以减小单条记录体积；AI 不需要读回或复述历史记录，Unity 侧统一调用 `FunctionTestLogWriter` 逐行追加。这条规则的目的是让"耗时可追溯"这件事本身不成为新的 token 开销来源。

### 12. 日志 Schema 契约
执行任何测试前，必须读取 [`references/execution-log-schema.md`](references/execution-log-schema.md)，并以该文件作为测试事件日志和 Markdown 日志报告的唯一格式契约。

每次测试运行必须创建带 4 位序号的运行目录 `Doc/AI开发文档/output/{feature_id}/{run_dir}/`，其中 `run_dir={feature_id}-{sequence}`，例如 `hero-list-0001`。默认规则是永远扫描 `Doc/AI开发文档/output/{feature_id}/` 下同一 `feature_id` 的现有目录，取最大 4 位序号并加 1 作为本轮目录；例如已存在 `hero-list-0029` 时，新一轮独立测试必须使用 `hero-list-0030`。只有用户明确指定“复测/继续/修复/覆盖某个 run_dir”（例如明确说 `复测 hero-list-0029` 或输入路径就是 `Doc/AI开发文档/output/hero-list/hero-list-0029`）时，才允许原位更新该目录。不得因为最近一次运行目录存在、报告已存在、同一测试用例路径相同、同一 feature_id 相同，自动复用旧目录。

---

## 执行效率优化规则（核心约束，与 Token 优化原则同等优先级）

### 路径契约（强制）

- 输入根目录固定为 `Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}/`。
- 输出根目录固定为 `Doc/AI开发文档/output/{feature_id}/{run_dir}/`，其中 `run_dir={feature_id}-{seq4}`。
- 本文其他历史示例中的 `Doc/AI开发文档/{run_dir}`、`Doc/AI开发文档/{feature_id}/testcases/` 和 `Doc/AI开发文档/{feature_id}/{run_dir}` 均视为旧路径，执行时不得使用。
- `FunctionTestLogWriter` 接收逻辑 `runDir={run_dir}`，实际落盘到 output 目录；报告渲染、JSON 转换和上传必须传 output 下的明确绝对路径。
- `runDir` 是逻辑运行名，不是目录路径；它只能是类似 `hero-list-0033` 的单段名称，禁止包含 `/`、`\\`、`..` 或 `Doc/AI开发文档`。
- 初始化运行目录必须调用 `FunctionTestLogWriter.InitializeRunDirectory(runDir)`，禁止在 evaluate 中对 `runDir` 调用 `Directory.CreateDirectory`，也禁止把 `runDir` 与 `Doc/AI开发文档/output` 再次拼接。
- 初始化返回值必须以 `ok:run_directory_initialized|` 开头；若返回 `err:run_dir_invalid|expected_leaf_name`，必须修正参数后才能继续，不得创建任何目录或写入日志。

以下九条规则是对执行过程耗时的强约束，优先级与上方 Token 优化原则相同。若与后文其他章节的旧描述（如固定等待时长、打印模板）冲突，**以本节为准**，冲突处已在对应章节做出调整。第 7-9 条是基于历史执行数据发现新问题后补充的规则，用于覆盖前六条规则未能覆盖或未被严格执行的场景。

### 1. 实时结构化记录规则（替代收尾倒推，**不得增加额外 MCP 调用**）
**禁止**在测试全部执行完毕后再回忆、按截图/日志时间戳倒推每一步过程。**每个步骤执行完成后必须立即记录一条结构化数据**，不得留到收尾阶段统一整理。

**强制补充：最终用例 verdict 也必须实时产生。** `RunTC` 判定某个 case 通过/失败/阻塞时，必须在同一次 evaluate 中立刻追加该 case 的最终记录；测试结束后只允许渲染已有记录，不允许再根据 case 列表批量生成 `EVT-FINAL-*`、批量填充相同 summary、或把少量代表性证据复制到未执行 case。若渲染前发现某 case 没有实时最终记录，必须回到执行阶段继续执行该 case；不得把“缺少记录”“reference 未生成”或“本轮探索耗时较长”当作无法继续执行的依据，也不得批量补 `blocked`。只有确认 MCP/Unity 不可用、用户停止或确实无法恢复执行时，才允许异常补 `blocked`。补 `blocked` 不是正常执行方式；原因必须写明“缺少执行时实时最终记录”，并在报告中归因为执行记录缺失。

本规则的字段、事件枚举、状态枚举、测试事件日志格式和 Markdown 日志报告渲染规则，以 [`references/execution-log-schema.md`](references/execution-log-schema.md) 为准；本节只规定执行时机和调用约束。

**本条与"Token 优化原则"是同一优先级的强约束，记录动作本身不允许成为新的 token 开销来源：**
- **禁止为写日志单独发起一次 MCP/evaluate 调用**。日志记录必须**合并进本步骤本身的那次 evaluate**里——同一次 C# 反射脚本里完成"操作 → 轮询判定 → 组装 DTO → 调用 `FunctionTestLogWriter` 落盘一行 → 返回结果"，而不是先做完动作再单独调一次 evaluate 去写文件
- **字段用缩写键**，减小单条记录体积（对照表见下）：`id`(step_id) `c`(case_id) `a`(action) `t`(target) `r`(result) `d`(duration_ms) `ts`(start_time) `te`(end_time) `ev`(evidence_path) `why`(reason，仅失败/阻塞/超限时填)
- **AI 不需要读回或在对话中复述已写入的历史记录**。日志文件由 Unity 侧的 `FunctionTestLogWriter` 直接追加落盘（JSONL，每行一条）；AI 每次只需在当前 evaluate 中构造 DTO 并调用 writer，不得拼出 JSON 字符串。每批收口仍必须由 writer 的覆盖/唯一性校验读取本批结果。
- 记录粒度：每个 evaluate / click / wait / verify 动作结束后落一行
- 记录位置：`Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-run-log.json`（JSONL 格式，一行一条）
- **最终报告必须基于该文件直接渲染生成，禁止在报告生成阶段重新回忆、拼凑或按时间戳反推过程；渲染报告时才把缩写键映射为可读列名**
- **JSONL 序列化与落盘校验（强制、零外部依赖）**：禁止手工拼接 JSON 的 `{`、`}`、逗号或字符串转义，禁止在已序列化结果后再追加 `}`；必须使用现有 `CyStarRoad.Test.FunctionTestLogWriter` 的固定 `[Serializable]` DTO 和入口（`AppendEventRecord`、`AppendClassifyRecord`、`AppendFinalCaseRecordFromDateTime`）。事件 ID、ISO 时间和 duration 由 writer 统一生成/计算；原始 MCP 错误写入 `RunLogDetails` 的原文字段。禁止使用 `Dictionary<string, object>`、`object`、匿名对象或临时 JSON 字符串承载 `details`，未声明的字段必须先扩展 DTO 和日志 schema。writer 必须完成 `JsonUtility` 序列化、反序列化和物理行回读；任何校验失败都必须停止报告渲染并报告 `run-log_write_invalid`，不得删除尾字符、补大括号、引入第三方 JSON 库或用报告阶段脚本静默修正。
- **Windows 中文路径安全**：不得用 `cmd.exe` 的 `python -c`、一行内联脚本或包含中文绝对路径的命令补写 `{run_dir}-run-log.json`。实时日志必须在 Unity evaluate 的同一次 C# 脚本内调用 `FunctionTestLogWriter`；路径构造、UTF-8 落盘和物理行回读由 writer 负责。若需要在报告阶段调用 Python 固定脚本，优先传工作区相对路径 `Doc/AI开发文档/output/{feature_id}/{run_dir}`，不得传经过终端乱码复制后的路径。
- **C# evaluate 字符串硬规则**：编排层生成的 evaluate C# 代码中，固定字符串只能使用 C# verbatim string（`@"..."`）；Windows 路径、中文路径、JSON、原始工具响应和日志字段不得使用普通 C# 字符串字面量。verbatim string 内的双引号必须写成连续两个双引号（`""`），反斜杠不得再手工转义。执行前的模板烟测必须覆盖至少一个路径字符串和一个 JSON 字符串。
- **工具错误记录参数硬规则**：默认调用带 6 个业务参数的 `FunctionTestLogWriter.AppendToolErrorRecord(runDir, toolName, toolPhase, target, status, rawToolResponse)` 重载，由 writer 自动补齐 `compileError=""` 和 `runtimeError=""`；只有确实存在对应错误文本时，才调用 8 参数重载显式传入两者。禁止在 evaluate 中临时省略参数或自行拼接错误 JSON。

```json
{"id":"S03","c":"TC-003","a":"click","t":"onscenenode/bg1","r":"passed","d":1200,"ts":"...","te":"...","ev":null}
```

### 2. 绝对路径缓存规则
**首次成功定位的 UI 节点绝对路径、Logic 实例引用必须缓存，后续步骤（含同 feature_id 的后续用例）优先复用缓存路径，禁止重新从根节点递归/枚举查找。此缓存不包含 `UILogicManager.xlsx` 的位置、`UIPerfectPath` 或任何效果图解析结果。**

- 缓存内容：UI 根节点绝对路径、Logic 类型全限定名、关键子节点路径（按钮、列表容器等）
- 缓存方式：写入 `PlayerPrefs`（如 `__test_logic_type__`、`__test_logic_root__`），供同一会话后续步骤直接读取（详见"提速技巧 #47"完整 helper 代码）
- **复用优先级**：需要定位节点时，第一步必须先尝试用缓存路径直接 `GameObject.Find`；只有缓存路径读取失败（节点为 null 或类型不匹配）时，才触发一次重新探测并更新缓存
- 禁止：缓存已存在的情况下，仍走全树递归 `capture_scene_snapshot`（root_path 过大）或 `FindNodeByComment` 全树遍历
- 缓存失效场景：切换 feature_id、重新进入 PlayMode 后，缓存路径需要重新校验一次（一次校验成本远低于每次重新探测）

### 3. 前置条件分组执行规则
**执行前必须先扫描输入文档中的全部用例，按"进入路径 / UI 根节点 / 前置状态是否相同"分组，组内共享一次进入操作，禁止在用例之间反复进出同一界面。分组是为了连续执行和降低重复进出 UI 成本，不是抽样；不得只挑选少量代表性用例完成“最小实测”。**

**MCP 调用粒度以小分组为单位**：同一页面、同一前置状态且无独立跨帧等待需求的 Case 合并为小组，每组使用 1 次 `evaluate` 调用 `TestHelper.RunSuiteAndRecord(runDir, inputCasePath, referencePath, groupId, plans)`；跨页面或需要独立等待/恢复的 Case 拆成 1–2 条的小组。该入口内部会为每个 plan 独立调用 `RunTC`、执行断言；普通模式立即写入 final record。自测自修时，为可能需要修复的 plan 设置 `defer_final_on_nonpassed=true`，非 passed 结果先写 case-scoped 非 final attempt，修复验证结束后再写唯一 final record。不生成或读取 case-map。

`RunSuite` 是分组批量执行入口，不是批量写结果入口。每个 `plan` 必须同时包含当前 Case 的 `source_steps`、真实 `operations` 和独立 `assertion`；只有纯展示/只读类用例才允许显式使用 `snapshot`。自然语言映射采用“逐步尽可能执行”而不是全有或全无：一部分步骤无法映射时，仍须执行其余已验证的真实操作，并在计划中记录 `mapping_level=partial`、`mapped_steps` 和 `unmapped_steps`；只有核心验收条件无法覆盖时才使用 `test_inconclusive`。同一次 evaluate 可以共享进入路径，但不得把同一个 plan 或统一快照复制给整组 Case。`RunSuite` 内部必须为每个 plan 独立调用 `RunTC`，随后执行该 plan 的断言；返回值只能作为对应 Case 的操作/断言回执，不能直接替代 final record。组级 summary 只允许作为分组统计，不能作为任一 Case 的 passed 证据。若某个 Case 需要真实交互但没有执行操作链，必须回到组内继续执行该 Case，不得因 reference 缺失、探索成本或前面 Case 已完成而提前收尾。不得因为同组其他 Case passed 而继承 passed。只有确认 MCP/Unity 不可用、用户停止或该 Case 确实无法继续执行时，才允许异常 `blocked`，不得直接降级后收尾。

每个执行分组必须有一个不可跳过的 per-case final record writer。它属于测试编排层，不要求 `RunSuite` 自己写文件；但在获得每条 case 的独立最终断言后，必须在同一次收口 evaluate 中完成：

1. 为本组每个 `case_id` 组装独立 `RunLogRecord`，包含 `case_id`、`group_id`、真实操作/读取项、独立断言、证据和最终 `status`。
2. 使用固定 `[Serializable]` DTO 和 `UnityEngine.JsonUtility.ToJson()` 序列化，禁止把 `RunSuite` 原始字符串或组级 summary 当作最终记录。
3. 调用 `FunctionTestLogWriter.AppendFinalCaseRecordFromDateTime(runDir, request, start, end)` 或统一事件入口追加一行 JSONL；不得在 evaluate 中直接调用底层 17 参数 `AppendFinalCaseRecord(...)`，也不得直接 `File.AppendAllText` 拼接记录。
4. writer 立即回读刚写入的物理行，用 `JsonUtility.FromJson<RunLogRecord>()` 校验，并确认 `run_id`、`case_id`、`event`、`status` 与本次记录一致。
5. 分组收口前比较 `expected_case_ids` 与本组已写入的最终 `case_id`：`missing`、`unexpected`、重复最终记录都必须为空；否则立即停止并记录 `run-log_write_invalid`，不得进入下一组、报告渲染或上传。

当前项目的固定实现入口为 `CyStarRoad.Test.FunctionTestLogWriter`：分类基准使用 `AppendClassifyRecord(...)`，普通事件使用 `AppendEventRecord(...)`，原始工具错误默认使用 6 参数 `AppendToolErrorRecord(...)` 重载（需要时再使用 8 参数重载），每条最终用例使用 `AppendFinalCaseRecordFromDateTime(...)`，分组收口使用 `ValidateFinalCaseGroup(...)` 或全批次收口使用 `ValidateFinalCaseCoverage(...)`。`functional_case_ids` 必须是完整 JSON 字符串数组，禁止写成 `TC-001..TC-152`、首尾范围或其他压缩文本。不得在 evaluate 中重新手写一套 JSON 拼接或绕过这些入口。

**最终 Case 时间参数固定模板（强制）**：编排层只调用 `AppendFinalCaseRecordFromDateTime(...)`，由统一入口完成时间转换：

```csharp
DateTimeOffset start = DateTimeOffset.Now;
// 执行操作与独立断言
DateTimeOffset end = DateTimeOffset.Now;
var request = new FinalCaseRecordRequest {
    event_id = eventId, group_id = groupId, case_id = caseId,
    step_id = stepId, target = target, status = status,
    evidence = evidence, reason = reason, operation = operation,
    assertion = assertion, expected = expected, actual = actual,
    snapshot = snapshot
};
FunctionTestLogWriter.AppendFinalCaseRecordFromDateTime(runDir, request, start, end);
```

底层 `duration_ms` 参数和 17 参数位置接口仅保留在 writer 内部兼容使用；正式批量执行前必须编译验证上述统一模板。出现 `CS1503`、`CS1501` 或 `CS7036` 时不得临时改某一条调用继续执行，必须修正统一入口或模板并重新烟测。

动作 evaluate 与异步断言需要分开时，最终记录必须合并到“获得最终独立断言”的那次 evaluate 中。若编译、PlayMode 或登录环境已被确认阻断，必须为受影响的每个 case 分别写入真实的 `blocked`/`test_inconclusive` 记录及同一阻断原因，不能让 case 从日志中消失。

#### TestHelper 动作回执与独立断言契约

`TestHelper.RunTC` / `RunSuiteAndRecord` 的 `ok:*` 返回值只表示动作方法被调用，不能直接形成 `passed`。每条 Case 必须先在当前运行中构建 `CaseExecutionPlan`，把自然语言步骤、操作链、断言和预期绑定到同一个对象；这些字段随该 Case 的 final record 写入 run-log，不得只依赖临时数组或统一快照，并按以下顺序执行：

1. 先用 `RunSuiteAndRecord(runDir, inputCasePath, referencePath, groupId, plans)` 执行每条用例自己的真实操作链；`plans[i]` 必须同时包含 `case_id`、`source_steps`、`operations` 和 `assertion`。
2. `RunSuiteAndRecord` 在每条 `RunTC` 返回后立即执行该 plan 自己的断言；普通模式写 final record，自测自修 plan 在非 passed 时只写 attempt，最终确认后才写 final。不得在组执行结束后用统一快照批量生成 final record。若页面状态丢失，停止当前小组，调用已验证的恢复动作（如 `RunMappedAction("detail_back")`），再用独立 evaluate 调用 `CheckBoundUiReady()` 验证恢复；恢复成功后只重跑受影响 Case。
3. 对异步页面/业务变化，禁止在同一次主线程 `evaluate` 中执行“动作 + Thread.Sleep + 断言”。动作完成后由编排层每 100–300ms 发起一次独立 `evaluate`，最多轮询 8 秒；命中语义条件立即结束，超时才记录 `failed`。
4. 只有操作链完成且独立断言 `status=passed` 才能写 `passed`；动作成功但断言未满足写 `failed`；当前环境无法构造目标异常或边界条件写 `test_inconclusive`。

发现 `failed` 后，必须由 AI 基于当前 run-log 的 case-scoped 过程记录或 final record 完成失败归因，不依赖输入用例预先提供 issue 字段：读取该 Case 的 `expected`、`actual`、操作回执、断言回执和证据，先排除测试误判、环境阻塞和条件不可构造，再判断是否为已确认的产品问题。普通模式先写 final；自测自修模式先写非 final attempt，修复完成后再写唯一 final。确认是产品问题时，AI 立即调用 `TestHelper.RecordAutoLocatedIssue(...)`（或现有 `FunctionTestLogWriter.AppendIssueRecord(...)`）生成并写入唯一 `issue_id`、问题描述、根因、目标和证据；允许修改模式下，确认可修复后继续修改业务代码，调用 `TestHelper.RecordIssue(..., issueAction="fixed", fixVerified=true, fixRound=N, status="passed", ...)` 写入修复事件，并复测当前用例/相关依赖；无法确认根因时记录未归因失败及完整证据，但不计入 Bug。两种模式都不得修改既有 `TestHelper`、`FunctionTestLogWriter` 等测试基础设施；只读不修模式不得执行改码复测。`located` 必须关联 failed 证据，`fixed` 必须关联修复证据和通过复测证据，blocked/test_inconclusive、known-issues 条目或动作回执本身不能直接当作 Bug。报告必须展示 issue_id、关联 Case、问题描述、根因和证据；同一个 failed Case 可以关联多个 issue_id，`定位Bug数`按 `located` 的 issue_id 去重。

通用示例：

```csharp
// 一次批量 evaluate：每条 plan 自带步骤、操作和断言
return CyStarRoad.Test.TestHelper.RunSuiteAndRecord(
    "hero-list-0001",
    "Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0001/test_case.json",
    "references/hero-list.md",
    "hero-detail",
    new CyStarRoad.Test.CaseExecutionPlan[]{
        new CyStarRoad.Test.CaseExecutionPlan {
            case_id = "TC-HL-001",
            source_steps = new string[]{"点击英雄卡片"},
            operations = new string[]{"click:0"},
            assertion = "assert_active:UI_TowerDefence_HeroGrow,true",
            expected = "详情页激活"
        }
    });
```

当前项目已有的通用断言 API 位于 `Assets/Scripts/CyStarRoad/Test/TestHelper.cs`；功能特有的路径、字段和 Case 映射必须写入 `references/{feature_id}.md`，不能只存在当前对话或临时脚本中。

**TestHelper 公共封装速查（除上文已列出的 `RunTC`/`RunSuiteAndRecord`/`RunMappedAction`/`RecoverBoundRoot`/`Toggle`/`UpdateFinalCaseReasons`/`RecordAutoLocatedIssue` 外，以下封装同样可用，均位于 `CyStarRoad.Test.TestHelper`）：**

| 方法 | 签名 | 用途 | 何时使用 |
|------|------|------|---------|
| `CloseUI` | `public static string CloseUI(string uiName)` | 关闭指定 UI（弹窗/面板）：遍历程序集定位 `GameFramework.Logic.GameUISystem` 调用 `CloseUI`，找不到时兜底 `SetActive(false)`。返回 `ok:closed:{name}` / `ok:already_closed` / `err:...` | 执行"UI 遮挡检测与清理"时优先调用本封装代替手写内联反射，避免每次 evaluate 重复构造类型定位代码 |
| `GetComponentByTypeName` | `public static object GetComponentByTypeName(GameObject go, string typeName, bool includeChildren = true)` | 按类型名获取组件（兼容 HotFix 层/跨 dll 类型名无法直接 `typeof` 的场景）。先找自身组件，再找子节点组件 | 需要读取 HotFix 层组件（如 `GameText`/`GameImage`/`GameButton`）但当前 evaluate 域无法直接 `typeof` 该类型时使用 |

> 注意：`CloseUI`/`GetComponentByTypeName` 是 `TestHelper` 提供的便捷封装，位于 [`TestHelper.cs`](Assets/Scripts/CyStarRoad/Test/TestHelper.cs:368) 与 [`TestHelper.cs`](Assets/Scripts/CyStarRoad/Test/TestHelper.cs:412)；已有功能无需改用它们，但新增遮挡清理或跨 dll 组件读取代码时应优先复用，减少重复反射代码的 token 消耗。

**覆盖基准必须来自输入用例全集**：`functional` 用例的执行清单必须等于输入文档完整解析出的全部 functional CaseId。Token 优化、最小化节点读取、参考缓存、分组建议、文件预览和上下文截断都不能改变覆盖基准。若输入有 152 条用例，其中 152 条均为 functional，则本轮执行和报告前扫描必须以这 152 条为基准；只记录 5 条、9 条、10 条或任意子集后生成报告，属于执行覆盖不足，必须回到用例解析和分组执行阶段继续补齐缺失用例。

```csharp
return CyStarRoad.Test.TestHelper.RunSuiteAndRecord(
    "hero-list-0001",
    "Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0001/test_case.json",
    "references/hero-list.md",
    "hero-initial",
    new CyStarRoad.Test.CaseExecutionPlan[]{
        new CyStarRoad.Test.CaseExecutionPlan {
            case_id = "TC-001", source_steps = new[]{"观察槽位"},
            operations = new[]{"snapshot"},
            assertion = "assert_snapshot_contains:m_OnSceneHeroIds=cnt:3",
            expected = "上阵数量为3"
        },
        new CyStarRoad.Test.CaseExecutionPlan {
            case_id = "TC-002", source_steps = new[]{"进入编辑并保存"},
            operations = new[]{"edit", "save"},
            assertion = "assert_snapshot_contains:m_IsEditMode=False",
            expected = "保存后退出编辑态"
        }
    });
```

- 分组依据：相同 UI 根节点、相同初始状态、相同数据前置条件
- 分组后执行顺序：组内用例连续执行，仅在组与组切换时才重新进入/退出 UI
- 分组结果需在"用例归类结果"之后一并输出，例如：
  ```
  分组A（英雄列表初态，TC-001/002/003）
  分组B（编辑模式操作，TC-007/008/009）
  ```
- 本条是"Token 优化原则 #10 阶段性批量操作"的正式化表述，二者保持一致，执行时以本条的分组输出格式为准

### 4. 前置条件前置校验规则（快速校验 + 数据构造优先）

**用例执行前必须先做一次纯状态读取，判断前置条件是否满足。**

- 前置校验必须满足：
  - 只允许反射读字段/属性（如 `ownedHeroCount`、`m_OnSceneHeroIds.Count`）
  - **禁止**在校验阶段调用任何 Click / 触发方法，**禁止**产生新的等待或轮询
  - 若判断所需数据尚未加载（如尚未进入目标界面），必须先进入目标界面或触发必要加载，再重新读取；不得因为首次读取为空就直接 blocked
- 校验应基于用例文档前置条件转化为可执行布尔表达式，例如：
  ```
  前置条件：ownedHeroCount > MAX_ON_SCENE_COUNT
  → 读取字段后直接判断 true/false
  ```

- **数据前置条件不满足时的构造流程**：当前置校验发现账号数据、资源、上阵状态、编辑状态、列表数量、满员/空位、negative/boundary 场景不满足时，**不得直接标记 blocked**，必须按以下流程构造后再复测：
  1. **发送 GM 指令补充资源**：通过 evaluate 调用 GM 接口（定义见 [`GlobalMsgMgr.cs`](Assets/Scripts/CyStarRoad/Container/GlobalContainer/GlobalMsgMgr.cs:531)）
     ```csharp
     // 补充货币（钻石+金币各10万）
     Game.Logic.GlobalMsgMgr.Inst.AISendGMAddMoney("");
     // 补充所有道具（每项99个）
     Game.Logic.GlobalMsgMgr.Inst.AISendGMAddAllItem();
     ```
  2. **通过 UI 或业务接口构造状态**：需要满员、空槽、上阵、下阵、编辑态、取消态、保存态等状态时，优先用真实 UI 操作构造；UI 路径不稳定时可使用已验证的业务接口/GM/测试服接口构造，但必须回到 Unity UI 验证最终状态。
  3. **等待服务器同步**：构造后短轮询（300-500ms/次，最长 8 秒）检查数据是否已同步——读取 `GlobalDataMgr`、目标 UI 字段、列表数量、槽位状态或对应业务字段，确认状态已达到用例前置条件。
   4. **同步完成后重新校验**：重新读取前置条件字段，满足则继续执行用例；测试环境仍可运行但目标异常/边界条件无法构造时记录 `test_inconclusive`，并写明“已尝试构造但未满足”及具体失败点；环境或强关联前置失败导致无法执行时才记录 `blocked`。
  5. **回滚优先但不阻塞执行**：涉及上阵/下阵/保存阵容等会改变账号状态的用例，执行前尽量记录原始状态，执行后尽量恢复；若无法恢复，不得因此跳过用例，但必须在 run-log 和报告中写明改动与未回滚风险。
   6. **适用范围**：所有因资源不足、账号状态不匹配、列表数量不足、满员/空位条件不满足、negative/boundary 条件缺失导致的前置条件不满足，均先走构造流程。构造后仍无法合理形成目标测试条件时记 `test_inconclusive`；缺少可用运行环境、关键前置不可用或强关联前置用例失败导致无法执行时才记 `blocked`。
  7. **记录要求**：数据构造步骤必须写入 JSON 记录（`event=setup` 或 `event=fix`，`target=<构造入口>`，`reason=<构造目的>`，`details.before/after/rollback` 记录改动前后状态），并在报告"4. 失败与归因"中注明“已主动构造测试数据”。
  8. **同分组数据构造只需执行一次**：同分组内多条用例共用相同前置条件时，构造操作只在分组进入时执行一次，后续用例直接复用已构造状态。

- **耗时预期修正**：前置校验不等于"瞬时完成"，一次 MCP 反射调用本身有正常的网络/引擎往返延迟（通常几百毫秒到数秒），规则约束的是"不轮询、不等待固定时长"，不是承诺绝对耗时 <1 秒。报告中该类 blocked 用例的耗时应体现为"一次读取的真实往返耗时"，不得为凑数字而虚报或截断
- 同分组内多条用例依赖相同前置字段时，应在进入分组时一次性批量读取，避免逐条用例重复读取

### 5. 短轮询 + 早超时 + 已知问题规避（替代固定等待）
**禁止统一使用固定 2-5 秒等待。改为"短轮询检查目标状态 + 早停超时上限"，仅在动画/场景切换等纯视觉表现场景才允许固定等待兜底。**

- 默认轮询策略：点击/触发操作后，每 300-500ms 轮询一次目标状态（如 `activeInHierarchy`、字段值变化），命中预期立即继续，不需要等满固定时长
- 早停超时上限：普通 UI/业务步骤单次轮询最长不超过 **8 秒**，超时仍未达到预期状态时判定该步骤失败并记录证据，不得无限等待到硬性重试上限才发现问题；登录大厅前置属于 `TestBoot` 异步状态机，按规则 4b 的独立超时和最终语义查询执行，不得套用 8 秒上限
- **硬校验（强制，不得跳过）**：JSON 记录中任意一条 `duration_ms > 8000` 的步骤，若该步骤不属于"纯视觉动画/转场"类别，**必须**在该条记录的 `reason` 字段中显式标注超限原因（如撞到了其他固定超时、连续重试未生效等），不得留空。报告生成阶段需扫描所有超过 8000ms 的步骤并在"4. 失败与归因"中单独列出，视为规则执行异常，而非正常现象。时间字段和 duration 必须由同一 writer 生成，禁止调用方分别手写三者。
- **已知问题清单必须真实持久化存储**：维护独立文件 `Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-known-issues.json`，每条记录格式：
  ```json
  {"node":"heroicon","symptom":"标准点击后未打开UI_TowerDefence_HeroGrow","workaround":"反射调用 OnHeroItemClick()","confirmed_at":"2026-07-09"}
  ```
  - **执行任意点击类操作前，必须先查询该文件**，命中已知问题节点时直接跳过标准点击与失败重试环节，直接执行 `workaround` 中记录的方案，并在一句话摘要与 JSON 记录中标注"因已知问题跳过标准点击"
  - 首次在某次运行中发现新的不稳定点击链路且已验证兜底方案有效后，**必须**在该次运行结束前把该条目写入 `known-issues.json`，供后续运行直接复用，不得只停留在当次报告的文字描述里
- 本条替代原"等待时间要求"（固定 2-5 秒）与"UI 打开延迟校验规则"，两处已在对应章节标注调整

### 6. 执行过程输出精简规则（结构化短语，禁止冗余叙事，但不得省略输出）
**每个步骤执行完成后，必须同时做两件独立的事，二者不可相互替代，但二者共享同一次工具调用，不产生额外调用成本：**
1. **向对话输出简短进度**——用于实时沟通，不属于测试报告证据。
2. **在同一次 evaluate 内完成测试事件落盘记录**（详见"执行效率优化规则 #1"）——这是给测试报告渲染用的完整数据，**不需要为此单独再发起一次 MCP 调用**

**"精简"指的是进度提示短而清晰；测试报告只记录测试事件，不记录聊天窗口原文。**

- 测试事件继续写入 `{run_dir}-run-log.json`；其中 `case_id`、`step_id` 用于关联具体用例和步骤
- 禁止内容（这些只进 JSON，不进对话摘要句）：
  - 完整路径、完整字段名、时间戳等细节
  - "已确认""已完成""成功执行了"等冗余开头词
  - 对已获得结果的重复性自我确认式复述
- 本条替代原"打印给用户的分析结果格式"与"打印操作指南"中的多行分隔符模板，两处已在对应章节标注调整——**替代的是"模板格式"，不是"要不要输出"**

### 7. 首次进场一次性状态判定规则（替代无效的"进场缓存"思路）
**登录 → 大厅 → 目标UI 这一进场链路在单次运行中通常只执行一次，"缓存复用"对它无效——真正的耗时来源是链路内部"探测一步、看一眼结果、再决定下一步"的连续试探（如反复 probe_ui / probe_root_canvas / login_to_lobby / probe_post_login_ui），必须改为一次性状态判定。**

- **禁止**用"探测 → 观察 → 再探测"的迭代方式确认当前所在界面。进场前必须先执行**一次**能同时返回多项判定信息的状态查询（如同时读取：当前激活的顶层 Canvas/UI 名称、登录界面是否 active、所有大厅/主界面候选是否 active、目标 UI 节点是否已存在、业务数据是否就绪），根据这一次查询结果直接决定下一步动作（登录 / 跳过登录直接进大厅 / 直接进目标UI），不得对同一层级信息发起多次独立探测。登录成功判定必须允许项目主界面名称差异，不能只认 `UI_Main`。
- 触发登录/跳转类动作后，用短轮询+早停确认结果（复用"执行效率优化规则 #5"），而不是"动作 → 固定等待 → 再发起新一轮探测判断是否成功"
- **真正能复用缓存的场景**仅限于：(a) 同一次运行内的失败重试（"复测与回归"阶段，最多3次重跑）；(b) 一次会话内连续测试多个 feature 且未退出 PlayMode。这两种情况下，若进场链路此前已确认走通，才允许直接复用已缓存的路径/状态标志跳过重新探测；**首次进场无缓存可用，优化重点应放在减少探测次数本身，而不是寄希望于缓存命中**

### 8. 记录连续性校验规则（禁止耗时黑洞）
**JSON 记录中任意相邻两条的 `end_time(前一条)` 与 `start_time(后一条)` 之间，不得出现无记录说明的时间间隙。**

- 若两条记录之间存在超过 **2 秒** 的未记录间隙，视为存在"漏记步骤"或"隐藏等待"，必须在报告生成前定位原因并补记：
  - 若确实发生了某个动作但未即时写入 JSON（违反"实时结构化记录规则"），应尽量补记该动作
  - 若该间隙是工具调用本身的排队/网络延迟，应在相邻记录的 `reason` 字段中注明，而非留空不解释
- 报告生成阶段需对 JSON 记录做一次连续性扫描，若发现未解释的间隙，需在"4. 失败与归因"中作为"测试流程问题"单独列出，而不是让总耗时里悄悄"消失"一段无法追溯的时间

### 9. 效果对比校验规则（防止优化空转）
**每次运行结束后，若存在同一 feature_id 的历史 timing JSON，优先比较本次业务 Skill 有效耗时与历史 Skill 有效耗时；不得再用 run-log 首尾跨度或步骤 `duration_ms` 累加值作为 Skill 优化结论。**

- 若没有 Skill timing 记录，只能标注“本轮缺少 Skill 时间，无法进行耗时对比”，不得用 Unity 生命周期时间冒充。
- 该规则不要求每次都必须变快；用例数量、数据状态和环境等待都会影响结果，但必须明确本轮比较使用的时间口径。

---

## UI 参考文档系统（提速核心）

本 skill 配合 [`ui-quick-reference`](../ui-quick-reference/SKILL.md) skill 使用，从两个来源获取 UI 快速参考文档。两类文档由不同阶段维护：离线静态 reference 由 workflow 前置/回刷，运行时 reference 由本 skill 在 Unity 测试中维护。

**查找优先级（强制执行）：**

1. **先检查 `../ui-quick-reference/references/{feature_id}.md` 是否存在** — 存在时读取，用于获取离线扫描生成的 AutoGen 字段映射、Logic 回调映射、Prefab 节点和子 UI 列表；不存在时不得直接 Read 报错，应记录 `query_reference.details.reference_kind=offline`、`gap=missing`，继续读取运行时参考和最小运行时信息。离线文件的生成由 workflow 在本 skill 启动前负责
2. **再检查并读取 `references/{feature_id}.md` 和本会话缓存** — 获取本项目已在运行时验证过的节点路径、触发方式、已知问题和分组建议
3. **做最小运行时查询** — 对候选绝对路径执行 `GameObject.Find` / `evaluate`；无候选路径时，仅对当前目标 UI 根执行一次最小范围 `capture_scene_snapshot`
4. **参考不足或运行时验证失败时再限定 Grep 当前目标 UI 的 AutoGen/Logic** — 只补齐缺失字段、回调、父链或数据守卫，不得无边界扫描
5. **将离线/源码结果转换为候选并回到 Unity 验证** — 验证节点存在、active、组件类型、父链和操作后的状态推进；验证成功后才允许执行、判定或更新缓存。若运行时验证结果与既有 `references/{feature_id}.md` 不一致，以本次运行时结果为准，并在本轮执行过程中同步修正运行时 reference，不等到下次测试。若发现离线静态映射与源码/Prefab不一致，只记录 `static_reference_gap`，由 workflow 测试后调用 `ui-quick-reference` 回刷
6. **截图只用于视觉证据或坐标点击** — 不得用截图替代能够通过节点状态完成的运行时验证

两种 `references/` 的职责分工：

| 来源 | 路径 | 内容特点 | 生成方式 |
|------|------|---------|---------|
| `ui-quick-reference` | `../ui-quick-reference/references/` | AutoGen 字段映射、Logic 回调映射、Prefab 节点、子 UI 列表 | workflow 前置或静态缺陷回刷时调用离线扫描器 |
| `unity-functiontest` | `references/` | 运行时实测路径、已验证触发方式、已知问题、用例分组、兜底方案 | Unity 测试中增量维护，workflow 测试后收口 |

**已存在 `../ui-quick-reference/references/{feature_id}.md` 时**，必须先从中获取按钮/字段/回调/子 UI 映射，再结合运行时参考和缓存做最小运行时验证。**不存在时不能当作错误中断**；本 skill 只记录离线 reference 缺失并继续，生成动作由 workflow 负责。
**运行时参考不存在、路径失效或目标身份不明确时**，按“AutoGen/Logic 语义保底查询规则”生成候选并回到 Unity 验证。验证通过后立即创建或修正 `references/{feature_id}.md` 的运行时路径、目标 UI、触发方式和分组建议；运行时 reference 的最终存在性和内容完整性由 workflow 在测试返回后收口检查。

参考文档包含以下内容：

- UI 根节点名、完整场景路径、Logic 全限定名、Assembly 名
- 节点树速查（槽位、列表、按钮、页签的完整层级路径）
- 按钮速查表（AutoGen 字段 → 运行时节点名 → 触发方式）
- Logic 关键字段/方法表
- 状态读取 helper（一次 evaluate 批量返回全部关键状态的 C# 代码）
- 已知问题清单（稳定点击 vs 兜底方案）
- 用例分组建议


### 运行时 reference 生命周期

#### 测试中增量维护

运行时 reference 只允许写入本轮 Unity 已验证的事实。首次确认目标 UI 后，如果 `references/{feature_id}.md` 不存在，应基于模板创建初版；随后在以下事实确认后立即增量更新：

- 目标 UI 的运行时根路径和完整父链
- 真实导航入口与登录/业务数据要求
- 控件的实际组件类型和有效触发方式
- 点击、切页或异步创建后的可复核状态断言
- 已确认复现且已验证有效的兜底方案
- 遮挡弹窗处理和用例分组建议

不得把 AutoGen/Logic 候选、未验证的截图猜测或单纯的 MCP action acknowledgement 写入运行时 reference。

#### Reference-only 收口模式

当 `functiontest-workflow` 在 Unity 测试返回后调用本模式时：

1. 输入当前 `feature_id` 和本轮 `run_dir`。
2. 只读取本轮 `run-log.json`、`known-issues.json`、已有运行时 reference 和本轮实际验证证据。
3. 创建或增量更新 `references/{feature_id}.md`。
4. 不进入 PlayMode，不执行新的用例，不创建新的 `run_dir`，不修改任何 case verdict，不重新渲染 Markdown 报告。
5. 如果本轮没有进入目标 UI 或没有足够运行时证据，不得补造内容；返回并记录 `runtime_reference_gap`，由 workflow 保留真实测试结果并继续后续报告流程。

本模式用于保证 reference 收口，不替代测试过程中的实时更新。

### 模板

新建 feature 参考文档时，复制 `references/ui-quick-ref-template.md` 并填入实际数据。

### 现有参考文档

| feature_id | ui-quick-reference 源 | unity-functiontest 源 | 说明 |
|-----------|----------------------|----------------------|------|
| `draw-card` | [`ui-quick-reference/references/draw-card.md`](../ui-quick-reference/references/draw-card.md) | `references/draw-card.md` | 抽卡主界面 (UI_DrawCard_Main) |
| `draw-card-rate` | [`ui-quick-reference/references/draw-card-rate.md`](../ui-quick-reference/references/draw-card-rate.md) | — | 抽卡概率预览 (UI_DrawCard_RatePreviewView) |
| `draw-card-result` | [`ui-quick-reference/references/draw-card-result.md`](../ui-quick-reference/references/draw-card-result.md) | — | 抽卡结果页 (UI_DrawCard_ResultView) |
| `piece-deploy` | — | `references/piece-deploy.md` | 棋子上阵/布阵界面 (UI_Formation) |
| `chess-system` | — | `references/chess-system.md` | 棋子列表+详情/升级/升星 (UI_ToyMainList + UI_ToyTrain) |
| `chess-star` | — | `references/chess-star.md` | 棋子升星功能 (UI_ToyTrain 升星页签/升级页签) |

## 路径与工具约束
- 测试报告输出路径：`Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-unity-functiontest-report.md`
- 证据路径：直接使用 MCP 工具返回路径

默认 MCP 工具：
- `mcp__mymcp__enter_test_scene` / `mcp__mymcp__stop_scene_play`：控制 PlayMode
- `mcp__mymcp__evaluate`：执行 C# 表达式，做状态读取、断言、轮询、触发 UI 回调
- `mcp__mymcp__capture_scene_snapshot`：抓取场景树和 UI Rect 信息。`root_path` 按需填（默认从根抓全量；常见做法是传 `GameEntry/Builtin/UI` 把范围缩到 UI 子树）
- `mcp__mymcp__simulate_click`：点击交互的兜底工具，配合 `capture_screenshot` 走方式二完成模拟点击。坐标必须是 Unity 屏幕坐标（左下角原点），详见"点击执行流程"。**禁止直接把按钮名当坐标使用**
- `mcp__mymcp__capture_screenshot`：截图取证。**调用时传入 `feature_id`**（如 `capture_screenshot("piece-deploy")`），截图写入 `Temp/UIParse/{feature_id}/` 目录，同功能首次调用自动清理旧截图。不传参兼容旧行为（写入 `Temp/UIParse/Common/`）
- `mcp__mymcp__query_logs`：日志取证与失败诊断
- `scripts/focus_unity_window.ps1`：在每次编译前按 `project_root` 找到对应 Unity 进程并尝试置前主窗口；退出码 0 表示已验证聚焦，退出码 3/4 表示已找到 Unity 但窗口验证失败（仍允许先尝试编译），退出码 1/2 表示没有安全的目标进程
- `mcp__mymcp__execute_compile`：**启动前编译检查**（强制）。先完成一次聚焦尝试；只要已找到当前项目 Unity 进程，就调用一次触发 Unity 编译，返回结果用于判断代码是否可运行。若首次调用超时或没有编译完成回执，再聚焦并重试一次；明确返回编译成功或错误后不重复调用。编译失败时立即终止测试、生成报告并注明报错信息，不进入 PlayMode。修复代码后也必须重复同一流程确认编译通过，再进入 PlayMode 重测

若关键 MCP 工具不可用，应记录为 `blocked`。

## AutoGen/Logic 语义保底查询规则

AutoGen/Logic 只用于解释和定位运行时查询无法可靠识别的 UI，不是默认入口、不是独立测试流程，也不能单独证明功能通过。保底查询不得新增 TestHelper API 或调用；本 skill 已有 TestHelper 规则保持不变。

### 允许触发的条件

先检查并读取已存在的 `../ui-quick-reference/references/{feature_id}.md`、`references/{feature_id}.md` 和本会话缓存；`ui-quick-reference` 离线参考不存在时不得直接 Read 报错，应记录缺失并继续后续流程。仅在参考不足或完成最小运行时查询后出现以下任一情况时，才进一步限定 Grep 当前目标 AutoGen/Logic：

1. 已记录绝对路径在当前运行时为 null、inactive 或组件类型不匹配
2. 目标路径不存在，且最小目标 UI 快照无法直接定位控件
3. 存在多个同名节点，父链或业务身份无法区分
4. 动态列表项无法确定目标身份或业务守卫条件
5. 控件触发后没有预期状态推进，需要确认回调、目标 UIID 或数据守卫
6. 参考记录与当前 UI 结构明显不一致，需要生成新的运行时候选

进入进一步 Grep 保底前必须记录 `fallback_reason`。已有参考和运行时路径可用时禁止继续读取源码；不得以“源码更方便”为理由跳过运行时查询。

### 限定读取范围与查询过程

1. 固定当前目标 UI、目标控件语义和预期状态，不得无边界扫描整个项目
2. 若对应 `../ui-quick-reference/references/{feature_id}.md` 已存在，先读取；不存在时先记录缺失，不得中断。信息不足时，只 Grep 当前目标 `*_AutoGen.cs`、`*_Logic.cs`，必要时再读取直接子控件的 AutoGen/Logic
3. 从 AutoGen 提取 summary 节点名、字段名、组件类型和 `uiBinder` 绑定关系
4. 从 Logic 提取 `Event_Register()`、事件回调、数据守卫、目标 UIID、`CreateUIAsync` 或预期状态变化
5. 形成 `字段名 → 运行时节点候选 → 组件类型 → 父链/UI 根 → 回调/守卫 → 目标状态` 候选链
6. 回到 Unity 验证候选节点存在、active、组件和父链匹配；再通过本 skill 原有运行时触发方式执行，并独立验证操作后的页面或业务状态
7. 只有本次运行时验证成功的路径、别名和触发方式才允许增量写入 `references/{feature_id}.md` 或 `known-issues.json`

### 记录要求

每次触发保底查询，必须在 `{run_dir}-run-log.json` 的对应步骤记录：

- `fallback_reason`：进入保底的运行时失败或歧义
- `source_files`：实际读取的参考、AutoGen/Logic 文件
- `control_identity`：字段名、运行时节点名、组件类型、UI 根与父链
- `logic_chain`：回调、守卫、目标 UIID 或预期状态
- `runtime_verification`：存在性、active、组件、父链及操作前后状态
- `action_result`：最终触发方式、状态推进与 verdict

### 禁止事项

- 禁止每次点击前默认读取 AutoGen/Logic，或扫描与当前目标无关的源码
- 禁止把 AutoGen 字段、Logic 回调、UIID 或 `CreateUIAsync` 当作运行时事实或 `passed` 证据
- 禁止把源码中的字段名直接当成运行时节点路径
- 禁止用反射直接调用 Logic 回调替代第一优先的控件触发；反射业务方法仍只保留在原“终极兜底”
- 禁止将未经当前运行时验证的候选写入缓存、reference 或 known-issues
- 禁止在保底查询中新增 TestHelper API、修改 AutoGen/Logic 或创建第二套执行流程

## UI节点定位策略

正常流程先读取 `ui-quick-reference` 离线参考，再结合运行时参考/缓存路径和最小目标 UI 快照定位节点。以下 AutoGen/Logic 源码解析规则只在已经记录 `fallback_reason` 后执行，用于补齐候选；候选仍必须回到 Unity 验证。

### 路径查找规则
1. **参考路径优先**：先从 `../ui-quick-reference/references/{feature_id}.md` 获取字段/回调/节点候选，再使用 `references/{feature_id}.md` 或缓存的完整路径做 `GameObject.Find`
2. **最小范围发现**：路径失败时只抓当前目标 UI 根，确认实际父链、节点名和组件
3. **源码语义保底**：仍无法定位或存在歧义时，才从 `UI名称 + "_AutoGen"` 的 summary/字段和 `UI名称 + "_Logic"` 的事件/守卫生成候选
4. **运行时闭环**：候选命中后验证 active、组件、父链和状态推进，再记录实际路径

### AutoGen/Logic 候选解析顺序（仅保底触发后）

#### 1. 定位 Logic 与 AutoGen 文件
1. **Logic 文件**：UI 功能脚本通常命名为 `UI_功能名_Logic.cs`
2. **AutoGen 文件**：同名 `UI_功能名_AutoGen.cs` 文件包含字段定义和注释
3. **查找 `Event_Register()` 方法**：按钮的注册事件都在此方法中
4. **分析按钮/开关注册形式**：
   ```csharp
   // GameButton（旧版 Unity UI 事件）
   UIEventListener.Get(按钮对象).onClick = OnButtonClick;
   // GameButton（新版）
   按钮对象.clickable.RegisterCallback<ClickEvent>(OnButtonClick);
   //GameButton（新版，绑定对象）
   按钮对象.onClick = () => OnButtonClick(); 或者 按钮对象.onClick = OnButtonClick；
   
   // GameToggle（页签类切换，如 hero_Tab、level_Tab）
   // 在 Event_Register() 中通过 tgl.onValueChanged.AddListener 注册
   // 例如：tgl.onValueChanged.AddListener(OnHeroTabChanged);
   // 触发方式：直接设置 toggle.isOn = true 即可触发回调
   ```

#### 2. 在 Logic 文件中查找点击事件
1. **优先在 `UI名称 + "_Logic"` 中查找**注册的点击事件
2. **ScrollView 内的元素**：若点击事件不在 Logic 中，查看是否是 ScrollView 里的元素
3. **item 的点击事件**：在对应的 `item名称 + "_Logic"` 中查找（如 `HeroItem_Logic`）或者 `UC_XXXXitem名称 + "_Logic"` 中查找（如 `UC_Item_hero_card_Logic`）

#### 3. 角色或棋子列表项路径模式

ScrollView 列表中的 Item 项命名统一为 `EditorRuntime_Content_N`（N 从 0 开始递增），其父级为 `Content` 节点。**已知 UI 列表首个 item 的完整固定路径如下，直接拼接即可 O(1) 定位，禁止递归遍历：**

| UI 名称 | 首个 Item 完整路径 | 进入目标 |
|---------|-------------------|---------|
| `UI_ToyMainList` | `UI_ToyMainList/ScrollView/Viewport/Content/EditorRuntime_Content_0` | 点击进入 `UI_ToyTrain`（棋子详情培养） |
| `UI_HeroMainList` | `UI_HeroMainList/UC_HeroList_Page/ScrollView/Viewport/Content/EditorRuntime_Content_0` | 点击进入英雄详情 |
| 通用英雄列表 | `UI_XXX/XXXX/ScrollView/Viewport/Content/EditorRuntime_Content_N` | 英雄项内按钮 `heroicon`（点击进入详情） |

**列表项点击通用流程（已知路径 → 直接 GameObject.Find → 读数据 → 校验守卫条件 → 触发）：**

```csharp
// 步骤1：直接用已知路径拿首个 item，O(1) 无需递归
var item0 = GameObject.Find("UI_ToyMainList/ScrollView/Viewport/Content/EditorRuntime_Content_0");
// 或英雄列表：
// var item0 = GameObject.Find("UI_HeroMainList/UC_HeroList_Page/ScrollView/Viewport/Content/EditorRuntime_Content_0");

// 步骤2：读取关键字段校验守卫条件（如 frag=0/0 表示 Owned 可点击）
var fg = item0.transform.Find("txt_suipian"); // 或递归 FindR(item0.transform, "txt_suipian", 5)
var fragText = fg != null ? ((GameFramework.Logic.GameText)fg.GetComponent(typeof(GameFramework.Logic.GameText))).text : "?";

// 步骤3：校验通过后获取 GameButton 并触发 onClick
if (fragText == "0/0") { // OwnState == Owned
    var gbNode = item0.transform.Find("GameButton"); // 或 FindR(item0.transform, "GameButton", 5)
    var gbType = typeof(GameFramework.Logic.GameButton);
    var gb = gbNode.GetComponent(gbType);
    var action = gbType.GetProperty("onClick").GetValue(gb);
    if (action != null) action.GetType().GetMethod("Invoke").Invoke(action, null);
}
```

**⚠️ 列表项点击前必须校验业务守卫条件**：`item_toy_card_Logic` 的 onClick Lambda 内部检查 `_toyData.OwnState != Owned` → early-return。只点击满足守卫条件的项（如 `frag=0/0`），跳过 `frag=0/30` 或 `locked` 的项。

**若首个 item 不满足条件，用索引递增遍历**：
```csharp
var content = GameObject.Find("UI_ToyMainList/ScrollView/Viewport/Content");
for (int i = 0; i < content.transform.childCount; i++) {
    var item = content.transform.GetChild(i); // EditorRuntime_Content_i
    // ... 校验 + 触发
}
```

### AutoGen 字段名 ≠ 运行时节点名——通过注释定位
**常见陷阱**：AutoGen 中声明的字段名（如 `icon_4_btn`）**不是**场景中的实际节点名，直接搜索字段名会找不到按钮。

**正确做法**：以 AutoGen 字段的 XML 注释作为运行时节点名来搜索。

**示例**：
```
// AutoGen 中：
/// <summary>
/// btn_shouchong
/// </summary>
public GameButton btn_shouchong_1_btn;
```
→ 运行时节点名是 `btn_shouchong`，而非 `btn_shouchong_1_btn`

**操作流程**：
1. 读取 `UI_XXX_AutoGen.cs` 文件
2. 找到目标字段（如 `btn_shouchong_1_btn`）上方的 `/// <summary>xxx</summary>` 注释
3. 在 `capture_scene_snapshot` 场景树中搜索节点名 `xxx`（即注释内容）
4. 找到节点后，获取其 `GameButton` 组件并触发

**递归查找辅助代码**：
```csharp
Transform FindNodeByComment(Transform root, string comment) {
    if (root == null) return null;
    if (root.name == comment) return root;
    foreach (Transform child in root) {
        var result = FindNodeByComment(child, comment);
        if (result != null) return result;
    }
    return null;
}
```

### 常见UI路径规律
- **GameTabToggleGroup** 位于 `UI_XXX/Bottom/GameTabToggleGroup_1/`
- **UC_HeroList_Page / UC_ToyStarUp** 等子 UI 位于对应的 `UI_XXX/` 下，而非 GameTabToggleGroup 下

### 动态路径处理
- `GameObject.Find(path)` 仅匹配**激活**的根节点
- Content 可能是动态生成，路径不固定
- 递归查找：
```csharp
Transform FindNode(Transform tr, string targetName) {
    if (tr.name == targetName) return tr;
    foreach (Transform child in tr) {
        var result = FindNode(child, targetName);
        if (result != null) return result;
    }
    return null;
}
```

### 布局区域语义枚举与保底查找
当用例按区域描述 UI（如 A/B/C/D/F 区），但运行时节点名与用例或参考文档不一致时，禁止只按单一路径或单组名称判失败；必须执行“精确路径 → 根路径发现 → 语义枚举 → 结构/组件语义 → 截图证据”的分层查找，并在运行记录中写明命中策略。

#### 区域候选名枚举
| 区域语义 | 典型用途 | 必查候选名（大小写不敏感，支持 contains） | 结构/组件兜底 |
|---------|----------|------------------------------------------|---------------|
| `areaA` / `currency` / `resource` | 货币、资源、体力、钻石 | `money`、`gold`、`diamond`、`currency`、`resource`、`ziyuan`、`Img_common_ziyuandi`、`Num`、`add` | 同一父节点下存在多个 `GameText` 数值和加号按钮，或截图可见资源栏 |
| `areaB` / `display` / `selected` / `onscene` | 展示区、已选棋子、出战/场上信息、主体展示 | `onscene`、`OnScene`、`bg1`、`bg2`、`bg3`、`display`、`show`、`selected`、`detail`、`preview`、`model`、`card`、`Pre_wanju_daka` | 若无独立展示节点，允许用“首个可见已拥有卡片 + 图片/等级/阵营/星级/占位信息 + 截图主体区域”作为语义命中 |
| `areaC` / `list` / `library` / `scroll` | 棋子库、列表、背包、卡片容器 | `ScrollView`、`Viewport`、`Content`、`EditorRuntime_Content_`、`item`、`card`、`library`、`list` | `GameScrollRect_V2` 或 `ScrollRect` 下存在多个动态子项，子项包含图标/等级/按钮 |
| `areaD` / `filter` / `edit` / `team` | 筛选、编队、合成、切换按钮 | `btn_biandui`、`biandui`、`team`、`formation`、`filter`、`RadioButtonItemTemplate`、`UC_CommonRadioGroup`、`btn_wanju`、`btn_hecheng` | 同一父节点下存在多个 `GameButton`/Toggle，文本体现筛选或编辑入口 |
| `areaE` / `tab` / `subpage` | 详情页子页签、升级、升星、技能属性 | `tab`、`toggle`、`daohang`、`shengji`、`shengxing`、`skill`、`attr`、`UC_ToyLvUp`、`UC_ToyStarUp` | `GameTabToggleGroup` 或 ToggleGroup 下存在多个互斥页签，切换后子页面 active 变化 |
| `areaF` / `bottom` / `navigation` | 底部主导航 | `UI_MainBottom`、`Bottom`、`GameTabToggleGroup`、`main`、`home`、`bag`、`hero`、`toy` | 屏幕底部区域存在多个导航按钮，当前页签高亮 |

#### 查找顺序
1. 先用 `references/{feature_id}.md` 或已缓存完整路径做 `GameObject.Find(fullPath)`，命中则记录 `strategy=exactPath`。
2. 精确路径失败时，枚举所有同名 UI 根节点并回溯完整父路径；`capture_scene_snapshot` 必须改用发现的完整路径，例如 `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_XXX`，记录 `strategy=rootDiscovery`。
3. 在 UI 根节点内按候选名做大小写不敏感匹配；同时用 AutoGen 注释名补充候选，记录 `strategy=nameAlias` 与实际节点路径。
4. 候选名仍未命中时，用组件和结构语义兜底：列表看 `ScrollRect/GameScrollRect_V2 + Content 子项数`，按钮组看多个 `GameButton/Toggle`，资源栏看多个数值文本与加号按钮，展示区看图片/等级/星级/阵营/已拥有卡片组合，记录 `strategy=semanticFallback`。
5. 语义证据仍不足时才截图；截图能证明用户可见区域满足预期时，允许通过，并记录 `strategy=visualFallback` 与截图路径。

#### 判定规则
- 单个预期路径、单个节点名或单个区域别名未命中，不得直接判 `failed`。
- 区域布局类用例至少完成候选名枚举和结构/组件语义兜底后，才允许判失败。
- 精确路径未命中但语义兜底满足用户可见预期时，结果记为 `passed`，证据中写明“路径别名未命中，语义兜底命中”。
- 精确路径未命中且语义兜底无法证明 UI 状态时，优先记为 `blocked` 或 `测试流程问题`，不得归因到业务代码。
- 每次发现实际路径或别名后，必须写入运行日志的 `path_aliases` / `strategy` 字段，并在报告“节点证据摘要”中保留，供后续补充 `references/{feature_id}.md`。

### 组件获取反射写法
```csharp
var gameBtnType = typeof(GameFramework.Logic.GameButton);
var btn = btn_shouchong_1_btn.GetComponent(gameBtnType);
var executeMethod = gameBtnType.GetMethod("ExecuteButtonClick",
    BindingFlags.Public | BindingFlags.Instance);
executeMethod.Invoke(btn, null);
```

## 用例范围分类规则
每条用例需要被归类为以下之一：

- **functional**
  - 包含 UI 打开/关闭
  - 包含点击/输入/拖拽/聚焦
  - 包含动画、协程、异步等待
  - 包含场景流转
  - 包含视图层状态验证

- **非功能测试范围**
  - 代码的纯逻辑/数据/公式验证
  - 这类用例在报告中标记并跳过

- **blocked**
  - 功能目标或预期结果缺失，无法判断测试是否通过
  - 输入文档不完整到无法形成可执行步骤
  - 步骤依赖完全不可观测行为
  - 注意：缺少 UIID 或目标 UI 路径本身不构成阻塞；应优先按方式一抓取默认 UI 根节点场景结构并通过 evaluate 触发按钮，失败后再按方式二截图预估并模拟点击。

## 点击执行流程
执行测试时优先使用已存在的 `ui-quick-reference` 离线参考，再结合已验证运行时路径定位控件，并使用本 skill 原有 `evaluate` 触发方式操作。若离线参考不存在，不得直接 Read 报错；应记录缺失并继续使用运行时参考、最小运行时查询和受控 AutoGen/Logic 保底。只有参考不足、运行时路径失效、目标身份有歧义或操作后无状态推进时，才限定查询 AutoGen/Logic 源码补齐候选；源码候选验证失败后再进入截图模拟点击。任何触发返回成功都必须独立验证页面或业务状态。

### 点击执行流程（四层递进）

#### 第一优先：ui-quick-reference 离线参考 + 已验证运行时路径 + evaluate 触发控件

1. 先检查 `../ui-quick-reference/references/{feature_id}.md`；存在时读取字段映射、按钮回调、Prefab 节点和子 UI 列表，不存在时记录“离线参考未生成”并继续
2. 再检查并读取 `references/{feature_id}.md`、本会话缓存路径和 `{feature_id}-known-issues.json`
3. 对目标绝对路径做最小运行时校验，确认节点存在、`activeInHierarchy=true`、组件类型和父链匹配
4. 命中已验证 known-issues 时直接复用其中的有效触发方式；否则按组件类型使用本 skill 现有 `GameButton`、`GameToggle`、长按或拖拽触发规则
5. 触发动作与异步状态轮询分开执行；按 300-500ms/次、最长 8 秒验证目标页面或业务状态
6. 参考不足、缓存路径失效、目标身份不明确或状态未推进时停止盲试，记录原因并进入第二优先

evaluate 完整示例：
```csharp
var go = GameObject.Find("GameEntry/Builtin/UI/Canvas/UI_Main/page_main/btn_shouchong");
if (go == null) return "not found";
if (!go.activeInHierarchy) return "inactive";
var btn = go.GetComponent<GameFramework.Logic.GameButton>();
if (btn == null) btn = go.GetComponentInChildren<GameFramework.Logic.GameButton>(true);
if (btn == null) return "no GameButton";
btn.ExecuteButtonClick();
return "invoked: " + go.name;
```

---

#### 第二优先：AutoGen/Logic 语义保底定位 + 运行时验证

仅在第一优先失败或存在歧义时执行“AutoGen/Logic 语义保底查询规则”：

1. 记录 `fallback_reason`，限定目标 UI、控件语义和预期状态
2. 先查对应 ui-quick-reference；仍不足时仅 Grep 当前目标 AutoGen/Logic 和必要的直接子控件
3. 生成控件身份、父链、组件、回调/守卫及目标状态候选，不直接调用 Logic 回调
4. 回到 Unity 验证候选存在、active、组件和父链，并通过第一优先已有的控件触发方式执行
5. 独立轮询操作后的页面或业务状态；验证成功后才允许更新 reference/known-issues 或判定用例
6. 将 `source_files`、`control_identity`、`logic_chain`、`runtime_verification`、`action_result` 写入运行记录

AutoGen/Logic 查询本身不能作为通过证据；候选无法通过运行时验证时不得写入缓存，并进入第三优先。

---

#### 第三优先：截屏 + 预估位置 + 模拟点击（兜底第二层）
当 evaluate 触发无效时，使用截图预估坐标：

1. 调用 `mcp__mymcp__capture_screenshot` 获取截图
2. 在截图中目测预估按钮中心像素位置 `(px, py)`
3. 坐标转换：Unity 屏幕坐标原点在**左下角**
   - `unityX = px`
   - `unityY = 图片高度 - py`
4. 调用 `mcp__mymcp__simulate_click(screen_x=unityX, screen_y=unityY)`
5. **短轮询验证结果**（300-500ms/次，最长 8 秒早停），仍未达预期时截图作为失败证据

---

#### 终极兜底：反射调用业务方法
当以上三层都无法生效时（如长按、拖拽、EventTrigger 等特殊交互）：
- 通过 `Type.GetType("Namespace.ClassName, AssemblyName")` 获取类型
- `BindingFlags.NonPublic | BindingFlags.Instance` 反射调用私有业务方法
- 在测试报告中**必须标注**"终极兜底 + 路径 + 调用的具体方法"

---

### 等待时间要求（短轮询 + 早停，详见"执行效率优化规则 #5"）
**默认不再使用固定等待，改为操作后短轮询目标状态**：
- 轮询间隔：300-500ms 一次，检查目标状态（`activeInHierarchy`、字段值等）是否已达预期
- 命中预期立即继续，无需等满固定时长
- 早停超时上限：单次轮询最长 **8 秒**，超时仍未达到预期状态则判定该步骤失败并记录证据，不得无限等待
- 对已在"已知问题清单"中标记为"点击链路不稳定"的节点，**跳过轮询与重试，直接执行已验证的兜底方案**（如反射调用），并标注"因已知问题跳过标准点击"
- 仅当目标本身是纯视觉表现（如粒子特效、转场动画）且无法通过节点状态判断完成时，才允许退化为固定等待兜底（此时固定等待时长可参考：Tab/页签切换 2-3 秒、UI 打开/关闭 2-3 秒、列表刷新 3 秒），并在记录中标注"视觉动画，采用固定等待兜底"

**禁止在操作后不做任何状态检查就立即返回或继续**，必须通过轮询或（视觉场景下的）固定等待确认目标状态后再继续。以下截图步骤只适用于 evaluate 触发无效、需要模拟点击坐标、视觉状态无法由节点证明、或失败取证的场景；不得突破“每条 functional 用例最多 2 张截图”的收敛规则。
1. 调用 `mcp__mymcp__capture_screenshot` 拿到截图路径，用 `Read` 查看图片。
2. 在图片中由执行者**目测预估**目标按钮的大概中心像素位置 `(px, py)`（图片像素坐标的原点在**左上角**，Y 向下增大）。
3. 把预估像素坐标转成 Unity 屏幕坐标（Unity 屏幕坐标原点在**渲染区左下角**，Y 向上增大）：`unityX = px`，`unityY = 图片高度 - py`。
4. 直接调用 `mcp__mymcp__simulate_click(screen_x=unityX, screen_y=unityY)`。`simulate_click` 内部已通过 `UnityScreenToSystemScreenConverter.TryConvert` 完成桌面坐标转换，**不要在调用前自己转换桌面坐标、也不要把桌面坐标传给该工具**，否则会被二次转换点错位置。
5. 点击后优先通过页面状态、文本变化、业务状态读取或日志判断是否成功；只有节点状态无法证明、发生失败或属于视觉验证时，才截图补充证据。若成功，继续下一步。
6. 若预估点击失败、误点、坐标越界或点击后没有预期状态变化，可基于最新截图重试一次；仍失败时按失败证据归因。
7. `UnityScreenToSystemScreenConverter` 只支持 Windows Unity Editor，且坐标必须落在 `[0, Screen.width) × [0, Screen.height)` 范围内；越界时 `simulate_click` 会失败。

### TestHelper 通用封装 API

`TestHelper` 提供以下通用 API，编排层可直接调用，避免每次手写反射探路：

- **`TestHelper.CloseUI(string uiName)`** — 关闭/移除指定 UI（弹窗、面板、界面）。
  内部遍历程序集按类型名定位 `Game.Core.GameUISystem`（注意：不是
  `GameFramework.Logic.GameUISystem`），调用其 `Inst.RemoveUIImmediate(string)`
  立即移除；找不到该入口时兜底 `SetActive(false)`。
  返回 `ok:closed:{name}`（真实关闭）/ `ok:closed_force:{name}`（兜底）/
  `ok:already_closed:{name}` / `err:...`。
  注意：`RemoveUIImmediate` 是正确关闭方式，关闭后可正常 `OpenUI` 重建；
  不要用 `SetActive(false)` 作为首选关闭（会与 `GameUISystem` 状态不同步，
  导致无法重建）。
  使用示例：`return TestHelper.CloseUI("UI_TDHeroAll");`

- **`TestHelper.GetComponentByTypeName(GameObject go, string typeName, bool includeChildren = true)`** —
  按组件类型名取组件（兼容 HotFix 层/跨 dll 类型名无法 `typeof` 的场景，如
  `HeroItem_Logic`、`BaseUI`、`GameButton`、`GameText`）。
  `includeChildren=false` 只查自身；`true`（默认）查子节点。
  使用示例：`var logic = TestHelper.GetComponentByTypeName(item, "HeroItem_Logic");`
  `var gb = TestHelper.GetComponentByTypeName(heroicon, "GameButton", false);`

### 组件触发规则（本项目 UI 框架特例）
`GameFramework.Logic.GameButton` 的源码定义了 `Action onClick` 与 `Action<GameButton> onClick2`，`ExecuteButtonClick()` 是普通 GameButton 的默认触发入口，会进入按钮自身点击流程并触发对应回调。实际执行时必须先看 `references/{feature_id}.md` 与 `{feature_id}-known-issues.json` 中的已验证触发方式；无记录时默认先用 `ExecuteButtonClick()`，若状态不推进，再按下列组件特例兜底：

- **GameToggle**（继承 `Toggle`）：页签类切换（如 `hero_Tab`、`level_Tab`、`rouge_Tab`）。在 `Event_Register()` 中通过 `tgl.onValueChanged.AddListener` 注册回调。触发方式：直接设置 `toggle.isOn = true` 即可触发 `onValueChanged`，无需走反射。

  **重要**：GameToggle 的节点本身挂有 `GameToggle` 组件，可直接获取：
  ```csharp
  var toggle = heroTab.GetComponent<GameFramework.Logic.GameToggle>();
  toggle.isOn = true;  // 触发 onValueChanged 回调
  ```
- **GameTabItem**（节点位于 `GameTabToggleGroup_*` 下，同时挂 `GameImage` / `GameTabItem` / `GameButton`）：`ItemInit` 把 `OnClicked` 注册到 `GameButton.onClick2`。若 `ExecuteButtonClick()` 后页签状态未推进，直接调用 `btn.onClick2?.Invoke(btn as GameButton)`。
- **长按 / 拖拽按钮**（`EventTrigger.PointerDown/PointerUp` 实现的，如本项目 `shengjibtn` 的长按连升）：`simulate_click` 走不通时，先按已验证短按链路触发；如果短按被守卫拦截，再回退到反射调用业务方法作为终极兜底，并在报告中标注。
- **列表项 / HeroItem**（节点本身无 GameButton）：点击逻辑通常挂在子节点的 GameButton 上（如 `HeroItem.heroicon`），用 `GetComponentInChildren<GameButton>(true)` 找到挂点后默认先走 `ExecuteButtonClick()`；若状态不推进，再按该 feature reference 或 known-issues 中的已验证方式兜底。

### 提速技巧（经验总结）

经过多次测试实践，总结以下提速经验：

1. **普通 GameButton 默认优先使用 `ExecuteButtonClick()`，但以运行时验证结果为准**
   - 本项目 GameButton 源码中 `ExecuteButtonClick()` 会进入按钮自身点击流程，并在可点击条件满足时调用 `onClick` 和 `onClick2`
   - 若已知问题或本次验证表明该节点需要 Action 委托、`onClick2`、长按/拖拽或业务方法兜底，应直接使用已验证方式，不再重复标准点击
   - 使用反射调用：`gameBtnType.GetMethod("ExecuteButtonClick", BindingFlags.Public | BindingFlags.Instance).Invoke(btn, null)`
   - 示例代码：
   ```csharp
   var gameBtnType = typeof(GameFramework.Logic.GameButton);
   var btn = heroicon.GetComponent(gameBtnType);
   var executeMethod = gameBtnType.GetMethod("ExecuteButtonClick", BindingFlags.Public | BindingFlags.Instance);
   executeMethod.Invoke(btn, null);
   ```

2. **GameToggle（底部 Tab）触发直接设置 `isOn = true`**
   - 底部导航的 hero_Tab、level_Tab、rouge_Tab 都是 GameToggle 类型
   - 直接获取组件后设置 `isOn = true` 即可触发 `onValueChanged` 回调
   - **不需要反射**，直接获取 GameToggle 组件：
   ```csharp
   var toggle = heroTab.GetComponent<GameFramework.Logic.GameToggle>();
   toggle.isOn = true;  // 触发 onValueChanged 回调
   ```
   - 短轮询检查目标 UI 是否出现（300-500ms/次，最长 8 秒早停），无需固定等满 2-3 秒

3. **滑动列表 / 页签列表 Content 查找策略**
   - 滑动列表基础结构通常是 `ScrollView/Viewport/Content`；`ScrollView` 节点名可能被业务名替换，例如 `scr_H20V20`、`Down_YeQian`、`up_YeQianQieHuan`，但子结构仍优先按 `Viewport/Content` 查找。
   - 固定路径未命中时，不得直接判定列表为空；必须先查找挂载 `GameFramework.Logic.GameScrollRect`、`GameFramework.Logic.GameScrollRect_V2`、`UnityEngine.UI.ScrollRect` 等滑动组件的节点，再读取组件的 `content` 字段/属性或查找其子路径 `Viewport/Content`、`Content`。
   - `GameObject.Find(path)` 仅匹配**激活**的根节点；Content 可能动态生成或父节点重命名，应先用已知父路径缩小范围，再执行组件兜底查找，避免全树递归。
   - 推荐 helper：
   ```csharp
   Transform FindScrollContent(Transform root, string preferredName) {
       if (root == null) return null;
       string[] scrollTypeNames = new string[] {
           "GameFramework.Logic.GameScrollRect",
           "GameFramework.Logic.GameScrollRect_V2",
           "UnityEngine.UI.ScrollRect"
       };
       Transform[] nodes = root.GetComponentsInChildren<Transform>(true);
       foreach (Transform node in nodes) {
           if (!string.IsNullOrEmpty(preferredName) && node.name != preferredName) continue;
           foreach (string typeName in scrollTypeNames) {
               UnityEngine.Component component = node.GetComponent(typeName);
               if (component == null) continue;
               System.Reflection.PropertyInfo contentProperty = component.GetType().GetProperty("content");
               Transform contentByProperty = contentProperty != null ? contentProperty.GetValue(component, null) as Transform : null;
               if (contentByProperty != null) return contentByProperty;
               System.Reflection.FieldInfo contentField = component.GetType().GetField("content");
               Transform contentByField = contentField != null ? contentField.GetValue(component) as Transform : null;
               if (contentByField != null) return contentByField;
               Transform contentByPath = node.Find("Viewport/Content") ?? node.Find("Content");
               if (contentByPath != null) return contentByPath;
           }
       }
       foreach (Transform node in nodes) {
           Transform contentByPath = node.Find("Viewport/Content") ?? node.Find("Content");
           if (contentByPath != null) return contentByPath;
       }
       return null;
   }
   ```

5. **获取 GameButton 组件的反射写法**
   ```csharp
   var gameBtnType = typeof(GameFramework.Logic.GameButton);
   var btn = heroicon.GetComponent(gameBtnType); // 用gameBtnType而非直接GetComponent<GameButton>()
   ```

7. **角色和玩具详情导航优化 — 按名称预定位 GameButton**
   - **优化方案**：进入玩具详情前，先在玩具列表（`UI_ToyMainList/.../ScrollView/Viewport/Content/EditorRuntime_Content_*/GameButton`）中按名称查找对应项，再触发点击进入详情
                  进入角色详情前，先在角色列表（`UI_HeroMainList/.../ScrollView/Viewport/Content/EditorRuntime_Content_*/GoButton`）中按名称查找对应项，再触发点击进入详情
   - 递归查找示例：
   ```csharp
   Transform FindHeroIconByName(Transform root, string heroName) {
       Transform FindRecursive(Transform t) {
           if (t.name == "heroicon") {
               var txt = t.GetComponentInChildren<GameFramework.Logic.GameText>();
               if (txt != null && txt.text.Contains(heroName)) return t;
           }
           foreach (Transform child in t) {
               var r = FindRecursive(child);
               if (r != null) return r;
           }
           return null;
       }
       return FindRecursive(root);
   }
   ```

8. **UILogic 字段名未知时的快速定位**
   - 读取业务状态（如升星界面的星星数）时，因字段名不熟悉导致多次 runtime_error
   - **优化方案**：先反射获取所有 `_txt` 字段名列表，再按名称取值
   ```csharp
   var fields = someType.GetFields()
       .Where(f => f.Name.EndsWith("_txt"))
       .Select(f => f.Name)
       .ToArray();
   return string.Join(",", fields);
   ```

9. **已知 UI 结构时直接用完整路径，避免递归查找**
   - 若已知节点的相对位置规律（如父节点已知、子节点名称固定），直接拼接路径比递归遍历更快
   - 例如：知道某按钮在 `CanvasX/UI_Y/Bottom/` 下，就直接用 `GameObject.Find("CanvasX/UI_Y/Bottom/BtnName")`

10. **列表/Grid 中按索引 vs 按名称的选择策略**
    - **直接用索引**（如 `Content/Item_0`）：列表顺序固定且已知时，节省递归查找和文本比对
    - **递归按名称查找**：列表顺序不确定、或需要在多个列表中定位时使用
    - 决策原则：先评估已知信息足够判断位置时，优先用索引路径；信息不足时再递归

11. **上阵/选中状态的视觉判断可辅助定位**
    - 部分 UI 中，选中或激活状态的节点会有特殊子节点（如 `onscenemask`、`Selected` 等）
    - 可通过 `off=true/false` 判断某项是否已上阵/选中，减少状态确认的 evaluate 调用

12. **GameTabItem 类型页签的 GameButton 查找策略**
    - 部分 TabItem 节点本身不挂 GameButton，GameButton 在其子节点上
    - 查找顺序：`GetComponent<GameButton>()` → null → `GetComponentInChildren<GameButton>(true)`
    - 先按该 feature reference / known-issues 中的已验证触发方式执行；无记录时先尝试 `ExecuteButtonClick()`，若页签状态未推进再走 `onClick2` 兜底

13. **父子 UI 层级关系未知时的快速定位**
    - 子 UI（如 UC_ToyStarUp）可能是父 UI（UI_ToyTrain）的子节点，而非独立 Canvas
    - 遇到 off=true 的节点时不要跳过，它可能是隐藏的子面板；通过递归查找可快速定位

15. **角色名称中文字符串比对用 IndexOf/Contains**
    - `GameText.text.IndexOf("角色名称") >= 0` 比正则或精确匹配更健壮
    - 避免依赖字符串长度或精确格式，Contains/IndexOf 更通用

18. **分步递归查找比一次性递归更快**
    - 当已知节点的直接父节点时，先用 `GameObject.Find(path)` 找到父节点，再 `GetChild()` 获取子节点
    - 比从根节点递归查找效率更高，减少不必要的遍历

19. **通过 FindObjectsOfType 快速确认 UI Canvas 是否存在**
    - 当不知道目标 UI 在哪个 Canvas 下时，用 `FindObjectsOfType<Canvas>()` 枚举所有 Canvas
    - 筛选活跃的 Canvas：`canvas.gameObject.activeInHierarchy && canvas.gameObject.name.Contains("UI_xxx")`

20. **测试前先确认账号英雄数据**
    - 通过 `GameScrollRect_V2.GetDataCount()` 或 `DataAndPosProviders.Count` 确认英雄列表数量
    - 数量<3时，跳过编辑阵容测试（用例要求上阵数量>=3）
    - 确认目标英雄是否在列表中，避免在错误英雄身上浪费时间

23. **编辑阵容下阵后的上阵操作**
    - 下阵后列表项的 GameButton 引用可能丢失，`ExecuteButtonClick` 无响应
    - 此时 `simulate_click` 点击列表项更可靠
    - 注意：`simulate_click` 后必须验证状态，不能依赖返回值判断成功；优先用 evaluate 读取节点/文本/业务状态，无法证明或失败时再截图取证

24. **连续 simulate_click 后必须状态确认**
    - `simulate_click` 成功不等于 UI 响应（如面板切换、动画未完成等）
    - 每次 `simulate_click` 后优先读取节点、文本、列表数量或业务字段确认结果；只有状态不可证明、失败取证或视觉验证时才截图

28. **PlayMode重进后UI加载时序**
    - `enter_test_scene` 后UI未完全加载时节点可能找不到
    - 先用一次状态枚举确认当前画面状态；仍无法判断时，再抓场景快照或截图，避免反复等待

31. **批量evaluate执行** - 多个不相关的操作合并到一次evaluate
    ```csharp
    // 反面例子：3次evaluate
    evaluate(() => { clickBtn1(); return "ok"; });
    evaluate(() => { clickBtn2(); return "ok"; });
    evaluate(() => { clickBtn3(); return "ok"; });

    // 优化：1次evaluate
    evaluate(() => {
        clickBtn1();
        clickBtn2();
        clickBtn3();
        return "all clicked";
    });
    ```

32. **状态批量读取** - 多个用例的状态验证一次返回
    ```csharp
    // 反面例子：每个用例单独验证
    evaluate(() => { return GetHeroCount(); }); // TC-001
    evaluate(() => { return GetItemState(); }); // TC-002

    // 优化：一次返回所有状态
    evaluate(() => {
        return "heroes=" + GetHeroCount() + ", items=" + GetItemState();
    });
    ```

33. **跳过截图原则** - evaluate可验证时不用截图
    - **用截图**：需要验证视觉布局、坐标位置、UI动画
    - **不用截图**：节点存在性、状态变化、数据验证
    - 每次截图约3-5秒，避免不必要的截图

34. **用例合并策略** - 相关用例连续执行不重复加载
    - **合并场景**：TC-001/002/003 都是英雄列表界面，可以一起验证
    - **跳过前置**：用例2的前置条件=用例1的后置条件时，合并执行
    - **状态复用**：上阵/下阵操作后的状态被后续用例使用时，不还原状态

35. **测试耗时统计** - 记录每个阶段耗时便于分析
    ```csharp
    // 开头记录
    return "TestStart:" + System.DateTime.Now.ToString("HH:mm:ss.fff");

    // 结尾记录
    return "TestEnd:" + System.DateTime.Now.ToString("HH:mm:ss.fff");
    ```

36. **并行工具调用** - 独立的MCP调用可并行
    - `capture_scene_snapshot` 和 `query_logs` 可并行
    - 但 `evaluate` 和 `simulate_click` 必须串行（依赖时序）

37. **递归 FindNode 必须处理 null 参数**
    ```csharp
    // 错误：tr 为 null 时会在第一行 tr.name 抛出 NullReferenceException
    Transform FindNode(Transform tr, string targetName) {
        if (tr.name == targetName) return tr;  // ❌ tr 可能为 null
        ...
    }

    // 正确：开头加 null 检查
    Transform FindNode(Transform tr, string targetName) {
        if (tr == null) return null;
        if (tr.name == targetName) return tr;
        ...
    }
    ```

38. **反射中 BindingFlags 必须用完整限定名**
    - 本项目 MCP evaluate 环境不能直接写 `BindingFlags.Public`，需用 `System.Reflection.BindingFlags.Public`
    - 建议统一用 `System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance` 避免歧义

39. **递归函数名不要与局部变量名冲突**
    - 若写了 `var onscenenode = FindNode(...)` 后，内部又引用 `onscenenenode`（拼写错误），编译器会报"identifier does not exist"
    - 建议局部变量用短名如 `node`/`n`，函数参数用完整名避免冲突

40. **状态枚举优先于反复 evaluate 试探**
    - 当不确定当前 UI 状态时（如导航后不知道在哪个界面），不要连续发多个 evaluate 试探
    - 先用一次 evaluate 枚举活跃 Canvas、目标子 UI 和关键 Selected 状态；仍无法判断或需要视觉证据时，再截图或 `capture_scene_snapshot`

41. **GameToggle.isOn 不一定反映真实 UI 状态**
    - `toggle.isOn = true` 赋值后，Toggle 可能已触发 but 面板切换协程尚未完成
    - 以子 UI 是否存在、Selected 节点、关键文本或列表状态确认真实切换；节点状态无法证明时再截图确认，不以 `isOn` 返回值为转移

42. **批量操作后立即验证状态**
    - 在一次 evaluate 内完成多个操作后，不要直接返回成功
    - 应在 evaluate 末尾读取关键状态并返回，由返回值确认操作真实结果

43. **simulate_click 坐标参考截图已知元素**
    - 估算坐标时，以截图中的已知 UI 元素为参照（如底部 Tab 高度、顶部资源栏位置）
    - 避免漫无目的的估算，可先截图确认当前界面布局再预估

44. **AdapterArea 下可能有多个 Canvas**
    - `GameEntry/Builtin/UI/AdapterArea/` 下有 Canvas0~Canvas6 等多个 Canvas
    - 目标 UI 不在预期 Canvas 时，用递归查找定位，而非仅靠固定路径拼接

45. **Onscene 节点 bg1/bg2/bg3 可直接用路径访问**
    - 上阵区域 `onscenenode` 下有固定名称的 bg1/bg2/bg3 子节点
    - 已知上阵槽位索引时，直接拼接路径如 `onscenenode/bg1` 比递归查找更快

46. **打印当前 UI 所有点击事件（调试辅助）**
   例如，在执行测试过程中，当需要了解当前界面的所有可点击按钮时，使用以下 evaluate 代码打印所有 GameButton 及其事件：
   ```csharp
   var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea");
   var btns = root.GetComponentsInChildren<GameFramework.Logic.GameButton>(true);
   var sb = new System.Text.StringBuilder();
   sb.AppendLine("Total GameButtons: " + btns.Length);
   foreach (var b in btns) {
       var p = b.transform.parent != null ? b.transform.parent.name + "/" + b.name : b.name;
       var hasOnClick = b.onClick != null; // GameButton.onClick 是 Action 类型
       sb.AppendLine(p + " (onClick:" + hasOnClick + ")");
   }
   return sb.ToString();
   ```
   该代码会返回类似：
   ```
   Total GameButtons: 27
   LevelInfo/arrowBtn (onClick:True)
   root/boxClose (onClick:True)
   ...
   ```
   **使用场景**：
   - 刚进入一个 UI 界面后，不知道有哪些按钮可以点击
   - 点击事件定位困难时，先打印所有按钮再针对性查找
   - 配合截图，确认当前界面布局与打印的按钮列表对应

47. **Logic 实例缓存 helper（关键提速，必须使用）**
    反射查找 Logic 实例（遍历 assembly → 找 type → 找 adapter → 读 m_Instance）单次约 1.5k tokens。**第一次拿到后必须缓存，后续禁止重复探测**：
    ```csharp
    // ===== 第一次：完整探测并缓存 =====
    var allTypes = System.AppDomain.CurrentDomain.GetAssemblies();
    System.Type t = null;
    foreach (var asm in allTypes) {
        var x = asm.GetType("HotFix_Project.UI_ToyMainList_Logic");
        if (x != null) { t = x; break; }
    }
    var root = GameObject.Find("UI_ToyMainList");
    var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
    var adapter = typeof(GameFramework.Logic.BaseUI)
        .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
        .GetValue(baseUI);
    var logic = adapter.GetType()
        .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
        .GetValue(adapter);
    // 缓存到 PlayerPrefs
    UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
    UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_ToyMainList");
    return "cached:" + t.FullName;

    // ===== 之后每次 evaluate：用缓存路径快速拿 =====
    var t2 = System.Type.GetType(UnityEngine.PlayerPrefs.GetString("__test_logic_type__"));
    var root2 = GameObject.Find(UnityEngine.PlayerPrefs.GetString("__test_logic_root__"));
    var lg = root2.GetComponent<GameFramework.Logic.BaseUI>()
        .GetType().GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
        .GetValue(root2.GetComponent<GameFramework.Logic.BaseUI>())
        .GetType().GetField("m_Instance", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
        .GetValue(/* adapter */);
    // 单次状态读取从 1500 tokens 降到 400 tokens
    ```

48. **最小化节点读取 helper（关键提速，必须使用）**
    不要每次都用 `capture_scene_snapshot` 或全树递归去查 UI 节点状态。**用本 helper 一次性批量返回目标 UI 的关键状态**：
    ```csharp
    // 把所有要确认的状态合并到一次 evaluate 返回
    var sb = new System.Text.StringBuilder();
    var root = GameObject.Find("UI_ToyMainList");

    // 1) 上阵区域 3 槽位状态
    foreach (var slot in new[] { "bg1", "bg2", "bg3" }) {
        Transform bg = null;
        foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
            if (t.name == slot) { bg = t; break; }
        if (bg == null) { sb.AppendLine(slot + ":missing"); continue; }
        var lev = bg.Find("levbg/lev");
        var levTxt = lev != null ? lev.GetComponent<GameFramework.Logic.GameText>() : null;
        var iconImg = bg.Find("icon")?.GetComponent<GameFramework.Logic.GameImage>();
        sb.AppendLine(slot + ":lev=" + (levTxt != null ? levTxt.text : "")
            + ",icon=" + (iconImg != null && iconImg.sprite != null ? "yes" : "no")
            + ",active=" + bg.gameObject.activeInHierarchy);
    }

    // 2) HeroItem 列表状态（每项 ID + 名称 + 上阵标记）
    var hits = new System.Collections.Generic.List<Transform>();
    foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
        if (t.name.StartsWith("EditorRuntime_Content_")) hits.Add(t);
    hits.Sort((a, b) => string.Compare(a.name, b.name));
    foreach (var h in hits) {
        var mask = h.Find("onscenemask")?.gameObject;
        var nameTxt = h.GetComponentInChildren<GameFramework.Logic.GameText>(true);
        sb.AppendLine(h.name + ":name=" + (nameTxt != null ? nameTxt.text : "")
            + ",onScene=" + (mask != null && mask.activeInHierarchy));
    }

    // 3) 编辑模式状态（反射读 m_IsEditMode）
    var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
    var ad = typeof(GameFramework.Logic.BaseUI).GetField("m_MonoInvocationAdapter",
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(baseUI);
    var lg = ad.GetType().GetField("m_Instance", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(ad);
    var editMode = lg.GetType().GetField("m_IsEditMode",
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).GetValue(lg);
    sb.AppendLine("editMode=" + editMode);

    return sb.ToString();  // 单次 evaluate 返回 3 块状态，约 600 tokens
    ```
    **禁止**：
    - 禁止 1 个状态发 1 次 evaluate（TC-001/002/003 应合并为 1 次）
    - 禁止用 capture_scene_snapshot 替代本 helper（snapshot 至少 3k tokens）
    - 禁止在 helper 内 try-catch 包装大量反射后返回完整 stack

49. **进入 AutoGen/Logic 保底后，Grep 优先于 Read 查 UI 文件**
    ```bash
    # ❌ 反例
    Read(UI_ToyMainList_Logic.cs)  # 全文 705 行 ~25k tokens

    # ✅ 正例
    Grep("_selectedTab|_selectedCampFilter|_toyCardItemPool|_cachedToyCardDataList", UI_ToyMainList_Logic.cs)
    Grep("btn_wanju_1_1_btn", UI_ToyMainList_AutoGen.cs)  # 找按钮运行时节点名
    ```
    本条仅在运行时查询失败并记录 `fallback_reason` 后适用。完整读取 Logic.cs 仅在排查深层 bug 时进行，且**仅读 Grep 命中的相关函数体**（offset/limit 限定行范围）。

50. **类型查找失败时立刻返回短错误，禁止循环重试**
    ```csharp
    // ❌ 反例：失败后多次 evaluate 重试
    evaluate(找 type) → null → evaluate(遍历 assembly) → ... → evaluate(改路径) → ...
    // 每次失败都带回 stack trace，累计 5k+ tokens

    // ✅ 正例：1 次 evaluate 内完成所有尝试并返回短摘要
    var sb = new System.Text.StringBuilder();
    System.Type t = null;
    try {
        t = System.Type.GetType("HotFix_Project.UI_ToyMainList_Logic, CyStarRoad");
        if (t != null) sb.AppendLine("direct_ok");
        else {
            foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
                t = asm.GetType("HotFix_Project.UI_ToyMainList_Logic");
                if (t != null) { sb.AppendLine("scan_ok:" + asm.GetName().Name); break; }
            }
        }
        if (t == null) return "type_null";  // 短字符串，不带 stack
    } catch (System.Exception e) {
        return "err:" + e.Message.Substring(0, System.Math.Min(60, e.Message.Length));
    }
    ```

51. **UI 遮挡观察 helper（必须使用）**
    每个用例步骤确认目标 UI 打开后，调用测试包内 `TestHelper.CheckBoundUiReady()` 和 `TestHelper.ObserveOverlay()` 一次性返回根、Logic、Canvas 与遮挡证据。不得维护项目名 `keepSet`，不得自动关闭未知 UI；只有当前 Case 已提供明确关闭操作时才允许关闭并复查。
    ```csharp
    var ready = TestHelper.CheckBoundUiReady();
    var overlay = TestHelper.ObserveOverlay();
    // ready 不是 ready: 或 overlay 含 blocker= 时，只写入证据并停在当前 Case。
    // 不得根据 UI 名称猜测关闭对象，也不得 SetActive(false) 清理未知 UI。
    return ready + "|" + overlay;
    ```
    - **触发时机**：每次目标 UI 就绪后、点击或验证前执行一次 `CheckBoundUiReady() + ObserveOverlay()`。
    - **处理方式**：`clear=true` 时继续；出现 `blocker=` 时只记录证据，未提供当前 Case 关闭操作时不处理。
    - **检测范围**：测试 helper 只返回高于目标且带输入 Raycaster 的活跃 Canvas，不依赖 UI 名称白名单。

### 点击失败时的排查顺序
1. **第一优先失败**：缓存/参考路径的运行时校验或控件触发失败 → 进入第二优先 AutoGen/Logic 语义保底
2. **第二优先失败**：源码候选无法通过运行时验证或触发后无状态推进 → 进入第三优先截图模拟点击
3. **第三优先失败**：simulate_click 失败 → 进入终极兜底反射调用业务方法
4. 若所有方式都无法确认目标或结果，按证据归因为 `blocked` 或相应失败类型

## 执行工作流
1. 校验输入：确认功能测试需求存在；若未提供 `feature_id`，根据任务标题、功能名或测试目标推断 kebab-case 标识。
2. **读取 UI 参考并最小运行时查询**：按优先级依次执行——
   - 优先查 `../ui-quick-reference/references/{feature_id}.md`，获取 AutoGen 字段映射、按钮回调映射、Prefab 节点和子 UI 列表
   - 再查 `references/{feature_id}.md`、本会话缓存和 known-issues，复用已验证节点树、路径、触发方式与分组建议
   - 对候选路径执行最小 `GameObject.Find` / `evaluate`；无候选时只抓当前目标 UI 根的最小快照
   - 仅当两处参考不足、路径失效、目标有歧义或状态不推进时，再限定读取当前目标 AutoGen/Logic
   - 所有离线候选必须回到 Unity 验证；离线 reference 缺失只记录 `query_reference` 缺陷并继续执行。确认目标 UI 后，必须立即创建运行时 reference 初版，不能等到测试结束或下次测试
3. 解析用例：必须完整读取输入文档中的全部用例后，再解析为统一结构：`{CaseId, Title, PreConditions, Steps[], PostConditions, UiTargets[]}`。不得只读取文件开头、预览内容、前 N 条、当前屏幕可见行、示例用例或模型上下文中已经出现过的片段；若输入是 JSON/XLSX/Markdown/TXT，必须以文件实际内容为准完成全量枚举，并记录解析出的 `total_case_count` 和完整 `CaseId` 列表。
   - **输入编码与解析门禁（强制）**：对 JSON/Markdown/TXT 必须按文件字节内容以显式 UTF-8（兼容 BOM）读取，禁止依赖 PowerShell 默认编码、控制台代码页或乱码后的终端文本。PowerShell 读取 JSON 时使用 `[System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)`；Python 使用 `open(path, encoding="utf-8-sig")`。测试用例 JSON 按单个 JSON 文档解析；`*-run-log.json` 是 JSONL，必须逐行解析，禁止把整个日志文件交给单文档 JSON 解析器。
   - 在建立覆盖基准前记录 `input_path`、`input_sha256`、`input_encoding=utf-8`、`source_format`、`total_case_count` 和完整 `CaseId` 列表。解析成功前不得进入分类、分组或报告阶段。
   - 解析失败时保留原文件，不修复、转码、删减或猜测用例；记录原始异常、行号、列号和解析模式，并停止建立覆盖基准。仅当显式 UTF-8 重试成功且证据明确时，才可将前次失败归因于编码问题；否则只报告为输入解析阻塞。
4. 用例归类：将每条用例归为 `functional`、`非功能测试范围` 或 `blocked`。
5. **输出归类结果**：将用例分类结果返回给用户。
6. **用例分组**（详见"执行效率优化规则 #3"）：优先使用 `references/{feature_id}.md` 中的分组建议，但分组建议只能决定执行顺序和共享前置，不能减少输入文档中的 functional CaseId。若 reference 只列出少量历史分组或示例 CaseId，不得据此缩小本轮覆盖范围。
7. 初始化实时记录（详见"执行效率优化规则 #1"）：先确定本轮 `feature_id`，再按“默认永远 max+1，只有显式复测指定目录才覆盖”的规则确定 `run_dir={feature_id}-{sequence}`（如 `hero-list-0030`）；实际目录固定为 `Doc/AI开发文档/output/{feature_id}/{run_dir}`，必须先调用 `FunctionTestLogWriter.InitializeRunDirectory(runDir)` 创建该目录，禁止自行对逻辑 `runDir` 做目录拼接或 `Directory.CreateDirectory`，并初始化 `run-log.json` 和 `known-issues.json`，随后立即通过现有 `FunctionTestLogWriter.AppendEventRecord(...)` 写入一条 `event=setup` 的生命周期记录，再读取 known-issues；`setup.start_time` 必须早于编译和任何 PlayMode/登录/点击交互。若任一正式产物已存在，默认停止并换用新目录；只有用户明确复测/继续/修复/覆盖指定目录时才允许原位更新并显式允许覆盖。初始化还必须记录绝对 `input_case_path`、`run_dir`、`report_path` 和 `upload_json_path`。本步骤必须发生在编译检查、PlayMode、进场校验、用例执行和报告渲染之前；编译失败、PlayMode 失败、进场失败或环境阻塞也必须写入本轮 run-log 并生成 blocked 报告。初始化完成后必须立即把第 3-6 步得到的用例全集分类基准写入本轮 run-log 的 `event=classify` 记录，`details` 至少包含 `total`、`functional`、`functional_case_ids`、`non_functional_case_ids`、`blocked_case_ids`。第 15 步之前禁止调用 `render_functiontest_report.py`，测试前目录不存在不是失败原因；若误调用渲染脚本失败，不得退出，必须回到本步骤创建本轮目录并继续执行。不得在本步骤之前检查“三件套是否存在”并据此中断；不得对尚未创建/未执行的未来 `run_dir` 直接调用报告渲染脚本；不得读取历史 Markdown 报告来替代本轮执行计划或完成判断。
    - 初始化完成后、调用 `mcp__mymcp__execute_compile` 前，直接调用必须依次完成识图能力判断/截图开关/效果图对比开关和修复模式确认；workflow 调用必须校验启动前置阶段 A/B 已返回 `vision_capability`、`screenshot_enabled`、`effect_diff_enabled`、`repair_mode` 四个状态，不得重复询问。任何一个状态未完成前不得编译或进入 PlayMode。
8. **启动前代码编译检查**（强制，详见"硬性约束"）：先执行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/focus_unity_window.ps1 -ProjectRoot <当前工作区目录>`，保留脚本标准输出、错误输出和退出码。退出码 0（`UNITY_FOCUSED`）后立即调用 `mcp__mymcp__execute_compile`；退出码 3/4（`UNITY_FOUND_NO_WINDOW`/`UNITY_FOUND_FOCUS_FAILED`）但已找到当前项目 Unity 进程时，也立即尝试调用一次 `execute_compile`。若该调用无响应或超时，再重新执行聚焦脚本并重试一次编译；退出码 1/2（`PROJECT_ROOT_INVALID`/`UNITY_NOT_FOUND`）才禁止调用 `execute_compile`，按无安全编译目标记录环境阻塞并收口报告。明确获得编译成功或编译错误后不得重复重试。
   - 编译**通过**：继续进入 PlayMode。
   - 编译**失败**：立即终止后续执行，**不进入 PlayMode、不执行任何用例**；将完整报错信息（错误文件、行号、错误内容）写入 `{run_dir}-run-log.json`，直接进入报告生成阶段，报告 verdict 统一记为 `blocked`，并在"4. 失败与归因"中注明"启动前编译失败"+完整报错信息。允许修改代码时，后续按修复模式从编译检查重新开始；只测不修模式保留真实 `blocked`。
    - MCP 返回的完整原始响应必须同时写入 `RunLogDetails.raw_tool_response`，并标注 `tool_name`/`tool_phase`；不得只保留摘要或异常类型。测试流程进行期间只允许使用或修正本轮临时创建的编排/辅助代码；既有测试代码的修改属于测试结束后的独立工作。
9. **进入 PlayMode 与启动场景兜底**：先检查默认路径 `Assets/Scenes/Start.unity` 是否存在。
   - 默认路径存在时，调用 `mcp__mymcp__enter_test_scene`。若调用失败或超时，按原始失败原因写入本轮 `{run_dir}-run-log.json`，跳到第 15 步生成 `blocked` 报告；不得因为连接、编译、加载或就绪失败擅自改选其他场景。
   - 默认路径不存在时，扫描 `Assets/Scenes/` 下的 `.unity` 文件，优先列出名称包含 `Launcher`、`Launch`、`Boot`、`Init`、`Login`、`Start` 的候选及其完整项目相对路径；没有命中时列出该目录全部场景。必须询问用户确认本次测试的启动场景路径，不得自动选择候选。
   - 用户确认后，仅接受实际存在且格式为 `Assets/Scenes/<场景名>.unity` 的路径。调用 `mcp__mymcp__load_scene(<场景名>, false)`，确认场景已在 Build Settings 且已打开后，再调用 `mcp__mymcp__start_scene_play` 并确认 PlayMode 已进入；随后继续第 10 步的原有进场与 `TestBoot` 就绪检查。用户未提供、路径不合法、场景未加入 Build Settings、打开场景失败或进入 PlayMode 失败时，写入 `blocked` 报告，不得猜测路径或改写项目配置。
   - 本步骤的场景兜底必须写入 run-log：默认路径检查结果、候选列表、用户确认的路径、采用的工具调用与完整原始返回。使用兜底时记录 `fallback=load_scene+start_scene_play`；不得将它记为 `enter_test_scene` 成功。
10. **进场**（详见"执行效率优化规则 #7"）：一次查询同时判定多项状态，一次性决策下一步动作。对于非登录类功能测试，若当前处于 `UI_LoginGame`，优先通过 `CyStarRoad.Test.TestBoot.Boot()` 触发前置登录，并记录每次返回值；对 `login_triggered`、`loading:login`、`loading` 采用每 200-300ms 一次的独立状态查询，最长 65 秒，确认 `ready` 或“登录界面已离开 + 可交互大厅候选已出现 + 业务数据已就绪”后再继续。8 秒早停规则只适用于普通 UI/业务步骤，不适用于该登录前置。不得使用 `TestHelper.Click()` 触发登录按钮。判定登录阻塞前必须确认本轮已有编译和进入 PlayMode 事件；只有 `err:login_failed_after_3_retries`，或最终查询仍为登录界面且无大厅候选，才写入 `environment_blocked:login_timeout`。所有 Boot 返回值、最终 active UI、候选状态和已执行动作必须写入本轮 `{run_dir}-run-log.json`；若缺少编译/PlayMode事件，则记录为测试阶段不完整后进入报告收口，不得伪造登录阻塞。
11. 按分组执行 functional 用例：
   - **进入分组前**：一次性完成本组共享的进入操作（打开UI/切换页签等），优先复用已缓存的绝对路径（详见"执行效率优化规则 #2"）
    - **模板烟测**：识别本批使用的每种验证 evaluate/C# 模板，在正式批量执行前各运行一次无副作用编译烟测；任何重复局部变量、委托签名、序列化或 API 错误都必须先修测试编排/测试辅助代码并重新烟测，烟测未通过不得开始批量执行。
    - **小分组调用**：从 JSON `execution_groups[]` 读取 `group_id`，按顺序为每条 Case 构建 `CaseExecutionPlan`，按相同页面/前置状态组成小组，用 **1 次 evaluate** 调用 `TestHelper.RunSuiteAndRecord(runDir, inputCasePath, referencePath, groupId, plans)`。若旧 JSON 没有 `execution_groups`，才允许按本节规则在运行时分组；跨页面或需要独立跨帧恢复的 Case 必须拆小组。所有分组的 CaseId 合并后必须覆盖 `event=classify.details.functional_case_ids` 中的全部 CaseId，不允许只执行前 5 条、优先级最高的几条、参考文档列出的几条或“最小化实测”子集。每个 plan 的 `source_steps`、`operations` 和 `assertion` 必须来自该 Case；展示/只读 Case 可以使用 `snapshot`，但必须映射到自己的字段或断言；需要交互的 Case 必须执行对应操作链后再断言。分组通过条件必须由组内每个 Case 的 case-scoped verdict 汇总得出，不允许用任意 1 条 Case 的 passed 推导整组 passed。
    - **每条用例执行前**：先做一次纯状态读取完成前置条件校验（详见"执行效率优化规则 #4"）；前置条件不满足时先主动构造测试账号数据/资源/业务状态→等待服务器同步→重新校验，仍无法构造目标条件且环境可运行时标记 `test_inconclusive`；只有环境/关键前置或强关联失败导致无法执行时标记 `blocked`、写入记录、跳过该用例
   - 前置条件满足的用例：按步骤执行；点击类操作前先用 `CheckBoundUiReady()` 和当前 Case 的既有前置状态读取确认候选。槽位类操作必须先调用 `FindFirstSlotByState("目标状态")`；返回 `ready:slot_index=N` 后才用 `slot_first:目标状态` 或已验证 `down:N` 触发，返回 `slot_unavailable` 记录为 `test_inconclusive`，不得盲点固定索引。未命中则按标准流程点击后用短轮询+早停确认状态（详见"执行效率优化规则 #5"），单步超过8秒早停上限时必须在记录中写明原因
    - **UI 遮挡观察**：每步目标 UI 就绪后、执行验证操作前，调用 `ObserveOverlay()`；`clear=true` 才直接继续，存在 `blocker=` 时仅记录并使用当前 Case 已声明的关闭操作，不自动清理未知 UI。
    - **每个步骤完成后**：测试事件记录**合并在本步骤同一次 evaluate 内**完成落盘到 `{run_dir}-run-log.json`，且每条事件必须包含 `start_time`、`end_time`、`duration_ms`（详见"执行效率优化规则 #1"，禁止为写日志单独再发起一次调用），与上一条测试事件记录之间不得有超过2秒的未解释间隙（详见"执行效率优化规则 #8"）
   - 多个操作/状态检查尽量合并到一次 evaluate（批量执行、状态合并）
    - **每条用例结束后**：写入该用例自己的操作序列、断言结果、证据和 verdict 到测试事件日志。若某条 case 没有独立执行或独立断言结果，不能写 `passed`，应继续执行该 case；确认无法继续执行或无法恢复执行时才允许异常 `blocked`
    - 若本次运行中发现新的、已验证有效的点击兜底方案，**必须**在该用例结束前写入 `known-issues.json`（详见"执行效率优化规则 #5"）
    - **效果图对比（仅在 `effect_diff_enabled=true` 时执行）**：每个唯一 `UIName` 第一次完成真实进场并确认界面稳定后，调用 `../ui-quick-reference/scripts/read_ui_effect_path.py <UIName> --project-root <工作区目录>`，按当前 `UIName` 从当前工作区重新定位 `UILogicManager.xlsx` 并读取 `UIPerfectPath`；reference 不提供表格或效果图路径。工作区、上一级、上两级是两类资源共用的精确查找候选；项目根目录在这三者中按 `Public`、`Art`、`Doc`、`Server` 等项目级目录的精确或有限模糊匹配评分确定，同分取更外层目录，无匹配时取向上两级。表格和相对图片三处均未命中时，都只在该同一个项目根目录内做一次模糊搜索。`UIPerfectPath` 为绝对路径时直接读取，未找到则按未填写处理并提示检查路径。查询返回 `found` 时使用结果中的 `resolved_path`（已验证可直接打开的绝对路径），只采集一张该 UI 的稳定实际截图，调用 `../ui-image-diff/SKILL.md` 生成本轮 `run_dir/ui-image-diff/` 下的对比报告，并在 run-log 写入基准图、实际图、报告路径和结论摘要；同一 UI 不重复对比。绝对路径失败、精确和模糊匹配都未找到、最高候选并列、匹配度过低、表格解析失败或 UI 不匹配时，提示检查路径、按未配置路径处理并跳过当前 UI 的效果图对比截图，继续功能测试；这不停止 Unity/PlayMode、不因该原因生成 blocked 用例，也不改变 Case verdict。效果图对比报告是视觉辅助证据，不自动等同于 failed 或 Bug，只有与明确视觉验收条件对应并完成 AI 归因后才可影响 Case 结果。
12. **failed 处理（按修复模式执行）**：任何步骤/用例出现 `failed` 时，必须先确认本轮修复模式。允许修改代码时，**不得跳过该用例继续执行后续用例**，必须立即执行以下边测边修边复测流程；只测不修模式下，禁止执行“自行修复/重新编译/复测改代码结果”流程，只记录失败证据、根因判断和建议修复方向，并继续执行可继续执行的后续用例或进入报告生成。若问题属于条件不足、工具能力不支持或风险不可控，应记录为 `blocked` 并保留原因，不进入强行修复循环：
   - **根因定位与自动记录**：基于当前步骤的 evaluate 返回、日志、截图、expected/actual 和断言回执自动完成失败归因；优先排除"测试误判"（路径/名称/守卫条件错误），再归因到业务代码或测试流程问题。同一小批的 failed、blocked、test_inconclusive Case 先分别读取完整日志并形成 `FinalCaseReasonPatch[]`，再一次调用 `TestHelper.UpdateFinalCaseReasons(runDir, patches)` 回写各自唯一 final record；文本至少说明实际操作、预期、实际结果、证据和根因是否确认。确认是产品问题时，立即调用 `TestHelper.RecordAutoLocatedIssue(...)` 写入唯一 `issue_id`、问题描述、根因、目标和证据；无法确认根因时记录未归因失败，不得伪造 Bug
   - **AI 原因文本模板**：`reason` 只要求包含失败/阻塞现象、实际操作、预期结果、实际结果、证据和根因判断；具体句式由 AI 根据当前 Case 的日志自行组织，不能复制固定失败模板，也不能在根因未确认时猜测产品 Bug。
   - **自行修复**：对可修复的根因直接修改源码或测试流程——业务代码问题修复对应 `.cs` 文件；测试流程问题修正路径/触发方式/前置校验；编译错误修复对应语法/引用错误。需要自修的 plan 必须在首次执行前设 `defer_final_on_nonpassed=true`：初次失败只写非 final attempt，修复、重新编译和同 run_dir 验证完成后再写唯一 final；禁止用 Replace 或新建 `max+1` 目录。每次完整的“修复→重新编译→同 run_dir 复测”成功完成后，只写入一个 `event=fix` 轮次标记，并在该记录的 `details.fix_round` 写入本次测试的全局轮次编号（1、2、3），同时写入 `issue_action=fixed`、`fix_verified=true`、`status=passed`；同一轮的编译、rerun、retry 记录不得再次增加轮次。修复内容必须实时写入 JSON 记录（`action=fix`，`target=文件路径:行号`，`reason=修复说明`）
   - **重新编译检查**：若修改了 .cs 源码，必须先执行 `focus_unity_window.ps1`；已找到本项目 Unity 但未输出 `UNITY_FOCUSED` 时仍先尝试调用 `mcp__mymcp__execute_compile`，仅在无响应或超时后重新聚焦并重试一次，确认编译通过
   - **复测**：编译通过后重新执行当前失败的用例/步骤，通过后继续执行下一个用例
   - **轮次上限**：本次测试的全局修复轮次最多 3 轮；3 轮后仍失败，将该用例标记为 `failed` 并写入 JSON 记录，继续执行后续用例。若确认不是可修复失败而是执行条件不足，则标记为 `blocked` 并写明原因。最终报告汇总时注明"已达自动修复轮次上限，需人工介入"或具体 blocked 原因。
   - **通过后继续**：复测通过后，立即继续执行下一个用例，不停顿、不等待
13. 收口与退出 PlayMode：先调用 `query_logs(types_json=["Error","Exception"], keyword="", max_count=50)`，将每条结果通过 `RunLogDetails.type/message/stack_trace` 写为 `event=query_logs`；随后调用 `mcp__mymcp__stop_scene_play`。实际 stop 调用不额外写入 `stop_playmode` 生命周期记录。
14. **报告前扫描**（详见报告输出规则）：对 JSON 记录做五项扫描——(a) 先读取 `event=classify.details.functional_case_ids` 作为覆盖基准，检查每个 functional case 是否都有 case-scoped 实时最终记录；展示/只读 case 允许共享批量状态读取，但必须有自己的检查目标或断言结果；需要交互的 case 必须有真实操作链或状态变化证据。缺少用例记录、交互类缺少操作链、或 passed 记录无法映射到该 case 的检查目标时，默认判定为“执行覆盖不足”，应回到第 11 步继续执行缺失用例或补充独立断言，只有确认无法继续执行或无法恢复执行时才允许异常补 `blocked`，不得继承同组其他 case 的 passed，也不得在缺失大批用例时直接降级后收尾，(b) 超过8秒早停上限且非视觉动画类的步骤，(c) 相邻记录间超过2秒的未解释间隙，(d) 若存在历史 Skill timing 则比较 Skill 有效耗时，(e) 所有 AutoGen/Logic 保底记录是否包含触发原因、限定源码、候选身份、运行时验证和动作结果。扫描结果均需写入报告对应章节。
15. 撰写报告：本步骤是唯一允许调用报告渲染脚本的阶段。调用本 Skill 的 `scripts/render_functiontest_report.py`，基于本轮 `Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-run-log.json` 渲染生成 `Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-unity-functiontest-report.md`，并传入本轮 Skill timing 文件及 `--skill-name unity-functiontest`。渲染器同时扫描本轮 `run_dir/ui-image-diff/`，把已生成的效果图对比报告路径作为视觉证据附在最终报告中；没有报告时写明未开启、未配置或本轮未形成可比较结果，不伪造对比结论。报告渲染只能发生在第 7-14 步已经执行完成、且 run-log 第一条为 `setup`、中间存在编译和用例执行证据、最后一次 `query_logs` 已完成、`skill_end` 已写入之后。渲染器只展示 final record 中 AI 写入的 `reason`，不再根据固定模板改写失败原因；非 passed Case 若缺少该字段，只提示“AI失败归因缺失”，不得伪造失败原因。报告中的 Skill 时间只读取 timing 文件，不读取 run-log 生命周期跨度或步骤 `duration_ms` 累加值。禁止在此阶段重新回忆、拼凑或按时间戳倒推过程。报告必须如实保留 `passed / failed / blocked`，不得为了形成“全通过”结论改写用例状态。**报告中的"4.1 自动修复记录"直接从 JSON 中已验证完成的 `event=fix` 记录汇总生成，无需在报告阶段再触发新的修复流程。**

## 证据收集优先级规则

**核心原则：优先使用 Unity Canvas 节点信息作为证据，截图仅作为辅助/最终确认手段。**

### 证据优先级（从高到低）

1. **Unity Canvas 节点状态**（首选证据）
   - 节点 `activeInHierarchy` 或 `activeSelf` 是否为 true
   - `GameText.text` 文案内容
   - `GameToggle.isOn` 状态
   - `GameButton` 组件是否存在
   - `GameImage.sprite` 是否加载

2. **ScrollView 子节点信息**
   - Content 下子节点数量
   - 各子节点的 `activeInHierarchy`
   - 子节点内的关键文案（通过 `GetComponentInChildren<GameText>(true)` 获取）

3. **场景快照结构**（`capture_scene_snapshot`）
   - 用于确认节点层级路径是否存在
   - 查看节点树结构是否符合预期
   - 确认子 UI 是否创建/激活

4. **截图取证**（最后手段）
   - 当节点状态无法验证 UI 实际显示效果时使用
   - 验证视觉布局、动画效果
   - 作为操作成功/失败的最终确认

### Unity 节点验证检查清单

每一步操作后，必须检查以下 Unity 元素并向用户打印结果：

```
【节点证据检查】
  ▸ UI是否显示：{节点路径}.activeInHierarchy = true/false
  ▸ 节点active状态：{activeSelf = true/false, activeInHierarchy = true/false}
  ▸ GameText文案：{gameText.text}
  ▸ ScrollView子节点数：{content.childCount}
  ▸ 子节点列表：{child1.name}, {child2.name}, ...
```

### 证据收集模板（每步必须执行）

**Token 优化重点**：步骤内的多个状态检查必须合并到 1 次 evaluate，禁止每个子项发 1 次 evaluate。

#### 标准批量模板（推荐，1 次 evaluate 返回所有步骤证据）

```csharp
// 单次 evaluate 同时返回：节点存在、激活状态、GameText、ScrollView 子节点
var evidence = new System.Text.StringBuilder();
evidence.AppendLine("【节点证据检查】");

// 1. 检查目标节点是否存在
var targetNode = GameObject.Find("目标路径");
evidence.AppendLine("  ▸ 节点存在：" + (targetNode != null));
if (targetNode != null) {
    evidence.AppendLine("  ▸ activeSelf = " + targetNode.activeSelf);
    evidence.AppendLine("  ▸ activeInHierarchy = " + targetNode.activeInHierarchy);

    // 2. 检查 GameText 文案（合并读取）
    var gameText = targetNode.GetComponent<GameFramework.Logic.GameText>();
    if (gameText != null) {
        evidence.AppendLine("  ▸ GameText.text = " + gameText.text);
    }

    // 3. 检查 ScrollView 子节点（合并读取）
    var scrollView = targetNode.GetComponentInChildren<GameFramework.Logic.GameScrollRect_V2>(true);
    if (scrollView != null && scrollView.content != null) {
        var content = scrollView.content;
        evidence.AppendLine("  ▸ ScrollView.content.childCount = " + content.childCount);
        for (int i = 0; i < System.Math.Min(content.childCount, 6); i++) {
            var c = content.GetChild(i);
            evidence.AppendLine("      - " + c.name + " (active=" + c.gameObject.activeInHierarchy + ")");
        }
    }
}

return evidence.ToString();
```

#### 多用例共用模板（推荐，1 次 evaluate 跨多个 TC 的状态合并）

```csharp
// 用于前置条件相同的多条用例（TC-001/002/003 都是玩具列表初态）
// 一次返回所有用例所需的初始状态
var sb = new System.Text.StringBuilder();
var root = GameObject.Find("UI_ToyMainList");

// TC-001 需要：上阵区域英雄列表
sb.AppendLine("[TC-001] 上阵区域:");
void ShowSlot(Transform t, int d) {
    if (d > 10) return;
    if (t.name == "bg1" || t.name == "bg2" || t.name == "bg3") {
        var lev = t.Find("levbg/lev");
        var levTxt = lev != null ? lev.GetComponent<GameFramework.Logic.GameText>() : null;
        sb.AppendLine("  " + t.name + ": lev=" + (levTxt != null ? levTxt.text : ""));
    }
    foreach (var c in t) ShowSlot(c, d + 1);
}
ShowSlot(root.transform, 0);

// TC-002 需要：上阵槽位数（MAX_ON_SCENE_COUNT 已是常量，直接判断）
sb.AppendLine("[TC-002] 槽位数=3 (MAX_ON_SCENE_COUNT)");

// TC-003 需要：每个上阵英雄的头像+等级+属性图标
sb.AppendLine("[TC-003] 上阵英雄信息详见上方 lev 输出");

return sb.ToString();
```

#### 反例（禁止）

```csharp
// ❌ 反例：每个状态发 1 次 evaluate，每次 500-1000 tokens
evaluate(读节点存在)         // 400 tokens
evaluate(读 activeSelf)      // 400 tokens
evaluate(读 activeInHierarchy) // 400 tokens
evaluate(读 GameText.text)   // 400 tokens
evaluate(读 ScrollView 子节点) // 800 tokens
// 5 次 evaluate 总计 2400 tokens，且都是单字段

// ✅ 正例：1 次 evaluate 返回所有字段，约 600 tokens
```

### 打印操作指南

**聊天窗口进度提示不写入测试产物。** 详细字段（路径、文案、子节点数等）写入测试事件日志的结构化字段。

```
正在进入英雄列表。
```

而不是原来的多行 ASCII 边框 + 逐字段罗列格式。

### 何时截图（何时不用截图）

**核心规则：每条 functional 用例最多 2 张截图**（入场 1 张 + 关键状态变化或结束 1 张）。

**允许截图**：
- 用例入场后的初始状态（1 张，建立基线证据；同一 UI 根节点本轮已截图则复用）
- 用例结束前 / 关键状态变化后（1 张，仅当 evaluate 节点状态不足以证明操作生效时）
- 用例失败的最终证据（失败取证时允许，但仍应尽量控制在本用例 2 张内）
- 视觉验证（布局、动画效果）—— 当 evaluate 节点状态无法表达时

**不需要截图**：
- 节点 active 状态可以明确判断时（用 evaluate 读 activeInHierarchy）
- GameText 文案可以明确读取时（用 evaluate 读 text）
- 状态变化可以通过 evaluate 返回值判断时
- 批量操作中的中间步骤（每批最后一个步骤才截图）
- 调试性截图（用 evaluate 打印节点信息代替）

**截图读取（Read PNG）严格收敛**：
- 用例通过时最多 `Read` 1 张关键截图作为报告佐证
- 用例失败时 `Read` 失败截图作为归因依据
- **禁止** "看一眼" 式 `Read`（每张 PNG 约 5k tokens，仅用于 Read 也要计入成本）
- **禁止** 每步操作都 `Read` 截图

## Unity 元素分析规则

每一步测试必须对 Unity Canvas 节点进行详细分析，判断是否达到用例预期。

### 节点状态分析维度

1. **存在性分析**
   - 节点路径是否可找到
   - 节点是否在预期层级下

2. **激活状态分析**
   - `activeSelf`：节点自身激活状态
   - `activeInHierarchy`：节点在层级树中的激活状态（父节点可能影响）
   - 预期：`activeInHierarchy == true` 表示用户可见

3. **文本内容分析**（GameText）
   - 读取 `gameText.text` 文案
   - 与预期文案比对（支持 Contains/IndexOf 模糊匹配）
   - 检查是否包含关键字符串

4. **ScrollView/列表分析**
   - `content.childCount`：子节点数量
   - 每个子节点的 `activeInHierarchy`
   - 子节点名称是否符合预期模式（如 `EditorRuntime_Content_*`）
   - 关键子节点的文案内容

5. **GameToggle 状态分析**
   - `isOn`：当前选中状态
   - `onValueChanged` 是否触发（通过子节点 Selected 确认）

6. **GameButton 存在性分析**
   - 节点是否挂载 GameButton 组件
   - `onClick` 事件是否已注册

### Unity 元素 vs 预期对比模板

```csharp
// 步骤验证模板
var result = new System.Text.StringBuilder();
result.AppendLine("【Unity 元素分析】");

// 目标节点
var uiNode = GameObject.Find("UI_XXX");
if (uiNode == null) {
    result.AppendLine("❌ UI节点不存在：UI_XXX");
    return result.ToString();
}
result.AppendLine("✓ UI节点存在");

// 激活状态
result.AppendLine("  ▸ activeInHierarchy = " + uiNode.activeInHierarchy + " (预期: true)");
if (!uiNode.activeInHierarchy) {
    result.AppendLine("  ⚠ UI未显示，可能被父节点隐藏");
}

// GameText 文案
var txt = uiNode.GetComponentInChildren<GameFramework.Logic.GameText>(true);
if (txt != null) {
    var actualText = txt.text;
    var expectedText = "预期文案";
    var match = actualText.IndexOf(expectedText) >= 0;
    result.AppendLine("  ▸ GameText.text = \"" + actualText + "\"");
    result.AppendLine("    预期包含: \"" + expectedText + "\" → " + (match ? "✓ 匹配" : "❌ 不匹配"));
}

// ScrollView 子节点
var scroll = uiNode.GetComponentInChildren<GameFramework.Logic.GameScrollRect_V2>(true);
if (scroll != null && scroll.content != null) {
    var content = scroll.content;
    result.AppendLine("  ▸ ScrollView 子节点数: " + content.childCount + " (预期: >= 1)");
    for (int i = 0; i < Mathf.Min(content.childCount, 5); i++) {
        var child = content.GetChild(i);
        result.AppendLine("    [" + i + "] " + child.name + " (active=" + child.gameObject.activeInHierarchy + ")");
    }
}

return result.ToString();
```

### 预期对比判断标准

| 元素类型 | 验证方式 | 通过条件 |
|---------|---------|---------|
| UI显示 | `activeInHierarchy == true` | 节点可见 |
| 按钮 | `GameButton` 组件存在 | 可以触发 |
| 文案 | `text.Contains(关键字)` 或 `text == 精确值` | 内容匹配 |
| 列表 | `childCount >= N` | 数量达标 |
| 开关 | `isOn == true` | 已选中 |
| 子节点 | `child.activeInHierarchy == true` | 特定项激活 |

### 打印给用户的分析结果格式

详细的 Unity 元素分析结果（节点路径、activeInHierarchy、GameText 文案等）写入测试事件日志；对话中只显示必要的简短进度：

```
打开详情页失败，正在核对当前界面。
```

而不是原来的多行 ASCII 边框 + 逐字段罗列格式。若需要向用户展示详细证据，在最终报告的"节点证据摘要"表格中体现，而非执行过程中逐步打印。

## 失败归因规则
将失败归因为以下类型之一：
- **MCP 不可用**：工具调用错误，记为 `blocked`
- **PlayMode 未启动 / 异常退出**：记为 `blocked`
- **截图文件为空**：视为测试流程问题，允许重试
- **业务代码问题**：根因在功能代码本身
- **框架问题**：根因在 UI 框架或运行时机制
- **资源或环境问题**：资源缺失、环境异常等
- **测试流程问题**：调用顺序错误、等待不足、定位错误等
- **测试误判**：测试代码本身使用了错误的目标名/路径/条件，导致正确行为被误判为失败。此时应在报告中单独注明"测试误判"而非"业务代码问题"

若无法基于真实证据完成归因，先判断是否属于“测试条件无法构造”：属于时标记 `test_inconclusive`；只有环境/前置条件不可用、强关联前置用例失败，或确实无法继续执行时才标记 `blocked`。

### 测试误判快速诊断（优先执行）
当一个操作"失败"时，**先排除以下测试误判可能**，再归因到业务代码：
1. **轮询了错误的 UI 名称** — 如点击按钮后实际创建的 UI 是 `UI_AttributeOverview`，但测试轮询了 `GameObject.Find("UI_ToyDetailAttr")`。→ 确认方式：先检查运行时节点和 reference；仍无法确认时记录 `fallback_reason`，再 Grep 当前 Logic 的 `CreateUIAsync` 生成候选，并回到 Unity 验证。
2. **点击了不满足守卫条件的列表项** — 如 ScrollView 首个卡片的 `OwnState != Owned`，代码 early-return 不会创建详情 UI。→ 确认方式：读取每项的 `txt_suipian` 等关键字段，找满足条件的项再点击。
3. **异步 UI 创建尚未跨帧完成** — 同一次 evaluate 内触发 `CreateUIAsync` 后立刻 `GameObject.Find` 可能持续返回 null。→ 将“触发动作”和“状态确认”拆成两次独立 evaluate，第二次按 300-500ms 短轮询并在 8 秒内早停；不得用同次 evaluate 内的固定 `Sleep(2000)` 代替跨帧验证。

## 重试上限与放弃规则
- **单步重试上限**：同一 UI 操作（如定位节点、触发按钮、等待状态）连续尝试约 10 次仍无法达到预期效果时，判定为该步骤失败。
- **放弃时的记录**：放弃前必须将失败原因完整记录到报告中，内容包括：
  1. 尝试了多少次
  2. 每次失败的具体表现（如"节点未找到"、"按钮触发后无响应"、"状态未更新"等）
  3. 推测的根本原因（基于日志、截图、evaluate 状态等证据）
  4. 已耗费的测试时间（从该步骤首次尝试到放弃时的时长）
- **后续处理**：记录完毕后，立即跳过该步骤继续执行后续用例/步骤，**不得无限卡在该步骤上**。
- **报告标记**：已经执行且实际结果不符合预期的步骤标记为 `failed`；因环境/强关联前置失败而无法开始的步骤标记为 `blocked`；因无法构造目标异常/边界条件而无法得出结论的步骤标记为 `test_inconclusive`。后续步骤正常执行并单独判定 verdict。

## 报告输出规则
**功能测试报告必须由 `{run_dir}-run-log.json` 中的逐步结构化记录和本轮 Skill timing 文件直接渲染生成**（详见"执行效率优化规则 #1"），禁止在收尾阶段重新回忆或按截图/日志时间戳倒推 Skill 时间。PlayMode 实际启停不写开始/结束 run-log 记录；Skill 开始、结束和有效耗时必须从 timing 文件读取。第一条必须是 `setup`，报告前最后一次 `query_logs` 必须已按 `details.type/message/stack_trace` 写入。

**报告必须使用固定渲染脚本生成**：调用本 Skill 的 `scripts/render_functiontest_report.py {run_dir}`，由该脚本读取 `{run_dir}-run-log.json` 生成 `{run_dir}-unity-functiontest-report.md`。固定脚本只允许在测试阶段完成后调用；测试前不得调用渲染脚本探测未来目录是否存在。执行前目录不存在时应先创建目录并执行测试，不得直接渲染未来目录后用“目录不存在”判定失败或退出。禁止在运行目录或项目中临时创建 `generate_report*.py`、`render_report*.py`、`*-report.py` 等一次性报告生成脚本；如果固定脚本不能满足字段需求，必须修改固定脚本本身，而不是临时另写脚本。

**同一 `run_dir` 只允许维护一组正式产物**：只有用户明确指定复测/继续/修复/覆盖某个 `run_dir` 时，本轮才允许原位更新 `{run_dir}-run-log.json`、`{run_dir}-known-issues.json` 和 `{run_dir}-unity-functiontest-report.md`；除此之外，任何新一轮独立测试都必须扫描同 feature_id 历史目录并使用最大 4 位序号 +1 的新目录。禁止在同一运行目录下生成带 `rerun`、`full-rerun`、时间戳、批次号或版本号的新报告/日志文件；也禁止把新一轮独立测试写回最近一次旧目录。

**生成报告前必须执行七项扫描**（覆盖门禁 + 规则 #5/#8/#9 + 编译检查 + AutoGen/Logic 保底审计）：
1. **检查 functional case 覆盖** — 每个 functional case 必须有 case-scoped 实时最终记录；展示/只读类 passed case 可以共享批量状态读取，但必须有自己的检查目标或断言结果；交互/状态变化类 passed case 必须有独立操作序列、独立断言结果或状态变化证据。缺少记录、交互类缺少操作链、或 passed 记录无法映射到该 case 的检查目标时，必须回到执行阶段继续执行该 case；不得因 reference 缺失、探索成本、同组其他 case 已完成而提前收尾或继承 passed。只有确认 MCP/Unity 不可用、用户停止或确实无法继续执行/恢复执行时，才允许异常补 `blocked`，且原因必须写明“缺少执行时实时最终记录/独立断言证据”；reference 缺失、离线扫描失败或运行时 reference 尚未创建不属于该条件。
2. 扫描所有 `duration_ms > 8000` 且非视觉动画类的步骤，列入"4. 失败与归因"
3. 扫描相邻记录间超过 2 秒的未解释间隙，列入"4. 失败与归因"
4. 若存在历史 Skill timing，比较本次 Skill 有效耗时与历史 Skill 有效耗时；缺少 timing 时明确写出无法比较，不得改用 Unity 生命周期时长
5. **查询 Unity 运行时错误日志** — 报告生成前必须调用 `query_logs` 工具，过滤 `types_json=["Error","Exception"]`、关键词留空、`max_count=50`，将返回的错误/异常信息追加到报告"6. 运行时错误日志"节。若返回为空则标注"无错误日志"。
6. **审计 AutoGen/Logic 保底记录** — 扫描所有存在 `fallback_reason` 的步骤，确认 `source_files`、`control_identity`、`logic_chain`、`runtime_verification`、`action_result` 齐全；缺字段、未回到运行时验证或仅凭源码判定 `passed` 时，必须修正 verdict，并列入"4. 失败与归因"。
7. **扫描 failed 用例并按修复模式处理** — 最终报告渲染前扫描所有 verdict 为 `failed` 的用例（含编译失败场景）。允许修改代码时，按"执行工作流第 12 步"执行自动修复与重测流程，修复与重测结果写入"4. 失败与归因"的"自动修复记录"小节，并更新"2. 用例与结果"中对应 verdict。只测不修模式下，不触发自动修复与重测，只把 failed 证据、根因判断和建议修复方向写入"4. 失败与归因"，并保留原始 verdict。

最终报告 7 节，**必须包含 Skill 时间、日志上报耗时计算和分组映射关系**（§1.1 展示业务 Skill 时间，§1.2 说明本次日志上报耗时计算，§2 按分组展示，§2.1 给出分组→用例编号完整映射）：

```md
# Functional Test Report

## 1. 任务概览
- 输入：<路径或内联>
- feature_id：<kebab-case>
- 用例总数：<M>（functional = <F> / 非功能测试范围 = <R> / passed = <P> / failed = <Y> / blocked = <B> / test_inconclusive = <I>）
- 启动前编译检查：<通过 / 失败（附完整报错信息）>
- Skill 开始时间：<timing JSON 中当前业务 Skill 的 skill_start_time>
- Skill 结束时间：<timing JSON 中当前业务 Skill 的 skill_end_time>
- Skill 有效耗时：<固定渲染器计算出的本次可上报耗时；根 Skill 优先使用 timing JSON 的 Skill 时间并按规则扣除环境过滤，无法使用时按 Cyou 三个时间环境变量回退；嵌套子 Skill 只显示原始时间，否则显示 0>
- 自动修复轮次：<N 轮（0=未完成修复轮次；最多3轮）>
- 历史对比：<与上一次同 feature_id 的 Skill 有效耗时相比，或说明缺少 timing>

### 1.1 Skill 时间明细

### 1.2 日志上报耗时计算

- 本次上报业务 Skill：<Skill 名称>
- Skill 开始时间：<skill_start 时间；没有记录时填写“未记录”>
- Skill 结束时间：<skill_end 时间；没有记录时填写“未记录”>
- Skill 原始耗时（结束时间 - 开始时间）：<毫秒和秒；无法计算时填写“不可用”>
- `CYOU_SESSION_DURATION_MS`：<实际读取值；没有时填写“未读取”>
- `CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS`：<实际读取值；有起止快照时同时填写本次变化量>
- `CYOU_SESSION_CONDENSE_DURATION_MS`：<实际读取值；有起止快照时同时填写本次变化量>
- 本次实际用于上报的耗时：<固定渲染器计算出的数值；任何情况下都必须显示，无法取得有效时间时显示 0>
- 计算过程：<用实际毫秒数写出减法或回退结果，确保用户可以自行核对>
- 本次计算原因：用自然语言说明根 Skill 的 `skill_start`、`skill_end` 是否有效，以及是否读取到 `CYOU_SESSION_DURATION_MS`、`CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS`、`CYOU_SESSION_CONDENSE_DURATION_MS`，并说明为什么使用完整 Skill 时间、由根 Skill 扣除过滤时间或上报 0；嵌套子 Skill 要说明只展示原始时间、过滤由父 Skill 统一处理
- PlayMode 生命周期和 run-log 各步骤 `duration_ms` 不参与日志上报耗时计算

### 1.3 用例分类说明（必须）

| 分类 | 数量 | 含义 | 处理方式 |
|------|------|------|----------|
| functional | <F> | UI 交互/状态验证/操作流程 | 按分组合并执行，同组共用一次 evaluate |
| 非功能测试范围 | <R> | 纯逻辑/数据公式、多端同步、响应时间测量 | 不属于 UI 功能测试，MCP 不执行 |
| blocked | <B> | 环境、关键前置或强关联用例失败导致无法执行 | 标记为 blocked 并保留原因 |
| test_inconclusive | <I> | 无法构造异常刷新、网络故障、并发竞争等目标测试条件 | 上报为 invalid_case_count，不计入 failure_case_count |

- **非功能测试范围明细**：列出具体 CaseId 和跳过原因（如 TC-FM-xxx: 数据持久化，TC-FM-xxx: 多端同步 等）
- **blocked 明细**：列出具体 CaseId 和阻塞原因
- **test_inconclusive 明细**：列出具体 CaseId 和无法构造的测试条件；数量上报为 invalid_case_count

## 2. 用例与结果（逐条列出，按分组排序，一目了然）

> 每条用例独立一行，verdict 列区分 passed/failed/blocked/test_inconclusive。
> 同一分组内用例连续排列，分组名只在分组首行显示，后续同组用例的"分组"列留空。

| 分组 | CaseId | Verdict | 关键证据 |
| --- | --- | --- | --- |
| <分组名> | <CaseId> | ✅ passed | <一句话摘要> |
| | <CaseId> | ✅ passed | <一句话摘要> |
| | <CaseId> | ❌ failed | <失败原因摘要> |
| | <CaseId> | 🚫 blocked | <阻塞原因摘要> |
| | <CaseId> | test_inconclusive | <无法构造测试条件摘要> |
| <分组名> | <CaseId> | ✅ passed | <一句话摘要> |
| ... | ... | ... | ... |

> 汇总：functional passed = <X 条>，failed = <Y 条>，blocked = <Z 条>，test_inconclusive = <I 条>；非功能测试范围 = <R 条>（不执行）

### 2.1 分组汇总（分组 → 用例数量 + verdict 统计）

| 分组 | 用例数 | passed | failed | blocked | test_inconclusive | 说明 |
|------|--------|--------|--------|---------|-------------------|------|
| <分组名> | <N> | <N> | 0 | 0 | 0 | <分组用途简述> |
| ... | ... | ... | ... | ... | ... |

**禁止**只写"部分用例"或模糊描述，必须逐条列出每组覆盖的具体 CaseId 范围和每条 verdict。本表用于快速判断哪些分组有 failed/blocked 用例需要关注。

## 3. 节点证据摘要（每用例关键 Unity 元素状态）

| CaseId | UI节点 | activeInHierarchy | GameText | 子节点数 | 备注 |
| --- | --- | --- | --- | --- | --- |
| <id> | UI_XXX | true/false | "文案" | N | 通过/失败原因 |

## 4. 问题、阻塞与未定论归因
- **启动前编译失败**（仅编译失败时）：<完整报错信息：错误文件:行号 + 错误内容> / 问题类型：编译错误 / 处理结果：<已自动修复通过 / 达到轮次上限需人工介入>
- <CaseId>：<失败原因> / <问题类型> / <证据路径> / <处理结果：已重试通过 / 已知问题 / 阻塞> / <相关方法>
- <StepId 超限>：超过8秒早停上限但未走视觉兜底 / <原因，若 JSON reason 字段为空则标注"原因未记录，违反规则#5硬校验">
- <记录间隙>：<前一StepId> 到 <后一StepId> 之间存在 <间隙秒数> 秒未解释间隙，违反规则#8

### 4.1 自动修复记录（有 failed 用例时必填）
| 轮次 | CaseId | 失败原因 | 修复文件:行号 | 修复说明 | 重编译 | 重测 verdict | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 第1轮 | <id> | <根因> | <path:line> | <修复内容> | 通过/失败 | passed/failed | <如"已达上限需人工介入"> |
| 第2轮 | ... | ... | ... | ... | ... | ... | ... |

- 修复范围说明：<仅重测 failed 用例所在分组 / 含依赖被修复代码的 passed 用例>
- 最终未通过用例：<列出3轮后仍 failed 的 CaseId，无则填"无">

## 5. 结论
- 总体状态：通过 / 部分通过 / 失败 / 阻塞
- 耗时优化情况：<本轮 Skill 有效耗时较历史下降/持平/上升 X%；若缺少 timing，注明无法比较>
- 下一步：<复测 case X；联系策划补全待确认项；若发现规则#5/#7/#8执行不到位，需在下一步中注明需要修复的规则>

## 6. 运行时错误日志
> 由 `query_logs(types_json=["Error","Exception"], keyword="", max_count=50)` 在报告生成前查询并填充。若返回为空则填写"无错误日志"。

| 序号 | 时间 | 类型 | 消息（前120字符） | 堆栈（前200字符） |
| --- | --- | --- | --- | --- |
| <n> | <timestamp> | Error/Exception | <message> | <stack_trace> |

```

按需补充：触发方式（方式一 evaluate 反射 / 方式二 模拟点击）、业务状态变化对比。

## Reference 输出边界

本 skill 只维护运行时 reference，不再负责离线静态 reference 的正常生成。离线静态 reference 的路径、前置生成、有效性检查和缺陷回刷由 `functiontest-workflow` 编排，生成器由 `ui-quick-reference` 执行。

运行时 reference 的固定路径为：

```text
references/{feature_id}.md
```

运行时 reference 必须来自本轮 Unity 实测，至少包含：

1. 目标 UI 根节点和完整运行时路径；
2. 实际进入方式、登录/业务数据要求；
3. 已验证的控件路径、组件和触发方式；
4. 操作后的状态验证字段或节点；
5. 已确认的已知问题和有效兜底方案；
6. 用例分组、共享前置和 `RunSuite` 建议。

运行过程中发现的新路径、路径别名、按钮触发方式、遮挡处理和已知问题，必须在对应事实验证后增量写入运行时 reference 或本轮 `known-issues.json`。不得把 AutoGen/Logic 候选、未验证的截图猜测或单纯 action acknowledgement 写入 reference。

效果图配置例外规则：离线 `ui-quick-reference` reference 不允许记录 `UILogicManager.xlsx`、`UIPerfectPath`、文件存在性或解析状态。该例外仅限制表格与效果图配置；本 Skill 的 UI 节点绝对路径、Logic 实例等运行时缓存仍按本节规则保留，但不得作为效果图配置来源。每次需要效果图对比时，必须调用 `../ui-quick-reference/scripts/read_ui_effect_path.py`，按当前 `UIName` 从当前工作区重新定位表格与基准图；只有当前查询返回有效文件路径时，才调用 `ui-image-diff`。配置变化不通过 reference 或路径缓存生效。

### Reference 中文展示规则

运行时 reference 面向中文测试人员阅读，必须使用中文标题、章节名、表头、语义说明、进入方式、状态验证说明、已知问题和兜底方案。UI 名称、节点路径、类名、方法名、字段名、`feature_id`、状态 token 等技术标识必须保持原样，并在旁边补充中文解释；不能把技术标识强行翻译成中文。只有英文标题或英文说明、缺少中文语义解释的 reference 视为格式不完整，reference-only 收口时必须基于本轮已验证证据补齐中文说明。

报告生成后，`functiontest-workflow` 可调用本 skill 的“Reference-only 收口模式”读取本轮 `run-log.json`、`known-issues.json` 和证据，补齐运行时 reference。该模式不重新进入 PlayMode、不执行用例、不创建新 run_dir、不修改 verdict、不重新渲染报告。

如果本轮没有进入目标 UI，或没有足够的运行时证据，必须记录 `runtime_reference_gap`，不得创建虚假的运行时路径或触发方式；reference 资料问题不改变真实测试 verdict，也不减少 functional 用例覆盖。

## 必须输出
使用本 skill 后，至少输出：
- **启动前编译检查结果**：`execute_compile` 的通过/失败状态；失败时附完整报错信息（错误文件:行号 + 错误内容）
- **用例归类结果**（`functional` / `非功能测试范围` / `blocked` 各自的数量和编号列表）
- **执行进度**：测试事件字段写入 `{run_dir}-run-log.json`，每条事件必须包含 `start_time`、`end_time`、`duration_ms`；对话进度提示不写入测试产物
- 报告路径
- 每条用例的 verdict 与证据路径
- **耗时统计**：根 Skill 时间从本轮 timing JSON 的 `skill_start_time`、`skill_end_time` 和 `skill_active_duration_ms` 读取，并由根 Skill 统一处理环境过滤；嵌套子 Skill 的 `skill_active_duration_ms` 只表示原始子 Skill 时间，不扣除会话环境变量。时间无效时如实标注并由 JSON 转换按根 Skill 回退规则处理。PlayMode 生命周期不参与 Skill 时长；run-log 的单条 `duration_ms` 只用于步骤证据和超时扫描
- 失败归因汇总
- **效果图对比结果**：开启且形成有效对比时输出每个 UI 的基准图、实际截图、对比报告路径和结论；未开启、基准图未配置或无法读取时输出跳过原因。效果图路径必须来自本轮实时读取的 `UILogicManager.xlsx`，不得来自 reference 缓存。
- **自动修复与重测记录**（有 failed 用例时）：每轮修复的文件:行号、修复说明、重编译结果、重测 verdict 变化；3 轮后仍 failed 的用例清单

## 阻塞条件
出现以下任一情况时返回 `blocked`：
1. 功能测试需求缺失，且无法从用户输入中提取可执行步骤或预期结果
2. 关键 MCP 工具连续 3 次调用失败，导致既无法通过方式一抓取场景结构并 evaluate 触发按钮，也无法通过方式二截图预估并模拟点击
3. 环境不可用、关键前置不可用，或上游失败用例造成强关联依赖无法执行

注意：缺少显式 `feature_id`、UIID、目标 UI 路径或精准坐标不应直接阻塞；应先推断 `feature_id`，再按方式一抓取默认 UI 根节点场景结构并通过 evaluate 触发按钮。
**资源不足、账号状态不匹配、negative/boundary 场景缺失、满员/空位状态不满足，在主动构造测试数据完成前不得标记为 blocked**；必须先走"执行效率优化规则 #4"中的数据构造流程。构造仍失败但测试环境本身可运行时标记 `test_inconclusive`；只有环境/前置不可用或强关联前置用例失败导致无法执行时标记 `blocked`。

## 常见错误
- **跳过 Unity 聚焦/编译回执检查直接进入 PlayMode** - 未先尝试执行 `focus_unity_window.ps1`，或在已找到 Unity 但首次编译无响应后未做一次“重新聚焦→重新编译”，就直接 `enter_test_scene`，可能导致 Unity 未实际处理刷新或旧程序集被加载；必须在获得明确编译成功回执后进入 PlayMode
- **编译失败后仍强行执行用例** - `execute_compile` 返回失败却继续进 PlayMode 跑用例，所有用例必然异常；编译失败时必须终止执行、直接生成报告，进入自动修复流程
- **允许修改代码时 failed 用例不修复就交付报告** - 在允许修改代码模式下，报告中存在 failed 用例却直接结束，未按执行工作流第 12 步执行自动修复与重测；必须扫描 failed 用例→定位根因→修复→重新编译→重测，最多 3 轮。只测不修模式不适用此反例；只测不修模式应保留 failed 并交付报告。
- **自动修复后未重新编译检查** - 修改源码后未执行聚焦尝试，或首次编译无响应后未重新聚焦并重试，或未确认编译通过就重测，可能导致 PlayMode 加载旧程序集；修复后必须完成编译回执确认后进入 PlayMode
- **自动修复重测范围过大或过小** - 重测时重跑全部用例（含已 passed）浪费耗时，或只重跑单条 failed 用例忽略分组依赖；应重测 failed 用例所在分组，含依赖被修复代码的 passed 用例
- **收尾阶段才整理报告** - 执行过程中未逐步写入 JSON 记录，导致收尾时只能靠截图/日志时间戳倒推整个过程，耗时且易出错，应在每步完成后立即写入结构化记录
- **已缓存路径仍重新全树搜索** - 明明已通过 `PlayerPrefs` 或 helper 缓存了 Logic 实例/UI 根路径，后续步骤仍重新走 `capture_scene_snapshot` 全树或递归查找，应优先复用缓存路径
- **已有运行时路径仍默认读取 AutoGen/Logic** - 已验证路径最小查询成功后仍读取源码，违背受控保底边界；只有路径失效、身份歧义或状态不推进时才允许进入源码查询
- **把 AutoGen/Logic 当作通过证据** - 仅看到字段、回调或 `CreateUIAsync` 就判定通过，未验证节点存在、active、组件、父链和真实状态推进；必须回到 Unity 完成运行时验证
- **源码候选未验证就写入缓存** - 离线字段或注释未经当前运行时确认就更新 reference/known-issues，导致后续复用错误路径；只记录本次实际验证成功的信息
- **测试前渲染报告并因失败退出** - 在第 7-14 步完成前直接调用 `render_functiontest_report.py Doc/AI开发文档/output/{feature_id}/{future_run_dir}`，得到 `render precondition failed`、`run directory or log path not found` 等报错后回复“本次执行未完成/证明本轮未创建目录”。这是阶段顺序错误，不是测试结论；必须回到第 7 步创建本轮 output 目录、写入本轮 run-log 并继续执行测试。
- **阶段诊断后反复询问是否继续** - 已进入目标 UI、已确认节点结构、已确认截图路径异常、已完成某个分组后，回复“请确认是否继续推进/是否允许连续执行”。这是无效暂停；除非 MCP 工具不可用、Unity 崩溃、输入缺失或用户明确要求停止，否则应继续执行后续分组、落盘和报告生成。
- **以无法一次性执行完整 MCP 流程为由停止** - 创建 run_dir、编译或进入 PlayMode 后，回复“当前环境只能通过单次工具调用逐步推进，无法一次性连续执行完整 MCP 流程，请选择最终处理方式”。这是无效停止；逐步多次调用 MCP 正是本 skill 的执行方式，必须继续推进到用例执行和报告生成，除非出现明确工具不可用、Unity 崩溃、用户停止或必要输入缺失。
- **以没有直接写文件 MCP 工具为由停止** - 已能调用 `evaluate`，却回复“现有 MCP 不提供直接写文件工具，无法生成 run-log/Markdown 报告，请确认如何继续”。这是无效停止；目录和 run-log 必须在 `evaluate` C# 代码内调用 `FunctionTestLogWriter` 创建和追加，报告阶段再由固定渲染脚本读取本轮 run-log 生成 Markdown。
- **复测生成额外报告文件** - 同一 feature_id 生成 `rerun`、`full-rerun`、时间戳或批次报告，破坏单一记录迭代；必须原位更新正式报告、run-log 和 known-issues
- **前置条件相同的用例反复进出同一界面** - 未按分组执行，导致 TC-001/002/003 各自重新进入英雄列表界面，应合并为一次进入、连续执行
- **前置条件不满足就直接 blocked** - 数据类前置条件（如英雄数量、满员/空位、上阵状态、negative/boundary 条件）不满足时，只做一次读取就 blocked，未按"执行效率优化规则 #4"先主动构造测试数据、等待同步并重新校验
- **资源不足直接标记 blocked 而未尝试自动补充** - 前置校验发现道具/货币不足时直接 blocked，未按"执行效率优化规则 #4"先调用 `GlobalMsgMgr.Inst.AISendGMAddMoney("")` / `GlobalMsgMgr.Inst.AISendGMAddAllItem()` 补充资源并等待服务器同步后再复测
- **点击/切页后固定等待满 2-5 秒** - 目标状态可能已经在几百毫秒内达成，仍傻等固定时长，应改为短轮询+早停
- **对已知不稳定的点击链路仍重复走标准点击→失败→诊断→兜底** - 已确认某节点标准点击不稳定时，应直接跳过标准点击环节，走已验证的兜底方案
- **8秒早停上限只写在规则里没有真正执行** - 普通 UI/业务步骤的 `duration_ms` 出现远超8000ms 的整数值（如20000/26000/28000ms），说明撞到了其他固定超时而非按规则早停，应排查具体轮询实现是否真的遵守8秒上限；登录前置是唯一例外，必须按 4b 记录 `TestBoot` 状态机和 65 秒上限，不能把登录等待误报成普通步骤超时
- **已知问题清单没有真正落盘复用** - 同一个不稳定节点（如 `heroicon` 点击不开详情）在多次运行中反复被当作新问题重新试错，应在首次确认兜底方案有效后立即写入 `known-issues.json`，并同步沉淀到 `references/{feature_id}.md` 的已知问题章节，下次执行前先查询该文件
- **进场流程用"探测一步看一眼"的方式反复试探** - 出现"探测当前界面→发现在登录页→触发登录→再探测是否进大厅→再探测目标UI"这类连续单点试探链路，应改为一次查询同时判定多项状态、一次性决定下一步动作，而不是寄望于缓存（首次进场没有缓存可用，详见"执行效率优化规则 #7"）
- **JSON 记录之间出现无法解释的时间空白** - 相邻两条记录的 end_time 与 start_time 之间有较大间隙却没有对应的步骤记录或原因说明，说明存在漏记的动作或隐藏等待，应排查并补记
- 无可用运行时参考/缓存且最小目标 UI 查询也失败时，未先抓取 `GameEntry/Builtin/UI` 下的必要场景结构，就直接调用 `simulate_click`
- 抓取场景快照时未优先使用默认根节点 `GameEntry/Builtin/UI`，导致快照范围过大或遗漏 UI 定位约束
- 未确认目标节点 path 与 `GameButton`，就直接反射调用业务方法
- 把截图像素坐标（左上角原点、Y 向下）直接当作 Unity 屏幕坐标（左下角原点、Y 向上），未做 `unityY = 图片高度 - py` 翻转
- 在调用 `simulate_click` 前已自行调用 `UnityScreenToSystemScreenConverter` 得到桌面坐标，又把桌面坐标当成 Unity 屏幕坐标传给 `simulate_click`，导致工具二次转换点错位置
- 模拟点击失败后未基于最新截图重新预估一次，就直接归因为业务问题
- 对长按类按钮（`EventTrigger` PointerDown/PointerUp 实现）单纯反复用 `simulate_click`，未识别需要 evaluate 或反射方式触发
- **simulate_click 返回 success 不代表操作成功** - `simulate_click` 只返回”鼠标事件已发送”，不代表按钮被点击或 UI 有响应。正确流程：simulate_click 后**先通过 evaluate 检查 Canvas 下是否有新节点打开、文本/列表/业务状态是否变化**来验证操作是否生效；只有节点状态无法证明、需要视觉验证或失败取证时才补充截图；不能仅凭返回值判断成功
- **截图回传路径读取失败后停止** - `capture_screenshot` 返回路径与当前工作区映射不一致、`Read PNG` 报 ENOENT 或截图文件暂不可读时，只影响截图证据读取；应记录路径异常并继续使用运行时节点、文本、列表数量、按钮状态和业务字段验证。截图不是主路径，不得因此中断用例执行或要求用户确认。
- 无运行时状态证据却标记”通过”
- 强行执行”非功能测试范围”的用例
- **把 GameButton 触发方式写死为单一路径** - 普通 GameButton 默认优先 `ExecuteButtonClick()`，但 Action 委托、GameTabItem、长按/拖拽或已知问题节点可能需要其他已验证方式；任何触发方式返回 success 后，都必须继续验证页面或业务状态变化
- **ScrollView 中 Content 路径动态变化** - `GameObject.Find(path)` 仅匹配激活的根节点，Content 可能是动态生成，路径不固定，需用递归查找
- **onscene 区域按钮（bg1/bg2/bg3）可能不响应 `onClick.Invoke()`** - 本项目上阵区域英雄的点击事件注册方式可能与普通按钮不同，`ExecuteButtonClick()` 触发后无联动时，可尝试 `simulate_click` 作为兜底
- **递归函数内访问局部变量时的命名拼写** - 若局部变量名为 `node`，函数内不小心写成 `nnode`（多字母），编译器会报 identifier 不存在，检查半天发现是拼写错误
- **`toggle.isOn = true` 设置后 UI 未切换就继续下一步** - Toggle 的 `isOn` 赋值会立即返回，但面板切换协程可能还在执行中，应先通过子 UI、Selected 节点、关键文本或列表状态确认界面已切换；节点状态无法证明时再截图确认
- **保底查询中用 AutoGen 字段名（如 `btn_shouchong_1_btn`）直接搜索场景节点** - AutoGen 字段名**不等于**运行时节点名，实际节点名是字段上方注释（如 `btn_shouchong`）；进入保底后应把注释名作为候选，再回到 Unity 验证实际节点和父链
- **登录后只轮询单一 UI 名称** — 只用 `GameObject.Find("UI_Main")` 或某一个固定候选作为登录成功标准，容易在实际已进入 `UI_TDTab`、`UI_TowerDefence_Main` 等项目主界面时误报 `login_wait_timeout`。必须拆分“触发登录”和“独立状态查询”，并用登录界面 active 状态、active 顶层 UI 列表、项目主界面候选和业务数据就绪状态共同判定。
- **不校验列表项业务数据就直接点击首个 card** — 如 `item_toy_card_Logic` 的 `onClick` Lambda 内部有 `OwnState != Owned → return` 守卫。必须先读 `txt_suipian` 等字段找满足条件的项
- **运行时目标名称失败后仍未核对候选 UIID** — 如按钮实际创建 `UI_AttributeOverview`，但测试轮询 `UI_ToyDetailAttr`→永远 null；先以运行时节点和参考记录核对，仍不明确时再进入保底，Grep 当前 Logic 的 `CreateUIAsync` 生成候选 UIID，并回到 Unity 验证
- **同次 evaluate 内混合 action+轮询（`CreateUIAsync` 异步时序）** — `CreateUIAsync` 将 UI 创建调度到主线程下一帧；evaluate 末尾 `while+sleep` 轮询 `GameObject.Find(targetUI)` 必然返回 null，浪费 5-8s 超时。**任何含 `CreateUIAsync` 的触发操作后，必须用独立第二次 evaluate 做轮询**，禁止在一次 evaluate 内做"actions+wait+poll"组合
- **目标 UI 被遮挡弹窗覆盖但未清理** — 上一步用例打开的奖励弹窗、确认弹窗、预览弹窗等未被关闭，遮挡了当前步骤的目标 UI，导致后续截图/验证拍到的是遮挡弹窗而非目标界面。每步轮询确认目标 UI 激活后，必须先执行"UI 遮挡检测与清理 helper"（#51），确认无遮挡后再继续验证

## 操作结果校验规则（重要）

**核心原则：evaluate/simulate_click 返回成功 ≠ UI 实际响应。每次 UI 操作后必须强制校验。**

### UI 打开延迟校验规则（重要，短轮询版，详见"执行效率优化规则 #5"）

**打开新 UI 后，不再固定等待 2-5 秒，改为短轮询检查目标节点状态。**

本项目 UI 框架在触发 UI 打开操作（如点击按钮、Tab 切换）后，存在以下延迟场景：
- UI 面板的激活/隐藏切换有协程延迟
- 资源加载和界面创建有异步过程
- 动画过渡需要一定时间完成
- 状态同步存在帧间延迟

**短轮询要求**：
- 操作后每 300-500ms 轮询一次目标状态（如目标 UI 的 `activeInHierarchy`、列表 `childCount` 是否变化），命中预期立即继续
- 普通 UI/业务步骤早停超时上限统一为 **8 秒**：超过仍未达到预期状态，判定该步骤失败，记录证据（不得无限等待到硬性重试上限才发现问题）；登录大厅前置按 4b 的 `TestBoot` 状态机独立轮询和 65 秒上限执行
- 命中"已知问题清单"中的不稳定节点时，跳过轮询，直接执行已验证的兜底方案
- 仅当无法通过节点状态判断完成（如纯动画/转场特效）时，才退化为固定等待兜底，参考时长：打开新 UI 2-3 秒、关闭 UI 2 秒、Tab 切换 2-3 秒、列表刷新 3 秒，并在记录中标注"视觉动画，采用固定等待兜底"

**注意**：不要在操作后立即通过 evaluate 返回值判断成功，必须通过轮询确认目标节点状态已变化后再截图或抓取场景快照进行校验。

### 必须在校验后确认的关键指标
- **Tab 切换**：目标 Tab 的 `Selected` 子节点 `active=true`，且子 UI Canvas 已创建/激活
- **按钮点击**：按钮所属面板/界面是否打开/关闭，状态文本是否变化
- **列表操作**：列表数据数量是否变化，目标项是否出现在正确位置
- **弹窗**：弹窗是否真的显示出来（优先检查 `activeInHierarchy`、弹窗根节点、标题/正文/按钮文本；节点状态无法证明时再截图）
- **UI 遮挡**：目标 UI 是否被其他激活弹窗遮挡（每步轮询确认目标 UI 激活后，必须先执行"UI 遮挡检测与清理 helper" #51，清理遮挡弹窗后优先用节点状态验证；仍无法证明时再截图）

### 错误示例：相信代码返回值就继续执行
```csharp
// ❌ 错误：toggle.isOn = true 返回 success 只能说明代码执行了，不代表 UI 切换了
toggle.isOn = true;
return “切换成功”; // 继续下一步
```

### 正确做法：状态检查优先，必要时截图确认
```csharp
// ✓ 正确：操作后先用 evaluate 验证 UI 实际状态
toggle.isOn = true;

// 验证实际 UI 状态（通过场景结构或组件状态）
var toggleState = heroTabGo.GetComponent<GameToggle>().isOn;
var childUICreated = GameObject.Find(“UI_TDHeroAll”) != null; // 子 UI 是否存在

if (!toggleState || !childUICreated) {
    return “切换失败，需要重试或换方式触发”;
}

// 若节点状态无法证明预期、需要视觉验证或失败取证，再截图补充证据
// var screenshot = MCP.capture_screenshot("piece-deploy");
return “切换成功”;
```

### 不确定当前界面的排查流程
当不清楚自己当前在哪个界面时，不要连续发多个 evaluate 试探：

1. **枚举活跃 Canvas** - `FindObjectsOfType<Canvas>()` 列出所有活跃界面
2. **检查子 UI 是否存在** - 如 `GameObject.Find("UI_XXX")` 是否返回非 null
3. **检查 Toggle 的 Selected 状态** - 确认哪个 Tab 被选中
4. **检查遮挡弹窗** - 执行"UI 遮挡检测与清理 helper"（#51），确认是否有其他弹窗盖在目标 UI 之上
5. **必要时截图** - 仅当上述状态仍无法确认当前界面、需要视觉验证或失败取证时截图

禁止在未确认当前界面的情况下继续执行后续步骤。

## 服务端交互测试规则（非本地 UI 链路验证）

**核心原则：`点击按钮 → 发包 → 收包 → 界面变化` 是完整的客户端可观测链路，不应仅因为"需要服务器响应"就标记 blocked。**

### 可执行判定标准

满足以下**全部 3 条**即可在 MCP 环境中执行，无需数据 Mock：

1. **本地 UI 弹窗可观测**：点击后可通过 `GameObject.Find("UI_MessageBox" / "UI_CommonConfirm")` 读取确认弹窗
2. **网络包可由客户端主动发送**：`btn.onClick?.Invoke()` 触发 `TryXxx()` → `XxxMsgMgr.Inst.SendXxx()` 发网络包（PlayMode 测试服环境网络正常）
3. **服务器响应有本地 UI 落点**：收包后客户端创建新的 UI 节点（如 `UI_Xxx_ResultView`），可通过 `GameObject.Find` 短轮询确认

### 标准验证链路

```
1. btn.onClick?.Invoke() 触发操作
2. 短轮询确认弹窗/过渡状态（300ms，≤3s）
   → 读弹窗文案（GameText.text）确认内容
3. confirmButton.onClick?.Invoke() （或 cancelButton）
4. 短轮询目标结果 UI.activeInHierarchy（300ms，≤8s）
5. 读状态（名称/数值/新标签等）；节点状态无法证明、需要视觉验证或失败取证时再补充截图
6. Option: 结果页点击再操作按钮 或 关闭返回
```

### 常见模式速查

| 功能 | 发包触发点 | 弹窗 | 结果 UI | 额外注意 |
|------|----------|------|--------|---------|
| 抽卡 | `TryDrawCard()` | `UI_MessageBox`（Canvas4） | `UI_DrawCard_ResultView`（Canvas3） | 再抽不弹窗，直接发包 |
| 商店购买 | `TryBuy()` | 可能有确认弹窗 | 购买成功提示/物品获得 | 检查道具数量变化 |
| 升级/升星 | `TryLevelUp()` | 通常无弹窗 | 属性面板刷新 | `GameText` 数值变化 |
| 战令领取 | `TryClaim()` | 可能有确认弹窗 | 奖励弹窗/道具获得 | 检查领取状态变化 |

### 当前环境无法构造的情况（test_inconclusive）

- 需要故障注入才能验证的异常刷新、网络断开/失败恢复
- 需要服务端竞争条件或多客户端协同的并发场景
- 需要服务器时间推进（免费次数重置、限时活动）但当前环境无法构造
- 纯服务端逻辑（掉落概率校验、保底触发次数精确值）且当前客户端无可验证落点

以上标记为 `test_inconclusive`，并在报告中记录无法构造的具体条件；不得计入 `failed` 或日志上报的失败统计，只计入 `invalid_case_count`。

> **资源不足已不再属于 blocked 范畴**。测试中可通过 [`GlobalMsgMgr.Inst.AISendGMAddMoney("")`](Assets/Scripts/CyStarRoad/Container/GlobalContainer/GlobalMsgMgr.cs:531) 和 [`GlobalMsgMgr.Inst.AISendGMAddAllItem()`](Assets/Scripts/CyStarRoad/Container/GlobalContainer/GlobalMsgMgr.cs:537) 自动补充货币与道具，详见"执行效率优化规则 #4"中的资源自动补充流程。

---

## 阻塞条件修订

原阻塞条件第 1 条不变。**补充**：

**不再将「需要服务器响应」作为 blocking 条件**。只要点击操作可触发网络发包，且收包后有本地 UI 落点可用 `GameObject.Find` 短轮询，即可在 MCP 中完成完整链路验证。

## 速查
- 必要输入：功能测试文档（或路径）；`feature_id` 可选，缺少时推断
- 执行模式：纯 MCP 编排，不生成 C# 测试脚本
- 证据：使用 MCP 原样返回路径
- PlayMode：开始 `enter_test_scene`，结束 `stop_scene_play`
- **启动前编译检查**：进入 PlayMode 前必须先执行 `focus_unity_window.ps1`；已找到当前项目 Unity 时调用 `execute_compile`，首次无响应/超时再聚焦并重试一次；最终编译失败或无安全目标时终止执行、直接生成报告注明原因，不进入 PlayMode
- **failed 处理按修复模式执行**：允许修改代码时，任何 `failed` 步骤先修复→复测→再继续；只测不修模式下，任何 `failed` 步骤只记录证据、根因判断和建议修复方向，不修改代码、不触发自动修复复测。环境/强关联前置不可用的用例保留 `blocked`；无法构造目标异常或边界条件的用例保留 `test_inconclusive`；达到修复上限仍失败的用例保留 `failed`。报告必须生成并展示四种真实 verdict；`test_inconclusive` 数量写入上报 JSON 的 `invalid_case_count`，总用例数写入 `total_case_count`；允许修改代码时修复记录实时写入 JSON，最终汇总到报告"4.1 自动修复记录"；单次测试全局最多修复 3 轮
- 本轮完成门禁：新一轮测试执行结束后必须有本轮新 `run_dir`、本轮实时 run-log 事件、本轮报告三件套；这是执行后验收条件，不是执行前置条件；执行前目录不存在时先创建并执行，不能直接渲染未来目录
- 运行目录：`Doc/AI开发文档/output/{feature_id}/{run_dir}/`，`run_dir={feature_id}-{sequence}`；默认永远取同 feature_id 历史最大 4 位序号 +1，例如已存在 `hero-list-0029` 时新一轮使用 `hero-list-0030`
- 实时记录：`Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-run-log.json`，每步执行完立即写入，报告基于本轮 run-log 渲染，不倒推
- 日志契约：执行前必须读取 `references/execution-log-schema.md`；聊天窗口显示原文日志、run-log 字段和 Markdown 日志报告必须按该契约输出
- 已知问题清单：`Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-known-issues.json`，点击前先查询，命中直接走兜底，新发现的问题当次运行内必须写入
- 报告：`Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-unity-functiontest-report.md`
- 非功能测试范围：在报告中标记并跳过
- 分组执行：前置条件相同的用例一次进入、连续执行
- 分组调用：同组用例用 1 次 `RunSuite` 合并执行，不逐条发起 evaluate
 - 前置校验：操作前先纯读取校验前置条件；不满足时先主动构造测试数据/账号状态并复验，环境可运行但目标条件仍无法构造时记 `test_inconclusive`，环境/强关联前置不可用时才记 `blocked`
- 等待策略：普通 UI/业务步骤短轮询（300-500ms）+ 早停（≤8秒），非视觉场景不用固定等待；登录大厅前置使用 `TestBoot` 状态机独立轮询（200-300ms，最长 65 秒），超限步骤必须写明原因
- **UI 遮挡检测**：每步轮询确认目标 UI 激活后，必须先执行遮挡检测与清理（helper #51），确认无遮挡弹窗后才继续验证；白名单：`UI_Test`、`UI_NoticeTipsUP`、`UI_CommonUIMask`、`UI_TouchBlock`
- 已知不稳定节点：直接走已验证兜底方案，跳过标准点击重试
- 路径缓存：首次定位后缓存绝对路径，后续优先复用
- AutoGen/Logic 保底：先查 `ui-quick-reference`，再查运行时参考/缓存；仅在两处参考不足、运行时查询失败、歧义或无状态推进时限定读取源码；源码只生成候选，必须回到 Unity 验证
- 复测产物：只有用户明确指定复测/继续/修复/覆盖某个 `run_dir` 时，才原位更新该目录的正式 run-log、known-issues 和报告；新的独立运行必须使用下一个 4 位序号目录
- 进场判定：登录/大厅/目标UI 用一次状态查询判定+一次性决策；登录成功用“登录界面状态 + active 顶层 UI 列表 + 项目主界面候选 + 业务数据就绪”组合判断，禁止只认单一 `UI_Main`；缓存仅对失败重试/连续多feature场景有效，首次进场无缓存可用
- 记录连续性：相邻JSON记录间隙超2秒需有原因说明，不允许"消失的时间"
- 历史对比：如有历史 timing，报告比较同 feature_id 的 Skill 有效耗时；缺少 timing 时如实标注

## 加载指引
处理本项目 Unity 功能测试任务时，直接加载 `unity-functiontest`。其余 skill 仅按需加载：
- `ui-quick-reference`：需要离线生成 UI 快速参考图谱（AutoGen 字段映射、按钮回调映射）时加载
- `ui-framework-kb`：需要理解 UI 组件、弹窗、页面、控件命名时加载
- `dev-code-standards` / `cyoucode-unity-framework-kb`：仅当修改代码时加载
