---
name: testcase-gen
description: 拖动需求文档（docx/xlsx/md/txt）作为参数传入，一键生成测试用例。游戏类型默认推塔防（TOWER_DEF，如齿轮滚滚），无需询问。触发词：生成测试用例、分析需求、写测试用例、测试要点、导出用例、生成用例、分析文档、跑流水线、/testcase-gen
---

# 测试用例一键生成

## Skill 时间记录（强制）

遵守 `../functiontest-report-json/references/skill-timing-contract.md`。开始读取需求文档前，调用 `../functiontest-report-json/scripts/skill_timing.py start`；生成、导出并确认用例文件落盘后调用 `end`。单独调用时使用本轮 operation 目录下的 `*-skill-timing.json`，作为根 Skill 按规则扣除环境过滤时间；由 workflow 调用时使用 workflow 传入的 timing 文件和 `parent_invocation_id`，只记录自己的原始起止时间，不扣除会话环境变量，由父 workflow 在最终上报时统一扣除。由 workflow 调用时只记录时间，不单独生成或上传 JSON。

## 前置准备

首次使用前，先装好 Python 依赖：

```bash
pip install openpyxl python-docx
```

如果文档是 `.docx` 格式，需要 `python-docx`。如果是 `.xlsx`，需要 `openpyxl`。导出 Excel 始终需要 `openpyxl`。

如果遇到 `ModuleNotFoundError`，提醒用户运行上面的安装命令后重试。

## 工作流程

### 第 1 步：读取文档

### 文档路径

文档路径由用户拖动文档作为参数传入，直接从调用参数中获取。若参数为空或路径不存在，再询问用户提供正确路径。

### 游戏类型

默认「推塔防（TOWER_DEF）」类型（如齿轮滚滚等），无需询问用户。若用户明确指定其他类型，则使用用户指定的类型。

### 英文功能目录名

询问用户该功能的英文目录名（如 `formation`、`battle`、`guild`），用于输出目录命名。

用户不指定时，从文档标题/核心关键词中自动提取并翻译为英文（如「布阵」→ `formation`、「战斗」→ `battle`、「公会」→ `guild`）。

### 读取文档

读取文档内容。二进制格式用脚本提取：

**.docx：**
```bash
python -c "
from docx import Document
doc = Document(r'<路径>')
for p in doc.paragraphs:
    if p.text.strip(): print(p.text)
for t in doc.tables:
    for row in t.rows:
        print(' | '.join(c.text.strip() for c in row.cells))
"
```

**.xlsx：**
```bash
python -c "
from openpyxl import load_workbook
wb = load_workbook(r'<路径>', read_only=True, data_only=True)
for ws in wb.worksheets:
    for row in ws.iter_rows(values_only=True):
        cells = [str(c) for c in row if c is not None]
        if cells: print(' | '.join(cells))
wb.close()
"
```

**.md / .txt：** 直接用 Read 工具读取。

文件不存在则告知用户，让用户提供正确路径。

**确定输入目录：** 所有测试用例生成产物统一放在 `Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/` 目录下，其中 `{feature_en}` 为用户提供的英文功能名（小写、下划线分隔），`{seq4}` 为 4 位递增编号。默认永远扫描 `Doc/AI开发文档/input/{feature_en}-testcases/` 下已有 `{feature_en}-testcases-####` 目录，取最大编号 +1；只有用户明确要求复用/覆盖某个测试用例目录时，才允许写入已有目录。不得把测试用例生成产物写入 `Doc/AI开发文档` 根目录或 output 目录。

### 第 2 步：清洗文档

去除与功能测试无关的内容，详见 [references/test_point_spec.md §一](references/test_point_spec.md)：
- 跳过元信息章节（文档简介、版本历史、术语定义、目录等）
- 跳过已有测试要点表格（含"测试要点/CheckList/优先级"等表头的行）
- 跳过版本控制表格（含"密级/版权/文档编号/作者"等表头的行）
- 跳过独立标记（"版权所有"、"不得复制"）

### 第 3 步：提取模块列表（Map 阶段）

通读清洗后的文档，一次性提取所有功能模块和子功能点，详见 [references/test_point_spec.md §二](references/test_point_spec.md)。

输出 JSON 数组：`[{name: "模块名", sub_features: [{name: "子功能点名"}]}]`。每个子功能点粒度要细到能独立生成测试要点。

**在对话中展示提取结果：**
```
📦 识别到 X 个功能模块，Y 个子功能点：
  1. 模块A
     - 子功能点1
     - 子功能点2
  2. 模块B
     - 子功能点3
     ...
```

### 第 4 步：逐模块生成测试要点（Reduce 阶段）

对每个子功能点，按顺序执行：

**4a. 提取上下文：** 从文档中定位该子功能点对应的章节段落（从该标题到下一个同级或更高级标题之间的内容）。只用这一段生成，不要混入其他模块内容。提取内容过短（<50字）则尝试用父模块名提取；短文档（<12000字）可用全文但聚焦该模块。详见 [references/test_point_spec.md §二](references/test_point_spec.md)。

**4b. 确定覆盖维度：** 根据用户指定的游戏类型，参考 [references/test_point_spec.md §三](references/test_point_spec.md) 中的 8 个强制覆盖维度。支持：SLG、MMO、SIM（模拟经营）、TURN（回合制卡牌）、ROGUELIKE（肉鸽）、TOWER_DEF（塔防）。未指定默认 TOWER_DEF（推塔防，如齿轮滚滚）。

**4c. 穷举生成要点：** 严格遵循 [references/test_point_spec.md](references/test_point_spec.md) 全部规则：
- §四 字段定义 — 严格按格式填写，参考示例
- §五 Few-shot 示例 — 模仿示例的细致程度和完整性
- §六.1 穷举原则 — 每条规则、每个枚举值、每个状态、每个分支 → 至少一条要点
- §六.2 数值覆盖 — 0、最小值、最大值、最大值+1、负数
- §六.3 输入框覆盖 — 全部 11 种数据条件，每条单独一个 test_point
- §六.4 流程覆盖 — 每个关键步骤一条 + 网络断开 + 超时 + 并发冲突
- §六.5 生成顺序 — feature_point → sub_module → parent_point → test_point

**4d. 后处理修正：** 每个模块生成完后，逐条检查：
- `feature_point`：如果照搬了模块名或子功能点名，从 `parent_point` 中提取关键词替换
- `sub_module`：如果以"类"、"场景"结尾或超过 15 字，从 `parent_point` 中提取业务动作归纳
- `test_point`：去除末尾套话词（"正确性"、"准确性"、"有效性"、"是否合理"）

**在对话中展示测试要点：** 按模块分组，用 Markdown 表格展示。每个模块展示前 5 条要点，标注总数：
```
📝 模块「守卫营建造」— 共 X 个测试要点：
| 优先级 | 子模块 | 操作(parent_point) | 数据/条件(test_point) |
|--------|--------|---------------------|------------------------|
| P0 | 建造状态 | 大本营升级解锁守卫营 | 大本营恰好升至n级 |
| P0 | 建造状态 | 点击水下地块守卫营 | 守卫营处于水下状态 |
...
```

### 第 5 步：质量评估

按 [references/test_point_spec.md §九](references/test_point_spec.md) 四维度评分：
- 四个维度各占 25%
- 逐点检查：function_module ≥ 2 字、test_point ≥ 5 字、priority 有效性、无缺失/空字段

**在对话中展示评分结果：**
```
🔍 质量评估：
  覆盖率：0.XX | 准确性：0.XX | 可执行性：0.XX | 完整性：0.XX
  综合评分：0.XX
  问题：xxx（如有）
```

综合分 < 0.6 则回到第 4 步改进。

**保存测试要点 JSON：** 质量评估通过后，将测试要点数据保存为 JSON 文件：

```bash
python -c "
import json, os
data = <测试要点JSON数组>
dir = 'Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}'
os.makedirs(dir, exist_ok=True)
with open(f'{dir}/test_point_{feature_en}.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f'✅ 测试要点已保存: {dir}/test_point_{feature_en}.json')
"
```

### 第 6 步：生成测试用例

基于测试要点，逐条生成详细测试用例，详见 [references/test_case_spec.md](references/test_case_spec.md)：
- 每个要点至少 1 正向 + 1 异常；P0/P1 至少 2 正向
- 步骤具体到操作对象和操作内容
- 预期结果可量化验证

**保存测试用例 JSON：**

```bash
python -c "
import json, os
data = <测试用例JSON数组>
dir = 'Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}'
os.makedirs(dir, exist_ok=True)
with open(f'{dir}/test_case_{feature_en}.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f'✅ 测试用例已保存: {dir}/test_case_{feature_en}.json')
"
```

### 第 7 步：展示用例内容

**在对话中展示完整测试用例表格**，让用户直接看到结果，不要等到导出 Excel 才给。

用 Markdown 表格展示（至少展示前 20 条，如果总数超过 20 条则展示前 20 条 + 最后 5 条）：

```
| 用例ID | 模块 | 子模块 | 标题 | 优先级 | 类型 | 步骤(前2步) | 预期结果 |
|--------|------|--------|------|--------|------|-------------|----------|
| TC-xxx | ... | ... | ... | P0 | 正向 | 1.xxx 2.xxx | xxx |
```

如果用例太多，按模块分组展示每个模块的前 3 条。

### 第 8 步：导出 Excel 和 Markdown

运行导出脚本，一次性生成 Excel 和 Markdown 两份文档。脚本路径：`<skill目录>/scripts/export_test_cases.py`。

```bash
python "<skill目录>/scripts/export_test_cases.py" "Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.xlsx" "Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.json"
```

脚本自动生成三份文件：
- **测试要点 JSON**：`Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_point_{feature_en}.json`
- **测试用例 JSON**：`Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.json`
- **Excel**：`Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.xlsx` — 优先级列着色（P0 红 / P1 橙 / P2 黄 / P3 灰）、冻结首行、自动筛选、内置统计汇总
- **Markdown**：`Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.md` — 格式化的测试用例表格，可直接查看或提交到仓库

### 第 9 步：汇总统计

```
📊 生成完成！

文档：<文档名>
游戏类型：<类型>
功能目录：{feature_en}
测试要点：X 个（覆盖 Y 个模块 / Z 个子功能点）
测试用例：Y 条
综合质量：Z.Z（覆盖率 A / 准确性 B / 可执行性 C / 完整性 D）

优先级：P0:X P1:X P2:X P3:X
类型：正向 X | 异常 X | 边界 X

📥 输出文件：
  - Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_point_{feature_en}.json
  - Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.json
  - Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.xlsx
  - Doc/AI开发文档/input/{feature_en}-testcases/{feature_en}-testcases-{seq4}/test_case_{feature_en}.md
```

## 单独调用后的 JSON 上报

当用户直接调用 testcase-gen，而不是由 functiontest-workflow 编排时，生成测试用例并展示结果后，必须自动完成一次用量上报：

1. 调用 check-cyoucode-spend 读取当前 Token 和消耗。
2. 调用 functiontest-report-json 的 operation-only 模式，固定操作类型为“本地生成用例”，同时传入本轮已闭合的 timing 文件和 `--skill-name testcase-gen`，输出到本轮新的 operation 运行目录。
3. 调用 functiontest-json-upload 上传最终 JSON。

operation-only JSON 不读取测试报告，pass、failed、blocked、test_inconclusive、success_count、failure_count、bug_count 和 feature_count 等测试统计全部为 0，只写入操作类型、Token 和消耗数据。若 testcase-gen 是由 functiontest-workflow 调用，则不在此处重复上传，由主动测试工作流统一使用“主动测试工作流”上报。

示例输出路径：

```text
Doc/AI开发文档/output/{feature_en}/{feature_en}-operation-{seq4}/{feature_en}-operation-{seq4}-functiontest-upload.json
```

## 错误处理

| 情况 | 处理方式 |
|------|----------|
| 文件不存在 | 告知用户，让用户提供正确路径 |
| `ModuleNotFoundError: openpyxl` | 提示：`pip install openpyxl` |
| `ModuleNotFoundError: docx` | 提示：`pip install python-docx` |
| 文档内容过短（<100字） | 警告用户，继续处理 |
| 未能提取到任何模块 | 告知用户文档可能不含功能需求描述 |
| 质量评分 < 0.6 | 展示问题，询问用户是否重试或继续 |

## 资源文件

- `references/test_point_spec.md` — 文档清洗、Map-Reduce、游戏类型覆盖维度、字段定义、Few-shot 示例、穷举规则、后处理、质量评估
- `references/test_case_spec.md` — 测试用例字段、类型定义、命名规范、优先级分布
- `scripts/export_test_cases.py` — 测试用例 JSON 导出为带样式 Excel 和 Markdown
