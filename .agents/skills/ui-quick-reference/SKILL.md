---
name: ui-quick-reference
description: 为本项目 Unity 功能测试生成离线静态 UI 参考图谱。当需要查找功能单元对应的 UI 界面、预制体节点信息（包括按钮和绑定接口的映射关系）、关联脚本和通用组件关系时使用。负责动态查找并解析 UILogicManager.bytes（优先通过 Unity 运行时链路），兼容文本表、Prefab、AutoGen、Logic，并维护本 Skill 的 references/{feature_id}.md；效果图配置和基准图路径均在使用时重新动态定位，不写入 reference；不负责 Unity 运行时路径、点击兜底、已知问题或运行时 reference。
---

# UI Quick Reference

## 概述

本 Skill 中的 `references/...` 和 `scripts/...` 均相对于本文件所在目录解析；跨 Skill 文件使用 `../{skill-name}/...`，不得从项目根目录拼接技能目录路径。

本 skill 用于快速扫描指定功能单元的全部 UI 资源，生成一份结构化的「离线静态 UI 参考图谱」，输出到本 Skill 的 `references/{feature_id}.md`。reference 不记录 `UILogicManager.xlsx` 位置、`UIPerfectPath`、效果图存在性或任何解析结果；每次效果图对比均从当前工作区重新定位。“不记录/不缓存”仅针对表格定位和效果图配置，不影响 `unity-functiontest` 对已验证 UI 节点绝对路径、Logic 实例等运行时信息的独立缓存。

## Skill 时间记录（强制）

遵守 `../functiontest-report-json/references/skill-timing-contract.md`。开始定位 UI 资料前，调用 `../functiontest-report-json/scripts/skill_timing.py start`；reference 生成或更新并确认落盘后调用 `end`。单独调用时使用本轮 operation 目录下的 `*-skill-timing.json`，作为根 Skill 按规则扣除环境过滤时间；由 workflow 调用时使用 workflow 传入的 timing 文件和 `parent_invocation_id`，只记录自己的原始起止时间，不扣除会话环境变量，由父 workflow 在最终上报时统一扣除。由 workflow 调用时只记录时间，不单独生成或上传 JSON。

本 skill 不读取 PlayMode，不判断按钮是否真实生效，也不写入 `../unity-functiontest/references/`。运行时 reference 由 `unity-functiontest` 在实际测试中维护，workflow 负责决定何时调用本 skill。

核心能力：UI 定位（优先读取 UILogicManager.bytes）→ Prefab 扫描（YAML 层级解析，构建完整路径）→ AutoGen 解析 → Logic 解析 → 文档生成。

运行时节点名使用**从预制体根节点开始的全路径**格式（如 `UI_Formation\wanju_group\btn_baocun_1`），AutoGen 完整映射中 GameButton 类型额外包含绑定的响应接口函数名。

## 工作流

### Step 1: 定位 UI

在当前工作区目录下动态查找名称匹配 `UILogicManager` 的文件，不限定固定目录或扩展名。若找到 `UILogicManager.bytes`，**优先使用 Unity 运行时解析链路**，不要把它当作普通文本或因为 Python 无法按 UTF-8 读取就判定为缺失。只有没有 `.bytes` 时，才尝试按 TSV 文本表兼容解析；如果实际项目使用其他扩展名，也沿用动态候选文件和可用的 Unity 表加载链路。通过配表定位目标 UI，支持三种匹配方式，**按优先级依次尝试**：

1. **精确匹配 UIName** — 输入 `UI_DrawCard_Main` 直接命中
2. **关键字模糊匹配** — 输入 `抽卡` 匹配 UIName 或 UIDes，可能有多个结果
3. **兜底：列出候选** — 无匹配时列出前 20 条 UI 记录供选择

文本格式的 `UILogicManager` 文件按现有 TSV 表结构解析，扩展名不作固定要求：

```
ID    UIName    UIDes    canvasIndex    ...
36    UI_DrawCard_Main    抽卡主页面    2    ...
```

### UI 效果图路径查询（只读实时配置）

- reference 禁止记录 `UILogicManager.xlsx` 位置、`UIPerfectPath` 的具体值、文件是否存在、解析状态或“未配置”等结论；这些内容每次均动态定位。
- 工作区固定为传入的 `project_root`，即当前 AI 工作目录；项目根目录在工作区、向上回退一层、向上回退两层三个候选中，按 `Public`、`Art`、`Doc`、`Server` 等目录的精确或有限模糊匹配评分确定；同分取更外层目录，无匹配时默认向上两级。
- 每次效果图对比均调用 `scripts/read_ui_effect_path.py` 重新执行同一套四步：先在工作区、上一级、上两级精确查找；三处都未命中时，仅在本次确定的项目根目录内进行一次模糊搜索。`UILogicManager.xlsx` 的精确查找使用每个候选下的标准 `Public/Tables/Excel/Client/UILogicManager.xlsx`（兼容导表临时路径）；效果图相对路径直接拼接每个候选。两类资源最终模糊搜索必须使用同一个项目根目录，禁止继续向上或无界扫描。
- 当前项目只读取 `UIPerfectPath`。填写绝对路径时直接使用该路径；填写非绝对路径时按上述四步查找。`workspace_relative` 固定表示相对当前工作区解析。
- 查询结果中的 `resolved_path` 是已验证可直接打开的绝对路径；`configured_path` 保留表格原值，`path_source` 和 `match_mode` 用于审计本次命中方式。
- 相对路径精确查找失败后，只进行一次基于填写内容的图片名模糊匹配；候选按文件名、路径后缀、父目录和字符串相似度排序，最匹配的候选排在第一位。
- 绝对路径不存在、相对路径精确查找和模糊搜索均无结果、最高候选并列或匹配度过低时，均按未填写路径处理，并提示用户检查路径是否正确；一个候选也没有时不再继续查找。只有返回 `found` 才允许进入 `ui-image-diff`；未配置或未找到时跳过当前 UI 的效果图对比截图，记录原因，不停止 Unity/PlayMode、不因该原因生成 `blocked` 用例、不阻塞普通功能测试，也不写回 reference。

实时查询示例：

```bash
python scripts/read_ui_effect_path.py UI_TDHeroAll --project-root <工作区目录>
```

### Step 2: 扫描 Prefab

解析 `Assets/GameResource/UIResource/UIPrefab/{UI_Name}/Prefab/` 下的 `.prefab` YAML 文件，提取节点层级关系。

- 解析 GameObject 文档（`m_Name`）和 Transform 文档（`m_Father`、`m_Children`）
- 从根节点（`m_Father: {fileID: 0}`）开始 DFS 构建完整路径
- 输出 `node_name → full_path` 映射表供后续步骤使用

### Step 3: 解析 Prefab（提取节点层级路径）

扫描 `Assets/GameResource/UIResource/UIPrefab/{UI_Name}/Prefab/` 下的 `.prefab` 文件，解析 Unity YAML 结构：

1. 提取所有 `GameObject.m_Name` → `Transform.m_Father` 父子关系
2. 找到根 Transform（`m_Father: {fileID: 0}`），DFS 构建**从预制体根节点开始的完整路径**
3. 输出 `node_name → full_path` 映射表（路径分隔符为 `\`）

示例：`btn_baocun_1` → `UI_Formation\wanju_group\btn_baocun_1`

### Step 4: 解析 AutoGen

读取 `Assets/Scripts/CyStarRoad/UILogic/{UI_Name}/{UI_Name}_AutoGen.cs`，提取 CodeGen 绑定字段。结合 Step 3 的 Prefab 路径映射，生成完整路径。

**字段 → 运行时节点全路径 映射规则**：

| 字段名 | 节点名（去后缀） | 运行时节点全路径 | 规则 |
|--------|-----------------|-----------------|------|
| `btn_baocun_1_4_btn` | `btn_baocun_1` | `UI_Formation\wanju_group\btn_baocun_1` | 去后缀 + Prefab 路径查找 |
| `btn_close_0_btn` | `btn_close` | `UI_Formation\btn_close` | 同上 |
| `img_cost_one_0_img` | `img_cost_one` | `UI_Formation\xxx\img_cost_one` | 同上 |

类型后缀对照：

| 后缀 | 类型 |
|------|------|
| `_btn` | GameButton |
| `_txt` | GameText |
| `_img` | GameImage |
| `_go` | GameObject |
| `_com` | UIComList（子组件） |

### Step 5: 解析 Logic

读取 `Assets/Scripts/CyStarRoad/UILogic/{UI_Name}/{UI_Name}_Logic.cs`，提取：

- 按钮回调注册（`btn.onClick = () => { Method(); }`），支持多种命名模式（`Event_Register` / `BindEvents` / `Button_Register` / 直接 `field.onClick =`）
- 关键私有字段定义（`private int _currentPoolId;` 等）

### Step 6: 生成文档

默认只输出到本 skill 的 `references/{feature_id}.md`，包含静态结构信息。输出文档的标题、章节名、表头和语义说明必须使用中文；UI 名称、节点路径、类名、方法名、字段名和 `feature_id` 等技术标识保持原样。`../unity-functiontest/references/{feature_id}.md` 不由本离线扫描脚本代写，而由 FunctionTest 在运行时根据实测信息维护：

1. 基本信息 — UIID、CanvasIndex、Logic 全限定名、完整场景路径
2. 子 UI 列表 — 同一功能关联的所有子界面
3. 进场流程 — 真实导航入口、已验证按钮链路和进入后轮询确认模板；不输出直接创建 UI 的代码模板
4. 节点树速查 — AutoGen 绑定组件清单 + 命名规则（全路径格式）
5. 按钮/交互速查 — AutoGen 字段 → 运行时节点全路径 → 回调方法映射
6. AutoGen 字段完整映射 — 所有 CodeGen 字段的完整映射表；GameButton 类型额外包含响应接口函数名
7. Logic 关键字段 — 字段名、类型、用途
8. Logic 缓存 + 状态读取 helper — 反射缓存代码模板
9. 兼容字段 — 旧文档中的“已知问题”和“用例分组建议”只允许保留，不属于本 skill 的权威数据；权威内容以 `unity-functiontest/references/{feature_id}.md` 和本轮 `known-issues.json` 为准

**已存在文件时增量更新**：只更新静态结构信息，保留旧文档中的兼容字段，不把运行时路径、点击结果或已知问题重新推断后覆盖。生成或更新 reference 是测试资料维护，不属于业务代码修改；即使 FunctionTest 选择“不允许修改代码”，也必须允许生成和刷新 reference。

## 单独调用后的 JSON 上报

当用户直接调用 ui-quick-reference，而不是由 functiontest-workflow 编排时，扫描或更新 reference 完成后，必须自动完成一次用量上报：

1. 调用 check-cyoucode-spend 读取当前 Token 和消耗。
2. 调用 functiontest-report-json 的 operation-only 模式，固定操作类型为“UI快速分析”，同时传入本轮已闭合的 timing 文件和 `--skill-name ui-quick-reference`，输出到本轮新的 operation 运行目录。
3. 调用 functiontest-json-upload 上传最终 JSON。

operation-only JSON 不读取测试报告，pass、failed、blocked、test_inconclusive、success_count、failure_count、bug_count 和 feature_count 等测试统计全部为 0，只写入操作类型、Token 和消耗数据。若 ui-quick-reference 是由 functiontest-workflow 调用，则不在此处重复上传，由主动测试工作流统一使用“主动测试工作流”上报。

示例输出路径：

```text
Doc/AI开发文档/output/{feature_id}/{feature_id}-operation-{seq4}/{feature_id}-operation-{seq4}-functiontest-upload.json
```

### `UILogicManager.bytes` 推荐解析链

项目中的 `.bytes` 是加密二进制表，推荐复用 Unity 已有实现，不要在 Python 中重复实现解密协议：

1. 动态找到名称匹配 `UILogicManager` 且扩展名为 `.bytes` 的文件。
2. 调用 Unity `evaluate`，使用 `Game.Core.TableUILogicManager.GetDataByUIName` 读取目标 UI。
3. Unity 内部通过 `TableManager` 和 `GameUtil.decryptEncypt` 完成加载、解密，再由 `TableUILogicManager.Deserialize` 反序列化。
4. 将 Unity 返回的 `ID`、`UIName`、`canvasIndex` 传给扫描脚本的 `--runtime-*` 参数，覆盖文本解析结果。

目标 UIName 已明确时，`evaluate` 可使用以下最小代码：

```csharp
var d = Game.Core.TableUILogicManager.GetDataByUIName("UI_TDHeroAll");
if (d == null) return "";
return d.ID + "\t" + d.UIName + "\t" + d.canvasIndex;
```

随后将返回值拆分为 `ID`、`UIName`、`CanvasIndex`，调用：

```bash
python scripts/scan_ui_references.py UI_TDHeroAll --feature-id hero-list --runtime-ui-id 225 --runtime-ui-name UI_TDHeroAll --runtime-canvas-index 2
```

如果 Unity 查询不到目标 UI，必须保留解析失败证据，不得伪造 UIID 或 CanvasIndex；只有用户明确提供 UIName 时，才允许沿用脚本的明确 UIName 兜底。

## 使用示例

### 示例 1：按关键字生成

```bash
python scripts/scan_ui_references.py 抽卡
```

输出：`references/draw-card.md`

### 示例 2：指定 UIName 和 feature_id

```bash
python scripts/scan_ui_references.py UI_DrawCard_Main --feature-id draw-card
```

### 示例 3：指定静态输出目录

```bash
python scripts/scan_ui_references.py 抽卡 --out-dir references
```

指定 `--out-dir` 时只写入静态 reference 目录；未指定时默认写入本 skill 的 references 目录。禁止把输出目录指向 `../unity-functiontest/references/`。

### 示例 4：更新已有参考文档

```bash
python scripts/scan_ui_references.py UI_ToyMainList --feature-id chess-system
```

### 示例 5：使用 Unity 解析 `.bytes` 后生成参考文档

```bash
python scripts/scan_ui_references.py UI_TDHeroAll --feature-id hero-list --runtime-ui-id 225 --runtime-ui-name UI_TDHeroAll --runtime-canvas-index 2
```

## 兜底策略

| 场景 | 兜底 |
|------|------|
| 关键字匹配不到 | 列出前 20 条 UI 记录供选择 |
| 精确匹配命中 | 直接使用，忽略模糊匹配 |
| 多个模糊匹配 | 按匹配度排序并输出候选；最高候选明确领先时使用第一位，并列或匹配度过低时按未配置处理 |
| Prefab 目录不存在 | 仅用 AutoGen 生成字段清单，标注"待 Prefab 确认" |
| AutoGen 文件不存在 | 仅生成基本信息，标注"待补充" |
| Logic 文件不存在 | 仅生成结构信息，按钮映射留空 |
| 已有文件存在 | 增量更新静态结构，保留旧文档兼容字段 |

## 资源

### scripts/

- [`scan_ui_references.py`](scripts/scan_ui_references.py) — 核心扫描脚本。在当前工作区目录优先动态查找 `UILogicManager.bytes`；Unity 解析结果通过 `--runtime-ui-id`、`--runtime-ui-name`、`--runtime-canvas-index` 等参数传入，再结合 `Prefab` → `AutoGen` → `Logic` 生成离线静态参考文档。支持 `--feature-id`、`--out-dir`、`--project-root` 和 `--runtime-*` 参数；其中 `--project-root` 表示当前工作区目录。未传 `--out-dir` 时默认生成到本 Skill 的 `references/`，并拒绝写入运行时 reference 目录。
- [`read_ui_effect_path.py`](scripts/read_ui_effect_path.py) — 按当前 `UIName` 每次重新定位并读取 `UILogicManager.xlsx` 中的效果图路径；不读取或写入 reference、进程内路径缓存。

### references/

存放本 skill 生成的离线 UI 快速参考图谱文件（`{feature_id}.md`）。FunctionTest 运行时参考文档单独存放在 `../unity-functiontest/references/`，由运行时实测维护；两者不得由同一个扫描输出覆盖。
