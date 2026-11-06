# shop - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `shop` |
| UIID | `UI_Store` |
| UIDes | 系统商店 |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_Store` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Store` |
| Logic 全限定名 | `HotFix_Project.UI_Store_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_Store`（见 Gen/Table/UIID.cs） |

### 子 UI

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_Store_Purchase` | 【弹窗】购买商品详情窗口 | 3 |
| `UI_Store_Tabs` | 系统商店底部导航栏 | 2 |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_Store");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_Store");
```

## 3. 节点树速查

# Prefab: UI_Store.prefab
# 根节点: UI_Store
# 节点总数: 36
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_Store\bg\NoEmpty\guanggao_layerout\Pre_button_common_01b\button_guanggao` | `button_guanggao_0_btn` | GameButton | 广告刷新 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\Btn_Shuaxin` | `Btn_Shuaxin_1_btn` | GameButton | 货币刷新 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\layer\IMG_Need_Res` | `IMG_Need_Res_0_img` | GameImage | 刷新需要的货币 |
| `UI_Store\bg\NoEmpty\GRP_Daojishi_group\TXT_daojishi` | `TXT_daojishi_0_txt` | GameText | 倒计时 |
| `UI_Store\bg\NoEmpty\guanggao_layerout\GRP_times_group\TXT_guanggao` | `TXT_guanggao_1_txt` | GameText | 剩余广告次数 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout\GRP_times_group_1\TXT_shuaxin` | `TXT_shuaxin_2_txt` | GameText | 剩余刷新次数 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\layer\TXT_shuaxin_Need_Count` | `TXT_shuaxin_Need_Count_3_txt` | GameText | 刷新货币的数量 |
| `UI_Store\bg\NoEmpty\guanggao_layerout` | `guanggao_layerout_0_go` | GameObject | 广告组件 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout` | `shuaxin_Layerout_1_go` | GameObject | 刷新组件 |
| `UI_Store\bg\NoEmpty\guanggao_layerout\GRP_times_group` | `GRP_times_group_2_go` | GameObject | 广告剩余次数显示 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout\GRP_times_group_1` | `GRP_times_group_1_3_go` | GameObject | 货币剩余次数显示 |
| `UI_Store\bg\NoEmpty\guanggao_layerout\Pre_button_common_01b\ClickBtn_huise` | `ClickBtn_huise_4_go` | GameObject | 灰色的广告 |
| `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\Btn_huise` | `Btn_huise_5_go` | GameObject | 灰色的刷新 |
| `UI_Store\bg\NoEmpty` | `NoEmpty_6_go` | GameObject | 列表范围框 |

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
| `button_guanggao_0_btn` | `UI_Store\bg\NoEmpty\guanggao_layerout\Pre_button_common_01b\button_guanggao` | GameButton | 广告刷新 | — |
| `Btn_Shuaxin_1_btn` | `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\Btn_Shuaxin` | GameButton | 货币刷新 | — |
| `IMG_Need_Res_0_img` | `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\layer\IMG_Need_Res` | GameImage | 刷新需要的货币 | — |
| `TXT_daojishi_0_txt` | `UI_Store\bg\NoEmpty\GRP_Daojishi_group\TXT_daojishi` | GameText | 倒计时 | — |
| `TXT_guanggao_1_txt` | `UI_Store\bg\NoEmpty\guanggao_layerout\GRP_times_group\TXT_guanggao` | GameText | 剩余广告次数 | — |
| `TXT_shuaxin_2_txt` | `UI_Store\bg\NoEmpty\shuaxin_Layerout\GRP_times_group_1\TXT_shuaxin` | GameText | 剩余刷新次数 | — |
| `TXT_shuaxin_Need_Count_3_txt` | `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\layer\TXT_shuaxin_Need_Count` | GameText | 刷新货币的数量 | — |
| `guanggao_layerout_0_go` | `UI_Store\bg\NoEmpty\guanggao_layerout` | GameObject | 广告组件 | — |
| `shuaxin_Layerout_1_go` | `UI_Store\bg\NoEmpty\shuaxin_Layerout` | GameObject | 刷新组件 | — |
| `GRP_times_group_2_go` | `UI_Store\bg\NoEmpty\guanggao_layerout\GRP_times_group` | GameObject | 广告剩余次数显示 | — |
| `GRP_times_group_1_3_go` | `UI_Store\bg\NoEmpty\shuaxin_Layerout\GRP_times_group_1` | GameObject | 货币剩余次数显示 | — |
| `ClickBtn_huise_4_go` | `UI_Store\bg\NoEmpty\guanggao_layerout\Pre_button_common_01b\ClickBtn_huise` | GameObject | 灰色的广告 | — |
| `Btn_huise_5_go` | `UI_Store\bg\NoEmpty\shuaxin_Layerout\Pre_button_common_01a\Btn_huise` | GameObject | 灰色的刷新 | — |
| `NoEmpty_6_go` | `UI_Store\bg\NoEmpty` | GameObject | 列表范围框 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `shopTimers` | Dictionary<ShopType, TimeSpan> | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_Store_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_Store");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_Store");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Store");
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
