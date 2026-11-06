# Execution Log Schema

本文件是 `unity-functiontest` 的日志契约。执行测试前必须读取本文件；测试事件日志和最终 Markdown 报告都必须按本文件生成。

## 0. 输出目录命名

每次测试运行必须创建独立运行目录：

```text
Doc/AI开发文档/output/{feature_id}/{run_dir}/
```

`run_dir` 格式：

```text
{feature_id}-{sequence}
```

要求：

- `feature_id` 使用 kebab-case，例如 `hero-list`。
- `sequence` 使用 4 位递增数字，例如 `0001`、`0002`。
- 示例目录：`Doc/AI开发文档/output/hero-list/hero-list-0001/`。
- 同一轮测试的测试事件日志、功能测试报告、known-issues 均写入同一个 `{run_dir}` 目录。
- 不得直接写入 `Doc/AI开发文档/{feature_id}/` 或 `Doc/AI开发文档/{run_dir}/` 作为本轮正式产物目录。

## 1. 核心原则

本轮只保留测试事件日志；不创建、不读取、不渲染聊天窗口原文日志。

## 2. 测试事件日志

测试事件日志路径：

```text
Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-run-log.json
```

文件格式为 JSONL：一行一个测试事件对象。该文件用于测试报告、耗时、证据和状态审计，不用于还原完整聊天窗口原文。

必填字段：

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "event_id": "string",
  "case_id": "",
  "step_id": "",
  "event": "string",
  "target": "string",
  "status": "string",
  "start_time": "ISO-8601",
  "end_time": "ISO-8601",
  "duration_ms": 0,
  "evidence": [],
  "reason": "",
  "details": {}
}
```

兼容字段：

- 旧字段 `id` 等价于 `event_id` 或 `step_id`，按记录语义判定。
- 旧字段 `c` 等价于 `case_id`。
- 旧字段 `a` 等价于 `event`。
- 旧字段 `t` 等价于 `target`。
- 旧字段 `r` 等价于 `status`。
- 旧字段 `d` 等价于 `duration_ms`。
- 旧字段 `ts` 等价于 `start_time`。
- 旧字段 `te` 等价于 `end_time`。
- 旧字段 `ev` 等价于 `evidence`。
- 旧字段 `why` 等价于 `reason`。

## 4. 事件与状态枚举

`event` 只能使用以下值，新增值必须先更新本文件：

```text
setup
load_input
classify
compile
enter_playmode
login
navigate
discover
query_reference
query_autogen
query_logic
click
wait
verify
screenshot
query_logs
fix
rerun
report
blocked
```

`enter_playmode` 与 `stop_playmode` 仅为历史 run-log 兼容值；新运行不得写入这两类实际 PlayMode 启停记录。

`status` 只能使用以下值：

```text
passed
failed
blocked
test_inconclusive
```

四种状态含义固定如下：

- `passed`：前置条件满足，操作完成，并有独立于操作返回值的运行时结果证据证明结果符合预期；证据可以是业务状态、UI 语义状态或能明确对应预期的最终截图。同步操作可以在同一次 `evaluate` 中完成操作和结果读取，异步操作仍需操作后独立轮询。
- `failed`：测试条件已构建且可执行，但实际结果违反预期。
- `blocked`：环境、关键前置或失败用例造成的强关联依赖阻断，当前用例无法执行。
- `test_inconclusive`：流程可以运行，但测试账号、工具或服务环境无法合理构造目标异常/边界/并发条件，无法形成有效结论。

旧 run-log 中的 `environment_blocked`、`data_blocked`、`skipped`、`non_comparable` 由报告渲染器兼容读取，但新测试不得再写入这些状态；其中 `environment_blocked` 归一为 `blocked`，其余归一为 `test_inconclusive`。`test_inconclusive` 进入日志上报 JSON 的 `invalid_case_count`，不进入 `failure_case_count`；`total_case_count` 必须等于四种 verdict 数量之和。

所有新事件必须通过 `FunctionTestLogWriter.AppendEventRecord(...)`、`AppendClassifyRecord(...)`、`AppendIssueRecord(...)`、`AppendCaseAttemptRecordFromDateTime(...)` 或 `AppendFinalCaseRecordFromDateTime(...)` 写入。`event_id` 由 writer 生成唯一值；`start_time`、`end_time` 和 `duration_ms` 必须由同一 writer 计算，禁止调用方分别手写造成不一致。

问题统计必须使用唯一 `details.issue_id`：发现 `failed` 后，由 AI 读取 `expected`、`actual`、操作回执、断言回执和证据，排除测试误判、环境阻塞及条件不可构造等情况。所有非 passed Case 的自然语言 `reason` 必须在本批 Case 全部写完 final record 后，组装唯一 case_id 的 `FinalCaseReasonPatch[]`，一次调用 `TestHelper.UpdateFinalCaseReasons(runDir, patches)` 回写；不得逐条 evaluate 或逐条渲染。final record 是 append-once：同一 `run_id + case_id` 只能有一条 `details.final_record=true` 的 `event=verify`，禁止 Replace 或二次判定覆盖。开启自测自修时，初次验证、修复证据、重新编译和同一 `run_dir` 内的验证都写为非 final 过程事件；确认最终结果后才写唯一 final record，不能通过新建 `max+1` 运行目录规避该规则。确认是产品问题时调用 `TestHelper.RecordAutoLocatedIssue(...)`，由该入口写入 `FunctionTestLogWriter.AppendIssueRecord(...)`；`issue_action=located` 且事件状态为 `failed` 表示定位到问题，必须同时具备非空 `issue_id`、自然语言 `reason`、问题描述、`root_cause`、`target` 和 `evidence`。在允许修改模式下，只有完整的“修复→重新编译→同 run_dir 验证”通过后，才写入一个 `event=fix`，并满足 `issue_action=fixed`、`fix_verified=true`、事件状态为 `passed`；同一轮的 compile、rerun、retry 记录不重复计数，`details.fix_round` 使用本次测试全局轮次编号 1、2、3。只读不修模式禁止修改业务代码；两种模式都不得修改既有 `TestHelper`、`FunctionTestLogWriter` 等测试基础设施。无法确认根因时只保留未归因失败及完整证据，不写入可计数的 issue。一个可计数的问题事件必须是 `event=verify` 或 `event=fix`；`blocked`、`test_inconclusive`、`known-issues.json` 或单纯 Case 状态不能形成 Bug；同一个 failed Case 可以关联多个 issue_id。报告必须展示 AI 生成的问题描述、根因判断、关联 Case 和证据。`bug_count` 统计 `issue_action=located` 的去重问题 ID，`fixed_issue_count` 统计已验证修复的 `issue_action=fixed` 问题 ID，`fix_round_count` 统计本次测试已完成的修复轮数；不能用 failed 用例数或 blocked 数量替代。

### `query_logs` 事件约定

收口时在实际 `stop_scene_play` 前查询一次日志。每条写入 `event=query_logs` 的记录都必须有以下 string 字段，空值也写空字符串，禁止只塞原始 JSON：

```json
{
  "type": "Error",
  "message": "完整消息或空字符串",
  "stack_trace": "完整堆栈或空字符串"
}
```

最终 Case 的时间参数固定使用以下转换：

```csharp
string startText = start.ToString("o");
string endText = end.ToString("o");
FunctionTestLogWriter.AppendFinalCaseRecordFromDateTime(runDir, request, start, end);
```

不得把 `DateTimeOffset` 对象直接传入 `startTime`/`endTime`；这两个参数的 API 类型是 `string`。

### Unity/MCP 原始错误保留

Unity MCP 工具返回的编译、运行时、序列化、委托签名和调用异常，必须原样保存在 `details` 的以下字段中；摘要只能作为辅助字段，不能替代原文：

```json
{
  "tool_name": "mcp__mymcp__evaluate",
  "tool_phase": "verification_template_smoke_test",
  "raw_tool_response": "<完整原始返回>",
  "compile_error": "<完整编译错误；无则为空>",
  "runtime_error": "<完整运行时错误；无则为空>",
  "result_json": "<原始结构化结果；无则为空>"
}
```

编排层必须先保存原始返回，再解析/分类；原始错误未被处理时不得生成 `passed`。若错误来自测试编排或临时辅助代码，测试流程进行期间只修正本轮临时创建的代码，必须保留修正前原文并重新执行同一验证；既有 `TestHelper`、`FunctionTestLogWriter` 等测试代码的修改属于测试结束后的独立工作。

### `query_reference` 事件约定

涉及 UI reference 的检查、增量更新、缺口记录和测试后收口统一使用 `event=query_reference`，并在 `details` 中记录 reference 类型及生命周期阶段。该事件不等同于测试用例结果，不能单独据此判定用例通过或失败。

推荐字段：

```json
{
  "reference_kind": "offline",
  "feature_id": "hero-list",
  "gap": "missing",
  "phase": "preflight",
  "action": "generate_or_skip",
  "path": "../ui-quick-reference/references/hero-list.md",
  "source": "ui-quick-reference",
  "verified": false
}
```

字段约束：

- `reference_kind` 只能是 `offline` 或 `runtime`。
- `phase` 只能是 `preflight`、`runtime_update` 或 `postflight`。
- `gap` 可使用 `missing`、`invalid`、`stale`、`mismatch`、`incomplete`、`blocked_before_target`；没有缺口时省略该字段或置为空字符串。
- `action` 应明确记录 `skip`、`generate`、`update`、`refresh` 或 `close`。
- `path` 必须使用相对于当前 Skill 的 reference 路径：离线文档位于 `../ui-quick-reference/references/`，实时文档位于 `references/`。
- 当测试在目标 UI 前被编译、登录、PlayMode 或环境问题阻断时，实时 reference 不得补造；使用 `reference_kind=runtime`、`phase=postflight`、`gap=blocked_before_target` 记录原因。
- 当离线结构与运行时实际映射不一致时，使用 `reference_kind=offline`、`phase=postflight`、`gap=mismatch`，由 `functiontest-workflow` 在测试后调用 `ui-quick-reference` 刷新静态文档。

## 3. 时间与连续性

测试事件日志要求：

- `duration_ms` 必须等于 `end_time - start_time`，允许 1ms 以内的四舍五入误差。
- `start_time` 和 `end_time` 为必填字段，格式使用 ISO-8601 并带时区；同一运行内时间基准必须一致，不得混用本地时间与 UTC 后导致耗时不可复算。
- 每次正式测试运行的第一条记录必须是 `event=setup`，在编译前写入并提供开始时间。收口时必须在实际 `stop_scene_play` 前写完最后一次 `query_logs`；PlayMode 实际启停不写 run-log 开始/结束事件。缺少 setup、编译/进场/Case 证据或收口 query_logs 时，禁止生成正式 Markdown 报告。
- 生命周期记录只用于校验运行证据，不作为 Skill 或 JSON 的上报时长；Skill 耗时只读取独立 timing 文件。
- Skill 的开始时间、结束时间和有效耗时必须读取独立的 Skill timing JSON：没有 `parent_invocation_id` 的根 Skill 在环境变量完整时，按 `skill_end - skill_start - 根 Skill 时间范围内审批等待增量 - 根 Skill 时间范围内上下文压缩增量` 计算；环境变量缺失时使用完整本地 Skill 时间。由 workflow 调用的嵌套子 Skill 只保留自己的原始 `skill_end - skill_start`，不扣除会话环境变量，环境过滤只由父 Skill 最终计算一次。根 Skill 本地时间无效时，环境变量完整则使用会话总时间减两个过滤时间，否则为 0；嵌套子 Skill 本地时间无效时不得用会话时长冒充。run-log 中各事件的 `duration_ms` 只用于事件证据和超时扫描，不再累加为“有效执行耗时”。
- 相邻测试事件之间超过 2 秒的空白必须写明原因。
- 任意非视觉动画事件 `duration_ms > 8000` 时，`reason` 必须说明超限原因。
- 不得倒填、乱序或按报告阶段回忆补写过程。
- 每批执行结束立即校验 final record 的 `case_id` 集合和唯一性；只允许补测校验明确缺失的 case，禁止重复执行已有唯一 final record。

## 4. Markdown 日志报告

测试结束后，报告只从本轮 `{run_dir}-run-log.json` 的测试事件、证据、耗时和 verdict 渲染，不记录聊天窗口原文。

## 5. 禁止事项

- 禁止用聊天窗口输出替代测试事件日志。
- 禁止报告阶段回忆、拼凑或改写测试事件。
- 禁止在同一 `{run_dir}` 下附带聊天窗口原文日志或聊天原文报告。
