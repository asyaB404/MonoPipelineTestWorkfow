// 创建日期：2026-10-26；作者：Cyou。
// 功能：Game Tools 的新 Mono/Pipeline 测试包入口和 GameClient 原 App/资源管线适配器。
// 基础参数：用户明确选择项目外新交付目录、监听端口，并点击批准构建；不启动、登录、操作或上传游戏。
// 注意：仅临时调整 Mono/宏/HybridCLR/开发设置和 Pipeline 配置；原资源、版本、SDK 生成仍由原管线负责。
#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using Core_Editor;
using GameFramework.Base;
using GameFrameworkEditor;
using HybridCLR.Editor.Settings;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using EditorUtility = UnityEditor.EditorUtility;

namespace GameEditor
{
    /// <summary>新测试包独立入口，不调用旧测试构建模块或注册全局平台替代项。</summary>
    public static class GlobalMonoPipelineGameClientBuild
    {
        public const string MenuPath = "Game Tools/打包/Build/Build-App/Window-Mono-Pipeline测试包(新流程)";
        public const string PackageDirectoryName = "Package";
        public const string InventoryFileName = "build-inventory.json";
        private const string BackupDirectoryName = "build-backup";
        private const string StagingPrefix = ".mono-pipeline-build-";
        private const int HashBufferBytes = 1024 * 1024;
        private const int MaximumEntries = 16384;
        private static readonly string[] s_LegacySymbols = { "PC_TEST_AGENT", "DEBUG_AUTO_TEST" };
        private static bool s_Building;

        // 功能：在现有 Game Tools 分组打开参数窗口；参数无，不准备配置、构建或启动游戏。
        [MenuItem(MenuPath, false, (int)GameTools_BuildTools.BuildAppWindowMonoPipeline)]
        public static void OpenBuildWindow()
        {
            MonoPipelineGameClientBuildWindow window = EditorWindow.GetWindow<MonoPipelineGameClientBuildWindow>();
            if (window == null) throw new InvalidOperationException("mono_pipeline_build_window_missing");
            window.titleContent = new GUIContent("Mono Pipeline 测试包");
            window.minSize = new Vector2(640, 300);
            window.Show();
        }

        // 功能：菜单只在编辑器空闲时可打开；参数无，不执行构建前置或修改设置。
        [MenuItem(MenuPath, true, (int)GameTools_BuildTools.BuildAppWindowMonoPipeline)]
        private static bool ValidateMenu()
        {
            return !s_Building && !EditorApplication.isCompiling && !EditorApplication.isUpdating
                && !EditorApplication.isPlayingOrWillChangePlaymode;
        }

        // 功能：显式调用一次原完整 App/资源管线，发布新未压缩目录；参数是已批准的项目外新路径及本次端口。
        public static string Build(string outputDirectory, int runtimePort, bool approved)
        {
            if (!approved || !ValidateMenu()) throw new InvalidOperationException("explicit_idle_editor_build_approval_required");
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.StandaloneWindows64)
                throw new InvalidOperationException("switch_to_windows_64_before_build_no_automatic_platform_switch");
            if (string.IsNullOrWhiteSpace(EditorGameDefine.BuildWorkPath))
                throw new InvalidOperationException("original_build_work_path_missing");
            string output = RequireNewExternalDirectory(outputDirectory);
            string parent = Path.GetDirectoryName(output);
            if (parent == null || !Directory.Exists(parent)) throw new DirectoryNotFoundException("output_parent_missing");
            string staging = Path.Combine(parent, StagingPrefix + Guid.NewGuid().ToString("N"));
            RequireSafePath(staging);
            string project = ProjectRoot();
            string configPath = Path.Combine(project, MonoPipelineBuildSupport.ConfigurationPath);
            RequireSafePath(configPath);
            bool configExisted = File.Exists(configPath);
            string createdConfigHash = null;
            BuildSettingsSnapshot snapshot = new BuildSettingsSnapshot();
            s_Building = true;
            try
            {
                Directory.CreateDirectory(staging);
                string inventory = Path.Combine(staging, InventoryFileName);
                if (!configExisted)
                {
                    MonoPipelineBuildSupport.PrepareDisabledConfiguration(true, runtimePort);
                    createdConfigHash = FileHash(configPath);
                }
                // 构建对既有启用/port=0 配置的范围改写由本次确认覆盖，始终绑定原字节摘要。
                string configHash = MonoPipelineBuildSupport.InspectConfigurationSha256(runtimePort, true);
                snapshot.Apply();
                AppBuilderResult result = BuildPipelineX.BuildAppWithProfiler(
                    EditorGameDefine.BuildWorkPath, BuildType.App, ConfigureType.Development,
                    PlatformType.Window, BuildModeType.Original, SDKType.NO_SDK,
                    BuildProfilerType.Development, ScriptingImplementation.Mono2x,
                    delegate(BuildOption option)
                    {
                        return new MonoPipelineWindowPlatform(option, staging, inventory, configHash, runtimePort);
                    });
                if (result == null || !result.IsSuccess || result.Report == null)
                    throw new InvalidOperationException("original_pipeline_successful_report_missing");
                VerifyPackageCopy(Path.Combine(staging, PackageDirectoryName), inventory);
            }
            catch (Exception exception)
            {
                Debug.LogError("[MonoPipelineBuild] 构建未完成，保留本次暂存/备份供审查：" + staging);
                Debug.LogException(exception);
                throw;
            }
            finally
            {
                try
                {
                    snapshot.Restore();
                }
                finally
                {
                    s_Building = false;
                    if (!configExisted && createdConfigHash != null && File.Exists(configPath))
                    {
                        if (FileHash(configPath) == createdConfigHash) File.Delete(configPath);
                        else throw new IOException("new_configuration_changed_externally_preserved_at_" + configPath);
                    }
                }
            }
            // 只发布新同父目录；不覆写既有交付，不对失败做自动重建或游戏命令重试。
            RequireNewExternalDirectory(output);
            try
            {
                Directory.Move(staging, output);
            }
            catch (Exception exception)
            {
                Debug.LogError("[MonoPipelineBuild] 新目录发布失败，保留已核验暂存：" + staging);
                Debug.LogException(exception);
                throw;
            }
            Debug.Log("[MonoPipelineBuild] 文件级出包完成：" + output
                + "；手动启动 Package 内 EXE 时需要 " + GlobalMonoPipelineTest.RuntimeSwitch
                + "；构建库存未自动确认完整游戏/真实业务验收。");
            return output;
        }

        // 功能：为实际窗口平台保留原 SDK/资源生命周期；参数包含本次独享输出、配置摘要和端口。
        private sealed class MonoPipelineWindowPlatform : AppBuilderWindowNoSDK
        {
            private readonly string m_Staging;
            private readonly string m_Inventory;
            private readonly string m_ConfigHash;
            private readonly int m_Port;

            // 功能：登记本次平台上下文；参数 option 必须是原 Windows Mono 开发构建参数。
            public MonoPipelineWindowPlatform(BuildOption option, string staging, string inventory, string configHash, int port)
                : base(option)
            {
                if (option == null || option.PlatformType != PlatformType.Window
                    || option.ScriptingBackend != ScriptingImplementation.Mono2x || !option.IsProfiler)
                    throw new InvalidOperationException("original_windows_mono_development_option_required");
                m_Staging = staging;
                m_Inventory = inventory;
                m_ConfigHash = configHash;
                m_Port = port;
            }

            // 功能：用原场景/输出/资源准备调用一次真正 BuildPlayer；参数无，不调用旧测试入口。
            public override AppBuilderResult OnBuild()
            {
                if (Option == null) throw new InvalidOperationException("original_build_option_missing");
                BuildPlayerOptions original = new BuildPlayerOptions();
                original.locationPathName = Option.VersionInstallFileTempPath;
                original.scenes = GameFrameworkEditor.EditorUtility.GetEnabledScenes();
                original.target = BuildTarget.StandaloneWindows64;
                original.options = Option.BuildOptions;
                BuildPlayerOptions prepared = MonoPipelineBuildSupport.PrepareOptions(original, true);
                BuildReport report = MonoPipelineBuildSupport.RunPrepared(prepared,
                    UnityEditor.BuildPipeline.BuildPlayer, true, m_ConfigHash,
                    Path.Combine(m_Staging, BackupDirectoryName), m_Inventory, m_Port, true);
                if (report == null || report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
                    throw new InvalidOperationException("actual_windows_build_report_not_succeeded");
                return new AppBuilderResult(true, "Windows Mono Pipeline Development", report);
            }

            // 功能：仅新平台保留未压缩包，不压缩/删除原包或准备上传；参数无，复制后按真实库存逐文件核验。
            public override void OnPostBuild()
            {
                if (Option == null) throw new InvalidOperationException("original_build_option_missing");
                string package = Path.Combine(m_Staging, PackageDirectoryName);
                CopyPackage(Option.VersionInstallTempPath, package);
                VerifyPackageCopy(package, m_Inventory);
            }
        }

        // 功能：持有本次要临时调整的编辑器设置；参数无，不声称资源/SDK生成或域重载能自动回滚。
        private sealed class BuildSettingsSnapshot
        {
            private readonly ScriptingImplementation m_Backend;
            private readonly Il2CppCodeGeneration m_CodeGeneration;
            private readonly string m_Defines;
            private readonly bool m_Development;
            private readonly bool m_ConnectProfiler;
            private readonly bool m_AllowDebugging;
            private readonly bool m_HybridEnabled;
            private bool m_Touched;

            // 功能：只读捕获后端/宏/开发与 HybridCLR 设置；参数无，缺必要实例直接拒绝。
            public BuildSettingsSnapshot()
            {
                if (HybridCLRSettings.Instance == null) throw new InvalidOperationException("hybridclr_settings_missing");
                m_Backend = PlayerSettings.GetScriptingBackend(BuildTargetGroup.Standalone);
                m_CodeGeneration = PlayerSettings.GetIl2CppCodeGeneration(NamedBuildTarget.Standalone);
                m_Defines = PlayerSettings.GetScriptingDefineSymbolsForGroup(BuildTargetGroup.Standalone);
                m_Development = EditorUserBuildSettings.development;
                m_ConnectProfiler = EditorUserBuildSettings.connectProfiler;
                m_AllowDebugging = EditorUserBuildSettings.allowDebugging;
                m_HybridEnabled = HybridCLRSettings.Instance.enable;
            }

            // 功能：仅本次临时关闭 HybridCLR、选择 Mono 和隔离旧启动宏；参数无，不安装或更换插件。
            public void Apply()
            {
                m_Touched = true;
                HybridCLRSettings settings = HybridCLRSettings.Instance;
                if (settings == null) throw new InvalidOperationException("hybridclr_settings_missing");
                settings.enable = false;
                HybridCLRSettings.Save();
                PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone, ScriptingImplementation.Mono2x);
                HashSet<string> defines = new HashSet<string>(StringComparer.Ordinal);
                if (!string.IsNullOrEmpty(m_Defines))
                {
                    foreach (string item in m_Defines.Split(';'))
                    {
                        string value = item.Trim();
                        if (value.Length > 0) defines.Add(value);
                    }
                }
                foreach (string legacy in s_LegacySymbols) defines.Remove(legacy);
                defines.Add(MonoPipelineBuildSupport.TestSymbol);
                string[] ordered = new string[defines.Count];
                defines.CopyTo(ordered);
                Array.Sort(ordered, StringComparer.Ordinal);
                PlayerSettings.SetScriptingDefineSymbolsForGroup(BuildTargetGroup.Standalone, string.Join(";", ordered));
                EditorUserBuildSettings.development = true;
                EditorUserBuildSettings.connectProfiler = false;
                EditorUserBuildSettings.allowDebugging = true;
            }

            // 功能：每项独立尝试恢复本次快照，错误不冒充恢复成功；参数无，不承诺强杀/域重载回滚。
            public void Restore()
            {
                if (!m_Touched) return;
                List<Exception> errors = new List<Exception>();
                RestoreStep(delegate { PlayerSettings.SetScriptingDefineSymbolsForGroup(BuildTargetGroup.Standalone, m_Defines); }, errors);
                RestoreStep(delegate { PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone, m_Backend); }, errors);
                RestoreStep(delegate { PlayerSettings.SetIl2CppCodeGeneration(NamedBuildTarget.Standalone, m_CodeGeneration); }, errors);
                RestoreStep(delegate { EditorUserBuildSettings.development = m_Development;
                    EditorUserBuildSettings.connectProfiler = m_ConnectProfiler; EditorUserBuildSettings.allowDebugging = m_AllowDebugging; }, errors);
                RestoreStep(delegate
                {
                    HybridCLRSettings settings = HybridCLRSettings.Instance;
                    if (settings == null) throw new InvalidOperationException("hybridclr_settings_missing_during_restore");
                    settings.enable = m_HybridEnabled;
                    HybridCLRSettings.Save();
                }, errors);
                RestoreStep(delegate { AssetDatabase.SaveAssets(); }, errors);
                if (errors.Count > 0) throw new AggregateException("mono_pipeline_build_settings_restore_failed", errors);
            }
        }

        // 功能：独立执行恢复项并保留失败；参数 action 为该项恢复操作，errors 为本次共享错误列表。
        private static void RestoreStep(Action action, List<Exception> errors)
        {
            try { action(); }
            catch (Exception exception) { errors.Add(exception); }
        }

        // 功能：项目外新交付落点核验；参数必须为明确本地绝对路径，不接受现存/项目内/项目祖先。
        private static string RequireNewExternalDirectory(string encoded)
        {
            if (string.IsNullOrWhiteSpace(encoded) || !Path.IsPathRooted(encoded) || encoded.StartsWith("\\\\", StringComparison.Ordinal))
                throw new IOException("explicit_external_local_output_required");
            string output = Path.GetFullPath(encoded).TrimEnd(Path.DirectorySeparatorChar);
            string project = ProjectRoot().TrimEnd(Path.DirectorySeparatorChar);
            if ((output + Path.DirectorySeparatorChar).StartsWith(project + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
                || (project + Path.DirectorySeparatorChar).StartsWith(output + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new IOException("output_must_be_outside_project_and_not_its_ancestor");
            RequireSafePath(output);
            if (File.Exists(output) || Directory.Exists(output)) throw new IOException("new_output_already_exists");
            return output;
        }

        // 功能：从真实资源根求当前项目根；参数无，不固定维护机盘符或业务场景路径。
        private static string ProjectRoot()
        {
            DirectoryInfo parent = Directory.GetParent(Application.dataPath);
            if (parent == null) throw new IOException("project_root_missing");
            return parent.FullName;
        }

        // 功能：拒绝路径链中的重解析点；参数路径是源包或明确的新交付/暂存。
        private static void RequireSafePath(string path)
        {
            MonoPipelineBuildSupport.SafePath(path, false);
        }

        // 功能：复制本次完整静态包至新目录；参数不覆写、不追踪链接、不裁掉资源/动态内容。
        private static void CopyPackage(string source, string target)
        {
            RequireSafePath(source);
            RequireSafePath(target);
            if (!Directory.Exists(MonoPipelineBuildSupport.GetFileSystemPath(source))
                || File.Exists(MonoPipelineBuildSupport.GetFileSystemPath(target))
                || Directory.Exists(MonoPipelineBuildSupport.GetFileSystemPath(target)))
                throw new IOException("actual_source_package_and_new_target_required");
            Queue<KeyValuePair<string, string>> directories = new Queue<KeyValuePair<string, string>>();
            directories.Enqueue(new KeyValuePair<string, string>(source, target));
            int count = 0;
            while (directories.Count > 0)
            {
                KeyValuePair<string, string> pair = directories.Dequeue();
                Directory.CreateDirectory(MonoPipelineBuildSupport.GetFileSystemPath(pair.Value));
                string[] members = MonoPipelineBuildSupport.GetFileSystemEntries(pair.Key);
                if (members == null) throw new IOException("build_package_directory_unreadable");
                foreach (string member in members)
                {
                    if (++count > MaximumEntries) throw new IOException("build_package_entry_budget_exceeded");
                    RequireSafePath(member);
                    string destination = Path.Combine(pair.Value, Path.GetFileName(member));
                    if (Directory.Exists(MonoPipelineBuildSupport.GetFileSystemPath(member)))
                        directories.Enqueue(new KeyValuePair<string, string>(member, destination));
                    else File.Copy(MonoPipelineBuildSupport.GetFileSystemPath(member), MonoPipelineBuildSupport.GetFileSystemPath(destination), false);
                }
            }
        }

        // 功能：按真实库存逐文件核验新包，拒绝缺失/额外/摘要变化；参数 package/inventory 仅为本次目录。
        private static void VerifyPackageCopy(string package, string inventoryPath)
        {
            RequireSafePath(package);
            RequireSafePath(inventoryPath);
            JObject inventory = JObject.Parse(File.ReadAllText(MonoPipelineBuildSupport.GetFileSystemPath(inventoryPath)));
            JArray files = inventory["files"] as JArray;
            if (files == null || files.Count < 1 || files.Count > MaximumEntries)
                throw new IOException("actual_build_file_inventory_missing");
            string prefix = Path.GetFullPath(package).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            HashSet<string> names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (JToken token in files)
            {
                if (token == null) throw new IOException("build_inventory_member_missing");
                string relative = (string)token["path"];
                if (string.IsNullOrEmpty(relative) || Path.IsPathRooted(relative) || !names.Add(relative))
                    throw new IOException("build_inventory_path_invalid_or_duplicate");
                string file = Path.Combine(package, relative.Replace(Path.AltDirectorySeparatorChar, Path.DirectorySeparatorChar));
                if (!file.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) throw new IOException("build_inventory_path_escape");
                RequireSafePath(file);
                FileInfo information = new FileInfo(MonoPipelineBuildSupport.GetFileSystemPath(file));
                if (!information.Exists || information.Length != (long)token["bytes"] || FileHash(file) != (string)token["sha256"])
                    throw new IOException("copied_build_inventory_member_changed_" + relative);
            }
            string[] actual = Directory.GetFiles(MonoPipelineBuildSupport.GetFileSystemPath(package), "*", SearchOption.AllDirectories);
            if (actual == null || actual.Length != names.Count) throw new IOException("copied_package_has_extra_or_missing_files");
        }

        // 功能：普通文件流式 SHA256；参数只读取本次配置/库存成员，不加载或执行文件。
        private static string FileHash(string path)
        {
            RequireSafePath(path);
            using (FileStream stream = new FileStream(MonoPipelineBuildSupport.GetFileSystemPath(path), FileMode.Open, FileAccess.Read, FileShare.Read, HashBufferBytes))
            using (SHA256 hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
    }

    /// <summary>显式选择新输出和端口的参数窗口；仅点击并确认构建后才改设置。</summary>
    public sealed class MonoPipelineGameClientBuildWindow : EditorWindow
    {
        [SerializeField] private string m_OutputParent = string.Empty;
        [SerializeField] private string m_OutputName = string.Empty;
        [SerializeField] private int m_Port = MonoPipelineBuildSupport.DefaultHostPort;

        // 功能：初始化可编辑的新目录名；参数无，不创建目录或准备构建配置。
        private void OnEnable()
        {
            if (string.IsNullOrEmpty(m_OutputName))
                m_OutputName = "MonoPipelineTest-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 8);
        }

        // 功能：显示本次构建参数与明确审批；参数无，打开窗口不会调用构建或启动 Player。
        private void OnGUI()
        {
            EditorGUILayout.HelpBox("新流程：原 App/资源构建 + Windows Mono 开发包。需要先手动切换 Windows 64。"
                + "本次临时调整后端/宏/HybridCLR/通道配置并恢复；不启动、登录、发 GM 或上传游戏。", MessageType.Info);
            m_OutputParent = EditorGUILayout.TextField("项目外输出父目录", m_OutputParent);
            if (GUILayout.Button("选择输出父目录"))
            {
                string selected = EditorUtility.OpenFolderPanel("选择项目外输出父目录", m_OutputParent, string.Empty);
                if (!string.IsNullOrEmpty(selected)) m_OutputParent = selected;
            }
            m_OutputName = EditorGUILayout.TextField("新的交付目录名", m_OutputName);
            m_Port = EditorGUILayout.IntField("本次监听端口", m_Port);
            EditorGUILayout.HelpBox("端口由同包宿主契约核验。当前已有启用/自动端口配置也只在本次批准范围内改写，原字节恢复。"
                + "输出包含 Package 和 build-inventory.json；库存不自动确认完整游戏或真实测试通过。", MessageType.None);
            if (GUILayout.Button("确认参数并构建新测试包"))
            {
                try
                {
                    if (string.IsNullOrWhiteSpace(m_OutputParent) || string.IsNullOrWhiteSpace(m_OutputName)
                        || m_OutputName != Path.GetFileName(m_OutputName) || m_OutputName.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
                        throw new IOException("explicit_output_parent_and_single_new_directory_name_required");
                    string output = Path.Combine(m_OutputParent, m_OutputName);
                    bool approved = EditorUtility.DisplayDialog("批准新 Mono Pipeline 测试包构建",
                        "将调用原完整 App/资源管线，并临时选择 Mono、隔离旧测试宏、关闭 HybridCLR、启用开发和本次 Pipeline 配置。"
                        + "\n输出：" + output + "\n不会启动或操作游戏；不承诺强杀/域重载自动回滚。", "批准本次构建", "取消");
                    if (approved)
                    {
                        string actual = GlobalMonoPipelineGameClientBuild.Build(output, m_Port, true);
                        EditorUtility.DisplayDialog("新测试包文件级构建完成", actual + "\n请使用 Package 内 EXE；业务与运行时仍须独立验收。", "确认");
                    }
                }
                catch (Exception exception)
                {
                    Debug.LogException(exception);
                    EditorUtility.DisplayDialog("新测试包构建未完成", exception.Message + "\n未自动重试、启动或修复游戏。", "确认");
                }
            }
        }
    }
}
#endif
