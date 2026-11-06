# login - UI 快速参考

## 1. 基本信息

| 属性 | 值 |
|------|-----|
| feature_id | `login` |
| UIID | `UI_LoginGame` |
| UIDes | 登录界面 |
| CanvasIndex | 0 |
| UI 根节点名 | `UI_LoginGame` |
| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame` |
| Logic 全限定名 | `HotFix_Project.UI_LoginGame_Logic` |
| Assembly | 遍历 AppDomain 获取（非固定名） |
| UIID 常量 | `UIID.UI_LoginGame`（见 Gen/Table/UIID.cs） |

## 2. 进场流程

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；当前参考不提供进场调用代码
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
// 轮询确认
var ui = GameObject.Find("UI_LoginGame");
// activeInHierarchy == true → 就绪
```

**全限定路径轮询（推荐）**：
```csharp
var root = "GameEntry/Builtin/UI/AdapterArea/Canvas0/";
var ui = GameObject.Find(root + "UI_LoginGame");
```

## 3. 节点树速查

# Prefab: UI_LoginGame.prefab
# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取

### AutoGen 绑定组件清单

| 运行时节点名 | 字段名 | 类型 | 注释 |
|-------------|--------|------|------|
| `LoginButton` | `LoginButton_0_btn` | GameButton | 登录按钮 |
| `NoticeBtn` | `NoticeBtn_1_btn` | GameButton | 公告按钮 |
| `RepairBtn` | `RepairBtn_2_btn` | GameButton | 修复按钮 |
| `AccountBtn` | `AccountBtn_3_btn` | GameButton | 注销登出 |
| `bg` | `bg_4_btn` | GameButton | selelctServer |
| `gusetLoginButton` | `gusetLoginButton_5_btn` | GameButton | 游客登录 |
| `GoogleLoginButton` | `GoogleLoginButton_6_btn` | GameButton | Google登录 |
| `FaceBookIDLoginButton` | `FaceBookIDLoginButton_7_btn` | GameButton | FaceBase登录 |
| `AppleIDLoginButton` | `AppleIDLoginButton_8_btn` | GameButton | AppleID登录 |
| `AIBtn` | `AIBtn_9_btn` | GameButton | 客服 |
| `AgeTipsBtn` | `AgeTipsBtn_10_btn` | GameButton | 适龄提示按钮 |
| `UserAgreementBtn` | `UserAgreementBtn_11_btn` | GameButton | 用户协议 |
| `UserInfoBtn` | `UserInfoBtn_12_btn` | GameButton | 信息清单 |
| `TestVideo` | `TestVideo_13_btn` | GameButton | 视频测试 |
| `TestVideo_Skip` | `TestVideo_Skip_14_btn` | GameButton | 视频跳过 |
| `TestShare` | `TestShare_15_btn` | GameButton | 测试分享 |
| `Test` | `Test_16_btn` | GameButton | 测试 |
| `CloseTest` | `CloseTest_17_btn` | GameButton | 关闭测试 |
| `ExitGameBtn` | `ExitGameBtn_18_btn` | GameButton | 退出游戏按钮 |
| `StatusImg_Green` | `StatusImg_Green_0_img` | GameImage | 服务器状态_正常 |
| `StatusImg_Red` | `StatusImg_Red_1_img` | GameImage | 服务器状态_红色 |
| `StatusImg_Yellow` | `StatusImg_Yellow_2_img` | GameImage | 服务器状态_黄色 |
| `StatusImg_Gray` | `StatusImg_Gray_3_img` | GameImage | 服务器状态_灰色 |
| `AgreementToggle_0_tgl` | `AgreementToggle_0_tgl` | GameToggle | 协议同意选项 |
| `InputAccount_0_inpt` | `InputAccount_0_inpt` | GameInputField | Game Input Field【文本输入控件】_0 |
| `SeverName` | `SeverName_0_txt` | GameText | 默认服务器名 |
| `VersionTxt` | `VersionTxt_1_txt` | GameText | 游戏版本号 |
| `Resversionnum` | `Resversionnum_2_txt` | GameText | 资源版本号 |
| `LoginBtns` | `LoginBtns_0_go` | GameObject | NormalLoginButtons |
| `SdkLoginBtns` | `SdkLoginBtns_1_go` | GameObject | SDKLoginBtns |

**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀即为 `运行时节点名`。
例如 `btn_chouka1_0_btn` → 运行时节点 `btn_chouka1`。

## 4. 按钮/交互速查

| AutoGen 字段 | 运行时节点 | 触发方式 | Logic 回调 |
|-------------|-----------|---------|-----------|
| `ExitGameBtn_18_btn` | `ExitGameBtn` | `onClick?.Invoke()` | ExitGame() |
| `RepairBtn_2_btn` | `RepairBtn` | `onClick?.Invoke()` | GameUISystem.Inst.GetUIInitData() |
| `LoginButton_0_btn` | `LoginButton` | `onClick?.Invoke()` | LoginButton_0_btnOnClick() |
| `gusetLoginButton_5_btn` | `gusetLoginButton` | `onClick?.Invoke()` | sdkLogin() |
| `GoogleLoginButton_6_btn` | `GoogleLoginButton` | `onClick?.Invoke()` | SDKManager.Inst.switchAccount() |
| `AppleIDLoginButton_8_btn` | `AppleIDLoginButton` | `onClick?.Invoke()` | SDKManager.Inst.switchAccount() |
| `FaceBookIDLoginButton_7_btn` | `FaceBookIDLoginButton` | `onClick?.Invoke()` | SDKManager.Inst.switchAccount() |
| `AIBtn_9_btn` | `AIBtn` | `onClick?.Invoke()` | game() |
| `NoticeBtn_1_btn` | `NoticeBtn` | `onClick?.Invoke()` | ShowLoginNotice() |
| `bg_4_btn` | `bg` | `onClick?.Invoke()` | SendReqRoleLogicServerList() |
| `AgeTipsBtn_10_btn` | `AgeTipsBtn` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `UserAgreementBtn_11_btn` | `UserAgreementBtn` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `UserInfoBtn_12_btn` | `UserInfoBtn` | `onClick?.Invoke()` | 真实入口触发后预期打开目标 UI |
| `Test_16_btn` | `Test` | `onClick?.Invoke()` | transform.Find() |

**通用规则**：所有 GameButton 均可用 `onClick?.Invoke()` 触发，无需 ExecuteButtonClick。

## 5. AutoGen 字段完整映射

| 字段名 | 运行时节点名 | 类型 | 注释 |
|--------|-------------|------|------|
| `LoginButton_0_btn` | `LoginButton` | GameButton | 登录按钮 |
| `NoticeBtn_1_btn` | `NoticeBtn` | GameButton | 公告按钮 |
| `RepairBtn_2_btn` | `RepairBtn` | GameButton | 修复按钮 |
| `AccountBtn_3_btn` | `AccountBtn` | GameButton | 注销登出 |
| `bg_4_btn` | `bg` | GameButton | selelctServer |
| `gusetLoginButton_5_btn` | `gusetLoginButton` | GameButton | 游客登录 |
| `GoogleLoginButton_6_btn` | `GoogleLoginButton` | GameButton | Google登录 |
| `FaceBookIDLoginButton_7_btn` | `FaceBookIDLoginButton` | GameButton | FaceBase登录 |
| `AppleIDLoginButton_8_btn` | `AppleIDLoginButton` | GameButton | AppleID登录 |
| `AIBtn_9_btn` | `AIBtn` | GameButton | 客服 |
| `AgeTipsBtn_10_btn` | `AgeTipsBtn` | GameButton | 适龄提示按钮 |
| `UserAgreementBtn_11_btn` | `UserAgreementBtn` | GameButton | 用户协议 |
| `UserInfoBtn_12_btn` | `UserInfoBtn` | GameButton | 信息清单 |
| `TestVideo_13_btn` | `TestVideo` | GameButton | 视频测试 |
| `TestVideo_Skip_14_btn` | `TestVideo_Skip` | GameButton | 视频跳过 |
| `TestShare_15_btn` | `TestShare` | GameButton | 测试分享 |
| `Test_16_btn` | `Test` | GameButton | 测试 |
| `CloseTest_17_btn` | `CloseTest` | GameButton | 关闭测试 |
| `ExitGameBtn_18_btn` | `ExitGameBtn` | GameButton | 退出游戏按钮 |
| `StatusImg_Green_0_img` | `StatusImg_Green` | GameImage | 服务器状态_正常 |
| `StatusImg_Red_1_img` | `StatusImg_Red` | GameImage | 服务器状态_红色 |
| `StatusImg_Yellow_2_img` | `StatusImg_Yellow` | GameImage | 服务器状态_黄色 |
| `StatusImg_Gray_3_img` | `StatusImg_Gray` | GameImage | 服务器状态_灰色 |
| `AgreementToggle_0_tgl` | `AgreementToggle_0_tgl` | GameToggle | 协议同意选项 |
| `InputAccount_0_inpt` | `InputAccount_0_inpt` | GameInputField | Game Input Field【文本输入控件】_0 |
| `SeverName_0_txt` | `SeverName` | GameText | 默认服务器名 |
| `VersionTxt_1_txt` | `VersionTxt` | GameText | 游戏版本号 |
| `Resversionnum_2_txt` | `Resversionnum` | GameText | 资源版本号 |
| `LoginBtns_0_go` | `LoginBtns` | GameObject | NormalLoginButtons |
| `SdkLoginBtns_1_go` | `SdkLoginBtns` | GameObject | SDKLoginBtns |

## 6. Logic 关键字段

| 字段名 | 类型 | 用途 |
|--------|------|------|
| `nServerId` | int | 当前选中服务器 ID（static） |
| `nServerName` | string | 当前选中服务器名（static） |
| `ServerDataList` | List<ServerListData> | 服务器列表数据缓存 |
| `curServerIndex` | int | 当前选中服务器在列表中的索引，-1 表示未选中 |
| `nCurNoticeState` | int | 公告状态：1=登录前公告，2=登录后公告 |
| `_isClickNoticeBtn` | bool | 是否由点击公告按钮触发弹窗（区分主动/被动） |
| `hasBeenPopAgreement` | bool | 是否已弹出过协议同意弹窗 |
| `autoLoginBtnTimerGUID` | long | 自动登录定时器 GUID |
| `_isShowAnnouncement` | bool | 当前是否正在展示公告 |

## 7. Logic 缓存 + 状态读取 helper

```csharp
// === 首次缓存 ===
System.Type t = null;
foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {
    t = asm.GetType("HotFix_Project.UI_LoginGame_Logic");
    if (t != null) { UnityEngine.PlayerPrefs.SetString("__test_logic_asm__", asm.GetName().Name); break; }
}
UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);
UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "UI_LoginGame");
UnityEngine.PlayerPrefs.Save();
var root = GameObject.Find("UI_LoginGame");
var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();
var adapter = typeof(GameFramework.Logic.BaseUI)
    .GetField("m_MonoInvocationAdapter", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(baseUI);
var lg = adapter.GetType()
    .GetField("m_Instance", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
    .GetValue(adapter);

// === 批量状态读取（合并单次 evaluate） ===
var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame");
// 根据实际节点补充读取代码
```

## 8. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| — | — | — | — |

## 9. 用例分组建议

| 分组 | 用例 | 说明 |
|------|------|------|
| 进场验证 | 登录界面打开后根节点存在、activeInHierarchy=true | 轮询 `GameEntry/Builtin/UI/AdapterArea/Canvas0/UI_LoginGame` |
| 进场验证 | 版本号文本正确显示 | `VersionTxt` 显示 `Context.DisplayVersion`，`Resversionnum` 显示 `GameResUpdater.CacheVer` |
| 进场验证 | 服务器状态图标正确切换 | `SetServerStatus()` 按 Fluent/Crowded/Full/Offline/Maintenance 切换 Green/Yellow/Red/Gray |
| 账号登录 | 输入账号后点击登录按钮 | `LoginButton` → `LoginButton_0_btnOnClick()`，空账号自动随机生成 |
| 账号登录 | 未勾选协议时点击登录 | 弹出提示 `UI_NoticeTipsUP_Logic.Inst.PopTips(8000088)` |
| SDK 登录 | 游客登录 | `gusetLoginButton` → `SDKManager.Inst.sdkLogin()` |
| SDK 登录 | Google/Apple/Facebook 切换账号 | 对应按钮 → `SDKManager.Inst.switchAccount(SDKAccountType.X)` |
| 公告 | 点击公告按钮 | `NoticeBtn` → `ShowLoginNotice()`，`_isClickNoticeBtn=true` |
| 公告 | 登录前自动弹公告 | `Awake()` 中 `ShowAnnouncement()`，有公告内容时创建 `UI_Announcement` |
| 协议弹窗 | 适龄提示 | `AgeTipsBtn` → 创建 `UI_CommonPopShort` |
| 协议弹窗 | 用户协议 | `UserAgreementBtn` → 创建 `UI_CommonPop` |
| 协议弹窗 | 信息清单 | `UserInfoBtn` → 创建 `UI_CommonPop` |
| 服务器选择 | 点击 bg 按钮请求服务器列表 | `bg` → `LoginManager.Inst.SendReqRoleLogicServerList()` |
| 修复 | 点击修复按钮弹确认框 | `RepairBtn` → 弹 `UI_MessageBox`，确认后 `RepairUpdateRes()` |
| 退出 | 点击退出游戏 | `ExitGameBtn` → `SDKManager.Inst.ExitGame()` |
| 测试入口 | 测试面板开关 | `Test` 打开 / `CloseTest` 关闭父节点 |
