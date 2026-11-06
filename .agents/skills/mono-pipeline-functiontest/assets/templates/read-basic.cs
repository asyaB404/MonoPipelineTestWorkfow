// 创建日期：2026-10-26；作者：Cyou。
// 功能：纯 Unity 基础属性方法体，不依赖尚未提供的公共桥接或热更强类型。
// 参数：由宿主包装真实 run/case/command/build/frame；本片段不作业务断言。
return new System.Collections.Generic.Dictionary<string, object> {
    {"unity_version", UnityEngine.Application.unityVersion},
    {"build_guid", UnityEngine.Application.buildGUID},
    {"platform", UnityEngine.Application.platform.ToString()},
    {"frame", UnityEngine.Time.frameCount},
    {"is_playing", UnityEngine.Application.isPlaying}
};
