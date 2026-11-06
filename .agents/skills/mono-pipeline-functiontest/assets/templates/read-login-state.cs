// 创建日期：2026-11-02；作者：Cyou。
// 功能：通用登录链路只读探针，返回登录页/登录按钮/协议勾选/主界面/被测入口的激活状态，供链路段 before/after 判定；不点击、不改数据、不调用 SDK/GM。
// 参数：无入参；由宿主包装 run/case/command/build/frame。节点路径见 references/login-navigation.md。
System.Func<string, UnityEngine.GameObject> __find = delegate(string p) {
    UnityEngine.GameObject go = UnityEngine.GameObject.Find(p);
    if (go != null) { return go; }
    UnityEngine.Transform[] all = UnityEngine.Resources.FindObjectsOfTypeAll<UnityEngine.Transform>();
    foreach (UnityEngine.Transform t in all) {
        if (t == null || t.gameObject == null) { continue; }
        if (!t.gameObject.scene.IsValid()) { continue; }
        string path = t.name; UnityEngine.Transform cur = t.parent;
        while (cur != null) { path = cur.name + "/" + path; cur = cur.parent; }
        if (path == p) { return t.gameObject; }
    }
    return null;
};
System.Func<string, string> __state = delegate(string p) {
    UnityEngine.GameObject go = __find(p);
    if (go == null) { return "absent"; }
    if (go.activeInHierarchy) { return "active_in_hierarchy"; }
    if (go.activeSelf) { return "active_self_inactive_parent"; }
    return "inactive";
};
System.Func<string, bool?> __toggle = delegate(string p) {
    UnityEngine.GameObject go = __find(p);
    if (go == null) { return (bool?)null; }
    UnityEngine.UI.Toggle t = go.GetComponent<UnityEngine.UI.Toggle>();
    if (t != null) { return (bool?)t.isOn; }
    foreach (UnityEngine.Component c in go.GetComponents<UnityEngine.Component>()) {
        if (c == null || c.GetType().Name != "GameToggle") { continue; }
        System.Reflection.PropertyInfo pr = c.GetType().GetProperty("isOn");
        if (pr == null) { continue; }
        try { object v = pr.GetValue(c, null); return v == null ? (bool?)null : System.Convert.ToBoolean(v); } catch (System.Exception) { return (bool?)null; }
    }
    return (bool?)null;
};
string __login = "GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame";
return new System.Collections.Generic.Dictionary<string, object> {
    {"login_page_state", __state(__login)},
    {"login_button_state", __state(__login + "/LoginBtns/LoginButton")},
    {"sdk_login_group_state", __state(__login + "/SdkLoginBtns")},
    {"agreement_toggle_on", __toggle(__login + "/AgreementToggle")},
    {"main_page_state", __state("GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_Main")},
    {"frame", UnityEngine.Time.frameCount}
};
