# main-hud - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `main-hud` |
| UIID | `UI_Main` |
| UIDes | 主界面 |
| CanvasIndex | 0 |
| UI 根节点名 | `UI_Main` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_Main` |
| Logic 全限定名 | `HotFix_Project.UI_Main_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_Main`（见 Gen/Table/UIID.cs） |

### 子 UI（功能关联界面）

| UIID | 用途 | Canvas |
|------|------|--------|
| `UI_MainBottom` | 底部导航栏 | 1 |
| `UI_DrawCard_Main` | 抽卡主页面（btn_chouka 入口） | 2 |
| `UI_MainPassPanel` | 主线战令界面（btn_zhanling 入口） | 2 |
| `UI_Bag` | 背包（btn_bag 入口） | — |
| `UI_Store_Tabs` | 商店（btn_shop 入口） | — |
| `UI_FirstRechargePop` | 首充弹窗（btn_shouchong 入口） | — |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_Main");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas0/";
var ui = GameObject.Find(root + "UI_Main");
```

## 3. 节点树速查

# Prefab: UI_Main.prefab
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取

### AutoGen 绑定组件清单

**GameButton 控件**

| 运行时节点名 | 字段名 | 类型 | 注释 |
|-------------|--------|------|------|
| `btn_chouka` | `btn_chouka_0_btn` | GameButton | 抽卡 |
| `btn_shouchong` | `btn_shouchong_1_btn` | GameButton | 首充 |
| `btn_zhanling` | `btn_zhanling_2_btn` | GameButton | 战令 |
| `btn_bag` | `btn_bag_3_btn` | GameButton | 背包 |
| `btn_shop` | `btn_shop_4_btn` | GameButton | 商店 |
| `GMAddExpImg` | `GMAddExpImg_5_btn` | GameButton | GM加经验 |

**UIComList 子组件**

| 运行时节点名 | 字段名 | 子组件类型 | 注释 |
|-------------|--------|-----------|------|
| `moneyRoot` | `moneyRoot_0_com` | commonResource_Logic | 顶部货币条 |
| `character` | `character_1_com` | character_Logic | 玩家信息 |
| `UC_MainStagePage` | `UC_MainStagePage_2_com` | UC_MainStagePage_Logic | 关卡信息 |
| `btn_shop` | `btn_shop_3_com` | LockItem_Logic | 商店解锁 |
| `btn_shouchong` | `btn_shouchong_4_com` | LockItem_Logic | 首充解锁 |

**集合字段**

| 字段名 | 元素类型 | 长度 | 说明 |
|--------|---------|------|------|
| `commonResource_Logic_List` | commonResource_Logic[] | 1 | 货币条集合 |
| `character_Logic_List` | character_Logic[] | 1 | 玩家信息集合 |
| `UC_MainStagePage_Logic_List` | UC_MainStagePage_Logic[] | 1 | 关卡页集合 |
| `LockItem_Logic_List` | LockItem_Logic[] | 2 | 解锁项集合（shop/shouchong） |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀即为 `运行时节点名`。
例如 `btn_chouka_0_btn` → 运行时节点 `btn_chouka`；`moneyRoot_0_com` → `moneyRoot`。

## 4. 按钮/交互速查

### AutoGen 按钮回调（直接委托形式）

| AutoGen 字段 | 运行时节点 | 触发方式 | Logic 回调 | 跳转目标 |
|-------------|-----------|---------|-----------|---------|
| `btn_chouka_0_btn` | `btn_chouka` | `onClick?.Invoke()` | `ChoujiangBtnClick()` | `CreateUIAsync(UI_DrawCard_Main)` |
| `btn_shouchong_1_btn` | `btn_shouchong` | `onClick?.Invoke()` | `FirstRechargeClick()` | `CreateUIAsync(UI_FirstRechargePop)` |
| `btn_zhanling_2_btn` | `btn_zhanling` | `onClick?.Invoke()` | `ZhanlingClick()` | `CreateUIAsync(UI_MainPassPanel)` |
| `btn_bag_3_btn` | `btn_bag` | `onClick?.Invoke()` | `BagButtonClick()` | `CreateUIAsync(UI_Bag)` |
| `btn_shop_4_btn` | `btn_shop` | `onClick?.Invoke()` | `ShopClick()` | `StoreType=Normal; CreateUIAsync(UI_Store_Tabs)` |
| `GMAddExpImg_5_btn` | `GMAddExpImg` | `onClick?.Invoke()` | `GMAddExp()` | `SendPacketToServerEx(CLGmReq "0 100")` |

### 测试按钮（transform.Find 形式，非 AutoGen，位于 `test/` 节点下）

| 节点路径 | 回调行为 | 跳转目标 |
|---------|---------|---------|
| `test/背包测试` | lambda | `CreateUIAsync(UI_Battle_Backpack_Crafting)` |
| `test/上阵测试` | lambda | `CreateUIAsync(UI_Formation)` |
| `test/开始战斗` | lambda | `MainLineStageMsgMgr.Inst.CLStageBegin(stageId)` |
| `test/战斗结束` | lambda | `MainLineStageMsgMgr.Inst.CLStageEnd(stageId, Win, 0, 50)` |

> 注：`test/` 下按钮包在 `try/catch` 中，缺失节点时仅打印 "残留测试逻辑，请删除"，不阻断主流程。

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名 | 类型 | 注释 |
|--------|-------------|------|------|
| `btn_chouka_0_btn` | `btn_chouka` | GameButton | 抽卡 |
| `btn_shouchong_1_btn` | `btn_shouchong` | GameButton | 首充 |
| `btn_zhanling_2_btn` | `btn_zhanling` | GameButton | 战令 |
| `btn_bag_3_btn` | `btn_bag` | GameButton | 背包 |
| `btn_shop_4_btn` | `btn_shop` | GameButton | 商店 |
| `GMAddExpImg_5_btn` | `GMAddExpImg` | GameButton | GM加经验 |
| `moneyRoot_0_com` | `moneyRoot` | UIComList(commonResource_Logic) | 顶部货币条 |
| `character_1_com` | `character` | UIComList(character_Logic) | 玩家信息 |
| `UC_MainStagePage_2_com` | `UC_MainStagePage` | UIComList(UC_MainStagePage_Logic) | 关卡信息 |
| `btn_shop_3_com` | `btn_shop` | UIComList(LockItem_Logic) | 商店解锁 |
| `btn_shouchong_4_com` | `btn_shouchong` | UIComList(LockItem_Logic) | 首充解锁 |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| — | — | UI_Main_Logic 的 `#region 字段定义` 为 TODO，无自定义私有字段 |

### Logic 关键方法

| 方法名 | 调用时机 | 行为 |
|--------|---------|------|
| `Awake(BaseUI)` | UI 创建 | `InitUILogic` → `PlayUIInAnim` → `Event_Register` → `InitEvent` |
| `Start()` | Awake 后 | `Init()` |
| `Init()` | Start | `moneyRoot_0_com.InitCustom(Diamond, Gold, Power)` → `character_1_com.Init()` → `RefreshBtnState()` |
| `InitEvent()` | Awake 末 | 监听 `CE_FunctionUnlock` / `CE_UpdateFirstRechargeGift` → `RefreshBtnState` |
| `RefreshBtnState()` | 解锁事件/Init | 遍历 `LockItem_Logic_List` 调 `RefreshItemState()` |
| `OnDestroy()` | UI 销毁 | `ClearUILogic()` |

### 事件监听

| 事件 ID | 回调 | 说明 |
|---------|------|------|
| `CE_FunctionUnlock.ID` | `RefreshBtnState` | 功能解锁刷新按钮状态 |
| `CE_UpdateFirstRechargeGift.ID` | `RefreshBtnState` | 首充礼包更新 |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_Main_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_Main");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_Main");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_Main");
// 读取货币条、玩家信息、关卡页等子组件状态
```

## 8. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| — | — | — | — |

## 9. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| — | — | — |
