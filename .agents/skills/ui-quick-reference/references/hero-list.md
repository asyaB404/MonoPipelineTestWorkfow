# hero-list - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `hero-list` |
| UIID | `UI_TDHeroAll` |
| UIDes |  |
| CanvasIndex | 2 |
| UI 根节点名 | `UI_TDHeroAll` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_TDHeroAll` |
| Logic 全限定名 | `HotFix_Project.UI_TDHeroAll_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_TDHeroAll`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 离线结构候选：真实导航入口和运行时触发方式必须由 unity-functiontest 在 PlayMode 中验证
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，不作为运行时通过证据
// 运行时需独立轮询确认
var ui = GameObject.Find("UI_TDHeroAll");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas2/";
var ui = GameObject.Find(root + "UI_TDHeroAll");
```

## 3. 节点树速查

# Prefab: UI_TDHeroAll.prefab
# 根节点: UI_TDHeroAll
# 节点总数: 51
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取
# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：

### AutoGen 绑定组件清单

| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |
|----------------------|--------|------|------|
| `UI_TDHeroAll\bg\bottom\btnok` | `btnok_0_btn` | GameButton | 确定 |
| `UI_TDHeroAll\bg\bottom\btnconcel` | `btnconcel_1_btn` | GameButton | 取消 |
| `UI_TDHeroAll\bg\bottom\btnedit` | `btnedit_2_btn` | GameButton | 编辑 |
| `UI_TDHeroAll\btnback` | `btnback_3_btn` | GameButton | 返回按钮 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | `icon_4_btn` | GameButton | OnSceneHeroBtn1 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | `icon_5_btn` | GameButton | OnSceneHeroBtn2 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | `icon_6_btn` | GameButton | OnSceneHeroBtn3 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | `icon_0_img` | GameImage | 上阵头像1 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | `icon_1_img` | GameImage | 上阵头像2 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | `icon_2_img` | GameImage | 上阵头像3 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\eleicon` | `eleicon_3_img` | GameImage | 上阵英雄1属性 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\eleicon` | `eleicon_4_img` | GameImage | 上阵英雄2属性 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\eleicon` | `eleicon_5_img` | GameImage | 上阵英雄3属性 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg` | `levbg_6_img` | GameImage | 上阵英雄1等级底图 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg` | `levbg_7_img` | GameImage | 上阵英雄2等级底图 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg` | `levbg_8_img` | GameImage | 上阵英雄3等级底图 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\lev` | `lev_0_txt` | GameText | 英雄1等级 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\lev` | `lev_1_txt` | GameText | 英雄2等级 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\lev` | `lev_2_txt` | GameText | 英雄3等级 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg1` | `bg1_0_go` | GameObject | 上阵1的spine位置 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg2` | `bg2_1_go` | GameObject | 上阵2的spine位置 |
| `UI_TDHeroAll\bg\bottom\onscenenode\bg3` | `bg3_2_go` | GameObject | 上阵3的spine位置 |
| `ScrollView_0_gsrV2` | `ScrollView_0_gsrV2` | GameScrollRect_V2 | 英雄列表 |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。
例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\wanju_group\btn_baocun_1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |
|-------------|---------------------|---------|-----------|
| `btnok_0_btn` | `UI_TDHeroAll\bg\bottom\btnok` | 候选：`onClick?.Invoke()` | OnClickOk() |
| `btnconcel_1_btn` | `UI_TDHeroAll\bg\bottom\btnconcel` | 候选：`onClick?.Invoke()` | OnClickCancel() |
| `btnedit_2_btn` | `UI_TDHeroAll\bg\bottom\btnedit` | 候选：`onClick?.Invoke()` | OnClickEdit() |
| `btnback_3_btn` | `UI_TDHeroAll\btnback` | 候选：`onClick?.Invoke()` | OnClickBack() |

**离线候选说明**：`onClick?.Invoke()` 仅表示源码层候选触发方式；实际是否有效必须由 unity-functiontest 在 PlayMode 中验证，不能直接作为通过证据。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |
|--------|----------------------|------|------|---------|
| `btnok_0_btn` | `UI_TDHeroAll\bg\bottom\btnok` | GameButton | 确定 | `OnClickOk()` |
| `btnconcel_1_btn` | `UI_TDHeroAll\bg\bottom\btnconcel` | GameButton | 取消 | `OnClickCancel()` |
| `btnedit_2_btn` | `UI_TDHeroAll\bg\bottom\btnedit` | GameButton | 编辑 | `OnClickEdit()` |
| `btnback_3_btn` | `UI_TDHeroAll\btnback` | GameButton | 返回按钮 | `OnClickBack()` |
| `icon_4_btn` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | GameButton | OnSceneHeroBtn1 | — |
| `icon_5_btn` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | GameButton | OnSceneHeroBtn2 | — |
| `icon_6_btn` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | GameButton | OnSceneHeroBtn3 | — |
| `icon_0_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | GameImage | 上阵头像1 | — |
| `icon_1_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | GameImage | 上阵头像2 | — |
| `icon_2_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\icon` | GameImage | 上阵头像3 | — |
| `eleicon_3_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\eleicon` | GameImage | 上阵英雄1属性 | — |
| `eleicon_4_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\eleicon` | GameImage | 上阵英雄2属性 | — |
| `eleicon_5_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\eleicon` | GameImage | 上阵英雄3属性 | — |
| `levbg_6_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg` | GameImage | 上阵英雄1等级底图 | — |
| `levbg_7_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg` | GameImage | 上阵英雄2等级底图 | — |
| `levbg_8_img` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg` | GameImage | 上阵英雄3等级底图 | — |
| `lev_0_txt` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\lev` | GameText | 英雄1等级 | — |
| `lev_1_txt` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\lev` | GameText | 英雄2等级 | — |
| `lev_2_txt` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2\levbg\lev` | GameText | 英雄3等级 | — |
| `bg1_0_go` | `UI_TDHeroAll\bg\bottom\onscenenode\bg1` | GameObject | 上阵1的spine位置 | — |
| `bg2_1_go` | `UI_TDHeroAll\bg\bottom\onscenenode\bg2` | GameObject | 上阵2的spine位置 | — |
| `bg3_2_go` | `UI_TDHeroAll\bg\bottom\onscenenode\bg3` | GameObject | 上阵3的spine位置 | — |
| `ScrollView_0_gsrV2` | `ScrollView_0_gsrV2` | GameScrollRect_V2 | 英雄列表 | — |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `m_IsEditMode` | bool | — |
| `m_OnSceneHeroIds` | List<int> | — |
| `m_BackupOnSceneHeroIds` | List<int> | — |
| `m_HeroItemPool` | List<HeroItem_Logic> | — |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_TDHeroAll_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_TDHeroAll");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_TDHeroAll");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_TDHeroAll");
// 根据实际节点补充读取代码
```

## 8. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| 静态层级路径 | 离线 reference 曾指向 `AdapterArea/Canvas2`，本轮运行时实际为 `UI_Root/Canvas2` | 使用 `GameEntry/Builtin/UI/UI_Root/Canvas2/UI_TDHeroAll` | 2026-08-26 |
| 异常条件构造 | 当前 Unity/MCP 环境无法构造网络断开、异常字段和重复提交 | 相关用例记录 `test_inconclusive`，不判定产品失败 | 2026-08-26 |

## 9. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| — | — | — |
