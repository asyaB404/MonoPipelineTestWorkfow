// ========================================================================
// Copyright (c) 2022 ChangYou, All rights reserved.
// http://www.changyou.com/
// 
// Filename:    AppBuilder.cs
// Time:        2022-03-01 13:14:25
// Author:      xiangjinbao
// Email:       xiangjinbao@cyou-inc.com
// Version:     v1.0.0
// Description: AppBuilder
// ========================================================================

using System;
using System.IO;
using GameFramework.Base;
using UnityEditor;
using UnityEngine;

namespace GameFrameworkEditor
{
    public class AppBuilder : BuilderBase
    {
        private ChannelVO m_CurChannelVo;

        private AppBuilderResult m_Result;
        private readonly IAppBuilderPlatform m_Builder;

        public ChannelVO CurChannelVO
        {
            get => m_CurChannelVo;
            private set => m_CurChannelVo = value ?? throw new FrameworkException("Channel Info is Invalid.");
        }

        public IAppBuilderPlatform Builder => m_Builder;

        /// <summary>
        /// 构造函数
        /// </summary>
        /// <param name="option"></param>
        /// <param name="builder"></param>
        internal AppBuilder(BuildOption option, IAppBuilderPlatform builder)
        {
            // 版本参数
            m_Option = option;
            Debug.Log($"[Build] build option param: {m_Option}");

            // 应用构建器
            m_Builder = builder;
        }

        /// <summary>
        /// 构建版本入口。
        /// </summary>
        /// <param name="option"></param>
        public static void Build(BuildOption option)
        {
            if (option.ChannelType == ChannelType.Invalid)
            {
                return;
            }

            IAppBuilderPlatform builder = AppBuilderFactory.GetBuilder(option);
            Debug.Log($"[Build] IAppBuilderPlatform: {builder.GetType().FullName}");
            new AppBuilder(option, builder).Build();
        }

        /// <summary>
        /// 创建时间：2026-10-26；创建人：Cyou。
        /// 功能：使用本次明确的平台构建器执行原完整 App/资源生命周期，返回实际构建结果。
        /// 参数：option 为原构建参数，platform 为本次平台实例；不注册或修改全局构建器工厂。
        /// </summary>
        public static AppBuilderResult Build(BuildOption option, IAppBuilderPlatform platform)
        {
            if (option == null) throw new ArgumentNullException("option");
            if (platform == null) throw new ArgumentNullException("platform");
            if (option.ChannelType == ChannelType.Invalid)
                throw new FrameworkException("[Build] explicit app channel is invalid.");
            AppBuilder app = new AppBuilder(option, platform);
            app.Build();
            AppBuilderResult result = app.m_Result;
            if (result == null || !result.IsSuccess || result.Report == null)
                throw new FrameworkException("[Build] explicit app builder did not return a successful report.");
            return result;
        }

        /// <summary>
        /// 构建前事件。
        /// </summary>
        protected override bool OnPreBuild()
        {
            if (!CheckedValid())
            {
                throw new FrameworkException("[App] BuildApp param is invalid.");
            }

            // 设置性能测试平台
            SetProfilerPlatform();

            // 初始化渠道
            CurChannelVO = Option.PubConfig.GetChannelByType(Option.PlatformType, Option.ChannelType);

            // 清空临时目录
            if (Directory.Exists(Option.VersionInstallTempPath))
            {
                FileUtil.DeleteFileOrDirectory(Option.VersionInstallTempPath);
            }
            Directory.CreateDirectory(Option.VersionInstallTempPath);

            // 设置构建信息
            PlayerSettings.bundleVersion = Option.PubConfig.GameVersion;
            PlayerSettings.productName = Option.PubConfig.ProductName;
            PlayerSettings.applicationIdentifier = CurChannelVO.BundleId;

            // 是否构建调试包
            EditorUserBuildSettings.development = Option.IsProfiler;
            EditorUserBuildSettings.connectProfiler = Option.IsConnectProfiler;
            EditorUserBuildSettings.allowDebugging = Option.IsProfiler;

            BuildUtility.UpdateAppConfig(Option);

            Builder.OnPreBuild();
            BuildAppRes();

            return true;
        }

        /// <summary>
        /// 构建事件。
        /// </summary>
        protected override bool OnBuild()
        {
            try
            {
                m_Result = Builder.OnBuild();
                if (m_Result.IsSuccess)
                {
                    Debug.Log("[Build] build success.");
                }
                else
                {
                    throw new FrameworkException("[Build] build app failure.");
                }
            }
            catch (Exception e)
            {
                Debug.LogError(e.StackTrace);
                UnityEditor.EditorUtility.ClearProgressBar();
                throw new FrameworkException(e.Message);
            }
            return true;
        }

        /// <summary>
        /// 构建后处理事件。
        /// </summary>
        protected override bool OnPostBuild()
        {
            if (!CheckedValid())
            {
                throw new FrameworkException("[App] BuildApp param is invalid.");
            }
            m_Builder.OnPostBuild();

            Debug.Log($"Build app success, appConfig: {Option.AppConfig}");
            Debug.Log($"Build app success, verConfig: {Option.VerConfig}");

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            return true;
        }

        /// <summary>
        /// 构建应用资源。
        /// </summary>
        private void BuildAppRes()
        {
            BuildResPipeline.Build(Option);
        }

        /// <summary>
        /// 检查构建参数是否有效。
        /// </summary>
        private void SetProfilerPlatform()
        {
            if (!Option.IsProfiler || Option.PlatformType == PlatformType.WebGL)
            {
                var perfPlatformPath = "Packages/com.cyou.perfplatform";
                if (Directory.Exists(perfPlatformPath))
                {
                    FileUtil.DeleteFileOrDirectory(perfPlatformPath);
                }
            }
        }

        /// <summary>
        /// 检查是否有效。
        /// </summary>
        /// <returns></returns>
        public bool CheckedValid()
        {
            string error = BuildUtility.CheckedValid(Option, Option.VerConfig);
            if (string.IsNullOrEmpty(error))
            {
                return true;
            }

            throw new FrameworkException(error);
        }
    }
}
