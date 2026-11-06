---
name: check-cyoucode-spend
description: 读取并报告当前 Cyou 运行环境的 session/task/turn/tool_call/litellm_call 标识符、LiteLLM API key 别名，以及会话累计花费、Token、持续时间、数据库确认状态和待确认模型调用数。用于用户查询当前 session ID、各类追踪 ID、API key 别名、当前或本轮已消耗用量、会话花费、Token、耗时，或询问用量是否已由 LiteLLM 确认时。
---

# Check CyouCode Spend

## Skill 时间记录（强制）

遵守 `../functiontest-report-json/references/skill-timing-contract.md`。如果调用方提供 timing 文件和父级 `invocation_id`，在读取快照前用公共脚本记录本 Skill 的 `skill_start --report-hidden`，脚本输出后记录对应的 `skill_end`。该辅助 Skill 的时间只作为交付阶段记录，不得覆盖业务 Skill 的测试时长；由 Workflow 调用时不得另建独立业务计时。

## 前提

使用支持会话用量环境变量和 Cyou API 查询的 Cyou Code。基础能力从 0.36.3 起提供；若状态字段为空，当前插件可能尚未包含请求级用量刷新能力。

## 执行

进入本 Skill 目录后，通过 `execute_command` 运行：

```cmd
python scripts\main.py
```

直接使用脚本输出回答用户。不要自行查询 LiteLLM/PostgreSQL，不要添加 sleep、轮询或等待；客户端会在后台完成数据库校准。

## 输出字段

- `session_id`：会话 ID；同一对话窗口及其子任务共享。
- `task_id`：当前任务 ID。
- `turn_id`：当前用户消息对应的对话轮次 ID。
- `tool_call_id`：本次 Skill/命令工具调用 ID。
- `litellm_call_id`：触发本次工具调用的模型请求 ID。
- `api_key_alias`：当前 Cyou API key 在 `LiteLLM_VerificationToken.key_alias` 中配置的别名。
- `team_alias`：当前 `CYOU_TEAM_ALIAS` 环境变量中的团队/项目组名称，转 JSON 时作为 `project_group`。
- `session_spend_usd`：当前会话累计花费，单位 USD。
- `session_total_tokens`：当前会话累计 Token 数。
- `session_duration_ms`：会话内最早与最新模型请求开始时间之差，单位毫秒；不是所有请求耗时之和。
- `session_approval_duration_ms`：会话内等待用户权限审批的累计耗时，单位毫秒（对应 `CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS`）。
- `session_condense_duration_ms`：会话内上下文压缩（condense）的累计耗时，单位毫秒（对应 `CYOU_SESSION_CONDENSE_DURATION_MS`）。
- `session_usage_status`：`provisional` 或 `confirmed`。
- `session_pending_calls`：尚待 LiteLLM 数据库确认的模型调用数。

## 报告规则

- `provisional` 表示结果已包含刚完成模型请求的本地增量，可在 `completion_result` 或 `followup` 前立即报告；同时说明该值可能被数据库结果小幅校准。
- `confirmed` 表示当前没有待确认调用，结果已由 LiteLLM 数据库快照校准。
- API key 未配置别名时，`api_key_alias` 为 `None`；照实报告未配置，不要输出或推断明文 API key。
- 状态或用量字段为 `None` 时，照实报告尚无可用快照，不要把它解释为零，也不要主动等待重试。
- 脚本只读环境变量，不修改任何状态。
- 本 Skill 只负责读取并返回会话快照，不负责替其他 Skill 计算业务执行时长。
