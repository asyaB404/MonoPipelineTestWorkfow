namespace Core_Editor
{
    /// 菜单排序和分组规则：
    /// 排序：平级菜单排序按照Priority优先级来进行排序，如果有子菜单，又没有设置该菜单的Priority优先级数值；则考虑子菜单里边最小优先级的数值
    /// 分组（分割线）：平级菜单Priority优先级>=10,则会生成分割线。同样如果没有设置改菜单的Priority优先级数值；则考虑子菜单里边最大优先级数值

    #region Game Tools菜单

    /// <summary>
    /// Game Tools/导表和协议
    /// </summary>
    public enum GameTools_TableProto
    {
        Min = 0,

        Proto2Kratos,                           // Game Tools/导表和协议/微服务相关/Proto2Kratos
        ExportProtoAll,                         // Game Tools/导表和协议/导出协议Proto
        ExportTableClient,                      // Game Tools/导表和协议/导出客户端表
        ExportTableServer,                      // Game Tools/导表和协议/导出服务器表
        ExportTableAll,                         // Game Tools/导表和协议/导出客户端+服务器表

        Max,
    }

    /// <summary>
    /// Game Tools/UI制作
    /// </summary>
    public enum GameTools_UITools
    {
        Min = ((int)GameTools_TableProto.Min) + 1,

        OpenGameClientSettingsWindow,           // Game Tools/UI制作/编辑UI

        #region UI_Logic相关
        ProcessAllLogicFile,                    // Game Tools/UI制作/UI_Logic相关/拆分Logic代码和绑定代码
        DeleteAllNullDependLogic,               // Game Tools/UI制作/UI_Logic相关/无用的UI_Logic脚本删除
        CheckNullUI_LogicWithPrefab,            // Game Tools/UI制作/UI_Logic相关/检测UIPrefab上挂载的空UI_Logic
        CheckMutUIBinderWithPrefab,             // Game Tools/UI制作/UI_Logic相关/检测是否有一个对象挂载多个uibinder的情况
        CheckAllUIPrefabLogic,                  // Game Tools/UI制作/UI_Logic相关/输出UI_Logic的引用计数和引用字段为空的数据

        #endregion

        #region 修改图片
        // 以下工具已迁移到 Game Tools/优化工具 下：
        // UI_PrefabUDSpriteCheck         → 已移除
        // UI_PrefabEmptySpriteCheck      → 已移除
        // UI_PrefabEmptyOrUDSpriteReplace → 已移除
        // UI_ReplaceGameImageWithLanguageCN → 已移动到 GameTools_OptimizeTools

        #endregion

        #region 修改文本
        UI_ReplaceGameTextWithTable,            // Game Tools/UI制作/修改文本/GameText和字典号相关/替换GameText的内容为字典表配置的内容
        UI_TextChange,                          // Game Tools/UI制作/修改文本/GameText和字典号相关/根据UIPrefab的Text的文字内容写入字典号
        UI_TextCheck,                           // Game Tools/UI制作/修改文本/GameText和字典号相关/统计UIPrefab引用的Text的文字内容
        ShowGameTextLocalizationTool,           // Game Tools/UI制作/修改文本/修复 GameText 多语言 Key
        ShowFontSizeChangeEditorWindow,         // Game Tools/UI制作/修改文本/修改字号界面
        AddTextSize,                            // Game Tools/UI制作/修改文本/字号+1
        DecTextSize,                            // Game Tools/UI制作/修改文本/字号-1
        UI_ReplaceGameTextByLanguageCN,         // Game Tools/UI制作/修改文本/替换GameText的内容为字典表中文配置
        FindSystemFontDepends,                  // Game Tools/UI制作/修改文本/查找系统字体引用
        CheckTableDicExist,                     // Game Tools/UI制作/修改文本/检查字典不存在表里面
        ClearGameTextTxt,                       // Game Tools/UI制作/修改文本/清空GameText上的默认文本
        FindFontBySize,                         // Game Tools/UI制作/修改文本/统计所有文本的字号
        setGameButtonClickInternal,             // Game Tools/UI制作/修改文本/设置GameButon点击间隔
        TextVerticalOverflow,                   // Game Tools/UI制作/修改文本/设置VerticalOverflow为Overflow
        GameTextToLanguageTxt,                  // Game Tools/UI制作/修改文本/设置文本为字典的内容
        ScanGameTextAllBindLanguageInfo,        // Game Tools/UI制作/修改文本/（选中）扫描预制界面里所有绑定的字典号信息

        #endregion

        OpenSettingEditorWindow,                // Game Tools/UI制作/编辑器配置界面

        Max = 70,
    }

    /// <summary>
    /// 打包
    /// </summary>
    public enum GameTools_BuildTools
    {
        Min = ((int)GameTools_UITools.Min) + 1,

        #region Build

        #region Build-App
        BuildAppAndroid,         // Game Tools/打包/Build/Build-App/Android-非SDK包
        BuildAppAndroidCN,       // Game Tools/打包/Build/Build-App/Android-SDK国内
        BuildAppAndroidHW,       // Game Tools/打包/Build/Build-App/Android-SDK海外

        BuildAppiOS,             // Game Tools/打包/Build/Build-App/iOS-非SDK包
        BuildAppiOSCN,           // Game Tools/打包/Build/Build-App/iOS-SDK国内
        BuildAppiOSHW,           // Game Tools/打包/Build/Build-App/iOS-SDK海外

        BuildAppMacOS,           // Game Tools/打包/Build/Build-App/MacOS-非SDK包
        BuildAppWindow,          // Game Tools/打包/Build/Build-App/Window-非SDK包
        BuildAppWindowTestAgent, // Game Tools/打包/Build/Build-App/Window-灰盒测试包(PC_TEST_AGENT)
        BuildAppHarmony,         // Game Tools/打包/Build/Build-App/Harmony-非SDK包

        BuildAppWebGL,           // Game Tools/打包/Build/Build-App/WebGL-网页版

        BuildAppWebGLWeiChatCN,  // Game Tools/打包/Build/Build-App/WebGL-微信CN小游戏
        BuildAppWebGLWeiChatHW,  // Game Tools/打包/Build/Build-App/WebGL-微信HW小游戏

        BuildAppWebGLDouYinCN,   // Game Tools/打包/Build/Build-App/WebGL-抖音CN小游戏
        BuildAppWebGLDouYinHW,   // Game Tools/打包/Build/Build-App/WebGL-抖音HW小游戏

        BuildAppWebGLFacebookHW, // Game Tools/打包/Build/Build-App/WebGL-FBHW小游戏

        BuildAppGUI,             // Game Tools/打包/Build/Build-App/GUI(All)

        #endregion

        #region Build-CSharp
        BuildWindowScript,      // Game Tools/打包/Build/Build-CSharp/CompileScript-Window
        BuildMacOSXScript,      // Game Tools/打包/Build/Build-CSharp/CompileScript-MacOSX
        BuildIOSScript,         // Game Tools/打包/Build/Build-CSharp/CompileScript-iOS
        BuildAndroidScript,     // Game Tools/打包/Build/Build-CSharp/CompileScript-Android
        BuildWebGLScript,       // Game Tools/打包/Build/Build-CSharp/CompileScript-WebGL
        BuildLinuxScript,       // Game Tools/打包/Build/Build-CSharp/CompileScript-Linux
        BuildHarmonyOSScript,   // Game Tools/打包/Build/Build-CSharp/CompileScript-HarmonyOS

        #endregion

        #region Build-Res
        BuildResGUI,            // Game Tools/打包/Build/Build-Res/GUI(All)
        BuildResAndroid,        // Game Tools/打包/Build/Build-Res/Android
        BuildResiOS,            // Game Tools/打包/Build/Build-Res/iOS
        BuildResMacOS,          // Game Tools/打包/Build/Build-Res/MacOS
        BuildWindowRes,         // Game Tools/打包/Build/Build-Res/Window
        BuildHarmonyRes,        // Game Tools/打包/Build/Build-Res/Harmony
        BuildLinuxRes,          // Game Tools/打包/Build/Build-Res/Linux
        BuildWebGLRes,          // Game Tools/打包/Build/Build-Res/WebGL
        BuildResAndroidPatch,   // Game Tools/打包/Build/Build-Res/Android(Patch)
        BuildResiOSPatch,       // Game Tools/打包/Build/Build-Res/iOS(Patch)
        BuildResMacOSPatch,     // Game Tools/打包/Build/Build-Res/MacOS(Patch)
        BuildResWindowPatch,    // Game Tools/打包/Build/Build-Res/Window(Patch)
        BuildResHarmonyPatch,   // Game Tools/打包/Build/Build-Res/Harmony(Patch)
        BuildResWebGLPatch,     // Game Tools/打包/Build/Build-Res/WebGL(Patch)
        BuildResLinuxPatch,     // Game Tools/打包/Build/Build-Res/Linux(Patch)

        #endregion

        #region Build-SDK
        BuildAppAndroidClearSDK,        // Game Tools/打包/Build/Build-SDK/清理AllSDK
        BuildAppInterfaceSDKCN,         // Game Tools/打包/Build/Build-SDK/拷贝应用层SDK国内-接口层
        BuildAppInterfaceSDKHW,         // Game Tools/打包/Build/Build-SDK/拷贝应用层SDK海外-接口层
        BuildMiniInterfaceSDKCN,        // Game Tools/打包/Build/Build-SDK/拷贝小程序SDK国内-接口层
        BuildMiniInterfaceSDKHW,        // Game Tools/打包/Build/Build-SDK/拷贝小程序SDK海外-接口层
        BuildAppAndroidCNCopySDK,       // Game Tools/打包/Build/Build-SDK/Android-拷贝CNSDK
        BuildAppAndroidHWCopySDK,       // Game Tools/打包/Build/Build-SDK/Android-拷贝HWSDK
        BuildAppiOSCNCopySDK,           // Game Tools/打包/Build/Build-SDK/iOS-拷贝CNSDK
        BuildAppiOSHWCopySDK,           // Game Tools/打包/Build/Build-SDK/iOS-拷贝HWSDK
        BuildAppWebGLWeiChatCNCopySDK,  // Game Tools/打包/Build/Build-SDK/WebGL-拷贝微信CNSDK
        BuildAppWebGLWeiChatHWCopySDK,  // Game Tools/打包/Build/Build-SDK/WebGL-拷贝微信HWSDK
        BuildAppWebGLDouYinCopySDK,     // Game Tools/打包/Build/Build-SDK/WebGL-拷贝抖音CNSDK
        BuildAppWebGLDouYinHWCopySDK,   // Game Tools/打包/Build/Build-SDK/WebGL-拷贝抖音HWSDK
        BuildAppWebGLFacebookHWCopySDK, // Game Tools/打包/Build/Build-SDK/WebGL-拷贝FBHWSDK

        #endregion

        #region Build-Code
        BuildCodeMenu,           // Game Tools/打包/Build/Build-Code

        #endregion

        #endregion

        #region 打热更资源包
        PackHotfixRes_Android,   // Game Tools/打包/打热更资源包/打热更资源包-Android
        PackHotfixRes_IOS,       // Game Tools/打包/打热更资源包/打热更资源包-IOS
        PackHotfixRes_WebGL,     // Game Tools/打包/打热更资源包/打热更资源包-WebGL
        OpenGenerateMD5Editor,   // Game Tools/打包/打热更资源包/测试工具：生成文件MD5

        #endregion

        #region 资源检查
        CheckBundle1,            // Game Tools/打包/资源检查/检查Bundle
        CheckBundle2,            // Game Tools/打包/资源检查/检查Bundle(并设置)
        CheckBundle1Selected,    // Game Tools/打包/资源检查/检查Bundle-选中
        CheckBundle2Selected,    // Game Tools/打包/资源检查/检查Bundle-选中(并设置)
        CheckFontSize,           // Game Tools/打包/资源检查/检查字号大小【耗时20秒】
        CheckMaterialAll,        // Game Tools/打包/资源检查/检查字号大小【耗时20秒】
        CheckAllMaterial,        // Game Tools/打包/资源检查/检查材质
        CheckMaterialSelected,   // Game Tools/打包/资源检查/检查材质-选中
        CheckTextureAll,         // Game Tools/打包/资源检查/检查材质-选中
        CheckTextureSelected,    // Game Tools/打包/资源检查/检查贴图-选中目录
        FindUnusedTable,         // Game Tools/打包/资源检查/筛查无用的Table数据表脚本

        #endregion

        OpenSettingWindow,                  // Game Tools/打包/Build Config
        CopyAllAsmdefDllsWithDependencies,  // Game Tools/打包/程序集编译/Compilation GameFramework Library
        UpdateResEditorTesterHelper,        // Game Tools/打包/Editor模式资源更新测试

        Max,

        // 创建日期：2026-10-26；作者：Cyou。新 Mono/Pipeline 菜单共享原测试构建分组，保留全部旧枚举值。
        BuildAppWindowMonoPipeline = BuildAppWindowTestAgent,
    }

    /// <summary>
    /// 资源文件整合
    /// </summary>
    public enum GameTools_ResFileOperate
    {
        Min = ((int)GameTools_BuildTools.Max) + 1,

        OpenGUIDFindAssetEditor,                // Game Tools/资源文件整合/GUID文件查找工具

        #region Shader
        SetShaderBundleName,                    // Game Tools/资源文件整合/Shader/Shader收集
        OpenShaderVariantsStripperWindow,       // Game Tools/资源文件整合/Shader/Shader变体剔除工具/OpenStripperWindow
        OpenShaderVariantCollectionToolsWindow, // Game Tools/资源文件整合/Shader/Shader变体收集工具/OpenWindow

        #endregion

        #region Unity系统目录跳转
        OpenFolderTemporaryCachePath,           // Game Tools/资源文件整合/Unity系统目录跳转/TemporaryCachePath
        OpenFolderPersistentDataPath,           // Game Tools/资源文件整合/Unity系统目录跳转/PersistentDataPath
        OpenFolderStreamingAssetsPath,          // Game Tools/资源文件整合/Unity系统目录跳转/StreamingAssets
        OpenFolderDataPath,                     // Game Tools/资源文件整合/Unity系统目录跳转/DataPath

        #endregion

        #region 字体库相关
        OpenFontBitmapExporter,                 // Game Tools/资源文件整合/字体库相关/BitmapFontExporter
        OpenFontReplacerEditor,                 // Game Tools/资源文件整合/字体库相关/字体替换

        #endregion

        #region 特效相关
        DeleteParticleDepResource,              // Game Tools/资源文件整合/特效相关/特效无用依赖资源删除
        ParticleTextureDepPrefab,               // Game Tools/资源文件整合/特效相关/特效纹理所依赖的Prefab统计
        DeleteParticleLoader,                   // Game Tools/资源文件整合/特效相关/删除Prefab上无用的特效加载器
        InvideParticleSystemDelete,             // Game Tools/资源文件整合/特效相关/特效无用的系统材质删除
        ClearMatProperties,                     // Game Tools/资源文件整合/特效相关/包含无用纹理采样的材质处理
        OnOpenParticleReadWirte,                // Game Tools/资源文件整合/特效相关/批量开启shape粒子的纹理读写开关

        #endregion

        AssetTagSettingsEditor,                 // Game Tools/资源文件整合/资源打标签/Tag Settings
        AssetTagWindow,                         // Game Tools/资源文件整合/资源打标签/TagInspector

        Max,
    }

    /// <summary>
    /// 其他工具
    /// </summary>
    public enum GameTools_OtherTools
    {
        Min = ((int)GameTools_ResFileOperate.Min) + 1,

        AnimaionClipCheck,                      // Game Tools/其他工具/动画文件检测
        ExportAssetsTextTable,                  // Game Tools/其他工具/本地化文档资源生成/Asset表格资源导出（中->英
        ExportTextTable,                        // Game Tools/其他工具/本地化文档资源生成/文字表格导出（中->英
        ExportAudioTextTable,                   // Game Tools/其他工具/本地化文档资源生成/音频表格资源导出（中->英
        MixedDataToDLL,                         // Game Tools/其他工具/混淆DLL/MixedDataToDLL
        OpenTranslateEditor,                    // Game Tools/其他工具/翻译工具
        OpenRedDotVisualizer,                   // Game Tools/其他工具/红点可视化工具

        Max
    }

    /// <summary>
    /// 优化工具
    /// </summary>
    public enum GameTools_OptimizeTools
    {
        Min = ((int)GameTools_OtherTools.Min) + 1,

        #region 修改图片/图片优化
        UI_ReplaceGameImageWithLanguageCN,      // Game Tools/优化工具/替换GameImage的内容为资源表中文配置
        ReplaceNoneOrUDWithNoneImage1,          // Game Tools/优化工具/替换预制体里None或UD_开头的GameImage为US_Frame_NoneImage1
        ReplaceButtonHitAreaWithNoneImage1,     // Game Tools/优化工具/替换预制体里按钮点击区域图片为US_Frame_NoneImage1

        #endregion

        #region Transform优化
        RoundTransformTo1Decimal,               // Game Tools/优化工具/预制体Transform浮点数保留一位小数

        #endregion

        #region Overdraw优化相关
        OutlinedShadowFind,                     // Game Tools/优化工具/Overdraw优化相关/UIText的Outlined和Shadow查找
        FillCenterSet,                          // Game Tools/优化工具/Overdraw优化相关/九宫格纹理FillCenter设置
        PrefabBinderNoUDImg,                    // Game Tools/优化工具/Overdraw优化相关/所有Prefab的NoneImage1的OverDraw处理
        SetRawGameImageReferenceScript,         // Game Tools/优化工具/Overdraw优化相关/设置预设RawImage的texture为null

        #endregion

        AllUICreateSpriteAtlas,                 // Game Tools/优化工具/所有UI的图集优化
        DynamicImgCreateSpriteAtlas,            // Game Tools/优化工具/动态纹理图集优化
        FindScriptChineseTxt,                   // Game Tools/优化工具/查找代码里面的中文
        FindResourceChineseName,                // Game Tools/优化工具/查找资源路径命名中的中文
        FindFunctionValueParam,                 // Game Tools/优化工具/查找函数声明中包含值类型的形参

        Max,
    }

    /// <summary>
    /// 特殊工具
    /// </summary>
    public enum GameTools_SpecialTools
    {
        Min = GameTools_OptimizeTools.Min + 1,

        GameLanguageSystemReplace1,             // Game Tools/特殊工具/GameLanguageSystem参数类型替换为int(不带params    
        GameLanguageSystemReplace2,             // Game Tools/特殊工具/GameLanguageSystem参数类型替换为int(带params
        TableManagerTempletCreate,              // Game Tools/特殊工具/TableManagerTemplet重新生成
        TableTempCreate,                        // Game Tools/特殊工具/UtilityTemplet重新生成
        SkeletonDataAssetJsonToSkel,            // Game Tools/特殊工具/将SkeletonDataAsset依赖的json替换为skel
        LogOutAllPlantformSymbols,              // Game Tools/特殊工具/查看当前所有平台的预编译指令
        UpdateModuleToModifyNameSpace,          // Game Tools/特殊工具/模块化工具升级命名空间替换
        PlayerPrefsDeleteAll,                   // Game Tools/特殊工具/清空玩家偏好(PlayerPrefs.DeleteAll
        GameImageBlurAndDispier,                // Game Tools/特殊工具/统计GameImageBlurAndDispier

        Max,
    }

    /// <summary>
    /// prefab工具
    /// </summary>
    public enum GameTools_PrefabTools
    {
        Min = ((int)GameTools_SpecialTools.Min) + 1,

        ClearMatProperties2,                    // Game Tools/prefab工具/（选中）Prefab重新导入
        // SetUIPrefabEqualsDelUDImg 已移除（原菜单 Game Tools/UI制作/修改图片/（选中）去掉prefab界面里GameImage的UD图）
        SetUIPrefabEqualsPublicPrefab,          // Game Tools/prefab工具/（选中）选中一个publicPrefab，设置所有引用此prefab的位置和样式
        OutPutHeadAndBodyDiff,                  // Game Tools/prefab工具/HeadAndBody偏移量
        BigTexturesCheck,                       // Game Tools/prefab工具/UI引用的公共大背景的数量统计
        OpenExportPrefabPackageWindow,          // Game Tools/prefab工具/导出UI Prefab Package
        DeleteUI,                               // Game Tools/prefab工具/无用Prefab删除/无用的UI删除
        ScanAllTextureRefreshFormat,            // Game Tools/prefab工具/统一修改纹理的压缩格式和音效的压缩格式
        OutPutAllLinguageChar,                  // Game Tools/prefab工具/获取字典里面的所有字符
        OutPutDragonAndPlayerDiff,              // Game Tools/prefab工具/输出龙和角色的偏移配置
        ScanTextureRefreshPreview,              // Game Tools/prefab工具/预览所有图集 需要切到 Android 平台

        Max,
    }

    /// <summary>
    /// 游戏开关
    /// </summary>
    public enum GameTools_GameToggles
    {
        Min = GameTools_PrefabTools.Min + 1,

        ToggleFeature,                          // Game Tools/游戏开关/Track Asset Download
        EnableGuide,                            // Game Tools/游戏开关/游戏引导 开
        DisableGuide,                           // Game Tools/游戏开关/游戏引导 关
        EnableLog,                              // Game Tools/游戏开关/游戏日志 开
        DisableLog,                             // Game Tools/游戏开关/游戏日志 关

        Max
    }

    /// <summary>
    /// 图片纹理相关
    /// </summary>
    public enum GameTools_TextureTools
    {
        Min = GameTools_GameToggles.Max + 10,

        AutomaticCompressedCheck,               // Game Tools/图片纹理相关/AutomaticCompressed纹理统计
        BigTexturesMove,                        // Game Tools/图片纹理相关/UI大背景挪动
        UIUnDepenTexture2,                      // Game Tools/图片纹理相关/UI无用纹理删除(动态)
        UIUnDepenTexture1,                      // Game Tools/图片纹理相关/UI无用纹理删除(静态
        TrimTextures,                           // Game Tools/图片纹理相关/UI纹理裁剪(只裁切选中的
        UITexturesCheck,                        // Game Tools/图片纹理相关/UI纹理规范检测
        OpenImageSlicerEditor,                  // Game Tools/图片纹理相关/图片九宫格裁剪
        BigImgChecked,                          // Game Tools/图片纹理相关/大于960 * 1280纹理统计
        ScanTextureSizeMax1024,                 // Game Tools/图片纹理相关/扫描大于1024 的图片并且 设置了 2048
        ScanTextureAlphaMoreThan50,             // Game Tools/图片纹理相关/扫描空白大于 80% 的图片宽或高大于128
        TextureWarpModeSetClamp,                // Game Tools/图片纹理相关/批量处理CharacterResource目录下Wrap模式为Repeat的纹理为Clamp
        ClearSpritePackingTag,                  // Game Tools/图片纹理相关/批量清理Sprite图片的PackingTag
        CheckEffectSpineLoopAnimation,          // Game Tools/图片纹理相关/检查特效中挂spine不是循环动作，没有挂
        POTTextureCheck,                        // Game Tools/图片纹理相关/正方形纹理统计
        TextureNameFind,                        // Game Tools/图片纹理相关/纹理命名规范检测
        TexturesFormatSetting_ETC2,             // Game Tools/图片纹理相关/纹理格式批量设置(ETC2)
        TexturesFormatSetting_ASTC,             // Game Tools/图片纹理相关/纹理格式批量设置(ASTC)
        TextureCompressionFormatWindow,         // Game Tools/图片纹理相关/纹理压缩格式可视化设置
        POTTextureCheck2,                       // Game Tools/图片纹理相关/非4的倍数纹理统计
        CanclePhysicsShape,                     // Game Tools/图片纹理相关/纹理的Generate Physics Shape处理
        TextureMerge,                           // Game Tools/图片纹理相关/纹理合并(US_Image->Common)
        TexturePrefabReferenceFinder,           // Game Tools/图片纹理相关/查找图片预制体引用

    }

#endregion

}
