# talent - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `talent` |
| UIID | `UI_TalentDetailView` |
| UIDes | 角色天赋详情+天赋解锁 |
| CanvasIndex | 3 |
| UI 根节点名 | `UI_TalentDetailView` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_TalentDetailView` |
| Logic 全限定名 | `HotFix_Project.UI_TalentDetailView_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_TalentDetailView`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_TalentDetailView");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas3/";
var ui = GameObject.Find(root + "UI_TalentDetailView");
```

// 注意：UI_TalentDetailView 需外部调用 SetTalentId(int talentId) 设置天赋 ID 后才能正确展示数据

## 3. 节点树速查

# Prefab: UI_TalentDetailView.prefab
# 根节点: UI_TalentDetailView
# 节点总数: 26
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_TalentDetailView\tips_skillinfo\kejiesuo\btn_baocun` | `btn_baocun_0_btn` | GameButton | 解锁按钮-点击解锁发送解锁协议解锁 |
| `BGCloseBtn` | `BGCloseBtn_1_btn` | GameButton | 关闭按钮-点击关闭页面 |
| `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group_1\UD_ZiYuan_test1_1` | `UD_ZiYuan_test1_1_0_img` | GameImage | 图标-消耗品1 |
| `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group\UD_ZiYuan_test1` | `UD_ZiYuan_test1_1_img` | GameImage | 图标-消耗品2 |
| `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group_1\TXT_1_20_30_0_0` | `TXT_1_20_30_0_0_0_txt` | GameText | 消耗品数量-消耗品1-不足时使用2100910003充足时使用-开启富文本 |
| `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group\TXT_1_19_30_0_0` | `TXT_1_19_30_0_0_1_txt` | GameText | 消耗品数量-消耗品2-不足时使用2100910003充足时使用-开启富文本 |
| `UI_TalentDetailView\tips_skillinfo\TXT_2_18_46_0_0` | `TXT_2_18_46_0_0_2_txt` | GameText | 天赋名称 |
| `UI_TalentDetailView\tips_skillinfo\GameObject\TXT_1_16_42_0_0` | `TXT_1_16_42_0_0_3_txt` | GameText | 属性名-加成的属性名-来自数据支撑层天赋表AttrAdd |
| `UI_TalentDetailView\tips_skillinfo\GameObject\TXT_1_16_42_0_2` | `TXT_1_16_42_0_2_4_txt` | GameText | 属性值-加成的属性值-来自数据支撑层天赋表AttrAdd |
| `UI_TalentDetailView\tips_skillinfo\kejiesuo` | `kejiesuo_0_go` | GameObject | 状态-可解锁 |
| `UI_TalentDetailView\tips_skillinfo\weidatiaojian` | `weidatiaojian_1_go` | GameObject | 状态-未解锁 |
| `UI_TalentDetailView\tips_skillinfo\yijihuo` | `yijihuo_2_go` | GameObject | 已解锁 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btn_baocun_0_btn` | `UI_TalentDetailView\tips_skillinfo\kejiesuo\btn_baocun` | `onClick` | `OnClickUnlockButton` |
| `BGCloseBtn_1_btn` | `BGCloseBtn` | `onClick` | `CloseUI` |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。
**事件注册位置**：[`Event_Register()`](Assets/Scripts/CyStarRoad/UILogic/UI_TalentDetailView/UI_TalentDetailView_Logic.cs:127)

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btn_baocun_0_btn` | `UI_TalentDetailView\tips_skillinfo\kejiesuo\btn_baocun` | GameButton | 解锁按钮-点击解锁发送解锁协议解锁 | `OnClickUnlockButton` |
| `BGCloseBtn_1_btn` | `BGCloseBtn` | GameButton | 关闭按钮-点击关闭页面 | `CloseUI` |
| `UD_ZiYuan_test1_1_0_img` | `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group_1\UD_ZiYuan_test1_1` | GameImage | 图标-消耗品1 | — |
| `UD_ZiYuan_test1_1_img` | `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group\UD_ZiYuan_test1` | GameImage | 图标-消耗品2 | — |
| `TXT_1_20_30_0_0_0_txt` | `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group_1\TXT_1_20_30_0_0` | GameText | 消耗品数量-消耗品1-不足时使用2100910003充足时使用-开启富文本 | — |
| `TXT_1_19_30_0_0_1_txt` | `UI_TalentDetailView\tips_skillinfo\kejiesuo\xiaohao_group\TXT_1_19_30_0_0` | GameText | 消耗品数量-消耗品2-不足时使用2100910003充足时使用-开启富文本 | — |
| `TXT_2_18_46_0_0_2_txt` | `UI_TalentDetailView\tips_skillinfo\TXT_2_18_46_0_0` | GameText | 天赋名称 | — |
| `TXT_1_16_42_0_0_3_txt` | `UI_TalentDetailView\tips_skillinfo\GameObject\TXT_1_16_42_0_0` | GameText | 属性名-加成的属性名-来自数据支撑层天赋表AttrAdd | — |
| `TXT_1_16_42_0_2_4_txt` | `UI_TalentDetailView\tips_skillinfo\GameObject\TXT_1_16_42_0_2` | GameText | 属性值-加成的属性值-来自数据支撑层天赋表AttrAdd | — |
| `kejiesuo_0_go` | `UI_TalentDetailView\tips_skillinfo\kejiesuo` | GameObject | 状态-可解锁 | — |
| `weidatiaojian_1_go` | `UI_TalentDetailView\tips_skillinfo\weidatiaojian` | GameObject | 状态-未解锁 | — |
| `yijihuo_2_go` | `UI_TalentDetailView\tips_skillinfo\yijihuo` | GameObject | 已解锁 | — |
| `Icon_talent_group_0_com` | —（子组件引用） | UIComList | 天赋图标小组件-在详情页面中不显示排数图标 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `_currentTalentId` | int | 当前展示的天赋 ID |
| `_currentTalentData` | TalentDataMgr.TalentData | 当前天赋数据缓存 |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_TalentDetailView_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_TalentDetailView");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_TalentDetailView");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_TalentDetailView");
// 读取当前天赋 ID
// var talentId = (int)lg.GetType().GetField("_currentTalentId", ...).GetValue(lg);
// 读取天赋数据缓存
// var talentData = lg.GetType().GetField("_currentTalentData", ...).GetValue(lg);
```

## 8. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| — | — | — | — |

## 9. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| — | — | — |
