# Skill 时间记录协议

本协议适用于直接调用或由 `functiontest-workflow` 编排调用的项目 Skill。真实时间必须由公共脚本写入，AI 不得手工估算、补造或从 Unity `run-log` 推算。

## 记录方式

1. Skill 开始执行时，立即调用 `../functiontest-report-json/scripts/skill_timing.py start`，记录 `skill_start_time`，并保存返回的 `invocation_id`。
2. Skill 的主要业务工作完成、失败、阻塞或用户中止时，必须调用同一脚本的 `end`，记录 `skill_end_time`，且一个 `invocation_id` 只能结束一次。
3. 开始和结束调用都必须使用同一个 timing JSON 文件；嵌套 Skill 通过 `parent_invocation_id` 建立父子关系。
4. 路径相对于当前 Skill 目录解析，不得拼接 `.agents/`，不得使用环境专属绝对路径。

## 时长口径

本协议区分根 Skill 和嵌套子 Skill。Cyou 的三个时间环境变量是当前会话的累计值，不能让同一会话中的父子 Skill 各自重复扣除。

根 Skill（没有 `parent_invocation_id`）的本地开始和结束时间有效时，先计算：

```text
原始时长 = skill_end_time - skill_start_time
有效时长 = 原始时长 - 根 Skill 时间范围内的审批等待增量 - 根 Skill 时间范围内的上下文压缩增量
```

三个 Cyou 时间环境变量完整可读时，根 Skill 使用开始、结束两次快照的变化量扣除；`CYOU_SESSION_DURATION_MS` 不会在本地起止时间有效时再次直接参与相减，只在根 Skill 本地时间无效时作为回退依据。环境变量不完整或不可读时，根 Skill 使用原始本地时间，并标记为未做环境时间扣除。

嵌套 Skill（存在 `parent_invocation_id`）只记录自己的原始 `skill_start_time → skill_end_time`，不扣除任何会话环境变量；环境变量快照只保留作审计。它的时间只用于报告明细，不单独生成或上传日志，环境过滤只在父 Skill 最终计算时执行一次。嵌套 Skill 没有有效起止时间时，不得使用整个会话时长冒充子 Skill 时长，应标记为不可用。

本地时间无效时，若三个 Cyou 时间环境变量完整存在，则回退到 `CYOU_SESSION_DURATION_MS - 审批等待时间 - 上下文压缩时间`；三个变量均不存在时直接使用 0。不能从报告文本、run-log 或人工估算补造时间。

## 报告和上传边界

- Workflow 的时间是包含子 Skill 的整体时间，不等于子 Skill 时间之和，也不能再减去子 Skill 时间。
- 报告中展示业务 Skill 的开始、结束和有效时长；`setup → stop_playmode` 只属于 Unity 内部生命周期，不作为 Skill 上报时长。
- Workflow 只允许最终上传一次；被 Workflow 调用的子 Skill 只记录时间，不单独生成或上传日志。
- JSON 转换和上传使用已经结束的业务 Skill 时间，不能为了包含转换/上传耗时而重新打开 Skill 计时。
- `functiontest-report-json`、`check-cyoucode-spend` 和 `functiontest-json-upload` 如需记录自身时间，只能作为交付阶段辅助记录，不得覆盖业务 Skill 的时间。

## 强制禁止

- 禁止把 `setup → stop_playmode` 当成任意 Skill 的时间。
- 禁止把所有子 Skill 的时长累加成 Workflow 时长。
- 禁止每个子 Skill 都减一次最终的审批/压缩累计值。
- 禁止因缺少 timing 文件而编造 `skill_start` 或 `skill_end`。
