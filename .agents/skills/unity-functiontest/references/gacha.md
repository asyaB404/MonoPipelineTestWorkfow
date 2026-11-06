# gacha - 运行时参考（Unity 实测）

创建时间：2026-11-02
更新人：Cyou（2026-11-04 gacha-0003 增量更新）
功能简介：抽卡系统（单抽/十连/概率/保底/展示/异常容错）的运行时路径、触发方式与状态读取方式，用于 unity-functiontest 执行期复用。

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `gacha` |
| 主 UI | `UI_DrawCard_Main`（抽卡主页面） |
| 主 UI 场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_DrawCard_Main` |
| 结果 UI | `UI_DrawCard_ResultView` |
| 结果 UI 场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas3/UI_DrawCard_ResultView` |
| 概率 UI | `UI_DrawCard_RatePreviewView`（Canvas2） |
| 奖励弹窗 | `UI_GetReward`（Canvas4，抽卡后自动弹出） |
| Logic | `HotFix_Project.UI_DrawCard_Main_Logic` |

## 2. 进入方式（已实测）

1. 登录：`CyStarRoad.Test.TestBoot.Boot()` → 返回 `login_triggered`，随后独立状态查询确认 `UI_LoginGame` 不再激活且 `UI_Main`、`UI_MainBottom` 活跃。
2. 大厅入口：`GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_Main/btn_chouka/btn_chouka`（GameButton）。
3. 触发方式：`GameButton.ExecuteButtonClick()` 实测有效。
4. 就绪判定：`GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas2/UI_DrawCard_Main").activeInHierarchy == true`。

## 3. 已验证节点路径（主界面）

| 语义 | 路径（相对 UI_DrawCard_Main） | 组件 |
|------|------------------------------|------|
| 单抽按钮 | `btn_chouka1` | GameButton |
| 十连按钮 | `btn_chouka2` | GameButton |
| 概率按钮 | `btn_gailv` | GameButton |
| 普通页签 | `btn_chouka`（gacha-0003 实测 active=False，仅占位） | GameButton |
| 限时页签 | `btn_limittime`（active=False） | GameButton |
| 返回 | `btn_back`（active=False） | GameButton |
| 单抽费用文本 | `btn_chouka1/xiaohao_group_1/txt_costnum_one` | GameText（富文本，实测 `<color=#FFFFFF>1</color>`） |
| 十连费用文本 | `btn_chouka2/xiaohao_group/txt_costnum_ten` | GameText（富文本，实测 `<color=#FFFFFF>10</color>`） |
| 单抽按钮标题 | `btn_chouka1/TXT_2_2_46_3_0` | GameText（实测 `抽1次`） |
| 十连按钮标题 | `btn_chouka2/TXT_2_2_46_2_0` | GameText（实测 `抽10次`） |
| 概率按钮标题 | `btn_gailv/TXT_2_2_36_6_0` | GameText（实测 `概率`） |
| 保底提示 | `TXT_2_16_46_0_0`（直接挂在 UI 根） | GameText（实测 `50次后必得传说玩具`） |
| 保底剩余数字 | `TXT_2_27_60_0_0` | GameText（实测 `12`，与保底提示不同步） |
| 选中页签标题 | `xuanzhong_1/TXT_2_2_46_6_0_1` | GameText（实测 `玩具祈愿`，**读取标题必须用此节点**） |
| 未选中页签标题 | `normal_1/TXT_2_1_46_6_0_1` | GameText（active=False，内容同为 `玩具祈愿`，误读会导致判定失败） |
| 顶部资源栏 | `money_01/Num`（券）、`money_02/Num`（钻石） | GameText |

> 关键修正（gacha-0003 实测）：`txt_costnum_one` 位于 `btn_chouka1/xiaohao_group_1/` 下，`txt_costnum_ten` 位于 `btn_chouka2/xiaohao_group/` 下；直接 `Find("btn_chouka1/txt_costnum_one")` 返回 null。

## 3.1 概率页已验证节点（gacha-0003）

| 语义 | 路径（相对 UI_DrawCard_RatePreviewView） | 组件 |
|------|------|------|
| 关闭按钮 | `btn_close` | GameButton |
| 分组标题+概率 | `biaoti_group/TXT_2_5_46_0_0`（4 个同名节点） | GameText |
| 分组容器 | `Container_Card`（实测 4 个，与 RewardDropGroup 4 组一一对应） | GameObject |

实测概率文本：`传说玩具2.50%` / `史诗玩具5.00%` / `稀有玩具37.00%` / `普通玩具55.50%`（合计 100%）。

## 3.2 结果页已验证节点（gacha-0003）

| 语义 | 路径（相对 UI_DrawCard_ResultView） | 组件 |
|------|------|------|
| 单抽/再抽1次 | `btn_chouka1`（标题 `TXT_2_32_52_7_0_1=再抽1次`，费用 `xiaohao_group_1/TXT_1_2_30_0_0_1`） | GameButton |
| 十连/再抽10次 | `btn_chouka2`（标题 `TXT_2_32_52_7_0=再抽10次`，费用 `xiaohao_group/TXT_1_2_30_0_0`） | GameButton |
| 关闭结果页 | `BGCloseBtn` | GameButton |
| 单抽分组 | `danchou_group`（单抽时 active=True） | GameObject |
| 十连分组 | `shilian_group`（十连时 active=True） | GameObject |
| 卡片模板 | `Pre_wanju_daka` / `Pre_wanju_daka_1..9`（十连实测 21 个卡片节点） | GameObject |

## 4. 数据层状态读取（已实测）

命名空间：`Game.Logic.DrawCardContainer.DrawCardDataMgr`；道具：`Game.Logic.ItemDataMgr`；服务器时间：全局 `ServerTime`。

> 注意：`DrawCardDataMgr.Inst` 为 `BaseContainer<T>.Inst` 继承属性，反射获取时必须使用 `BindingFlags.Public|Static|FlattenHierarchy`；仅用 Public|Static 会得到 `instProp=False`。

| 用途 | 调用 |
|------|------|
| 当前卡池 | `DrawCardDataMgr.Inst.GetCurrentPoolId()` → 实测 `100001` |
| 卡池数据 | `DrawCardDataMgr.Inst.GetCurrentCardPoolData()` |
| 开放状态 | `cp.IsOpen`（gacha-0003 实测恒为 `False`，单位不一致问题依旧） |
| 优先消耗（券） | `cp.PriorityItemId`（实测 `1004000`）、`cp.PriorityItemCount`（`1`） |
| 备用消耗（钻石） | `cp.FallbackResId`（实测 `2`）、`cp.FallbackResCount`（`100`） |
| 保底剩余 | `cp.UrGuaranteeRemain`（50）、`cp.SsrGuaranteeRemain`（25） |
| 抽数计数 | `cp.UrDrawCount`、`cp.SsrDrawCount`（每次单抽/十连均 +1，非逐次累加十连） |
| 消耗检测 | `DrawCardDataMgr.Inst.CheckCanDraw(poolId, drawCount)` → `CostCheckResult`；`CostType`：0=优先道具足够、1=仅备用、2=卡池缺失、3=混合扣除 |
| 最近结果 | `DrawCardDataMgr.Inst.GetLastDrawResult()` → `DrawResultData{PoolId, Items(ItemId/ItemCount/Rarity/IsNew/HighEffect/ItemType), HasNewToy, DuplicateToyFragments, TotalCount}` |
| 券数量 | `ItemDataMgr.Inst.GetItemCount(1004000)` |
| 钻石数量 | `ItemDataMgr.Inst.GetItemCount(2)` |
| 卡池配置 | `cp.TableData.RewardDropGroup`（实测 `[19100001,19100002,19100003,19100004]`，4 组）、`SingleItem=[1004000,1]`、`SingleRes=[2,100]` |

## 5. 测试数据构造（已实测）

| 目的 | 调用 |
|------|------|
| 补抽卡券 | `Game.Logic.GlobalMsgMgr.Inst.AISendGMAddItem(1004000, N)`（实测有效，600 到账） |
| 补钻石 | `Game.Logic.GlobalMsgMgr.Inst.AISendGMAddItem(2, N)`（实测有效，500000 到账） |
| 补代币 | `Game.Logic.GlobalMsgMgr.Inst.AISendGMAddMoney(Game.Core.MoneyType.None, N)` |
| 扣道具（构造不足/边界） | `Game.Logic.GlobalMsgMgr.Inst.AISendGMRemoveItem(itemId, N)`（**gacha-0003 实测不生效**：券恒 599/600） |
| 扣道具（负值 AddItem） | `AISendGMAddItem(1004000, -N)`（**实测不生效**） |
| 扣代币 | `Game.Logic.GlobalMsgMgr.Inst.AISendGMRemoveMoney(moneyType, N)`（**实测不生效**：钻石恒 500000） |

> 结论：GM 仅“添加”方向生效；所有精确资源边界（券=0/1/9/10、钻石=C1/C1-1/C10）无法构造，相关用例按 `test_inconclusive` 处理。

## 6. 抽卡链路实测（gacha-0003）

1. `btn_chouka1.ExecuteButtonClick()` → 券 600→599，`GetLastDrawResult()` 变为 `cnt=1`。
2. `btn_chouka2.ExecuteButtonClick()` → 券 600→590，钻石不变，`GetLastDrawResult()` 变为 `cnt=10`（含 `IsNew=True` 项与 `DuplicateToyFragments`）。
3. 自动出现 `UI_DrawCard_ResultView`（Canvas3）与 `UI_GetReward`（Canvas4）。
4. 关闭：`UI_DrawCard_ResultView/BGCloseBtn.ExecuteButtonClick()` 或 `TestHelper.CloseUI("UI_DrawCard_ResultView")`；`UI_GetReward` 用 `TestHelper.CloseUI("UI_GetReward")`。
5. 每抽 1 次 `UrDrawCount`/`SsrDrawCount` 各 +1（十连也只 +1，非 +10）；`UrGuaranteeRemain` 同步 -1。

## 7. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| `UI_DrawCard_Main` 卡池开放状态 | `CardPoolData.IsOpen` 恒为 `False`（单位不一致），但单抽/十连链路本身正常 | 判断可抽性使用 `CheckCanDraw(...).CanDraw`，不使用 `IsOpen` | 2026-11-02 |
| `UI_DrawCard_RatePreviewView/biaoti_group/TXT_2_5_46_0_0` | 概率文本颜色恒为 `#3A3347`，未按品质色着色（gacha-0002/gacha-0003 均复现） | 无（产品问题，ISSUE-GAC-001） | 2026-11-04 |
| `normal_1/TXT_2_1_46_6_0_1` | 读取页签标题误取未选中态节点（active=False），导致标题判定为空 | 标题必须取 `xuanzhong_1/TXT_2_2_46_6_0_1` | 2026-11-04 |
| `GlobalMsgMgr.AISendGMRemoveItem` / 负值 AddItem | GM 扣除不生效，券/钻石无法精确置值 | 无；精确边界用例记 `test_inconclusive` | 2026-11-04 |
| `btn_chouka1/txt_costnum_one` | 直接拼接该路径返回 null | 使用 `btn_chouka1/xiaohao_group_1/txt_costnum_one` | 2026-11-04 |

## 8. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| `gacha-open` | TC-GAC-001~003 | 入口打开、解锁校验 |
| `gacha-prob` | TC-GAC-004~008、010~011 | 概率页、保底提示 |
| `gacha-single` | TC-GAC-009、012~017、024 | 单抽消耗与免费/券 |
| `gacha-diamond` | TC-GAC-018~023 | 钻石二次确认 |
| `gacha-ten` | TC-GAC-026~034、039~040 | 十连消耗与结果页 |
| `gacha-display` | TC-GAC-025、035~038、041~043 | 动画跳过与再次抽取 |
| `gacha-pity` | TC-GAC-044~047 | 保底掉落与计数 |
| `gacha-network` | TC-GAC-048 | 断网/超时/重复提交 |
