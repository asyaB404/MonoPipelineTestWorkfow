# battle_pass_reward_preview - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `battle_pass_reward_preview` |
| UIID | `UI_MainPassRewardPreview` |
| UIDes | 战令奖励预览 |
| CanvasIndex | 3 |
| UI 根节点名 | `UI_MainPassRewardPreview` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_MainPassRewardPreview` |
| Logic 全限定名 | `HotFix_Project.UI_MainPassRewardPreview_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_MainPassRewardPreview`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_MainPassRewardPreview");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas3/";
var ui = GameObject.Find(root + "UI_MainPassRewardPreview");
```

## 3. 节点树速查

# Prefab: UI_MainPassRewardPreview.prefab
# 根节点: UI_MainPassRewardPreview
# 节点总数: 12
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_MainPassRewardPreview\tc_small\btn_close` | `btn_close_0_btn` | GameButton | btn_close |
| `UI_MainPassRewardPreview\tc_small\btn_close\img_btn_common_close` | `img_btn_common_close_0_img` | GameImage | img_btn_common_close |
| `UI_MainPassRewardPreview\tc_small\tTitle` | `tTitle_0_txt` | GameText | 标题 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_close_0_btn` | `UI_MainPassRewardPreview\tc_small\btn_close` | `onClick?.Invoke()` | GameUISystem.Inst.RemoveUIImmediate() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_close_0_btn` | `UI_MainPassRewardPreview\tc_small\btn_close` | GameButton | btn_close | `GameUISystem.Inst.RemoveUIImmediate()` |
| `img_btn_common_close_0_img` | `UI_MainPassRewardPreview\tc_small\btn_close\img_btn_common_close` | GameImage | img_btn_common_close | — |
| `tTitle_0_txt` | `UI_MainPassRewardPreview\tc_small\tTitle` | GameText | 标题 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `m_MergedRewardList` | List<PBDropItemDataInfo> | — |
| `m_EmptyItemList` | List<CommondAwardItem_Logic> | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_MainPassRewardPreview_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_MainPassRewardPreview");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_MainPassRewardPreview");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_MainPassRewardPreview");
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
