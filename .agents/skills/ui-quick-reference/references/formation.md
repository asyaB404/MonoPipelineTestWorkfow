# formation - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `formation` |
| UIID | `UI_Formation` |
| UIDes | 战斗布阵界面 |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_Formation` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Formation` |
| Logic 全限定名 | `HotFix_Project.UI_Formation_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_Formation`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_Formation");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_Formation");
```

## 3. 节点树速查

# Prefab: UI_Formation.prefab
# 根节点: UI_Formation
# 节点总数: 108
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_Formation\buzhen_tanchuang\btn_close` | `btn_close_0_btn` | GameButton | btn_close |
| `UI_Formation\wanju_group\btn_xiazhen` | `btn_xiazhen_1_btn` | GameButton | btn_xiazhen |
| `UI_Formation\wanju_group\btn_shangzhen` | `btn_shangzhen_2_btn` | GameButton | btn_shangzhen |
| `UI_Formation\wanju_group\btn_tongbu_1` | `btn_tongbu_1_3_btn` | GameButton | btn_tongbu_1 |
| `UI_Formation\wanju_group\btn_baocun_1` | `btn_baocun_1_4_btn` | GameButton | btn_baocun_1 |
| `UI_Formation\juese_group\btn_baocun` | `btn_baocun_5_btn` | GameButton | btn_baocun |
| `UI_Formation\juese_group\btn_tongbu` | `btn_tongbu_6_btn` | GameButton | btn_tongbu |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1` | `shaixuan_quanbu_1_7_btn` | GameButton | 筛选背包玩具按钮-全部阵营 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1` | `shaixuan_guang_1_8_btn` | GameButton | 筛选背包玩具按钮-光阵营 Camp值2 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1` | `shaixuan_an_1_9_btn` | GameButton | 筛选背包玩具按钮-暗阵营 Camp值1 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1` | `shaixuan_quanbu_1_10_btn` | GameButton | 筛选背包角色按钮-全部阵营 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1` | `shaixuan_an_1_11_btn` | GameButton | 筛选背包角色按钮-光阵营 Camp值2 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1` | `shaixuan_guang_1_12_btn` | GameButton | 筛选背包角色按钮-暗阵营 Camp值1 |
| `UI_Formation\buzhen_tanchuang\Img_common_frame1` | `Img_common_frame1_0_img` | GameImage | Img_common_frame1 |
| `UI_Formation\buzhen_tanchuang\btn_close\img_btn_common_close` | `img_btn_common_close_1_img` | GameImage | img_btn_common_close |
| `UI_Formation\wanju_group\btn_xiazhen\Img_btn_common_01lan_1` | `Img_btn_common_01lan_1_2_img` | GameImage | Img_btn_common_01lan_1 |
| `UI_Formation\wanju_group\btn_shangzhen\Img_btn_common_01lan` | `Img_btn_common_01lan_3_img` | GameImage | Img_btn_common_01lan |
| `UI_Formation\wanju_group\btn_tongbu_1\Img_btn_common_02huang_1` | `Img_btn_common_02huang_1_4_img` | GameImage | Img_btn_common_02huang_1 |
| `UI_Formation\wanju_group\btn_baocun_1\Img_btn_common_01huang_1` | `Img_btn_common_01huang_1_5_img` | GameImage | Img_btn_common_01huang_1 |
| `UI_Formation\wanju_group\shaixuan_1\img_common_shaixuandi_1` | `img_common_shaixuandi_1_6_img` | GameImage | img_common_shaixuandi_1 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1\Img_common_shaixuandi1_5` | `Img_common_shaixuandi1_5_7_img` | GameImage | Img_common_shaixuandi1_5 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\gaoliang` | `gaoliang_8_img` | GameImage | Img_common_shaixuan2_5 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\Img_common_shaixuandi1_4` | `Img_common_shaixuandi1_4_9_img` | GameImage | Img_common_shaixuandi1_4 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\Img_icon_common_an_1` | `Img_icon_common_an_1_10_img` | GameImage | Img_icon_common_an_1 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\gaoliang` | `gaoliang_11_img` | GameImage | Img_common_shaixuan2_4 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1\Img_common_shaixuandi1_3` | `Img_common_shaixuandi1_3_12_img` | GameImage | Img_common_shaixuandi1_3 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1\Img_icon_common_guang_1` | `Img_icon_common_guang_1_13_img` | GameImage | Img_icon_common_guang_1 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\gaoliang` | `gaoliang_14_img` | GameImage | Img_common_shaixuan2_3 |
| `UI_Formation\juese_group\btn_baocun\Img_btn_common_01huang` | `Img_btn_common_01huang_15_img` | GameImage | Img_btn_common_01huang |
| `UI_Formation\juese_group\btn_tongbu\Img_btn_common_02huang` | `Img_btn_common_02huang_16_img` | GameImage | Img_btn_common_02huang |
| `UI_Formation\juese_group\img_Form_zhenweidi` | `img_Form_zhenweidi_17_img` | GameImage | img_Form_zhenweidi |
| `UI_Formation\juese_group\shaixuan\img_common_shaixuandi` | `img_common_shaixuandi_18_img` | GameImage | img_common_shaixuandi |
| `UI_Formation\juese_group\img_Form_juese_spine` | `img_Form_juese_spine_19_img` | GameImage | 当前上阵角色spine |
| `UI_Formation\buzhen_tanchuang\TXT_2_1_64_1_0` | `TXT_2_1_64_1_0_0_txt` | GameText | TXT_2_1_64_1_0 |
| `UI_Formation\wanju_group\btn_xiazhen\TXT_2_2_50_3_0_1` | `TXT_2_2_50_3_0_1_1_txt` | GameText | TXT_2_2_50_3_0_1 |
| `UI_Formation\wanju_group\btn_shangzhen\TXT_2_2_50_3_0` | `TXT_2_2_50_3_0_2_txt` | GameText | TXT_2_2_50_3_0 |
| `UI_Formation\wanju_group\btn_tongbu_1\TXT_2_2_40_2_0_1` | `TXT_2_2_40_2_0_1_3_txt` | GameText | TXT_2_2_40_2_0_1 |
| `UI_Formation\wanju_group\btn_baocun_1\TXT_2_2_50_2_0_1` | `TXT_2_2_50_2_0_1_4_txt` | GameText | TXT_2_2_50_2_0_1 |
| `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1\TXT_2_2_46_0_0_1` | `TXT_2_2_46_0_0_1_5_txt` | GameText | TXT_2_2_46_0_0_1 |
| `UI_Formation\juese_group\btn_baocun\TXT_2_2_50_2_0` | `TXT_2_2_50_2_0_6_txt` | GameText | TXT_2_2_50_2_0 |
| `UI_Formation\juese_group\btn_tongbu\TXT_2_2_40_2_0` | `TXT_2_2_40_2_0_7_txt` | GameText | TXT_2_2_40_2_0 |
| `UI_Formation\wanju_group\CaoWeiParent` | `CaoWeiParent_0_go` | GameObject | 玩具上阵槽位父对象 |
| `UI_Formation\wanju_group` | `wanju_group_1_go` | GameObject | 玩具页面 |
| `UI_Formation\juese_group` | `juese_group_2_go` | GameObject | 角色页面 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_close_0_btn` | `UI_Formation\buzhen_tanchuang\btn_close` | `onClick?.Invoke()` | _close.OnClickClose() |
| `btn_baocun_1_4_btn` | `UI_Formation\wanju_group\btn_baocun_1` | `onClick?.Invoke()` | _network.SaveBattleSetting() |
| `btn_baocun_5_btn` | `UI_Formation\juese_group\btn_baocun` | `onClick?.Invoke()` | _network.SaveBattleSetting() |
| `btn_shangzhen_2_btn` | `UI_Formation\wanju_group\btn_shangzhen` | `onClick?.Invoke()` | _battleBag.OneKeyEquipToys() |
| `btn_xiazhen_1_btn` | `UI_Formation\wanju_group\btn_xiazhen` | `onClick?.Invoke()` | _battleBag.OneKeyUnequipToys() |
| `shaixuan_quanbu_1_7_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1` | `onClick?.Invoke()` | _filter.SetToyCampFilter() |
| `shaixuan_an_1_9_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1` | `onClick?.Invoke()` | _filter.SetToyCampFilter() |
| `shaixuan_guang_1_8_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1` | `onClick?.Invoke()` | _filter.SetToyCampFilter() |
| `shaixuan_quanbu_1_10_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1` | `onClick?.Invoke()` | _filter.SetRoleCampFilter() |
| `shaixuan_an_1_11_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1` | `onClick?.Invoke()` | _filter.SetRoleCampFilter() |
| `shaixuan_guang_1_12_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1` | `onClick?.Invoke()` | _filter.SetRoleCampFilter() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_close_0_btn` | `UI_Formation\buzhen_tanchuang\btn_close` | GameButton | btn_close | `_close.OnClickClose()` |
| `btn_xiazhen_1_btn` | `UI_Formation\wanju_group\btn_xiazhen` | GameButton | btn_xiazhen | `_battleBag.OneKeyUnequipToys()` |
| `btn_shangzhen_2_btn` | `UI_Formation\wanju_group\btn_shangzhen` | GameButton | btn_shangzhen | `_battleBag.OneKeyEquipToys()` |
| `btn_tongbu_1_3_btn` | `UI_Formation\wanju_group\btn_tongbu_1` | GameButton | btn_tongbu_1 | — |
| `btn_baocun_1_4_btn` | `UI_Formation\wanju_group\btn_baocun_1` | GameButton | btn_baocun_1 | `_network.SaveBattleSetting()` |
| `btn_baocun_5_btn` | `UI_Formation\juese_group\btn_baocun` | GameButton | btn_baocun | `_network.SaveBattleSetting()` |
| `btn_tongbu_6_btn` | `UI_Formation\juese_group\btn_tongbu` | GameButton | btn_tongbu | — |
| `shaixuan_quanbu_1_7_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1` | GameButton | 筛选背包玩具按钮-全部阵营 | `_filter.SetToyCampFilter()` |
| `shaixuan_guang_1_8_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1` | GameButton | 筛选背包玩具按钮-光阵营 Camp值2 | `_filter.SetToyCampFilter()` |
| `shaixuan_an_1_9_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1` | GameButton | 筛选背包玩具按钮-暗阵营 Camp值1 | `_filter.SetToyCampFilter()` |
| `shaixuan_quanbu_1_10_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1` | GameButton | 筛选背包角色按钮-全部阵营 | `_filter.SetRoleCampFilter()` |
| `shaixuan_an_1_11_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1` | GameButton | 筛选背包角色按钮-光阵营 Camp值2 | `_filter.SetRoleCampFilter()` |
| `shaixuan_guang_1_12_btn` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1` | GameButton | 筛选背包角色按钮-暗阵营 Camp值1 | `_filter.SetRoleCampFilter()` |
| `Img_common_frame1_0_img` | `UI_Formation\buzhen_tanchuang\Img_common_frame1` | GameImage | Img_common_frame1 | — |
| `img_btn_common_close_1_img` | `UI_Formation\buzhen_tanchuang\btn_close\img_btn_common_close` | GameImage | img_btn_common_close | — |
| `Img_btn_common_01lan_1_2_img` | `UI_Formation\wanju_group\btn_xiazhen\Img_btn_common_01lan_1` | GameImage | Img_btn_common_01lan_1 | — |
| `Img_btn_common_01lan_3_img` | `UI_Formation\wanju_group\btn_shangzhen\Img_btn_common_01lan` | GameImage | Img_btn_common_01lan | — |
| `Img_btn_common_02huang_1_4_img` | `UI_Formation\wanju_group\btn_tongbu_1\Img_btn_common_02huang_1` | GameImage | Img_btn_common_02huang_1 | — |
| `Img_btn_common_01huang_1_5_img` | `UI_Formation\wanju_group\btn_baocun_1\Img_btn_common_01huang_1` | GameImage | Img_btn_common_01huang_1 | — |
| `img_common_shaixuandi_1_6_img` | `UI_Formation\wanju_group\shaixuan_1\img_common_shaixuandi_1` | GameImage | img_common_shaixuandi_1 | — |
| `Img_common_shaixuandi1_5_7_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1\Img_common_shaixuandi1_5` | GameImage | Img_common_shaixuandi1_5 | — |
| `gaoliang_8_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\gaoliang` | GameImage | Img_common_shaixuan2_5 | — |
| `Img_common_shaixuandi1_4_9_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\Img_common_shaixuandi1_4` | GameImage | Img_common_shaixuandi1_4 | — |
| `Img_icon_common_an_1_10_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\Img_icon_common_an_1` | GameImage | Img_icon_common_an_1 | — |
| `gaoliang_11_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\gaoliang` | GameImage | Img_common_shaixuan2_4 | — |
| `Img_common_shaixuandi1_3_12_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1\Img_common_shaixuandi1_3` | GameImage | Img_common_shaixuandi1_3 | — |
| `Img_icon_common_guang_1_13_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_guang_1\Img_icon_common_guang_1` | GameImage | Img_icon_common_guang_1 | — |
| `gaoliang_14_img` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_an_1\gaoliang` | GameImage | Img_common_shaixuan2_3 | — |
| `Img_btn_common_01huang_15_img` | `UI_Formation\juese_group\btn_baocun\Img_btn_common_01huang` | GameImage | Img_btn_common_01huang | — |
| `Img_btn_common_02huang_16_img` | `UI_Formation\juese_group\btn_tongbu\Img_btn_common_02huang` | GameImage | Img_btn_common_02huang | — |
| `img_Form_zhenweidi_17_img` | `UI_Formation\juese_group\img_Form_zhenweidi` | GameImage | img_Form_zhenweidi | — |
| `img_common_shaixuandi_18_img` | `UI_Formation\juese_group\shaixuan\img_common_shaixuandi` | GameImage | img_common_shaixuandi | — |
| `img_Form_juese_spine_19_img` | `UI_Formation\juese_group\img_Form_juese_spine` | GameImage | 当前上阵角色spine | — |
| `TXT_2_1_64_1_0_0_txt` | `UI_Formation\buzhen_tanchuang\TXT_2_1_64_1_0` | GameText | TXT_2_1_64_1_0 | — |
| `TXT_2_2_50_3_0_1_1_txt` | `UI_Formation\wanju_group\btn_xiazhen\TXT_2_2_50_3_0_1` | GameText | TXT_2_2_50_3_0_1 | — |
| `TXT_2_2_50_3_0_2_txt` | `UI_Formation\wanju_group\btn_shangzhen\TXT_2_2_50_3_0` | GameText | TXT_2_2_50_3_0 | — |
| `TXT_2_2_40_2_0_1_3_txt` | `UI_Formation\wanju_group\btn_tongbu_1\TXT_2_2_40_2_0_1` | GameText | TXT_2_2_40_2_0_1 | — |
| `TXT_2_2_50_2_0_1_4_txt` | `UI_Formation\wanju_group\btn_baocun_1\TXT_2_2_50_2_0_1` | GameText | TXT_2_2_50_2_0_1 | — |
| `TXT_2_2_46_0_0_1_5_txt` | `UI_Formation\wanju_group\shaixuan_1\shaixuan_quanbu_1\TXT_2_2_46_0_0_1` | GameText | TXT_2_2_46_0_0_1 | — |
| `TXT_2_2_50_2_0_6_txt` | `UI_Formation\juese_group\btn_baocun\TXT_2_2_50_2_0` | GameText | TXT_2_2_50_2_0 | — |
| `TXT_2_2_40_2_0_7_txt` | `UI_Formation\juese_group\btn_tongbu\TXT_2_2_40_2_0` | GameText | TXT_2_2_40_2_0 | — |
| `CaoWeiParent_0_go` | `UI_Formation\wanju_group\CaoWeiParent` | GameObject | 玩具上阵槽位父对象 | — |
| `wanju_group_1_go` | `UI_Formation\wanju_group` | GameObject | 玩具页面 | — |
| `juese_group_2_go` | `UI_Formation\juese_group` | GameObject | 角色页面 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_Formation_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_Formation");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_Formation");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_Formation");
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
