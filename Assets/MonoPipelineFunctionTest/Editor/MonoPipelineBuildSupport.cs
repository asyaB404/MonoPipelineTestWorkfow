// 创建日期：2026-10-26；作者：Cyou。
// 功能：未来显式配置准备、原构建管线的参数/配置范围辅助、成功 BuildReport 的离线库存；基础参数：明确批准、原选项/管线、配置摘要、项目外新备份和包外新库存路径。
// 不含固定场景 BuildPlayer，不安装/启动服务；正常 finally 恢复不承诺域重载、掉电或强杀回滚。
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Unity.Pipeline.Config;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

/// <summary>由目标项目的原 App/资源管线显式调用；不直接依赖热更插件或替换原出包流程。</summary>
public static class MonoPipelineBuildSupport
{
    public const string TestSymbol = "MONO_PIPELINE_FUNCTIONTEST";
    public const string ConfigurationPath = "ProjectSettings/Packages/com.unity.pipeline/RuntimePipelineConfig.json";
    private const string ManifestName = "package-manifest.json";
    private const string DescriptorName = ".unity-pipeline-runtime-port";
    private const int DefaultPort = 7901;
    private const int MinimumPort = 7900;
    private const int MaximumPort = 7949;
    private const int RequestTimeoutMilliseconds = 5000;
    private const int MaximumWorkItemsPerFrame = 1;
    private const int MaximumConfigBytes = 64 * 1024;
    private const int MaximumPackageEntries = 16384;
    private const long MaximumPackageFileBytes = 1024L * 1024L * 1024L;
    private const int HashBufferBytes = 1024 * 1024;
    private const int MaximumConfigurationDepth = 8;
    private const string WindowsExtendedPathPrefix = "\\\\?\\";
    private static readonly UTF8Encoding s_Utf8 = new UTF8Encoding(false, true);

    // 功能：提供同一份宿主端口默认值；参数无，不读取或修改工程配置。
    public static int DefaultHostPort { get { return DefaultPort; } }

    // 功能：只读核验本次构建配置并返回原字节摘要；参数明确端口与对既有启用配置的本次审阅批准。
    public static string InspectConfigurationSha256(int runtimePort, bool approvedExistingEnabled)
    {
        if (runtimePort < MinimumPort || runtimePort > MaximumPort)
            throw new InvalidOperationException("explicit_host_port_required");
        string path = ProjectPath(ConfigurationPath);
        JObject configuration = ReadConfiguration(path, true);
        if ((bool)configuration["enableInBuilds"] && !approvedExistingEnabled)
            throw new InvalidOperationException("existing_enabled_configuration_requires_explicit_scoped_review");
        return FileHash(path);
    }

    // 功能：提供显式编辑器菜单，只准备禁用配置；参数无，已有配置只核对并保留。
    [MenuItem("Tools/Mono Pipeline FunctionTest/Prepare disabled configuration")]
    public static void PrepareDisabledConfigurationMenu()
    {
        bool approved = EditorUtility.DisplayDialog("Mono Pipeline FunctionTest",
            "仅在缺失时创建禁用的 Pipeline 配置。不会编译、构建、启动或批准运行时权限。", "明确批准配置准备", "取消");
        if (approved) PrepareDisabledConfiguration(true, DefaultPort);
    }

    // 功能：缺失时显式新建小型禁用配置；参数 approved/port 是本次批准，不创建 .asset 或覆盖未知配置。
    public static void PrepareDisabledConfiguration(bool approved, int port)
    {
        if (!approved || port < MinimumPort || port > MaximumPort) throw new InvalidOperationException("explicit_configuration_approval_and_host_port_required");
        string path = ProjectPath(ConfigurationPath);
        SafePath(path, false);
        if (File.Exists(path))
        {
            JObject existing = ReadConfiguration(path);
            if ((bool)existing["enableInBuilds"]) throw new InvalidOperationException("existing_enabled_configuration_requires_project_review");
            return;
        }
        string parent = Path.GetDirectoryName(path);
        if (parent == null) throw new IOException("configuration_parent_missing");
        Directory.CreateDirectory(parent);
        JObject config = new JObject {
            ["enableInBuilds"] = false, ["port"] = port, ["requestTimeoutMs"] = RequestTimeoutMilliseconds,
            ["enableAuditLogging"] = true, ["autoStart"] = true, ["maxWorkItemsPerFrame"] = MaximumWorkItemsPerFrame
        };
        WriteNew(path, s_Utf8.GetBytes(config.ToString(Formatting.Indented)));
    }

    // 功能：保留原场景/资源/输出，只增加本次宏和 Development 选项；参数原选项必须为既有 Windows Mono 管线。
    public static BuildPlayerOptions PrepareOptions(BuildPlayerOptions original, bool approved)
    {
        if (!approved || original.target != BuildTarget.StandaloneWindows64
            || string.IsNullOrEmpty(original.locationPathName) || original.scenes == null || original.scenes.Length == 0)
            throw new InvalidOperationException("explicit_original_windows_build_options_required");
        if (PlayerSettings.GetScriptingBackend(BuildTargetGroup.Standalone) != ScriptingImplementation.Mono2x)
            throw new InvalidOperationException("project_mono_backend_must_be_prepared_by_original_pipeline");
        HashSet<string> symbols = new HashSet<string>(StringComparer.Ordinal);
        if (original.extraScriptingDefines != null)
        {
            foreach (string symbol in original.extraScriptingDefines)
            {
                if (!string.IsNullOrWhiteSpace(symbol)) symbols.Add(symbol);
            }
        }
        symbols.Add(TestSymbol);
        string[] defines = new string[symbols.Count];
        symbols.CopyTo(defines);
        Array.Sort(defines, StringComparer.Ordinal);
        original.extraScriptingDefines = defines;
        original.options |= BuildOptions.Development;
        return original;
    }

    // 功能：在新外部备份保护下临时启用 Pipeline，调用原管线一次并输出真实库存；参数不授权运行 Player。
    public static BuildReport RunPrepared(BuildPlayerOptions prepared, Func<BuildPlayerOptions, BuildReport> originalPipeline,
        bool approved, string approvedConfigSha256, string externalBackupDirectory, string inventoryOutput)
    {
        return RunPreparedCore(prepared, originalPipeline, approved, approvedConfigSha256,
            externalBackupDirectory, inventoryOutput, null, false);
    }

    // 功能：对已有启用/自动端口配置做明确批准的本次范围改写；参数 runtimePort/approvedExistingEnabled 不授予运行权限。
    public static BuildReport RunPrepared(BuildPlayerOptions prepared, Func<BuildPlayerOptions, BuildReport> originalPipeline,
        bool approved, string approvedConfigSha256, string externalBackupDirectory, string inventoryOutput,
        int runtimePort, bool approvedExistingEnabled)
    {
        if (runtimePort < MinimumPort || runtimePort > MaximumPort)
            throw new InvalidOperationException("explicit_host_port_required");
        return RunPreparedCore(prepared, originalPipeline, approved, approvedConfigSha256,
            externalBackupDirectory, inventoryOutput, runtimePort, approvedExistingEnabled);
    }

    // 功能：共用一次原构建调用和原字节恢复；参数可选本次端口及既有启用配置审阅，不改全局后端或宏。
    private static BuildReport RunPreparedCore(BuildPlayerOptions prepared, Func<BuildPlayerOptions, BuildReport> originalPipeline,
        bool approved, string approvedConfigSha256, string externalBackupDirectory, string inventoryOutput,
        int? runtimePort, bool approvedExistingEnabled)
    {
        if (!approved || originalPipeline == null || prepared.target != BuildTarget.StandaloneWindows64
            || (prepared.options & BuildOptions.Development) == 0 || prepared.extraScriptingDefines == null
            || Array.IndexOf(prepared.extraScriptingDefines, TestSymbol) < 0)
            throw new InvalidOperationException("explicit_prepared_original_pipeline_required");
        if (PlayerSettings.GetScriptingBackend(BuildTargetGroup.Standalone) != ScriptingImplementation.Mono2x)
            throw new InvalidOperationException("mono_backend_required_no_automatic_hybrid_pipeline_conversion");
        string configPath = ProjectPath(ConfigurationPath);
        JObject configuration = ReadConfiguration(configPath, runtimePort.HasValue);
        byte[] before = File.ReadAllBytes(configPath);
        if (Sha256(before) != approvedConfigSha256
            || ((bool)configuration["enableInBuilds"] && !approvedExistingEnabled))
            throw new InvalidOperationException("configuration_approval_changed_or_already_enabled");
        string backup = ExternalPath(externalBackupDirectory);
        string inventory = ExternalPath(inventoryOutput);
        if (File.Exists(backup) || Directory.Exists(backup) || File.Exists(inventory) || Directory.Exists(inventory))
            throw new IOException("backup_and_inventory_must_be_new");
        string backupParent = Path.GetDirectoryName(backup);
        if (backupParent == null || !Directory.Exists(backupParent)) throw new DirectoryNotFoundException("external_backup_parent_missing");
        Directory.CreateDirectory(backup);
        WriteNew(Path.Combine(backup, "RuntimePipelineConfig.json"), before);
        configuration["enableInBuilds"] = true;
        configuration["autoStart"] = true;
        configuration["enableAuditLogging"] = true;
        if (runtimePort.HasValue) configuration["port"] = runtimePort.Value;
        configuration["requestTimeoutMs"] = RequestTimeoutMilliseconds;
        configuration["maxWorkItemsPerFrame"] = MaximumWorkItemsPerFrame;
        byte[] scoped = s_Utf8.GetBytes(configuration.ToString(Formatting.Indented));
        ReplaceKnown(configPath, approvedConfigSha256, scoped);
        bool previousDevelopment = EditorUserBuildSettings.development;
        EditorUserBuildSettings.development = true;
        try
        {
            BuildReport report = originalPipeline(prepared);
            if (report == null) throw new InvalidOperationException("original_build_report_missing");
            WriteSuccessfulBuildInventory(report, inventory);
            return report;
        }
        finally
        {
            try
            {
                ReplaceKnown(configPath, Sha256(scoped), before);
            }
            finally
            {
                if (EditorUserBuildSettings.development)
                    EditorUserBuildSettings.development = previousDevelopment;
                else
                    Debug.LogError("Development setting changed externally; preserved, configuration backup requires review.");
            }
        }
    }

    // 功能：供原 App/资源管线在成功构建后独立调用；参数真实 BuildReport/newOutput 不自动确认完整游戏交付。
    public static void WriteSuccessfulBuildInventory(BuildReport report, string newOutput)
    {
        if (report == null) throw new ArgumentNullException("report");
        BuildSummary summary = report.summary;
        if ((object)summary == null || summary.result != BuildResult.Succeeded || summary.platform != BuildTarget.StandaloneWindows64
            || (summary.options & BuildOptions.Development) == 0
            || PlayerSettings.GetScriptingBackend(BuildTargetGroup.Standalone) != ScriptingImplementation.Mono2x)
            throw new InvalidOperationException("successful_windows_mono_development_build_report_required");
        string exe = Path.GetFullPath(summary.outputPath);
        if (!File.Exists(exe) || !string.Equals(Path.GetExtension(exe), ".exe", StringComparison.OrdinalIgnoreCase))
            throw new IOException("build_report_exe_missing");
        string root = Path.GetDirectoryName(exe);
        if (root == null) throw new IOException("build_package_root_missing");
        string output = ExternalPath(newOutput);
        if ((output + Path.DirectorySeparatorChar).StartsWith(root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("build_inventory_must_be_outside_static_package");
        List<object> files = ScanPackage(root);
        BuildFile[] reportFiles = report.GetFiles();
        if (reportFiles == null || reportFiles.Length > MaximumPackageEntries) throw new InvalidOperationException("build_report_file_inventory_invalid");
        List<object> origins = new List<object>();
        foreach (BuildFile file in reportFiles)
        {
            if ((object)file == null || string.IsNullOrEmpty(file.path)) throw new InvalidOperationException("build_report_file_missing");
            string absolute = Path.GetFullPath(file.path);
            string prefix = root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!absolute.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new IOException("build_report_file_outside_package");
            origins.Add(new Dictionary<string, object> { { "path", absolute.Substring(prefix.Length).Replace('\\', '/') },
                { "bytes", file.size }, { "role", file.role } });
        }
        Dictionary<string, object> inventory = new Dictionary<string, object> {
            { "_comment", "创建日期：2026-10-26；作者：Cyou；功能：成功 BuildReport 的实际静态库存；参数：包外文件、真实构建身份/成员；完整游戏交付需独立明确审阅。" },
            { "schema", "mono-pipeline-build-inventory/1" }, { "source", "BuildReport" }, { "build_result", "Succeeded" },
            { "exe", Path.GetFileName(exe) }, { "build_guid", summary.guid.ToString() }, { "unity_version", Application.unityVersion },
            { "platform", "WindowsPlayer" }, { "backend", "mono" }, { "development", true },
            { "files", files }, { "report_files", origins }, { "report_total_size", summary.totalSize },
            { "complete_game_delivery", false }, { "acceptance_gaps", new string[] {
                "Original game App/resource/hot-update inventory requires explicit complete-delivery review", "Unity/Player and business acceptance are separate" } }
        };
        WriteNew(output, s_Utf8.GetBytes(JsonConvert.SerializeObject(inventory, Formatting.Indented)));
    }

    // 功能：扫描全部实际静态文件和摘要，包括 0 字节成员；参数只排除根清单/运行描述符，拒绝链接、重复路径和超预算。
    private static List<object> ScanPackage(string root)
    {
        SafePath(root, true);
        Queue<string> directories = new Queue<string>();
        directories.Enqueue(root);
        HashSet<string> names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        List<object> files = new List<object>();
        int entries = 0;
        string prefix = root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        while (directories.Count > 0)
        {
            string directory = directories.Dequeue();
            string[] members = GetFileSystemEntries(directory);
            if (members == null) throw new IOException("package_directory_unreadable");
            foreach (string path in members)
            {
                if (++entries > MaximumPackageEntries) throw new IOException("package_entry_budget_exceeded");
                FileAttributes attributes = File.GetAttributes(GetFileSystemPath(path));
                if ((attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("package_reparse_point_refused");
                string relative = path.Substring(prefix.Length).Replace('\\', '/');
                if (!names.Add(relative)) throw new IOException("package_case_conflict");
                if ((attributes & FileAttributes.Directory) != 0) { directories.Enqueue(path); continue; }
                if (relative == ManifestName || relative == DescriptorName) continue;
                FileInfo information = new FileInfo(GetFileSystemPath(path));
                long bytes = information.Exists ? information.Length : -1;
                if (bytes < 0 || bytes > MaximumPackageFileBytes)
                    throw new IOException("package_member_byte_budget_invalid: path=" + relative
                        + "; bytes=" + bytes + "; max=" + MaximumPackageFileBytes);
                files.Add(new Dictionary<string, object> { { "path", relative }, { "bytes", bytes }, { "sha256", FileHash(path) } });
            }
        }
        return files;
    }

    // 功能：核验既有 Pipeline 小配置和实际 Load；参数未知字段/类型/端口保守拒绝，不覆写大文件。
    private static JObject ReadConfiguration(string path, bool allowAutomaticPort = false)
    {
        SafePath(path, true);
        FileInfo file = new FileInfo(path);
        if (!file.Exists || file.Length < 1 || file.Length > MaximumConfigBytes) throw new IOException("pipeline_configuration_byte_budget_invalid");
        JObject document;
        using (JsonTextReader reader = new JsonTextReader(new StringReader(s_Utf8.GetString(File.ReadAllBytes(path)))))
        {
            reader.MaxDepth = MaximumConfigurationDepth;
            document = JObject.Load(reader, new JsonLoadSettings { DuplicatePropertyNameHandling = DuplicatePropertyNameHandling.Error });
        }
        if (document == null) throw new IOException("pipeline_configuration_missing");
        HashSet<string> allowed = new HashSet<string>(new string[] { "enableInBuilds", "port", "requestTimeoutMs", "enableAuditLogging", "autoStart", "maxWorkItemsPerFrame" }, StringComparer.Ordinal);
        foreach (JProperty property in document.Properties())
        {
            if (property == null || !allowed.Remove(property.Name)) throw new IOException("pipeline_configuration_unknown_field");
        }
        if (allowed.Count != 0 || document["enableInBuilds"].Type != JTokenType.Boolean || document["autoStart"].Type != JTokenType.Boolean
            || document["enableAuditLogging"].Type != JTokenType.Boolean || document["port"].Type != JTokenType.Integer
            || document["requestTimeoutMs"].Type != JTokenType.Integer || document["maxWorkItemsPerFrame"].Type != JTokenType.Integer)
            throw new IOException("pipeline_configuration_metadata_mismatch");
        int port = (int)document["port"];
        if ((port != 0 || !allowAutomaticPort) && (port < MinimumPort || port > MaximumPort))
            throw new IOException("pipeline_configuration_port_outside_host_contract");
        RuntimePipelineConfig actual = RuntimePipelineConfig.Load();
        if (actual == null) throw new IOException("pipeline_configuration_load_failed");
        UnityEngine.Object.DestroyImmediate(actual);
        return document;
    }

    // 功能：求项目内精确路径；参数 relative 是公共固定小配置路径。
    private static string ProjectPath(string relative)
    {
        DirectoryInfo parent = Directory.GetParent(Application.dataPath);
        if (parent == null) throw new IOException("project_root_missing");
        return Path.Combine(parent.FullName, relative);
    }

    // 功能：验证明确项目外路径；参数只允许本地新备份/库存，不接受上溯、设备或 UNC 路径。
    private static string ExternalPath(string encoded)
    {
        if (string.IsNullOrEmpty(encoded) || !Path.IsPathRooted(encoded) || encoded.StartsWith("\\\\", StringComparison.Ordinal))
            throw new IOException("explicit_external_local_path_required");
        foreach (string part in encoded.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar))
        {
            if (part == ".." || part == ".") throw new IOException("external_path_traversal_refused");
        }
        string full = Path.GetFullPath(encoded);
        DirectoryInfo project = Directory.GetParent(Application.dataPath);
        if (project == null || (full + Path.DirectorySeparatorChar).StartsWith(project.FullName.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("backup_inventory_must_be_outside_project_and_project_tool");
        SafePath(full, false);
        return full;
    }

    // 功能：将已规范的本地绝对路径转换为内部 I/O 路径；参数不接受 UNC、设备路径或上溯，Windows 使用扩展前缀。
    public static string GetFileSystemPath(string path)
    {
        if (string.IsNullOrEmpty(path) || !Path.IsPathRooted(path)) throw new IOException("absolute_local_filesystem_path_required");
        string logical = path.Replace(Path.AltDirectorySeparatorChar, Path.DirectorySeparatorChar);
        foreach (string part in logical.Split(Path.DirectorySeparatorChar))
        {
            if (part == "." || part == "..") throw new IOException("filesystem_path_traversal_refused");
        }
        if (Path.DirectorySeparatorChar != '\\') return logical;
        if (logical.Length < 3 || !char.IsLetter(logical[0]) || logical[1] != ':' || logical[2] != '\\')
            throw new IOException("absolute_local_filesystem_path_required");
        return WindowsExtendedPathPrefix + logical;
    }

    // 功能：长路径枚举后返回普通逻辑路径，不把内部前缀写进库存；参数 directory 是已规范的本地绝对目录。
    public static string[] GetFileSystemEntries(string directory)
    {
        string[] entries = Directory.GetFileSystemEntries(GetFileSystemPath(directory));
        if (entries == null) throw new IOException("package_directory_unreadable");
        if (Path.DirectorySeparatorChar == '\\')
        {
            for (int index = 0; index < entries.Length; index++)
            {
                if (entries[index] == null) throw new IOException("package_member_path_missing");
                if (entries[index].StartsWith(WindowsExtendedPathPrefix, StringComparison.Ordinal))
                    entries[index] = entries[index].Substring(WindowsExtendedPathPrefix.Length);
            }
        }
        return entries;
    }

    // 功能：支持长路径的全路径链重解析检查；参数 requireExisting 区分新文件与既有配置/包，不授予构建或写入许可。
    public static void SafePath(string path, bool requireExisting)
    {
        string full = GetFileSystemPath(path);
        if (requireExisting && !File.Exists(full) && !Directory.Exists(full)) throw new IOException("required_path_missing");
        string current = path.Replace(Path.AltDirectorySeparatorChar, Path.DirectorySeparatorChar);
        while (!string.IsNullOrEmpty(current))
        {
            string ioPath = GetFileSystemPath(current);
            if ((File.Exists(ioPath) || Directory.Exists(ioPath)) && (File.GetAttributes(ioPath) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("reparse_point_refused");
            string trimmed = current.TrimEnd(Path.DirectorySeparatorChar);
            int separator = trimmed.LastIndexOf(Path.DirectorySeparatorChar);
            if (separator < 0) break;
            if (Path.DirectorySeparatorChar == '\\' && separator == 2) current = trimmed.Substring(0, 3);
            else if (separator == 0) current = Path.DirectorySeparatorChar.ToString();
            else current = trimmed.Substring(0, separator);
        }
    }

    // 功能：有界流式文件摘要；参数 path 是当前普通文件。
    private static string FileHash(string path)
    {
        SafePath(path, true);
        using (FileStream stream = new FileStream(GetFileSystemPath(path), FileMode.Open, FileAccess.Read, FileShare.Read, HashBufferBytes))
        using (SHA256 hash = SHA256.Create())
        {
            return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
    }

    // 功能：计算实际配置字节摘要；参数 bytes 不转码归一。
    private static string Sha256(byte[] bytes)
    {
        if (bytes == null) throw new ArgumentNullException("bytes");
        using (SHA256 hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }

    // 功能：普通文件新建写入；参数不覆盖既有交付/备份。
    private static void WriteNew(string path, byte[] bytes)
    {
        if (bytes == null) throw new ArgumentNullException("bytes");
        SafePath(path, false);
        string parent = Path.GetDirectoryName(path);
        if (parent == null || !Directory.Exists(parent)) throw new IOException("new_file_parent_missing");
        using (FileStream stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            stream.Write(bytes, 0, bytes.Length);
            stream.Flush(true);
        }
    }

    // 功能：仅替换仍匹配批准摘要的小配置；参数外部修改保留并报错，正常路径使用原字节恢复。
    private static void ReplaceKnown(string path, string expected, byte[] bytes)
    {
        if (bytes == null || FileHash(path) != expected) throw new IOException("configuration_changed_preserved_not_overwritten");
        string temporary = path + ".mono-pipeline-" + Guid.NewGuid().ToString("N");
        WriteNew(temporary, bytes);
        try
        {
            if (FileHash(path) != expected) throw new IOException("configuration_changed_before_replace");
            File.Replace(temporary, path, null);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }
}
#endif
