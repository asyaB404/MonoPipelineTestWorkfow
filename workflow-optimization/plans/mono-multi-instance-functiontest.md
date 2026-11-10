# MonoPipeline 多开多测改造讨论方案

<!-- 创建时间：2026-11-10；创建人：Codex；功能简介：评估并规划当前 mono-pipeline-functiontest 的多 Player 并行执行能力；基础参数：并行实例数 N、原始完整用例、每实例目标目录/PID/账号状态、总输出根；本文为讨论稿，不代表代码已修改或实机验收完成。 -->

## 1. 讨论结论

当前 `mono-pipeline-functiontest` 支持单个 Player 上的多用例顺序执行，不提供多个 Player 的并行调度。改造目标是在不改父 `functiontest-workflow` 的前提下，为本 Skill 增加可选的多实例执行模式；原串行模式继续作为默认模式。

并行数使用明确参数配置，不在代码中固定为 2 或 4。运行上限由可用 Player 端口、已隔离的目标目录、机器负载和测试服务承载能力共同决定。端口池当前为 7900–7949，共 50 个候选端口；50 是当前宿主契约的端口范围，不代表任意机器都能稳定运行 50 个 Player。

实现可行性判断为高。当前 Unity Pipeline Player 的运行监听器会在 7900–7949 端口池内选择可用端口；但该仓库的 GameClient Mono 构建适配器要求显式配置 7900–7949 内的端口，宿主早期门禁和目标配置校验也不接受 `port=0`。多实例改造需要同步放宽构建配置与宿主门禁对配置值 0 的限制，并继续严格核验运行时描述符中的实际端口、PID 和端口所有者。

## 2. 当前约束

| 范围 | 当前实现 | 并行改造影响 |
| --- | --- | --- |
| 用例执行 | `run-suite` 在一个 Session 内逐例顺序执行，Session 固定绑定一个 Target | 增加外层并行调度；同一 Player 内仍按序执行 |
| Player 端口 | RuntimePipelineServer 在 7900–7949 范围内选择空闲监听端口；当前 Mono 构建适配器和宿主门禁要求显式配置 7900–7949 内的端口 | 允许测试包配置 `port=0`，宿主仍以运行时描述符中的实际端口建立目标 |
| 早期门禁 | `GlobalMonoPipelineTest.EarlyGate` 当前拒绝配置端口 0 | 同步修改门禁；实际端口仍必须在许可范围内 |
| 目标目录 | 描述符位于 `exe.parent/.unity-pipeline-runtime-port`，并绑定唯一 PID/端口/工作目录 | 每个 Player 使用独立的完整包工作目录，防止描述符互相覆盖 |
| 运行记录 | 每个 Session 新建独立 journal，并对单个 journal 使用独占 writer 锁 | 每个 lane 独立 journal；新增 coordinator 汇总多个 lane |
| 外部工作流 | 一个 Mono 技能执行对应一个父 Workflow 子计时与最终报告 | 多实例作为同一次 Mono 调用的内部 lane；父 Workflow 不增加或改写子计时记录 |

相关实现：[`SKILL.md`](../../.agents/skills/mono-pipeline-functiontest/SKILL.md:25)、[`session.py`](../../.agents/skills/mono-pipeline-functiontest/scripts/session.py:1902)、[`GlobalMonoPipelineTest.cs`](../../.agents/skills/mono-pipeline-functiontest/assets/unity/GlobalMonoPipelineTest.cs:47)、[`inputs.py`](../../.agents/skills/mono-pipeline-functiontest/scripts/inputs.py:290)、[`pipeline.py`](../../.agents/skills/mono-pipeline-functiontest/scripts/pipeline.py:362)、[`RuntimePipelineServer.cs`](../../Packages/com.unity.pipeline/Runtime/PlayerSupport/RuntimePipelineServer.cs:31)、[`GlobalMonoPipelineGameClientBuild.cs`](../../Assets/Editor/ClientEditor/GlobalMonoPipelineGameClientBuild.cs:56)。

## 3. 推荐结构

### 3.1 Coordinator 与 Lane

新增一个 Mono 内部 coordinator，接收原始完整用例、并行数 N、目标包和已授权的每实例账号/状态。Coordinator 保存本轮总运行身份、原始输入摘要、用例分配表及最终汇总；每个 lane 对应一个 Player、一个目标身份、一份独立 journal 和一个用例子集。

用例先按显式依赖和初始状态分组，再分配到 lane。一个 lane 内保持用例原有顺序；不依赖其他 lane 的用例可并行。每个 Player 分别执行登录后功能门禁和必要准备，不能把一个 Player 的门禁通过结论套给其他 Player。账号创建和账号池管理沿用现有授权流程，不作为本次宿主自动化范围。

### 3.2 Player 隔离与动态端口

从一份经过交付清单核验的 Mono 包生成 N 个本轮私有工作副本。每个 Player 从自己的副本目录启动，并设置相同且明确的工作目录；每份副本产生自己的 `.unity-pipeline-runtime-port` 描述符。构建配置使用 `port=0`，Player 从 RuntimePipelineServer 的 7900–7949 范围选择空闲端口。

目标准备必须对每个 lane 分别验证 EXE 路径、PID、进程创建时间、BuildGuid、工作目录、描述符 ACL、实际端口及端口监听所有者。端口忙、描述符缺失或身份交叉时，只阻断对应 lane，不猜测 PID/端口，也不把请求发给其他实例。

首次版本只启动本轮明确创建的副本进程；不接管、不关闭用户已有 Player。若用户授权本轮清理，只能结束本轮启动且 PID/创建时间仍匹配的实例。

### 3.3 用例分片与完整性

现有 Session 审计要求本轮原始用例全集完整收口，不能直接将全集复制给每个 lane 再把其他 lane 的用例记为缺失。Coordinator 应保留唯一原始全集，并为每个 lane 生成可追溯的用例投影，记录原始来源摘要、分配用例 ID 和子集摘要。

总审计校验以下条件：原始用例 ID 集合与所有 lane 最终 ID 的并集完全相等；任一原始用例只分配一次；每个 `passed` 都由所属 lane 的真实操作和独立比较产生；未开始或中断用例保留真实状态，不补造 final。

### 3.4 调度、故障和报告

Coordinator 使用有界 worker pool，worker 数等于用户指定的 N；每个 lane 最多有一个未决业务动作。lane 在执行前失败时，可将尚未派发的用例分配给其他健康 lane；动作已派发但结果未知时，禁止重放该用例，冻结对应 lane 并保留不确定结果。其他 lane 继续或停止由整轮停止条件决定。

每个 lane 独立完成附加、功能门禁、业务步骤、关闭和审计。Coordinator 汇总所有 lane 的不可变证据引用，生成一份保留原用例全集和原编号的正式 Mono 报告。父 Workflow 仍只看到原有的一个 Mono 子技能调用和一份最终报告。lane 身份、PID、实际端口、工作目录、账号别名及失败原因进入本轮审计摘要；不记录账号密码或认证令牌。

## 4. 改造阶段

1. 宿主目标模型：增加 lane/target 集合和动态端口门禁；配置 `port=0` 时仍要求描述符报告合法实际端口，且该端口只能由目标 PID 持有。
2. 包副本与进程启动：新增本轮隔离工作目录、完整包复制、启动就绪检查和本轮进程身份登记；保留现有单 Player 默认路径。
3. 用例分配与审计：新增用例依赖分组、lane 子集来源绑定、跨 lane 去重及全集闭合验证。
4. 报告汇总：扩展 coordinator 报告，使多 lane 结果仍形成单一完整报告，并保留每个 lane 的证据与计时来源。
5. 回归和实机阶梯验证：先完成离线伪目标与故障隔离测试，再用实际 Mono Player 从 2、3、4 个实例逐级增加，继续测至机器或测试服务不再满足稳定性指标；据测量结果确定建议并发值，不设人为的 4 个上限。

## 5. 验收条件

- 串行模式默认行为、原计划格式、原四态判定和现有报告消费接口保持兼容。
- N 个 lane 均有互异工作目录、PID、运行描述符、实际端口和 journal；所有请求均由对应 PID 的端口响应。
- 原始全集中的每个用例在最终报告中出现且仅出现一次；跨 lane 失败或中断不会改写其他 lane 的结果。
- 动作回执未知、Player 崩溃、端口占用、描述符串线、账号门禁失败和单 lane 输出损坏均有单独验证用例。未知动作不重试，缺失用例不生成假 final。
- 实机验证记录 N、CPU、内存、GPU、Player 帧推进、桥接响应耗时、超时/断连数、服务端错误及报告覆盖率；最大稳定并发数按连续实测确定。
- 修改技能公共文件后刷新 `delivery-manifest.json`，执行隔离回归，并完成至少一次真实双 Player Mono 执行与报告审计。离线回归不替代实机验收。

## 6. 风险与把握

| 风险 | 等级 | 缓解方式 |
| --- | --- | --- |
| 同目录描述符冲突或 PID/端口串线 | 高 | 每 lane 使用独立包目录；启动后按 PID、创建时间、BuildGuid、端口所有者四重核验 |
| `port=0` 与宿主配置校验不一致 | 中 | 同步 C# 早期门禁、Python 输入校验、构建接线及测试常量；仍只接受范围内实际端口 |
| lane 分片导致用例遗漏、重复或跨 lane 状态假设 | 高 | Coordinator 绑定全集摘要并做 ID 并集/唯一性审计；只并行化独立用例组 |
| 并发负载使帧推进、桥接或服务端响应变慢 | 中、需实测 | 并发数可配置并分级压测；监控每实例与全局资源，以稳定性指标确定实际推荐值 |
| 一个 lane 的未知动作污染整批状态 | 中 | lane 独立冻结和记录；只重分配从未派发的用例，不重放未知动作 |
| 现有报告/父 Workflow 回归 | 中 | 保持父调用数量为一个、结果汇总为一份；串行路径继续跑回归 |

当前结构下，多实例执行的代码改造可行性把握高，预计约 85%–90%。这表示可以实现隔离调度和审计汇总，不代表未经实测的并发稳定性成功率。实际可稳定运行的 N 需要使用当前 Mono 包测量；不从双实例结果外推机器上限。账号状态按每 lane 独立准备后，账号互踢和共享业务状态不作为架构阻断项。

## 7. 兼容与范围

本方案只新增 `mono-pipeline-functiontest` 的可选多实例路径；串行默认路径、既有 journal 和历史报告不重写。实现前后都不得把并行产生的速度变化解释为用例行为变化；报告中保留 lane 数及真实计时。

本方案不修改 `functiontest-workflow` 父文件，不自动注册账号、发 GM、登录未授权账号或上传结果，不扩展到 IL2CPP/AOT。讨论稿确认后，实施时同步更新本 Skill、宿主契约、交付清单和对应需求追踪记录。当前文档树未发现 Mono 多实例的独立需求规格；本方案以现有 Skill 契约为基线，后续实施需求需从本文验收条件建立追踪。

## 8. 旧入口清理

已删除停用的 `pc-batch-test` 技能入口、`pc-batch-test-portable` 便携别名及 `pc-test-handoff` 交接入口。它们不属于当前 Mono 执行链，也不作为多实例改造依赖。

在原 GameClient 工作区保留 `.agents/skills/pc-batch-test/references/active-workflow.md`：当时 `unity-functiontest` 的 PC 后端说明仍引用该共享流程文件；该清理未扩大到 Unity FunctionTest 的旧 PC 后端。本仓库不包含这份旧 PC 技能文件。Mono 集成测试中用于拒绝旧 `pc-batch-test` 父计时的校验保留，避免旧父记录被误接入。
