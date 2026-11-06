// ========================================================================
// Copyright (c) 2022 ChangYou, All rights reserved.
// http://www.changyou.com/
//
// Filename:    ResBuilderScript.cs
// Time:        2022-05-16 10:53:29
// Author:      xiangjinbao
// Email:       xiangjinbao@cyou-inc.com
// Version:     V1.0.0
// Description: ResBuilderScript
// ========================================================================

using System;
using System.Diagnostics;
using System.IO;
using GameFramework.Base;
using HybridCLR.Editor;
using HybridCLR.Editor.Commands;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;

#if UNITY_EDITOR
using Core_Editor;
#endif

namespace GameFrameworkEditor
{
    /// <summary>
    /// 代码打包。
    /// </summary>
    public class ResBuilderScript : ResBuilderGeneral
    {
        public static readonly byte[] ENCRYPTION_CODE = new byte[] { 0x05, 0x62, 0x83 };

        [MenuItem("Game Tools/打包/Build/Build-Code", false, ((int)GameTools_BuildTools.BuildCodeMenu))]
        private static void BuildCodeMenu()
        {
            BuildOption option = new BuildOption();
            option.ConfigureType = ConfigureType.Development;
            option.PlatformType = EditorUtility.GetCurrentBuildPlatformType();
            Start(option);
        }

        /// <summary>
        /// 对完打Lua接口。
        /// </summary>
        /// <param name="option"></param>
        public static void Start(BuildOption option)
        {
            ResBuilderScript builderScript = new ResBuilderScript(null);
            builderScript.Option = option;
            builderScript.Build();
        }

        /// <summary>
        /// 构建函数。
        /// </summary>
        /// <param name="builder"></param>
        public ResBuilderScript(ResBuilder builder) : base(builder)
        {
        }

        protected override bool OnAssetBuild()
        {
            //// windows下不执行Hybridclr,因为windows有单独的长线更新器，并且这里我还要把HybridCLR Settings的Enable设置成false
            //if (Option.PlatformType == PlatformType.Window)
            //{
            //    HybridCLRSettings.Instance.enable = false;
            //    HybridCLRSettings.Save();
            //    return true;
            //}

            //HybridCLRSettings.Instance.enable = true;
            //HybridCLRSettings.Save();

            // HybridCLR 是 IL2CPP 专用方案（AOT 补充元数据 + AOT 泛型桥接）。Mono 主动测试包下
            // 托管程序集走原生 Assembly.Load，既不需要也不应执行 AOT 桥接生成，否则会基于不存在的
            // IL2CPP 裁剪产物报错。此处按 ScriptingBackend 精确区分，不依赖宏。
            bool isIl2CppBackend = Option.ScriptingBackend == ScriptingImplementation.IL2CPP;

            Stopwatch watch = new Stopwatch();
            watch.Start();
            // 必须保证 StartAssetEditing/StopAssetEditing 成对：中途抛异常若漏掉 Stop，
            // 资源库会一直停在编辑状态，Unity 报 "asset database editing is started" 且拒绝域重载。
            AssetDatabase.StartAssetEditing();
            try
            {
                if (isIl2CppBackend)
                {
                    // HybridCLR 一键打包执行的生成命令(LinkXml、AotDlls、il2CppDef等)
                    PrebuildCommand.GenerateAll();
                }
                else
                {
                    // Mono 不走 GenerateAll，但热更 DLL 仍需产出：GenerateAll 内部会调用
                    // CompileDllCommand.CompileDll，跳过它就得在此显式补上，否则
                    // Code/CyStarRoad.bytes 会是过期或缺失的。
                    Debug.Log("[Res] ScriptingBackend 为 Mono2x，跳过 HybridCLR PrebuildCommand.GenerateAll。");
                    CompileDllCommand.CompileDllActiveBuildTarget();
                }

                string dstDir = Option.CodeTempPath;
                if (Directory.Exists(dstDir))
                {
                    FileUtil.DeleteFileOrDirectory(dstDir);
                }

                EditorUtility.DeleteEmptyDirectories(dstDir);

                // 目标目录必须无条件建好：原先唯一的 Directory.CreateDirectory 在
                // CopyAOTAssemblies 内部，Mono 后端跳过该方法后 CopyHotUpdateAssemblies
                // 的 File.Copy 会直接抛 DirectoryNotFoundException。
                if (!Directory.Exists(dstDir))
                {
                    Directory.CreateDirectory(dstDir);
                }

                if (isIl2CppBackend)
                {
                    CopyAOTAssemblies(dstDir);
                }
                CopyHotUpdateAssemblies(dstDir);
                AssetDatabase.Refresh();

                // 适配配置拷贝
                BuildTargetGroup buildTarget = EditorUtility.GetBuildTargetGroupByType(Option.PlatformType);
                CopyGameConfigJson(buildTarget);
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
                AssetDatabase.Refresh();
            }
            watch.Stop();

            Debug.Log("[Res] build script success, time = " + watch.Elapsed.TotalSeconds);

            return true;
        }

        private static void CopyAOTAssemblies(string dstPath)
        {
            var target = EditorUserBuildSettings.activeBuildTarget;
            string aotAssembliesSrcDir = SettingsUtil.GetAssembliesPostIl2CppStripDir(target);

            if (!Directory.Exists(dstPath))
            {
                Directory.CreateDirectory(dstPath);
            }

            DirectoryInfo directory = new DirectoryInfo(dstPath);
            foreach (FileInfo file in directory.GetFiles())
            {
                file.Delete();
            }

            foreach (string dllName in SettingsUtil.AOTAssemblyNames)
            {
                string srcDllPath = $"{aotAssembliesSrcDir}/{dllName}.dll";
                if (!File.Exists(srcDllPath))
                {
                    Debug.LogError($"ab中添加AOT补充元数据dll:{srcDllPath} 时发生错误,文件不存在。裁剪后的AOT dll在BuildPlayer时才能生成，因此需要你先构建一次游戏App后再打包。");
                    continue;
                }

                string dllBytesPath = $"{dstPath}/{dllName}.bytes";
                File.Copy(srcDllPath, dllBytesPath, true);
                Debug.Log($"[CopyAOTAssembliesToStreamingAssets] copy AOT dll {srcDllPath} -> {dllBytesPath}");
            }
        }

        /// <summary>
        /// 处理dll
        /// </summary>
        private static void CopyHotUpdateAssemblies(string dstPath)
        {
            BuildTarget target = EditorUserBuildSettings.activeBuildTarget;
            string hotfixDllSrcDir = SettingsUtil.GetHotUpdateDllsOutputDirByTarget(target);
            foreach (var dll in SettingsUtil.HotUpdateAssemblyFilesExcludePreserved)
            {
                string dllPath = $"{hotfixDllSrcDir}/{dll}";
                string dllBytesPath = $"{dstPath}/{Path.GetFileNameWithoutExtension(dll)}.bytes";
                File.Copy(dllPath, dllBytesPath, true);
                Debug.Log($"[CopyHotUpdateAssembliesToStreamingAssets] copy hotfix dll {dllPath} -> {dllBytesPath}");
            }
        }

        /// <summary>
        /// 拷贝游戏配置。
        /// </summary>
        /// <param name="target"></param>
        private static void CopyGameConfigJson(BuildTargetGroup target)
        {
            string aotAssembliesDstDir = Application.dataPath + "/GameResource/Config/";
            if (!Directory.Exists(aotAssembliesDstDir))
            {
                Directory.CreateDirectory(aotAssembliesDstDir);
            }

            // DirectoryInfo directory = new DirectoryInfo(aotAssembliesDstDir);
            // foreach (FileInfo file in directory.GetFiles())
            // {
            //     file.Delete();
            // }

            string platformResStr = "Android";
            if (target == BuildTargetGroup.iOS)
            {
                platformResStr = "IOS";
            }
            else if (target == BuildTargetGroup.WebGL)
            {
                platformResStr = "WebGL";
            }
#if CYENGINE_2_0_0
            else if (target == BuildTargetGroup.OpenHarmony)
            {
                platformResStr = "OpenHarmony";
            }
#endif
            string yuanPath = Application.dataPath + "/PlatformRes/" + platformResStr + "/GameCofig";
            DirectoryInfo dir = new DirectoryInfo(yuanPath);
            FileInfo[] fil = dir.GetFiles();
            foreach (FileInfo f in fil)
            {
                // 如果是 meta 文件, 且存在不要拷贝, 否则会导致 guid 冲突, 自编译引擎会卡死
                if (f.Extension.Equals(".meta", StringComparison.OrdinalIgnoreCase))
                {
                    if (File.Exists(aotAssembliesDstDir + f.Name))
                    {
                        continue;
                    }
                }
                File.Copy(f.FullName, aotAssembliesDstDir + f.Name, true);
            }

            AssetDatabase.Refresh();
        }

        public override bool OnPostBuild()
        {
            AssetDatabase.StartAssetEditing();
            {
                // if (Directory.Exists(Option.CodeTempPath))
                // {
                // 	FileUtil.DeleteFileOrDirectory(Option.CodeTempPath);
                // }
            }
            AssetDatabase.StopAssetEditing();
            AssetDatabase.Refresh();
            return base.OnPostBuild();
        }
    }
}