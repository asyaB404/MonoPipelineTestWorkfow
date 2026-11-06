# 隔离验证

<!-- 创建日期：2026-10-26；作者：Cyou；更新日期：2026-11-05；更新人：Codex；功能：维护回归入口与验证边界；参数：当前同包源码、临时假项目/包、内存目标或 loopback HTTP。历史验收流水原文保存在维护工程归档，不改写为新实测。 -->

仅在修改宿主、模板或交付契约时读取；正常业务测试不先跑维护回归。隔离 = 在自有临时文件与测试回执中验证工具行为，不启动或连接 Unity/真实 Player，不调用生成服务、登录、GM 或上传。

## 运行入口

从 Skill 根使用已有 Python 3.10+，完整回归：

```powershell
py -3 -X utf8 -I -B scripts/tests/run_tests.py
```

纯文档/链接整理可按影响选择原有测试，不能把定向通过写成全量通过：

```powershell
py -3 -X utf8 -I -B scripts/tests/run_tests.py scripts.tests.test_portable scripts.tests.test_workflow_preparation scripts.tests.test_compatibility
py -3 -X utf8 -I -B scripts/cli.py delivery-verify
```

输出 `ISOLATED_RESULT` 的 total/passed/failures/errors/skipped 取实际 runner；保存首次失败及最终输出，不能相加多次定向结果冒充完整回归。修改公共文件后应按显式维护批准刷新清单，再验证正式 CLI；不关闭自检、不在回归运行时继续编辑公共目录。只清理自己创建的临时目录，不清理旧运行证据。

## 覆盖分层

| 层级 | 主要回归与范围 |
| --- | --- |
| 输入和准备 | [test_workflow_preparation.py](../scripts/tests/test_workflow_preparation.py)：完整原字段/索引/摘要、来源顺序及未批准默认值 |
| 计划和提交 | [test_case_plan.py](../scripts/tests/test_case_plan.py)、[test_submission_repair.py](../scripts/tests/test_submission_repair.py)：静态预检、草稿发布、原文/引用、状态续行及真实错误分类 |
| 共享准备和完成条件 | [test_chain_context.py](../scripts/tests/test_chain_context.py)、[test_preflight_completion.py](../scripts/tests/test_preflight_completion.py)：独立链路、完整声明/基线、稳定完成与失败锁存、未知动作停止 |
| 会话及证据 | [tests](../scripts/tests/run_tests.py)：许可/身份、新帧、总预算、不重放、四状态、不可变来源、独占 writer/摘要链、关闭/计时/唯一报告 |
| 自包含和语法 | [test_portable.py](../scripts/tests/test_portable.py)、[test_compatibility.py](../scripts/tests/test_compatibility.py)：8 模块、无导入副作用、阻断原工程的真实迁移、链接/模板、Python 3.10 文法 |
| 生成C#与固定点击 | [test_builtin_visuals.py](../scripts/tests/test_builtin_visuals.py)：实际编译执行观测、返回投影和点击；验证原始视觉属性、委托/对象/预算拒绝、后代按钮、实例变化、交互状态和单次调用；仅自有控制台桩 |
| 返回隔离与简洁输出 | [test_submission_repair.py](../scripts/tests/test_submission_repair.py)、[test_session.py](../scripts/tests/test_session.py)：可信只读错误隔离、下一例继续、动作/错误身份仍冻结、旧包装审计及CLI显示不改journal/退出码 |
| 交付和接入 | [test_delivery.py](../scripts/tests/test_delivery.py)、[test_gameclient_adapter.py](../scripts/tests/test_gameclient_adapter.py)：原依赖迁移、清单/ZIP、预算、原子发布、批准/备份、外部改动保护和可选适配边界 |
| 包与长路径 | [test_package_empty_files.py](../scripts/tests/test_package_empty_files.py)、[test_windows_long_path_io.py](../scripts/tests/test_windows_long_path_io.py)：真实方法的空成员/长路径 I/O 与原拒绝边界 |
| Unity 负载 | [test_unity_payload.py](../scripts/tests/test_unity_payload.py)、[test_gate_execution.py](../scripts/tests/test_gate_execution.py)：公共 API/编译分支及从真实源提取的门禁控制台桩，不是 Unity 完整编译 |

夹具 [support.py](../scripts/tests/support.py) 使用不可运行静态字节/临时许可，能够产生编译失败、部分生效后断连、旧帧、错误扣费等反例，不是永远成功后端。正式 CLI 不开放测试身份/传输参数；替换仅限测试调用层。所需已有编译器/Unity 引用缺失时，可选编译用例按真实条件跳过，不自动安装；语法测试不等于在每个支持解释器上实际运行。

## 实机验收

离线全通过不证明 Unity/UPM 解析、真实包完整构建、服务/ACL、热更 metadata、账号前置、UI/动画、截图 renderframe、日志全轮覆盖或任意编码秘密。独立 Agent 的内存目标验证也不等于另一模型验收。

公司 CyouCode 的业务验收独立留证：使用新轮次、原完整用例、实际授权和前置，报告真实动作、全部预期证据、受限原因、人工介入及所有轮次总耗时。不能复用旧通过数或将文档字节减少直接等同于实机提速。
