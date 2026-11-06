# hero-cultivate-upgrade - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `hero-cultivate-upgrade` |
| UIID | `UI_Hero_upgrade_page` |
| UIDes | 角色升级页面 |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_Hero_upgrade_page` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Hero_upgrade_page` |
| Logic 全限定名 | `HotFix_Project.UI_Hero_upgrade_page_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_Hero_upgrade_page`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_HeroMainList` | 角色背包界面 | 0 |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_Hero_upgrade_page");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_Hero_upgrade_page");
```

## 3. 节点树速查

# Prefab: UI_Hero_upgrade_page.prefab
# 根节点: UI_Hero_upgrade_page
# 节点总数: 53
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_Hero_upgrade_page\btn_xiayige` | `btn_xiayige_0_btn` | GameButton | 按钮-左切换-点击切换到上一个英雄 |
| `UI_Hero_upgrade_page\btn_shangyige` | `btn_shangyige_1_btn` | GameButton | 按钮-右切换-点击切换到下一个英雄 |
| `UI_Hero_upgrade_page\btn_back` | `btn_back_2_btn` | GameButton | 返回按钮-点击关闭本页面 |
| `UI_Hero_upgrade_page\shengji\shengjiButton` | `shengjiButton_3_btn` | GameButton | 按钮-点击升级 |
| `UI_Hero_upgrade_page\shuxing_group\btn_xiangqing` | `btn_xiangqing_4_btn` | GameButton | 按钮-详情-点击打开详情页面 |
| `UI_Hero_upgrade_page\img_common_hero` | `img_common_hero_0_img` | GameImage | 英雄静态立绘 |
| `UI_Hero_upgrade_page\txt_heroname` | `txt_heroname_0_txt` | GameText | 英雄名字 |
| `UI_Hero_upgrade_page\zhanli\txt_fightscore` | `txt_fightscore_1_txt` | GameText | 战力 |
| `UI_Hero_upgrade_page\shuxing_group\txt_herolevel` | `txt_herolevel_2_txt` | GameText | 英雄等级 |
| `UI_Hero_upgrade_page\zhanli\skill\UC_SkillItem_Hero` | `UC_SkillItem_Hero_0_go` | GameObject | 模板-技能模板 |
| `UI_Hero_upgrade_page\zhanli\skill` | `skill_1_go` | GameObject | 容器-技能容器 |
| `UI_Hero_upgrade_page\costItemes` | `costItemes_2_go` | GameObject | 容器-消耗容器 |
| `UI_Hero_upgrade_page\costItemes\UC_Item_Cost_HeroUpgrade` | `UC_Item_Cost_HeroUpgrade_3_go` | GameObject | 模板-消耗模板 |
| `UI_Hero_upgrade_page\shengji\shengjiButton\Img_btn_common_01huang_1` | `Img_btn_common_01huang_1_4_go` | GameObject | 按钮状态图标-升级-可升级时显示 |
| `UI_Hero_upgrade_page\shengji\shengjiButton\Img_btn_common_01hui` | `Img_btn_common_01hui_5_go` | GameObject | 按钮状态图标-升级-不可升级时显示 |
| `UI_Hero_upgrade_page\tupo\btn_tupo\Img_btn_common_01huang` | `Img_btn_common_01huang_6_go` | GameObject | 按钮状态图标-突破-可突破时显示 |
| `UI_Hero_upgrade_page\shengji\shengjiButton\Img_btn_common_01hui` | `Img_btn_common_01hui_7_go` | GameObject | 按钮状态图标-突破-不可突破时显示 |
| `UI_Hero_upgrade_page\SpineAcPoint` | `SpineAcPoint_8_go` | GameObject | 容器-spine动画的容器 |
| `UI_Hero_upgrade_page\shengji\shengjiButton\TXT_2_2_56_2_0_1` | `TXT_2_2_56_2_0_1_9_go` | GameObject | 升级按钮状态-升级 |
| `UI_Hero_upgrade_page\shengji\shengjiButton\TXT_2_2_56_2_0_2` | `TXT_2_2_56_2_0_2_10_go` | GameObject | 升级按钮状态-已满级 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| — | — | — | — |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_xiayige_0_btn` | `UI_Hero_upgrade_page\btn_xiayige` | GameButton | 按钮-左切换-点击切换到上一个英雄 | — |
| `btn_shangyige_1_btn` | `UI_Hero_upgrade_page\btn_shangyige` | GameButton | 按钮-右切换-点击切换到下一个英雄 | — |
| `btn_back_2_btn` | `UI_Hero_upgrade_page\btn_back` | GameButton | 返回按钮-点击关闭本页面 | — |
| `shengjiButton_3_btn` | `UI_Hero_upgrade_page\shengji\shengjiButton` | GameButton | 按钮-点击升级 | — |
| `btn_xiangqing_4_btn` | `UI_Hero_upgrade_page\shuxing_group\btn_xiangqing` | GameButton | 按钮-详情-点击打开详情页面 | — |
| `img_common_hero_0_img` | `UI_Hero_upgrade_page\img_common_hero` | GameImage | 英雄静态立绘 | — |
| `txt_heroname_0_txt` | `UI_Hero_upgrade_page\txt_heroname` | GameText | 英雄名字 | — |
| `txt_fightscore_1_txt` | `UI_Hero_upgrade_page\zhanli\txt_fightscore` | GameText | 战力 | — |
| `txt_herolevel_2_txt` | `UI_Hero_upgrade_page\shuxing_group\txt_herolevel` | GameText | 英雄等级 | — |
| `UC_SkillItem_Hero_0_go` | `UI_Hero_upgrade_page\zhanli\skill\UC_SkillItem_Hero` | GameObject | 模板-技能模板 | — |
| `skill_1_go` | `UI_Hero_upgrade_page\zhanli\skill` | GameObject | 容器-技能容器 | — |
| `costItemes_2_go` | `UI_Hero_upgrade_page\costItemes` | GameObject | 容器-消耗容器 | — |
| `UC_Item_Cost_HeroUpgrade_3_go` | `UI_Hero_upgrade_page\costItemes\UC_Item_Cost_HeroUpgrade` | GameObject | 模板-消耗模板 | — |
| `Img_btn_common_01huang_1_4_go` | `UI_Hero_upgrade_page\shengji\shengjiButton\Img_btn_common_01huang_1` | GameObject | 按钮状态图标-升级-可升级时显示 | — |
| `Img_btn_common_01hui_5_go` | `UI_Hero_upgrade_page\shengji\shengjiButton\Img_btn_common_01hui` | GameObject | 按钮状态图标-升级-不可升级时显示 | — |
| `Img_btn_common_01huang_6_go` | `UI_Hero_upgrade_page\tupo\btn_tupo\Img_btn_common_01huang` | GameObject | 按钮状态图标-突破-可突破时显示 | — |
| `Img_btn_common_01hui_7_go` | `UI_Hero_upgrade_page\shengji\shengjiButton\Img_btn_common_01hui` | GameObject | 按钮状态图标-突破-不可突破时显示 | — |
| `SpineAcPoint_8_go` | `UI_Hero_upgrade_page\SpineAcPoint` | GameObject | 容器-spine动画的容器 | — |
| `TXT_2_2_56_2_0_1_9_go` | `UI_Hero_upgrade_page\shengji\shengjiButton\TXT_2_2_56_2_0_1` | GameObject | 升级按钮状态-升级 | — |
| `TXT_2_2_56_2_0_2_10_go` | `UI_Hero_upgrade_page\shengji\shengjiButton\TXT_2_2_56_2_0_2` | GameObject | 升级按钮状态-已满级 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `_currentHeroId` | int | — |
| `_currentHeroIndex` | int | — |
| `_isRequesting` | bool | — |
| `_isOpenParamSet` | bool | — |
| `_currentOperateMode` | HeroUpgradeOperateMode | — |
| `_switchableHeroIdList` | List<int> | — |
| `_skillItemObjectList` | List<GameObject> | — |
| `_costItemObjectList` | List<GameObject> | — |
| `_lastCostItemIdList` | List<int> | — |
| `_attrItemObjectList` | List<GameObject> | — |
| `_heroSpineHandle` | UISpineModelHandle | — |
| `_currentSpineModelId` | int | — |
| `_preLevelUpUnlockedSkillIdList` | List<int> | — |
| `_pendingLevelUpHeroId` | int | — |
| `_upgradeButtonState` | UpgradeButtonState | — |
| `_estimatedLevelUpCount` | int | — |
| `_cachedOriginalUpgradeButtonText` | string | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_Hero_upgrade_page_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_Hero_upgrade_page");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_Hero_upgrade_page");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Hero_upgrade_page");
// 根据实际节点补充读取代码
```

## 8. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| — | — | — | — |

## 9. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| — | — | — |
