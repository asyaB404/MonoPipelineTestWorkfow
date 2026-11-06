# 玩具升级与升星培养页——离线 UI 参考

<!-- 维护日期：2026-09-23；维护人：Cyou；功能：主页面与升级/升星子页的静态定位、绑定及回调索引；输入：用户指定目标与当前预制体/源码。 -->

离线参考图谱 = 由预制体层级、自动生成绑定文件和逻辑源码构成的静态定位资料；本文不声明页面操作已通过验证。

## 1. 基本信息

| 属性 | 值 |
|---|---|
| 功能标识 | toy-upgrade-star |
| 界面名称 / 根节点 | [`UI_ToyTrain`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:6521) |
| 中文语义 | 玩具升级、升星共用培养外壳页；此语义由源码确认，不充当表内描述字段的读取结果 |
| 界面字符串常量 | [`UIID.UI_ToyTrain`](Assets/Scripts/CyStarRoad/Gen/Table/UIID.cs:410) |
| 表内数字编号 | 未核验，不推定 |
| 画布编号 | 2（沿用旧静态资料，未重新核验）；仅作候选，不据此生成场景绝对路径 |
| 主逻辑类型 | [`HotFix_Project.UI_ToyTrain_Logic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:28) |
| 主预制体 | [`UI_ToyTrain.prefab`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:1) |
| 维护工具 | [`scan_ui_references.py`](.agents/skills/ui-quick-reference/scripts/scan_ui_references.py:657) 的离线解析器与生成器；扫描结果结合绑定索引核对 |

## 2. 子页面与源码导航

| 子页面 | 中文语义 | 外壳组件字段 | 标签枚举 |
|---|---|---|---|
| [`UC_ToyLvUp`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:24961) | 升级子页 | [`UC_ToyLvUp_0_com`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:60) | [`ToyTrainTabType.LevelUp`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:24)，值为 0 |
| [`UC_ToyStarUp`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:10751) | 升星子页 | [`UC_ToyStarUp_1_com`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:64) | [`ToyTrainTabType.StarUp`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:25)，值为 1 |

源码入口为玩具卡片的 [`GameButton_0_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/item_toy_card_Logic.cs:181)：可激活分支优先处理激活，其余分支进入 [`OpenToyTrainPage()`](Assets/Scripts/CyStarRoad/UILogic/UICom/item_toy_card_Logic.cs:238)，并传入升级标签、玩具编号、分类和来源列表域。此处只记录导航线索，不提供直接创建页面的操作模板。

子页面身份以 [`InitUIReferences()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:161) 的赋值、[`RefreshView()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:380) 的分支和 [`RefreshTabPage()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:429) 的显隐条件为依据；两个页面对象的旧自动生成注释恰好对调，不能按该注释判定语义。

## 3. 主页面完整控件绑定

保留原 9 个自动生成普通控件，补齐 3 个子组件，共 12 个直接绑定。节点均从主预制体根开始，以反斜线分隔；绑定列表索引是判别同名节点的依据。

| 字段 | 类型 | 静态节点全路径 | 绑定索引 | 中文语义 | 响应接口 |
|---|---|---|---|---|---|
| [`btn_shengji_0_btn`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:22) | [`GameButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:22) | [`UI_ToyTrain\daohang\btn_shengji`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:8085) | [`GameButtonList[0]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:84) | 升级按钮-标签-切换升级页面 | [`OnClickLevelUpTab()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:177) |
| [`btn_shengxing_1_btn`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:26) | [`GameButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:26) | [`UI_ToyTrain\daohang\btn_shengxing`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:14780) | [`GameButtonList[1]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:85) | 升星按钮-标签-切换升星页面 | [`OnClickStarUpTab()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:182) |
| [`btn_back_2_btn`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:30) | [`GameButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:30) | [`UI_ToyTrain\daohang\btn_back`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:29429) | [`GameButtonList[2]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:86) | 返回按钮-关闭本页面 | [`OnClickCloseButton()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:187) |
| [`UC_ToyLvUp_0_go`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:35) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:35) | [`UI_ToyTrain\UC_ToyLvUp`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:24949) | [`GameObjectList[0]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:87) | 玩具升级子页；依据主逻辑赋值与标签分支 | — |
| [`UC_ToyStarUp_1_go`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:39) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:39) | [`UI_ToyTrain\UC_ToyStarUp`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:10739) | [`GameObjectList[1]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:88) | 玩具升星子页；依据主逻辑赋值与标签分支 | — |
| [`xuanzhong_1_2_go`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:43) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:43) | [`UI_ToyTrain\daohang\btn_shengji\xuanzhong_1`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:23449) | [`GameObjectList[2]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:89) | 升级按钮状态-选中 | — |
| [`normal_1_3_go`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:47) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:47) | [`UI_ToyTrain\daohang\btn_shengji\normal_1`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:4646) | [`GameObjectList[3]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:90) | 升级按钮状态-正常 | — |
| [`xuanzhong_4_go`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:51) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:51) | [`UI_ToyTrain\daohang\btn_shengxing\xuanzhong`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:20492) | [`GameObjectList[4]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:91) | 升星按钮状态-选中 | — |
| [`normal_5_go`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:55) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:55) | [`UI_ToyTrain\daohang\btn_shengxing\normal`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:15270) | [`GameObjectList[5]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:92) | 升星按钮状态-正常 | — |
| [`UC_ToyLvUp_0_com`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:60) | [`UC_ToyLvUp_Logic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:60) | [`UI_ToyTrain\UC_ToyLvUp`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:24988) | [`UIComList[0]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:93) | 升级子页逻辑 | — |
| [`UC_ToyStarUp_1_com`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:64) | [`UC_ToyStarUp_Logic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:64) | [`UI_ToyTrain\UC_ToyStarUp`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:10778) | [`UIComList[1]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:94) | 升星子页逻辑 | — |
| [`moneyRoot_2_com`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:68) | [`commonResource_Logic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:68) | [`UI_ToyTrain\moneyRoot`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:28958) | [`UIComList[2]`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:95) | 资源栏子组件 | — |

三个生成集合 [`UC_ToyLvUp_Logic_List`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:72)、[`UC_ToyStarUp_Logic_List`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:76)、[`commonResource_Logic_List`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:80) 分别只含对应子组件，赋值见 [`InitUIComBind()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_AutoGen.cs:96)，不是额外的场景节点。

页签私有别名 [`_levelUpTabButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:163)、[`_starUpTabButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:164) 分别指向表中的升级、升星按钮，不能当作节点名称。返回按钮通过嵌套源预制体 [`btn_back.prefab`](Assets/GameResource/UIResource/PublicResource/Prefab/Common/btn_back.prefab:129) 确认绑定在返回根对象，挂载于主页面导航容器。

## 4. 子页面操作字段

以下共 17 个按钮：升级页 9 个、升星页 8 个。表中点击/长按仅说明源码注册类型，不是执行结果。

### 升级子页

| 操作字段 | 静态节点全路径 | 绑定索引 | 输入类型 | 响应接口 | 中文语义 |
|---|---|---|---|---|---|
| [`btn_shengji1_0_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:22) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\shengji\btn_shengji1`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:2104) | [`GameButtonList[0]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:172) | 点击 | [`OnClickLevelUpOne()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:364) | 升级按钮-升一级 |
| [`btn_shengji2_1_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:26) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\shengji\btn_shengji2`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:8699) | [`GameButtonList[1]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:173) | 点击 | [`OnClickLevelUpFive()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:369) | 升级按钮-连续升5级 |
| [`btn_shangyige_2_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:30) | [`UI_ToyTrain\UC_ToyLvUp\Bg\qixixinxi\btn_shangyige`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:3519) | [`GameButtonList[2]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:174) | 点击 | [`OnClickPrevToy()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:374) | 上一个玩具；按回调递减索引，不沿用左右位置误注释 |
| [`btn_xiayige_3_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:34) | [`UI_ToyTrain\UC_ToyLvUp\Bg\qixixinxi\btn_xiayige`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:15753) | [`GameButtonList[3]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:175) | 点击 | [`OnClickNextToy()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:379) | 下一个玩具；按回调递增索引，不沿用左右位置误注释 |
| [`btn_xiangqing_4_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:38) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Img_common_frame4\btn_xiangqing`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:16035) | [`GameButtonList[4]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:176) | 点击 | [`OnClickAttributeOverviewButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:384) | 按钮-属性详情-点击打开属性详情页面 |
| [`btn_shengji2_5_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:42) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\qushengxing\btn_shengji2`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:12079) | [`GameButtonList[5]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:177) | 点击 | [`OnClickGoToStarUpButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:389) | 通知外壳切换升星页签 |
| [`btn_jinjie_6_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:46) | [`UI_ToyTrain\UC_ToyLvUp\Bg\qixixinxi\btn_jinjie`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:18291) | [`GameButtonList[6]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:178) | 点击 | [`OnClickAdvanceButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:394) | 按钮-进阶 |
| [`btn_longPress_7_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:50) | [`UI_ToyTrain\UC_ToyLvUp\bottom\zhanli\btn_longPress`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:10042) | [`GameButtonList[7]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:179) | 长按 | [`OnLongPressFightPower()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:401) | 长按显示具体数值 |
| [`btn_quhuoqu_8_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:54) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Lock_Buttom_Node\btn_quhuoqu`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:14094) | [`GameButtonList[8]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:180) | 点击 | [`OnClickAcquireToy()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:408) | 按钮-去获取-点击跳转到抽卡主页面 |

### 升星子页

| 操作字段 | 静态节点全路径 | 绑定索引 | 输入类型 | 响应接口 | 中文语义 |
|---|---|---|---|---|---|
| [`btn_shangyige_0_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:22) | [`UI_ToyTrain\UC_ToyStarUp\Bg\qixixinxi\btn_shangyige`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:11284) | [`GameButtonList[0]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:172) | 点击 | [`OnClickPreviousToyButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:326) | 按钮-左切换-点击切换上一个玩具 |
| [`btn_xiayige_1_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:26) | [`UI_ToyTrain\UC_ToyStarUp\Bg\qixixinxi\btn_xiayige`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:27403) | [`GameButtonList[1]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:173) | 点击 | [`OnClickNextToyButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:331) | 按钮-右切换-点击切换下一个玩具 |
| [`btn_shengji2_2_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:30) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node\shengji\btn_shengji2`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:27121) | [`GameButtonList[2]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:174) | 点击 | [`OnClickStarUpButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:336) | 发起升星流程 |
| [`btn_xiangqing_3_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:34) | [`UI_ToyTrain\UC_ToyStarUp\bottom\xiangqing\Img_common_frame4\btn_xiangqing`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:24615) | [`GameButtonList[3]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:175) | 点击 | [`OnClickAttributeOverviewButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:341) | 按钮-属性详情-点击打开属性详情页面 |
| [`btn_qushengji_4_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:38) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node\qushengji\btn_qushengji`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:43) | [`GameButtonList[4]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:176) | 点击 | [`OnClickGoToLevelUpButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:346) | 通知外壳切换升级页签 |
| [`btn_jinjie_5_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:42) | [`UI_ToyTrain\UC_ToyStarUp\Bg\qixixinxi\btn_jinjie`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:4403) | [`GameButtonList[5]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:177) | 点击 | [`OnClickAdvanceButton()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:351) | 按钮-进阶按钮 |
| [`btn_longPress_6_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:46) | [`UI_ToyTrain\UC_ToyStarUp\bottom\zhanli\btn_longPress`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:5318) | [`GameButtonList[6]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:178) | 长按 | [`OnLongPressFightPower()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:358) | 长按显示具体数值 |
| [`btn_quhuoqu_7_btn`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:50) | [`UI_ToyTrain\UC_ToyStarUp\bottom\Lock_Buttom_Node\btn_quhuoqu`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:1101) | [`GameButtonList[7]`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:179) | 点击 | [`OnClickAcquireToy()`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:365) | 按钮-去获取-点击跳转抽卡页面 |

升级页的五级升级与去升星按钮具有相同节点名，但绑定索引分别为 1 和 5，父容器分别是升级操作区与去升星提示区；必须用完整路径或所属子页的字段区分。

跨页操作由子页委托回到外壳：[`OnClickGoToStarUp`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:251) → [`OnClickGoToStarUpFromLevelUp()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:252)；[`OnClickGoToLevelUp`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:221) → [`OnClickGoToLevelUpFromStarUp()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:261)。两页选中玩具均经 [`OnSubPageSelectedToyChanged()`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:336) 同步到外壳。

长按战力不等同于普通点击；松开时的复位注册分别见 [`OnPressUp`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_Logic.cs:403) 与 [`OnPressUp`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_Logic.cs:360)。

## 5. 子页面状态与展示字段

这些字段可用于理解后续观察位置；这里只说明职责，不记录当前显示值或当前激活状态。子页的装饰图片、特效和内部通用组件不在此速查表的完整性承诺内，主页面的 12 项直接绑定不受影响。

### 升级子页

| 字段 | 类型 | 静态节点全路径 | 中文语义 |
|---|---|---|---|
| [`TXT_2_2_56_6_0_0_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:72) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:72) | [`UI_ToyTrain\UC_ToyLvUp\Bg\qixixinxi\wanjumingzi\bigbg_qizi_mingzidi\TXT_2_2_56_6_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:5643) | 玩具名称 |
| [`TXT_1_5_36_0_0_1_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:76) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:76) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Img_common_frame4\TXT_1_5_36_0_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:870) | 等级-富文本-languageid是2100910001要传入两个参数当前等级和最大等级 |
| [`TXT_1_2_40_6_0_2_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:80) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:80) | [`UI_ToyTrain\UC_ToyLvUp\Bg\qixixinxi\wanjumingzi\TXT_1_2_40_6_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:20291) | 玩具简介-toy表字段CharacterIntroduction |
| [`TXT_1_19_36_6_0_2_3_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:84) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:84) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\qushengxing\desc\TXT_1_19_36_6_0_2`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:21281) | 等级上限时的下一星级提示文本 |
| [`TXT_2_27_56_0_0_4_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:88) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:88) | [`UI_ToyTrain\UC_ToyLvUp\bottom\zhanli\TXT_2_27_56_0_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:19414) | 战力值 |
| [`TXT_1_5_36_0_1_5_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:92) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:92) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Img_common_frame4\TXT_1_5_36_0_1`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:4238) | 未拥有-在角色锁定或者未拥有时显示 |
| [`costItemContainer_0_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:97) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:97) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\shengji\costItemContainer`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:21663) | 消耗item的容器 |
| [`shengji_4_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:113) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:113) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\shengji`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:286) | 升级按钮容器-普通状态下显示 |
| [`qushengxing_5_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:117) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:117) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\qushengxing`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:10975) | 去升星状态容器 |
| [`manjizhuangtai_6_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:121) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:121) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node\manjizhuangtai`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:1431) | 状态-满级状态 |
| [`UnLock_Buttom_Node_11_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:141) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:141) | [`UI_ToyTrain\UC_ToyLvUp\bottom\UnLock_Buttom_Node`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:5768) | 底部容器-一级状态-玩具解锁状态下显示 |
| [`Lock_Buttom_Node_12_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:145) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:145) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Lock_Buttom_Node`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:27044) | 底部容器-一级状态-玩具未解锁状态下显示 |
| [`ScrollView_0_gsr`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:150) | [`GameScrollRect`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:150) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Img_common_frame4\ScrollView`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:21902) | 属性滚动列表 |
| [`scr_v20_1_gsr`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:154) | [`GameScrollRect`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyLvUp_AutoGen.cs:154) | [`UI_ToyTrain\UC_ToyLvUp\bottom\Img_common_frame2\scr_v20`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:19579) | 词条滚动列表 |

### 升星子页

| 字段 | 类型 | 静态节点全路径 | 中文语义 |
|---|---|---|---|
| [`TXT_2_2_56_6_0_0_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:68) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:68) | [`UI_ToyTrain\UC_ToyStarUp\Bg\qixixinxi\wanjumingzi\bigbg_qizi_mingzidi\TXT_2_2_56_6_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:11914) | 玩具名字 |
| [`TXT_2_27_56_0_0_1_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:72) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:72) | [`UI_ToyTrain\UC_ToyStarUp\bottom\zhanli\TXT_2_27_56_0_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:19936) | 战力值 |
| [`TXT_1_5_36_0_0_2_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:76) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:76) | [`UI_ToyTrain\UC_ToyStarUp\bottom\xiangqing\Img_common_frame4\TXT_1_5_36_0_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:27774) | 玩具等级 |
| [`TXT_1_2_40_6_0_3_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:80) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:80) | [`UI_ToyTrain\UC_ToyStarUp\Bg\qixixinxi\wanjumingzi\TXT_1_2_40_6_0`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:7920) | 玩具简介-toy表字段CharacterIntroduction |
| [`TXT_1_5_36_0_1_4_txt`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:84) | [`GameText`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:84) | [`UI_ToyTrain\UC_ToyStarUp\bottom\xiangqing\Img_common_frame4\TXT_1_5_36_0_1`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:14615) | 未拥有字体-在角色未解锁未拥有时显示 |
| [`costItemContainer_0_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:89) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:89) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node\shengji\costItemContainer`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:14337) | 容器-升星消耗品容器 |
| [`manjizhuangtai_4_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:105) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:105) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node\manjizhuangtai`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:17982) | 状态-满星级状态 |
| [`shengji_5_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:109) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:109) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node\shengji`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:13614) | 升星操作状态容器 |
| [`qushengji_6_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:113) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:113) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node\qushengji`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:25551) | 状态-去升级 |
| [`UnLock_Buttom_Node_9_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:125) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:125) | [`UI_ToyTrain\UC_ToyStarUp\bottom\UnLock_Buttom_Node`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:10399) | 底部容器-一级状态-玩具解锁的时候显示 |
| [`Lock_Buttom_Node_10_go`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:129) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:129) | [`UI_ToyTrain\UC_ToyStarUp\bottom\Lock_Buttom_Node`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:2842) | 底部容器-一级状态-玩具未解锁的时候显示 |
| [`ScrollView_0_gsr`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:134) | [`GameScrollRect`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:134) | [`UI_ToyTrain\UC_ToyStarUp\bottom\xiangqing\Img_common_frame4\ScrollView`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:11786) | 属性滚动列表 |
| [`scr_v20_1_gsr`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:138) | [`GameScrollRect`](Assets/Scripts/CyStarRoad/UILogic/UICom/UC_ToyStarUp_AutoGen.cs:138) | [`UI_ToyTrain\UC_ToyStarUp\bottom\xiangqing\Img_common_frame2\scr_v20`](Assets/GameResource/UIResource/UIPrefab/UI_ToyTrain/Prefab/UI_ToyTrain.prefab:20454) | 词条滚动列表 |

## 6. 主逻辑关键字段

| 字段 | 类型 | 中文用途 |
|---|---|---|
| [`_selectedTabIndex`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:35) | [`ToyTrainTabType`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:35) | 当前标签；升级为 0，升星为 1 |
| [`_currentToyId`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:40) | [`int`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:40) | 外壳共享的当前玩具编号 |
| [`_currentToyType`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:46) | [`int`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:46) | 当前玩具分类，作为子页过滤参数 |
| [`_currentViewType`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:52) | [`ToyDataMgr.ToyBagViewType`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:52) | 来源列表域；决定左右切换的数据集合 |
| [`_switchableToyDataList`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:58) | [`List<ToyDataMgr.ToyData>`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:58) | 外壳统一持有并传给两页的切换集合 |
| [`_levelUpTabButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:63) | [`GameButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:63) | 升级页签按钮别名 |
| [`_starUpTabButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:68) | [`GameButton`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:68) | 升星页签按钮别名 |
| [`_levelUpPage`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:73) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:73) | 升级页面对象 |
| [`_starUpPage`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:78) | [`GameObject`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:78) | 升星页面对象 |
| [`_levelUpLogic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:83) | [`UC_ToyLvUp_Logic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:83) | 升级子页逻辑 |
| [`_starUpLogic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:89) | [`UC_ToyStarUp_Logic`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:89) | 升星子页逻辑 |
| [`_isOpenParamSet`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:94) | [`bool`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:94) | 是否已设置打开参数，控制初次刷新 |
| [`_hasDispatchedTrainClosedEvent`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:99) | [`bool`](Assets/Scripts/CyStarRoad/UILogic/UI_ToyTrain/UI_ToyTrain_Logic.cs:99) | 避免重复派发关闭通知 |

## 7. 静态使用注意事项

- 固定扫描器得到的 98 是按节点名去重后的映射条目数；重复命名及嵌套预制体会使它小于完整层级，不能当作页面总节点数。本文按钮位置使用绑定索引与文件内引用复核。
- 当前保留的画布编号只是旧静态候选；表内数字编号未核验。这两项不阻塞后续测试，调用方须独立确定实际挂载位置。
- 两子页都包含同名按钮、消耗区和状态容器，字段与路径必须绑定所属子页；不得只用去掉后缀后的节点名全局检索。
- 按钮语义由所属页面和回调共同决定。去获取按钮的分支与解锁状态有关；静态回调注册不能推导任何一次操作已成功。

## 8. 静态维护记录

| 日期 | 维护人 | 变更 |
|---|---|---|
| 2026-09-23 | Cyou | 在原有根节点、界面字符串常量、画布候选、9 个普通字段和主逻辑字段基础上增量刷新；补齐子组件、17 个子页按钮、展示字段、来源列表域和中文语义；修正私有别名、返回节点和重复节点名映射；清理非静态内容及空模板；未修改业务、配置或测试代码。 |
