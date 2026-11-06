---
name: functiontest-json-upload
description: 将已生成的 FunctionTest 上传 JSON 调用 Skill 自带 bat/ps1 上传到日志中心。仅负责上传 JSON，不执行 Unity 测试、不解析 Markdown 报告、不生成 JSON。适用于“上传 functiontest JSON”“json 调用 bat 上报”“把 functiontest-upload.json 上传日志中心”等需求。
---

# FunctionTest JSON 上传

本 Skill 是职责 D：只接收已经处理好的 JSON，并调用固定脚本上传到日志中心。

本 Skill 中的 `scripts/...` 均相对于本文件所在目录解析，不依赖项目根目录下存在技能目录。

## Skill 时间记录（强制）

遵守 `../functiontest-report-json/references/skill-timing-contract.md`。开始校验和上传前，调用 `../functiontest-report-json/scripts/skill_timing.py start --report-hidden`；上传命令返回后立即调用 `end`。timing 记录仅用于记录本 Skill 自身的交付时间，不得修改已生成 JSON 的业务 Skill 时长，也不得因为上传过程再触发第二次上传。由 Workflow 调用时复用 Workflow 的 timing 文件并记录为隐藏的交付子阶段。

## 输入

只接受一个输入：

```text
functiontest-upload.json 路径
```

正式路径必须是：

```text
Doc\AI开发文档\output\{feature_id}\{run_dir}\{run_dir}-functiontest-upload.json
```

不得从 input 目录、feature 根目录或历史 output 目录猜测 JSON；先由调用方确认当前轮次的明确 JSON，再进入该 JSON 所在的 `run_dir` 执行固定包装器。

该 JSON 顶层只能包含两个字段，不得携带 Cyou 会话快照、run-log、visible-chat-log 或其他本地调试字段：

```json
{
  "tool_stats_payload": {},
  "user_stats_payload": {}
}
```

`cyou_runtime_snapshot` 不属于上报 schema；Cyou 的 `api_key_alias`、花费和 Token 只能合并到 YAML 定义的 `custom_metrics` 字段中。

普通测试用例 JSON、Markdown 报告、运行目录都不是本 Skill 的输入。

单独调用 testcase-gen、testcase-mcp-complete 或 ui-quick-reference 生成的最小上报 JSON 也是合法输入。此类 JSON 必须包含 user_stats_payload.items[0].custom_metrics.operation_type，且只能是主动测试工作流、质量部生成用例、本地生成用例、UI快速分析、独立Unity功能测试之一；前三类单独 Skill 的测试统计为 0，只保留 Token 和消耗数据。独立 Unity 功能测试必须保留真实测试统计，其中无效用例为 `test_inconclusive` 数量，总用例数必须等于成功、失败、阻塞和无效用例之和。

## 执行

进入当前 JSON 所在的 `run_dir` 后，依次使用测试包内固定生成器和 bat：

```text
python <本 Skill 的 scripts/prepare_upload_wrapper.py> --run-dir .
<本 Skill 的 scripts/report_functiontest.bat>
```

生成器只接受当前目录中唯一的 `*-functiontest-upload.json`，并生成带 UTF-8 BOM 的 `functiontest-upload-wrapper.ps1`。bat 不接收 JSON 路径参数，只调用该 ASCII 文件名的 wrapper；wrapper 再在本目录解析 JSON 的真实路径并调用固定 ps1。因此命令行不传中文路径，也不依赖 PowerShell 控制台代码页。上传端点只从同一测试包的 `scripts/upload-endpoint.json` 读取，不读取环境变量。

## 规则

1. 上传前必须确认 JSON 文件存在。
2. 上传前必须确认 JSON 顶层包含 `tool_stats_payload` 和 `user_stats_payload`。
3. 不得解析 Markdown 报告。
4. 不得修改 JSON 字段。
5. 不得读取 run-log 或 visible-chat-log。
6. 不得手写或临时修改上传脚本；只允许调用本 Skill 固定的 Python 生成器生成 wrapper。
7. 上传失败时保留原 JSON，并把脚本返回的错误原文反馈给用户。
8. 上传器读取 JSON 中的用例统计作为最后一道门禁：`total_case_count>0` 且 `block_case_count` 等于总数，或 `invalid_case_count`（对应 `test_inconclusive`）等于总数时，拒绝发送请求并返回“全部用例阻塞/未定论，已保留本地报告和 JSON”的原因；该拒绝不删除或修改本地文件。该规则不适用于 `total_case_count=0` 的 operation-only JSON。

## 本地演练

如果需要本地演练，直接用固定 ps1 的显式参数：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/report_functiontest.ps1 -JsonPath <当前JSON路径> -DryRun
```
