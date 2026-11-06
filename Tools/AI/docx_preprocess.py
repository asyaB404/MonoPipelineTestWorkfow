import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from typing import Dict, List

from lxml import etree


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class ImageCard:
    image_id: str
    image_stable_id: str
    display_image_id: str
    image_path: str
    rel_id: str
    image_target: str
    sha256: str
    paragraph_index: int
    section_path: List[str]
    nearby_heading: str
    caption: str
    before_text: str
    current_paragraph_text: str
    after_text: str
    source_block_ids: List[str]


@dataclass
class RequirementBlock:
    block_id: str
    stable_req_id: str
    paragraph_index: int
    section_path: List[str]
    raw_text: str
    normalized_text: str
    fingerprint: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    payload = "||".join(normalize_text(part) for part in parts if part)
    digest = sha256_bytes(payload.encode("utf-8"))[:8].upper()
    return f"{prefix}-{digest}"


def safe_mkdir(path: str):
    os.makedirs(path, exist_ok=True)


def read_xml(z: zipfile.ZipFile, path: str):
    if path not in z.namelist():
        return None
    return etree.fromstring(z.read(path))


def parse_rels(z: zipfile.ZipFile, rels_path: str) -> Dict[str, str]:
    result = {}

    if rels_path not in z.namelist():
        return result

    root = etree.fromstring(z.read(rels_path))
    for rel in root.xpath("//rel:Relationship", namespaces=NS):
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            result[rid] = target

    return result


def resolve_target(source_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    base_dir = posixpath.dirname(source_part)
    return posixpath.normpath(posixpath.join(base_dir, target))


def paragraph_text(p) -> str:
    texts = p.xpath(".//w:t/text()", namespaces=NS)
    return "".join(texts).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def paragraph_style(p) -> str:
    styles = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return styles[0] if styles else ""


def is_heading(style: str, text: str) -> bool:
    return heading_level(style, text) > 0


def heading_level(style: str, text: str) -> int:
    if not text:
        return 0

    s = style.lower() if style else ""
    match = re.search(r"heading\s*(\d+)", s)
    if match:
        return max(1, int(match.group(1)))

    if style and "标题" in style:
        match = re.search(r"(\d+)", style)
        return max(1, int(match.group(1))) if match else 1

    match = re.match(r"^(\d+(?:\.\d+)*)[、.\s]", text)
    if match:
        return len(match.group(1).split("."))

    if re.match(r"^[一二三四五六七八九十]+、", text):
        return 1

    return 0


def update_heading_stack(stack: List[str], level: int, text: str) -> List[str]:
    if level <= 0:
        return list(stack)

    if level <= 1:
        return [text]

    base = list(stack[: level - 1])
    while len(base) < level - 1:
        base.append("")

    return [item for item in (base + [text]) if item]


def is_caption(text: str) -> bool:
    if not text:
        return False

    t = text.strip().lower()
    return bool(
        re.match(r"^(图|figure|fig\.)\s*\d+", t, re.IGNORECASE)
        or re.match(r"^图\s*\d+[-－.]\d+", t)
    )


def image_rel_ids_in_paragraph(p) -> List[str]:
    rel_ids = []
    rel_ids.extend(p.xpath(".//a:blip/@r:embed", namespaces=NS))
    rel_ids.extend(p.xpath(".//v:imagedata/@r:id", namespaces=NS))

    seen = set()
    unique = []
    for rid in rel_ids:
        if rid not in seen:
            seen.add(rid)
            unique.append(rid)

    return unique


def context_text(paragraphs: List[str], idx: int, window: int = 2):
    before = [
        paragraphs[i]
        for i in range(max(0, idx - window), idx)
        if paragraphs[i].strip()
    ]
    after = [
        paragraphs[i]
        for i in range(idx + 1, min(len(paragraphs), idx + 1 + window))
        if paragraphs[i].strip()
    ]
    return "\n".join(before), "\n".join(after)


def find_caption(paragraphs: List[str], idx: int) -> str:
    for i in range(idx + 1, min(len(paragraphs), idx + 4)):
        if is_caption(paragraphs[i]):
            return paragraphs[i].strip()

    for i in range(max(0, idx - 2), idx):
        if is_caption(paragraphs[i]):
            return paragraphs[i].strip()

    return ""


def write_requirement_text(blocks: List[RequirementBlock], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for block in blocks:
            f.write(f"[{block.block_id}] {block.raw_text}\n\n")


def write_json(data, output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def nearby_block_ids(
    paragraph_to_block_id: Dict[int, str], idx: int, total_paragraphs: int, window: int = 2
) -> List[str]:
    ids = []
    for i in range(max(0, idx - window), min(total_paragraphs, idx + window + 1)):
        block_id = paragraph_to_block_id.get(i)
        if block_id and block_id not in ids:
            ids.append(block_id)
    return ids


def preprocess_docx(docx_path: str, output_dir: str):
    safe_mkdir(output_dir)

    images_dir = os.path.join(output_dir, "images")
    safe_mkdir(images_dir)

    image_cards_path = os.path.join(output_dir, "image_cards.json")
    image_index_path = os.path.join(output_dir, "image_index.json")
    requirement_text_path = os.path.join(output_dir, "requirement_text.md")
    requirement_blocks_path = os.path.join(output_dir, "requirement_blocks.json")
    evidence_registry_path = os.path.join(output_dir, "evidence_registry.json")
    summary_path = os.path.join(output_dir, "preprocess_summary.json")

    image_cards: List[ImageCard] = []
    requirement_blocks: List[RequirementBlock] = []
    paragraph_to_block_id: Dict[int, str] = {}

    with zipfile.ZipFile(docx_path, "r") as z:
        names = z.namelist()
        media_files = [name for name in names if name.startswith("word/media/")]

        document_part = "word/document.xml"
        rels_part = "word/_rels/document.xml.rels"

        root = read_xml(z, document_part)
        if root is None:
            raise RuntimeError("无法读取 word/document.xml，文档可能不是有效 docx")

        rels = parse_rels(z, rels_part)

        paragraphs_xml = root.xpath("//w:body//w:p", namespaces=NS)
        paragraphs = [paragraph_text(p) for p in paragraphs_xml]

        heading_stack: List[str] = []
        image_index = 0

        for idx, p in enumerate(paragraphs_xml):
            text = paragraphs[idx]
            normalized = normalize_text(text)
            style = paragraph_style(p)
            level = heading_level(style, text)

            if level > 0 and normalized:
                heading_stack = update_heading_stack(heading_stack, level, normalized)

            if not normalized:
                continue

            block_id = f"REQ-TEXT-{idx + 1:04d}"
            section_path = list(heading_stack)
            block = RequirementBlock(
                block_id=block_id,
                stable_req_id=stable_id(
                    "REQ",
                    json.dumps(section_path, ensure_ascii=False),
                    normalized,
                ),
                paragraph_index=idx,
                section_path=section_path,
                raw_text=text.strip(),
                normalized_text=normalized,
                fingerprint=sha256_bytes(normalized.encode("utf-8")),
            )
            requirement_blocks.append(block)
            paragraph_to_block_id[idx] = block_id

        write_requirement_text(requirement_blocks, requirement_text_path)

        heading_stack = []

        for idx, p in enumerate(paragraphs_xml):
            text = paragraphs[idx]
            style = paragraph_style(p)
            level = heading_level(style, text)
            if level > 0 and normalize_text(text):
                heading_stack = update_heading_stack(heading_stack, level, normalize_text(text))

            rel_ids = image_rel_ids_in_paragraph(p)
            if not rel_ids:
                continue

            for rel_id in rel_ids:
                target = rels.get(rel_id)
                if not target:
                    continue

                image_zip_path = resolve_target(document_part, target)
                if image_zip_path not in names:
                    continue

                image_bytes = z.read(image_zip_path)
                digest = sha256_bytes(image_bytes)

                ext = os.path.splitext(image_zip_path)[1] or ".bin"
                image_index += 1
                display_image_id = f"IMG-{image_index:03d}"
                image_stable_id = f"IMG-{digest[:8].upper()}"
                image_filename = f"{display_image_id}{ext}"
                image_output_path = os.path.join(images_dir, image_filename)

                with open(image_output_path, "wb") as f:
                    f.write(image_bytes)

                before, after = context_text(paragraphs, idx)
                caption = find_caption(paragraphs, idx)
                section_path = list(heading_stack)
                source_block_ids = nearby_block_ids(
                    paragraph_to_block_id, idx, len(paragraphs_xml)
                )

                image_cards.append(
                    ImageCard(
                        image_id=display_image_id,
                        image_stable_id=image_stable_id,
                        display_image_id=display_image_id,
                        image_path=image_output_path.replace("\\", "/"),
                        rel_id=rel_id,
                        image_target=image_zip_path,
                        sha256=digest,
                        paragraph_index=idx,
                        section_path=section_path,
                        nearby_heading=section_path[-1] if section_path else "",
                        caption=caption,
                        before_text=before,
                        current_paragraph_text=text,
                        after_text=after,
                        source_block_ids=source_block_ids,
                    )
                )

    requirement_block_dicts = [asdict(block) for block in requirement_blocks]
    image_card_dicts = [asdict(card) for card in image_cards]
    image_index = [
        {
            "image_stable_id": card.image_stable_id,
            "display_image_id": card.display_image_id,
            "legacy_image_id": card.image_id,
            "image_path": card.image_path,
            "sha256": card.sha256,
            "paragraph_index": card.paragraph_index,
            "section_path": card.section_path,
            "nearby_heading": card.nearby_heading,
            "caption": card.caption,
            "source_block_ids": card.source_block_ids,
        }
        for card in image_cards
    ]
    evidence_registry = {
        "schema_version": 1,
        "requirements": [
            {
                "stable_id": block.stable_req_id,
                "source_block_id": block.block_id,
                "paragraph_index": block.paragraph_index,
                "section_path": block.section_path,
                "text": block.raw_text,
            }
            for block in requirement_blocks
        ],
        "images": [
            {
                "stable_id": card.image_stable_id,
                "display_id": card.display_image_id,
                "image_path": card.image_path,
                "source_block_ids": card.source_block_ids,
                "sha256": card.sha256,
                "section_path": card.section_path,
            }
            for card in image_cards
        ],
    }

    write_json(requirement_block_dicts, requirement_blocks_path)
    write_json(image_card_dicts, image_cards_path)
    write_json(image_index, image_index_path)
    write_json(evidence_registry, evidence_registry_path)

    summary = {
        "docx_path": docx_path,
        "output_dir": output_dir,
        "stable_id_schema_version": 1,
        "text_paragraph_count": len([p for p in paragraphs if p.strip()]),
        "requirement_block_count": len(requirement_blocks),
        "media_count": len(media_files),
        "linked_image_count": len(image_cards),
        "requirement_text_path": requirement_text_path.replace("\\", "/"),
        "requirement_blocks_path": requirement_blocks_path.replace("\\", "/"),
        "image_cards_path": image_cards_path.replace("\\", "/"),
        "image_index_path": image_index_path.replace("\\", "/"),
        "evidence_registry_path": evidence_registry_path.replace("\\", "/"),
        "images_dir": images_dir.replace("\\", "/"),
        "compliance": {
            "has_media": len(media_files) > 0,
            "has_image_cards": len(image_cards) > 0,
            "has_requirement_blocks": len(requirement_blocks) > 0,
            "need_image_analysis": len(media_files) > 0,
        },
    }

    write_json(summary, summary_path)

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", required=True, help="输入 docx 路径")
    parser.add_argument("--out", required=True, help="输出目录")
    args = parser.parse_args()

    summary = preprocess_docx(args.docx, args.out)
    output = json.dumps(summary, ensure_ascii=False, indent=2)
    try:
        print(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((output + "\n").encode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()

