---
name: functiontest-workflow
description: 编排 Unity FunctionTest 完整工作流：可先选择本地 testcase-gen 生成测试用例、testcase-mcp-complete 质量部生成测试用例，或直接使用本地已有测试用例；随后调用 unity-functiontest 执行测试并写入 run-log，workflow 结束计时后统一生成 Markdown 报告，再调用 functiontest-report-json 转换 JSON，读取 Cyou 会话用量快照并合并进 JSON，符合上报条件时调用 functiontest-json-upload 上传日志中心。本版本不发送 cyou 开始标志或结束标志。适用于“一键生成用例并测试上报”“输入测试用例后完整执行 functiontest 流程”“测试用例路径自动测试上传”等需求。
---

# FunctionTest 完整工作流

本 Skill 是职责 A：只做编排，不直接执行 Unity 测试、不直接解析报告、不直接实现上传协议。

本 Skill 中的 `../{skill-name}/...` 路径均相对于本文件所在的 Skill 目录解析，不是相对于项目根目录解析。

## Skill 时间记录（强制）

本 Skill 必须遵守 `../functiontest-report-json/references/skill-timing-contract.md`。收到 workflow 调用后、第一次用户确认前，先创建唯一 timing 文件（例如 `Doc/AI开发文档/output/.skill-timing/workflow-{唯一标识}.json`）并调用 `../functiontest-report-json/scripts/skill_timing.py start` 记录 `functiontest-workflow` 的 `invocation_id`，这样用户确认等待可以按环境变量扣除。该 timing 文件必须在所有子 Skill 间复用；子 Skill 调用时传入相同文件和 `parent_invocation_id`，不得各自新建计时上下文。子 Skill 只记录自己的原始起止时间，不扣除会话环境变量；环境时间过滤只由本 Workflow 根记录在最终上报时统一执行一次。

Workflow 自己的 `skill_end` 必须在所有业务子流程、Unity 测试、reference 收口和报告所需数据准备完成后、JSON 转换前写入。随后由 Workflow 统一渲染/转换，并在通过上传门禁时上传一次。Workflow 的时间是包含子 Skill 的整体原始时间，最终上报时只由 Workflow 根记录扣除本时间范围内的审批和上下文压缩增量；不把子 Skill 时间相加，也不让子 Skill 重复扣除会话累计值。若子流程单独调用，则它没有父级，按根 Skill 规则独立计算和上报。

固定串联顺序：

```text
workflow skill_start
测试用例来源判断
-> 生成或确认最终测试用例路径
-> 调用 unity-functiontest 启动前置阶段 A（依次询问识图能力、截图开关和效果图对比开关）
-> 调用 unity-functiontest 启动前置阶段 B（仅询问修复模式）
-> 离线 UI reference 前置检查/生成
-> unity-functiontest 执行本轮测试
-> 按当前 UIName 实时读取效果图路径并按需调用 ui-image-diff（每个 UI 最多一次）
-> 运行时 UI reference 收口检查
-> 离线 UI reference 缺陷回刷（仅有缺陷记录时）
-> workflow skill_end
-> 生成最终 Markdown 报告
-> functiontest-report-json
-> check-cyoucode-spend
-> 通过全量用例状态门禁后调用 functiontest-json-upload（全 blocked 或全 test_inconclusive 时跳过）
```

版本说明：本版本不发送 cyou 开始标志或结束标志；后续如需接入 cyou 标志，再作为独立步骤补充。

## 启动交互

直接调用 `functiontest-workflow` 时，先询问用户本轮要采用哪一种测试用例来源；workflow 不复制或改写 `unity-functiontest` 的启动前置问题文本：

```text
请选择本轮测试用例来源：
1. testcase-gen 本地生成测试用例Skill
2. testcase-mcp-complete 质量部生成测试用例Skill
3. 直接使用本地已有测试用例文档
```

用户选择后，只能使用以下固定文本索要对应路径；此时不得同时询问是否允许修改代码：

- 选择 `testcase-gen 本地生成测试用例Skill` 时，固定询问：
```text
请提供本轮用于 testcase-gen 本地生成测试用例的策划设计文档路径。
```

- 选择 `testcase-mcp-complete 质量部生成测试用例Skill` 时，固定询问：
```text
请提供本轮用于 testcase-mcp-complete 质量部生成测试用例的策划设计文档路径。
```

- 选择“直接使用本地已有测试用例文档”时，固定询问：
```text
请提供本轮要直接执行的测试生成文档路径。
```

用户回复路径后，先确认该路径已收到；如果调用了用例生成 Skill，则先完成用例生成并以生成完成后的最终测试用例路径为准。最终测试用例路径确认后，依次调用 `unity-functiontest` 的启动前置阶段 A 和阶段 B，由该 Skill 分别询问识图能力/截图开关/效果图对比开关和修复模式。`testcase-gen` 和 `testcase-mcp-complete` 的输入是策划设计文档，`unity-functiontest` 的输入是最终测试生成文档，不得混用。

## 提问工具边界

workflow 自身调用 `Ask user question` / `request_user_input` 只用于完成测试用例来源选择及对应路径索要。识图能力、截图开关、效果图对比开关和修复模式的问题文本与选项由 `unity-functiontest` 提供，workflow 只能按固定顺序调用其启动前置阶段 A/B，不得代问、改写、缩减、摘要、省略、跳过或覆盖结果。除这两个启动前置阶段外，workflow 的其余阶段以及 `functiontest-report-json`、`check-cyoucode-spend`、`functiontest-json-upload` 执行期间不得调用提问工具询问是否继续、选择执行策略、确认阶段诊断、确认截图异常、确认耗时较长、确认是否生成报告或确认是否上传。遇到可继续执行的问题，直接继续；遇到真实阻塞，按失败处理规则记录并收口。

## 输入

路径契约固定为：输入 `Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}/`，输出 `Doc/AI开发文档/output/{feature_id}/{run_dir}/`，其中 `run_dir={feature_id}-{seq4}`。旧的 `Doc/AI开发文档/{feature_id}/testcases/` 和 `Doc/AI开发文档/{run_dir}/` 不再是正式输入/输出路径。

输入参数统一指向一个完整版本目录；编排层从该目录读取实际测试用例文件，不接受目录外散落文件作为正式输入。支持：

```text
测试用例路径
策划设计文档路径
测试生成文档路径
```

正式输入目录必须满足：`Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}/`。如果调用方传入目录内的具体文件，其父目录必须仍是该版本目录；不得接收旧的 `Doc/AI开发文档/{feature_id}/testcases/` 路径。

当前不再要求用户输入测试人名称，也不要求用户在路径中填写项目名。上传前优先从 `CYOU_API_KEY_ALIAS` 写入 `tester_account`，从 `CYOU_TEAM_ALIAS` 写入 `project_group`；对应环境变量缺失或为空时，读取本 Skill 的 `config.json` 中同名字段；配置文件缺失、格式错误或字段为空时写“无”。不得从测试用例路径、报告路径、目录名、Markdown 报告内容或用户路径输入推断项目组。

默认配置文件为 `config.json`：

```json
{
  "_comment": "本配置仅在非 Cyou 环境，或 Cyou 环境存在但无法读取用户名和项目组环境变量时生效；环境变量有值时始终优先使用环境变量。",
  "tester_account": "无",
  "_tester_account_comment": "日志系统对应字段：tester_account（用户名）",
  "_project_group_comment": "日志系统对应字段：project_group（项目组名）",
  "project_group": "无"
}
```

用户可以根据实际情况修改 `tester_account` 和 `project_group` 两个字段。

## 测试用例来源判断

执行工作流前必须先判断或询问用户输入属于哪一种来源：

1. 如果用户明确说“本地生成测试用例”“用 testcase-gen 生成”“从需求文档本地生成”，则先调用 `testcase-gen`。
2. 如果用户明确说“质量部生成测试用例”“用 testcase-mcp-complete”“用线上 MCP 生成”“上传需求到 MCP 生成”，则先调用 `testcase-mcp-complete`。
3. 如果用户明确说“直接使用本地测试用例”，或输入路径已经是可被 `unity-functiontest` 直接执行的测试用例文件，则跳过用例生成，直接进入测试。
4. 如果用户只调用了 `functiontest-workflow`，必须先询问三种来源；如果选择 1 或 2，再索要策划设计文档路径；如果选择 3，再索要测试生成文档路径。必要时完成用例生成并确认最终测试用例路径后，再由 `unity-functiontest` 依次完成启动前置阶段 A 和阶段 B，阶段 A 询问识图能力/截图开关/效果图对比开关，阶段 B 询问修复模式。
5. 如果用户只给了文档路径，但没有说明生成方式，必须先询问用户选择：`testcase-gen 本地生成`、`testcase-mcp-complete 质量部生成`、`直接使用本地测试用例`。得到选择后再继续。

测试用例生成完成后，后续 `unity-functiontest` 只接收最终生成出的测试用例文件路径，不接收原需求文档路径。

## 自生成测试用例输出目录

本目录规则只适用于 `testcase-gen` 和 `testcase-mcp-complete` 新生成的测试用例产物。用户选择“直接使用本地已有测试用例文档”时，无论该路径是否位于下述目录，都不得复制或移动，必须直接把用户提供的原路径传给 `unity-functiontest`。

自生成测试用例文件必须与测试报告目录分开存放，不能混入 `hero-list-0001` 这类测试运行报告目录。

输入统一放在：

```text
Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}/
```

其中：

- `{feature_id}` 是功能名，例如 `hero-list`。
- `{seq4}` 是 4 位递增编号，例如 `0001`、`0002`。
- 默认永远取 `Doc/AI开发文档/input/{feature_id}-testcases/` 下已有 `{feature_id}-testcases-####` 的 `max+1`。
- 只有用户显式要求复测或覆盖某个测试用例目录时，才允许写入已有编号目录。

示例：

```text
Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0001/test_case_hero_list.json
Doc/AI开发文档/input/hero-list-testcases/hero-list-testcases-0002/test_cases_document_682.xlsx
```

`testcase-gen` 或 `testcase-mcp-complete` 如果原始输出不在上述目录，工作流必须把最终可执行测试用例复制或移动到上述输入编号目录，再把该路径传给 `unity-functiontest`。用户直接提供的本地已有测试用例也必须位于 `Doc/AI开发文档/input/` 下；旧路径不得作为正式输入。

## 测试报告输出目录

测试报告继续放在测试运行目录中，必须与测试用例目录区分：

```text
Doc/AI开发文档/output/{feature_id}/{feature_id}-{seq4}/
```

新的独立测试默认取 `Doc/AI开发文档/output/{feature_id}/` 下已有 `{feature_id}-####` 的 `max+1`，例如已有 `hero-list-0029` 时，新一轮生成 `hero-list-0030`。

只有用户显式指定复测、覆盖某个运行目录，或已经开启自测自修时，才允许写入已有目录；自测自修的修复、重新编译和验证固定使用当前 `run_dir`，收口阶段不得自行创建 `max+1` 新轮次。

Markdown 报告中必须记录本轮实际使用的测试用例路径，保证报告能反查输入来源。

## Reference 前置与收口

本 Skill 负责编排两类 UI reference 的生命周期，不把离线 reference 的生成依赖到 Unity 测试执行阶段。

固定路径：

```text
离线结构 reference：`../ui-quick-reference/references/{feature_id}.md`
运行时实测 reference：`../unity-functiontest/references/{feature_id}.md`
```

### 测试前：离线 reference 前置检查

在测试用例路径和 `feature_id` 确认后、调用 `unity-functiontest` 前，必须执行一次离线 reference 前置检查：

1. 根据当前测试目标解析目标 UIName；优先使用已有 reference、测试用例中的 UI 信息和由 `ui-quick-reference` 动态查找的 `UILogicManager` 文件，不得仅凭模糊功能名盲选多个 UI。
2. 检查 `../ui-quick-reference/references/{feature_id}.md` 是否存在且有效。有效至少包括：`feature_id`、目标 UIID/UI 根节点、Prefab/AutoGen 结构信息和中文标题/语义说明；空模板、纯英文展示、目标不匹配或已记录为过期的文件视为无效。
3. 文件不存在或无效时，调用 `ui-quick-reference` 的 `scripts/scan_ui_references.py` 生成到其 `references/` 目录。不得写入其他 Skill 的运行时 reference 目录。
4. 文件存在且有效时跳过生成，直接进入 `unity-functiontest`。
5. 扫描失败、UIName 无法唯一解析或资源缺失时，写入本轮 reference 缺陷记录并继续 Unity 测试；不得因为离线 reference 缺失减少 functional 用例覆盖或直接将用例标记为 blocked。

离线 reference 的生成由本 Skill 编排、`ui-quick-reference` 执行；`unity-functiontest` 只读取它并在运行时记录缺陷，不负责离线文档的正常生成。

### 效果图配置读取规则

离线 reference 禁止保存 `UILogicManager.xlsx` 位置、`UIPerfectPath`、文件存在性、解析状态或“未配置”结论。该禁止范围仅限表格定位和效果图配置；已验证 UI 节点绝对路径、Logic 实例等运行时缓存仍按 `unity-functiontest` 的规则处理，且不得作为效果图配置来源。每次效果图对比前，必须按当前准确的 `UIName` 调用 `../ui-quick-reference/scripts/read_ui_effect_path.py`，从当前工作区重新定位并读取最新内容。工作区是传入的 `project_root`；项目根目录仅在工作区、上一级、上两级内按 `Public`、`Art`、`Doc`、`Server` 等目录的精确或有限模糊匹配评分确定，同分取更外层目录，无匹配时取向上两级。表格和图片都执行相同四步：工作区、上一级、上两级依次精确查找，均未命中时只在本次确定的同一个项目根目录内进行一次模糊搜索。表格精确查找使用每个候选下的标准 `Public/Tables/Excel/Client/UILogicManager.xlsx`（兼容导表临时路径）；图片相对路径直接拼接每个候选。`UIPerfectPath` 为绝对路径时直接使用，未找到则按未填写处理并提示检查路径；查询结果中的 `resolved_path` 是已验证可直接打开的绝对路径，`configured_path` 保留表格原值，`path_source` 和 `match_mode` 用于审计本次命中方式；绝对路径失败、模糊匹配无结果、最高候选并列或匹配度过低时均按未填写路径处理，并提示检查路径，不再继续查找。只有实时查询返回有效文件路径时才允许调用 `ui-image-diff`；未配置或未找到时跳过当前 UI 的效果图对比截图，只记录跳过原因，不停止 Unity/PlayMode、不因该原因生成 `blocked` 用例、不阻塞普通功能测试。

### 测试后：运行时 reference 收口

`unity-functiontest` 返回后、调用 `functiontest-report-json` 前，必须检查运行时 reference：

1. 如果本轮已进入目标 UI，`../unity-functiontest/references/{feature_id}.md` 必须存在，并至少包含中文标题/章节说明、实测 UI 根路径、进入方式、已验证触发方式和状态验证方式；技术标识保持原样但必须配中文语义解释。
2. 如果测试过程中发现新的路径、触发方式、遮挡处理或已知问题，必须先写入本轮 `run-log`/`known-issues`，再增量更新运行时 reference。
3. 如果运行时 reference 缺失或内容不完整，调用 `unity-functiontest` 的“reference-only 收口”子流程；该子流程只能读取本轮 `run_dir` 的实时日志和已验证证据，不得重新执行测试、创建新 `run_dir`、修改 verdict 或重新生成报告。
4. 如果本轮在编译、PlayMode 或进场阶段就被阻塞，未获得目标 UI 实测证据，不得伪造运行时 reference；在报告和日志中记录 `runtime_reference_gap`，继续后续报告流程。

### 测试后：离线 reference 缺陷回刷

测试过程中如果记录了 `static_reference_gap`、`static_reference_mismatch` 或静态节点映射错误，workflow 在运行时 reference 收口后调用 `ui-quick-reference` 刷新离线 reference。仅有运行时路径差异、触发方式差异或已知问题时，不得把运行时事实写回离线 reference，应只更新运行时 reference。

离线 reference 和运行时 reference 的缺陷回刷都必须是增量更新，不得删除本轮以外的有效资料。

## 执行规则

本流程不使用 `case-map`。测试用例 JSON 是唯一输入来源，Case 的操作链在当前运行中按实时 UI 状态生成并直接写入该 Case 的 `run-log` final record；`run-log` 同时承担操作证据、独立断言和覆盖审计。不得读取历史 case-map、生成新的 case-map，或用中间映射恢复下一条 Case 的操作路径。

### 测试目标与 CaseExecutionPlan 强制门禁

本流程的测试目标是：验证输入 JSON 中每条用例定义的业务行为，而不是为每个 `CaseId` 生成一条看起来完整的执行记录。`CaseId` 数量完整、final record 格式正确或覆盖率通过，均不能替代业务行为验证。

1. 每个 functional Case 必须依据该 Case 在输入 JSON 中的 `preconditions`、`source_steps`/`steps`、`operations`、`assertion` 和 `expected` 生成独立的 `CaseExecutionPlan`；计划必须保留能够反查原始用例字段的内容或哈希。
2. `RunSuiteAndRecord()` 只执行调用方传入的 `CaseExecutionPlan[]`，不会自动解析 JSON。编排层不得把统一的 `snapshot`、统一的界面/节点状态断言、统一的操作链或统一的 expected 套用到多个未明确声明可复用的 Case 上。
3. 在正式批量执行前，必须审计计划与输入 JSON 的一一对应关系，并检查计划的操作链、断言和 expected 是否与原始 Case 语义一致。多个 Case 只有在明确声明“共享进入路径/共享只读查询”时才允许共享对应前置；每个 Case 仍必须保留自己的可执行操作、断言和 expected。计划映射不完整时，记录 `mapping_level=partial`、`mapped_steps` 和 `unmapped_steps`，不得把整个 run 判为无效，也不得用统一计划覆盖全部 Case。
4. **无法自动理解全部自然语言步骤，不等于无法执行任何业务操作。** `OpMap` 只是动作复用方式，不是业务前置条件；没有 OpMap 时，必须继续通过运行时路径探查、实时状态判断、已验证的直接调用或其他现有测试入口执行。必须按 Case 逐条拆解 `preconditions`、`source_steps`/`steps`、`operations`、`assertion` 和 `expected`：优先复用当前已验证的 UI 路径、操作映射、Logic/reference 事实和运行时已发现控件，将可安全映射的触发、输入、选择、导航、等待、观察和状态查询按原顺序执行；只对确实无法映射的步骤记录 `unmapped_steps`。禁止因为缺少 OpMap或一部分自然语言暂时无法解析，就把整条 Case 替换为统一 `snapshot` 计划。
5. **部分映射必须继续真实测试。** 对包含交互步骤的 Case，至少执行所有已验证且与核心 expected 直接相关的真实操作，并在动作后独立查询业务状态。`snapshot` 只能作为显式观察步骤或辅助证据，不能作为所有 Case 的默认操作；动作回执、页面存在或覆盖记录不能代替业务断言。若核心验收条件已由实际操作和独立断言完整覆盖，即使存在不影响核心结论的附属描述步骤未映射，也可以依据实际证据判定 `passed` 或 `failed`，同时记录遗漏步骤。缺少 OpMap只影响某种动作复用方式，不是 `test_inconclusive` 的充分理由；若核心验收条件仍无法执行或验证，才记录 `test_inconclusive`；若环境/强关联前置导致连已映射操作都无法开始，才记录 `blocked`。
6. “放宽 pass 条件”只放宽自然语言完整映射的要求，不放宽业务证据要求：`passed` 必须仍有该 Case 的真实操作（纯展示/只读 Case 可使用与其目标字段对应的读取）和独立最终断言；`failed` 必须来自已执行操作后的预期不符；`test_inconclusive` 不能仅因为无法完整还原自然语言而批量产生。执行过程中必须优先扩大真实操作覆盖，不能为了避免误判而把所有 Case 统一降级为 `test_inconclusive`。
7. 当前 run 因编排错误、计划映射错误或证据门禁失败而无效时，只关闭并标记当前 run 为 `invalid_run`，保留原始证据和原因；不得把“当前运行无效”扩大为“整个测试任务终止”。默认只在本轮创建临时编排/辅助代码并在结束后删除，再创建新的递增 run_dir，从完整输入 JSON 重新执行；测试结束后的既有测试代码修改属于独立工作，不并入当前测试流程。只有用户明确取消任务、环境持续阻塞且无法恢复或其他流程定义的终止条件，才允许终止整个任务。
8. 分组执行只是优化手段，不是测试成立的前提。若当前环境无法证明多个 Case 可以安全分组，必须降级为逐个 Case 独立执行，不能串联前一条 Case 的操作、状态或断言。除明确的环境阻塞外，任何标记为 `passed` 或 `failed` 的 Case 都必须同时具备该 Case 独立的实际操作证据和独立最终断言证据；无法真实执行核心验收条件的 Case 才标记为 `test_inconclusive`，不得把“自然语言未完全解析”当作整批 Case 的统一兜底理由。

1. 解析输入得到原始路径；`project_group` 和 `tester_account` 按“环境变量优先、`config.json` 兜底、最终使用‘无’”的规则读取。
2. 按“测试用例来源判断”确定是否调用 `testcase-gen` 或 `testcase-mcp-complete`；如果生成了新测试用例，先归档到 `Doc/AI开发文档/input/{feature_id}-testcases/{feature_id}-testcases-{seq4}`。如果用户选择直接使用本地已有测试用例文档，则要求其位于该 input 目录下后再执行。
3. 在最终测试用例路径确认后，依次调用 `unity-functiontest` 的启动前置阶段 A 和阶段 B；阶段 A 依次处理识图能力、截图开关和效果图对比开关，阶段 B 处理修复模式。workflow 只接收两个阶段返回的结果，不自行判断或覆盖。两种修复模式都不得修改既有 `TestHelper`、`FunctionTestLogWriter` 等测试基础设施；只读不修模式覆盖 `unity-functiontest` 内“failed 必须先修复再生成报告”的默认口径，改为“failed 保留真实 verdict 并照常生成报告”。
4. 执行“Reference 前置与收口”中的离线 reference 前置检查；该阶段必须发生在 Unity 测试前，且失败只记录 reference 缺陷，不减少测试覆盖。
5. 调用 `unity-functiontest` 执行测试时，传入最终测试用例文件路径、启动前置阶段 A/B 已返回的 `vision_capability`、`screenshot_enabled`、`effect_diff_enabled`、`repair_mode`、timing 文件路径和 workflow 的 `invocation_id`；`unity-functiontest` 必须校验四个状态均已确认，不得再次询问。它负责执行本轮 Unity 测试、按已确认的截图开关采集或禁用运行时截图、在效果图开关打开时按当前 UIName 实时读取效果图并生成子流程输入、写入 run-log 和闭合自己的 Skill 时间；由 workflow 调用时不单独渲染、转换或上传 Markdown/JSON。传入的是完整测试用例文件路径，不是文件预览内容、前 N 条样例或当前上下文片段；`unity-functiontest` 必须自行读取该文件的全部用例并以全量解析结果作为覆盖基准。workflow 判断 Unity 测试阶段成功时必须同时确认：本轮新 `run_dir` 已创建、run-log 第一条是 `setup`、中间存在编译/进场/用例执行事件，且 `query_logs` 已在实际 stop_playmode 前按 `details.type/message/stack_trace` 写入。PlayMode 实际启停不再额外写入开始/结束 run-log 记录。源码确认、运行时路径确认、目标 UI 已进入、下一步方向明确、已完成某个阶段或分组，都不算测试阶段完成。
5.1 效果图子流程在 `unity-functiontest` 执行期间完成、由 workflow 负责最终收口：对每个首次真实进入且状态稳定的唯一 `UIName`，调用 `../ui-quick-reference/scripts/read_ui_effect_path.py <UIName> --project-root <工作区目录>` 从当前工作区重新定位表格与基准图；不读取 reference 路径。表格和相对图片均依次检查工作区、上一级、上两级，均未命中时仅在按项目目录标记评分确定的同一个项目根目录内模糊搜索。返回 `found` 后采集一张稳定截图，再调用 `../ui-image-diff/SKILL.md` 生成 `run_dir/ui-image-diff/` 下的报告。同一 UI 本轮最多对比一次。绝对路径失败、精确和模糊匹配都未找到、最高候选并列、匹配度过低、表格解析失败或 UI 不匹配时均提示检查路径、按未配置处理并跳过当前 UI 的效果图对比截图；效果图对比不单独转换 JSON、不单独上传，也不自动把视觉差异计为 failed 或 Bug。workflow 最终报告统一收录这些对比报告和跳过原因。
5.2 每次调用 `mcp__mymcp__execute_compile`（包括首次编译、修复后重编译和烟测编译）前，`unity-functiontest` 必须先执行 `../unity-functiontest/scripts/focus_unity_window.ps1 -ProjectRoot <当前工作区目录>` 并保留原始输出和退出码。输出 `UNITY_FOCUSED`（退出码 0）时立即编译；输出 `UNITY_FOUND_FOCUS_FAILED` 或 `UNITY_FOUND_NO_WINDOW`（退出码 4/3）但已确认找到本项目 Unity 时仍立即尝试一次编译，不得把前台失败直接当成编译失败；只有 `PROJECT_ROOT_INVALID` 或 `UNITY_NOT_FOUND`（退出码 1/2）才禁止编译。首次编译无响应或超时后，再重新聚焦并重试一次；取得明确编译成功或编译错误回执后不重复调用。聚焦脚本和每次编译的原始结果都要记入本轮编译前置证据。
6. 执行“Reference 前置与收口”中的运行时 reference 收口和离线 reference 缺陷回刷；仅在该收口完成或已记录 `runtime_reference_gap` 后，才能结束 workflow 业务阶段。

7. 调用 timing 脚本结束 `functiontest-workflow` 的 `invocation_id`。结束后再调用 `../unity-functiontest/scripts/render_functiontest_report.py`，传入本轮 run-log、同一 timing 文件和 `--skill-name functiontest-workflow`，生成最终 Markdown 报告。Workflow 内的 Unity 子 Skill 不得提前生成最终报告。

```text
Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-unity-functiontest-report.md
```

8. 调用 `functiontest-report-json`，必须把最终 Markdown 报告和同一 timing 文件作为输入，并把本轮唯一的 JSON 路径作为输出；不得只传 feature 目录或依赖 Cyou 自动查找历史文件。固定传入操作类型“主动测试工作流”和 `--skill-name functiontest-workflow`。若 output 已存在，默认停止；只有用户明确要求复测/覆盖指定 run_dir 时才额外传 `--allow-overwrite`。`functiontest-report-json` 按环境变量优先、`../functiontest-workflow/config.json` 兜底的规则写入用户名和项目组，生成：

```text
Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-functiontest-upload.json
```

9. 调用 `check-cyoucode-spend`，读取当前 Cyou 环境快照；随后调用 `functiontest-report-json` 的合并步骤，并传入同一 timing 文件。`functiontest-report-json` 在其自身 Skill 内负责读取当前 AI 对话上下文中的实际模型名并传入 `--ai-model`；workflow 不重复实现或代为获取，只需确保该参数链路不被覆盖。合并步骤只更新 Token、消耗、身份和模型，不覆盖已经确定的 Workflow Skill 时长。
10. 上传前读取本轮 JSON 的 `user_stats_payload.items[0].custom_metrics`：若 `total_case_count>0` 且 `block_case_count` 等于总数，或 `invalid_case_count`（对应 `test_inconclusive`）等于总数，则保留报告和 JSON，记录不上报原因，不调用 `functiontest-json-upload`；其他情况才传入最终 JSON 路径执行一次上传。该规则只针对“全部阻塞”或“全部 test_inconclusive”，混合状态仍按正常规则处理。
11. 最终回复只列出测试用例路径、修复模式、报告路径、JSON 路径、reference 收口状态、spend 快照和上传结果，避免重新总结大报告。

## 上报操作类型

本 Skill 完成完整主动测试后，调用 functiontest-report-json 时必须使用固定中文操作类型“主动测试工作流”。最终 JSON 的 `user_stats_payload.items[0].custom_metrics.operation_type` 必须写入该值，再按原顺序调用 check-cyoucode-spend，并在通过全量用例状态门禁时调用 functiontest-json-upload。

functiontest-workflow 内部调用任何业务子 Skill（包括 `testcase-gen`、`testcase-mcp-complete`、`ui-quick-reference` 和 `unity-functiontest`）时，不触发子 Skill 单独上报；子 Skill 只返回产物和已闭合的原始子 Skill 时间，由本 Skill 结束自身根计时后统一按根记录过滤环境时间、渲染报告、转换、合并用量，并在通过上传门禁时上传一次。

## 修复范围与日志安全门禁

- `只读不修` 测试流程进行期间不修改项目业务代码、业务资源、业务配置、生产逻辑和项目中已有的测试代码；`Assets/.../Test` 下已有的 `TestHelper`、`FunctionTestLogWriter` 等文件保持不变。只允许 AI 本轮创建并在结束后删除的临时编排/辅助代码，以及脚本调用、Skill/reference 和本轮报告产物；测试结束后的既有代码修改另行处理。
- Bug/修复统计必须来自 run-log 的唯一 `issue_id`：发现 `failed` 后，由 AI 读取 `expected`、`actual`、操作回执、断言回执和证据，排除测试误判、环境阻塞及条件不可构造等情况；同一小批的 failed、blocked 或 test_inconclusive Case 必须各自生成自然语言 `reason`，再以 `FinalCaseReasonPatch[]` 一次调用 `TestHelper.UpdateFinalCaseReasons(runDir, patches)` 回写各自唯一 final record，禁止由固定模板代替。每个 `run_id + case_id` 只允许一条 `details.final_record=true`；禁用 Replace。开启自测自修时，初次验证、修复、重新编译和复测都在当前 `run_dir` 写非 final 过程事件，确认最终结果后才写唯一 final record。确认是产品问题时调用现有 `TestHelper.RecordAutoLocatedIssue(...)`（该入口内部写入 `FunctionTestLogWriter.AppendIssueRecord(...)`），写入 `issue_action=located`、事件状态为 `failed`，并保证 issue_id、自然语言 `reason`、问题描述、根因、目标和证据非空；在允许修改模式下，只有一轮完整的“修复→重新编译→当前 run_dir 验证”成功完成后，才写入一个 `event=fix` 轮次标记，并同时满足 `issue_action=fixed`、`fix_verified=true`、事件状态为 `passed`；编译、rerun、retry 记录归属于该轮但不重复计数。一次测试内的 `details.fix_round` 使用全局轮次编号 1、2、3，报告和 JSON 的 `fix_round_count` 只统计本次测试已完成的轮次。无法确认根因时只保留未归因失败及完整证据，不计入 Bug。两种模式都不得修改既有 `TestHelper`、`FunctionTestLogWriter` 等测试基础设施；允许修改模式下的业务修复必须在当前流程内记录 `action=fix`、原始证据、修改文件/行号、重新编译结果和复测结果，临时辅助代码在本轮结束后删除。报告必须把 issue_id、关联 Case、问题描述、根因和证据写成 AI 生成的自然语言记录；一个 failed Case 可以关联多个 issue_id。只有结构化 issue 事件参与统计，blocked/test_inconclusive、known-issues 条目或动作回执不能单独形成 Bug；报告和汇报 JSON 分别统计去重后的 `issue_action=located` 问题 ID及已验证修复的问题 ID，禁止用 failed 用例数、blocked 数量、修复轮次或脚本默认值替代。
- AI 生成 `reason` 的推荐结构（只约束信息完整性，不固定句式）：`失败/阻塞现象`、`实际执行的操作`、`预期结果`、`实际结果`、`证据`、`根因判断`。内容必须来自当前 Case 的日志；根因未确认时明确说明未确认，不得为了自然语言完整而猜测产品 Bug。
- 所有 run-log 必须通过现有 `CyStarRoad.Test.FunctionTestLogWriter` 的 DTO/写入入口生成；禁止临时拼接 JSON、手工转义、字符串补括号或用匿名对象承载 `details`。事件 ID 由 writer 生成，`duration_ms` 必须由同一组 `start_time/end_time` 计算。
- `runDir` 只能是逻辑运行名，例如 `hero-list-0033`，禁止传入 `Doc/AI开发文档/output/...` 或任何包含 `/`、`\\`、`..` 的路径。初始化必须调用 `FunctionTestLogWriter.InitializeRunDirectory(runDir)`；返回非 `ok:run_directory_initialized|` 时立即停止，禁止自行拼接路径创建目录。
- 每条最终 Case 记录必须调用 `FunctionTestLogWriter.AppendFinalCaseRecordFromDateTime(runDir, request, start, end)`；该统一入口内部固定执行 `start.ToString("o")`、`end.ToString("o")` 并传齐底层参数。编排层禁止直接调用 17 参数的 `AppendFinalCaseRecord(...)`，禁止自行拼接时间字符串或传入 `DateTimeOffset` 到底层接口。
- 每种验证模板在正式批量执行前必须各做一次无副作用编译烟测；模板有重复局部变量、委托签名或序列化错误时，先修测试编排/测试辅助代码，烟测通过后才能开始批量执行。
- 每批完成后立即校验 `case_id` 的 final record 覆盖和唯一性。发现重复时停止进入下一批，不重复执行已完成 case；只允许对明确缺失的 case 补测，补测后再次校验。
- 运行目录初始化时先创建并读取 `{run_dir}-known-issues.json`，再进行编译、PlayMode、登录、点击或其他交互；不得首次点击后才补建/读取。
- Unity/MCP 返回的原始错误必须原样保存在 run-log 的 DTO 字段（至少包含 `tool_name`、`tool_phase`、`raw_tool_response`，编译/运行时错误分别保留）；编排层不得用摘要替代原文，也不得在原始错误未处理时推导 passed。
- 每轮必须显式确定绝对 `input_case_path`、`run_dir`、`report_path` 和 `upload_json_path`，并把四者写入初始化/收口记录。报告转换调用必须传本轮明确的 report 输入和 JSON 输出路径，禁止只传 feature 目录、自动拾取历史报告或让 Cyou 自行猜路径。
- 新一轮默认使用同 feature 的最大序号加一；若 report、run-log 或 upload JSON 已存在，默认立即拒绝覆盖并停止。只有用户明确表达“复测/继续/修复/覆盖指定 run_dir”时，才允许复用目录，并显式传递 `--allow-overwrite`；没有该语义不得覆盖 `0001` 或其他历史报告。

## 花费控制

- 测试用例生成只在用户选择或输入需求文档时执行；已提供本地测试用例时不得重复生成。
- 离线 reference 只在测试前缺失、无效或被明确标记为静态不一致时生成/刷新；不得每条用例重复扫描，也不得把运行时路径或点击兜底写入离线 reference。
- 运行时 reference 在 Unity 测试过程中按已验证事实增量更新，测试返回后由 workflow 强制收口检查；reference 缺陷不改变 case verdict。
- JSON 转换只运行固定转换脚本，不重新阅读大报告、不复述报告内容。
- spend 步骤只读取环境变量快照并合并 JSON，不做额外分析。
- 上传步骤只上传 JSON，不解析 Markdown、不读取 run-log、不生成摘要。
- `check-cyoucode-spend` 放在上传前，是为了尽量覆盖测试和 JSON 转换阶段的消耗；上传本身的极小消耗不再二次统计，避免形成“统计后再上传”的循环。

## 职责边界

- `testcase-gen` 只负责本地生成测试用例。
- `testcase-mcp-complete` 只负责通过质量部线上 MCP 生成测试用例。
- `ui-quick-reference` 只负责离线静态 reference 的扫描和增量刷新；输出目录固定为该 Skill 的 `references/`。
- `unity-functiontest` 只负责 Unity 测试、实时证据、运行时 reference 增量维护、效果图对比子流程触发和自身 Skill 时间；单独调用时生成 Markdown 报告，由 workflow 调用时只返回 run-log，最终报告由 workflow 生成；不负责离线 reference 的正常生成。
- `ui-image-diff` 只负责基准图与实际截图的 UI 固定控件差异报告；由测试调用时使用本轮 `run_dir/ui-image-diff/`，不单独转换 JSON、不单独上传，不能把视觉差异直接当作 Bug。
- `functiontest-workflow` 负责离线 reference 前置、运行时 reference 收口和静态缺陷回刷编排。
- `functiontest-report-json` 只负责 Markdown 报告转 JSON，以及把 Cyou 用量快照合并进已生成 JSON。
- `check-cyoucode-spend` 只负责读取当前 Cyou 环境用量快照，不修改测试结果。
- `functiontest-json-upload` 只负责上传 JSON。
- 本 Skill 只负责按顺序调用，不得临时生成转换脚本或上传脚本。

## 失败处理

- 用户未明确测试用例来源且输入疑似需求文档时，必须先询问生成方式，不得默认替用户选择。
- `unity-functiontest` 启动前置阶段 A/B 未完成时，不得进入编译或 PlayMode；workflow 不得代替该 Skill 询问或默认选择。
- 如果用户在 `unity-functiontest` 的识图能力分支选择“停止”，workflow 必须闭合根 timing 并结束本次任务，不生成报告、不转换 JSON、不合并用量、不上传日志。
- 用户选择“不允许修改代码”后，任何发现的问题都只能写入报告，不得为了通过测试而修改代码；`unity-functiontest` 仍必须生成正式 Markdown 报告，报告中保留真实 `passed / failed / blocked / test_inconclusive`。
- 测试用例生成失败时，停止后续 Unity 测试、JSON 转换、spend 合并和上传。
- 离线 reference 前置扫描失败时，不停止 Unity 测试；必须在本轮 reference 审计记录中写明 `reference_kind=offline`、缺陷原因和后续回刷状态。
- `unity-functiontest` 明确完成或明确失败返回后，如果没有本轮新 `run_dir`、本轮 run-log 或本轮闭合的 Skill 时间，才视为 Unity 测试阶段未完成并停止后续报告渲染、JSON 转换、spend 合并和上传；不得在调用 `unity-functiontest` 前用“产物不存在”作为停止理由，也不得在测试仍处于执行阶段时用“产物未齐”提前停止。`unity-functiontest` 返回“只能单次工具调用逐步推进、无法一次性连续执行完整 MCP 流程、请选择最终处理方式”“完整用例集规模较大、逐条执行会非常耗时、需要确定接下来的执行策略”“请确认阶段性诊断”“截图路径读取异常，是否继续”等内容，或除两个启动前置阶段内的固定问题外在 Unity 测试阶段调用 `Ask user question` / `request_user_input` 时，不视为有效失败返回，必须继续调用或回到 `unity-functiontest` 执行阶段推进测试。`render_functiontest_report.py` 返回 `render precondition failed`、`run directory or log path not found` 等前置失败时，只能说明渲染被错误地放到了测试完成前，不能作为“本轮测试已执行但未完成”的交付结论，必须继续调用或回到 `unity-functiontest` 执行阶段创建本轮目录并写入本轮 run-log。只测不修模式下，存在 `failed` 用例本身不是停止理由，只要最终报告已生成就必须继续 JSON 转换、spend 合并和上传。
- 运行时 reference 收口失败时，不得重新执行整轮测试或伪造 reference；如果本轮有目标 UI 实测证据，必须继续执行 reference-only 收口；如果本轮未进入目标 UI，记录 `event=query_reference`、`status=test_inconclusive`、`details.runtime_reference_gap` 后继续报告和 JSON 转换，最终按全量用例状态门禁决定是否上传。
- Markdown 报告存在但 `passed=0、failed=0、blocked=0、test_inconclusive=0` 或 `用例总数=0` 时，必须视为无效报告，停止 JSON 转换和上传；非空报告仍可转换 JSON，但若 `blocked` 等于用例总数，或 `test_inconclusive` 等于用例总数，则保留本地报告/JSON并跳过上传；只有这两种全量状态以外的报告才继续调用 `functiontest-json-upload`。`test_inconclusive` 数量仍写入 `invalid_case_count`。
- JSON 转换失败时，不调用 spend 合并和上传。
- `check-cyoucode-spend` 环境变量为空时，对应字段写 `0` 或空字符串，不阻塞上传。
- 上传失败时，保留已生成 JSON 路径，并报告脚本返回的错误原文。
- 任一步失败都不能补造后续产物。

## Windows 中文路径安全规则

- 调用脚本时优先使用工作区相对路径，例如 `Doc/AI开发文档/output/{feature_id}/{run_dir}`，避免在 `cmd.exe` 中拼接中文绝对路径。
- 禁止用 `python -c "...中文路径..."`、一行内联脚本或未验证编码的 `cmd.exe` 命令写入 `{run_dir}-run-log.json`。
- 上一条只禁止错误的终端写入方式，不表示需要“直接写文件 MCP 工具”。`unity-functiontest` 的目录初始化和 run-log 写入必须在 `evaluate` 的 C# 代码内调用 `FunctionTestLogWriter.InitializeRunDirectory(runDir)` 及其写入入口；禁止在 evaluate 中对 `runDir` 直接调用 `Directory.CreateDirectory`，也禁止把 `runDir` 与 `Doc/AI开发文档/output` 再次拼接。
- 若脚本输出路径在终端显示为乱码，不得仅凭终端显示继续上传；必须以文件存在性、run-log 中 `case_id` 记录数和报告用例数校验结果。
- JSON 转换和上传前必须先确认报告非空；转换脚本会拒绝 `0` 用例报告，工作流应在该错误处停止。
- 所有 Unity `evaluate` 编排代码中的固定 C# 字符串统一使用 verbatim string（`@"..."`），尤其是 Windows/中文路径、JSON 和原始工具响应；不得使用普通字符串字面量承载反斜杠路径。verbatim string 内双引号写成 `""`，反斜杠不重复转义。
- 记录 Unity/MCP 原始错误时默认调用 `FunctionTestLogWriter.AppendToolErrorRecord` 的 6 参数重载，让 writer 自动补齐空的 `compileError` 和 `runtimeError`；只有确有对应错误文本时才使用 8 参数重载，禁止临时漏参调用。
