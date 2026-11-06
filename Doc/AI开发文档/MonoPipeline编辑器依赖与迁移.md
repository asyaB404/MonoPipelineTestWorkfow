# MonoPipeline编辑器依赖与迁移

<!-- 创建日期：2026-11-06（Asia/Shanghai）；创建人：Codex；功能：说明独立仓库中Mono构建菜单、框架依赖及选择性迁移边界；参数：匹配的GameClient/GameFramework目标、原公共四源、7个离线包和单独构建批准。既有源码作者及版权保持原样。 -->

适配器 = 将Mono测试构建接到目标原App/资源管线的项目专用代码。独立仓库已补齐菜单及直接相关框架源码的工程路径副本，不再只把菜单藏在Skill内部；这些是当前框架参考实现，不是完整游戏框架或任意Unity项目的一键打包SDK。

## 文件清单

下表路径相对仓库根；7个源码均携带原`.meta`。完整路径、大小、SHA256及合并要求记录于`Tools/AI/mono-build-files.json`。

| 文件 | 作用 | 迁移方式 |
| --- | --- | --- |
| `Assets/Editor/ClientEditor/GlobalMonoPipelineGameClientBuild.cs` | 注册`Game Tools/打包/Build/Build-App/Window-Mono-Pipeline测试包(新流程)`，临时选择Mono、Development、HybridCLR状态和Pipeline配置，执行原管线 | 同框架且目标缺失时新增，已有同名类型先比对，不重复放置Skill模板 |
| `Assets/Editor/Core/MenuPriorityConst.cs` | `BuildAppWindowMonoPipeline`菜单排序别名 | 只合并所需枚举项，保留目标现有菜单值 |
| `Assets/Scripts/GameFramework/Editor/Build/BuildPipelineX.cs` | 明确脚本后端、共享参数准备及本次平台工厂重载 | 合并相关方法，不覆盖其他构建、版本或性能工具修改 |
| `Assets/Scripts/GameFramework/Editor/Build/App/BuildAppPipeline.cs` | 将本次平台实例传给原App生命周期 | 合并类型化重载 |
| `Assets/Scripts/GameFramework/Editor/Build/App/Builder/AppBuilder.cs` | 使用显式平台执行原资源/构建生命周期，返回成功BuildReport | 合并重载，保留目标原生命周期 |
| `Assets/Scripts/GameFramework/Editor/Build/Res/Builder/Impl/ResBuilderScript.cs` | Mono时编译热更DLL、建立输出目录并跳过AOT生成；资源编辑状态在finally恢复 | 对比合并后端分支，不删目标原资源步骤 |
| `Assets/Scripts/GameFramework/Runtime/Logic/Preload/Preloader/PreloaderCoder.cs` | 只有IL2CPP才统计及加载AOT元数据；Mono仍加载热更DLL | 对比合并`ENABLE_IL2CPP`守卫；属于运行时依赖，不是编辑器脚本 |

公共`Assets/MonoPipelineFunctionTest`中的`GlobalMonoPipelineTest.cs`、`MonoPipelineReflection.cs`、`MonoPipelineEvidence.cs`和`Editor/MonoPipelineBuildSupport.cs`及GUID原已随仓库提供，本轮不改。7个Unity包和原许可证同样保持原样。

Skill内`assets/adapters/GameClient/framework-overloads.patch`是原有三处管线重载及菜单排序的四文件补丁；它未包含上述资源生成和预加载守卫。不要运行旧PC增量安装器或把整个旧PC测试入口当依赖，也不要将该补丁已合并等同于Mono包已能构建、启动。

## 目标必须已有

| 目标依赖 | 需核对的实际能力 |
| --- | --- |
| 原GameFramework编辑器构建体系 | `BuildOption.ScriptingBackend`、接收`BuildProfilerType`的`BuildOption.Create`、`BuildProfilerType.Development`；创建参数及开发标志不能丢失 |
| Windows平台实现 | `AppBuilderWindowNoSDK`及其父类；`OnPreBuild`必须按`Option.ScriptingBackend`设后端，不能固定回IL2CPP |
| 原构建结果及配置 | `AppBuilderResult(bool, string, object)`、`IsSuccess`、`Report`，`EditorGameDefine.BuildWorkPath`、原App/Res/版本/渠道配置 |
| 原运行框架及业务 | GameFramework核心DLL/源码、场景、热更业务DLL和资源链；本仓库不复制整套框架或业务游戏 |
| HybridCLR及SDK编辑器链 | 当前参考为HybridCLR 8.8.0；菜单直接引用其编辑器设置，原Windows无SDK前置仍调用SDK编辑器工具，不能按“无SDK包”删除编译依赖 |
| Unity及Pipeline | 参考Unity 2022.3.62f3，原7个包和引擎内建模块；匹配目标既有程序集布局，不覆盖UPM声明和锁文件 |

目标未具备这些能力时不能只拖一个菜单文件；应在目标原框架中合并对应实现，不从本机Library或生成`.csproj`复制编译产物。当前副本中的原项目其他修改、版权和GUID一并保留，提供全文件是为了对比，不表示批准覆盖所有差异。

## 使用注意

1. 先备份目标同名文件，核对框架API、程序集引用及GUID；按上表合并依赖，然后加入菜单，公共四源只接入一次。目标已有文件保留其GUID，不用参考`.meta`覆盖未知既有身份。
2. 合并后由目标工程独立完成Unity编译，手动切换Windows 64；打开菜单只显示参数窗口，点击构建和单独确认后才执行原资源/打包管线。输出必须为项目外新目录，端口按原契约选择。
3. 运行时文件`PreloaderCoder.cs`的更改需要随目标原框架程序集重新编译并进入新包，不能只修改编辑器源。只使用已有合格Mono包执行测试时，无需因为本次仓库补文件而重新打包。

构建结束正常恢复相关设置不等于所有资源、版本、SDK生成或强杀/域重载均可回滚。文件摘要一致、隔离检查通过都不能作为真实Unity出包或业务验收通过的证明。

## 修改记录

2026-11-06，Codex：核对发现首轮仓库仅展开公共四源，菜单仍在Skill内、框架仅有四文件增量补丁；按当前工程原字节补齐7源码/7元数据并列出目标已有框架条件。没有修改当前工程源码、父Workflow、Skill执行逻辑或Player，没有实际构建。

本次15项构建适配/可迁移性/语法兼容定向检查全部通过，9.174秒。仓库补交的7源码连同公共四源，共11个源码使用当前工程417个真实引用隔离编译，退出码0；编译期间只写项目输出目录，不启动Unity或构建Player。源码类型有意覆盖已有引用中的同名类型，检查命令抑制对应`CS0436`警告；不是全工程编译或跨项目可构建证明。

14个新增源码/元数据与原工程逐字节一致，仓库`Assets`的13个GUID无重复，Skill99个文件及原交付清单摘要未变。首两次隔离命令分别因输出参数拼接、绝对引用路径解析遗漏失败，修正验证命令后通过，未修改交付源码以绕过问题；原始失败及最终结果保留于维护工程的`Doc/AI开发文档/output/mono-editor-delivery-codex-20261106/`，不是运行依赖。
