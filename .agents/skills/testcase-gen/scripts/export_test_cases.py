"""导出测试用例到 Excel 和 Markdown 文件

用法:
    python export_test_cases.py <output_path> <json_file>

output_path 为 xlsx 路径，脚本会自动在同目录生成同名的 .md 文件。

json_file 格式:
    [
      {
        "case_id": "TC-COM-001",
        "function_module": "战斗系统",
        "sub_module": "技能释放",
        "test_point": "验证技能冷却时间计算",
        "title": "[正向] 验证技能冷却时间正常倒计时",
        "priority": "P0",
        "risk_level": "HIGH",
        "execution_type": "POSITIVE",
        "preconditions": ["玩家已登录", "已学习技能A"],
        "steps": ["1. 释放技能A", "2. 观察冷却倒计时"],
        "expected": ["冷却倒计时正常显示", "倒计时结束后可再次释放"],
        "confidence": 0.95
      }
    ]

依赖: pip install openpyxl
"""
import json
import sys
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


HEADERS = [
    "用例ID", "功能模块", "子模块", "测试要点", "标题",
    "优先级", "风险等级", "类型", "前置条件", "步骤", "预期结果"
]

COL_WIDTHS = [24, 16, 14, 32, 35, 8, 10, 12, 25, 32, 32]


def load_test_cases(path: str) -> list:
    """从 JSON 文件加载测试用例数据"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def export_excel(test_cases: list, output_path: str) -> str:
    """将测试用例列表导出为 Excel 文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = "测试用例"

    # 样式
    hfont = Font(bold=True, color="FFFFFF", size=11)
    hfill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    halign = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    # 优先级颜色
    P_COLORS = {
        "P0": PatternFill(start_color="FFD7D7", end_color="FFD7D7", fill_type="solid"),
        "P1": PatternFill(start_color="FFE8CC", end_color="FFE8CC", fill_type="solid"),
        "P2": PatternFill(start_color="FFFDE6", end_color="FFFDE6", fill_type="solid"),
        "P3": PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid"),
    }

    # 表头
    for col, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = hfont
        cell.fill = hfill
        cell.alignment = halign
        cell.border = border

    # 数据行
    for row_idx, tc in enumerate(test_cases, 2):
        row_data = [
            tc.get("case_id", ""),
            tc.get("function_module", ""),
            tc.get("sub_module", ""),
            tc.get("test_point", ""),
            tc.get("title", ""),
            tc.get("priority", ""),
            tc.get("risk_level", ""),
            tc.get("execution_type", ""),
            _join(tc.get("preconditions", [])),
            _join(tc.get("steps", [])),
            _join(tc.get("expected", [])),
        ]
        priority_fill = P_COLORS.get(tc.get("priority", ""))
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if priority_fill and col == 6:  # 优先级列着色
                cell.fill = priority_fill

    # 列宽
    for i, width in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width

    # 冻结首行
    ws.freeze_panes = "A2"

    # 自动筛选
    ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=len(HEADERS)).column_letter}{len(test_cases) + 1}"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wb.save(output_path)

    _print_stats(test_cases, output_path)

    return output_path


def export_markdown(test_cases: list, output_path: str) -> str:
    """将测试用例列表导出为 Markdown 文件"""
    lines = []
    lines.append("# 测试用例")
    lines.append("")
    lines.append(f"共 {len(test_cases)} 条用例")
    lines.append("")

    # 统计摘要
    stats = _calc_stats(test_cases)
    lines.append("## 统计")
    lines.append("")
    lines.append(f"| 维度 | 分布 |")
    lines.append(f"|------|------|")
    lines.append(f"| 优先级 | P0:{stats.get('P0',0)} P1:{stats.get('P1',0)} P2:{stats.get('P2',0)} P3:{stats.get('P3',0)} |")
    lines.append(f"| 类型 | 正向:{stats.get('POSITIVE',0)} 异常:{stats.get('NEGATIVE',0)} 边界:{stats.get('BOUNDARY',0)} |")
    lines.append("")

    # 按模块分组
    modules = {}
    for tc in test_cases:
        mod = tc.get("function_module", "未分类")
        modules.setdefault(mod, []).append(tc)

    for mod_name, cases in modules.items():
        lines.append(f"## {mod_name}")
        lines.append("")
        lines.append(f"共 {len(cases)} 条用例")
        lines.append("")
        lines.append("| 用例ID | 子模块 | 标题 | 优先级 | 类型 | 步骤 | 预期结果 |")
        lines.append("|--------|--------|------|--------|------|------|----------|")
        for tc in cases:
            case_id = tc.get("case_id", "")
            sub_module = tc.get("sub_module", "")
            title = tc.get("title", "")
            priority = tc.get("priority", "")
            exec_type = tc.get("execution_type", "")
            steps = _join(tc.get("steps", [])).replace("\n", "<br>")
            expected = _join(tc.get("expected", [])).replace("\n", "<br>")
            lines.append(f"| {case_id} | {sub_module} | {title} | {priority} | {exec_type} | {steps} | {expected} |")
        lines.append("")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[OK] Markdown exported: {output_path}")
    return output_path


def _calc_stats(test_cases: list) -> dict:
    """计算统计信息"""
    stats = {"total": len(test_cases)}
    for tc in test_cases:
        p = tc.get("priority", "?")
        stats[p] = stats.get(p, 0) + 1
        t = tc.get("execution_type", "?")
        stats[t] = stats.get(t, 0) + 1
    return stats


def _print_stats(test_cases: list, output_path: str):
    """打印统计信息"""
    stats = _calc_stats(test_cases)
    print(f"[OK] Export done: {output_path}")
    print(f"   Total: {stats['total']} cases")
    print(f"   P0:{stats.get('P0',0)} P1:{stats.get('P1',0)} P2:{stats.get('P2',0)} P3:{stats.get('P3',0)}")
    print(f"   POSITIVE:{stats.get('POSITIVE',0)} NEGATIVE:{stats.get('NEGATIVE',0)} BOUNDARY:{stats.get('BOUNDARY',0)}")


def _join(items) -> str:
    """将列表转为换行分隔的字符串"""
    if not items:
        return ""
    if isinstance(items, list):
        return "\n".join(str(i) for i in items)
    return str(items)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python export_test_cases.py <output.xlsx> <test_cases.json>")
        sys.exit(1)

    output_path = sys.argv[1]
    json_path = sys.argv[2]

    if not os.path.exists(json_path):
        print(f"错误: JSON 文件不存在: {json_path}")
        sys.exit(1)

    test_cases = load_test_cases(json_path)

    # 导出 Excel
    export_excel(test_cases, output_path)

    # 导出 Markdown（同目录同名 .md）
    md_path = os.path.splitext(output_path)[0] + ".md"
    export_markdown(test_cases, md_path)