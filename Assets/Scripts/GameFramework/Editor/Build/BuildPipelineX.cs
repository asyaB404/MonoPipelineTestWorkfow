// ========================================================================
// Copyright (c) 2022 ChangYou, All rights reserved.
// http://www.changyou.com/
// 
// Filename:    BuildPipelineX.cs
// Time:        2022-03-11 11:24:24
// Author:      xiangjinbao
// Email:       xiangjinbao@cyou-inc.com
// Version:     v1.0.0
// Description: BuildPipelineX
// ========================================================================

using System;
using System.IO;
using System.Text;
using GameFramework.Base;
using GameFrameworkEditor;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using EditorUtility = UnityEditor.EditorUtility;

public static class BuildPipelineX
{
    /// <summary>
    /// 命令行构建接口。成功或失败都会显式退出 Unity，避免批处理进程残留。
    /// </summary>
    public static void Build()
    {
        int exitCode;
        try
        {
            InternalBuild();
            exitCode = 0;
        }
        catch (Exception exception)
        {
            Debug.LogError("[Build] CLI build failed, Unity will exit with code 1.");
            Debug.LogException(exception);
            exitCode = 1;
        }

        EditorApplication.Exit(exitCode);
    }

    /// <summary>
    /// 执行命令行构建内部流程。
    /// </summary>
    private static void InternalBuild()
    {
        if (string.IsNullOrEmpty(Environment.CommandLine))
        {
            throw new FrameworkException("Build input param is invalid.");
        }

        Debug.LogFormat("[Build] Input Infos: \n{0}", ToFormatArgs());

        BuildOption option = BuildOption.Create(Environment.GetCommandLineArgs());
        SetBuildMode(option, BuildRunType.CLI);
        PlatformConfig platformConfig = UpdateBuildConfig(option);
        
        // 切换平台
        if (option.PlatformType != PlatformType.Invalid)
        {
            Debug.Log("SwitchPlatform before, curPlatform : " + EditorUserBuildSettings.activeBuildTarget);
            bool switchResult = GameFrameworkEditor.EditorUtility.SwitchPlatform(option.PlatformType);// 代码切换平台后直接打包存在问题
            if (switchResult)
            {
                Debug.LogError("[Build] first SwitchPlatform build may failure, please build.");
            }
            Debug.Log("SwitchPlatform after, curPlatform : " + EditorUserBuildSettings.activeBuildTarget);
        }
        else
        {
            Debug.LogError("[Build] platform is invalid.");            
        }
        
        // 清理历史构建
        CleanupHistoryBuild(option);

        if (option.BuildType == BuildType.App)
        {
            BuildAppPipeline.Build(option);
        }
        else if (option.BuildType == BuildType.Res)
        {
            BuildResPipeline.Build(option);
        }
        else
        {
            Debug.LogFormat("Build Param Usage: \n{0}", option.ToString());
            throw new FrameworkException("[Build] BuildOption BuildType is invalid.");
        }
        // 保存平台版本配置文件
        platformConfig.Save(option.PlatformVerFilePath);
        
        // 复制版本文件到上传目录
        CopyVerFileToUpload(option);

        // 仅在 Edog 构建包装入口提供输出路径时，记录本次真实构建上下文。
        WritePerfBuildContext(option);
        
        // 构建完成
        Debug.Log("[Build] Final All Build Success.");
    }

    [Serializable]
    private sealed class PerfBuildContext
    {
        public string ProjectCode;
        public string ProjectPath;
        public string AbDir;
        public string RelatedVersion;
        public string ConfigureType;
        public string PlatformType;
        public string BuildType;
    }

    /// <summary>
    /// 将本次成功构建的真实工程路径、AssetBundle 路径和版本写给外层 Edog 包装脚本。
    /// 普通本地构建未设置 WJ_PERF_BUILD_CONTEXT 时不写文件。
    /// </summary>
    private static void WritePerfBuildContext(BuildOption option)
    {
        string outputPath = Environment.GetEnvironmentVariable("WJ_PERF_BUILD_CONTEXT");
        if (string.IsNullOrEmpty(outputPath))
        {
            Debug.Log("[BuildPipelineX.WritePerfBuildContext] skipped=True");
            return;
        }

        string outputDirectory = Path.GetDirectoryName(outputPath);
        if (string.IsNullOrEmpty(outputDirectory))
        {
            throw new FrameworkException("[BuildPipelineX.WritePerfBuildContext] Output directory is invalid.");
        }
        Directory.CreateDirectory(outputDirectory);

        PerfBuildContext context = new PerfBuildContext
        {
            ProjectCode = "WJ",
            ProjectPath = Path.GetFullPath(Path.Combine(Application.dataPath, "..")),
            AbDir = Path.GetFullPath(option.WorkingResBundlePath),
            RelatedVersion = option.PubConfig.GameVersion,
            ConfigureType = option.ConfigureType.ToString(),
            PlatformType = option.PlatformType.ToString(),
            BuildType = option.BuildType.ToString()
        };
        File.WriteAllText(outputPath, JsonUtility.ToJson(context, true), new UTF8Encoding(false));
        Debug.Log($"[BuildPipelineX.WritePerfBuildContext] version={context.RelatedVersion}, abDir={context.AbDir}, output={outputPath}");
    }

    /// <summary>
    /// channelType
    /// </summary>
    /// <param name="outPath"></param>
    /// <param name="buildType"></param>
    /// <param name="configureType"></param>
    /// <param name="platformType"></param>
    /// <param name="sdkType"></param>
    /// <param name="modeType"></param>
    public static void BuildApp(string outPath, BuildType buildType, ConfigureType configureType, PlatformType platformType, BuildModeType modeType, SDKType sdkType = SDKType.NO_SDK, bool enableProfiler = false)
    {
        if (!GameFrameworkEditor.EditorUtility.IsPlatformTypeTarget(platformType))
        {
            EditorUtility.DisplayDialog("提示", $"当前平台非{platformType},请先手动切换。", "确认");
            return;
        }
        
        BuildOption option = BuildOption.Create(outPath, buildType, configureType, platformType, modeType, sdkType, enableProfiler);
        SetBuildMode(option, BuildRunType.GUI);
        PlatformConfig platformConfig = UpdateBuildConfig(option);
        platformConfig.Save(option.PlatformVerFilePath);
        
        BuildAppPipeline.Build(option);
    }

    /// <summary>
    /// 构建应用（显式指定调试类型）。批处理/主动测试专用：允许显式传入 ProfilerType 以开启 Development 构建，
    /// 现有 BuildApp 的第 7 个参数实为 isCLIMode，无法开启 Development，故单独提供本重载。
    /// </summary>
    /// <param name="outPath">输出根路径</param>
    /// <param name="buildType">构建类型</param>
    /// <param name="configureType">配置类型</param>
    /// <param name="platformType">平台类型</param>
    /// <param name="modeType">模式类型</param>
    /// <param name="sdkType">SDK 类型</param>
    /// <param name="profilerType">调试类型；传 Development 时产出 Development 包</param>
    /// <param name="scriptingBackend">脚本后端；不传时保持 BuildOption 默认值（IL2CPP），正式包不受影响</param>
    public static void BuildAppWithProfiler(string outPath, BuildType buildType, ConfigureType configureType,
            PlatformType platformType, BuildModeType modeType, SDKType sdkType, BuildProfilerType profilerType,
            ScriptingImplementation? scriptingBackend = null)
    {
        BuildOption option = PrepareProfilerBuildOption(outPath, buildType, configureType, platformType,
            modeType, sdkType, profilerType, scriptingBackend);
        BuildAppPipeline.Build(option);
    }

    /// <summary>
    /// 创建时间：2026-10-26；创建人：Cyou。
    /// 功能：使用明确的平台构建器接入原 App/资源管线，并返回真实构建结果；默认入口不改变。
    /// 参数：原构建参数、明确后端和平台构建器工厂；工厂只用于本次调用，不注册全局替代项。
    /// </summary>
    public static AppBuilderResult BuildAppWithProfiler(string outPath, BuildType buildType, ConfigureType configureType,
        PlatformType platformType, BuildModeType modeType, SDKType sdkType, BuildProfilerType profilerType,
        ScriptingImplementation? scriptingBackend, Func<BuildOption, IAppBuilderPlatform> platformFactory)
    {
        if (platformFactory == null) throw new ArgumentNullException("platformFactory");
        BuildOption option = PrepareProfilerBuildOption(outPath, buildType, configureType, platformType,
            modeType, sdkType, profilerType, scriptingBackend);
        IAppBuilderPlatform platform = platformFactory(option);
        if (platform == null) throw new FrameworkException("[Build] explicit platform builder is missing.");
        return BuildAppPipeline.Build(option, platform);
    }

    /// <summary>
    /// 创建时间：2026-10-26；创建人：Cyou。
    /// 功能：共享原平台核验、构建参数、版本与宏准备，避免新旧入口复制两套流程。
    /// 参数：原构建参数和可选后端；返回原管线实际使用的 BuildOption，不执行构建。
    /// </summary>
    private static BuildOption PrepareProfilerBuildOption(string outPath, BuildType buildType, ConfigureType configureType,
        PlatformType platformType, BuildModeType modeType, SDKType sdkType, BuildProfilerType profilerType,
        ScriptingImplementation? scriptingBackend)
    {
        if (!GameFrameworkEditor.EditorUtility.IsPlatformTypeTarget(platformType))
        {
            // 批处理下不可弹窗阻塞，直接抛错由上层捕获退出。
            throw new FrameworkException($"[Build] current platform is not {platformType}, switch platform first.");
        }

        BuildOption option = BuildOption.Create(outPath, buildType, configureType, platformType, modeType, sdkType, false, false, "", profilerType);
        if (scriptingBackend.HasValue)
        {
            // 仅显式传入时才覆盖，默认路径仍是 IL2CPP，正式包零改动。
            option.ScriptingBackend = scriptingBackend.Value;
        }
        SetBuildMode(option, BuildRunType.CLI);
        PlatformConfig platformConfig = UpdateBuildConfig(option);
        platformConfig.Save(option.PlatformVerFilePath);

        return option;
    }

    /// <summary>
    /// 打开构建应用界面。
    /// </summary>
    public static void OpenBuildAppWindow()
    {
        AppWindow.ShowWindow();
    }

    /// <summary>
    /// 构建资源。
    /// </summary>
    /// <param name="outPath"></param>
    /// <param name="buildType"></param>
    /// <param name="configureType"></param>
    /// <param name="platformType"></param>
    /// <param name="modeType"></param>
    /// <param name="isIncrementalBuild"></param>
    public static void BuildRes(string outPath, BuildType buildType, ConfigureType configureType, PlatformType platformType, BuildModeType modeType, bool isIncrementalBuild = false)
    {
        if (!GameFrameworkEditor.EditorUtility.IsPlatformTypeTarget(platformType))
        {
            EditorUtility.DisplayDialog("提示", $"当前平台非{platformType}, 请先手动切换。", "确认");
            return;
        }
        
        BuildOption option = BuildOption.Create(outPath, buildType, configureType, platformType, modeType, SDKType.NO_SDK, false, isIncrementalBuild);
        SetBuildMode(option, BuildRunType.GUI);
        PlatformConfig platformConfig = UpdateBuildConfig(option);
        platformConfig.Save(option.PlatformVerFilePath);
        
        BuildResPipeline.Build(option);
    }

    /// <summary>
    /// 打开构建资源界面。
    /// </summary>
    public static void OpenBuildResWindow()
    {
        ResWindow.ShowWindow();
    }

    /// <summary>
    /// 设置构建模式。
    /// </summary>
    /// <param name="option"></param>
    /// <param name="runType"></param>
    private static void SetBuildMode(BuildOption option, BuildRunType runType)
    {
        if (option == null)
        {
            throw new FrameworkException("[Build] BuildOption is invalid.");
        }
        option.RunType = runType;
        Debug.LogFormat("[Build] SetBuildModeParam runType: {0}", runType);
    }
    
    /// <summary>
    /// 清理历史构建
    /// </summary>
    /// <param name="option"></param>
    private static void CleanupHistoryBuild(BuildOption option)
    {
        // 清理历史安装包临时目录
        string appTempDir = Path.Combine(option.TempRootPath, "App");
        if (Directory.Exists(appTempDir) && option.BuildType == BuildType.App)
        {
            FileUtil.DeleteFileOrDirectory(appTempDir);
        }
        
        // 清理历史上传文件
        if (Directory.Exists(option.WorkingUploadPath))
        {
            FileUtil.DeleteFileOrDirectory(option.WorkingUploadPath);
        }
        
        // 清理历史Package包，避免占用空间
        if (Directory.Exists(option.PackagePath))
        {
            BuildUtility.CleanupBuildFiles(option.PackagePath, null, 5);
        }
        
        // 清理历史安装包，这里忽略掉版本文件
        if (Directory.Exists(option.VersionInstallPath))
        {
            BuildUtility.CleanupBuildFiles(option.VersionInstallPath, null, 5);
        }
    }
    
    /// <summary>
    /// 设置平台参数。
    /// </summary>
    /// <param name="option"></param>
    private static PlatformConfig UpdateBuildConfig(BuildOption option)
    {
        // 平台参数设置，Ver.txt 打包自动生成
        PlatformConfig platformConfig;
        if (PlatformConfig.Exist(option.PlatformVerFilePath))
        {
            platformConfig = PlatformConfig.Load(option.PlatformVerFilePath);
            if (option.BuildType == BuildType.App && option.IsIncrementAppVersion)
            {
                platformConfig.LastAppVersion += 1;
                platformConfig.UpdateChannelFlagInfo(option.ChannelTypeName, option.PackageFlag, platformConfig.LastAppVersion);
            }
        }
        else
        {
            platformConfig = new PlatformConfig();
            platformConfig.LastAppVersion = option.PubConfig.AppVersion;
            platformConfig.UpdateChannelFlagInfo(option.ChannelTypeName, option.PackageFlag, platformConfig.LastAppVersion);
        }
        
        PlatformChannelFlagInfo channelFlagInfo = platformConfig.GetChannelFlagInfo(option.ChannelTypeName, option.PackageFlag);
        if (channelFlagInfo == null)
        {
            throw new FrameworkException("[Build] PlatformChannelFlagInfo is invalid.");
        }
        option.PubConfig.AppVersion = channelFlagInfo.LastAppVersion;

        Debug.LogFormat("[Build] final publish config: {0}", option.PubConfig.ToString());
        Debug.LogFormat("[Build] final platform config: {0}", platformConfig.ToString());
        
        // 设置版本参数，打包自动生成
        SetVerConfig(option);
        Debug.LogFormat("[Build] final ver config: {0}", option.VerConfig.ToString());
        
        // 设置定义符号
        SetDefineSymbol(option);
        Debug.LogFormat("[Build] final define symbol: {0}", PlayerSettings.GetScriptingDefineSymbolsForGroup(EditorUserBuildSettings.selectedBuildTargetGroup));
        
        return platformConfig;
    }
    
    /// <summary>
    /// 设置版本参数。
    /// </summary>
    /// <param name="option"></param>
    private static void SetVerConfig(BuildOption option)
    {
        if (!VerConfigEditor.Exist(option.VersionConfigPath))
        {
            option.VerConfig = new VerConfig();
            option.VerConfig.AppVersion = option.PubConfig.AppVersion;
            option.VerConfig.MajorVersion = option.PubConfig.MajorVersion;
            option.VerConfig.MinorVersion = option.PubConfig.MinorVersion;
            option.VerConfig.PatchVersion = option.PubConfig.PatchVersion;
        }
        else
        {
            option.VerConfig = VerConfigEditor.Load(option.VersionConfigPath);    
        }
        if (option.BuildType == BuildType.Res && option.ModeType == BuildModeType.Patch)
        {
            option.VerConfig.PatchVersion += 1;
        }
        
        VerConfigEditor.Save(option.VersionConfigPath, option.VerConfig);
    }
    
    /// <summary>
    /// 设置定义符号。
    /// </summary>
    /// <param name="option"></param>
    private static void SetDefineSymbol(BuildOption option)
    { 
        // 日志宏定义
        PluginUtility.AddTargetSDKSymbol("_LOG");
        string logDebugDef = "_LOG_DEBUG";
        if (option.IsLogger)
        {
            PluginUtility.AddTargetSDKSymbol(logDebugDef);
        }
        else
        {
            PluginUtility.RemoveTargetSDKSymbol(logDebugDef);
        }

        // 添加SDK类型宏定义
        PluginUtility.RemoveAllSDKSymbol();
        PluginUtility.AddTargetSDKSymbol($"CY_{option.SDKType}".ToUpper());

        // 添加新版 SDK 标识
        if (option.SDKType != SDKType.NO_SDK)
        {
            PluginUtility.AddTargetSDKSymbol("CY_OMNISDK");
        }
        
        // 设置Channel渠道类型标记
        foreach (ChannelType channelType in Enum.GetValues(typeof(ChannelType)))
        {
            PluginUtility.RemoveTargetSDKSymbol($"UNITY_CHANNEL_{channelType}".ToUpper());
            PluginUtility.RemoveTargetSDKSymbol("ENABLE_WX_PERF_FEATURE");
        }
        PluginUtility.AddTargetSDKSymbol($"UNITY_CHANNEL_{option.ChannelType}".ToUpper());
        if (option.ConfigureType != ConfigureType.Distribution)
        {
            PluginUtility.AddTargetSDKSymbol("ENABLE_WX_PERF_FEATURE");// 微信小游戏性能优化
        }
        
        // 其他全局宏定义
        
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
    }

    /// <summary>
    /// 格式化参数。
    /// </summary>
    /// <returns></returns>
    private static string ToFormatArgs()
    {
        string[] args = Environment.GetCommandLineArgs();
        StringBuilder sb = new StringBuilder();
        foreach (string arg in args)
        {
            sb.AppendLine(string.Format("\t{0}", arg));
        }

        return sb.ToString();
    }
    
    /// <summary>
    /// 仅仅打包指定平台脚本。
    /// </summary>
    /// <param name="buildTarget"></param>
    public static void BuildOnlyCSharp(BuildTarget buildTarget)
    {
        string[] scenes = GameFrameworkEditor.EditorUtility.GetEnabledScenes();
        // 只构建脚本，路径随意，但是不能为空
        string outputPath = buildTarget.ToString();

        BuildOptions options = BuildOptions.BuildScriptsOnly;

        BuildReport report = BuildPipeline.BuildPlayer(scenes, outputPath, buildTarget, options);
        if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
        {
            Debug.LogFormat("[Build] build {0} script success", buildTarget);
        }
        else
        {
            Debug.LogErrorFormat("[Build] build {0} script failure", buildTarget);
        }
    }
    
    /// <summary>
    /// 拷贝版本文件到上传目录。
    /// </summary>
    /// <param name="option"></param>
    private static void CopyVerFileToUpload(BuildOption option)
    {
        // 拷贝版本文件
        string verFilePath = option.VersionConfigPath;
        if (File.Exists(verFilePath))
        {
            string uploadVerFilePath = Path.Combine(option.WorkingUploadPath, Path.GetFileName(verFilePath));
            if (File.Exists(uploadVerFilePath))
            {
                File.Delete(uploadVerFilePath);
            }
            FileUtil.CopyFileOrDirectory(verFilePath, uploadVerFilePath);    
        }
        else
        {
            Debug.LogErrorFormat("[Build] app_channelName_appVersion_ver.json {0} not exist", verFilePath);
        }

        // 拷贝平台版本文件
        string platformVerFilePath = option.PlatformVerFilePath;
        if (File.Exists(platformVerFilePath))
        {
            string uploadPlatformVerFilePath = Path.Combine(option.WorkingUploadPath, Path.GetFileName(platformVerFilePath));
            if (File.Exists(uploadPlatformVerFilePath))
            {
                File.Delete(uploadPlatformVerFilePath);
            }
            FileUtil.CopyFileOrDirectory(platformVerFilePath, uploadPlatformVerFilePath);
        }
        else
        {
            Debug.LogErrorFormat("[Build] ver.txt file {0} not exist", platformVerFilePath);
        }
    }
}
