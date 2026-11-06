# draw-card - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `draw-card` |
| UIID | `UI_DrawCard_Main` |
| UIDes | 抽卡主页面 |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_DrawCard_Main` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_DrawCard_Main` |
| Logic 全限定名 | `HotFix_Project.UI_DrawCard_Main_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_DrawCard_Main`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_DrawCard_RatePreviewView` | 抽卡概率展示页面 | 2 |
| `UI_DrawCard_ResultView` | 抽卡结果页 | 3 |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_DrawCard_Main");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_DrawCard_Main");
```

## 3. 节点树速查

# Prefab: UI_DrawCard_Main.prefab
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取

### AutoGen 绑定组件清单

| 运行时节点名 | 字段名 | 类型 | 注释 |
|-------------|--------|------|------|
| `btn_chouka1` | `btn_chouka1_0_btn` | GameButton |  |
| `btn_chouka2` | `btn_chouka2_1_btn` | GameButton |  |
| `btn_gailv` | `btn_gailv_2_btn` | GameButton |  |
| `btn_chouka` | `btn_chouka_3_btn` | GameButton |  |
| `btn_limittime` | `btn_limittime_4_btn` | GameButton |  |
| `btn_back` | `btn_back_5_btn` | GameButton |  |
| `img_cost_one` | `img_cost_one_0_img` | GameImage |  |
| `img_cost_ten` | `img_cost_ten_1_img` | GameImage |  |
| `TXT_2_16_46_0_0` | `TXT_2_16_46_0_0_0_txt` | GameText |  |
| `txt_costnum_one` | `txt_costnum_one_1_txt` | GameText |  |
| `txt_costnum_ten` | `txt_costnum_ten_2_txt` | GameText |  |
| `normal_1` | `normal_1_0_go` | GameObject |  |
| `xuanzhong_1` | `xuanzhong_1_1_go` | GameObject |  |
| `normal` | `normal_2_go` | GameObject |  |
| `xuanzhong` | `xuanzhong_3_go` | GameObject |  |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀即为 `运行时节点名`。
例如 `btn_chouka1_0_btn` → 运行时节点 `btn_chouka1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点 | 触发方式 | Logic 回调 |
|-------------|-----------|---------|-----------|
| `btn_chouka1_0_btn` | `btn_chouka1` | `onClick?.Invoke()` | OnClickSingleDrawButton() |
| `btn_chouka2_1_btn` | `btn_chouka2` | `onClick?.Invoke()` | OnClickTenDrawButton() |
| `btn_gailv_2_btn` | `btn_gailv` | `onClick?.Invoke()` | OnClickProbabilityButton() |
| `btn_chouka_3_btn` | `btn_chouka` | `onClick?.Invoke()` | OnClickNormalTabButton() |
| `btn_limittime_4_btn` | `btn_limittime` | `onClick?.Invoke()` | OnClickLimitedTabButton() |
| `btn_back_5_btn` | `btn_back` | `onClick?.Invoke()` | OnClickBackButton() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名 | 类型 | 注释 |
|--------|-------------|------|------|
| `btn_chouka1_0_btn` | `btn_chouka1` | GameButton |  |
| `btn_chouka2_1_btn` | `btn_chouka2` | GameButton |  |
| `btn_gailv_2_btn` | `btn_gailv` | GameButton |  |
| `btn_chouka_3_btn` | `btn_chouka` | GameButton |  |
| `btn_limittime_4_btn` | `btn_limittime` | GameButton |  |
| `btn_back_5_btn` | `btn_back` | GameButton |  |
| `img_cost_one_0_img` | `img_cost_one` | GameImage |  |
| `img_cost_ten_1_img` | `img_cost_ten` | GameImage |  |
| `TXT_2_16_46_0_0_0_txt` | `TXT_2_16_46_0_0` | GameText |  |
| `txt_costnum_one_1_txt` | `txt_costnum_one` | GameText |  |
| `txt_costnum_ten_2_txt` | `txt_costnum_ten` | GameText |  |
| `normal_1_0_go` | `normal_1` | GameObject |  |
| `xuanzhong_1_1_go` | `xuanzhong_1` | GameObject |  |
| `normal_2_go` | `normal` | GameObject |  |
| `xuanzhong_3_go` | `xuanzhong` | GameObject |  |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_DrawCard_Main_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_DrawCard_Main");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_DrawCard_Main");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_DrawCard_Main");
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
