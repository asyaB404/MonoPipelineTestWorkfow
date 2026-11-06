# battle-main - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `battle-main` |
| UIID | `UI_BattleMain` |
| UIDes | 战斗主界面 |
| CanvasIndex | 1 |
| UI 根节点名 | `UI_BattleMain` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas1/UI_BattleMain` |
| Logic 全限定名 | `HotFix_Project.UI_BattleMain_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_BattleMain`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_BattleMain");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas1/";
var ui = GameObject.Find(root + "UI_BattleMain");
```

## 3. 节点树速查

# Prefab: UI_BattleMain.prefab
# 根节点: UI_BattleMain
# 节点总数: 56
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_BattleMain\btn_zanting` | `btn_zanting_0_btn` | GameButton | btn_zanting |
| `UI_BattleMain\btn_shuju` | `btn_shuju_1_btn` | GameButton | btn_shuju |
| `UI_BattleMain\btn_tishi` | `btn_tishi_2_btn` | GameButton | btn_tishi |
| `UI_BattleMain\btn_beisu` | `btn_beisu_3_btn` | GameButton | btn_beisu |
| `UI_BattleMain\btn_jingxi` | `btn_jingxi_4_btn` | GameButton | btn_jingxi |
| `UI_BattleMain\btn_beisu\img_speed` | `img_speed_0_img` | GameImage | 倍数 |
| `UI_BattleMain\dengji_group\Img_battle_dengjidi\TXT_level` | `TXT_level_0_txt` | GameText | 等级 |
| `UI_BattleMain\boci_group\TXT_wave` | `TXT_wave_1_txt` | GameText | 波次 |
| `UI_BattleMain\boci_group\daojishi_group\TXT_time` | `TXT_time_2_txt` | GameText | ⌚️时间 |
| `UI_BattleMain\btn_jingxi\TXT_BaoXiang_Number` | `TXT_BaoXiang_Number_3_txt` | GameText | 惊喜奖励数量文本 |
| `UI_BattleMain\MyTransRoot\MySpineRoot` | `MySpineRoot_0_go` | GameObject | 我方spine挂点 |
| `UI_BattleMain\EnemyTransRoot\EnemySpineRoot` | `EnemySpineRoot_1_go` | GameObject | 敌方spine挂点 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_tishi_2_btn` | `UI_BattleMain\btn_tishi` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_zanting_0_btn` | `UI_BattleMain\btn_zanting` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_shuju_1_btn` | `UI_BattleMain\btn_shuju` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_jingxi_4_btn` | `UI_BattleMain\btn_jingxi` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_zanting_0_btn` | `UI_BattleMain\btn_zanting` | GameButton | btn_zanting | `真实入口触发后预期打开目标 UI` |
| `btn_shuju_1_btn` | `UI_BattleMain\btn_shuju` | GameButton | btn_shuju | `真实入口触发后预期打开目标 UI` |
| `btn_tishi_2_btn` | `UI_BattleMain\btn_tishi` | GameButton | btn_tishi | `真实入口触发后预期打开目标 UI` |
| `btn_beisu_3_btn` | `UI_BattleMain\btn_beisu` | GameButton | btn_beisu | — |
| `btn_jingxi_4_btn` | `UI_BattleMain\btn_jingxi` | GameButton | btn_jingxi | `真实入口触发后预期打开目标 UI` |
| `img_speed_0_img` | `UI_BattleMain\btn_beisu\img_speed` | GameImage | 倍数 | — |
| `TXT_level_0_txt` | `UI_BattleMain\dengji_group\Img_battle_dengjidi\TXT_level` | GameText | 等级 | — |
| `TXT_wave_1_txt` | `UI_BattleMain\boci_group\TXT_wave` | GameText | 波次 | — |
| `TXT_time_2_txt` | `UI_BattleMain\boci_group\daojishi_group\TXT_time` | GameText | ⌚️时间 | — |
| `TXT_BaoXiang_Number_3_txt` | `UI_BattleMain\btn_jingxi\TXT_BaoXiang_Number` | GameText | 惊喜奖励数量文本 | — |
| `MySpineRoot_0_go` | `UI_BattleMain\MyTransRoot\MySpineRoot` | GameObject | 我方spine挂点 | — |
| `EnemySpineRoot_1_go` | `UI_BattleMain\EnemyTransRoot\EnemySpineRoot` | GameObject | 敌方spine挂点 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `m_ExpTween` | Tweener | — |
| `m_ExpTweenEnergy` | Tweener | — |
| `m_OldExp` | int | — |
| `m_OldEnergy` | int | — |
| `m_UITimeId` | long | — |
| `m_TimeTextCount` | int | — |
| `m_IsStatue` | bool | — |
| `_mySpineHandle` | UISpineModelHandle | — |
| `_enemySpineHandle` | UISpineModelHandle | — |
| `_currentMySpineModelId` | int | — |
| `_currentEnemySpineModelId` | int | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_BattleMain_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_BattleMain");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_BattleMain");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas1/UI_BattleMain");
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
