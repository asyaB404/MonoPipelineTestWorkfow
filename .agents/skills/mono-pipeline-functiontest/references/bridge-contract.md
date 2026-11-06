# 公共 Unity 负载契约

<!-- 创建日期：2026-10-26；作者：Cyou；功能：已实现公共 Unity 源的实际 API、六字段返回、证据/启动与编译边界；参数：当前选择器/实例、已加载类型身份、run/case/command/build 与显式授权；C# 当前未编译或 Player 实测。 -->

桥接 = [GlobalMonoPipelineTest](../assets/unity/GlobalMonoPipelineTest.cs:10) 公共入口。源在本 Skill 中不是自动编译内容，首次明确接入后进入无祖先程序集定义/引用的预定义业务程序集；基础读取仍不依赖桥接，参照 [read-basic.cs](../assets/templates/read-basic.cs:1)。首次接入/依赖/构建范围使用 [delivery-contract.md](delivery-contract.md:1)。

## 六字段返回与守卫

[`Envelope()`](../assets/unity/GlobalMonoPipelineTest.cs:79) 固定只有版本、当前帧、实际构建、实际值、明确错误及请求目标六字段；不能新增顶层控制字段。宿主按 [`observed_value()`](../scripts/pipeline.py:492) 对本次实际归属、构建、帧和严格相等的目标解包。桥接请求的 [`value_format`](../scripts/session.py:460) 使用桥接格式；动作与只读都使用该格式，错误动作冻结，不把回执当产品成功。

[`EarlyGate()`](../assets/unity/GlobalMonoPipelineTest.cs:25) 在 Unity 子系统注册阶段运行，早于 Pipeline 的场景加载前初始化。仅 Windows Player 分支直接调用同包真实配置读取接口，保存烘焙值后先关闭启用/自动启动，再确认实际 Mono、Development、新测试宏、本次明确开关、原配置及端口范围；全部满足才重新开启。关闭路径不依赖业务类型发现或程序集数量。配置缺失/读取异常保留诊断，不声称已证明真实服务不监听。

公共反射/取证实现的编译条件同时隔离平台、开发、宏、编辑器和 IL2CPP。普通及 IL2CPP Windows Player 分支关闭配置；编辑器/其他平台不包含入口的 Pipeline 配置直接引用，编辑器辅助的引用仅在编辑器分支。归档内部平台范围、解释器与 Roslyn 引用保持原样；当前没有 Unity 编译证明。服务令牌仍真实写运行描述符，ACL/身份由宿主核验，不是沙箱或自动授权。

## 定位、观察和一次调用

| 实际 API | 参数/实际值与限制 |
|---|---|
| [`Status(target)`](../assets/unity/GlobalMonoPipelineTest.cs:69) | 当前门禁诊断；不代替登录/资源/业务就绪 |
| [`Discover(target, scene, nameContains, includeInactive, maxNodes, maxResults)`](../assets/unity/GlobalMonoPipelineTest.cs:118) | 真实已加载场景及自有驱动所在持久场景；不枚举项目 Prefab。硬上限 32768 节点、512 返回候选，截断明确；超扫描预算报错 |
| [`Observe(target, instanceId, componentType, assemblyFullName, moduleMvid, members)`](../assets/unity/GlobalMonoPipelineTest.cs:125) | 当前精确选择器和实例重新定位；组件为空明确观察节点，组件非空验证完整类型/程序集/MVID。明确字段/属性链，缺失/歧义/读取异常不能变默认假值或零；任意复杂值需显式成员投影 |
| [`LoadedTypes(target, prefix, maxTypes)`](../assets/unity/GlobalMonoPipelineTest.cs:132) | 当前已加载类型、来源/MVID、真实加载诊断和截断；不加载 DLL，不增加编译器引用 |
| [`InvokeStatic(target, typeName, assemblyFullName, moduleMvid, methodName, parameterTypes, arguments)`](../assets/unity/GlobalMonoPipelineTest.cs:138) | 当前集合完整类型唯一，来源/MVID 相等，声明方法和参数类型精确，禁止隐式转换及不支持的签名；只调用一次 |
| [`InvokeComponent(target, instanceId, typeName, assemblyFullName, moduleMvid, methodName, parameterTypes, arguments)`](../assets/unity/GlobalMonoPipelineTest.cs:145) | 另核验本轮唯一存活组件、当前激活/可操作值；只调用一次，异常不重试 |
| [`ClickButton(target, instanceId)`](../assets/unity/GlobalMonoPipelineTest.cs:155)、[`SetToggle(target, instanceId, value)`](../assets/unity/GlobalMonoPipelineTest.cs:161) | 精确标准控件激活/可交互才操作；按钮只派发一次，开关同值不重复派发。这是程序调用，不是完整指针输入；定制按钮走已验证明确反射接口，不叠加派发 |

选择器包含真实场景路径/名称、节点名称及同级序号；[Resolve()](../assets/unity/MonoPipelineReflection.cs:148) 每次重新遍历并检查本轮实例。旧路径只是候选，界面重建导致实例改变必须重新定位。目标实际值包括选择器/实例/组件和当前帧；发现回执不构成业务预期。

已加载热更类型使用同一唯一集合解析，禁止字节加载/替换同名 DLL。可反射调用不代表 Roslyn 有强类型 metadata 引用，缺编译器引用继续保留真实诊断。脚本/反射/getter 不是沙箱，只读和业务许可由当前 Agent 审阅；调用成功只是一次回执，之后仍由宿主在独立新帧验证真实业务。

## 日志与单例截图票据

[`MonoPipelineEvidenceContext`](../assets/unity/GlobalMonoPipelineTest.cs:206) 提供真实归属、已授权包外证据根、明确类别权限和当前 Agent 公开审阅；模板 [`bridge-evidence-context.json`](../assets/templates/bridge-evidence-context.json:1) 默认不批准任何权限/公开内容。

- [`ConfigureLogs()`](../assets/unity/GlobalMonoPipelineTest.cs:167) 显式开关采集；[`ReadLogs()`](../assets/unity/GlobalMonoPipelineTest.cs:174) / [`ExportLogs()`](../assets/unity/GlobalMonoPipelineTest.cs:180) 指定窗口/总序号。上限 512 条、消息 4096 字符、栈 8192 字符，真实序号/严重度/时间/帧，截断/丢失/禁用区间明确。后台帧只是最后主线程样本，明确非精确帧，不用它声称全轮无异常。
- [`RequestScreenshot()`](../assets/unity/GlobalMonoPipelineTest.cs:186) 单次返回票据；[`ScreenshotStatus()`](../assets/unity/GlobalMonoPipelineTest.cs:192) 必须在后续新帧查询完成并核验真实文件 SHA/字节。上限 8 个票据、600 帧及 30 秒的同一起点，不因查询重置或自动重拍；[`ReleaseScreenshot()`](../assets/unity/GlobalMonoPipelineTest.cs:198) 只显式释放票据内存，不删除文件。
- 捕获请求帧、捕获 API 调用帧、第一次完成检查帧及当前检查帧在实际值中分别标记；实际 renderframe 无法证明时为 null，不把完成检查帧伪装成渲染帧。不使用一张图证明全部 Case。

[Artifact()](../assets/unity/MonoPipelineEvidence.cs:192) 严格十字段：路径、摘要、字节、类别、run/case/当前观察命令、实际构建/当前观察帧、公开审阅状态。捕获请求命令不是附件本次观察命令。日志/PNG 新建于明确包外根的私有随机目录，拒绝重解析点、普通文件覆盖和超过 16 MiB 的证据。

默认公开状态未知，不能自动标公开。当前 Agent 实际敏感审阅后，再用新的观察命令和明确公开声明获取该附件元数据；[collect-evidence](../scripts/session.py:1072) 仍要求独立权限、同轮同例同观察命令/构建/帧、包外路径、原摘要/PNG 和当前 Agent 敏感审阅。正文窗口/捕获诊断在元数据外层，不能扩展这十字段。实际图片或编码秘密无法由程序自动证明已脱敏。

2026-10-26，Cyou：落实 4 个公共 C# 源、早期配置门禁、有界场景/反射、一次控件调用和日志/截图实际接口；未执行 Unity 编译、UPM 解析、真实服务/Player/热更/业务或截图验收。

同日修正门禁为 Windows Player 直接读取配置、先关闭再确认许可，并同步全部入口行号。新增 [`test_gate_execution.py`](../scripts/tests/test_gate_execution.py:1) 从真实方法体生成临时控制台桩；4 项真实通过仅证明隔离分支/关闭顺序，不替代完整 C# 的 Unity 编译或实包服务验证。
