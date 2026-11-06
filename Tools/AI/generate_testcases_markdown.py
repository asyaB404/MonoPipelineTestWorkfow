import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: str, content: str):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def normalize_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def markdown_cell(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


def alias_maps(alias_registry: dict) -> Dict[str, Dict[str, str]]:
    maps = alias_registry.get("maps", {})
    return {
        "requirement": maps.get("requirement_alias_map", {}),
        "image": maps.get("image_alias_map", {}),
        "element": maps.get("element_alias_map", {}),
        "text": maps.get("text_alias_map", {}),
    }


def resolve_evidence_ids(evidence_ids: List[str], maps: Dict[str, Dict[str, str]]) -> List[str]:
    resolved = []
    seen = set()
    for evidence_id in evidence_ids:
        token = evidence_id.strip()
        alias = token
        if token.startswith("REQ-") and token in maps["requirement"]:
            alias = maps["requirement"][token]
        elif token.startswith("IMG-") and token in maps["image"]:
            alias = maps["image"][token]
        elif token.startswith("ELE-") and token in maps["element"]:
            alias = maps["element"][token]
        elif token.startswith("TXT-") and token in maps["text"]:
            alias = maps["text"][token]

        if alias not in seen:
            seen.add(alias)
            resolved.append(alias)
    return resolved


def derive_image_summary(preprocess_summary: dict) -> Dict[str, str]:
    media_count = preprocess_summary.get("media_count", 0)
    linked_image_count = preprocess_summary.get("linked_image_count", 0)
    return {
        "image_total": str(media_count),
        "recognized_total": str(linked_image_count),
        "unrecognized_total": str(max(0, media_count - linked_image_count)),
        "image_source": "docx 内嵌图片" if media_count > 0 else "无",
        "compliance_summary": preprocess_summary.get(
            "compliance_summary",
            f"media_count = {media_count}，请确认测试步骤中已引用图片 alias/元素 alias。",
        ),
    }


def markdown_table(headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = [
        "| " + " | ".join(markdown_cell(item) for item in headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(item) for item in row) + " |")
    return lines


def render_scope(scope: dict) -> List[str]:
    return [
        "## 2. 测试范围",
        f"- 范围说明：{scope.get('description', '')}",
        f"- 重点关注：{scope.get('focus_areas', '')}",
        f"- 不在范围内：{scope.get('out_of_scope', '')}",
        "",
    ]


def render_evidence_index(alias_registry: dict) -> List[str]:
    lines = ["## 3. 需求依据索引", "", "### 3.1 文本依据", ""]

    req_rows = [
        [
            item.get("alias", ""),
            ", ".join(item.get("source_block_ids", [])),
            item.get("summary", ""),
        ]
        for item in alias_registry.get("requirements", [])
    ]
    if not req_rows:
        req_rows = [["-", "-", "-"]]
    lines.extend(markdown_table(["展示编号", "来源块", "内容摘要"], req_rows))

    lines.extend(["", "### 3.2 图片依据", ""])
    image_rows = [
        [
            item.get("alias", ""),
            item.get("image_path", ""),
            " / ".join(item.get("section_path", [])),
            item.get("caption", ""),
        ]
        for item in alias_registry.get("images", [])
    ]
    if not image_rows:
        image_rows = [["-", "-", "-", "-"]]
    lines.extend(markdown_table(["展示编号", "图片路径", "所属章节", "图注"], image_rows))

    lines.extend(["", "### 3.3 图片元素依据", ""])
    element_rows = [
        [
            item.get("alias", ""),
            item.get("image_alias", item.get("image_stable_id", "")),
            item.get("type", ""),
            item.get("visible_text", ""),
            item.get("location", ""),
            item.get("possible_action", ""),
        ]
        for item in alias_registry.get("elements", [])
    ]
    if not element_rows:
        element_rows = [["-", "-", "-", "-", "-", "-"]]
    lines.extend(
        markdown_table(
            ["展示编号", "所属图片", "类型", "可见文本", "位置", "可推断交互"],
            element_rows,
        )
    )
    lines.append("")
    return lines


def render_image_summary(summary: dict) -> List[str]:
    return [
        "## 4. 图片处理摘要",
        f"- 图片总数：{summary.get('image_total', '0')}",
        f"- 成功识别数：{summary.get('recognized_total', '0')}",
        f"- 未识别数：{summary.get('unrecognized_total', '0')}",
        f"- 图片来源：{summary.get('image_source', '')}",
        f"- 合规性结论：{summary.get('compliance_summary', '')}",
        "",
    ]


def render_overview(testcases: List[dict]) -> List[str]:
    type_counter = Counter(item.get("test_type", "unknown") for item in testcases)
    priority_counter = Counter(item.get("priority", "P3") for item in testcases)
    lines = ["## 5. 用例概览", "", "### 5.1 按类型统计", ""]
    lines.extend(markdown_table(["测试类型", "数量"], [[k, str(v)] for k, v in type_counter.items()]))
    lines.extend(["", "### 5.2 按优先级统计", ""])
    priority_order = ["P0", "P1", "P2", "P3"]
    priority_rows = [[key, str(priority_counter.get(key, 0))] for key in priority_order]
    lines.extend(markdown_table(["优先级", "数量"], priority_rows))
    lines.append("")
    return lines


def render_case(case: dict, maps: Dict[str, Dict[str, str]]) -> List[str]:
    lines = [
        f"#### [{case.get('id', 'TC-000')}] {case.get('title', '')}",
        f"**测试类型**：{case.get('test_type', 'functional')} | **优先级**：{case.get('priority', 'P2')}",
        "",
        "**前置条件**：",
    ]

    preconditions = normalize_list(case.get("preconditions"))
    if preconditions:
        lines.extend([f"- {item}" for item in preconditions])
    else:
        lines.append("- 无")

    lines.extend(["", "**测试步骤**：", "| 步骤 | 操作 | 预期结果 | 依据 |", "| --- | --- | --- | --- |"])
    for index, step in enumerate(case.get("steps", []), start=1):
        raw_evidence_ids = normalize_list(step.get("evidence_ids"))
        raw_evidence_ids.extend(normalize_list(step.get("stable_evidence_ids")))
        resolved_evidence = resolve_evidence_ids(raw_evidence_ids, maps)
        evidence_text = " / ".join(resolved_evidence) if resolved_evidence else "-"
        lines.append(
            f"| {step.get('step', index)} | {step.get('action', '')} | {step.get('expected', '')} | {evidence_text} |"
        )

    lines.extend(["", "**测试数据**："])
    test_data = normalize_list(case.get("test_data"))
    if test_data:
        lines.extend([f"- {item}" for item in test_data])
    else:
        lines.append("- 无")

    lines.extend(["", "**后置条件**："])
    postconditions = normalize_list(case.get("postconditions"))
    if postconditions:
        lines.extend([f"- {item}" for item in postconditions])
    else:
        lines.append("- 无")

    lines.extend(["", "---", ""])
    return lines


def render_testcases(testcases: List[dict], maps: Dict[str, Dict[str, str]]) -> List[str]:
    groups = defaultdict(list)
    group_titles = {
        "functional": "功能测试",
        "boundary": "边界测试",
        "error": "异常测试",
        "performance": "性能测试",
        "security": "安全测试",
    }
    for case in testcases:
        groups[case.get("test_type", "functional")].append(case)

    lines = ["## 6. 测试用例", ""]
    section_index = 1
    for key in ["functional", "boundary", "error", "performance", "security"]:
        cases = groups.get(key, [])
        if not cases:
            continue
        lines.append(f"### 6.{section_index} {group_titles.get(key, key)}")
        lines.append("")
        section_index += 1
        for case in cases:
            lines.extend(render_case(case, maps))
    return lines


def render_pending_items(items: List[dict]) -> List[str]:
    lines = ["", "## 7. 待确认项"]
    if not items:
        lines.append("")
        lines.append("无")
        return lines

    lines.append("")
    for index, item in enumerate(items, start=1):
        title = item.get("title", f"待确认项 {index}")
        description = item.get("description", "")
        basis_aliases = " / ".join(normalize_list(item.get("basis_aliases")))
        lines.append(f"{index}. **{title}**：")
        if description:
            lines.append(f"   - {description}")
        if basis_aliases:
            lines.append(f"   - 依据：{basis_aliases}")
        if item.get("recommendation"):
            lines.append(f"   - 建议：{item.get('recommendation')}")
        lines.append("")
    return lines


def has_image_evidence(testcases: List[dict], maps: Dict[str, Dict[str, str]]) -> bool:
    for case in testcases:
        for step in case.get("steps", []):
            raw_evidence_ids = normalize_list(step.get("evidence_ids"))
            raw_evidence_ids.extend(normalize_list(step.get("stable_evidence_ids")))
            resolved = resolve_evidence_ids(raw_evidence_ids, maps)
            if any(item.startswith("IMG-") or item.startswith("ELE-") for item in resolved):
                return True
    return False


def render_document(testcase_data: dict, alias_registry: dict, preprocess_summary: dict) -> str:
    maps = alias_maps(alias_registry)
    document_info = testcase_data.get("document_info", {})
    scope = testcase_data.get("test_scope", {})
    testcases = testcase_data.get("testcases", [])
    pending_items = testcase_data.get("pending_items", [])
    image_summary = derive_image_summary(preprocess_summary)

    lines = [
        "# 测试用例文档",
        "",
        "## 1. 文档信息",
        f"- 需求文档：{document_info.get('requirement_doc', '')}",
        f"- 生成日期：{document_info.get('generated_at', datetime.now().strftime('%Y-%m-%d'))}",
        f"- feature_id：{document_info.get('feature_id', '')}",
        f"- 用例总数：{len(testcases)}",
        "",
    ]
    lines.extend(render_scope(scope))
    lines.extend(render_evidence_index(alias_registry))
    lines.extend(render_image_summary(image_summary))
    lines.extend(render_overview(testcases))
    lines.extend(render_testcases(testcases, maps))
    lines.extend(render_pending_items(pending_items))
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--testcases-json", required=True, help="测试用例结构化输入 JSON")
    parser.add_argument("--alias-registry", required=True, help="evidence_alias_registry.json 路径")
    parser.add_argument("--preprocess-summary", required=True, help="preprocess_summary.json 路径")
    parser.add_argument("--output", required=True, help="输出 markdown 路径")
    args = parser.parse_args()

    testcase_data = load_json(args.testcases_json)
    alias_registry = load_json(args.alias_registry)
    preprocess_summary = load_json(args.preprocess_summary)
    maps = alias_maps(alias_registry)
    if preprocess_summary.get("media_count", 0) > 0 and not has_image_evidence(
        testcase_data.get("testcases", []), maps
    ):
        raise SystemExit("media_count > 0，但测试步骤中未引用任何 IMG-* / ELE-* alias，拒绝生成最终 markdown")

    markdown = render_document(testcase_data, alias_registry, preprocess_summary)
    save_text(args.output, markdown)

    output = json.dumps(
        {
            "output": args.output.replace("\\", "/"),
            "testcase_count": len(testcase_data.get("testcases", [])),
            "feature_id": testcase_data.get("document_info", {}).get("feature_id", ""),
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        print(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((output + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
