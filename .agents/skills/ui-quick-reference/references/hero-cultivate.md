# hero-cultivate - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `hero-cultivate` |
| UIID | `UI_HeroMainList` |
| UIDes | 角色背包界面 |
| CanvasIndex | 0 |
| UI 根节点名 | `UI_HeroMainList` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_HeroMainList` |
| Logic 全限定名 | `HotFix_Project.UI_HeroMainList_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_HeroMainList`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_HeroMainList");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas0/";
var ui = GameObject.Find(root + "UI_HeroMainList");
```

## 3. 节点树速查

# Prefab: UI_HeroMainList.prefab
# 根节点: UI_HeroMainList
# 节点总数: 49
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_hecheng` | `btn_hecheng_0_btn` | GameButton | 按钮标签-英雄列表-点击切换英雄列表页面节点 |
| `UI_HeroMainList\tab_group\btn_wanju_1` | `btn_wanju_1_1_btn` | GameButton | 按钮标签-英雄天赋-点击切换天赋页面节点 |
| `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_hecheng\xuanzhong_1` | `xuanzhong_1_0_go` | GameObject | 按钮标签-英雄列表-选中状态 |
| `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_hecheng\weixuanzhong_1` | `weixuanzhong_1_1_go` | GameObject | 按钮标签-英雄列表-正常状态 |
| `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_wanju\xuanzhong` | `xuanzhong_2_go` | GameObject | 按钮标签-英雄天赋-选中状态 |
| `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_wanju\weixuanzhong` | `weixuanzhong_3_go` | GameObject | 按钮标签-英雄天赋-正常状态 |

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
| `btn_hecheng_0_btn` | `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_hecheng` | GameButton | 按钮标签-英雄列表-点击切换英雄列表页面节点 | — |
| `btn_wanju_1_1_btn` | `UI_HeroMainList\tab_group\btn_wanju_1` | GameButton | 按钮标签-英雄天赋-点击切换天赋页面节点 | — |
| `xuanzhong_1_0_go` | `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_hecheng\xuanzhong_1` | GameObject | 按钮标签-英雄列表-选中状态 | — |
| `weixuanzhong_1_1_go` | `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_hecheng\weixuanzhong_1` | GameObject | 按钮标签-英雄列表-正常状态 | — |
| `xuanzhong_2_go` | `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_wanju\xuanzhong` | GameObject | 按钮标签-英雄天赋-选中状态 | — |
| `weixuanzhong_3_go` | `UI_HeroMainList\UC_TalentMainView\erjidaohang_group\btn_wanju\weixuanzhong` | GameObject | 按钮标签-英雄天赋-正常状态 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `_selectedTab` | HeroMainTab | — |
| `_isOpenParamSet` | bool | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_HeroMainList_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_HeroMainList");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_HeroMainList");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_HeroMainList");
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
