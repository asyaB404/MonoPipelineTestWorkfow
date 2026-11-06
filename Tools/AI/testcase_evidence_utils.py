import argparse
import json
import os
import sys
from typing import Dict, Iterable, List, Tuple


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def alias_index(prefix: str, index: int) -> str:
    return f"{prefix}-{index:03d}"


def unique_by_key(items: Iterable[dict], key: str) -> List[dict]:
    seen = set()
    result = []
    for item in items:
        value = item[key]
        if value in seen:
            continue
        seen.add(value)
        result.append(item)
    return result


def build_requirement_aliases(requirement_blocks: List[dict]) -> Tuple[List[dict], Dict[str, str]]:
    unique_items = unique_by_key(requirement_blocks, "stable_req_id")
    alias_rows = []
    alias_map: Dict[str, str] = {}

    for index, block in enumerate(unique_items, start=1):
        alias = alias_index("REQ", index)
        alias_map[block["stable_req_id"]] = alias
        alias_rows.append(
            {
                "alias": alias,
                "stable_id": block["stable_req_id"],
                "source_block_ids": [block["block_id"]],
                "section_path": block.get("section_path", []),
                "summary": block.get("normalized_text") or block.get("raw_text", ""),
            }
        )

    return alias_rows, alias_map


def build_image_aliases(image_index: List[dict]) -> Tuple[List[dict], Dict[str, str]]:
    alias_rows = []
    alias_map: Dict[str, str] = {}

    for index, image in enumerate(image_index, start=1):
        alias = image.get("display_image_id") or alias_index("IMG", index)
        alias_map[image["image_stable_id"]] = alias
        alias_rows.append(
            {
                "alias": alias,
                "stable_id": image["image_stable_id"],
                "image_path": image["image_path"],
                "section_path": image.get("section_path", []),
                "caption": image.get("caption", ""),
                "source_block_ids": image.get("source_block_ids", []),
            }
        )

    return alias_rows, alias_map


def build_element_aliases(image_analyses: List[dict]) -> Tuple[List[dict], Dict[str, str], Dict[str, str]]:
    element_rows = []
    element_map: Dict[str, str] = {}
    text_map: Dict[str, str] = {}

    element_counter = 1
    text_counter = 1
    for image in image_analyses:
        image_stable_id = image["image_stable_id"]
        stable_suffix = image_stable_id.split("IMG-", 1)[-1]

        for index, text in enumerate(image.get("ocr_texts", []), start=1):
            stable_id = text.get("stable_text_id") or f"TXT-{stable_suffix}-{index:03d}"
            alias = alias_index("TXT", text_counter)
            text_counter += 1
            text_map[stable_id] = alias
            element_rows.append(
                {
                    "kind": "text",
                    "alias": alias,
                    "stable_id": stable_id,
                    "image_stable_id": image_stable_id,
                    "type": text.get("role", "unknown"),
                    "name": text.get("text", ""),
                    "visible_text": text.get("text", ""),
                    "state": text.get("state", "unknown"),
                    "location": text.get("location", ""),
                    "possible_action": "none",
                }
            )

        for index, element in enumerate(image.get("elements", []), start=1):
            stable_id = element.get("stable_element_id") or f"ELE-{stable_suffix}-{index:03d}"
            alias = alias_index("ELE", element_counter)
            element_counter += 1
            element_map[stable_id] = alias
            element_rows.append(
                {
                    "kind": "element",
                    "alias": alias,
                    "stable_id": stable_id,
                    "image_stable_id": image_stable_id,
                    "type": element.get("type", "unknown"),
                    "name": element.get("name", ""),
                    "visible_text": element.get("visible_text", ""),
                    "state": element.get("state", "unknown"),
                    "location": element.get("location", ""),
                    "possible_action": element.get("possible_action", "unknown"),
                }
            )

    return element_rows, element_map, text_map


def render_markdown_index(
    requirement_aliases: List[dict],
    image_aliases: List[dict],
    element_aliases: List[dict],
) -> str:
    lines = ["## 需求依据索引", "", "### 文本依据", "", "| 展示编号 | stable_id | 来源块 | 内容摘要 |", "|---|---|---|---|"]
    for row in requirement_aliases:
        lines.append(
            f"| {row['alias']} | {row['stable_id']} | {', '.join(row['source_block_ids'])} | {row['summary']} |"
        )

    lines.extend(["", "### 图片依据", "", "| 展示编号 | stable_id | 图片路径 | 所属章节 | 图注 |", "|---|---|---|---|---|"])
    for row in image_aliases:
        lines.append(
            f"| {row['alias']} | {row['stable_id']} | {row['image_path']} | {' / '.join(row['section_path'])} | {row['caption']} |"
        )

    lines.extend(["", "### 图片元素依据", "", "| 展示编号 | stable_id | 所属图片stable_id | 类型 | 可见文本 | 位置 | 可推断交互 |", "|---|---|---|---|---|---|---|"])
    for row in element_aliases:
        lines.append(
            f"| {row['alias']} | {row['stable_id']} | {row['image_stable_id']} | {row['type']} | {row['visible_text']} | {row['location']} | {row['possible_action']} |"
        )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="Docx 预处理输出目录")
    parser.add_argument("--image-analysis", default="", help="可选：图片分析 JSON 文件路径")
    args = parser.parse_args()

    input_dir = args.input_dir
    requirement_blocks = load_json(os.path.join(input_dir, "requirement_blocks.json"))
    image_index = load_json(os.path.join(input_dir, "image_index.json"))

    requirement_aliases, requirement_map = build_requirement_aliases(requirement_blocks)
    image_aliases, image_map = build_image_aliases(image_index)

    element_aliases: List[dict] = []
    element_map: Dict[str, str] = {}
    text_map: Dict[str, str] = {}
    if args.image_analysis:
        image_analyses = load_json(args.image_analysis)
        element_aliases, element_map, text_map = build_element_aliases(image_analyses)

    alias_registry = {
        "schema_version": 1,
        "requirements": requirement_aliases,
        "images": image_aliases,
        "elements": element_aliases,
        "maps": {
            "requirement_alias_map": requirement_map,
            "image_alias_map": image_map,
            "element_alias_map": element_map,
            "text_alias_map": text_map,
        },
    }
    save_json(os.path.join(input_dir, "evidence_alias_registry.json"), alias_registry)

    markdown = render_markdown_index(requirement_aliases, image_aliases, element_aliases)
    with open(os.path.join(input_dir, "evidence_index.md"), "w", encoding="utf-8") as f:
        f.write(markdown)

    output = json.dumps({
        "alias_registry_path": os.path.join(input_dir, "evidence_alias_registry.json").replace("\\", "/"),
        "markdown_index_path": os.path.join(input_dir, "evidence_index.md").replace("\\", "/"),
        "requirement_alias_count": len(requirement_aliases),
        "image_alias_count": len(image_aliases),
        "element_alias_count": len(element_aliases),
    }, ensure_ascii=False, indent=2)
    try:
        print(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((output + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
