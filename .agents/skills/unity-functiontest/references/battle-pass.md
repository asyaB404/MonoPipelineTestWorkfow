# battle-pass 运行时参考（战令面板）

- 创建时间：2026-10-29
- 创建人：Cyou（unity-functiontest 运行时实测）
- 功能简介：战令（通行证）面板的运行时节点路径、触发方式、Logic 字段与状态断言口径。
- 参数说明：路径均来自本轮 PlayMode 实测；build_guid 见 run-log setup 记录。

## 一、目标 UI 与进入方式

| 项 | 值 |
| --- | --- |
| 面板根节点 | `UI_MainPassPanel` |
| 入口（实测有效） | `UI_Main/btn_zhanling`（active=true，`btn_zhanling/lockstate` active=false） |
| 另一入口 | `UI_Main/btn_shop` → 商城（实测商城无「基金」页签，与需求文档不符） |
| 登录前置 | `CyStarRoad.Test.TestBoot.Boot()`，实测返回 `login_triggered`，轮询后 `UI_LoginGame=false` 且 `UI_Main=true` |
| Logic 类型 | `HotFix_Project.UI_MainPassPanel_Logic`（程序集 CyStarRoad） |
| Logic 获取 | `panel.GetComponent("GameFramework.Logic.BaseUI")` → `m_MonoInvocationAdapter` → `m_Instance` |

## 二、Logic 关键字段（本轮实测值）

| 字段 | 实测值 | 含义 |
| --- | --- | --- |
| `curFundGrade` | 0 | 当前战令等级 |
| `isBuyed` | False | 是否已购买进阶战令 |
| `_configList` | count=20 | 战令配置列表 |
| `_configIndexById` | count=20 | 配置索引字典 |
| `_specialGiftIndices` | count=2 | 特殊奖励索引 |
| `_lastVisibleIndex` | 6 | 当前可见末尾索引 |
| `_lastNextStageIndex` | 9 | 下一阶段索引 |

## 三、关键节点路径

| 语义 | 路径 | 实测 |
| --- | --- | --- |
| 标题 | `Image_RootBg/Tex_Title2` | 进阶战令 |
| 免费奖励标题 | `Image_RootBg/Tex_Title1` | 免费奖励 |
| 标题副文案 | `Image_RootBg/Tex_Title1_1` | 通关关卡后可解锁大量奖励！ |
| 剩余时间 | `Spr_TitleTop_Bg/timer_group/txt_timer` | 26天14时 |
| 一键领取按钮 | `BottomTab/btn_lingqu` | active=true，文本「一键领取」 |
| 付费按钮 | `BottomTab/btn_goumai` | active=true，价格 `txt_costNum=￥98` |
| 折扣文案 | `BottomTab/btn_goumai/Img_Common_zhekou/TXT_1_2_30_6_0` | 立得 |
| 折扣数量 | `BottomTab/btn_goumai/Img_Common_zhekou/txt_getNum` | 980 |
| 已购买按钮 | `BottomTab/Btn_Buyed` | active=false（未购买态） |
| 帮助按钮 | `btn_help` | active=true |
| 返回按钮 | `BottomTab/mainTab/btn_back` | active=true |
| 战令页签 | `BottomTab/mainTab/btn_zhanling` | active=true |
| 合成页签 | `BottomTab/subTab_group/Scr_H30/btn_hecheng` | active=false |
| 等级列表容器 | `Image_RootBg/ScrollView/Viewport/Content` | 子项 `EditorRuntime_Content_0..7` |
| 进度分段容器 | `Image_RootBg/ScrollView/Viewport/Content_2/lvBg_Runtime` | 8 个 `Text_Lv`（1..8） |
| 当前等级项 | `.../EditorRuntime_Content_0/lvBg/Text_Lv` | 1 |
| 下一阶段 | `BottomTab/NextStage_Obj_RankItem/lvBg/Text_Lv` | 10 |

## 四、状态断言口径

- 高亮态：奖励项子节点 `ImageHighLight`（active=true 表示可领取高亮）
- 遮罩/未完成态：奖励项子节点 `Image_Black`（active=true 表示遮罩）
- 已购买态：`isBuyed=true` 且 `BottomTab/Btn_Buyed` active=true、`BottomTab/btn_goumai` active=false
- 等级：`curFundGrade` 与等级节点 `lvBg/Text_Lv` 交叉核对

## 五、本轮实测缺失节点（不可构造）

以下按需求文档应存在，但本轮构建的 `UI_MainPassPanel` 下**未找到**任何匹配节点，相关用例按条件不可构造处理：

| 需求项 | 查找关键字 | 结果 |
| --- | --- | --- |
| 活动 banner | banner / Banner | 无匹配节点 |
| 奖励预览按钮与弹窗 | preview / Preview / yulan | 无匹配节点 |
| 返利比文本 | rebate / fanli | 无匹配节点 |

## 六、已知问题

| 节点 | 现象 | 兜底方案 | 确认时间 |
| --- | --- | --- | --- |
| `UI_MainPassPanel` Logic 反射 | 用全局扫描的 `logicType.GetField()` 读实例字段会抛「字段不属于目标对象」并冻结整轮 | 必须用 `logic.GetType().GetField(name, flags)`，并断言 `f.DeclaringType == logic.GetType()` | 2026-10-29 |

## 七、用例分组建议

| 分组 | 用例 | 共享前置 |
| --- | --- | --- |
| G1-entry | TC-BP-001/002/003/004/005/072 | 主页面 + 入口 |
| G2-display | TC-BP-006~020, 029, 051~061 | 面板已打开（只读） |
| G3-tabs | TC-BP-021/022/023/024 | 面板已打开 + 页签 |
| G4-rewards | TC-BP-025/026/027/028, 030~034 | 面板已打开 + 奖励区 |
| G5-preview | TC-BP-035/036/037/038 | 预览按钮（本轮缺失） |
| G6-claim | TC-BP-039~050 | 可领取态 |
| G7-pay | TC-BP-062~068 | 未购买态 |
| G8-abnormal | TC-BP-069/070/071 | 异常条件 |
