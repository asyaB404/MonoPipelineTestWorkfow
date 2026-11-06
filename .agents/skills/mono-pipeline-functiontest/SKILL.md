---
name: mono-pipeline-functiontest
description: 为 functiontest-workflow 提供已构建 Windows Mono Development PC 包执行，也支持直接调用。复用项目内现有来源/用例及公共子技能，准备单一 Player，批量执行、留证并生成唯一报告；父 Workflow 不修改。Python 3.10+ 标准库宿主，不构建、不重启、不调用 Unity MCP，不自动登录、发 GM 或上传。
---

# Mono Pipeline 功能测试

<!-- 创建日期：2026-10-26；作者：Cyou；更新日期：2026-11-06；更新人：Codex；功能：父流程协作与直接调用的 PC 包测试入口；参数：完整原用例、包目标、授权、输出根及已有父上下文。本次30秒启动预算和固定登录精简归属Codex，历史实现与建议归属CyouCode；父Workflow保持原样。 -->

宿主 = 包外 Python 执行工具；Player = 已构建的 Unity 游戏进程；journal = 本轮不可变证据记录。仅支持 Mono Development，不证明 IL2CPP、AOT、裁剪或热更兼容。

## 用户输入与 Agent 产物

用户提供原始用例或需求材料、包目标和必要许可。Agent 保留原编号、全部前置/步骤/预期、附加字段及来源摘要，自行整理内部记录；不要求用户手写 JSON 或配置，不把底层 CLI 的文件参数转交用户。只确认无法取得的真实缺项，已有许可不重复询问，禁止输出带占位符的建议答案；准备齐全后不为“已生成中间文件”询问是否继续。

## 阶段 1：材料与来源

通常与项目内 `functiontest-workflow` 配合：复用父流程及公共子技能的来源选择、生成/核对和已确认开关，接收最终全量用例、范围、许可与真实父计时，不得再次调用 Workflow。父文件不修改，PC 执行适配集中在本技能；复用清单见[父流程与子技能协作](references/workflow-contract.md)。

直接调用按需复用项目现成组件，已有完整用例不重复生成。参考包只读对照，执行用项目已部署副本，不固定维护机路径或混用版本；不回退旧 PC 入口。真实缺项如实记录，不改父文件或自动安装。

## 阶段 2：准备与附加

1. 从本技能根运行 [mono-pipeline-test.bat](mono-pipeline-test.bat) 或 Python 3.10+ 的 [scripts/cli.py](scripts/cli.py)，先核对交付清单。Agent 常规调用在子命令前加 `--compact`，保留末样本与证据，减少重复输出；普通使用不刷新清单。内部准备见[交付契约](references/delivery-contract.md)。
2. 实际执行先查明确 EXE 是否已运行：存在则复用，否则由当前 Agent 自主启动 Player，不再要求用户手动启动。按确认的工作目录/测试开关启动，就绪只读轮询默认总预算30秒：立即检查，就绪即继续，不固定休眠、不自动延长；用户明确指定预算时沿用。失败停止，不杀死、不重启、不启动第二实例。此预算仅供启动就绪检查，不改连接或业务动作超时。仅离线准备时不启动、不附加、不生成冒充测试完成的正式报告。
3. `output-check` 后 `init`，使用返回的新本轮根 `attach`。已有父上下文时传实际 `--workflow-timing`、`--workflow-parent-id`、`--workflow-child-id`，使用同一功能前缀 `--run-prefix`，不重建父；直接调用使用自身计时。父流程中的编辑器编译/PlayMode/测试执行由本技能的 PC 链路承接，其他公共阶段按需复用；见协作契约。静态准备或启动成功不等于附加成功。

不伪造 PID/描述符，不自造许可证，不默认接受或扩大权限；内部迁移许可不等于运行或账号操作授权。附加、脚本读取、业务/准备动作、日志及截图分别按真实许可执行；登录、账号选择或资源构造不自动授权。令牌仅在内存认证头使用，不写命令行、报告或交付；不外挂保活或默认关闭自检。

## 阶段 3：正常执行路径

先读附加返回的 `discovery` 选择与现场一致的准备来源，再 `chain-start`、首次 `builtin:chain`、必要准备与独立比较、`chain-end`。初态不证明就绪，准备不计业务例、不代替前置。按钮优先用 `builtin:buttons` → 原 `action` 的 `builtin:click_button`，绑定实际节点及实例；守卫与动作后新帧不变，见[宿主契约](references/host-contract.md)。

同框架登录直接采用[固定登录流程](references/login-navigation.md)：普通按钮路径为`GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame/LoginBtns/LoginButton`，不重复探查协议、账号、SDK和主界面。按已有登录授权核验该按钮并点击一次，新帧确认激活登录页消失即完成登录准备；目标业务页面仍按原用例检查，不额外绑为登录成功条件。

| 操作 | 使用方式 |
| --- | --- |
| 构造计划 | 沿用 [case-suite.json](assets/templates/case-suite.json)，每例 `start-case` 开始、唯一 `final` 收尾；按真实前置、资源及结果依赖分批 |
| 本地预检 | `plan-check` 排除原文/索引、基线、脚本及引用错误；不接触 Player、不登记草稿、不消耗命令 ID |
| 执行 | 优先 `run-suite`，单例 `run-case`；现场分支才用单步探索，稳定后回到批处理，不另写执行器或草稿格式 |

相同机械字段用 `defaults`，常规读取用 `builtin`，已审定机械断言用 `rule`；特殊语义用完整 `basis`。预期取需求精确 `literal` 或独立配置 `baseline`，不从 UI 实际值反推，不采用脚本自述通过。

旧生成器先查固定未定论列表、假覆盖和依赖顺序。已读配置直接从有效观察文件登记基线，不把未登记误称运行端无能力；颜色/图片原值用 `chain/subtree`。字段和登记方法见宿主契约。

`covers_step=true` 仅覆盖确实完成的原只读步骤；原点击、抽取等必须有真实 `action`。拟 `passed` 的全部原索引须完整，`blocked` 保留未执行步骤，不补重复读取；静态通过不证明语义等价。逐例重查资源与前置，不能假定批间状态隔离，必须先完成真实操作再验证其结果页。

原步骤要求完成后核对时，观察关联本例最后动作，设 `poll.require_match=true`，等待真实完成信号和最后确认帧。页面存在不代替展示完成；未确认时批计划跳过后续动作/断言，保留未定论及已有失败。单步查 `poll_matched/status.completion_pending`，仅可新 ID 只读确认，不重发动作。

补交前读 `status`，先收口活动例，再选择 `remaining_case_ids` 中从未开始的用例；不重开已有 final。同一 ID 永不重放，已登记计划/请求/基线不改写；单步草稿可用 `request-check`、`request-publish` 检查后发布新文件。

## 判定与停止

功能解锁、时间窗、支付条件分别核对；资源不足不阻断原本不依赖支付的用例，不删除零资源等原条件。回执成功不代替结果；缺字段、旧帧、类型异常不补 false/0。

| 状态 | 必须具备 |
| --- | --- |
| `passed` | 原前置、全部步骤/预期及本例有效独立比较；只读例可无动作 |
| `failed` | 至少一个有效原预期反例，永久锁存，不被环境归因覆盖 |
| `blocked` | 实际缺权限、真实环境记录、独立未满足的关键前置或用户停止 |
| `test_inconclusive` | 已尝试但观察不足；不可构造须有构造尝试或真实环境阻断，不用 `not_attempted` 假收口 |

新包装只返回有界 JSON；委托、运行时对象须在片段内计算并投影为原值。已验证身份的只读返回错误或严格 `script_failed` 隔离本例并真实收口，其他例可继续。动作异常、阶段未知、超时、断连、身份/协议或来源异常仍整轮冻结；更正及新轮条件见[异常处理](references/orchestration-recovery.md)。

## 收口与参考

沿原全集 `close` → `audit`，缺 final 留真实中断原因和未执行清单。父模式再闭合实际子/reference/父计时，Mono `report` 一次；显式包内父才用 `context-*`。唯一报告取本轮 journal；统计/用量/上传按授权复用现成子技能，传明确报告/JSON路径。来源失效只交诊断，本宿主不自行上传。

| 按需场景 | 参考 |
| --- | --- |
| 命令、计划、比较、共享链路与完成等待 | [host-contract.md](references/host-contract.md) |
| 公共 Unity API、反射、日志/截图 | [bridge-contract.md](references/bridge-contract.md)、[read-basic.cs](assets/templates/read-basic.cs) |
| 离线交付、构建库存、首次接入 | [delivery-contract.md](references/delivery-contract.md)、[internal-license.md](references/internal-license.md) |
| 项目适配或同框架固定登录 | [GameClient 接线](assets/adapters/GameClient/README.md)、[固定登录流程](references/login-navigation.md)，不重新发现已约定路径 |
| 修改宿主后的隔离验证 | [isolation-tests.md](references/isolation-tests.md) |

首次接入的批准/备份见交付契约。离线检查不代替公司 CyouCode 实机验收，不承诺通过数或耗时。
