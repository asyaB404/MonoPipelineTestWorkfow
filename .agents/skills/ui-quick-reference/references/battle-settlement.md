# battle-settlement - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `battle-settlement` |
| UIID | `UI_BattleResultPanel` |
| UIDes | 战斗结算界面 |
| CanvasIndex | 3 |
| UI 根节点名 | `UI_BattleResultPanel` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_BattleResultPanel` |
| Logic 全限定名 | `HotFix_Project.UI_BattleResultPanel_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_BattleResultPanel`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_BattleResultPanel");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas3/";
var ui = GameObject.Find(root + "UI_BattleResultPanel");
```

## 3. 节点树速查

# Prefab: UI_BattleResultPanel.prefab
# 根节点: UI_BattleResultPanel
# 节点总数: 45
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_BattleResultPanel\win\btn_WinShangHaiTongJi` | `btn_WinShangHaiTongJi_0_btn` | GameButton | btn_jixu_1 |
| `UI_BattleResultPanel\win\btn_WinQueDing` | `btn_WinQueDing_1_btn` | GameButton | btn_shezhi_1 |
| `UI_BattleResultPanel\lose\btn_LoseShangHaiTongJi` | `btn_LoseShangHaiTongJi_2_btn` | GameButton | btn_jixu |
| `UI_BattleResultPanel\lose\btn_LoseQueDing` | `btn_LoseQueDing_3_btn` | GameButton | btn_shezhi |
| `UI_BattleResultPanel\lose\btn_OpenWanJuZhaoHuan` | `btn_OpenWanJuZhaoHuan_4_btn` | GameButton | btn_OpenWanJuZhaoHuan |
| `UI_BattleResultPanel\lose\btn_OpenZhuJiaoPeiYang` | `btn_OpenZhuJiaoPeiYang_5_btn` | GameButton | btn_OpenZhuJiaoPeiYang |
| `UI_BattleResultPanel\lose\btn_WanJuPeiYang` | `btn_WanJuPeiYang_6_btn` | GameButton | btn_WanJuPeiYang |
| `UI_BattleResultPanel\win\Win_LevelName` | `Win_LevelName_0_txt` | GameText | TXT_2_2_46_0_0_2 |
| `UI_BattleResultPanel\win\Win_TongGuoBoCi` | `Win_TongGuoBoCi_1_txt` | GameText | TXT_1_2_40_0_0_1 |
| `UI_BattleResultPanel\lose\Lose_LevelName` | `Lose_LevelName_2_txt` | GameText | TXT_2_2_46_0_0_1 |
| `UI_BattleResultPanel\lose\Lose_TongGuoBoCi` | `Lose_TongGuoBoCi_3_txt` | GameText | TXT_1_2_40_0_0 |
| `UI_BattleResultPanel\win` | `win_0_go` | GameObject | 胜利面板 |
| `UI_BattleResultPanel\lose` | `lose_1_go` | GameObject | 失败面板 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_WinShangHaiTongJi_0_btn` | `UI_BattleResultPanel\win\btn_WinShangHaiTongJi` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_LoseShangHaiTongJi_2_btn` | `UI_BattleResultPanel\lose\btn_LoseShangHaiTongJi` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `btn_LoseQueDing_3_btn` | `UI_BattleResultPanel\lose\btn_LoseQueDing` | `onClick?.Invoke()` | GameUISystem.Inst.RemoveUIPlayOutAnim() |
| `btn_WinQueDing_1_btn` | `UI_BattleResultPanel\win\btn_WinQueDing` | `onClick?.Invoke()` | GameUISystem.Inst.RemoveUIPlayOutAnim() |
| `btn_OpenWanJuZhaoHuan_4_btn` | `UI_BattleResultPanel\lose\btn_OpenWanJuZhaoHuan` | `onClick?.Invoke()` | GameUISystem.Inst.RemoveUIPlayOutAnim() |
| `btn_OpenZhuJiaoPeiYang_5_btn` | `UI_BattleResultPanel\lose\btn_OpenZhuJiaoPeiYang` | `onClick?.Invoke()` | GameUISystem.Inst.RemoveUIPlayOutAnim() |
| `btn_WanJuPeiYang_6_btn` | `UI_BattleResultPanel\lose\btn_WanJuPeiYang` | `onClick?.Invoke()` | GameUISystem.Inst.RemoveUIPlayOutAnim() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_WinShangHaiTongJi_0_btn` | `UI_BattleResultPanel\win\btn_WinShangHaiTongJi` | GameButton | btn_jixu_1 | `真实入口触发后预期打开目标 UI` |
| `btn_WinQueDing_1_btn` | `UI_BattleResultPanel\win\btn_WinQueDing` | GameButton | btn_shezhi_1 | `GameUISystem.Inst.RemoveUIPlayOutAnim()` |
| `btn_LoseShangHaiTongJi_2_btn` | `UI_BattleResultPanel\lose\btn_LoseShangHaiTongJi` | GameButton | btn_jixu | `真实入口触发后预期打开目标 UI` |
| `btn_LoseQueDing_3_btn` | `UI_BattleResultPanel\lose\btn_LoseQueDing` | GameButton | btn_shezhi | `GameUISystem.Inst.RemoveUIPlayOutAnim()` |
| `btn_OpenWanJuZhaoHuan_4_btn` | `UI_BattleResultPanel\lose\btn_OpenWanJuZhaoHuan` | GameButton | btn_OpenWanJuZhaoHuan | `GameUISystem.Inst.RemoveUIPlayOutAnim()` |
| `btn_OpenZhuJiaoPeiYang_5_btn` | `UI_BattleResultPanel\lose\btn_OpenZhuJiaoPeiYang` | GameButton | btn_OpenZhuJiaoPeiYang | `GameUISystem.Inst.RemoveUIPlayOutAnim()` |
| `btn_WanJuPeiYang_6_btn` | `UI_BattleResultPanel\lose\btn_WanJuPeiYang` | GameButton | btn_WanJuPeiYang | `GameUISystem.Inst.RemoveUIPlayOutAnim()` |
| `Win_LevelName_0_txt` | `UI_BattleResultPanel\win\Win_LevelName` | GameText | TXT_2_2_46_0_0_2 | — |
| `Win_TongGuoBoCi_1_txt` | `UI_BattleResultPanel\win\Win_TongGuoBoCi` | GameText | TXT_1_2_40_0_0_1 | — |
| `Lose_LevelName_2_txt` | `UI_BattleResultPanel\lose\Lose_LevelName` | GameText | TXT_2_2_46_0_0_1 | — |
| `Lose_TongGuoBoCi_3_txt` | `UI_BattleResultPanel\lose\Lose_TongGuoBoCi` | GameText | TXT_1_2_40_0_0 | — |
| `win_0_go` | `UI_BattleResultPanel\win` | GameObject | 胜利面板 | — |
| `lose_1_go` | `UI_BattleResultPanel\lose` | GameObject | 失败面板 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_BattleResultPanel_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_BattleResultPanel");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_BattleResultPanel");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_BattleResultPanel");
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
