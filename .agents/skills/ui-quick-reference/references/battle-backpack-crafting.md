# battle-backpack-crafting - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `battle-backpack-crafting` |
| UIID | `UI_Battle_Backpack_Crafting` |
| UIDes | 战斗背包合成界面 |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_Battle_Backpack_Crafting` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Battle_Backpack_Crafting` |
| Logic 全限定名 | `HotFix_Project.UI_Battle_Backpack_Crafting_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_Battle_Backpack_Crafting`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_BattleMain` | 战斗主界面 | 1 |
| `UI_BattleGameRules` | 玩法帮助说明界面 | 3 |
| `UI_Battle_Statistics` | 战斗数据统计界面 | 3 |
| `UI_Battle_SkillSelect` | 战斗技能三选一界面 | 3 |
| `UI_Battle_Pause` | 战斗暂停界面 | 3 |
| `UI_Battle_Pause_SkillInfo` | 战斗暂停技能弹窗展示界面 | 3 |
| `UI_Battle_Pause_Settings` | 战斗暂停游戏设置界面 | 3 |
| `UI_BattleResultPanel` | 战斗结算界面 | 3 |
| `UI_BattleResult_DamageStatsPanel` | 战斗结算_伤害统计界面 | 3 |
| `UI_Battle_Backpack_ToyTips` | 【弹窗】战斗背包合成界面_玩具信息Tips | 2 |
| `UI_Battle_Slot_Panel` | 战斗老虎机界面 | 1 |
| `UI_StartBattlePanel` | 战斗界面战斗开始动画面板 | 1 |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_Battle_Backpack_Crafting");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_Battle_Backpack_Crafting");
```

## 3. 节点树速查

# Prefab: UI_Battle_Backpack_Crafting.prefab
# 根节点: UI_Battle_Backpack_Crafting
# 节点总数: 107
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_Battle_Backpack_Crafting\gongchegnshi_group\btn_zhankai` | `btn_zhankai_0_btn` | GameButton | btn_zhankai |
| `UI_Battle_Backpack_Crafting\Bg\btn_peifang` | `btn_peifang_1_btn` | GameButton | btn_peifang |
| `UI_Battle_Backpack_Crafting\Bg\btn_kuaisu` | `btn_kuaisu_2_btn` | GameButton | btn_kuaisu |
| `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin` | `btn_shuaxin_3_btn` | GameButton | btn_shuaxin |
| `UI_Battle_Backpack_Crafting\Bg\btn_kaizhan` | `btn_kaizhan_4_btn` | GameButton | btn_kaizhan |
| `UI_Battle_Backpack_Crafting\peifang_group_1\tc_middle\btn_peifang_close` | `btn_peifang_close_5_btn` | GameButton | 配方关闭按钮 |
| `UI_Battle_Backpack_Crafting\btn_zanting` | `btn_zanting_6_btn` | GameButton | 暂停 |
| `UI_Battle_Backpack_Crafting\Bg\btn_zajiao` | `btn_zajiao_7_btn` | GameButton | 快速杂交按钮 |
| `UI_Battle_Backpack_Crafting\Bg\btn_zajiao\ZaJiaoIcon` | `ZaJiaoIcon_0_img` | GameImage | 杂交对象Icon |
| `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin\bukeshuaxin\xiaohao_group\shuaxinXiaoHaoJinbiCount_TXT` | `shuaxinXiaoHaoJinbiCount_TXT_0_txt` | GameText | 刷新会消耗多少金币显示文本(可刷新按钮上的) |
| `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin\bukeshuaxin\xiaohao_group\shuaxinXiaoHaoJinbiCount_TXT` | `shuaxinXiaoHaoJinbiCount_TXT_1_txt` | GameText | 刷新会消耗多少金币显示文本(不可刷新按钮上的) |
| `UI_Battle_Backpack_Crafting\ziyuan_group\JinBiCount_TXT` | `JinBiCount_TXT_2_txt` | GameText | 显示当前金币的文本 |
| `UI_Battle_Backpack_Crafting\Bg\WanJuList` | `WanJuList_0_go` | GameObject | WanJuList |
| `UI_Battle_Backpack_Crafting\Bg\qipan_group\TitleParent` | `TitleParent_1_go` | GameObject | TitleParent |
| `UI_Battle_Backpack_Crafting\Bg\qipan_group\gezi` | `gezi_2_go` | GameObject | TilePrefab |
| `UI_Battle_Backpack_Crafting\Bg\PeiFangWanJuList` | `PeiFangWanJuList_3_go` | GameObject | PeiFangWanJuList |
| `UI_Battle_Backpack_Crafting\peifang_group_1` | `peifang_group_1_4_go` | GameObject | 玩家配方面板 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_shuaxin_3_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin` | `onClick?.Invoke()` | GetBattleMoney() |
| `btn_kuaisu_2_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_kuaisu` | `onClick?.Invoke()` | BatchUpgrade() |
| `btn_peifang_1_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_peifang` | `onClick?.Invoke()` | SetAsLastSibling() |
| `btn_zanting_6_btn` | `UI_Battle_Backpack_Crafting\btn_zanting` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_zajiao_7_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_zajiao` | `onClick?.Invoke()` | RefreshZajiaoButton() |
| `btn_peifang_close_5_btn` | `UI_Battle_Backpack_Crafting\peifang_group_1\tc_middle\btn_peifang_close` | `onClick?.Invoke()` | peifang_group_1_4_go.SetActive() |
| `btn_kaizhan_4_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_kaizhan` | `onClick?.Invoke()` | gameObject.SetActive() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_zhankai_0_btn` | `UI_Battle_Backpack_Crafting\gongchegnshi_group\btn_zhankai` | GameButton | btn_zhankai | — |
| `btn_peifang_1_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_peifang` | GameButton | btn_peifang | `SetAsLastSibling()` |
| `btn_kuaisu_2_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_kuaisu` | GameButton | btn_kuaisu | `BatchUpgrade()` |
| `btn_shuaxin_3_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin` | GameButton | btn_shuaxin | `GetBattleMoney()` |
| `btn_kaizhan_4_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_kaizhan` | GameButton | btn_kaizhan | `gameObject.SetActive()` |
| `btn_peifang_close_5_btn` | `UI_Battle_Backpack_Crafting\peifang_group_1\tc_middle\btn_peifang_close` | GameButton | 配方关闭按钮 | `peifang_group_1_4_go.SetActive()` |
| `btn_zanting_6_btn` | `UI_Battle_Backpack_Crafting\btn_zanting` | GameButton | 暂停 | `真实入口触发后预期打开目标 UI` |
| `btn_zajiao_7_btn` | `UI_Battle_Backpack_Crafting\Bg\btn_zajiao` | GameButton | 快速杂交按钮 | `RefreshZajiaoButton()` |
| `ZaJiaoIcon_0_img` | `UI_Battle_Backpack_Crafting\Bg\btn_zajiao\ZaJiaoIcon` | GameImage | 杂交对象Icon | — |
| `shuaxinXiaoHaoJinbiCount_TXT_0_txt` | `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin\bukeshuaxin\xiaohao_group\shuaxinXiaoHaoJinbiCount_TXT` | GameText | 刷新会消耗多少金币显示文本(可刷新按钮上的) | — |
| `shuaxinXiaoHaoJinbiCount_TXT_1_txt` | `UI_Battle_Backpack_Crafting\Bg\btn_shuaxin\bukeshuaxin\xiaohao_group\shuaxinXiaoHaoJinbiCount_TXT` | GameText | 刷新会消耗多少金币显示文本(不可刷新按钮上的) | — |
| `JinBiCount_TXT_2_txt` | `UI_Battle_Backpack_Crafting\ziyuan_group\JinBiCount_TXT` | GameText | 显示当前金币的文本 | — |
| `WanJuList_0_go` | `UI_Battle_Backpack_Crafting\Bg\WanJuList` | GameObject | WanJuList | — |
| `TitleParent_1_go` | `UI_Battle_Backpack_Crafting\Bg\qipan_group\TitleParent` | GameObject | TitleParent | — |
| `gezi_2_go` | `UI_Battle_Backpack_Crafting\Bg\qipan_group\gezi` | GameObject | TilePrefab | — |
| `PeiFangWanJuList_3_go` | `UI_Battle_Backpack_Crafting\Bg\PeiFangWanJuList` | GameObject | PeiFangWanJuList | — |
| `peifang_group_1_4_go` | `UI_Battle_Backpack_Crafting\peifang_group_1` | GameObject | 玩家配方面板 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `m_BoardStateChangedListener` | EventListener | — |
| `m_QuickMergeAvailabilityListener` | EventListener | — |
| `m_SpawnCompletedListener` | EventListener | — |
| `m_MyCampSpawnSourcesChangedListener` | EventListener | — |
| `m_ToyDataChangedListener` | EventListener | — |
| `m_PendingDynamicPrefabLoadCount` | int | — |
| `m_IsRuntimeInitialized` | bool | — |
| `m_IsDestroyed` | bool | — |
| `GridTypeDic` | Dictionary<int, GameObject> | — |
| `m_StageSlotGridIdSet` | HashSet<int> | — |
| `m_IsRecipePanelInitialized` | bool | — |
| `m_RecipeItemLogicList` | List<ite_peifang_Logic> | — |
| `RecipeTypeDic` | Dictionary<int, GameObject> | — |
| `m_SpawnPreviewPrefabCache` | Dictionary<int, GameObject> | — |
| `m_SpawnPreviewLoadingToyIds` | HashSet<int> | — |
| `m_SpawnPreviewFailedToyIds` | HashSet<int> | — |
| `m_SpawnPreviewItemToyIdMap` | Dictionary<GameObject, int> | — |
| `m_ActiveSpawnPreviewItems` | List<GameObject> | — |
| `m_SpawnPreviewVisualCacheMap` | Dictionary<GameObject, SpawnPreviewVisualCache> | — |
| `m_SpawnPreviewRebuildWhenLoadCompleted` | bool | — |
| `m_RefreshGoldCost` | int | — |
| `m_CurrentZajiaoToyId` | int | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_Battle_Backpack_Crafting_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_Battle_Backpack_Crafting");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_Battle_Backpack_Crafting");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Battle_Backpack_Crafting");
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
