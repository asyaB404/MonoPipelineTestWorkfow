# 同框架固定登录

<!-- 创建日期：2026-11-02；作者：Cyou；更新日期：2026-11-06；更新人：Codex；功能：按用户确认的中台固定路径完成登录准备；参数：已有登录授权、真实按钮实例及动作后新帧。固定登录精简建议归属Codex，原模板归属CyouCode；不包含账号或凭据。 -->

仅用于采用本中台登录结构的目标。用户已确认以下固定入口，不再把它当候选重新扫描，不推导协议、账号、SDK或主界面的通用登录方案；其他框架不自动套用。

## 固定入口

| 目标 | 固定完整路径 |
| --- | --- |
| 登录页 | `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame` |
| 普通登录按钮 | `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame/LoginBtns/LoginButton` |

## 执行顺序

1. 复用附加`discovery`选路并照常登记准备链路，首个观察仍为`builtin:chain`。登录页激活时直接以该页为`builtin:buttons.root`，选择固定完整按钮路径；仅核验实际实例、可交互状态及原守卫，不遍历全场景。已有登录授权直接复用，无授权不点击。
2. 以现有`setup_action`及`builtin:click_button`调用该按钮一次，不另写点击C#，不勾协议、不换账号、不调用SDK或GM。登录来源只写固定步骤，如`original_text="确认固定登录页状态，必要时点击普通登录按钮并等待登录页消失。"`，不再写“读取当前登录页、登录按钮、协议开关与主界面状态”。
3. 动作后使用[read-login-state.cs](../assets/templates/read-login-state.cs)独立新帧观察，设`poll.field=/login_page_state`、`operator=eq`、`value=absent`、`stable_samples=2`、`require_match=true`并绑定真实登录动作。登录页从激活变为不存在或不再激活，即按本框架约定完成登录准备；不额外等待`UI_Main`作为登录条件。未消失则保留未完成/实际错误，不重复点击。

## 使用注意

`GameObject.Find`只查激活层级，因此模板的`absent`表示当前没有激活登录页，也包含缓存但已隐藏的登录页；不做全场景非激活对象扫描。模板只返回状态和帧，不返回登录成功或测试通过的自述结论。

初始已处于稳定业务现场时跳过登录动作；启动空场景中尚未出现登录页不冒充已登录。按钮缺失、不可交互或点击后页面不消失时才按实际错误做定向诊断，不把协议扫描恢复成每轮固定前置。协议仍由原按钮回调处理，工具不绕过或自动同意。

登录、业务页面就绪、功能解锁和资源条件是不同事实；业务原前置仍逐例检查。登录准备仍遵循[共享链路](host-contract.md)，不计入业务通过数。[click-login.cs](../assets/templates/click-login.cs)保留为历史兼容模板，常规路径使用已有内置按钮动作；不改历史已登记请求及脚本快照。
