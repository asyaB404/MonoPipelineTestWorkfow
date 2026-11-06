# toy-upgrade-star 运行时 reference（PC universal 灰盒实测）

<!-- 创建日期：2026-10-20；创建人：Cyou；功能：记录玩具（棋子）升星/升级界面在 windowcustom 测试包中的实测进入方式与稳定节点；参数：UI 根路径、进入链、可执行断言节点。 -->

## 实测环境

- 目标包：`Bin/App/development/windowcustom/windowcustom.exe`（universal 灰盒，PID 33072，端口 9001）
- 后端：universal（attach 单实例，`engine_input` + `ui.click`）
- 场景句柄：`-86::`（每次启动会变化，需按当轮 `discover` 结果使用）
- 单帧对象规模：登录界面 191、主界面 296、玩具列表 940、棋子详情（升级页）1243、棋子详情（升星页）1430

## 进入链（按顺序点击）

1. 登录界面 `Canvas0[0]/UI_LoginGame[0]/LoginBtns[5]/LoginButton[0]` 点击登录（`Test[10]` 为隐藏入口，`active=false`，不可点击）
2. 主界面底部页签 `Canvas1[1]/UI_MainBottom[0]/buttonLayout[1]/UC_MainBottom_btn_TabItem[3]/button[0]`（名称文本「玩具」）
3. 玩具列表 `Canvas0[0]/UI_ToyMainList[1]/ScrollView[1]/Viewport[0]/Content[1]/EditorRuntime_Content_0[0]/GameButton[8]`
4. 棋子详情默认打开「升级」页 `Canvas2[2]/UI_ToyTrain[0]/Dynamic_ToyLvUp[1]`
5. 点击 `Canvas2[2]/UI_ToyTrain[0]/daohang[4]/btn_shengxing[2]` 切到「升星」页 `Dynamic_ToyStarUp[2]`

## 已实测稳定断言节点（升星页）

| 语义 | 相对 UI_ToyTrain[0] 的路径 | 属性 |
| --- | --- | --- |
| 升星页激活 | `Dynamic_ToyStarUp[2]` | active |
| 棋子名称 | `Dynamic_ToyStarUp[2]/UI_ToyTrain_StarUp(Clone)[0]/Bg[0]/qixixinxi[1]/wanjumingzi[5]/bigbg_qizi_mingzidi[0]/TXT_2_2_56_6_0[1]` | text |
| 定位描述 | `.../Bg[0]/qixixinxi[1]/wanjumingzi[5]/TXT_1_2_40_6_0[1]` | text |
| 星级组 | `.../Bg[0]/qixixinxi[1]/wanjumingzi[5]/UC_CommonStarGroup[2]` | active |
| 等级/上限 | `.../bottom[1]/xiangqing[1]/Img_common_frame4[1]/TXT_1_5_36_0_0[0]` | text |
| 战力 | `.../bottom[1]/zhanli[0]/TXT_2_27_56_0_0[3]` | text |
| 碎片/拥有态 | `.../bottom[1]/xiangqing[1]/Img_common_frame4[1]/TXT_1_5_36_0_1[1]` | text |
| 未达门槛文本 | `.../bottom[1]/UnLock_Buttom_Node[4]/qushengji[1]/btn_qushengji[0]/TXT_2_2_50_2_0[1]` | text（实测「去升级」） |
| 去升级按钮 | `.../bottom[1]/UnLock_Buttom_Node[4]/qushengji[1]/btn_qushengji[0]` | ui.click |
| 满级节点 | `.../bottom[1]/Lock_Buttom_Node[5]` | active（当前 false） |
| 上一/下一棋子 | `.../Bg[0]/qixixinxi[1]/btn_shangyige[2]` / `btn_xiayige[3]` | active + ui.click |

## 已知边界（本轮实测）

1. 切页签（`btn_shengji[1]` ↔ `btn_shengxing[2]`）会改变运行时对象集合。**该限制已于 2026-10-20 由授权子集语义解除**：宿主只校验计划实际引用的对象，未引用的新增对象不再触发漂移拒绝（见 [`authorizes()`](../../../../Tools/AI/functiontest_runtime/universal/capabilities.py:265)）。需重构建含新版代理的测试包后生效，旧包行为不变。跨两个页签时也可对各页签分别 `discover` 后用 `pc_agent_catalog.py merge` 合并为一份并集基线。
2. 升星页属性条目父节点当前未激活，条目子节点在剪枝清单中不可读，无属性提示点击入口。可用 `PC_TEST_AGENT_PRUNE_INACTIVE=0` 恢复递归枚举，或经业务只读状态注册层直接断言属性数值。
3. 区域A货币 `Num` 节点未暴露 `text` 属性，无法读取货币数量。同上，优先改用业务只读状态注册层（`PcTestAgentBusinessState`）读取货币数值，而不是依赖文本节点。
4. 剪枝开启时隐藏子树节点不可断言；需要深层断言时用 `PC_TEST_AGENT_PRUNE_INACTIVE=0` 重启代理。
5. 通用代理无 wait/拖拽/长按方法，列表滑动类用例仍无法映射。滚动方向的能力缺口已由 `ui.scroll`（垂直 ScrollRect）部分覆盖，拖拽入槽仍需后续支持。

## 需求冲突

- 棋子升星文档：星级上限 15 星；棋子系统文档：星级上限 10 星。本轮未取得配表基线，冲突保留待确认。

## 变更记录

- 2026-10-20：首次记录。本轮 `toy-upgrade-star-0013` 实测 48 条全集，passed=10、blocked=38（38 条为准备受阻，含页签切换与数据夹具缺口）。
- 2026-10-20：代理与宿主通用能力扩充后更新边界。页签切换漂移已放宽为授权子集语义；新增 `visible`/`slider`/`scroll_position` 只读属性与 `ui.set_slider`/`ui.scroll` 动作；新增业务只读状态注册层，可直接断言等级/碎片/货币等业务数值，减少依赖文本节点。上述均需重构建测试包后生效，本轮未重打，`blocked` 数量未重新实测。
