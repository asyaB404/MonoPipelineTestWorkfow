# 离线交付与显式接入

<!-- 创建日期：2026-10-26；作者：Cyou；更新日期：2026-11-05；更新人：Codex；功能：单目录交付、首次接入、构建库存和目标准备；参数：明确本地根、新输出、批准摘要、包外备份及权限记录。精简历史流水，不扩展 Unity/Player 授权。 -->

目录交付 = 同一 Skill 根携带宿主、模板、公共 Unity 源、依赖/许可及完整性清单；落点是技能目录，不是 Unity 自动编译目录。Agent 从用户原材料和真实授权生成内部记录，不要求手写 JSON，不默认接受模板中的未批准值。运行输出、描述符、账号/令牌、缓存和备份均不随包交付。

## 离线命令

使用同包 [mono-pipeline-test.bat](../mono-pipeline-test.bat) 或 [cli.py](../scripts/cli.py)，最低 Python 3.10，不固定维护机小版本、不安装环境。以下命令不启动或连接 Player，字段详见命令帮助。

| 命令 | 真实输入与结果 |
| --- | --- |
| `delivery-verify` | 只读核验完整目录，可选 ZIP；拒额外/缺失/摘要变化、绝对/上溯、重解析点、重复/大小写冲突和 ZIP 穿越，不自动修清单 |
| `delivery-export` | 目标不存在且父目录存在，根名保持 mono-pipeline-functiontest，可选新 ZIP；目的地不在源内或包含源，暂存核验后原子新建、不覆盖 |
| `delivery-refresh` | 仅显式维护批准及既有清单当前 SHA256；清单自身不循环散列，普通接收者不能用刷新绕过来源变化 |
| `unity-preview` | 明确 Unity 根，只读返回精确路径、增量、兼容跳过/冲突及摘要；可写包/项目外新计划文件 |
| `unity-apply` | 同一目标、批准计划 SHA256、独立批准、项目/工具外新备份；暂存、备份、复验后精确复制和小型声明增量 |
| `package-scan` | 明确真实 EXE、包/工具外新输出；缺成功构建来源时仅 candidate，完整标志 false |
| `package-manifest` | EXE、成功构建库存路径/SHA256、绑定库存的完整交付批准和新输出；不能仅见文件就认定完整游戏 |
| `target-prepare` | 明确 EXE/PID、[权限记录](../assets/templates/target-permission.json)、新公开目标及可选静态清单；只读创建时间/端口/描述符/ACL，不回显凭据 |

预览冲突退出 3，完整性错误 5，输入非法 2；无身份/传输测试旁路。[delivery-manifest.json](../delivery-manifest.json) 登记包内相对路径、字节数、SHA256、版本/许可和类别；[依赖目录](../assets/dependencies/catalog.json) 登记原归档。只读校验/导出不访问维护工程；清单用于原字节检测，不是认证签名。目录与 ZIP 分别原子发布，不承诺跨路径事务。

## 首次接入与文件保护

公共源从 [GlobalMonoPipelineTest.cs](../assets/unity/GlobalMonoPipelineTest.cs) 接入目标测试目录，目录/源 GUID 保留；祖先程序集定义/引用、第二入口、未知同名包、自定义布局或变更源/元数据保守拒绝。既有嵌入包/明确同版本缓存必须全部成员与摘要匹配才跳过，版本号相等不足以证明兼容。

依赖仅复制到明确嵌入布局，声明只改已知小型依赖精确值/缺项，其余原字节/BOM 保留；UPM 锁只读，不运行 UPM、编辑器、安装器或构建。SDK、引擎模块、资源及热更流程不由文件复制补齐。可选 [GameClient 接线](../assets/adapters/GameClient/README.md) 由同包[适配索引](../assets/adapters/catalog.json)限制明确成员，不把项目名/布局写进公共模块，也不接管未知适配源。

备份必须为项目/工具外新路径，先留原小文件与拟接入字节。捕获失败时仅恢复仍等于本次写入摘要的文件；外部改动保留并记录，接入记录最后写入。不承诺掉电/强杀多文件事务恢复；精确复制成功不证明 UPM、Unity 编译或业务可测。

本地自有暂存目录原子发布遇 Windows 错误 5/32/33 时，同一起点 5000 毫秒总预算、至多 100 毫秒轮询，每次重验路径/目的地与内容，记录真实尝试数；不改权限、不覆写外部内容，不用于游戏命令/断连/未知动作重试。

UTF-16 单元 = 单个 16 位编码值，部分字符占 2 个单元。接入文件至多 259、父目录至多 247 单元，并计算实际临时文件名；预览和批准接入分别在复制前核验目标/依赖/备份/恢复预算，超限退出 3，清理本次空暂存，不改系统长路径开关。运行证据目录另由 `output-check/init` 核验。

## 构建来源与目标

[MonoPipelineBuildSupport.cs](../assets/unity/Editor/MonoPipelineBuildSupport.cs) 的 `PrepareDisabledConfiguration` 仅缺失时新建禁用小配置，未知既有配置拒绝；`PrepareOptions` 保留场景/输出/资源流程，返回 Development/测试宏选项，Mono 后端先由原管线确认。

`RunPrepared` 在项目外新备份下临时启用配置及 Development 开关，只调用传入原管线一次，正常 finally 按原字节/设置恢复；不改全局后端/宏，外部改动保留，不保证原管线尊重新选项或异常终止恢复。`InspectConfigurationSha256` 与范围重载支持明确审阅既有启用/端口配置，仍绑定原摘要；默认接口不自动接受启用配置。实际打包不属于本 Skill 的默认操作。

`WriteSuccessfulBuildInventory` 仅在成功 BuildReport 后由原完整 App/资源管线调用，读取实际 GUID、Unity 版本、平台/开发标志及全部真实静态文件；后续资源流程改文件后旧库存失效，须在完整交付点重新输出。完整游戏仍需 [package-approval.json](../assets/templates/package-approval.json) 独立批准，不自动确认。

普通静态成员可为 0 字节，大小和摘要仍完整登记，不忽略空文件；EXE/Unity/Mono/桥接等必需成员为空仍拒绝完整包。单文件上限 1,073,741,824 字节，超限诊断带实际路径/字节。内部 Windows 长路径 I/O 保留逻辑路径，设备/UNC/上溯、重解析点、数量/字节和不覆写守卫不变，不修改系统配置。

公开目标由真实 EXE/PID、许可路径/SHA256、明确权限及包外请求/证据根生成；独立核验完整静态包、创建时间、ACL、端口独占与描述符，心跳待正常连接握手。令牌只在内存核验，不复制描述符原文；缺许可接受、附加或脚本权限拒绝，不自动补批准。准备成功不是启动、附加或业务通过。

## 验证边界

公共负载为 4 个 C# 源及 6 个 GUID 元数据，许可见 [internal-license.md](internal-license.md)。临时目录、内存回执、隔离编译或文件级接入不证明 Unity/UPM、完整 App/资源/热更出包、服务启动、真实 Player、截图渲染帧或业务结果；验证入口与分层范围见[隔离验证](isolation-tests.md)，具体次数/失败记录留在维护工程日志，不随日常契约重复分发。
