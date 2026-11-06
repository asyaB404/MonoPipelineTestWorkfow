# 同包内部迁移许可

<!-- 创建日期：2026-10-26；作者：Cyou；功能：随包保留真实原许可、授权范围与来源摘要；参数：包内归档/原许可和依赖清单；不授予运行权限或公开再分发许可。 -->

内部迁移授权 = 本次已批准的公司内部源码/插件文件复制，保留归档内原许可证、DLL、GUID 和第三方声明。它不是公开再分发授权，不批准安装器、下载、Unity 编译/构建、服务开放、Player 操作、账号、GM 或上传。

依赖只来自已授权本地归档，来源清单和授权资料的原字节 SHA256 已记录在 [catalog.json](../assets/dependencies/catalog.json:1)。接收者运行只需要当前完整目录，不需要原工程或原文档。当前包未提供原生安装结果、完整游戏、SDK、框架 DLL 或业务适配。

| 依赖实际版本 | 原归档 | 同包原许可 |
|---|---|---|
| Pipeline 0.6.0-exp.1-unity2022 | [pipeline.zip](../assets/dependencies/pipeline.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.pipeline/LICENSE.md:1) |
| Mono Cecil 1.11.5 | [cecil.zip](../assets/dependencies/cecil.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.nuget.mono-cecil/LICENSE.md:1)、[Third Party Notices.md](../assets/dependencies/licenses/com.unity.nuget.mono-cecil/Third%20Party%20Notices.md:1) |
| UGUI 1.0.0 | [ugui.zip](../assets/dependencies/ugui.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.ugui/LICENSE.md:1) |
| Input System 1.14.0 | [inputsystem.zip](../assets/dependencies/inputsystem.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.inputsystem/LICENSE.md:1) |
| Newtonsoft JSON 3.2.1 | [newtonsoft.zip](../assets/dependencies/newtonsoft.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.nuget.newtonsoft-json/LICENSE.md:1)、[Third Party Notices.md](../assets/dependencies/licenses/com.unity.nuget.newtonsoft-json/Third%20Party%20Notices.md:1) |
| Unity Test Framework 1.1.33 | [testframework.zip](../assets/dependencies/testframework.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.test-framework/LICENSE.md:1) |
| NUnit 1.0.6 | [nunit.zip](../assets/dependencies/nunit.zip) | [LICENSE.md](../assets/dependencies/licenses/com.unity.ext.nunit/LICENSE.md:1) |

7 个原 ZIP 共 9,245,072 字节；2599 个归档成员共 30,336,422 字节；另外保留 18 个可读原许可/元数据文件。归档未改写，Pipeline 的解释器、Roslyn 和平台限制完整保留。没有裁掉依赖或以依赖声明下限替代已解析版本。

Pipeline 归档只提供其总许可文件，未提供每个内嵌编译器 DLL 的独立许可文本；本包不虚构新增许可。原许可提到的外部条款仍由公司法务确认，当前内部迁移批准不扩大到外部发布。需要公开再分发时必须另行确认全部上游条款。

本次新增公共源码/工具按该内部交付范围使用；未提供独立公开开源许可。HybridCLR 特定构建/预加载接线、TextMeshPro 业务 UI 和旧游戏适配没有纳入公共闭包；目标项目原 App/资源/热更流程须单独适配。

2026-10-26，Cyou：固定内部来源/原归档/许可与 SHA256，纳入同包清单；未联网、安装或扩大许可。C# 未执行 Unity 编译或 Player 验收。
