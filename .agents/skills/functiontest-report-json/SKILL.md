---
name: functiontest-report-json
description: 将 Unity FunctionTest 的 Markdown 测试报告或运行目录转换为日志上报统计平台 JSON；也可为单独生成用例或 UI 快速分析生成仅含用量的最小 JSON，并为单独 Unity 功能测试保留真实统计生成 JSON，再把当前 Cyou 会话用量快照合并进已生成的 functiontest-upload.json。仅负责 JSON 生成和字段合并，不执行 Unity 测试、不调用 bat 上传。
---

# FunctionTest 报告转 JSON

本 Skill 是职责 C：只把 `unity-functiontest` 已生成的 Markdown 报告转换为日志中心要求的 JSON 结构；或在工作流上传前，把 Cyou 会话用量快照合并进已生成 JSON。

本 Skill 中的 `scripts/...` 和 `UnityFunctionTest_report_schema.yaml` 均相对于本文件所在目录解析，不依赖项目根目录下存在技能目录。

## Skill 时间记录（强制）

本 Skill 自身也遵守统一计时协议，协议文件为 `references/skill-timing-contract.md`。本 Skill 只读取调用方已经写入的业务 Skill 时间；不得用 `setup → stop_playmode` 或 run-log 的步骤时长重新推算业务 Skill 时长。

直接单独调用本 Skill 时，在开始解析、生成或合并 JSON 前，用本目录的 `scripts/skill_timing.py start --report-hidden` 为本 Skill 写入一条 `skill_start`；JSON 校验或合并完成后立即写入对应的 `skill_end`。由 `functiontest-workflow` 调用时，复用 Workflow 的 timing 文件并以 `parent_invocation_id` 记录为隐藏的交付子阶段，不得新建业务计时、覆盖 Workflow/Unity 的时长或再次上传。

不做以下事情：

- 不执行 Unity 功能测试。
- 不调用 `report_functiontest.bat` 上传。
- 不把普通测试用例 JSON 当作上报 JSON。
- 不临时生成新的 Python 报告解析脚本。
- 不自动扫描历史 run_dir、猜测旧报告或覆盖已有输出。

## 输入

支持三类输入：

- Markdown 报告路径：文件名以 `-unity-functiontest-report.md` 结尾。
- 运行目录路径：目录内存在 `{run_dir}-unity-functiontest-report.md`。
- 已生成的 functiontest 上传 JSON：必须包含 `tool_stats_payload` 和 `user_stats_payload` 两个顶层字段。

支持业务信息：

```text
报告路径
```

当前只要求输入报告路径；用户名优先由 `CYOU_API_KEY_ALIAS` 写入 `tester_account`，项目组优先由 `CYOU_TEAM_ALIAS` 写入 `project_group`；对应环境变量缺失或为空时读取 `../functiontest-workflow/config.json` 中的同名字段，配置也不可用时写 `无`。该配置仅在非 Cyou 环境，或 Cyou 环境存在但无法读取对应环境变量时生效。

工作流调用时必须同时传入本轮明确的报告输入路径和 JSON 输出路径：

```powershell
python scripts/convert_functiontest_report.py `
  --input "Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-unity-functiontest-report.md" `
  --output "Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-functiontest-upload.json" `
  --timing-file "Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-skill-timing.json" `
  --skill-name "functiontest-workflow"
```

脚本必须解析并打印/报错中保留绝对 input report、run directory 和 output JSON 路径。默认输出路径只为兼容旧调用保留；当目标已经存在时，默认拒绝覆盖。

## 输出

默认输出到报告同目录：

```text
{run_dir}-functiontest-upload.json
```

报告目录必须是 `Doc/AI开发文档/output/{feature_id}/{run_dir}/`；input 目录和旧的 `Doc/AI开发文档/{run_dir}/` 均不允许作为报告或 JSON 输出目录。

JSON 顶层结构固定为：

```json
{
  "tool_stats_payload": {},
  "user_stats_payload": {}
}
```

顶层字段必须严格等于 `tool_stats_payload` 和 `user_stats_payload`。`cyou_runtime_snapshot`、session/task/turn/call ID 以及其他运行时快照不属于上报 JSON；Cyou 快照只允许按下方映射合并到 YAML 定义的指标字段。

字段必须和同级文件一致：

```text
UnityFunctionTest_report_schema.yaml
```

## 固定转换规则

正常 Markdown 报告转换的操作类型固定为“主动测试工作流”；单独执行 unity-functiontest 时固定使用“独立Unity功能测试”。脚本支持显式传入同一组固定中文枚举，禁止写入英文 Skill 名称或其他自定义值。

1. 只从 Markdown 报告明确写出的汇总结果读取 `passed / failed / blocked / test_inconclusive` 四种状态，以及 `定位Bug数`、`修复问题数`。
2. 上报时长优先读取指定 timing JSON 中当前业务根 Skill 已闭合的 `skill_start_time` 和 `skill_end_time`，使用其中的 `skill_active_duration_ms`。根 Skill 的本地时间有效且三个 Cyou 时间环境变量完整时，只扣除根 Skill 时间范围内审批等待和上下文压缩的变化量；`CYOU_SESSION_DURATION_MS` 不会再次直接参与相减。若不在 Cyou 环境、无法读取完整环境变量，只要根 Skill 时间有效，仍上传完整本地时长，并在报告中提示未进行环境时间扣除。Workflow 的嵌套子 Skill 不作为上报业务 Skill，其 `skill_active_duration_ms` 只保留原始子 Skill 起止时间，环境过滤由父 Skill 统一执行。
3. timing JSON 缺失、根 Skill 记录缺失或根 Skill 本地时间无效时，若三个 Cyou 时间环境变量完整存在，则回退到 `CYOU_SESSION_DURATION_MS - CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS - CYOU_SESSION_CONDENSE_DURATION_MS`；三个变量均不可用时直接写 0，不再读取报告文本中的“总耗时”。嵌套子 Skill 本地时间无效时不得使用整个会话时长冒充子 Skill 时长。
4. 不得从 run-log 首尾时间或所有事件 `duration_ms` 累加值倒推 Skill 上报时长；`setup → stop_playmode` 只属于 Unity 内部生命周期。
4. 不得补造报告里没有的业务内容；缺少 `定位Bug数` 或 `修复问题数` 时必须拒绝转换，不能默认写入 0。
5. `tester_account` 和 `project_group` 均按“对应环境变量优先、`../functiontest-workflow/config.json` 兜底、最终使用 `无`”读取，不得从报告路径、报告内容或目录名推断。
6. 用例数量写入 `success_case_count`、`failure_case_count`、`block_case_count`、`invalid_case_count`、`total_case_count`；其中 `invalid_case_count` 等于 `test_inconclusive` 数量，`total_case_count` 等于四项之和。`test_inconclusive` 不计入 `failure_case_count`。
7. `fix_round_count` 同时写入 `tool_metrics` 和 `user_metrics`，位置都紧跟 `fixed_issue_count`；数值为本次测试中已完成的“修复→重新编译→重新运行/复测”轮数。只有 `issue_action=fixed`、`fix_verified=true` 且复测状态为 `passed` 的完整记录才计 1 轮。修复相关的编译、rerun、retry 记录不重复增加轮数。非修复模式或未发生修复时两边都写 `0`。
8. 报告成功/失败次数写入 `success_count`、`failure_count`，不得和用例数量混用。只要生成有效 Markdown 报告并通过非空校验，即 `success_count=1`、`failure_count=0`；不考虑四种用例 verdict 数量。`failed` 用例只计入 `failure_case_count`，`blocked` 用例只计入 `block_case_count`，`test_inconclusive` 只计入 `invalid_case_count`。
9. 功能数量写入 `feature_count`，口径为每上传一份有效 FunctionTest 报告计 1 次，因此固定等于 `success_count + failure_count`。
10. `定位Bug数` 必须由 run-log 中 `issue_action=located` 的去重 `issue_id` 记录生成，`修复问题数` 必须由已验证通过的 `issue_action=fixed` 记录生成并写入 Markdown；转换脚本只读取报告中的这两个真实统计，不接受手工命令行覆盖。
11. 生成后必须重新解析 JSON，确认格式有效。
12. 生成或合并后必须校验顶层字段和两组 `custom_metrics` 字段与 `UnityFunctionTest_report_schema.yaml` 完全一致；发现未定义字段时不得继续上传。
13. 生成模式发现 output JSON 已存在时必须失败并停止后续流程；只有用户明确要求“复测/继续/修复/覆盖指定 run_dir”时，才允许给转换脚本传 `--allow-overwrite`。不能因为 Cyou 未读取已有输出报告，就把新结果写回 `0001` 或其他历史文件。
14. 输入报告和输出 JSON 必须属于同一轮且路径不同；禁止把 feature 目录、历史报告或模糊目录作为 Cyou 输入。`--merge-cyou-spend` 是唯一允许原位更新已存在 upload JSON 的模式，且只能更新命令行明确给出的那个 JSON。执行本 Skill 的 AI 必须在本 Skill 内优先读取当前 AI 对话上下文中的实际模型名，并通过 `--ai-model` 传入；该要求同样适用于单独调用本 Skill，不得依赖 `functiontest-workflow`。不得硬编码模型名。只有当前上下文确实无法提供模型名时，才省略该参数并由脚本读取环境变量；所有来源均无法获取时写入 `暂无数据`。
15. 非空报告仍可生成并校验 JSON；但当 `blocked` 数量等于 `total_case_count`，或 `test_inconclusive` 数量等于 `total_case_count` 时，工作流必须保留本地报告和 JSON、记录不上报原因并跳过 `functiontest-json-upload`。该规则不适用于 `total_case_count=0` 的 operation-only JSON；全 `passed`、全 `failed` 及其他混合状态报告仍正常进入上传流程。

## 单独 Skill 的最小上报 JSON

testcase-gen、testcase-mcp-complete 和 ui-quick-reference 单独调用完成后，必须先调用 check-cyoucode-spend，再调用本 Skill 生成最小 JSON；不需要 Markdown 报告。

```powershell
python scripts/convert_functiontest_report.py --operation-only --operation-type "本地生成用例" --output "Doc/AI开发文档/output/{feature_id}/{feature_id}-operation-{seq4}/{feature_id}-operation-{seq4}-functiontest-upload.json" --timing-file "Doc/AI开发文档/output/{feature_id}/{feature_id}-operation-{seq4}/{feature_id}-operation-{seq4}-skill-timing.json" --skill-name "testcase-gen"
```

固定中文操作类型映射：

```text
testcase-gen             -> 本地生成用例
testcase-mcp-complete    -> 质量部生成用例
ui-quick-reference       -> UI快速分析
functiontest-workflow    -> 主动测试工作流
unity-functiontest       -> 独立Unity功能测试
```

前三类单独 Skill 的 operation-only 模式不读取 Markdown 报告，success_case_count、failure_case_count、block_case_count、invalid_case_count、total_case_count、bug_count、fixed_issue_count、fix_round_count、success_count、failure_count、feature_count 以及报告成功/失败统计全部为 0；total_cost_usd、total_tokens 从当前 Cyou 用量快照写入。时长优先读取对应根 Skill timing JSON 中已闭合的有效时长；单独调用时该 Skill 没有父级，按根 Skill 规则扣除环境过滤时间；timing 记录不可用时，按“三个 Cyou 时间环境变量完整存在则使用会话总时间减两个过滤时间，否则为 0”的规则处理。Workflow 内部调用的子 Skill 不进入 operation-only，也不单独上报。stats.usage_count 只表示该 Skill 被调用一次，不表示测试通过。独立 Unity 功能测试不适用 operation-only 模式。

JSON 的 user_stats_payload.items[0].custom_metrics.operation_type 必须使用上述固定中文枚举；生成后仍必须交给 functiontest-json-upload 上传。

单独执行 unity-functiontest 时不使用 operation-only 模式。必须等待本轮 Markdown 报告生成后，使用报告转换模式传入 operation_type=“独立Unity功能测试”，保留真实 passed、failed、blocked 和 test_inconclusive 统计口径，再合并用量并交由上传器按全量用例状态门禁决定是否上传。

## Cyou 用量快照

工作流上传前可调用本脚本的轻量合并模式：

```powershell
python scripts/convert_functiontest_report.py --merge-cyou-spend --ai-model "{当前AI上下文模型}" --timing-file "Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-skill-timing.json" "Doc/AI开发文档/output/{feature_id}/{run_dir}/{run_dir}-functiontest-upload.json"

调用本 Skill 时，`{当前AI上下文模型}` 必须由执行本 Skill 的 AI 直接从当前上下文取得；不得要求上游 workflow 代为获取。若当前上下文不可见或没有模型值，才省略 `--ai-model`。
```

该模式只读取当前环境变量并回写已生成 JSON，不重新解析 Markdown 报告：

```text
CYOU_SESSION_ID
CYOU_TASK_ID
CYOU_TURN_ID
CYOU_LITELLM_CALL_ID
CYOU_API_KEY_ALIAS
CYOU_TEAM_ALIAS
CYOU_SESSION_SPEND_USD
CYOU_SESSION_TOTAL_TOKENS
CYOU_SESSION_DURATION_MS
CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS
CYOU_SESSION_CONDENSE_DURATION_MS
```

合并映射固定为：`tester_account <- CYOU_API_KEY_ALIAS`，缺失时读取 `../functiontest-workflow/config.json` 的 `tester_account`；`project_group <- CYOU_TEAM_ALIAS`，缺失时读取同一配置的 `project_group`；`total_cost_usd <- CYOU_SESSION_SPEND_USD`，`total_tokens <- CYOU_SESSION_TOTAL_TOKENS`。该配置只作为非 Cyou 环境或环境变量无法读取时的兜底。

**时长映射（Skill 记录方式）**：优先使用当前业务根 Skill timing JSON 中的 `skill_active_duration_ms`。根 Skill 环境变量完整时，该值由 `skill_end - skill_start` 扣除根 Skill 时间范围内审批等待和上下文压缩的变化量得到；根 Skill 环境变量缺失时，它就是完整的本地 Skill 时间。Workflow 的嵌套子 Skill 的 `skill_active_duration_ms` 只表示原始子 Skill 起止时间，不扣除会话环境变量，也不单独上报。最终根 Skill 值写入 `stats.duration_ms`、`tool_metrics.total_duration_seconds`、`user_metrics.test_duration_seconds`（秒 = ms/1000）。根 Skill 时间无效时，三个 Cyou 时间环境变量完整存在则使用会话总时间减两个过滤时间，否则写 0；嵌套子 Skill 时间无效时保持不可用。`setup → stop_playmode` 和 run-log 中所有步骤 `duration_ms` 不参与上报时长计算。

`ai_model` 的最高优先级必须由调用方直接传入当前 AI 上下文模型值（例如显式 `--ai-model`）；脚本本身无法直接读取模型上下文。未传入时再读取运行环境变量 `CYOU_AI_MODEL`、`CYOU_MODEL`、`AI_MODEL`、`MODEL_NAME`；全部无法获取时写入文本 `暂无数据`，不得硬编码具体模型名。

## 使用脚本

```powershell
python scripts/convert_functiontest_report.py --input "Doc/AI开发文档/output/hero-list/hero-list-0001/hero-list-0001-unity-functiontest-report.md" --output "Doc/AI开发文档/output/hero-list/hero-list-0001/hero-list-0001-functiontest-upload.json"
```

脚本只打印生成或校验通过的 JSON 路径；输出已存在且未显式 `--allow-overwrite` 时必须以清晰错误退出。上传必须交给 `functiontest-json-upload`。
