// 创建日期：2026-11-02；作者：Cyou；更新日期：2026-11-06；更新人：Codex。
// 功能：只读固定登录页是否仍激活，不扫描协议、账号、SDK或主界面。
// 参数：无入参；固定路径经用户确认，宿主保留身份/新帧；absent包含已隐藏的缓存页，不自述登录成功。
const string __loginPath = "GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame";
UnityEngine.GameObject __loginPage = UnityEngine.GameObject.Find(__loginPath);
return new System.Collections.Generic.Dictionary<string, object> {
    {"login_page_state", __loginPage == null ? "absent" : "active_in_hierarchy"},
    {"frame", UnityEngine.Time.frameCount}
};
