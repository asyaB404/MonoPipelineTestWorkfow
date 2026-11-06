# 宿主执行契约

<!-- 创建日期：2026-10-26；作者：Cyou；更新日期：2026-11-05；更新人：Codex；功能：公共命令、计划、比较、链路及证据约束；参数：完整原输入、目标、权限、本轮根与请求。历史实施/验收流水移出日常契约，原作者归属不变。 -->

从 Skill 根使用 [mono-pipeline-test.bat](../mono-pipeline-test.bat) 或 `py -3 -I -B scripts/cli.py`，最低 Python 3.10。Agent 常规调用在子命令前加 `--compact`，如 `scripts/cli.py --compact observe --run ... --request ...`；默认仍完整输出。简洁模式仅省有效观察的重复信封与中间轮询值，保留每个样本的 ID/帧/引用、最终实际值、错误、状态和退出码；journal 与审计原值不变。材料与来源按[主入口](../SKILL.md)，所有会话操作复用 [session.py](../scripts/session.py)。

## 命令与收口

| 命令 | 输入与职责 |
| --- | --- |
| `output-check`、`init` | 候选输出/功能前缀预算；完整用例、目标、输出及可选来源/父绑定，返回实际本轮根 |
| `attach` | 核验单目标许可、包、身份/ACL/能力与 Mono Development；同一探针返回最多256节点的仅名称/路径/激活态 discovery |
| `chain-start`、`chain-end` | 独立准备来源与唯一就绪闭合；不增加业务用例 |
| `plan-check`、`run-case`、`run-suite` | 同一静态预检；后两者登记计划后顺序执行，附加/关闭/报告仍独立 |
| `request-check`、`request-publish` | 草稿结构/当前例关联检查；后者独占发布新文件，不发送动作 |
| `start-case`、`observe`、`action` | 单次开始本例、只读观察、通过前置与守卫后的单次动作 |
| `compare`、`final` | 对已有观察独立比较；完整覆盖与失败锁存后的唯一四状态 |
| `baseline`、`reference` | 登记独立预期来源；保存同例同构建已验证的定位事实，不代替业务结论 |
| `attribute`、`note`、`collect-evidence` | 关联真实事件的归因/说明/日志截图；未定位不计确认 Bug，不修产品代码 |
| `status`、`close`、`audit`、`report` | 本地状态、真实关闭、证据审计、唯一报告；不新连接 Player |
| `context-*` | 仅独立包内父的初始化/状态/关闭/审计/报告，与 Workflow 父互斥 |
| 离线维护命令 | 交付/目标/首次接入见[交付契约](delivery-contract.md)，不提供身份或传输旁路 |

通常承接父 Workflow 的 PC 执行阶段，复用其真实来源、范围、开关及计时；父文件保持原样，公共子技能复用与执行差异统一见[协作契约](workflow-contract.md)。初始化绑定实际 `--workflow-timing`、`--workflow-parent-id`、`--workflow-child-id`，互斥显式包内 `--parent`；先宿主 `close/audit`，再结束实际子/reference/父计时，最后 Mono `report` 一次，起点/归属/闭合/包含关系继续核验。直接调用可使用自身计时，不伪造父上下文，也不以父文档是否有 PC 分流标题作为执行门禁。

退出码：0 操作完成；1 有效反例；2 输入非法；3 环境阻塞/明确未执行；4 未定论/冻结；5 完整性错误。退出码不替代 journal 的产品状态；显式等待未确认也可返回 4 而不冻结，见完成条件。

## 原输入、权限与不可变来源

原字段/字节完整快照，索引只作审计视图；初始化不含操作映射。严格 JSON 拒绝重复键、NaN、越界/非有限数和未知控制字段，保留允许的文件头及原业务附加字段。用例、来源、目标、许可、清单及已登记请求/基线不得静默改写或删除；来源失效的本地终止见[异常处理](orchestration-recovery.md)。

| 请求绑定 | 精确来源 |
| --- | --- |
| 前置比较 | 原前置文本/显式索引；获准构造前确认未满足，构造后独立新帧回读 |
| 步骤与动作 | 原步骤文本/显式索引；动作不因更换 ID 重复消耗 |
| 动作守卫 | 原步骤文本/索引及同目标最新前观测，不能借前置文本替代 |
| 预期比较 | 完整原预期/索引、相关原步骤及独立依据，不能用回执成功替代 |

权限为 `attach`、`script_execute`、`business_action`、`setup_action`、`log_read`、`screenshot`，分别核验。许可接受不自动批准账号动作，缺权限不读不动。登录、账号选择、GM 或资源构造须有明确范围和真实入口，不能为了满足断言改产品值。令牌只从核验 ACL 的描述符进入内存认证头；目标不携带令牌，不复制描述符原文到报告或交付。

模板：[cases.json](../assets/templates/cases.json)、[provenance.json](../assets/templates/provenance.json)、[target.json](../assets/templates/target.json)、[target-permission.json](../assets/templates/target-permission.json)。原文按显式索引而非列表位置绑定；结构错误先修草稿，通过检查登记后才不可变。`Session.submit`、单步 CLI 与请求发布共用同一检查，不开放重试或授权旁路。

## 独立共享链路

先看 attach 的 `discovery`，区分登录页和已进入业务现场，再选择实际准备来源。初态只是选路参考，不是已登记业务观察，不证明权限、登录或就绪；不读文本/图片，不自动导航。附加后、首个 `start-case` 前 `chain-start`：schema 为 `mono-pipeline-chain/1`，含完整标题、前置、步骤、预期及 Agent 审阅；来源来自已批准范围，不添加业务例或权限。首次观察仍须 `builtin:chain`。

准备仍使用普通 `observe/compare/action`：每次动作需 `setup_action`、同目标最新 before、独立通过守卫和上一动作后的新帧。准备索引只绑定独立来源；所有准备预期成立后，以空请求 `chain-end`，就绪由宿主回算，不能手填。

链路未验证、只读脚本冻结、未知动作或来源变化时不准就绪/开始业务例。链路在同一 journal 留完整证据但不生成业务 final、不计原总数或通过数；各例仍独立验证自己的前置和预期。回归见 [test_chain_context.py](../scripts/tests/test_chain_context.py)。

## 计划与合法续行

沿用 [case-suite.json](../assets/templates/case-suite.json)：多例 schema `mono-pipeline-case-suite/1`，顶层 `schema/defaults/cases`，每例 `case_id/group_id/steps`；1–64 例，每例至多 512 步，全批至多 4096 步。单例 schema `mono-pipeline-case-plan/1`，将 `case_id/group_id/steps` 放顶层；每步 `{operation, request}`。例 ID 不重复、命令 ID 全轮唯一，每例首步 `start-case`、末步唯一 `final`；步骤操作限命令表中的本例操作，不包含附加/关闭/报告。

`defaults` 只补缺失的机械字段，已有值优先；允许 `send/target/value_format/timeout_ms/read_only_review/target_review/reason`。`compare/final/start-case` 不继承，未登记键拒绝，`timeout_ms` 仍受目标实际上限约束；使用字段名写入计划证据，不创建第二套计划格式。

`plan-check/run-case/run-suite` 共用结构、脚本路径/发送预算、原文、同目标最新前观测、守卫和跨步骤引用检查。拟 `passed` 须声明全部原前置/步骤/预期；动作自身覆盖原步骤，只读步骤才用 `covers_step=true`。拟 `failed` 需原预期比较；关键前置阻塞需比较，环境阻塞需真实记录，权限阻塞需实际缺少的已知权限。`blocked` 不要求补未执行步骤，`not_constructible` 需本例构造动作或真实环境阻断，真实效果仍在运行期核验。

基线先登记后引用，可跨批内用例复用但不重复登记同 ID；预检读取原 JSON 并验摘要。未来/未登记基线，以及同一观察、同一原前置、同字段的互斥等值比较均拒绝；合法 setup 后的新观察允许状态不同。登录与功能解锁等不同事实分别绑定，不能借同一原句代替。

`plan-check` 不建连、不登记来源、不写 `cli_begin/cli_result`、不消耗命令 ID、不冻结本轮；静态通过不证明语义、守卫或产品通过。执行器先登记计划原字节/摘要，每步仍留真实事件及计划索引。`run-suite` 复用一次连接，省去重复 CLI/身份/全包摘要开销，不隔离 Player 业务状态；按依赖拆批，逐例重新观察前置和资源，不预填整组未定论。

`status.remaining_case_ids` 仅含从未开始的原例，`current_case` 是活动例，`finals` 是已收口结果。补交先处理活动例，再选未开始例；不另维护 DONE 表、不重开已有 final。已开始/活动/收口用例的开始计划在登记前拒绝，关闭/冻结轮不续行，不为旧动作换 ID 重放。

## 观察与独立比较

常规读取用现有 `builtin`，与手写 `script` 互斥：`chain` 读根/节点，`subtree` 指定 `root`，`buttons` 枚举按钮，`logic_field` 指定 `logic_type/field`。节点预算、深度及参数由 [builtin_observation](../scripts/session.py) 校验。完整场景路径和自定义按钮均可观察；热更字段从真实实例及继承链读取，多个候选不取第一项，复杂值不伪装字符串，缺对象/字段不补零或假值。

`chain/subtree` 的节点保留完整 `path`，有对应控件且可读时另返回 `text_color_rgb/text_color_rgba`、`image_color_rgb/image_color_rgba`（小写、无 `#` 的 6/8 位色值）和 `sprite_name`（真实 Sprite.name，不裁剪或推断资源 ID）。同时支持标准控件与 `GameText/GameImage` 公共属性；失败/缺失不补颜色或名称，原生 Image 未加载图片时名称为 null。这些是组件原值，不是最终渲染像素或资源唯一身份；按当前控件路径及独立配置逐项比较。

### 固定按钮动作

沿用 [action.json](../assets/templates/action.json)，不另写点击 C#：先 `builtin:buttons`，可用 `root/name_contains` 缩小范围，选返回行中的实际 `path`，不能拿父容器代替。每行含 `component_type/instance_id/node_instance_id/button_count/enabled/interactable/effective_interactable/click_method`；`truncated=true`、路径/组件歧义、缺失或不可交互时拒绝生成动作。实例 ID 为真实非零 Int32，允许负数。

原 action 仅新增 `builtin="click_button"` 和 `builtin_options={"path":"实际完整节点路径"}`，与 `script` 互斥，格式为 json。before 必须是本例同目标最新、有效且由宿主生成的 buttons，独立守卫和原前置仍须通过。宿主从 before 派生组件/实例，发送时再次核对，GameButton 优先且只调用一次公开 `InvokeOnClickListener`；仅标准按钮则使用其公开事件。观察不调用会更新点击间隔的私有方法，不同时触发两条接口。返回 `method_called` 只记录方法调用，业务结果仍须动作后新帧独立比较。

JSON Pointer = 实际结构值的字段路径。每条 [compare](../assets/templates/compare.json) 绑定原范围/索引/完整文本、步骤索引、观察 ID/字段、规则、独立依据和真实语义审阅。观察必须同例/构建/目标、无业务错误；动作后比较绑定本例最后动作后的独立新帧，不用动作回执。

支持 `eq/ne/gt/ge/lt/le/contains/delta`，标量 bool/int/float/str 类型严格、不隐式转换，数值必须有限。`contains` 仅用于原预期确为文本包含且已审核的情况；`delta` 使用同目标本例 before/after。缺字段/null/异常/类型不符/旧帧均未定论，不伪造产品反例。`rule/op/target/value` 简写只适用于 [RULE_BASIS](../scripts/session.py) 已审定机械语义，`target` 是 JSON Pointer，不能与完整 `basis` 混写。

独立依据为原需求精确 `literal`，或已登记配置/需求 `baseline` 的字段及显式符号因子；保留原路径、摘要和审阅，费用/奖励比较真实业务差值。配置与 UI 可同次或分别读取，只要保留各自来源再独立比较；不能从 UI 实际值反推预期、采用脚本自算通过标记，或用节点存在替代费用/等级。一个有效原预期反例即可锁存 `failed`，不必先补齐其余预期。

### 直接登记已读取的配置

不需要新增导出器，也不必手抄一份配置 JSON。先在准备链路或必要探索中按真实类型/字段读配置原值，再走现有接口：

1. 从 `observe.samples` 选择已验证的最终样本，核对 `observation_valid=true`、构建/目标及真实配置来源；取该样本的 `observation_ref.path/sha256`。`observe` 外层没有直接的 `observation_ref`。
2. 用 `baseline` 登记：`reference_id` 为新 ID，`kind=configuration`，`path` 为本轮根拼接上述真实路径，`sha256` 取上述摘要，`review` 明确读的是哪份配置而非 UI 实际值。保留该文件原字节，不注册旧轮或无效观察，不把实际奖励、UI 或动作回执改称配置。
3. 比较仍用 `basis.kind=baseline/reference_id/field/reviewer/statement/semantic_review`；文件是观察信封，故字段从 `/value/` 下取，例如 `/value/configuration/required_count`。数组按真实 ID 配对逐项比较标量，并核对总量/缺项/多项，不只断言 `mismatch_count=0`。派生值在独立新 JSON 中保留原配置路径、摘要和推导审核，不能从 UI 反推。

这条路径由 [test_submission_repair.py](../scripts/tests/test_submission_repair.py) 的正反例覆盖：正确 UI 可通过，错误 UI 仍锁存失败；它仅简化已有基线登记，不改变预期独立性或四状态。

## 显式业务完成条件

`observe.poll.require_match` 可选，默认 false，保留旧轮询语义。原步骤要求完成后验证结果时显式设 true，并关联本例最后动作；下例仅展示追加字段，实际 ID、原始状态字段和预算取当前业务记录：

```json
{
  "purpose": "after",
  "after_command_id": "CURRENT_ACTION_ID",
  "poll": {"field": "/page_state", "operator": "eq", "value": "Ready", "stable_samples": 2, "require_match": true}
}
```

预算内既要稳定新帧样本，又要最后确认帧有效且匹配；结果仍取 `observe` 的末个样本。未确认时保存事实，批计划跳过本例剩余动作/断言，到原 final 真实收口未定论；已有有效反例仍失败。其他例可继续，但依赖该结果的例须重查前置，不能把动画中余额未变判成扣费失败。

单步不自动结束本例：查看 `poll_matched/completion_required/status.completion_pending`。成功读取但完成未确认时退出 4，`ok=true/frozen=false`，不是传输失败；明确未执行的编译诊断退出 3。可用新文件/新 ID 只读确认后再比较，未确认时拒绝新动作，结果比较记未定论；不重发动作。审计按样本、确认帧和比较当时状态回算，后续恢复不改写早期无效比较。

条件由 Agent 依据本次业务审核，不能强制全局 Idle，也不能凭旧结果页存在证明本次完成；完成后仍独立核对费用/奖励。历史已登记计划不补写字段。传输/协议/身份/未知求值仍冻结整轮，不转成普通等待超时；该能力为包外宿主能力，不要求新增 Unity API。

区分结果数据可读与整个展示/关闭流程完成：页面可以在获取新角色、逐条展示阶段已经存在；原步骤要求展示完成或关闭时，等待该阶段的真实就绪状态，关闭后另读页面消失。不要将尚在播放的页面当完成，也不要为了让断言成立强制跳过原步骤要求自然播放的动画。运行期私有状态已经可读时优先使用现有 `logic_field` 或原只读投影，不因采集脚本没输出就认定 PC 包缺接口。

## 描述符连接与开销

心跳 = 描述符最近服务状态更新时间，仅已认证的基本状态请求刷新；命令目录和运行状态不能代替。连接先完整核验许可、静态包、ACL/凭据格式、EXE/PID 创建时间、端口独占、构建/版本/平台和时间顺序，旧心跳此时只记录；Windows 身份由一次 PowerShell 探测取得，不减校验项。

静态身份有效后，一次内存凭据的基本状态握手使用原 `identity_timeout_ms`（默认 10000）；严格验真实回执并重读描述符/系统身份，除心跳外全部字段与凭据不变，心跳可靠落盘且满足 `descriptor_age_ms`（15000）及 `clock_tolerance_ms`（2000），再验命令目录、运行身份和附加探针。ready 不代表业务通过。

每次执行前仍验同目标；合法连接的心跳过旧时，排除身份/凭据变化后走同一单次握手，不重建/接管目标。纯本地 `verify_target` 仍拒绝过期，`target-prepare` 仅生成待握手公开记录，不请求或改心跳。失败、超时、畸形回执、删除/改写或未知身份仍阻塞，已附加轮永久冻结；本地状态/比较/审计/关闭不探活。

`identity_cache_ms`（默认 2000）仅限同一进程/同一 Pipeline 已实际取得的探测和静态摘要，超窗重新核验，不跨 CLI、不替代握手。journal 证据摘要按真实文件身份在进程内记忆，变化/消失仍严格拒绝；来源/请求/基线外部校验不缓存。`integrity_mode=identity_only` 和 `--no-self-check` 仅操作者显式选择，不作提速默认，前者不证明完整包字节。禁止后台保活、修改阈值/描述符或换轮绕过冻结。

## 证据、异常与报告

实时 writer 独占锁、seq、摘要链和独立头锚；intent fsync 后才发。原片段/包装分别留原字节和摘要，发送期使用 Windows 不共享写入/替换的读取句柄，优先发送冻结包装；脚本不是沙箱。日志/截图需独立权限、同例/构建/观察帧、路径/大小/摘要及 Agent 敏感审阅，见[公共 API](bridge-contract.md)。

新包装在序列化前只复制标量、普通数组/List和字符串键Dictionary；拒绝委托、任意对象、非有限数、深度/节点/字节超界，不反射任意返回对象的属性或执行返回委托。特殊业务片段应先计算，再返回这些类型的原值；不要将未调用的 `Func` 或 Unity 对象直接塞进字典。新包装带版本标记，审计按冻结格式重建；旧证据/冻结状态不改写。

只有身份已验证的只读 `return_value_contract:*`，或严格分类的只读 `script_failed`，可隔离本例并跳至真实收口，已有失败锁存、其他例继续。返回契约错误保留成功执行回执及无效观察，不谎称编译未执行；单步 `case_frozen=true/frozen=false`、退出4。动作/探针同类错误、运行异常、传输/身份/协议/来源或未知阶段仍全轮冻结。明确未执行编译诊断更正和来源中断见[异常处理](orchestration-recovery.md)。

报告由原全集和唯一 final 生成，保留完整预期/绑定/异常，未开始例单列、不补假 final；缺例关闭需明确原因。正式报告前关闭、审计及本轮真实计时必须成立，仅已绑定父上下文时核验父子计时；父总时长不累加分项，无上传就无上传耗时，日志不全不称无异常。来源变更只可诊断终止，不继续正式报告。原摘要/锁是完整性检测，不是防同权限主体全量重写的认证签名；程序保守拒收已知敏感字段/文本，不能证明图片或任意编码无秘密。
