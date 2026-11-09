# Mono Pipeline Project

<!-- 创建日期：2026-11-06（Asia/Shanghai）；创建人：Codex；更新日期：2026-11-09；功能：内部交付Mono PC测试工作流及离线依赖；参数：目标Unity项目、已有Mono Development PC包、实际授权及用例。 -->

用于公司内部选择性部署，目录组织参考FunctionTest_2_5_1；不是完整Unity游戏工程，也不包含已构建Player。原公共技能作者归属保持不变，本次整理、30秒启动预算及固定登录精简由Codex完成。没有配置Git远端或上传。

## 目录

| 目录 | 内容 | 部署方式 |
| --- | --- | --- |
| `.agents/skills/mono-pipeline-functiontest` | PC执行宿主、模板、公共源码、原ZIP及许可、交付清单 | 整个技能目录复制到目标项目，不挑选其内部文件 |
| `.agents/skills`其余9个技能 | 原父Workflow、生成用例、静态UI参考、图像对比、统计、用量及上传；`unity-functiontest`供父流程启动问题和方法参考 | 按使用场景补齐，保留现有同版本部署 |
| `Assets/MonoPipelineFunctionTest`及同名`.meta` | 公共运行入口、反射、取证和编辑器构建辅助四源及GUID | 仅在目标尚未接入且需要重新出包时选择 |
| `Assets/Editor/ClientEditor/GlobalMonoPipelineGameClientBuild.cs`及`.meta` | 同GameClient框架的Mono打包菜单及原管线适配器 | 先合并下述框架依赖，再按原路径加入；其他框架不直接套用 |
| `Assets/Editor/Core`、`Assets/Scripts/GameFramework` | 6个当前框架依赖源码及`.meta`，包含3处管线重载、菜单排序、Mono资源生成和预加载守卫 | 按需对比合并已有文件，不能将整个`Assets`直接覆盖目标工程 |
| `Packages` | 7个原归档展开的Unity依赖，包含原DLL、元数据及许可 | 检查目标既有版本后逐包合并，不整目录覆盖 |
| `Tools/AI` | 需求文档预处理、证据整理、Markdown及可选Python依赖清单 | 需要文档处理时复制；不是Mono运行宿主的依赖 |

10个技能名：`mono-pipeline-functiontest`、`functiontest-workflow`、`testcase-gen`、`testcase-mcp-complete`、`ui-quick-reference`、`ui-image-diff`、`functiontest-report-json`、`check-cyoucode-spend`、`functiontest-json-upload`、`unity-functiontest`。

## 选择性部署

1. 已有可用Mono测试包：复制Mono技能即可直接使用；需完整父流程时按原契约补齐公共技能。明确以`mono-pipeline-functiontest`承接PC执行，不因父文本提到编辑器而调用Unity MCP。父Workflow原文未修改，也没有把它伪装成自动识别Mono的新版入口；协作细则见[workflow-contract.md](.agents/skills/mono-pipeline-functiontest/references/workflow-contract.md)。
2. 新项目需要首次接入：先对比公共`Assets`源码、GUID及各依赖；优先按Mono技能的`unity-preview`与批准后的`unity-apply`做文件级接入，或人工备份后选择性复制相同文件。不要同时重复接入，不覆盖目标`Packages/manifest.json`、锁文件、业务源码或既有配置。源码复制成功不代表已经完成Unity编译、原资源管线构建或Player验收。
3. 同GameClient框架需要构建菜单：仓库已按工程路径提供菜单和6个框架依赖源码，共7个`.cs`及7个`.meta`；先按[编辑器依赖与迁移](Doc/AI开发文档/MonoPipeline编辑器依赖与迁移.md)核对目标并对比合并，再选择菜单文件。Skill内[四文件增量补丁](.agents/skills/mono-pipeline-functiontest/assets/adapters/GameClient/framework-overloads.patch)仍保留，但它不包含Mono资源生成和预加载守卫，不能只合并该补丁就视为完整迁移。框架其余实现、HybridCLR、SDK、资源和服务端仍由目标项目提供，不套用到其他框架。已有现包不因本次交付补全要求重打。

## 依赖

宿主仅需要已有Python 3.10+标准库，不需要Unity CLI、MCP服务器或本机Python安装目录。本仓库不携带解释器；实际运行仍需目标机器Python及合格Windows Mono Development测试包。

| Unity包 | 原锁定版本 |
| --- | --- |
| `com.unity.pipeline` | `0.6.0-exp.1-unity2022` |
| `com.unity.nuget.mono-cecil` | `1.11.5` |
| `com.unity.ugui` | `1.0.0` |
| `com.unity.inputsystem` | `1.14.0` |
| `com.unity.nuget.newtonsoft-json` | `3.2.1` |
| `com.unity.test-framework` | `1.1.33` |
| `com.unity.ext.nunit` | `1.0.6` |

7个原ZIP、2599个成员摘要及引擎内建模块要求保存在[依赖清单](.agents/skills/mono-pipeline-functiontest/assets/dependencies/catalog.json)。内建模块由Unity安装提供，不伪造额外离线包。`Packages`为同一归档原字节展开，不是从当前工程随意拷贝的其他版本。

需要本地Word/Excel处理时，按`Tools/AI/requirements-functiontest.txt`准备依赖；其中版本来自本次实际已安装环境，包含两个传递依赖，不代表所有Python版本均已实跑，也不要求每次执行先安装。线上用例生成和日志上传仍需公司网络、相应工具与实际授权，仓库不携带认证信息。

## 启动与登录

启动就绪轮询默认总预算30秒，立即检查、就绪即继续；用户明确给出其他预算时使用该预算，超时不重启、不自动延长。该项为Agent准备阶段规则，不改变既有连接或业务动作超时，不承诺启动一定在30秒内完成。

中台固定登录按钮：`GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame/LoginBtns/LoginButton`。复用已有登录许可，通过内置按钮动作点击一次；动作后新帧确认`UI_LoginGame`不再激活即完成登录准备，不再固定读取协议、账号、SDK和主界面。业务页面、解锁和资源由各用例分别检查；启动空场景不算已登录。详见[固定登录流程](.agents/skills/mono-pipeline-functiontest/references/login-navigation.md)。

## 通用业务执行

先保留零资源、边界及计次初态，再按真实需求补充最少资源，不在共享准备中统一加大量资源。账号状态不合适且已批准换号时，优先在初始化之前选择一次新账号；不默认每例换号，不在旧轮改PID/许可，不借换号恢复未知动作。当前不提供跨账号多轮结果自动去重合并。

`plan-check`新增`planning_summary`，展示拟状态、实际动作/只读覆盖、无业务验证路径及前置原文到字段的绑定，供Agent审阅；不自动理解字段语义或判定通过。`run-suite`自检保存在返回JSON的`selfcheck`，不再在JSON前打印普通文本。

一条原步骤可包含不同内置按钮的必要顺序交互，各动作仍需当前实例、最新before、独立守卫及新帧；同一路径、同一组件/节点实例或混用手写脚本的重复动作仍拒绝。先完成需要交互的当前阶段，再等待最终完成；原文未要求关页时，不把额外清理设为通过条件。现有8个运行模块、命令和计划格式保持，不新增循环、自动交易重试或功能专用通过表。

操作细则及适用边界见[通用业务执行](.agents/skills/mono-pipeline-functiontest/references/business-execution.md)。当前版本不自动修正以前生成的错误业务计划；Agent须按当前原文和现场生成新草稿，不改历史已登记计划或final。改动在包外，无需因此重打已有PC包；实际passed及总耗时仍需新轮实机验证。

## 校验与版本

在仓库根目录只读核验完整Mono技能：

```powershell
py -3 -X utf8 -I -B .agents/skills/mono-pipeline-functiontest/scripts/cli.py delivery-verify
```

Git基线提交`1797bdc926160655ebdf4b8138e10771ab7674b4`保存本次精简前版本；后续提交单独记录精简，便于比较和回退。`.gitattributes`保留文件原字节，避免换行转换破坏清单摘要；普通使用不刷新清单。

打包侧新增7个源码及元数据的路径、大小、SHA256、作用与合并要求另见[mono-build-files.json](Tools/AI/mono-build-files.json)；这份清单不替代Skill自身交付清单，也不代表已经在目标工程编译或构建成功。

本仓库不包含旧PC技能、MCP服务器、历史运行产物、临时脚本、描述符、Player或账号令牌。`unity-functiontest`是随父流程保留的原参考副本，其中历史PC/MCP引用不是Mono依赖，也不保证在本仓库独立运行；需编辑器MCP测试时使用原FunctionTest交付，不自动切换后端。父Workflow的`config.json`按源项目原样保留，部署时应核实其用户名/项目组兜底值；运行时仍优先使用真实Cyou环境。

仅限原授权范围内公司内部使用，保留[内部迁移许可](.agents/skills/mono-pipeline-functiontest/references/internal-license.md)及各包原许可，不授予公开再分发权限。离线检查不代替公司CyouCode实机验收，不承诺提高业务passed数。

## 修改记录

2026-11-06，Codex：补齐原先仅位于Skill内部的打包菜单，按工程路径提供7个源码和7个元数据文件，补充Mono资源生成、AOT预加载与目标框架依赖说明；当前工程、Skill执行逻辑、父Workflow和原7个依赖包不改，未触发构建。

2026-11-09，Codex：从MCP/Mono差异提炼通用状态准备、结果依赖及必要界面交互；增加轻量计划概况，修正同一步内不同按钮被一律拒绝的问题，批自检改为结构化返回。没有加入抽卡编号或专用逻辑，原打包交付、父Workflow及公共子技能保持。

2026-11-09，Codex：依据CyouCode第15轮48例报告补强共享准备的目标功能可达核验与必要交互检查，并修正对应隔离测试夹具。未解锁负例仍须单独验证；未授权换号不执行。完整隔离回归316/316通过，实机passed变化待CyouCode新轮验证；未修改PC包、父Workflow或游戏业务代码。
