# 同框架登录候选

<!-- 创建日期：2026-11-02；作者：Cyou；更新日期：2026-11-05；更新人：Codex；功能：保留 CyouCode 历史核验过的登录候选，删除跨项目通用化和过期判定说明；参数：当前真实节点、明确 setup 授权及动作后新帧。不包含账号或凭据，不自动登录。 -->

仅在目标采用相同 GameFramework 登录结构且确需准备登录时使用。这些是历史定位候选，不保证其他项目、当前构建或重建界面的路径/状态相同；先 `builtin:chain/subtree/buttons` 核验现场，不把固定路径当已验证事实。

## 候选与模板

| 目标 | 历史路径（共同前缀 `GameEntry/Builtin/UI/AdapterArea/`） |
| --- | --- |
| 登录页 | `Canvas0/UI_LoginGame` |
| 普通登录按钮 | `Canvas0/UI_LoginGame/LoginBtns/LoginButton` |
| 协议开关 | `Canvas0/UI_LoginGame/AgreementToggle` |
| 账号输入 | `Canvas0/UI_LoginGame/InputAccount/InputAccount` |
| SDK 登录组 | `Canvas0/UI_LoginGame/SdkLoginBtns` |
| 主界面 | `Canvas0/UI_Main` |

[read-login-state.cs](../assets/templates/read-login-state.cs) 仅返回候选登录页/按钮/SDK 组/协议/主界面状态与帧；[click-login.cs](../assets/templates/click-login.cs) 对固定候选 `GameButton` 调用一次 `InvokeOnClickListener()`。两份模板有历史使用记录，保留原字节；只有路径、控件和授权均核验后才可使用。目标不同就在本轮新文件中按真实入口编写，不改旧模板或已登记来源。

## 当前使用规则

`GameButton` 与标准 `UnityEngine.UI.Button` 不同；真实回调先检查控件可点击和业务条件，一次调用成功不代表已发登录请求或登录成功。按当前源码/观察核对协议、账号及角色列表等条件，不沿用历史默认值，不自动勾选协议、更换账号或调用 SDK/GM。

登录属独立准备 `setup_action`，来源、守卫和新帧遵循[共享链路](host-contract.md)。界面切换异步，登录页消失不足以证明主界面就绪；以当前真实就绪条件设置原预算内的 `poll.require_match=true`，等待稳定样本及最后确认帧，未确认不重发登录或重启。

主界面入口可能是同名容器下的内层按钮，目标页也可能在不同 Canvas；重新定位实际按钮和目标页面。登录、功能解锁、资源/计次及执行入口是不同事实，逐项按原用例核对，不能用某个展示字段替代全部前置或删除原限制。
