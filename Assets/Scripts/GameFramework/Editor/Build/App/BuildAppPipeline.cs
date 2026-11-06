// ========================================================================
// Copyright (c) 2025 ChangYou, All rights reserved.
// http://www.changyou.com/
// 
// Filename:    BuildAppPipeline.cs
// Time:        2021-12-29 14:33:20
// Author:      xiangjinbao
// Email:       xiangjinbao@cyou-inc.com
// Version:     v1.0.0
// Description: BuildAppPipeline
// ========================================================================

using GameFrameworkEditor;

public class BuildAppPipeline
{
    /// <summary>
    /// 通用的构建应用接口。
    /// </summary>
    /// <param name="option">构架选项参数。</param>
    public static void Build(BuildOption option)
    {
        AppBuilder.Build(option);
    }

    /// <summary>
    /// 创建时间：2026-10-26；创建人：Cyou。
    /// 功能：将明确的平台构建器接到原 App/资源生命周期并返回真实结果，不改默认工厂。
    /// 参数：option 为原构建参数，platform 为本次调用独享的平台构建器。
    /// </summary>
    public static AppBuilderResult Build(BuildOption option, IAppBuilderPlatform platform)
    {
        return AppBuilder.Build(option, platform);
    }
}
