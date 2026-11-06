# Unity 功能测试运行时 UI 参考模板

为 `unity-functiontest` skill 提供每个功能的运行时 UI 参考文档。按 feature_id 命名：`references/{feature_id}.md`。本文件只保留通用结构，不写入任何具体 UI 的示例数据。文档标题、章节名、表头和语义说明必须使用中文；UI 名称、节点路径、类名、方法名和字段名等技术标识保持原样。

---

## 1. 执行速查

| 字段 | 值 |
|------|-----|
| 功能标识 | `<kebab-case>` |
| UI 根节点 | `<GameObject.Find 可用名称>` |
| 完整场景路径 | `<GameEntry/Builtin/UI/AdapterArea/CanvasX/UI_XXX>` |
| Logic 全限定名 | `<HotFix_Project.UI_XXX_Logic>` |
| 所属程序集 | `<遍历 AppDomain 获取，非固定名>` |
| UIID 常量 | `<UIID.UI_XXX>` |
| Canvas 序号 | `<UILogicManager 中的 canvasIndex>` |
| 登录要求 | `<需要登录/不需要登录/需业务数据就绪>` |

### 打开方式

```csharp
// 通过真实导航入口或已验证按钮链路进入目标 UI；本节不提供直接创建 UI 的调用代码。
// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，动作仍从真实入口触发。
```

```csharp
// 独立轮询确认：必须拆成第二次 evaluate。
var ui = UnityEngine.GameObject.Find("UI_XXX");
return ui != null && ui.activeInHierarchy ? "ready" : "not_ready";
```

## 2. 关键节点

| 语义 | 运行时路径 | 类型 | 用途 | 来源 |
|------|------------|------|------|------|
| 主按钮 | `UI_XXX/.../btn_action` | GameButton | `<用途>` | AutoGen/Prefab/实测 |
| 主列表 | `UI_XXX/.../ScrollView/Viewport/Content` | ScrollRect | `<用途>` | AutoGen/Prefab/实测 |

## 3. 交互映射

| AutoGen 字段 | 运行时节点路径 | 组件 | 触发方式 | Logic 回调 | 备注 |
|-------------|----------------|------|----------|------------|------|
| `btn_xxx_0_btn` | `UI_XXX/.../btn_xxx` | GameButton | `onClick?.Invoke()` | `OnXxxClick` | `<守卫条件/兜底>` |

## 4. 状态读取辅助代码

```csharp
// 本段只保留当前 feature 真实需要的批量读取字段。
var root = UnityEngine.GameObject.Find("UI_XXX");
if (root == null) return "root_null";

var builder = new System.Text.StringBuilder();
var titleNode = root.transform.Find("txt_title");
var titleText = titleNode != null ? titleNode.GetComponent<GameFramework.Logic.GameText>() : null;
builder.Append("title=").Append(titleText != null ? titleText.text : "?");

var content = root.transform.Find("ScrollView/Viewport/Content");
builder.Append(",listCount=").Append(content != null ? content.childCount : 0);
return builder.ToString();
```

## 5. 已知问题

| 节点 | 症状 | 兜底方案 | 确认日期 |
|------|------|---------|---------|
| — | — | — | — |

## 6. 用例分组建议

| group_id | 用例 | 共享前置 | RunSuite 操作摘要 |
|----------|------|----------|------------------|
| `initial` | `TC-001` | 刚进入 UI，默认状态 | `snapshot` |

## 7. 运行时补充

### 路径别名

| 预期路径/名称 | 实测路径/名称 | 命中策略 | 记录时间 |
|---------------|---------------|----------|----------|
| — | — | — | — |

### 遮挡处理

| 遮挡 UI | 处理方式 | 结果 | 记录时间 |
|---------|----------|------|----------|
| — | — | — | — |

### 视觉基准图

| UI | 基准图路径 | 首次截图路径 | 对比结论 |
|----|------------|--------------|----------|
| — | — | — | — |

### 修复摘要

| CaseId | 修复文件:行号 | 修复说明 | 重测结果 |
|--------|---------------|----------|----------|
| — | — | — | — |
