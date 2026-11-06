# battle-pause - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `battle-pause` |
| UIID | `UI_Battle_Pause` |
| UIDes | 战斗暂停界面 |
| CanvasIndex | 3 |
| UI 根节点名 | `UI_Battle_Pause` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_Battle_Pause` |
| Logic 全限定名 | `HotFix_Project.UI_Battle_Pause_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_Battle_Pause`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_Battle_Backpack_Crafting` | 战斗背包合成界面 | 2 |
| `UI_BattleMain` | 战斗主界面 | 1 |
| `UI_BattleGameRules` | 玩法帮助说明界面 | 3 |
| `UI_Battle_Statistics` | 战斗数据统计界面 | 3 |
| `UI_Battle_SkillSelect` | 战斗技能三选一界面 | 3 |
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
var ui = GameObject.Find("UI_Battle_Pause");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas3/";
var ui = GameObject.Find(root + "UI_Battle_Pause");
```

## 3. 节点树速查

# Prefab: UI_Battle_Pause.prefab
# 根节点: UI_Battle_Pause
# 节点总数: 32
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_Battle_Pause\windows_zanting\btn_jixu` | `btn_jixu_0_btn` | GameButton | btn_jixu |
| `UI_Battle_Pause\windows_zanting\btn_shezhi` | `btn_shezhi_1_btn` | GameButton | btn_shezhi |
| `UI_Battle_Pause\windows_zanting\btn_tuichu` | `btn_tuichu_2_btn` | GameButton | btn_tuichu |
| `UI_Battle_Pause\windows_zanting\CloseBg` | `CloseBg_3_btn` | GameButton | btn_cLOSEbG |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_jixu_0_btn` | `UI_Battle_Pause\windows_zanting\btn_jixu` | `onClick?.Invoke()` | CE_FightSceneFightPause() |
| `CloseBg_3_btn` | `UI_Battle_Pause\windows_zanting\CloseBg` | `onClick?.Invoke()` | CE_FightSceneFightPause() |
| `btn_shezhi_1_btn` | `UI_Battle_Pause\windows_zanting\btn_shezhi` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_tuichu_2_btn` | `UI_Battle_Pause\windows_zanting\btn_tuichu` | `onClick?.Invoke()` | FinishCombat_Common() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_jixu_0_btn` | `UI_Battle_Pause\windows_zanting\btn_jixu` | GameButton | btn_jixu | `CE_FightSceneFightPause()` |
| `btn_shezhi_1_btn` | `UI_Battle_Pause\windows_zanting\btn_shezhi` | GameButton | btn_shezhi | `真实入口触发后预期打开目标 UI` |
| `btn_tuichu_2_btn` | `UI_Battle_Pause\windows_zanting\btn_tuichu` | GameButton | btn_tuichu | `FinishCombat_Common()` |
| `CloseBg_3_btn` | `UI_Battle_Pause\windows_zanting\CloseBg` | GameButton | btn_cLOSEbG | `CE_FightSceneFightPause()` |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_Battle_Pause_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_Battle_Pause");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_Battle_Pause");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_Battle_Pause");
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
