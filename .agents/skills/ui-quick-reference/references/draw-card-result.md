# draw-card-result - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `draw-card-result` |
| UIID | `UI_DrawCard_ResultView` |
| UIDes | 抽卡结果页 |
| CanvasIndex | 3 |
| UI 根节点名 | `UI_DrawCard_ResultView` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_DrawCard_ResultView` |
| Logic 全限定名 | `HotFix_Project.UI_DrawCard_ResultView_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_DrawCard_ResultView`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_DrawCard_Main` | 抽卡主页面 | 2 |
| `UI_DrawCard_RatePreviewView` | 抽卡概率展示页面 | 2 |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_DrawCard_ResultView");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas3/";
var ui = GameObject.Find(root + "UI_DrawCard_ResultView");
```

## 3. 节点树速查

# Prefab: UI_DrawCard_ResultView.prefab
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取

### AutoGen 绑定组件清单

| 运行时节点名 | 字段名 | 类型 | 注释 |
|-------------|--------|------|------|
| `btn_chouka1` | `btn_chouka1_0_btn` | GameButton |  |
| `btn_chouka2` | `btn_chouka2_1_btn` | GameButton |  |
| `BGCloseBtn` | `BGCloseBtn_2_btn` | GameButton |  |
| `UD_ZiYuan_test1_1` | `UD_ZiYuan_test1_1_0_img` | GameImage |  |
| `UD_ZiYuan_test1` | `UD_ZiYuan_test1_1_img` | GameImage |  |
| `TXT_1_2_30_0_0_1` | `TXT_1_2_30_0_0_1_0_txt` | GameText |  |
| `TXT_1_2_30_0_0` | `TXT_1_2_30_0_0_1_txt` | GameText |  |
| `danchou_group` | `danchou_group_0_go` | GameObject |  |
| `pos` | `pos_1_go` | GameObject |  |
| `shilian_group` | `shilian_group_2_go` | GameObject |  |
| `Pre_wanju_daka` | `Pre_wanju_daka_3_go` | GameObject |  |
| `Pre_wanju_daka_1` | `Pre_wanju_daka_1_4_go` | GameObject |  |
| `Pre_wanju_daka_2` | `Pre_wanju_daka_2_5_go` | GameObject |  |
| `Pre_wanju_daka_3` | `Pre_wanju_daka_3_6_go` | GameObject |  |
| `Pre_wanju_daka_4` | `Pre_wanju_daka_4_7_go` | GameObject |  |
| `Pre_wanju_daka_5` | `Pre_wanju_daka_5_8_go` | GameObject |  |
| `Pre_wanju_daka_6` | `Pre_wanju_daka_6_9_go` | GameObject |  |
| `Pre_wanju_daka_7` | `Pre_wanju_daka_7_10_go` | GameObject |  |
| `Pre_wanju_daka_8` | `Pre_wanju_daka_8_11_go` | GameObject |  |
| `Pre_wanju_daka_9` | `Pre_wanju_daka_9_12_go` | GameObject |  |
| `Item_card_drawCard_template` | `Item_card_drawCard_template_13_go` | GameObject |  |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀即为 `运行时节点名`。
例如 `btn_chouka1_0_btn` → 运行时节点 `btn_chouka1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点 | 触发方式 | Logic 回调 |
|-------------|-----------|---------|-----------|
| `btn_chouka1_0_btn` | `btn_chouka1` | `onClick?.Invoke()` | OnClickSingleDrawButton() |
| `btn_chouka2_1_btn` | `btn_chouka2` | `onClick?.Invoke()` | OnClickTenDrawButton() |
| `BGCloseBtn_2_btn` | `BGCloseBtn` | `onClick?.Invoke()` | OnClickCloseButton() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名 | 类型 | 注释 |
|--------|-------------|------|------|
| `btn_chouka1_0_btn` | `btn_chouka1` | GameButton |  |
| `btn_chouka2_1_btn` | `btn_chouka2` | GameButton |  |
| `BGCloseBtn_2_btn` | `BGCloseBtn` | GameButton |  |
| `UD_ZiYuan_test1_1_0_img` | `UD_ZiYuan_test1_1` | GameImage |  |
| `UD_ZiYuan_test1_1_img` | `UD_ZiYuan_test1` | GameImage |  |
| `TXT_1_2_30_0_0_1_0_txt` | `TXT_1_2_30_0_0_1` | GameText |  |
| `TXT_1_2_30_0_0_1_txt` | `TXT_1_2_30_0_0` | GameText |  |
| `danchou_group_0_go` | `danchou_group` | GameObject |  |
| `pos_1_go` | `pos` | GameObject |  |
| `shilian_group_2_go` | `shilian_group` | GameObject |  |
| `Pre_wanju_daka_3_go` | `Pre_wanju_daka` | GameObject |  |
| `Pre_wanju_daka_1_4_go` | `Pre_wanju_daka_1` | GameObject |  |
| `Pre_wanju_daka_2_5_go` | `Pre_wanju_daka_2` | GameObject |  |
| `Pre_wanju_daka_3_6_go` | `Pre_wanju_daka_3` | GameObject |  |
| `Pre_wanju_daka_4_7_go` | `Pre_wanju_daka_4` | GameObject |  |
| `Pre_wanju_daka_5_8_go` | `Pre_wanju_daka_5` | GameObject |  |
| `Pre_wanju_daka_6_9_go` | `Pre_wanju_daka_6` | GameObject |  |
| `Pre_wanju_daka_7_10_go` | `Pre_wanju_daka_7` | GameObject |  |
| `Pre_wanju_daka_8_11_go` | `Pre_wanju_daka_8` | GameObject |  |
| `Pre_wanju_daka_9_12_go` | `Pre_wanju_daka_9` | GameObject |  |
| `Item_card_drawCard_template_13_go` | `Item_card_drawCard_template` | GameObject |  |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_DrawCard_ResultView_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_DrawCard_ResultView");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_DrawCard_ResultView");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_DrawCard_ResultView");
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
