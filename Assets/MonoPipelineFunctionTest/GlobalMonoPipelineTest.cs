// 创建日期：2026-10-26；作者：Cyou。
// 功能：项目无关测试入口、六字段返回、早期 Pipeline 内存门禁；基础参数：当前选择器、实际实例/程序集身份、明确权限上下文。
// 本文件是待显式接入的源码，不在 Skill 目录中参与 Unity 编译；普通包、编辑器和 IL2CPP 不启用测试行为。
using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

/// <summary>公共入口进入无祖先 asmdef/asmref 的 Assembly-CSharp，不注册 Roslyn metadata 或加载 DLL。</summary>
public static class GlobalMonoPipelineTest
{
    public const string BridgeVersion = "mono-pipeline-functiontest/1";
    public const string RuntimeSwitch = "-mono-pipeline-test";
    public const int MaximumSelectorCharacters = 4096;
    public const int MaximumDiagnosticCharacters = 4096;
    private const int MinimumHostPort = 7900;
    private const int MaximumHostPort = 7949;
    private static bool s_Active;
    private static string s_GateReason = "early_gate_not_executed";

    internal static bool Active { get { return s_Active; } }

    // 功能：SubsystemRegistration 先于 Pipeline 的 BeforeSceneLoad；参数无，只关闭未授权的内存配置，不写项目文件。
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    private static void EarlyGate()
    {
        s_Active = false;
        s_GateReason = "requires_windows_mono_development_macro_and_explicit_switch";
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD && MONO_PIPELINE_FUNCTIONTEST && !UNITY_EDITOR && !ENABLE_IL2CPP
        bool switched = Array.IndexOf(Environment.GetCommandLineArgs(), RuntimeSwitch) >= 0;
        s_Active = switched && !Application.isEditor && Application.platform == RuntimePlatform.WindowsPlayer
            && Debug.isDebugBuild && Type.GetType("Mono.Runtime") != null;
#endif
#if UNITY_STANDALONE_WIN && !UNITY_EDITOR
        // 仅 Windows Player 分支引用对应平台的真实配置；未知 API 在编译期拒绝，不留下已启用配置。
        // 先关闭再核验本次许可，程序集数量或业务类型发现不能绕过普通包的关闭路径。
        try
        {
            Unity.Pipeline.Config.RuntimePipelineConfig config = Unity.Pipeline.Config.RuntimePipelineConfig.Load();
            if (config == null)
            {
                s_Active = false;
                s_GateReason = "pipeline_config_absent";
                return;
            }
            bool bakedEnabled = config.enableInBuilds && config.autoStart;
            int configuredPort = config.port;
            config.enableInBuilds = false;
            config.autoStart = false;
            s_Active = s_Active && bakedEnabled
                && configuredPort >= MinimumHostPort && configuredPort <= MaximumHostPort;
            s_GateReason = s_Active ? "explicit_test_gate_open" : "baked_config_disabled_or_test_gate_closed";
            if (s_Active)
            {
                config.enableInBuilds = true;
                config.autoStart = true;
            }
        }
        catch (Exception exception)
        {
            s_Active = false;
            s_GateReason = "pipeline_gate_metadata_error:" + exception.GetType().FullName;
            Debug.LogException(exception);
        }
#endif
    }

    // 功能：返回实际启动门禁诊断；参数 target 必须与宿主请求一致，此状态不是业务通过。
    public static Dictionary<string, object> Status(string target)
    {
        return Envelope(target, new Dictionary<string, object> {
            { "active", s_Active }, { "gate_reason", s_GateReason }, { "runtime_switch", RuntimeSwitch },
            { "unity_version", Application.unityVersion }, { "platform", Application.platform.ToString() },
            { "development", Debug.isDebugBuild }, { "runtime_verified_by_host", false }
        }, s_Active ? null : s_GateReason);
    }

    // 功能：固定六字段 envelope；参数 value 为实际 JSON 兼容值，error 不把缺失/异常转换为默认值。
    internal static Dictionary<string, object> Envelope(string target, object value, string error)
    {
        return new Dictionary<string, object> {
            { "bridge", BridgeVersion }, { "frame", Time.frameCount }, { "build_guid", Application.buildGUID },
            { "value", value }, { "error", error }, { "target", target }
        };
    }

#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD && MONO_PIPELINE_FUNCTIONTEST && !UNITY_EDITOR && !ENABLE_IL2CPP
    // 功能：仅本次显式测试包创建自有持久取证驱动；参数无，不创建/操作业务对象。
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    private static void InitializeTestDriver()
    {
        if (s_Active) MonoPipelineEvidence.InitializeDriver();
    }

    // 功能：统一捕获明确异常，保留实际错误；参数 action 同步只调用一次，不重试。
    private static Dictionary<string, object> Execute(string target, Func<object> action)
    {
        if (!s_Active) return Envelope(target, null, s_GateReason);
        try
        {
            if (string.IsNullOrEmpty(target) || target.Length > MaximumSelectorCharacters || action == null)
                throw new ArgumentException("selector_or_operation_invalid");
            return Envelope(target, action(), null);
        }
        catch (Exception exception)
        {
            Exception actual = exception is TargetInvocationException && exception.InnerException != null
                ? exception.InnerException : exception;
            Debug.LogException(actual);
            string diagnostic = actual.GetType().FullName + ":" + actual.Message;
            if (diagnostic.Length > MaximumDiagnosticCharacters)
                diagnostic = diagnostic.Substring(0, MaximumDiagnosticCharacters);
            return Envelope(target, null, diagnostic);
        }
    }

    // 功能：有界发现真实已加载场景节点；参数 scene/name 是候选过滤，输出不证明业务行为。
    public static Dictionary<string, object> Discover(string target, string scene, string nameContains,
        bool includeInactive, int maxNodes, int maxResults)
    {
        return Execute(target, delegate { return MonoPipelineReflection.Discover(scene, nameContains, includeInactive, maxNodes, maxResults); });
    }

    // 功能：观察唯一存活对象的明确成员；参数 instanceId 来自本轮发现，组件身份来自真实已加载类型。
    public static Dictionary<string, object> Observe(string target, int instanceId, string componentType,
        string assemblyFullName, string moduleMvid, string[] members)
    {
        return Execute(target, delegate { return MonoPipelineReflection.Observe(target, instanceId, componentType, assemblyFullName, moduleMvid, members); });
    }

    // 功能：有界列举当前程序集/类型身份；参数 prefix/maxTypes 限定观察，不增加编译器引用。
    public static Dictionary<string, object> LoadedTypes(string target, string prefix, int maxTypes)
    {
        return Execute(target, delegate { return MonoPipelineReflection.LoadedTypes(prefix, maxTypes); });
    }

    // 功能：只调用当前唯一真实静态方法一次；参数为完整类型/程序集/MVID、精确参数类型与实际参数。
    public static Dictionary<string, object> InvokeStatic(string target, string typeName, string assemblyFullName,
        string moduleMvid, string methodName, string[] parameterTypes, object[] arguments)
    {
        return Execute(target, delegate { return MonoPipelineReflection.Invoke(null, typeName, assemblyFullName, moduleMvid, methodName, parameterTypes, arguments); });
    }

    // 功能：只调用本轮唯一组件方法一次；参数 instanceId 防止旧路径匹配到重建后的另一实例。
    public static Dictionary<string, object> InvokeComponent(string target, int instanceId, string typeName,
        string assemblyFullName, string moduleMvid, string methodName, string[] parameterTypes, object[] arguments)
    {
        return Execute(target, delegate {
            GameObject node = MonoPipelineReflection.Resolve(target, instanceId);
            return MonoPipelineReflection.Invoke(node, typeName, assemblyFullName, moduleMvid, methodName, parameterTypes, arguments);
        });
    }

    // 功能：检查当前标准 Button 可操作后只派发一次 onClick；参数不是鼠标输入或独立业务验证。
    public static Dictionary<string, object> ClickButton(string target, int instanceId)
    {
        return Execute(target, delegate { return MonoPipelineReflection.ClickButton(target, instanceId); });
    }

    // 功能：检查当前标准 Toggle 后至多设置一次；参数 value 是本次期望操作，不把同帧回执当 after。
    public static Dictionary<string, object> SetToggle(string target, int instanceId, bool value)
    {
        return Execute(target, delegate { return MonoPipelineReflection.SetToggle(target, instanceId, value); });
    }

    // 功能：明确开关有界日志采集；参数 context 必须显式 log_read，容量/截断上限受硬预算约束。
    public static Dictionary<string, object> ConfigureLogs(string target, MonoPipelineEvidenceContext context,
        bool enabled, int capacity, int messageCharacters, int stackCharacters)
    {
        return Execute(target, delegate { return MonoPipelineEvidence.ConfigureLogs(context, enabled, capacity, messageCharacters, stackCharacters); });
    }

    // 功能：读取本次授权日志窗口；参数 afterSeq/maxRecords 不隐藏丢失、禁用区间或线程帧的不确定性。
    public static Dictionary<string, object> ReadLogs(string target, MonoPipelineEvidenceContext context, long afterSeq, int maxRecords)
    {
        return Execute(target, delegate { return MonoPipelineEvidence.ReadLogs(context, afterSeq, maxRecords); });
    }

    // 功能：把明确窗口写到私有证据文件；参数公开审阅声明来自当前 Agent，附件恰为十字段。
    public static Dictionary<string, object> ExportLogs(string target, MonoPipelineEvidenceContext context, long afterSeq, int maxRecords)
    {
        return Execute(target, delegate { return MonoPipelineEvidence.ExportLogs(context, afterSeq, maxRecords); });
    }

    // 功能：发出单次截图请求并立即返回 ticket；参数不自动批准截图或敏感内容公开。
    public static Dictionary<string, object> RequestScreenshot(string target, MonoPipelineEvidenceContext context, int timeoutFrames)
    {
        return Execute(target, delegate { return MonoPipelineEvidence.RequestScreenshot(context, timeoutFrames); });
    }

    // 功能：在后续新帧查询 ticket 和原文件摘要；参数 command_id 是这次观察，不冒充捕获请求命令。
    public static Dictionary<string, object> ScreenshotStatus(string target, MonoPipelineEvidenceContext context, string ticket)
    {
        return Execute(target, delegate { return MonoPipelineEvidence.ScreenshotStatus(context, ticket); });
    }

    // 功能：显式释放本例 ticket 内存；参数不删除证据文件、不允许另例接管或自动重拍。
    public static Dictionary<string, object> ReleaseScreenshot(string target, MonoPipelineEvidenceContext context, string ticket)
    {
        return Execute(target, delegate { return MonoPipelineEvidence.ReleaseScreenshot(context, ticket); });
    }
#endif
}

/// <summary>显式本次证据权限/归属/审阅 DTO；默认均未授权，不携 token 或账号。</summary>
public sealed class MonoPipelineEvidenceContext
{
    public string run_id;
    public string case_id;
    public string command_id;
    public string build_guid;
    public string evidence_root;
    public bool permission_granted;
    public string permission;
    public bool public_reviewed;
    public string reviewer;
    public string review_statement;
}
