# 2026-11-12 上阵/战令交叉对照与Codex修复

<!-- 创建日期：2026-11-12；创建人：Codex；功能：保存近期CyouCode实测事实及Codex本轮优化/验证记录；参数：相同原用例、两侧账号/权限边界及离线回归。原测试日志与历史建议归Cyou/CyouCode，本轮分析、方案和代码修改归Codex。 -->

## CyouCode实测事实

来源为GameClient的`.ai/ai_logs/2026-11-12（mono+pipeline侧）.md`、`2026-11-12-02（战令mono+pipeline侧）.md`、`2026-11-12-03（战令MCP侧）.md`及`2026-11-10（MCP侧）.md`（上阵）。本文件为讨论摘要，不替代原报告/journal；不复制账号、PID、令牌或机器输出根。

| 样例 | 总例数 | MCP passed/failed/blocked/inconclusive | Mono passed/failed/blocked/inconclusive |
| --- | --- | --- | --- |
| 上阵0002 | 40 | 30 / 3 / 0 / 7 | 23 / 2 / 10 / 5 |
| 战令0005 | 42 | 20 / 1 / 0 / 21 | 3 / 0 / 17 / 22 |

两侧账号初态、授权和导航覆盖不完全相同，不将差额等同于可恢复passed。战令MCP侧实际领取了奖励，Mono侧没有领取；原步骤“商城→基金页签→入口”也不能用直接大厅入口点击代替。MCP日志记录编译阶段存在超时和长间隔，不能把其父流程总耗时当作纯业务执行速度。

Mono战令日志第73至82行及第297行披露：TC-FREE-001/002/003用`GetProperty("UILogicInst")`，但实际`UIBinder.cs:530`声明`public object UILogicInst;`，导致全零失真。后续正确读取为`normal_unlocked=6`，已登记final保持不变。`CurrentStage=1000020`来自`GradeFundsDataMgr.RecalculateCurrentStage`的`LevelStage`，不能直接当等级；MCP同时读到`curFundGrade=0`，还需按具体原预期核对显示语义。

Mono上阵日志第59至70行记录：367条intent/command_result、361次connection_checked，40例完整收口，23 passed。其“多次CLI调用”的成本有明确依据，但日志不足以单独量化Player执行与Agent编排时间。

## Codex修改

- 复用现有observe管道，统一字段/属性读取；`logic_field`兼容公开`UILogicInst`及旧适配器，保持单实例要求。新增`member_probe`在限定root下一次读取多路径，逐成员保留类型、可读性、真实值与错误。
- 缺成员、getter异常、多实例歧义、空中间对象不补0/false；枚举/字符显式转文本，最终拒绝运行时对象、委托与非有限数值。不同对象即使值相等也不合并；同一逻辑对象的重复绑定可去重。
- Skill入口和业务参考合并重复门禁段落，明确读取质量先于业务状态判断、字段语义核对、按已有授权安排前后态，以及稳定组用一次run-suite。接口说明集中在host-contract，不新增业务特例脚本或额外执行器。
- 原步骤、独立比较、真实动作/新帧、失败锁存、不可变来源及交付校验保持。范围仅维护仓库的Skill、测试和优化文档；工程内旧Skill副本、父Workflow、PC包和GameClient源码未改。

## Codex验证

首轮定向回归：9项通过、0失败、0错误、0跳过，包含实际生成C#的编译执行。随后增加真实C#读取结果到宿主比较/final/audit的闭环验证，真实0通过、真实非零失败、成员缺失未定论。

首次完整回归：`total=324 passed=322 failures=1 errors=0 skipped=1`，420.189秒。唯一失败为新增`host-contract.md#成员读取`锚点不被已有包内文件链接检查支持；修正为普通文件链接，未修改链接检查或运行代码。跳过项是缺少现有Editor引用的可选Windows长路径C#集成；本轮新增成员读取的C#编译执行均实际完成。修复后的定向复验及交付核验结果另记，不相加冒充一次完整全通过。

最终定向复验：`scripts.tests.test_portable scripts.tests.test_compatibility`，`total=7 passed=7 failures=0 errors=0 skipped=0`，8.914秒，包含原失败的链接检查及独立迁移CLI。Skill格式检查通过。交付清单100成员核验通过，SHA256为`f74e8371f956b3233f268c707d8ef52aca211a9402c701ddfb57aad460f763cd`。完整回归后仅修正文档链接，没有再改运行代码；未重复运行完整回归。

部署边界：本次修改位于`Mono-Pipeline-Project`维护仓库main。检查发现GameClient工程内Skill副本仍与维护仓库不同（其`session.py`为228614字节，`SKILL.md`为11481字节），本轮没有覆盖该副本；CyouCode若继续运行该旧副本，不会使用本轮修复。验收必须记录实际执行Skill目录与交付摘要。当前没有新的CyouCode实机结果，不增加业务passed计数，不承诺具体增幅或耗时。

公司Agent验收关注相同用例/版本/权限/账号初态下的正式四状态，逐例检查原步骤与预期证据，同时记录命令数、连接次数、准备/业务/报告分项和总耗时；读数修正后若业务反例成立仍为failed。
