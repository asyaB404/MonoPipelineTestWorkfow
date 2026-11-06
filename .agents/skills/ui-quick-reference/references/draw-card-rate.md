# draw-card-rate - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `draw-card-rate` |
| UIID | `UI_DrawCard_RatePreviewView` |
| UIDes | 抽卡概率展示页面 |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_DrawCard_RatePreviewView` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_DrawCard_RatePreviewView` |
| Logic 全限定名 | `HotFix_Project.UI_DrawCard_RatePreviewView_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_DrawCard_RatePreviewView`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_DrawCard_Main` | 抽卡主页面 | 2 |
| `UI_DrawCard_ResultView` | 抽卡结果页 | 3 |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_DrawCard_RatePreviewView");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_DrawCard_RatePreviewView");
```

## 3. 节点树速查

# Prefab: UI_DrawCard_RatePreviewView.prefab
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取

### AutoGen 绑定组件清单

| 运行时节点名 | 字段名 | 类型 | 注释 |
|-------------|--------|------|------|
| `btn_close` | `btn_close_0_btn` | GameButton |  |
| `TXT_2_5_46_0_0` | `TXT_2_5_46_0_0_0_txt` | GameText |  |
| `TXT_2_5_46_0_0` | `TXT_2_5_46_0_0_1_txt` | GameText |  |
| `TXT_2_5_46_0_0` | `TXT_2_5_46_0_0_2_txt` | GameText |  |
| `TXT_2_5_46_0_0` | `TXT_2_5_46_0_0_3_txt` | GameText |  |
| `Pre_wanju_daka` | `Pre_wanju_daka_0_go` | GameObject |  |
| `Container_Card` | `Container_Card_1_go` | GameObject |  |
| `Container_Card` | `Container_Card_2_go` | GameObject |  |
| `Container_Card` | `Container_Card_3_go` | GameObject |  |
| `Container_Card` | `Container_Card_4_go` | GameObject |  |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀即为 `运行时节点名`。
例如 `btn_chouka1_0_btn` → 运行时节点 `btn_chouka1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点 | 触发方式 | Logic 回调 |
|-------------|-----------|---------|-----------|
| `btn_close_0_btn` | `btn_close` | `onClick?.Invoke()` | OnClickCloseButton() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名 | 类型 | 注释 |
|--------|-------------|------|------|
| `btn_close_0_btn` | `btn_close` | GameButton |  |
| `TXT_2_5_46_0_0_0_txt` | `TXT_2_5_46_0_0` | GameText |  |
| `TXT_2_5_46_0_0_1_txt` | `TXT_2_5_46_0_0` | GameText |  |
| `TXT_2_5_46_0_0_2_txt` | `TXT_2_5_46_0_0` | GameText |  |
| `TXT_2_5_46_0_0_3_txt` | `TXT_2_5_46_0_0` | GameText |  |
| `Pre_wanju_daka_0_go` | `Pre_wanju_daka` | GameObject |  |
| `Container_Card_1_go` | `Container_Card` | GameObject |  |
| `Container_Card_2_go` | `Container_Card` | GameObject |  |
| `Container_Card_3_go` | `Container_Card` | GameObject |  |
| `Container_Card_4_go` | `Container_Card` | GameObject |  |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_DrawCard_RatePreviewView_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_DrawCard_RatePreviewView");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_DrawCard_RatePreviewView");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_DrawCard_RatePreviewView");
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
