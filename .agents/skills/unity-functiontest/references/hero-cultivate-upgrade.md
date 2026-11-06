# hero-cultivate-upgrade - Unity 运行时 UI 参考

> 本文件由 `unity-functiontest` 在本轮实测后增量维护，只记录本轮 Unity 运行时已验证的事实。技术标识（UI 名称、节点路径、类名、字段名）保持原样并补充中文语义解释。
> 本轮运行目录：`Doc/AI开发文档/output/hero-cultivate-upgrade/hero-cultivate-upgrade-0003`。

## 1. 目标 UI 与运行时根路径

| 项目 | 值 | 中文语义 |
|------|-----|---------|
| 离线 feature_id | `hero-cultivate-upgrade` | 主角养成-升级功能 |
| 角色列表 UI 根 | `UI_HeroMainList` | 角色（英雄）列表界面 |
| 角色列表完整路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_HeroMainList` | 运行时实测父链 |
| 角色详情 UI 根 | `UI_Hero_upgrade_page` | 角色升级详情界面 |
| 角色详情完整路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Hero_upgrade_page` | 运行时实测父链 |
| 角色列表 Logic | `HotFix_Project.UI_HeroMainList_Logic` | 角色列表逻辑类 |
| 角色详情 Logic | `HotFix_Project.UI_Hero_upgrade_page_Logic` | 角色升级逻辑类 |

## 2. 实际进入方式与前置要求

1. 通过 `CyStarRoad.Test.TestBoot.Boot()` 触发前置登录；返回 `login_triggered` 时继续独立轮询，确认 `UI_LoginGame` 消失且 `UI_Main` 激活即为进入大厅。
2. 底部导航栏 `UI_MainBottom` 中「织梦者」页签对应 `MainHomeController.MainTabId.Engineer`，其 `UIId = UI_HeroMainList`。该页签受功能开关 `UnlockId=18` 限制，本轮实测 `FunctionOpenMgr.IsInst.IsFunctionOpen(18)` 返回 `false`，因此通过 `MainHomeController.Inst.OpenTab(Engineer)` 或底部按钮点击**不会**打开角色列表。
3. 本轮实际有效进入方式为 `CyStarRoad.Test.TestBoot.OpenUI("UI_HeroMainList")`（绕过主导航手动进入）。返回 `ok:opening:UI_HeroMainList`，随后独立轮询 `GameObject.Find("UI_HeroMainList")`。
4. 由角色列表进入角色详情：路径 `UI_HeroMainList/UC_HeroList_Page/ScrollView/Viewport/Content/EditorRuntime_Content_{N}/GoButton`，点击 `GoButton` 的 `GameButton.ExecuteButtonClick()`；`GameButton` 节点本身 `onClick` 为空，必须点 `GoButton`。
   - 进入详情前需校验列表项业务守卫：`txt_name`、`jindutiao/txt_suipian`（碎片数）可读；本轮 `EditorRuntime_Content_0=白雪公主`（已上阵）、`EditorRuntime_Content_1=红皇后`（未解锁）。

## 3. 已验证控件路径与触发方式

### 3.1 角色列表 UI_HeroMainList

| 控件语义 | 运行时节点路径（相对 UI 根） | 组件 | 触发方式 |
|---------|---------------------------|------|---------|
| 角色列表容器 | `UC_HeroList_Page/ScrollView/Viewport/Content` | — | 读取 `childCount`，本轮为 2 |
| 角色项 | `UC_HeroList_Page/ScrollView/Viewport/Content/EditorRuntime_Content_{N}` | — | N 从 0 起 |
| 角色名称 | `.../EditorRuntime_Content_{N}/txt_name` | GameText | 只读 |
| 上阵标签 | `.../EditorRuntime_Content_{N}/txt_state` | GameText | 已上阵时 `activeInHierarchy=true` 且文本为「已上阵」 |
| 等级/碎片 | `.../jindutiao/wanju_dengji/txt_level`、`.../jindutiao/txt_suipian` | GameText | 只读 |
| 进入详情按钮 | `.../EditorRuntime_Content_{N}/GoButton` | GameButton | `ExecuteButtonClick()` |

### 3.2 角色详情 UI_Hero_upgrade_page

| 控件语义 | 运行时节点路径（相对 UI 根） | 组件 | 触发方式 |
|---------|---------------------------|------|---------|
| 英雄名称 | `TopInfo/Bigbg_zhujue_mingzidi/txt_heroname` | GameText | 只读 |
| 切换上一个英雄 | `TopInfo/btn_xiayige` | GameButton | `ExecuteButtonClick()` |
| 切换下一个英雄 | `TopInfo/btn_shangyige` | GameButton | `ExecuteButtonClick()` |
| 皮肤按钮 | `TopInfo/btn_pifu` | GameButton | `ExecuteButtonClick()` |
| 英雄等级 | `BottomBg/shuxing_group/txt_herolevel` | GameText | 只读，格式 `Lv N` |
| 战力 | `BottomBg/zhanli/bigbg_common_zhanlidi/txt_fightscore` | GameText | 只读 |
| 属性项 | `BottomBg/shuxing_group/ScrollView/Viewport/Content/Item{N}/GameObject/txt_name`、`txt_value` | GameText | 只读 |
| 属性详情按钮 | `BottomBg/shuxing_group/btn_xiangqing` | GameButton | `ExecuteButtonClick()` 打开 `UI_AttributeOverview` |
| 技能容器 | `BottomBg/zhanli/skill` | — | 子节点为 `UC_SkillItem_Hero` / `UC_SkillItem_Hero(Clone)` |
| 技能项 | `BottomBg/zhanli/skill/UC_SkillItem_Hero(Clone)` | 含 GameButton | 技能图标可点击，名称 `UC_SkillItem_Common/txt_name` |
| 升级按钮 | `BottomBg/UnLock_Buttom_Node/shengji/shengjiButton` | GameButton | `ExecuteButtonClick()`；`useLongPress=true`，`onLongPress` 已绑定 |
| 升级按钮高亮态 | `.../shengjiButton/Img_btn_common_01huang_1` | GameObject | 可升级时 `activeInHierarchy=true` |
| 升级按钮置灰态 | `.../shengjiButton/Img_btn_common_01hui` | GameObject | 不可升级时显示 |
| 已满级态 | `.../shengjiButton/Img_btn_common_01hui_maji` | GameObject | 满级时显示，文本 `TXT_2_2_56_2_0_2=已满级` |
| 升级文本 | `.../shengjiButton/Img_btn_common_01huang_1/TXT_2_2_56_2_0_1` | GameObject | 文本「升级」 |
| 突破按钮 | `BottomBg/UnLock_Buttom_Node/tupo/btn_tupo` | GameButton | 本轮 `tupo` 节点 `activeInHierarchy=false` |
| 消耗容器 | `BottomBg/UnLock_Buttom_Node/costItemes` | — | 子项 `UC_Item_Cost_HeroUpgrade(Clone)` |
| 消耗数量 | `.../costItemes/UC_Item_Cost_HeroUpgrade(Clone)/TXT_1_19_36_6_0` | GameText | 富文本 `存量/所需`，存量足够为白色，不足为 `#FF6D41` 红 |
| 锁定操作区 | `BottomBg/Lock_Buttom_Node` | — | 未解锁英雄时激活，文本「通过主线奖励获得」「去获取」 |
| 未锁定操作区 | `BottomBg/UnLock_Buttom_Node` | — | 已解锁英雄时激活 |
| 返回按钮 | `BottomBg/...`/`btn_back` | GameButton | `ExecuteButtonClick()` 关闭详情页 |
| 特效容器 | `SpineAcPoint` | GameObject | 升级特效锚点 |

## 4. Logic 关键字段（反射读取）

| 字段名 | 类型 | 运行时语义 |
|--------|------|-----------|
| `_currentHeroId` | int | 当前展示英雄 ID，本轮为 `1`（白雪公主） |
| `_upgradeButtonState` | enum `UpgradeButtonState` | 升级按钮状态机；空闲为 `Idle`，单次升级 `SingleUpgrading`，连升 `ContinuousUpgrading` |

读取方式（缓存 bind）：
`TestHelper.Bind("HotFix_Project.UI_Hero_upgrade_page_Logic", "UI_Hero_upgrade_page")` → `TestHelper.CheckBoundUiReady()`。

## 5. 操作后的状态验证方式

- 升级是否成功：读取 `BottomBg/shuxing_group/txt_herolevel`，`Lv N` 数值增加即成功；本轮实测 `Lv 12 → Lv 13`。
- 升级按钮是否可点：读取 `shengjiButton` 的 `interactable` 与 `Img_btn_common_01huang_1` / `Img_btn_common_01hui` 激活状态。
- 详情按钮展开：点击 `btn_xiangqing` 后独立轮询 `GameObject.Find("UI_AttributeOverview")` 是否 `activeInHierarchy`。
- 并发点击一致性：连续触发 `shengjiButton` 10 次，等级仅 +1（`Lv 41 → Lv 42`），`_upgradeButtonState` 回到 `Idle`，证明状态机对并发有保护。

## 6. 已知问题与有效兜底

| 节点/入口 | 症状 | 有效兜底方案 | 确认日期 |
|-----------|------|-------------|---------|
| 底部「织梦者」页签 | `FunctionOpenMgr.IsFunctionOpen(18)=false`，`OpenTab(Engineer)` 与按钮点击均不打开 `UI_HeroMainList` | 使用 `TestBoot.OpenUI("UI_HeroMainList")` 直接打开 | 2026-09-23 |
| 角色列表项 GameButton | `EditorRuntime_Content_N/GameButton` 的 `onClick` 为空，点击无响应 | 点击同级的 `GoButton` | 2026-09-23 |
| 角色详情页出战入口 | `UI_Hero_upgrade_page` 实际结构中不存在出战按钮或出战中文本节点 | 本轮无法在详情页执行出战切换；相关用例记为 `test_inconclusive` | 2026-09-23 |
| `mcp__mymcp__execute_compile` | 首次调用返回 `MCP error -32001 Request timed out`（60s） | 经 `evaluate` 调用 `UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation()` + `AssetDatabase.Refresh()` 触发编译，再轮询 `EditorApplication.isCompiling` 变为 `False` 确认编译完成 | 2026-09-23 |

## 7. 用例分组建议（本轮实际执行）

| 分组 | 用例 | 说明 |
|------|------|------|
| `group-entry` | TC-ENTRY-001/002/003 | 主界面入口进入角色列表，共享一次 `TestBoot.OpenUI` |
| `group-list` | TC-LIST-001..006 | 角色列表初态，共享一次列表状态读取 |
| `group-detail` | TC-DETAIL-001..010 | 角色详情基础信息，共享一次详情页读取 |
| `group-skill` | TC-SKILL-001..010 | 技能区域展示与交互 |
| `group-upgrade` | TC-UPGRADE-001..012 | 升级按钮状态、单次升级、长按、特效 |
| `group-break` | TC-BREAK-001..006 | 突破与满级（本轮无可构造前置） |
| `group-unlock` | TC-UNLOCK-001..004 | 技能解锁/升级提示弹窗 |
| `group-battle` | TC-BATTLE-001..006 | 出战按钮（详情页无该入口） |
| `group-exc` | TC-EXC-001/002/003 | 断网、并发、边界道具 |
