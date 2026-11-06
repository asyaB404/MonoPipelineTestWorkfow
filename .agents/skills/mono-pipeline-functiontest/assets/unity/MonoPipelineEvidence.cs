// 创建日期：2026-10-26；作者：Cyou。
// 功能：显式有界结构化日志、单次截图 ticket 和十字段附件元数据；基础参数：真实 run/case/command/build、包外证据根、权限/公开审阅及预算。
// 截图渲染帧未知时始终返回 null；文件使用私有新目录和 CreateNew，公开审阅不自动批准。
using UnityEngine;
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD && MONO_PIPELINE_FUNCTIONTEST && !UNITY_EDITOR && !ENABLE_IL2CPP
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using UnityEngine.SceneManagement;
#endif

/// <summary>同名自有 MonoBehaviour 保持 Unity 脚本映射；非测试编译只有空组件，不创建或运行测试行为。</summary>
public sealed class MonoPipelineEvidence : MonoBehaviour
{
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD && MONO_PIPELINE_FUNCTIONTEST && !UNITY_EDITOR && !ENABLE_IL2CPP
    private const int MaximumLogRecords = 512;
    private const int MaximumMessageCharacters = 4096;
    private const int MaximumStackCharacters = 8192;
    private const int MaximumTickets = 8;
    private const int MaximumTimeoutFrames = 600;
    private const double MaximumCaptureSeconds = 30.0;
    private const int MaximumEvidenceBytes = 16 * 1024 * 1024;
    private const int MaximumIdentityCharacters = 256;
    private const int MaximumPathCharacters = 4096;
    private const int HashBufferBytes = 64 * 1024;
    private static readonly object s_LogLock = new object();
    private static readonly Queue<Dictionary<string, object>> s_Logs = new Queue<Dictionary<string, object>>();
    private static readonly Dictionary<string, CaptureTicket> s_Tickets = new Dictionary<string, CaptureTicket>();
    private static MonoPipelineEvidence s_Driver;
    private static int s_MainThreadId;
    private static int s_LastMainFrame;
    private static int s_Capacity = MaximumLogRecords;
    private static int s_MessageCharacters = MaximumMessageCharacters;
    private static int s_StackCharacters = MaximumStackCharacters;
    private static bool s_Logging;
    private static long s_Sequence;
    private static long s_Dropped;
    private static long s_Truncated;
    private static long s_DisabledIntervals;
    private static long s_EnabledStartSequence;
    private static string s_LogRun;
    private static string s_LogCase;

    internal static Scene PersistentScene { get { return s_Driver == null ? default(Scene) : s_Driver.gameObject.scene; } }

    // 功能：创建唯一自有驱动并采样主线程；参数无，只有已授权运行门禁调用，不触碰业务对象。
    internal static void InitializeDriver()
    {
        if (!GlobalMonoPipelineTest.Active) throw new InvalidOperationException("test_gate_closed");
        if (s_Driver != null) return;
        s_MainThreadId = Thread.CurrentThread.ManagedThreadId;
        s_LastMainFrame = Time.frameCount;
        GameObject owner = new GameObject(typeof(MonoPipelineEvidence).Name);
        if (owner == null) throw new InvalidOperationException("capture_driver_creation_failed");
        UnityEngine.Object.DontDestroyOnLoad(owner);
        s_Driver = owner.AddComponent<MonoPipelineEvidence>();
        if (s_Driver == null) throw new InvalidOperationException("capture_driver_component_failed");
    }

    // 功能：排除工具自有场景节点；参数 node 不以业务名字或路径筛选。
    internal static bool IsOwnNode(GameObject node)
    {
        return node != null && s_Driver != null && s_Driver.gameObject != null && node == s_Driver.gameObject;
    }

    // 功能：更新供后台日志使用的真实主线程帧样本；参数无，后台记录明确标为非精确帧。
    internal static void SampleFrame()
    {
        Volatile.Write(ref s_LastMainFrame, Time.frameCount);
    }

    // 功能：销毁自有驱动时停止订阅；参数无，不删日志、证据或结束 Player。
    internal static void DriverDestroyed()
    {
        lock (s_LogLock)
        {
            if (s_Logging) Application.logMessageReceivedThreaded -= OnLog;
            s_Logging = false;
            s_DisabledIntervals++;
        }
        s_Driver = null;
    }

    // 功能：验证真实归属与显式权限；参数 expectedPermission 不接受自动授权或未知公开状态。
    private static void Context(MonoPipelineEvidenceContext context, string expectedPermission)
    {
        if (context == null || !context.permission_granted || context.permission != expectedPermission)
            throw new InvalidOperationException("explicit_evidence_permission_required");
        string[] identities = new string[] { context.run_id, context.case_id, context.command_id, context.build_guid };
        foreach (string identity in identities)
        {
            if (string.IsNullOrEmpty(identity) || identity.Length > MaximumIdentityCharacters || identity.IndexOf('\0') >= 0)
                throw new ArgumentException("evidence_identity_invalid");
        }
        if (context.build_guid != Application.buildGUID) throw new InvalidOperationException("evidence_build_mismatch");
        if (context.public_reviewed && (context.reviewer != "current_agent" || string.IsNullOrWhiteSpace(context.review_statement)))
            throw new InvalidOperationException("explicit_current_agent_privacy_review_required");
    }

    // 功能：校验绝对本机证据根及全链无重解析点；参数路径不得位于静态 Player 包内部。
    private static string EvidenceRoot(MonoPipelineEvidenceContext context)
    {
        string encoded = context.evidence_root;
        if (string.IsNullOrEmpty(encoded) || encoded.Length > MaximumPathCharacters || !Path.IsPathRooted(encoded)
            || encoded.StartsWith("\\\\", StringComparison.Ordinal) || encoded.IndexOf('\0') >= 0)
            throw new ArgumentException("explicit_local_evidence_root_required");
        foreach (string part in encoded.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar))
        {
            if (part == ".." || part == ".") throw new ArgumentException("evidence_path_traversal");
        }
        string resolved = Path.GetFullPath(encoded);
        if (resolved == Path.GetPathRoot(resolved)) throw new IOException("evidence_root_must_not_be_whole_drive");
        string full = resolved.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        DirectoryInfo current = new DirectoryInfo(full);
        if (!current.Exists) throw new DirectoryNotFoundException("evidence_root_missing");
        while (current != null)
        {
            if ((current.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("evidence_reparse_point_refused");
            current = current.Parent;
        }
        DirectoryInfo package = Directory.GetParent(Application.dataPath);
        if (package == null) throw new IOException("player_package_root_unknown");
        string packageRoot = package.FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        if ((full + Path.DirectorySeparatorChar).StartsWith(packageRoot, StringComparison.OrdinalIgnoreCase))
            throw new IOException("evidence_must_be_outside_static_package");
        return full;
    }

    // 功能：生成私有新文件路径；参数 kind 仅供内部类别，普通文件不覆盖、不重用已存在目录。
    private static string PrivateFile(MonoPipelineEvidenceContext context, string kind)
    {
        string root = EvidenceRoot(context);
        string directory = Path.Combine(root, "mono-pipeline-" + Guid.NewGuid().ToString("N"));
        if (Directory.Exists(directory) || File.Exists(directory)) throw new IOException("evidence_private_directory_exists");
        DirectoryInfo created = Directory.CreateDirectory(directory);
        if (created == null || !created.Exists || (created.Attributes & FileAttributes.ReparsePoint) != 0)
            throw new IOException("evidence_private_directory_invalid");
        return Path.Combine(directory, kind == "screenshot" ? "capture.png" : "window.log");
    }

    // 功能：有界新建证据字节；参数 content 不得空/超预算，CreateNew 保证不覆写现有普通文件。
    private static void WriteNew(string path, byte[] content)
    {
        if (content == null || content.Length < 1 || content.Length > MaximumEvidenceBytes) throw new IOException("evidence_byte_budget_exceeded");
        using (FileStream stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            stream.Write(content, 0, content.Length);
            stream.Flush(true);
        }
    }

    // 功能：计算字节 SHA256；参数 content 是实际保存的字节，不取文件名或票据替代。
    internal static string Sha256(byte[] content)
    {
        if (content == null) throw new ArgumentNullException("content");
        using (SHA256 algorithm = SHA256.Create())
        {
            return BitConverter.ToString(algorithm.ComputeHash(content)).Replace("-", "").ToLowerInvariant();
        }
    }

    // 功能：复核有界普通证据文件和已知摘要；参数 expectedHash/expectedBytes 来自真实写入，变化拒收。
    private static void VerifyFile(string path, string expectedHash, long expectedBytes)
    {
        FileInfo before = new FileInfo(path);
        if (!before.Exists || (before.Attributes & FileAttributes.ReparsePoint) != 0 || before.Length != expectedBytes
            || expectedBytes < 1 || expectedBytes > MaximumEvidenceBytes) throw new IOException("evidence_file_identity_invalid");
        DirectoryInfo parent = before.Directory;
        while (parent != null)
        {
            if ((parent.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("evidence_file_reparse_point_refused");
            parent = parent.Parent;
        }
        string actual;
        using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, HashBufferBytes))
        using (SHA256 algorithm = SHA256.Create())
        {
            actual = BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
            if (stream.Length != expectedBytes) throw new IOException("evidence_file_size_changed");
        }
        FileInfo after = new FileInfo(path);
        if (!after.Exists || after.Length != expectedBytes || after.LastWriteTimeUtc != before.LastWriteTimeUtc || actual != expectedHash)
            throw new IOException("evidence_file_digest_changed");
    }

    // 功能：生成严格十字段附件元数据；参数 frame 是当前观察帧，捕获/完成帧在外层实际值单列。
    private static Dictionary<string, object> Artifact(MonoPipelineEvidenceContext context, string path, string hash, long bytes, string kind)
    {
        VerifyFile(path, hash, bytes);
        return new Dictionary<string, object> { { "path", path }, { "sha256", hash }, { "bytes", bytes }, { "kind", kind },
            { "run_id", context.run_id }, { "case_id", context.case_id }, { "command_id", context.command_id },
            { "build_guid", Application.buildGUID }, { "frame", Time.frameCount },
            { "privacy", context.public_reviewed ? "public_reviewed" : "unreviewed" } };
    }

    // 功能：订阅一次有界日志并显式记录禁用区间；参数容量/文本上限不超出硬预算。
    internal static object ConfigureLogs(MonoPipelineEvidenceContext context, bool enabled, int capacity, int messageCharacters, int stackCharacters)
    {
        Context(context, "log_read");
        if (capacity < 1 || capacity > MaximumLogRecords || messageCharacters < 1 || messageCharacters > MaximumMessageCharacters
            || stackCharacters < 1 || stackCharacters > MaximumStackCharacters) throw new ArgumentOutOfRangeException("log_budget");
        lock (s_LogLock)
        {
            if (s_Logging) Application.logMessageReceivedThreaded -= OnLog;
            if (!enabled && s_Logging) s_DisabledIntervals++;
            if (enabled && (!s_Logging || context.run_id != s_LogRun || context.case_id != s_LogCase)) s_EnabledStartSequence = s_Sequence;
            s_Logging = enabled;
            s_Capacity = capacity;
            s_MessageCharacters = messageCharacters;
            s_StackCharacters = stackCharacters;
            s_LogRun = context.run_id;
            s_LogCase = context.case_id;
            while (s_Logs.Count > capacity) { s_Logs.Dequeue(); s_Dropped++; }
            if (enabled) Application.logMessageReceivedThreaded += OnLog;
            return new Dictionary<string, object> { { "enabled", enabled }, { "start_seq", s_EnabledStartSequence },
                { "latest_seq", s_Sequence }, { "capacity", capacity }, { "scope", "explicit_enabled_intervals_only" } };
        }
    }

    // 功能：采集真实日志，后台线程明确使用最后主线程帧样本；参数 message/stack 不默默丢失或假称脱敏。
    private static void OnLog(string message, string stack, LogType severity)
    {
        lock (s_LogLock)
        {
            if (!s_Logging) return;
            string actualMessage = message ?? "";
            string actualStack = stack ?? "";
            bool truncated = actualMessage.Length > s_MessageCharacters || actualStack.Length > s_StackCharacters;
            if (actualMessage.Length > s_MessageCharacters) actualMessage = actualMessage.Substring(0, s_MessageCharacters);
            if (actualStack.Length > s_StackCharacters) actualStack = actualStack.Substring(0, s_StackCharacters);
            if (truncated) s_Truncated++;
            bool exact = Thread.CurrentThread.ManagedThreadId == s_MainThreadId;
            int frame = exact ? Time.frameCount : Volatile.Read(ref s_LastMainFrame);
            Dictionary<string, object> entry = new Dictionary<string, object> {
                { "seq", ++s_Sequence }, { "severity", severity.ToString() }, { "message", actualMessage }, { "stack", actualStack },
                { "utc", DateTime.UtcNow.ToString("o") }, { "frame", frame }, { "frame_exact", exact },
                { "frame_source", exact ? "callback_current_frame" : "last_main_thread_sample" }, { "truncated", truncated },
                { "run_id", s_LogRun }, { "case_id", s_LogCase }
            };
            if (s_Logs.Count == s_Capacity) { s_Logs.Dequeue(); s_Dropped++; }
            s_Logs.Enqueue(entry);
        }
    }

    // 功能：读取当前例明确日志窗口及完整性状态；参数 afterSeq 是独立窗口起点，不宣称全轮无异常。
    internal static Dictionary<string, object> ReadLogs(MonoPipelineEvidenceContext context, long afterSeq, int maxRecords)
    {
        Context(context, "log_read");
        if (afterSeq < 0 || maxRecords < 1 || maxRecords > MaximumLogRecords) throw new ArgumentOutOfRangeException("log_window");
        lock (s_LogLock)
        {
            List<object> records = new List<object>();
            int total = 0;
            bool windowTruncated = false;
            bool inexactFrames = false;
            foreach (Dictionary<string, object> entry in s_Logs)
            {
                if (entry == null || (long)entry["seq"] <= afterSeq || (string)entry["run_id"] != context.run_id || (string)entry["case_id"] != context.case_id) continue;
                total++;
                windowTruncated |= (bool)entry["truncated"];
                inexactFrames |= !(bool)entry["frame_exact"];
                if (records.Count < maxRecords) records.Add(new Dictionary<string, object>(entry));
            }
            long earliest = s_Logs.Count == 0 ? s_Sequence + 1 : (long)s_Logs.Peek()["seq"];
            bool droppedWindow = afterSeq < earliest - 1;
            bool currentOwner = context.run_id == s_LogRun && context.case_id == s_LogCase;
            return new Dictionary<string, object> { { "records", records }, { "enabled", s_Logging }, { "earliest_seq", earliest },
                { "latest_seq", s_Sequence }, { "dropped_total", s_Dropped }, { "truncated_total", s_Truncated },
                { "disabled_intervals", s_DisabledIntervals }, { "dropped_window", droppedWindow }, { "truncated_window", windowTruncated || total > maxRecords },
                { "inexact_background_frames", inexactFrames }, { "complete", currentOwner && s_Logging && afterSeq >= s_EnabledStartSequence
                    && !droppedWindow && !windowTruncated && total <= maxRecords && !inexactFrames },
                { "scope", "requested_case_window_within_explicit_enabled_interval_not_entire_run" } };
        }
    }

    // 功能：保存本次日志窗口；参数公开状态只取显式上下文，宿主另做当前 Agent 审阅/敏感扫描。
    internal static object ExportLogs(MonoPipelineEvidenceContext context, long afterSeq, int maxRecords)
    {
        Dictionary<string, object> window = ReadLogs(context, afterSeq, maxRecords);
        byte[] content = Encoding.UTF8.GetBytes(JsonConvert.SerializeObject(window));
        string path = PrivateFile(context, "log");
        WriteNew(path, content);
        return new Dictionary<string, object> { { "coverage", window }, { "artifact", Artifact(context, path, Sha256(content), content.Length, "log") } };
    }

    // 功能：单次创建截图 ticket；参数真实上下文和预算，不同步等待、不自动重拍。
    internal static object RequestScreenshot(MonoPipelineEvidenceContext context, int timeoutFrames)
    {
        Context(context, "screenshot");
        if (s_Driver == null || timeoutFrames < 1 || timeoutFrames > MaximumTimeoutFrames || s_Tickets.Count >= MaximumTickets)
            throw new InvalidOperationException("capture_driver_or_ticket_budget_invalid");
        string root = EvidenceRoot(context);
        CaptureTicket ticket = new CaptureTicket {
            Id = Guid.NewGuid().ToString("N"), Run = context.run_id, Case = context.case_id, RequestCommand = context.command_id,
            Build = context.build_guid, Root = root, Path = PrivateFile(context, "screenshot"), RequestFrame = Time.frameCount,
            RequestUtc = DateTime.UtcNow.ToString("o"), StartedSeconds = Time.realtimeSinceStartupAsDouble, TimeoutFrames = timeoutFrames
        };
        s_Tickets.Add(ticket.Id, ticket);
        s_Driver.StartCoroutine(Capture(ticket));
        return new Dictionary<string, object> { { "ticket", ticket.Id }, { "state", "requested" }, { "capture_request_frame", ticket.RequestFrame },
            { "capture_request_command_id", ticket.RequestCommand }, { "render_frame", null }, { "render_frame_known", false } };
    }

    // 功能：在帧末执行一次实际截图并新建文件；参数 ticket 不重复捕获，异常保留实际失败状态。
    private static IEnumerator Capture(CaptureTicket ticket)
    {
        yield return new WaitForEndOfFrame();
        Texture2D texture = null;
        try
        {
            if (Expired(ticket)) throw new TimeoutException("capture_budget_expired_before_capture");
            texture = ScreenCapture.CaptureScreenshotAsTexture();
            if (texture == null) throw new IOException("capture_texture_missing");
            byte[] bytes = texture.EncodeToPNG();
            if (bytes == null || bytes.Length < 1 || bytes.Length > MaximumEvidenceBytes) throw new IOException("capture_png_byte_budget_exceeded");
            WriteNew(ticket.Path, bytes);
            ticket.Hash = Sha256(bytes);
            ticket.Bytes = bytes.Length;
            ticket.CaptureCallFrame = Time.frameCount;
            ticket.Written = true;
        }
        catch (Exception exception)
        {
            ticket.Error = exception.GetType().FullName + ":" + exception.Message;
            Debug.LogException(exception);
        }
        finally
        {
            if (texture != null) UnityEngine.Object.Destroy(texture);
        }
    }

    // 功能：判断同一截图请求的总帧/实际秒预算；参数查询不重置起点。
    private static bool Expired(CaptureTicket ticket)
    {
        return ticket == null || Time.frameCount - ticket.RequestFrame > ticket.TimeoutFrames
            || Time.realtimeSinceStartupAsDouble - ticket.StartedSeconds > MaximumCaptureSeconds;
    }

    // 功能：核对同轮同例同构建 ticket；参数新查询可用新 command_id，但不能换证据根接管。
    private static CaptureTicket Ticket(MonoPipelineEvidenceContext context, string id)
    {
        Context(context, "screenshot");
        CaptureTicket ticket;
        if (string.IsNullOrEmpty(id) || !s_Tickets.TryGetValue(id, out ticket) || ticket == null) throw new InvalidOperationException("capture_ticket_missing");
        if (ticket.Run != context.run_id || ticket.Case != context.case_id || ticket.Build != context.build_guid || ticket.Root != EvidenceRoot(context))
            throw new InvalidOperationException("capture_ticket_context_mismatch");
        return ticket;
    }

    // 功能：新帧检查截图完成和原 SHA/大小；参数 metadata.frame 是本次观察，真实 render_frame 不可证明则 null。
    internal static object ScreenshotStatus(MonoPipelineEvidenceContext context, string id)
    {
        CaptureTicket ticket = Ticket(context, id);
        if (Time.frameCount <= ticket.RequestFrame) throw new InvalidOperationException("capture_status_requires_new_frame");
        if (!string.IsNullOrEmpty(ticket.Error)) throw new IOException(ticket.Error);
        if (!ticket.Written && Expired(ticket)) throw new TimeoutException("capture_pending_budget_expired_no_retry");
        if (ticket.Written && ticket.CompletionCheckFrame == 0) ticket.CompletionCheckFrame = Time.frameCount;
        Dictionary<string, object> result = new Dictionary<string, object> { { "ticket", id }, { "state", ticket.Written ? "complete" : "pending" },
            { "capture_request_frame", ticket.RequestFrame }, { "capture_request_utc", ticket.RequestUtc },
            { "capture_request_command_id", ticket.RequestCommand }, { "capture_call_frame", ticket.Written ? (object)ticket.CaptureCallFrame : null },
            { "first_completion_check_frame", ticket.Written ? (object)ticket.CompletionCheckFrame : null },
            { "completion_check_frame", Time.frameCount }, { "render_frame", null }, { "render_frame_known", false } };
        if (ticket.Written) result.Add("artifact", Artifact(context, ticket.Path, ticket.Hash, ticket.Bytes, "screenshot"));
        return result;
    }

    // 功能：显式释放已完成/失败/过期票据；参数仅释放内存，保留所有证据文件。
    internal static object ReleaseScreenshot(MonoPipelineEvidenceContext context, string id)
    {
        CaptureTicket ticket = Ticket(context, id);
        if (!ticket.Written && string.IsNullOrEmpty(ticket.Error) && !Expired(ticket)) throw new InvalidOperationException("capture_still_pending");
        s_Tickets.Remove(id);
        return new Dictionary<string, object> { { "released_ticket", id }, { "files_deleted", false } };
    }

    private sealed class CaptureTicket
    {
        internal string Id;
        internal string Run;
        internal string Case;
        internal string RequestCommand;
        internal string Build;
        internal string Root;
        internal string Path;
        internal string RequestUtc;
        internal int RequestFrame;
        internal int TimeoutFrames;
        internal double StartedSeconds;
        internal int CaptureCallFrame;
        internal int CompletionCheckFrame;
        internal bool Written;
        internal string Hash;
        internal long Bytes;
        internal string Error;
    }

    // 功能：维护后台日志的主线程帧样本；参数无。
    private void Update() { MonoPipelineEvidence.SampleFrame(); }

    // 功能：取消本工具订阅；参数无，不处理业务生命周期。
    private void OnDestroy() { MonoPipelineEvidence.DriverDestroyed(); }
#endif
}
