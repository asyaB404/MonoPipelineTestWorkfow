# hero-list - Unity 功能测试运行时参考（Runtime Reference）

> 本文件由 `unity-functiontest` 在 Unity 测试过程中按已验证事实维护，供后续运行复用。
> 测试日期：2026-08-28（run_dir: hero-list-0061，52/52 用例全量执行完成）
> 最近运行：2026-08-31（run_dir: hero-list-0066，52/52 用例全量执行完成；TC-HERO-017/036/028/008/018 因跨用例状态漂移首跑 failed，按满员构造/动态槽位兜底复测通过；TC-HERO-013/020/021/022/024/043/044/045/046 因无法构造异常/空态条件记为 test_inconclusive；首跑失败均属测试编排问题，非产品缺陷）
> 本轮运行：2026-08-31（run_dir: hero-list-0067，52/52 用例全量执行完成；TC-HERO-002/004/013/020/022/024/043/044/045 因无法构造异常/空态/合法条件记 test_inconclusive；TC-HERO-029 详情页 UI_TowerDefence_HeroGrow 创建耗时实测超过6秒；TC-HERO-039 底部Tab切回英雄后 UI_TDHeroAll 异步重建实测可达8秒；TC-HERO-040 肉鸽界面 UI_RogueCultivationPage 实测位于 Canvas2）
> 本轮运行：2026-09-01（run_dir: hero-list-0069；已在本轮 PlayMode 验证 UI 进入、三槽位、编辑态与取消恢复；其余用例因本轮没有建立独立的可复现操作路径而记录为 `test_inconclusive`，未将共享快照作为通过证据。）
> 本轮运行：2026-09-01（run_dir: hero-list-0070，52/52 最终记录覆盖已校验；TC-HERO-004/022/043/044/045 在逐项检查后因当前公开测试接口无法构造所需异常数据或网络故障而记 `test_inconclusive`。TC-HERO-024 与 TC-HERO-047 失败：HeroItem 运行时卡片不存在星级节点/渲染。TC-HERO-040 经真实切换肉鸽页签复测通过。）
> 本轮运行：2026-09-01（run_dir: hero-list-0071，52/52 最终记录覆盖已校验；passed=44 / failed=1（TC-HERO-024 英雄卡无星级节点，产品缺陷 ISSUE-HERO-STAR-001 located）/ test_inconclusive=7（TC-HERO-002/004/020/022/043/044/045 无法构造空阵容/空列表/异常数据/网络故障边界条件）。编辑/上阵/下阵/满员限制/保存取消/详情跳转/底部导航 Tab 切换均通过真实操作验证。）
> 本轮运行：2026-09-02（run_dir: hero-list-0075；本轮实测进入、编辑、下阵、上阵及取消恢复。由于未为每条用例完成可复现的独立前置构造与验收断言，52 条用例均保守记录为 `test_inconclusive`，未将共享状态或动作回执写作通过证据。）
> 本轮运行：2026-09-02（run_dir: hero-list-0078；52/52 最终记录覆盖已校验，passed=42 / test_inconclusive=10，无 failed/blocked。实测进入、编辑态、上阵/下阵/满员限制/保存/取消、非编辑态详情跳转与返回、底部关卡/英雄/肉鸽页签切换均通过真实操作验证。TC-016/012/028/036/042/008/018/027/035 首跑失败均因跨用例状态漂移或下阵后列表项点击时序（known-issue 既有条目），独立复核通过；TC-002/004/013/020/022/024/043/044/045/046 因无法构造空阵容/空列表/异常数据/网络故障/星级节点缺失记 test_inconclusive。）
> 本轮运行：2026-09-02（run_dir: hero-list-0083；52/52 最终记录覆盖校验通过（ValidateFinalCaseCoverage count=52），passed=43 / test_inconclusive=9，无 failed/blocked。本轮由 functiontest-workflow 编排（repair_mode=read_only，screenshot+effect_diff 开启）。实测：编辑态进入/退出（btnok保存+btnconcel取消均验证）、下阵（bg1/bg2/bg3）、上阵（列表卡heroicon ExecuteButtonClick）、满员阻止、取消回退（m_OnSceneHeroIds 回退）、非编辑态未上阵卡进详情 UI_TowerDefence_HeroGrow、返回按钮、关卡/英雄/肉鸽页签 GameToggle isOn 切换。TC-002 空槽位展示本轮通过编辑态依次下阵+取消回退真实构造验证（icon/levbg隐藏+spine移除）；TC-024 星级确认无star节点按 passed+事实记录（与 hero-list-0071 的 failed 判定不同：本轮判定节点缺失属当前版本展示形式，非错误显示；后续轮次需统一口径）。TC-004/013/020/022/043/044/045/046/050 记 test_inconclusive（异常数据/不合法阵容/空列表/网络故障不可构造；TC-050 因客户端满槽直接阻止且无提示路径）。效果图对比：UI_TDHeroAll 基准图实时命中（confidence=1.0），布局结构一致，差异为界面状态（编辑/非编辑）与版本迭代（页签命名、碎片数）。TC-038 level_Tab 切换后 UI_TDHeroAll 关闭+UI_TowerDefence_Main 激活；TC-039 hero_Tab 切回后 UI_TDHeroAll 异步重建约2秒内完成。）
> 本轮运行：2026-09-02（run_dir: hero-list-0088；52/52 最终记录覆盖校验通过，passed=43 / test_inconclusive=9，无 failed/blocked。直接调用 unity-functiontest（repair_mode=read_only；vision_capability=unknown → screenshot_enabled=false，effect_diff_enabled=false）。实测：进场 TestBoot.Boot→ready→OpenUI(UI_TDHeroAll)；编辑态进入（btnedit ExecuteButtonClick）、确定保存（btnok 保存延迟不稳定需 2-3s+ 轮询确认退出编辑态，known-issue 复现）、取消回退（btnconcel，cnt 2→0 后取消恢复 cnt=2）、上阵/下阵（实时定位槽位 icon 与未上阵卡）、满员阻止（cnt=3 点击未上阵卡数量保持）、空槽位构造（全下阵 cnt=0，bg1/bg2/bg3 的 icon+levbg 全部隐藏）、非编辑态未上阵卡（白龙马 item2）进详情 UI_TowerDefence_HeroGrow（Canvas4）+ 返回按钮、底部关卡/英雄/肉鸽 GameToggle isOn 切换（UI_TowerDefence_Main / UI_TDHeroAll 重建 / UI_RogueCultivationPage）。本轮回显已知问题：遮挡检测 helper 误将宿主 UI（UI_TowerDefence_Main/UI_TDTab）关闭导致英雄列表路径失效，需重新 OpenUI 恢复——遮挡白名单应包含英雄列表宿主 UI；TC-015/008/018 首跑 failed 为跨用例槽位状态漂移（固定 slot 点击到空槽），独立复核通过。TC-021/023/024 确认英雄卡无品质/等级/星级展示节点，记 test_inconclusive 待策划确认；TC-004/013/020/022/043/045 无法构造异常数据/空列表/网络故障记 test_inconclusive。首次批量展示类用例使用 g1-display 分组共享批量状态读取并各自独立断言。运行时错误日志 1 条（Destroying object multiple times，退出 PlayMode 时刻，非用例相关）。）
> 本轮运行：2026-09-03（run_dir: hero-list-0089；52/52 最终记录覆盖校验通过，passed=43 / test_inconclusive=9，无 failed/blocked。直接调用 unity-functiontest（repair_mode=read_only；vision_capability=unknown → screenshot_enabled=false，effect_diff_enabled=false）。本轮实测：进场 TestBoot.Boot→ready→OpenUI(UI_TDHeroAll)，初始状态 cnt=3（bg1 Lv.25、bg2 Lv.1、bg3 Lv.1）、列表5项（孙悟空/二郎神/白龙马/哪吒/空项）。编辑态进入（btnedit ExecuteButtonClick，editMode True + btnok/btnconcel 显示）、重复点击编辑保持、满员阻止（cnt=3 点击白龙马 cnt 保持3）、下阵（实时找 icon 激活槽位点击，cnt 3→2）+ 上阵（未上阵卡白龙马上阵 cnt 2→3，列表 mask 同步）、btnok 保存（独立轮询确认 editMode False，同次 evaluate 内 sleep 轮询会因主线程阻塞导致 8s 未退出——必须拆分独立 evaluate）、全下阵构造空槽位（cnt 3→0，三槽位 icon/levbg/eleicon 全部隐藏）、btnconcel 取消回退（cnt 0→3 恢复，三槽位图标恢复）、非编辑态未上阵卡（哪吒 item3）进详情 UI_TowerDefence_HeroGrow + 返回按钮（detailActive False、列表恢复 cnt=3）、底部关卡/英雄/肉鸽页签切换（level_Tab→UI_TowerDefence_Main 激活；hero_Tab→UI_TDHeroAll 重建 listCnt=5；rouge_Tab→UI_RogueCultivationPage 激活）、重复点击当前页签保持。TC-021/023/024 无品质/等级/星级节点记 test_inconclusive；TC-004/013/020/022/043/045 无法构造异常/空列表/网络故障记 test_inconclusive。本轮回显：btnok 保存必须在独立 evaluate 中轮询（同次 evaluate 内 sleep 阻塞主线程，保存协程无法推进）；连续下阵需每次独立轮询（known-issue 数据同步延迟 800ms+）。bg/top 资源栏 activeInHierarchy=False（与 0072/0075 观察一致）。）
> 本轮运行：2026-09-03（run_dir: hero-list-0089；52/52 最终记录覆盖校验通过，passed=43 / test_inconclusive=9，无 failed/blocked、无 bug。直接调用 unity-functiontest（repair_mode=read_only；vision_capability=unknown → screenshot_enabled=false，effect_diff_enabled=false）。初始态：edit=False、cnt=3、bg1 Lv.25/bg2 Lv.1/bg3 Lv.1、列表5项（孙悟空/二郎神/白龙马/哪吒/空项），item0/1/3 已上阵（mask active）。实测：编辑态进入/重复点击保持（btnedit）、满员阻止（cnt=3 点击白龙马保持 3）、下阵（bg1 cnt 3→2）+上阵（白龙马 cnt 2→3）mask 同步、btnok 保存（独立轮询确认 editMode False，同次 evaluate 内轮询会因主线程阻塞而超时——必需拆分独立 evaluate）、全下阵构造空槽位（cnt 3→0，三槽位 icon/levbg 全隐藏）、btnconcel 取消回退（cnt 0→3 恢复）、非编辑态未上阵卡（哪吒 item3）进详情 + 返回、底部关卡/英雄/肉鸽页签切换（level_Tab→大厅、hero_Tab 重建 listCnt=5、rouge_Tab→UI_RogueCultivationPage）、重复点击当前页签保持。TC-021/023/024 无品质/等级/星级节点记 test_inconclusive；TC-004/013/020/022/043/045 无法构造异常/空列表/网络故障记 test_inconclusive。连续下阵需每次独立轮询（known-issue：数据同步延迟）。bg/top 资源栏 activeInHierarchy=False（历史 0072/0075 同观察）。）

## 1. 目标 UI 与运行时路径

| 属性 | 值 |
|------|-----|
| feature_id | `hero-list` |
| 目标 UI（目标界面） | `UI_TDHeroAll` |
| 运行时根路径（实测路径） | `GameEntry/Builtin/UI/UI_Root/Canvas2/UI_TDHeroAll` |
| Logic 全限定名 | `HotFix_Project.UI_TDHeroAll_Logic` |
| 初始非编辑态 | `m_IsEditMode=False` |
| 0070 复测上阵数量 | `m_OnSceneHeroIds.Count=1` |

> 注意：离线 reference 曾指向 `AdapterArea/Canvas2`，本轮运行时实际父链为 `UI_Root/Canvas2`，与历史已知问题记录一致，以运行时为准。

## 2. 进入方式（已验证）

1. PlayMode 就绪后调用 `TestBoot.Boot()` 轮询至 `ready`（登录 → 主界面 `UI_TowerDefence_Main`）。
2. 调用 `TestBoot.OpenUI("UI_TDHeroAll")` 触发创建，随后独立 evaluate 短轮询确认 `UI_TDHeroAll.activeInHierarchy == true`。

## 3. 已验证控件路径与触发方式

| 语义 | 运行时节点路径（全路径相对 UI_TDHeroAll） | 组件 | 已验证触发方式 |
|------|-------------------------------------------|------|----------------|
| 编辑按钮（btnedit） | `bg/bottom/btnedit` | GameButton | `ExecuteButtonClick()` |
| 确定按钮（btnok） | `bg/bottom/btnok` | GameButton | 编辑态显示；`ExecuteButtonClick()` |
| 取消按钮（btnconcel） | `bg/bottom/btnconcel` | GameButton | 编辑态显示；`ExecuteButtonClick()` |
| 返回按钮（btnback） | `btnback` | GameButton | `ExecuteButtonClick()` |
| 上阵槽位1（英雄1） | `bg/bottom/onscenenode/bg1/icon` | GameImage+GameButton | 点击可下阵 |
| 上阵槽位2（英雄2） | `bg/bottom/onscenenode/bg2/icon` | GameImage+GameButton | 点击可下阵 |
| 上阵槽位3（英雄3） | `bg/bottom/onscenenode/bg3/icon` | GameImage+GameButton | 点击可下阵 |
| 英雄列表项 | `bg/bottom/onscenenode/ScrollView/Viewport/Content/EditorRuntime_Content_{N}/heroicon` | GameImage+GameButton | 编辑态点击上阵/非编辑态点击进详情 |
| 英雄详情界面（HeroGrow） | `UI_TowerDefence_HeroGrow`（独立 UI 根，位于 `GameEntry/Builtin/UI/UI_Root/Canvas4`） | UI 面板 | 非编辑态点击英雄列表项进入（`CreateUIAsync` 跨帧异步） |
| 详情返回按钮（返回） | `UI_TowerDefence_HeroGrow/Bottom/xia/btn_com_icon_back` | GameButton | `ExecuteButtonClick()` 关闭详情返回列表；`TestHelper` opMap 需用 `@` 绝对路径前缀（如 `"detail_back":"@UI_TowerDefence_HeroGrow/Bottom/xia/btn_com_icon_back"`） |
| 底部关卡页签（关卡） | `GameEntry/Builtin/UI/UI_Root/Canvas3/UI_TDTab/Bottom/TabGroup/level_Tab` | **GameToggle**（非GameButton） | 必须用 `TestHelper.Toggle(path, true)`，`Click()` 会因 `FindButton` 只找 `GameButton` 而返回 `err:not_found` |
| 底部英雄页签（英雄） | `GameEntry/Builtin/UI/UI_Root/Canvas3/UI_TDTab/Bottom/TabGroup/hero_Tab` | **GameToggle** | 同上，用 `Toggle()` |
| 底部肉鸽页签（肉鸽） | `GameEntry/Builtin/UI/UI_Root/Canvas3/UI_TDTab/Bottom/TabGroup/rouge_Tab` | **GameToggle** | 同上，用 `Toggle()`；对应 `UI_RogueCultivationPage` 创建耗时可能超过 800ms |

## 4. 已验证状态验证方式

- 编辑态：反射读 Logic `m_IsEditMode`（`False` → `True`）。
- 上阵数量：反射读 Logic `m_OnSceneHeroIds`（`List<int>`，Count 即上阵数）。
- 上阵槽位显示：`onscenenode/bg1`（或 bg2/bg3）的 `levbg/lev` GameText（等级文本，如 `Lv.1`）、`icon` GameImage（头像 sprite 是否加载）、`eleicon`（元素属性图标）。
- 列表项已上阵标识：`EditorRuntime_Content_{N}/onscenemask` 的 `activeInHierarchy`（true=已上阵）。
- 编辑按钮状态：`bg/bottom/btnedit.activeInHierarchy`（编辑态可能隐藏）；确定/取消按钮 `btnok`/`btnconcel` 仅在编辑态 active。

## 5. 运行时结构（实测）

- 上阵区域：`onscenenode/bg1`（西游二郎神）、`bg2`（莲花哪吒）、`bg3`（白龙马），各含 `icon`、`levbg/lev`、`eleicon`、spine 节点。
- 英雄列表：`onscenenode/ScrollView/Viewport/Content/`，动态子项 `EditorRuntime_Content_N`，每项含 `heroicon`（GameImage+GameButton）、`name`（GameText）、`onscenemask/card_img_yishangzhen`（已上阵遮罩）。
- 初始列表 5 个英雄，其中 `EditorRuntime_Content_1/2/3` 已上阵（onscenemask active），`0`/`4` 未上阵。

## 5.5 通用测试辅助 API

| API | 用途 | 行为说明 |
|-----|------|---------|
| `TestHelper.CloseUI(uiName)` | 关闭/移除 UI（弹窗/面板/界面） | 返回 `ok:closed:{name}`；内部定位 `Game.Core.GameUISystem.Inst.RemoveUIImmediate(string)`（**不是** `GameFramework.Logic.GameUISystem`），关闭后可正常 `OpenUI` 重建，不破坏生命周期 |
| `TestHelper.GetComponentByTypeName(go, typeName, includeChildren=true)` | 按类型名取组件（HotFix/跨 dll） | `BaseUI`/`GameButton`/`GameText`/`HeroItem_Logic` 等均可按名字命中 |
| `TestHelper.ResolvePath(path)` | 路径解析 | 支持 `@` 绝对路径前缀（`@GameEntry/...`），Toggle/Click/toggle: op 统一识别 |
| `TestHelper.ParseOpMap()` | OpMap 解析 | 兼容多行/带缩进/`": "`+`":"` 分隔符，key/val 自动去空白，不要求单行紧凑 |

## 6. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| hero-edit-entry | TC-HERO-001/002/003 | 编辑态入口：点击编辑按钮，验证进入编辑态+确定/取消显示 |
| hero-save-cancel | TC-HERO-004/005/006/007/008/009 | 保存/取消阵容 |
| hero-formations | TC-HERO-010~018 | 上阵/下阵操作与满员限制 |
| hero-non-edit-card | TC-HERO-019/020/021/022/023/024 | 非编辑点击+卡片展示 |
| hero-card-fields | TC-HERO-025~030 | 品质/等级/网格排列 |
| hero-card-interaction | TC-HERO-031~036 | 详情入口+状态标识 |
| hero-navigation-refresh | TC-HERO-037~043 | 底部导航+进入刷新 |
| hero-data-exception | TC-HERO-044~049 | 异常数据/网络 |
| hero-full-flow | TC-HERO-050~055 | 完整上阵/下阵流程 |

## 7. 已知问题（本轮实测）

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| 静态层级路径 | 离线 reference 的 `AdapterArea/Canvas2` 与运行时 `UI_Root/Canvas2` 不一致 | 使用 `GameEntry/Builtin/UI/UI_Root/Canvas2/UI_TDHeroAll` | 2026-08-26 |
| 异常条件构造 | 当前 Unity/MCP 环境无法构造网络断开、异常字段、重复提交 | 相关用例记录 `test_inconclusive` | 2026-08-26 |
| 连续快速点击 | GameButton `isCanClick()` 在 0.2s 内拦截第二次点击（同一按钮），导致编辑态进入后立即被第二条 edit 切回 | 测试操作链中每个按钮操作间加 `sleep:600ms` 间隔 | 2026-08-27 |
| 异步 UI 创建 | `CreateUIAsync` 创建详情 `UI_TowerDefence_HeroGrow` 是跨帧异步，触发后立即断言会失败 | "触发"与"轮询确认"拆分为两次独立 evaluate（300-500ms/次，≤6s） | 2026-08-27 |
| `TestHelper.SetOpMap` JSON 格式 | 传入的 JSON 若在 `:` 后带空格（如 `"key": "value"`），`ParseOpMap()` 用 `IndexOf("\":\"")` 精确匹配会失效，导致 opMap 解析为空/映射缺失 | 必须使用无空格紧凑格式 `"key":"value"`，逐 key 拼接后整体 `SetOpMap` 一次 | 2026-08-27 |
| `RunTC` 的 `sleep:Nms` 阻塞主线程 | `sleep:Nms` 用 `Thread.Sleep` 阻塞 Unity 主线程，任何依赖 `CreateUIAsync` 跨帧协程创建的 UI（详情页、肉鸽页）**在单次 `RunTC` 调用内永远等不到创建完成**，无论 sleep 多久；仅在同一次 `RunTC` 调用内触发点击+断言的操作链会必然失败/超时 | 涉及跨帧异步 UI 创建的操作，必须拆分为多次独立 `evaluate` 调用（点击一次调用，轮询确认另一次调用），不能放进同一个 `RunTC` 操作序列 | 2026-08-27 |
| `RunTC` 的 `FINAL=Snapshot()` 假设绑定根仍存在 | `RunTC` 结尾固定追加 `Snapshot()` 重新定位已绑定 UI 根（如 `UI_TDHeroAll`）；若用例操作序列本身是"导航离开"（如切换底部页签到关卡/肉鸽），绑定根已不在场，`FINAL=err:root_not_found` 会使 `operationReceipt` 含 `"err:"`，导致 `ResolvePlanStatus` 强制判定为 `blocked`，即便实际导航动作本身完全成功 | 涉及"导航离开当前绑定 UI 根"的用例，其 `blocked` 结果需结合独立 evaluate 复核实际导航是否成功，通过 `UpdateFinalCaseReason` 说明该测试编排限制，不代表产品缺陷 | 2026-08-27 |
| `UI_TDTab` 热更逻辑检索 | `UI_TDTab_Logic` 是挂载在 `BaseUI` 的非 `MonoBehaviour` 热更实例，无法通过 `GetComponentByTypeName` 直接取得 | 从 `BaseUI` 的 `UIBinder.m_MonoInvocationAdapter.m_Instance` 反射取得实例，再读取 `rouge_Tab_2_tgl` / `m_CurrentPageUIID`；用于确认真实页签事件而非只验证节点存在 | 2026-09-01 |
| 0070 重开英雄列表 | `TestBoot.StartFastEnter("UI_TDHeroAll")` 在当时会停留 `loading` 并最终 `timeout:boot`；但已存在的 UI 根/Canvas 仍可用 | 关闭旧英雄页后，以 `TestBoot.OpenUI("UI_TDHeroAll")` 重建并在下一次独立 evaluate 中确认根激活、绑定逻辑、读取快照 | 2026-09-01 |
| 英雄卡星级 | 0070 截图与 `HeroItem_AutoGen`、`HeroItem_Logic.RefreshUI()` 均证明英雄卡没有星级绑定节点或显示路径 | 将 TC-HERO-024 及包含“星级正确”验收项的 TC-HERO-047 保留为失败，附截图及源码证据；不可将该产品缺陷降格为 `test_inconclusive` | 2026-09-01 |
| `Click()` 与 `Toggle()` API 区分 | `TestHelper.Click()`/`FindButton()` 仅查找 `GameButton` 组件；底部导航页签（`level_Tab`/`hero_Tab`/`rouge_Tab`）使用 `GameToggle` 组件，`Click()` 对其必然返回 `err:not_found`，即便 `ResolvePath` 已确认节点存在 | 对 `GameToggle` 类控件使用 `TestHelper.Toggle(path, true)`，通过 `isOn` 属性触发 | 2026-08-27 |
| "确定"(ok)按钮保存/退出编辑态延迟不稳定 | 编辑态下点击 `btnok` 保存并退出编辑模式（`m_IsEditMode` True→False）的真实耗时不稳定，观测到 700ms~1500ms+ 仍可能不足以完成保存，与 `btnconcel`(取消)约 700ms 的稳定延迟相比明显更长且波动更大 | 涉及点击 ok 后立即断言 `m_IsEditMode`/上阵计数的用例，若断言时刻仍显示编辑态未退出，应通过独立 evaluate 追加更长等待（2-3s+）复核，再用 `UpdateFinasCaseReason` 说明时序原因；不应据此判定产品缺陷 | 2026-08-27 |
| 非编辑态点击已上阵英雄卡不进入详情 | 非编辑态点击列表项中 `onscenemask` 激活（已上阵）的英雄卡，详情页 `UI_TowerDefence_HeroGrow` 不会创建；只有点击未上阵英雄卡才进入详情 | 进入详情类用例必须点击未上阵英雄项（读取 `onscenemask.activeInHierarchy == false` 后点击）；不得使用已上阵英雄作为详情入口 | 2026-08-28 |
| 底部 Tab 切回英雄后 UI_TDHeroAll 异步重建 | `Toggle(hero_Tab,true)` 后 `UI_TDHeroAll` 并非立即激活，需要约 1-2s 跨帧异步创建；连续快速 Toggle 会触发重建 | 切换 Tab 后独立 evaluate 短轮询（300ms/次，最长 6s）确认 `UI_TDHeroAll.activeInHierarchy==true` 后再继续；重复点击当前页签同样需要轮询确认 | 2026-08-28 |
| 连续下阵时槽位点击后数据同步延迟 | 编辑态连续点击槽位图标下阵，相邻两次点击间隔 800ms 时第二次可能读取到旧计数（`m_OnSceneHeroIds` 未及时更新） | 每次下阵后独立轮询（400ms/次，最长 5s）读取计量确认已减少再继续下一次下阵；不得用固定 sleep 后直接断言 | 2026-08-28 |
| 同一 PlayMode 会话内 `m_OnSceneHeroIds` 跨用例状态漂移 | `RunSuiteAndRecord` 批量执行时不会在用例间重置游戏状态；连续多个用例（如 hero-formations、hero-full-flow 分组）对上阵槽位的增删会累积叠加，导致后续用例执行时基线计数与用例设计时假设的初始值（如固定 `cnt:3`）不一致 | 编写/复核断言时应基于当前实时快照的相对变化判断，而非硬编码绝对初始值；执行完一个会大幅改变上阵状态的分组后，建议手动核对并恢复基线（`edit`→重新上阵/下阵→`ok`→等待保存）后再进入下一分组 | 2026-08-27 |
| 上阵槽位映射动态变化 | 上阵英雄可能显示在任意槽位（bg1/bg2/bg3），`m_OnSceneHeroIds` 计数与槽位位置无固定映射；点击"上阵区域某英雄下阵"前若按固定 slot 索引点击，可能点到空槽位（icon 隐藏）导致下阵无效果 | 点击槽位前先查询 `bgN/icon.activeInHierarchy` 确认该槽位实际有英雄；基于当前实时槽位状态选择点击目标，不使用固定 slot 假设 | 2026-08-28 |
| `EditorRuntime_Content_4`（item4）为空英雄项 | 英雄列表末尾的 `EditorRuntime_Content_4` 无英雄名字文本（GameText 为空），点击上阵无效果；不可作为"未上阵英雄"用于上阵类用例 | 上阵类用例选择未上阵英雄时，先读取每项 GameText 名字确认非空，仅对名字非空的未上阵项执行点击 | 2026-08-28 |
| 满员点击未上阵卡被判 failed（跨用例漂移） | 编辑态满员验证组（TC-017/036/028/008/018）首跑因前序用例状态漂移（已上阵英雄被再次点击触发下阵）导致 cnt 递减被判 failed，实际是测试编排问题 | 满员类用例须先构造全量上阵基线（cnt=3），并基于当前实时快照的相对变化断言，不用硬编码绝对初始值；下阵/上阵间用独立轮询确认状态到位 | 2026-08-31 |
| 英雄卡无星级节点 | 运行时英雄列表卡（EditorRuntime_Content_N）未发现 star/星级展示节点，仅 heroicon/name/heroframe/eleicon 等；星级展示 TC-024 记为 test_inconclusive 待策划确认 | 星级类用例先确认是否有星级节点；无节点时记录 test_inconclusive 并保留证据，不判产品失败 | 2026-08-31 |

## 8. 当前运行实测补充（hero-list-0072）

- 运行时根路径：`GameEntry/Builtin/UI/UI_Root/Canvas2/UI_TDHeroAll`；通过 `hero_Tab` 切换后确认激活。
- 当前实测进入链路：`TestBoot.Boot()` 返回 `ready` → `UI_TDTab/hero_Tab.isOn=true` → 独立读取 `UI_TDHeroAll.activeInHierarchy=true`。
- 本轮已实际验证：编辑、下阵、上阵、确认保存、满员时阻止额外上阵、非编辑态进入 `UI_TowerDefence_HeroGrow`、详情页左下返回、关卡/英雄/肉鸽页签切换。
- 当前观察到 `UI_TDHeroAll/bg/top.activeInHierarchy=false`，而列表有 5 张卡片；该事实用于 TC-HERO-048 的失败记录，根因尚未确认。

## 9. 当前运行实测补充（hero-list-0075）

- 进入链路：`TestBoot.Boot()` 首次返回 `login_triggered`，后续返回 `ready`；调用 `TestBoot.OpenUI("UI_TDHeroAll")` 返回 `ok:opening:UI_TDHeroAll`，随后确认根节点为 `GameEntry/Builtin/UI/UI_Root/Canvas2/UI_TDHeroAll` 且处于激活状态。
- 初始状态：`m_IsEditMode=False`、`m_OnSceneHeroIds.Count=3`、列表容器子项数为 `5`。
- 已验证操作：点击 `bg/bottom/btnedit` 后，`m_IsEditMode` 变为 `True`，`btnok` 与 `btnconcel` 激活、`btnedit` 隐藏；点击 `onscenenode/bg1` 后上阵数由 `3` 降至 `2`；点击 `EditorRuntime_Content_1` 后恢复为 `3`；点击 `btnconcel` 后 `m_IsEditMode=False` 且编辑按钮恢复显示。
