// 创建日期：2026-11-02；作者：Cyou。
// 功能：通用登录链路动作探针，反射调用 UI_LoginGame/LoginBtns/LoginButton 的 GameButton.InvokeOnClickListener() 一次；不重试、不轮询、不调用 SDK/GM。
// 参数：无入参；由宿主包装 run/case/command/build/frame。历史兼容模板，常规使用builtin:click_button；动作后新帧确认登录页消失，不额外绑定主界面。
UnityEngine.GameObject __loginBtn = UnityEngine.GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame/LoginBtns/LoginButton");
if (__loginBtn == null) { throw new System.InvalidOperationException("login_button_not_found"); }
System.Type __btnType = null;
UnityEngine.Component __btnComponent = null;
foreach (UnityEngine.Component __c in __loginBtn.GetComponents<UnityEngine.Component>()) {
    if (__c == null) { continue; }
    if (__c.GetType().Name == "GameButton") { __btnType = __c.GetType(); __btnComponent = __c; break; }
}
if (__btnType == null || __btnComponent == null) { throw new System.InvalidOperationException("game_button_component_missing"); }
System.Reflection.MethodInfo __m = __btnType.GetMethod("InvokeOnClickListener",
    System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic,
    null, System.Type.EmptyTypes, null);
if (__m == null) { throw new System.InvalidOperationException("invoke_onclick_listener_missing"); }
__m.Invoke(__btnComponent, null);
return new System.Collections.Generic.Dictionary<string, object> {
    {"invoked", true},
    {"button_type", __btnType.FullName},
    {"frame", UnityEngine.Time.frameCount}
};
