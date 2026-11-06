#!/usr/bin/env python3
"""
UI Quick Reference Scanner — 扫描指定功能单元的全部 UI 资源，生成快速参考图谱。

工作流：
1. 动态查找并解析 UILogicManager 文件 → 匹配 UIID / UIName / 描述
2. 扫描 Prefab 目录 → 提取节点层级树
3. 解析 AutoGen 文件 → 提取 CodeGen 字段 → 运行时节点名映射
4. 解析 Logic 文件 → 提取 Event_Register() 注册的回调映射
5. 生成本 skill references/{feature_id}.md

用法：
    python scan_ui_references.py <keyword> [--feature-id <id>] [--out-dir <path>]
        [--runtime-ui-id <id>] [--runtime-ui-name <name>] [--runtime-canvas-index <index>]

示例：
    python scan_ui_references.py 抽卡
    python scan_ui_references.py UI_DrawCard_Main --feature-id draw-card
"""

import argparse
import csv
import difflib
import os
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 路径常量（基于当前 Unity 工作区）
# ============================================================
# Skill 根目录从当前脚本位置推导，兼容不同 AI 的 skills 安装位置。
SKILLS_ROOT = Path(__file__).resolve().parents[2]
# 实际调用时可能从任意目录执行，用 cwd 查找项目根更可靠。
CWD = Path.cwd()

# UILogicManager 不绑定固定目录或扩展名；运行时从项目根动态查找。
UI_PREFAB_ROOT = Path("Assets/GameResource/UIResource/UIPrefab")
UI_LOGIC_ROOT = Path("Assets/Scripts/CyStarRoad/UILogic")
UI_QUICK_REF_TEMPLATE = SKILLS_ROOT / "unity-functiontest/references/ui-quick-ref-template.md"
# 本 skill 的输出目录
SKILL_REFERENCES = SKILLS_ROOT / "ui-quick-reference/references"

# 效果图路径解析只针对常见可直接读取的图片格式；不扫描 Unity 生成目录，
# 避免把缓存、构建产物或历史临时文件当成基准图候选。
EFFECT_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tga"}
EFFECT_IMAGE_IGNORED_DIRS = {
    ".git",
    ".svn",
    ".vs",
    "Library",
    "Temp",
    "Logs",
    "obj",
    "Build",
    "Builds",
    "node_modules",
}
FUZZY_MIN_EFFECT_SCORE = 0.56
FUZZY_TIE_EPSILON = 0.005

# 当前工作区由调用方给出；项目根仅在工作区、上一级、上两级中按常见目录名
# 评分确定。表格与效果图使用同一个项目根做最终模糊搜索，二者均不写入路径缓存。
UI_LOGIC_MANAGER_XLSX_NAME = "UILogicManager.xlsx"
UI_LOGIC_MANAGER_XLSX_STANDARD_RELATIVE = Path("Public/Tables/Excel/Client/UILogicManager.xlsx")
UI_LOGIC_MANAGER_XLSX_TEMP_RELATIVE = Path(
    "Public/Tables/_Tools/ExcelExporter_exe/_temp/Client/UILogicManager.xlsx"
)
FUZZY_MIN_UI_LOGIC_MANAGER_XLSX_SCORE = 0.70
PROJECT_ROOT_MARKERS = ("public", "art", "doc", "server")
PROJECT_ROOT_MARKER_MIN_SCORE = 0.72


# ============================================================
# 数据结构
# ============================================================
class UIEntry:
    """UILogicManager 文件中的一行条目"""
    def __init__(self, row: dict):
        self.id = row.get("ID", "")
        self.ui_name = row.get("UIName", "")
        self.ui_desc = row.get("UIDes", "")
        self.canvas_index = row.get("canvasIndex", "")
        self.open_close_list = row.get("open_close_List", "")
        self.ui_type = row.get("UIType", "")
        self.ui_perfect_path = str(row.get("UIPerfectPath") or "").strip()
        self.ui_perfect_path_field = "UIPerfectPath"

    @property
    def full_uiname(self) -> str:
        return self.ui_name

    @property
    def canvas_path(self) -> str:
        return f"Canvas{self.canvas_index}"

    @property
    def logic_fullname(self) -> str:
        return f"HotFix_Project.{self.ui_name}_Logic"

    @property
    def feature_id(self) -> str:
        """从 UIName 推断 feature_id（kebab-case）
        规则：UI_DrawCard_Main → draw-card
              UI_DrawCard_RatePreviewView → draw-card-rate-preview-view
        """
        name = self.ui_name
        if name.startswith("UI_"):
            name = name[3:]
        # 驼峰拆词：DrawCard → draw-card
        parts = name.split("_")
        result_parts = []
        for part in parts:
            sub = re.sub(r"([a-z])([A-Z])", r"\1-\2", part)
            sub = sub.lower()
            result_parts.append(sub)
        return "-".join(result_parts)


class AutoGenField:
    """AutoGen 文件中的一个绑定字段"""
    def __init__(self, field_name: str, comment: str, field_type: str, node_path_map: dict = None):
        self.field_name = field_name      # 字段名，如 btn_chouka1_0_btn
        self.comment = comment            # XML 注释内容，如 "抽卡按钮-单抽"
        self.field_type = field_type      # GameButton / GameText / GameImage / GameObject
        self.runtime_node_name = self._infer_runtime_name(node_path_map or {})

    def _infer_runtime_name(self, node_path_map: dict) -> str:
        """从字段名推断运行时节点名（以预制体根节点为起点的全路径）。

        规则：
        1. 去掉字段名末尾的 _{idx}_{type} 后缀得到节点名
        2. 在 prefab 节点路径映射中查找该节点名，获取完整路径
        3. 未找到时回退为节点名本身

        示例：
        - btn_baocun_1_4_btn → 节点名 btn_baocun_1 → 全路径 UI_Formation\\wanju_group\\btn_baocun_1
        """
        node_name = self.field_name
        # 去掉末尾的 _数字_类型后缀
        m = re.match(r"^(.+?)_\d+_(btn|txt|img|go|com)$", self.field_name)
        if m:
            node_name = m.group(1)
        else:
            # 去掉末尾的 _数字_数字_类型后缀
            m = re.match(r"^(.+?)_\d+_\d+_(btn|txt|img|go|com)$", self.field_name)
            if m:
                node_name = m.group(1)
            else:
                # 去掉末尾的 _数字后缀
                m = re.match(r"^(.+?)_\d+$", self.field_name)
                if m:
                    node_name = m.group(1)
        # 查 prefab 路径映射，获取完整路径
        return node_path_map.get(node_name, node_name)

    @property
    def type_label(self) -> str:
        return {
            "GameButton": "GameButton",
            "GameText": "GameText",
            "GameImage": "GameImage",
            "GameObject": "GameObject",
            "GameToggle": "GameToggle",
            "GameInputField": "GameInputField",
            "UIComList": "UIComList",
        }.get(self.field_type, self.field_type)

    @property
    def is_button(self) -> bool:
        return self.field_type == "GameButton"


class LogicCallback:
    """Logic 文件中 Event_Register() 注册的回调"""
    def __init__(self, auto_gen_field: str, runtime_node: str, callback_method: str):
        self.auto_gen_field = auto_gen_field
        self.runtime_node = runtime_node
        self.callback_method = callback_method


@dataclass(frozen=True)
class _EffectImageIndexEntry:
    """图片索引中的一条候选；索引只存在于当前 Python 进程。"""

    path: Path
    source: str
    root_priority: int
    relative_path: str


@dataclass(frozen=True)
class _EffectImageMatch:
    """模糊匹配候选及其可解释的排序信息。"""

    entry: _EffectImageIndexEntry
    score: float
    stem_similarity: float
    path_suffix_matches: int
    extra_stem_length: int


@dataclass
class EffectPathResolution:
    """效果图路径解析结果；保留旧的 ``(status, path)`` 调用兼容层。"""

    status: str
    display_path: str = ""
    absolute_path: str = ""
    path_source: str = ""
    match_mode: str = ""
    confidence: float = 0.0
    candidates: List[str] = dataclass_field(default_factory=list)
    reason: str = ""


# ============================================================
# 解析器
# ============================================================
class UILogicManagerParser:
    """解析 UILogicManager 文件的 TSV 表格"""

    def __init__(self, filepath: Optional[Path]):
        self.filepath = filepath
        self.entries: List[UIEntry] = []
        self._parse()

    def _parse(self):
        if self.filepath is None:
            return
        if not self.filepath.exists():
            print(f"[WARN] UILogicManager not found: {self.filepath}")
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                # 跳过前 5 行表头（index1/index2 等）
                lines = [l for l in f.readlines() if l.strip()]
                # 找到真正的数据行（从第 6 行开始）
                data_lines = [l for l in lines if l.strip() and not l.startswith("ID\t") and not l.startswith("int\t") and not l.startswith("index") and not l.strip().startswith("c/s")]
                # 第 1 行是列名
                header = ["ID", "UIName", "UIDes", "canvasIndex", "open_close_List", "Top_AudioId", "UIType", "HasInAnimation", "HasOutAnimation", "AudioEffect", "IsPrefab2Cache"]
                reader = csv.DictReader(data_lines, fieldnames=header, delimiter="\t", quoting=csv.QUOTE_NONE)
                for row in reader:
                    if row["ID"] and row["ID"].isdigit():
                        self.entries.append(UIEntry(row))
        except (UnicodeDecodeError, OSError) as exc:
            print(f"[WARN] UILogicManager 候选文件不可按当前文本格式解析，跳过: {self.filepath} ({exc.__class__.__name__})")

    def find_by_keyword(self, keyword: str) -> List[UIEntry]:
        """按关键字匹配 UIName 或 UIDes"""
        kw = keyword.lower()
        results = []
        for e in self.entries:
            if kw in e.ui_name.lower() or kw in e.ui_desc.lower():
                results.append(e)
        return results

    def find_by_uiname(self, uiname: str) -> Optional[UIEntry]:
        """精确匹配 UIName"""
        for e in self.entries:
            if e.ui_name == uiname:
                return e
        return None


class UILogicManagerXlsxParser:
    """读取表格项目根目录下 UILogicManager.xlsx 的 UIName → 效果图路径映射。

    这里只使用 Python 标准库解析 xlsx zip/xml，避免依赖项目环境中的 Excel
    或第三方库。解析失败时由调用方记录为配置缺失，不能影响普通 UI reference。
    """

    XML_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    EFFECT_PATH_FIELDS = ("UIPerfectPath",)

    def __init__(self, filepath: Optional[Path]):
        self.filepath = filepath
        self.entries: Dict[str, UIEntry] = {}
        self.effect_path_field = ""
        self.parse_error = ""
        self._parse()

    @staticmethod
    def _column_index(cell_ref: str) -> int:
        letters = re.match(r"([A-Za-z]+)", cell_ref or "")
        if not letters:
            return -1
        index = 0
        for char in letters.group(1).upper():
            index = index * 26 + ord(char) - ord("A") + 1
        return index - 1

    @staticmethod
    def _shared_strings(archive: zipfile.ZipFile) -> List[str]:
        try:
            raw = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        root = ET.fromstring(raw)
        values = []
        for item in root.findall("m:si", UILogicManagerXlsxParser.XML_NS):
            values.append("".join(node.text or "" for node in item.iter() if node.tag.endswith("}t") or node.tag == "t"))
        return values

    @staticmethod
    def _cell_value(cell: ET.Element, shared_strings: List[str]) -> str:
        cell_type = cell.attrib.get("t", "")
        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell.iter() if node.tag.endswith("}t") or node.tag == "t")
        value_node = cell.find("m:v", UILogicManagerXlsxParser.XML_NS)
        value = "" if value_node is None or value_node.text is None else value_node.text
        if cell_type == "s":
            try:
                return shared_strings[int(value)]
            except (ValueError, IndexError):
                return ""
        return value

    def _parse(self) -> None:
        if self.filepath is None or not self.filepath.exists():
            return
        try:
            with zipfile.ZipFile(self.filepath) as archive:
                shared_strings = self._shared_strings(archive)
                sheet_names = sorted(
                    name for name in archive.namelist()
                    if name.startswith("xl/worksheets/") and name.endswith(".xml")
                )
                for sheet_name in sheet_names:
                    root = ET.fromstring(archive.read(sheet_name))
                    rows = []
                    for row in root.findall(".//m:row", self.XML_NS):
                        values = {}
                        for cell in row.findall("m:c", self.XML_NS):
                            index = self._column_index(cell.attrib.get("r", ""))
                            if index >= 0:
                                values[index] = self._cell_value(cell, shared_strings).strip()
                        rows.append(values)

                    header_index = None
                    header: Dict[str, int] = {}
                    for index, values in enumerate(rows):
                        by_name = {value: column for column, value in values.items() if value}
                        effect_field = next(
                            (field for field in self.EFFECT_PATH_FIELDS if field in by_name),
                            None,
                        )
                        if "UIName" in by_name and effect_field:
                            header_index = index
                            header = by_name
                            self.effect_path_field = effect_field
                            break
                    if header_index is None:
                        continue

                    for values in rows[header_index + 1:]:
                        ui_name = values.get(header.get("UIName", -1), "").strip()
                        record_id = values.get(header.get("ID", -1), "").strip()
                        if not ui_name or not record_id.isdigit():
                            continue
                        path_value = values.get(header.get(self.effect_path_field, -1), "").strip()
                        row = {
                            "ID": record_id,
                            "UIName": ui_name,
                            "UIDes": values.get(header.get("UIDes", -1), ""),
                            "canvasIndex": values.get(header.get("canvasIndex", -1), ""),
                            self.effect_path_field: path_value,
                        }
                        self.entries[ui_name] = UIEntry(row)
                    if self.entries:
                        return
        except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
            self.parse_error = f"{exc.__class__.__name__}: {exc}"

    def find_by_uiname(self, uiname: str) -> Optional[UIEntry]:
        return self.entries.get(uiname)


def build_runtime_entry(args) -> Optional[UIEntry]:
    """用 Unity 运行时读取结果构造一条 UI 配表记录。

    `.bytes` 是加密二进制表，Python 文本解析器无法直接读取。Skill 编排层
    先通过 Unity TableManager/TableUILogicManager 取得目标 UI 的字段，再以
    命令行参数传入这里，避免在 Python 中重复实现项目的解密和反序列化。
    """
    if not any(
        value is not None
        for value in (args.runtime_ui_id, args.runtime_ui_name, args.runtime_canvas_index)
    ):
        return None

    if not args.runtime_ui_name:
        print("[ERROR] 使用 Unity 运行时字段时必须提供 --runtime-ui-name")
        sys.exit(2)

    return UIEntry({
        "ID": str(args.runtime_ui_id or "unknown"),
        "UIName": args.runtime_ui_name,
        "UIDes": args.runtime_ui_desc or "",
        "canvasIndex": str(args.runtime_canvas_index if args.runtime_canvas_index is not None else "unknown"),
        "open_close_List": args.runtime_open_close_list or "",
        "UIType": args.runtime_ui_type or "",
    })

    def find_by_id(self, uid: str) -> Optional[UIEntry]:
        for e in self.entries:
            if e.id == uid:
                return e
        return None


class AutoGenParser:
    """解析 AutoGen 文件，提取绑定字段"""

    def __init__(self, filepath: Path, node_path_map: dict = None):
        self.filepath = filepath
        self.fields: List[AutoGenField] = []
        self._node_path_map = node_path_map or {}
        self._parse()

    def _parse(self):
        if not self.filepath.exists():
            print(f"[WARN] AutoGen not found: {self.filepath}")
            return
        content = self.filepath.read_text(encoding="utf-8")
        # 逐行解析
        lines = content.split("\n")
        current_comment = ""
        in_summary = False
        for i, line in enumerate(lines):
            # 捕获 XML 注释：支持单行 <summary>xxx</summary> 与跨行 /// 形式
            # 跨行形式： /// <summary>  →  /// 内容  →  /// </summary>
            stripped = line.strip()
            if stripped.startswith("///"):
                inner = stripped.lstrip("/").strip()
                if "<summary>" in inner and "</summary>" in inner:
                    # 单行完整注释
                    m = re.search(r"<summary>\s*(.*?)\s*</summary>", inner)
                    current_comment = m.group(1).strip() if m else ""
                    continue
                if "<summary>" in inner:
                    in_summary = True
                    # 遇到新的 <summary>，先重置注释
                    current_comment = ""
                    # 处理 <summary> 同行有内容的情况
                    after = inner.replace("<summary>", "", 1).strip()
                    if after:
                        current_comment = after
                    continue
                if "</summary>" in inner:
                    # 结束，保留已累积内容
                    before = inner.replace("</summary>", "", 1).strip()
                    if before:
                        current_comment = (current_comment + " " + before).strip() if current_comment else before
                    in_summary = False
                    continue
                # summary 中间的内容行
                if in_summary and inner:
                    current_comment = (current_comment + " " + inner).strip() if current_comment else inner
                    continue

            # 检测字段声明（含滚动列表等通用组件）
            field_match = re.match(
                r"\s*public\s+(GameButton|GameText|GameImage|GameObject|GameToggle|GameInputField|GameScrollRect_V2)\s+(\w+)\s*;",
                line,
            )
            if field_match:
                field_type = field_match.group(1)
                field_name = field_match.group(2)
                # 忽略 UIComList 类型的集合字段
                if field_name.startswith("commonResource_Logic"):
                    current_comment = ""
                    continue
                self.fields.append(
                    AutoGenField(field_name, current_comment, field_type, self._node_path_map)
                )
                current_comment = ""


class LogicParser:
    """解析 Logic 和关联文件，提取 Event_Register 回调和方法。

    扫描策略：
    1. 优先读取 _Logic.cs 主文件
    2. 同时扫描同目录下所有 .cs 文件（如 _Pairs.cs），合并 onClick 绑定
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath        # _Logic.cs 主文件路径
        self.callbacks: List[Tuple[str, str]] = []  # (auto_gen_field, callback_method)
        self.key_fields: List[Tuple[str, str, str]] = []  # (field_name, type_hint, usage)
        self._parse()

    def _parse(self):
        # 合并所有同目录 .cs 文件内容
        all_content = ""
        main_content = ""
        if self.filepath.exists():
            main_content = self.filepath.read_text(encoding="utf-8")
            all_content = main_content
        # 扫描同目录下其他 .cs 文件
        logic_dir = self.filepath.parent
        if logic_dir.exists():
            for cs_file in sorted(logic_dir.glob("*.cs")):
                if cs_file.name == self.filepath.name:
                    continue
                all_content += "\n" + cs_file.read_text(encoding="utf-8")

        if not self.filepath.exists():
            print(f"[WARN] Logic not found: {self.filepath}")
            # 即使主文件不存在，也尝试扫描其他文件
            if not all_content:
                return

        # 提取 onClick 绑定：扫描所有 .cs 文件的全部内容
        # 匹配模式：field.onClick = () => { ... }; 或 field.onClick = _delegate.Method;
        for m in re.finditer(
            r"(\w+)\s*\.\s*onClick\s*=\s*(?:\(\)\s*=>\s*(\{[^{}]*\}|[^;]+)|([^;]+));",
            all_content,
            re.DOTALL,
        ):
            field_name = m.group(1)
            body = (m.group(2) or m.group(3) or "").strip()
            method_name = self._extract_first_call(body)
            if method_name and not any(c[0] == field_name for c in self.callbacks):
                self.callbacks.append((field_name, method_name))

        # 提取关键字段（仅从主 Logic 文件）
        self._extract_key_fields(main_content)

    def _extract_first_call(self, body: str) -> str:
        """从 onClick 赋值右侧提取回调方法名，用于回调速查。

        支持格式：
        - `() => { Method(); }` → Method
        - `_close.OnClickClose` → _close.OnClickClose（委托赋值）
        - `_network.SaveBattleSetting` → _network.SaveBattleSetting
        - `() => _filter.SetToyCampFilter(...)` → _filter.SetToyCampFilter

        返回值不含尾部括号。
        """
        b = body.strip()
        if b.startswith("{") and b.endswith("}"):
            b = b[1:-1].strip()
        # 跳过 if 关键字行
        # 优先匹配本地方法调用：Method();
        m = re.search(r"\b([A-Za-z_]\w*)\s*\(\s*\)", b)
        if m and m.group(1) not in ("if", "else", "for", "while", "switch", "return"):
            return m.group(1)
        # 匹配 X.Inst.Y() 或 X.Inst.Y(args)
        m = re.search(r"(\w+)\.Inst\.(\w+)\s*\(", b)
        if m:
            return f"{m.group(1)}.Inst.{m.group(2)}"
        # 匹配 X.Inst.xxx 属性/字段访问
        m = re.search(r"(\w+)\.Inst\.(\w+)", b)
        if m:
            return f"{m.group(1)}.Inst.{m.group(2)}"
        # 匹配 Class.Method() 调用
        m = re.search(r"(\w+)\.(\w+)\s*\(", b)
        if m and m.group(1) not in ("if", "else"):
            return f"{m.group(1)}.{m.group(2)}"
        # 匹配委托赋值：_close.OnClickClose / _network.SaveBattleSetting
        m = re.search(r"(_?\w+)\.(\w+)$", b)
        if m and m.group(1) not in ("if", "else"):
            return f"{m.group(1)}.{m.group(2)}"
        # 匹配直接方法委托：button.onClick = OnClickOk;
        m = re.fullmatch(r"([A-Za-z_]\w*)", b)
        if m and m.group(1) not in ("if", "else", "return"):
            return m.group(1)
        return ""

    def _extract_key_fields(self, content: str):
        """提取关键字段（类成员字段定义）
        仅匹配类体顶层、带 private/public/protected 修饰符的字段，
        或在 #region 字段定义 区块内、行首缩进为类成员级别的无修饰符字段。
        排除方法内局部变量、using 别名、return 语句等。
        """
        # 限定在「字段定义」region 内提取，避免误匹配方法体局部变量
        # 匹配 #region ===== 字段 ... 到 #endregion
        field_region_match = re.search(
            r"#region\s+=====.*?字段.*?====.*?#\s*endregion",
            content,
            re.DOTALL,
        )
        region_content = field_region_match.group(0) if field_region_match else content

        # 匹配带 private/public/protected 修饰符的字段（含 static）
        for m in re.finditer(
            r"^\s*(?:private|public|protected)\s+(?:static\s+|readonly\s+)*(\w+(?:<[^>]+>)?)\s+(_?\w+)\s*(?:=|;)",
            region_content,
            re.MULTILINE,
        ):
            field_type = m.group(1)
            field_name = m.group(2)
            # 忽略常见系统字段
            if field_name.startswith("m_") and field_name in ("m_IsOpen", "m_IsHidden"):
                continue
            self.key_fields.append((field_name, field_type, ""))

        # 匹配无修饰符的实例字段（如 int nCurNoticeState = 1;）
        # 仅在字段 region 内、行首为类成员缩进（2 个 tab 或 8 空格）的字段
        for m in re.finditer(
            r"^\t\t(int|bool|string|float|long|double|List<\w+>|Dictionary<[^>]+>|\w+)\s+(\w+)\s*(?:=|;)",
            region_content,
            re.MULTILINE,
        ):
            field_type = m.group(1)
            field_name = m.group(2)
            # 去重
            if any(kf[0] == field_name for kf in self.key_fields):
                continue
            # 排除 using 别名（如 using Random = UnityEngine.Random）
            if field_type in ("using", "var", "return"):
                continue
            self.key_fields.append((field_name, field_type, ""))

    def get_method_body(self, method_name: str, content: str = "") -> str:
        """获取指定方法的方法体摘要"""
        if not content:
            content = self.filepath.read_text(encoding="utf-8")
        # 匹配 private void MethodName() { ... }
        pattern = re.compile(
            rf"private\s+\w+\s+{re.escape(method_name)}\s*\([^)]*\)\s*\{{",
            re.DOTALL,
        )
        m = pattern.search(content)
        if not m:
            return ""
        start = m.start()
        # 找到匹配的闭合括号
        brace_count = 0
        in_brace = False
        for i in range(start, len(content)):
            if content[i] == "{":
                brace_count += 1
                in_brace = True
            elif content[i] == "}":
                brace_count -= 1
                if in_brace and brace_count == 0:
                    body = content[start : i + 1]
                    # 截取前 200 字符
                    if len(body) > 200:
                        body = body[:200] + "..."
                    return body
        return ""


# ============================================================
# Prefab 扫描
# ============================================================
class PrefabScanner:
    """扫描 Prefab 目录，解析 YAML 提取节点层级树与完整路径"""

    def __init__(self, prefab_dir: Path):
        self.prefab_dir = prefab_dir
        self.prefab_file: Optional[Path] = None
        # node_name → 从预制体根节点开始的完整路径（用 \ 分隔）
        self.node_path_map: dict = {}
        self._root_name: str = ""
        self._find_prefab()
        if self.prefab_file and self.prefab_file.exists():
            self._parse_yaml_hierarchy()

    def _find_prefab(self):
        """找到主 prefab 文件"""
        if not self.prefab_dir.exists():
            return
        # 找 Prefab 子目录下的 prefab
        prefab_subdir = self.prefab_dir / "Prefab"
        if prefab_subdir.exists():
            for f in prefab_subdir.iterdir():
                if f.suffix == ".prefab" and not f.name.endswith(".meta"):
                    self.prefab_file = f
                    return
        # 直接找 .prefab
        for f in self.prefab_dir.iterdir():
            if f.suffix == ".prefab" and not f.name.endswith(".meta"):
                self.prefab_file = f
                return

    def _parse_yaml_hierarchy(self):
        """解析 Unity YAML prefab，构建 node_name → full_path 映射。

        Unity prefab YAML 结构：
        - GameObject 文档：包含 m_Name（节点名），锚点 fileID 为 GameObject ID
        - RectTransform/Transform 文档：包含 m_GameObject（指向 GameObject）、
          m_Father（指向父 Transform，根节点为 0）、m_Children（子 Transform 列表）

        解析策略：
        1. 扫描所有 YAML 文档，建立 go_id→name、tf_id→(go_id, parent_tf_id, children[])
        2. 找到根 Transform（m_Father==0），DFS 构建完整路径
        """
        if not self.prefab_file or not self.prefab_file.exists():
            return
        content = self.prefab_file.read_text(encoding="utf-8")
        # 按 YAML 文档分隔符拆分
        docs = content.split("\n--- ")
        # 第一个文档的 '--- ' 前缀处理
        if docs and docs[0].startswith("--- "):
            docs[0] = docs[0][4:]

        go_name_map: dict = {}       # GameObject fileID → m_Name
        tf_info_map: dict = {}       # Transform fileID → (go_fileID, parent_tf_fileID)

        for doc in docs:
            doc = doc.strip()
            if not doc:
                continue
            # 提取锚点 fileID：!u!1 &123456789 或 !u!224 &123456789
            anchor_match = re.match(r"!u!\d+\s+&(\d+)", doc)
            if not anchor_match:
                continue
            file_id = anchor_match.group(1)

            # 提取 m_Name（GameObject 文档）
            name_match = re.search(r"m_Name:\s*(.+)", doc)
            go_name = name_match.group(1).strip() if name_match else ""

            # 提取 m_GameObject 引用（Transform 文档）
            go_ref_match = re.search(r"m_GameObject:\s*\{fileID:\s*(\d+)\}", doc)
            go_ref = go_ref_match.group(1) if go_ref_match else ""

            # 提取 m_Father 引用（Transform 文档）
            father_match = re.search(r"m_Father:\s*\{fileID:\s*(\d+)\}", doc)
            father_ref = father_match.group(1) if father_match else ""

            if go_name:
                go_name_map[file_id] = go_name
            if go_ref:
                tf_info_map[file_id] = (go_ref, father_ref)

        if not go_name_map or not tf_info_map:
            return

        # 构建 Transform 父子关系：parent_tf_id → [child_tf_id, ...]
        children_map: dict = {}
        root_tf_id = ""
        for tf_id, (go_id, parent_id) in tf_info_map.items():
            if parent_id == "0":
                root_tf_id = tf_id
            else:
                children_map.setdefault(parent_id, []).append(tf_id)

        if not root_tf_id:
            return

        # 构建 go_id → tf_id 反向映射
        go_to_tf: dict = {}
        for tf_id, (go_id, _) in tf_info_map.items():
            go_to_tf[go_id] = tf_id

        # DFS 构建完整路径
        def dfs(tf_id: str, parent_path: str):
            go_id = tf_info_map.get(tf_id, ("", ""))[0]
            if go_id not in go_name_map:
                return
            name = go_name_map[go_id]
            current_path = f"{parent_path}\\{name}" if parent_path else name
            self.node_path_map[name] = current_path
            for child_tf in children_map.get(tf_id, []):
                dfs(child_tf, current_path)

        root_go_id = tf_info_map[root_tf_id][0]
        self._root_name = go_name_map.get(root_go_id, "")
        dfs(root_tf_id, "")

    def extract_node_tree(self) -> str:
        """从 prefab 提取节点树摘要"""
        if not self.prefab_file or not self.prefab_file.exists():
            return "# Prefab 文件未找到\n"
        lines = [f"# Prefab: {self.prefab_file.name}"]
        if self._root_name:
            lines.append(f"# 根节点: {self._root_name}")
        lines.append(f"# 节点总数: {len(self.node_path_map)}")
        if self.node_path_map:
            lines.append("# 完整节点树需在 Unity 中用 capture_scene_snapshot 获取")
            lines.append("# 以下为关键路径示例（仅展示 AutoGen 绑定节点）：")
        return "\n".join(lines) + "\n"

    def get_node_path(self, node_name: str) -> str:
        """根据节点名查找从预制体根节点开始的完整路径。

        Args:
            node_name: 运行时节点名（如 btn_baocun_1）

        Returns:
            完整路径（如 UI_Formation\\wanju_group\\btn_baocun_1），
            未找到时返回 node_name 本身
        """
        return self.node_path_map.get(node_name, node_name)


# ============================================================
# 文档生成器
# ============================================================
class ReferenceDocGenerator:
    """生成快速参考文档"""

    def __init__(self, ui_entry: UIEntry, feature_id: str):
        self.ui_entry = ui_entry
        self.feature_id = feature_id
        self.sub_uis: List[UIEntry] = []
        self.auto_gen_fields: List[AutoGenField] = []
        self.logic_callbacks: List[Tuple[str, str]] = []  # (auto_gen_field, callback_method)
        self.key_fields: List[Tuple[str, str, str]] = []
        self.prefab_info: str = ""
        self.logic_methods: List[Tuple[str, str]] = []  # (method_name, body_summary)

    def _get_callback_for_field(self, auto_gen_field_name: str) -> str:
        """根据 AutoGen 字段名查找对应的回调方法名。

        Args:
            auto_gen_field_name: AutoGen 字段名（如 btn_baocun_1_4_btn）

        Returns:
            回调方法名（不含括号），未找到时返回空字符串
        """
        for field_name, method_name in self.logic_callbacks:
            if field_name == auto_gen_field_name:
                return method_name
        return ""

    def generate(self, existing_content: str = "") -> str:
        """生成参考文档，如果已有内容则增量更新"""
        lines = []
        lines.append(f"# {self.feature_id} - UI 快速参考")
        lines.append("")

        # ===== 基本信息 =====
        lines.append("## 1. 基本信息")
        lines.append("")
        ui = self.ui_entry
        lines.append("| 属性 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| feature_id | `{self.feature_id}` |")
        lines.append(f"| UIID | `{ui.ui_name}` |")
        lines.append(f"| UIDes | {ui.ui_desc} |")
        lines.append(f"| CanvasIndex | {ui.canvas_index} |")
        lines.append(f"| UI 根节点名 | `{ui.ui_name}` |")
        lines.append(f"| 完整场景路径 | `GameEntry/Builtin/UI/AdapterArea/{ui.canvas_path}/{ui.ui_name}` |")
        lines.append(f"| Logic 全限定名 | `{ui.logic_fullname}` |")
        lines.append(f"| Assembly | 遍历 AppDomain 获取（非固定名） |")
        lines.append(f"| UIID 常量 | `UIID.{ui.ui_name}`（见 Gen/Table/UIID.cs） |")
        if self.sub_uis:
            lines.append("")
            lines.append("### 子 UI")
            lines.append("")
            lines.append("| UIID | 用途 | Canvas |")
            lines.append("|------|------|--------|")
            for sub in self.sub_uis:
                lines.append(f"| `{sub.ui_name}` | {sub.ui_desc} | {sub.canvas_index} |")

        # ===== 进场流程 =====
        lines.append("")
        lines.append("## 2. 进场流程")
        lines.append("")
        lines.append("```csharp")
        lines.append("// 离线结构候选：真实导航入口和运行时触发方式必须由 unity-functiontest 在 PlayMode 中验证")
        lines.append("// 若源码回调内部会异步创建 UI，只把它作为预期结果线索，不作为运行时通过证据")
        lines.append("// 运行时需独立轮询确认")
        lines.append(f'var ui = GameObject.Find("{ui.ui_name}");')
        lines.append("// activeInHierarchy == true → 就绪")
        lines.append("```")
        lines.append("")
        lines.append("**全限定路径轮询（推荐）**：")
        lines.append("```csharp")
        lines.append(f'var root = "GameEntry/Builtin/UI/AdapterArea/{ui.canvas_path}/";')
        lines.append(f'var ui = GameObject.Find(root + "{ui.ui_name}");')
        lines.append("```")

        # ===== 节点树速查 =====
        lines.append("")
        lines.append("## 3. 节点树速查")
        lines.append("")
        if self.prefab_info:
            lines.append(self.prefab_info)
        else:
            lines.append("> 待 Unity 运行时通过 `capture_scene_snapshot` 获取实际节点树后补充。")
            lines.append("")

        # 从 AutoGen 字段生成节点树骨架
        if self.auto_gen_fields:
            lines.append("### AutoGen 绑定组件清单")
            lines.append("")
            lines.append("| 运行时节点名（全路径） | 字段名 | 类型 | 注释 |")
            lines.append("|----------------------|--------|------|------|")
            for f in self.auto_gen_fields:
                lines.append(f"| `{f.runtime_node_name}` | `{f.field_name}` | {f.type_label} | {f.comment} |")
            lines.append("")
            lines.append("**命名规则**：`字段名` 去掉末尾的 `_{idx}_{type}` 后缀得到节点名，再通过 Prefab 层级解析为**从预制体根节点开始的完整路径**。")
            lines.append("例如 `btn_baocun_1_4_btn` → 节点名 `btn_baocun_1` → 全路径 `UI_Formation\\wanju_group\\btn_baocun_1`。")

        # ===== 按钮/交互速查 =====
        lines.append("")
        lines.append("## 4. 按钮/交互速查")
        lines.append("")
        lines.append("| AutoGen 字段 | 运行时节点（全路径） | 触发方式 | Logic 回调 |")
        lines.append("|-------------|---------------------|---------|-----------|")
        if self.logic_callbacks:
            for field_name, method_name in self.logic_callbacks:
                # 找到对应字段的运行时节点名
                runtime_node = field_name
                for f in self.auto_gen_fields:
                    if f.field_name == field_name:
                        runtime_node = f.runtime_node_name
                        break
                lines.append(
                    f"| `{field_name}` | `{runtime_node}` | 候选：`onClick?.Invoke()` | {method_name}() |"
                )
        else:
            lines.append("| — | — | — | — |")
        lines.append("")
        lines.append("**离线候选说明**：`onClick?.Invoke()` 仅表示源码层候选触发方式；实际是否有效必须由 unity-functiontest 在 PlayMode 中验证，不能直接作为通过证据。")

        # ===== AutoGen 字段完整映射 =====
        lines.append("")
        lines.append("## 5. AutoGen 字段完整映射")
        lines.append("")
        # 判断是否有 GameButton 字段，决定是否展示回调方法列
        has_buttons = any(f.is_button for f in self.auto_gen_fields)
        if has_buttons:
            lines.append("| 字段名 | 运行时节点名（全路径） | 类型 | 注释 | 响应接口 |")
            lines.append("|--------|----------------------|------|------|---------|")
            for f in self.auto_gen_fields:
                callback = self._get_callback_for_field(f.field_name)
                callback_str = f"`{callback}()`" if callback else "—"
                lines.append(
                    f"| `{f.field_name}` | `{f.runtime_node_name}` | {f.type_label} | {f.comment} | {callback_str} |"
                )
        else:
            lines.append("| 字段名 | 运行时节点名（全路径） | 类型 | 注释 |")
            lines.append("|--------|----------------------|------|------|")
            for f in self.auto_gen_fields:
                lines.append(f"| `{f.field_name}` | `{f.runtime_node_name}` | {f.type_label} | {f.comment} |")

        # ===== Logic 关键字段 =====
        lines.append("")
        lines.append("## 6. Logic 关键字段")
        lines.append("")
        lines.append("| 字段名 | 类型 | 用途 |")
        lines.append("|--------|------|------|")
        if self.key_fields:
            for name, typ, _ in self.key_fields:
                lines.append(f"| `{name}` | {typ} | — |")
        else:
            lines.append("| — | — | — |")

        # ===== Logic 缓存 + 状态读取 helper =====
        lines.append("")
        lines.append("## 7. Logic 缓存 + 状态读取 helper")
        lines.append("")
        lines.append("```csharp")
        lines.append("// === 首次缓存 ===")
        lines.append("System.Type t = null;")
        lines.append("foreach (var asm in System.AppDomain.CurrentDomain.GetAssemblies()) {")
        lines.append(f'    t = asm.GetType("{ui.logic_fullname}");')
        lines.append("    if (t != null) { UnityEngine.PlayerPrefs.SetString(\"__test_logic_asm__\", asm.GetName().Name); break; }")
        lines.append("}")
        lines.append(f'UnityEngine.PlayerPrefs.SetString("__test_logic_type__", t.AssemblyQualifiedName);')
        lines.append(f'UnityEngine.PlayerPrefs.SetString("__test_logic_root__", "{ui.ui_name}");')
        lines.append("UnityEngine.PlayerPrefs.Save();")
        lines.append(f'var root = GameObject.Find("{ui.ui_name}");')
        lines.append("var baseUI = root.GetComponent<GameFramework.Logic.BaseUI>();")
        lines.append("var adapter = typeof(GameFramework.Logic.BaseUI)")
        lines.append("    .GetField(\"m_MonoInvocationAdapter\", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)")
        lines.append("    .GetValue(baseUI);")
        lines.append("var lg = adapter.GetType()")
        lines.append("    .GetField(\"m_Instance\", System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)")
        lines.append("    .GetValue(adapter);")
        lines.append("")
        lines.append("// === 批量状态读取（合并单次 evaluate） ===")
        lines.append(f'var root = GameObject.Find("GameEntry/Builtin/UI/AdapterArea/{ui.canvas_path}/{ui.ui_name}");')
        lines.append("// 根据实际节点补充读取代码")
        lines.append("```")

        # ===== 已知问题 =====
        lines.append("")
        lines.append("## 8. 已知问题")
        lines.append("")
        # 从已有内容中提取已知问题
        existing_known = self._extract_section(existing_content, "已知问题")
        if existing_known:
            lines.append(existing_known)
        else:
            lines.append("| 节点 | 症状 | 兜底方案 | 确认日期 |")
            lines.append("|------|------|---------|---------|")
            lines.append("| — | — | — | — |")

        # ===== 用例分组建议 =====
        lines.append("")
        lines.append("## 9. 用例分组建议")
        lines.append("")
        existing_group = self._extract_section(existing_content, "用例分组建议")
        if existing_group:
            lines.append(existing_group)
        else:
            lines.append("| 分组 | 用例 | 说明 |")
            lines.append("|------|------|------|")
            lines.append("| — | — | — |")

        lines.append("")
        return "\n".join(lines)

    def _extract_section(self, content: str, section_title: str) -> str:
        """从已有内容中提取指定章节"""
        if not content:
            return ""
        pattern = re.compile(
            rf"##\s+\d+\.\s*{re.escape(section_title)}\s*\n(.*?)(?=\n##\s+\d+\.|\Z)",
            re.DOTALL,
        )
        m = pattern.search(content)
        if m:
            return m.group(1).strip()
        return ""


# ============================================================
# 主流程
# ============================================================
def find_project_root() -> Path:
    """从当前目录向上查找项目根（包含 .git 或 Assets 目录）"""
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if (p / "Assets").exists() and (p / "ProjectSettings").exists():
            return p
    return cwd


def resolve_path(path: Path, project_root: Path) -> Path:
    """如果路径是相对于项目根的，拼接完整路径"""
    if not path.is_absolute():
        return project_root / path
    return path


def find_workspace_root(project_root: Path) -> Path:
    """当前工作区由调用方传入，不再根据 ``Public`` 目录猜测父级目录。"""
    return _safe_resolve(project_root)


def _table_project_root_candidates(workspace_root: Path, max_levels: int = 2) -> List[Tuple[str, Path]]:
    """返回配表可能所属的项目根目录，工作区本身不因命中而被改写。"""

    roots: List[Tuple[str, Path]] = [("workspace", _safe_resolve(workspace_root))]
    for source, ancestor in _ancestor_relative_roots(workspace_root, max_levels=max_levels):
        roots.append((source, ancestor))
    return roots


def _project_root_marker_score(candidate_root: Path) -> float:
    """按常见项目级目录名为候选目录评分，允许有限的名称模糊匹配。"""

    try:
        child_names = [item.name.casefold() for item in candidate_root.iterdir() if item.is_dir()]
    except OSError:
        return 0.0
    score = 0.0
    for marker in PROJECT_ROOT_MARKERS:
        best = 0.0
        for child_name in child_names:
            if child_name == marker:
                best = 1.0
                break
            similarity = difflib.SequenceMatcher(None, marker, child_name).ratio()
            if marker in child_name or child_name in marker:
                similarity = max(similarity, 0.82)
            if similarity >= PROJECT_ROOT_MARKER_MIN_SCORE:
                best = max(best, similarity)
        score += best
    return score


def find_ui_logic_manager_project_root(project_root: Path) -> Path:
    """在工作区及向上两级内确定表格和效果图共用的项目根目录。

    优先选择包含 ``Public``、``Art``、``Doc``、``Server`` 等常见项目级目录
    （含有限模糊匹配）的最高分候选；同分时优先更外层目录。若没有任何标记，
    默认向上两级目录。该结果只决定最终模糊搜索根，不改变当前工作区。
    """

    workspace_root = find_workspace_root(project_root)
    candidates = _table_project_root_candidates(workspace_root)
    if not candidates:
        return workspace_root
    scored = [(_project_root_marker_score(root), index, root) for index, (_, root) in enumerate(candidates)]
    best_score, _, best_root = max(scored, key=lambda item: (item[0], item[1]))
    return best_root if best_score > 0 else candidates[-1][1]


def _score_ui_logic_manager_xlsx_candidate(candidate: Path, table_project_root: Path) -> float:
    """按文件名和标准表相对路径给模糊配表候选排序。"""

    target_name = "uilogicmanager"
    actual_name = _normalize_match_text(candidate.stem)
    name_score = difflib.SequenceMatcher(None, target_name, actual_name).ratio()
    if actual_name == target_name:
        name_score = 1.0
    elif target_name in actual_name or actual_name in target_name:
        name_score = max(name_score, 0.90)
    try:
        relative = candidate.resolve().relative_to(table_project_root.resolve()).as_posix()
    except (OSError, ValueError):
        relative = candidate.as_posix()
    path_score = difflib.SequenceMatcher(
        None,
        _normalize_match_text(UI_LOGIC_MANAGER_XLSX_STANDARD_RELATIVE.as_posix()),
        _normalize_match_text(relative),
    ).ratio()
    return name_score * 0.70 + path_score * 0.30


def _find_fuzzy_ui_logic_manager_xlsx(table_project_root: Path) -> List[Tuple[float, Path]]:
    """只在已确定的项目根目录内模糊查找配表，不作无界父目录扫描。"""

    if not table_project_root.is_dir():
        return []
    candidates: List[Tuple[float, Path]] = []
    for root, dirs, files in os.walk(table_project_root, topdown=True, followlinks=False):
        dirs[:] = sorted(
            (name for name in dirs if name not in EFFECT_IMAGE_IGNORED_DIRS),
            key=str.casefold,
        )
        for filename in sorted(files, key=str.casefold):
            path = Path(root) / filename
            if path.suffix.casefold() != ".xlsx":
                continue
            score = _score_ui_logic_manager_xlsx_candidate(path, table_project_root)
            if score >= FUZZY_MIN_UI_LOGIC_MANAGER_XLSX_SCORE:
                candidates.append((score, path))
    candidates.sort(key=lambda item: (-item[0], str(item[1]).casefold()))
    return candidates


def discover_ui_logic_manager_xlsx(
    project_root: Path,
) -> Tuple[Optional[Path], UILogicManagerXlsxParser, Path, Path]:
    """动态查找 UILogicManager.xlsx，并显式区分工作区和表格项目根。

    工作区固定为调用方传入的 ``project_root``。表格按“工作区、上一级、上两级”
    依次检查标准位置；标准位置都不存在时，与效果图共用经项目标记评分确定的
    项目根，只在该根内做一次受限文件名模糊搜索。每次调用均重新定位，不读取
    reference 或进程内缓存。
    """
    workspace_root = find_workspace_root(project_root)
    table_project_root = find_ui_logic_manager_project_root(workspace_root)
    selected_path: Optional[Path] = None
    path_mode = ""
    for _, candidate_root in _table_project_root_candidates(workspace_root):
        candidate = candidate_root / UI_LOGIC_MANAGER_XLSX_STANDARD_RELATIVE
        if candidate.is_file():
            selected_path = candidate
            table_project_root = candidate_root
            path_mode = "标准路径"
            break
    if selected_path is None:
        for _, candidate_root in _table_project_root_candidates(workspace_root):
            candidate = candidate_root / UI_LOGIC_MANAGER_XLSX_TEMP_RELATIVE
            if candidate.is_file():
                selected_path = candidate
                table_project_root = candidate_root
                path_mode = "兼容临时路径"
                break
    if selected_path is None:
        fuzzy_candidates = _find_fuzzy_ui_logic_manager_xlsx(table_project_root)
        if fuzzy_candidates:
            selected_path = fuzzy_candidates[0][1]
            path_mode = "项目根目录模糊匹配"

    if selected_path is None:
        print(
            "[WARN] 在工作区、上一级和上两级均未找到标准 UILogicManager.xlsx；"
            f"项目根目录 {table_project_root} 内的模糊搜索也无结果"
        )
        return None, UILogicManagerXlsxParser(None), workspace_root, table_project_root

    parser = UILogicManagerXlsxParser(selected_path)
    display_path = _display_workspace_path(selected_path, table_project_root)
    if parser.parse_error:
        print(f"[WARN] UILogicManager.xlsx 解析失败: {display_path}；{parser.parse_error}")
    elif parser.entries:
        print(
            f"[INFO] 通过{path_mode}找到 UILogicManager.xlsx: {display_path}；"
            f"字段={parser.effect_path_field or '未识别'}，UI数量={len(parser.entries)}"
        )
    else:
        print(f"[WARN] 找到 UILogicManager.xlsx 但未识别到 UI 数据: {display_path}")
    return selected_path, parser, workspace_root, table_project_root


def _display_workspace_path(path: Path, workspace_root: Path) -> str:
    """优先返回工作区相对路径，避免把环境绝对路径写入 reference。"""
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _ancestor_relative_roots(project_root: Path, max_levels: int = 2) -> List[Tuple[str, Path]]:
    """返回项目根目录向上的有限回退根，避免无限扫描父级目录。"""

    roots: List[Tuple[str, Path]] = []
    current = _safe_resolve(project_root)
    for level in range(1, max_levels + 1):
        parent = current.parent
        if parent == current:
            break
        roots.append((f"ancestor_relative_{level}", parent))
        current = parent
    return roots


def _clean_effect_path(raw_path: str) -> str:
    """清理 xlsx 单元格中的空白和包裹引号。"""

    return str(raw_path or "").strip().strip('"').strip("'").strip()


def _normalize_match_text(value: str) -> str:
    """统一路径分隔符、Unicode 形式和大小写，供候选排序使用。"""

    return unicodedata.normalize("NFKC", str(value or "").replace("\\", "/")).casefold()


def _match_path_parts(value: str) -> List[str]:
    normalized = _normalize_match_text(value)
    return [part for part in normalized.split("/") if part and part not in (".", "..")]


def _match_tokens(value: str) -> List[str]:
    normalized = _normalize_match_text(value)
    return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalized)


def _safe_resolve(path: Path) -> Path:
    """非严格解析路径；遇到 Windows 特殊路径时保留原路径。"""

    try:
        return path.resolve()
    except OSError:
        return path


def _effect_image_roots(
    project_root: Path,
    workspace_root: Path,
    xlsx_path: Optional[Path],
) -> List[Tuple[str, int, Path]]:
    """返回一次模糊搜索使用的根目录。

    模糊回退只允许在“工作区、上一级、上两级”中评分确定的项目根内执行一次；
    不再把表格目录或其他父级目录加入扫描范围。保留 ``xlsx_path`` 参数仅为
    兼容已有调用方。
    """

    del xlsx_path
    current_workspace = _safe_resolve(project_root)
    fuzzy_root = find_ui_logic_manager_project_root(current_workspace)
    source = "project_root_fuzzy"
    if not fuzzy_root.is_dir():
        return []
    return [(source, 1, fuzzy_root)]


def _iter_effect_image_files(root: Path):
    """遍历图片文件；不跟随链接，也跳过 Unity 缓存和构建目录。"""

    if not root.is_dir():
        return
    for current_root, dirs, files in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(
            (name for name in dirs if name not in EFFECT_IMAGE_IGNORED_DIRS),
            key=str.casefold,
        )
        for filename in sorted(files, key=str.casefold):
            if Path(filename).suffix.casefold() not in EFFECT_IMAGE_SUFFIXES:
                continue
            yield Path(current_root) / filename


def _build_effect_image_index(
    project_root: Path,
    workspace_root: Path,
    xlsx_path: Optional[Path],
) -> List[_EffectImageIndexEntry]:
    """为本次查询建立图片索引，不写入或复用任何路径缓存。"""

    roots = _effect_image_roots(project_root, workspace_root, xlsx_path)
    index: List[_EffectImageIndexEntry] = []
    seen_paths = set()
    for source, priority, root in roots:
        for image_path in _iter_effect_image_files(root):
            # os.path.abspath 只做字符串规范化，不对每个文件触发一次物理 resolve，
            # 否则 Windows 下大项目的模糊回退会产生明显额外耗时。
            resolved = Path(os.path.abspath(str(image_path)))
            path_key = os.path.normcase(str(resolved))
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            try:
                relative_path = resolved.relative_to(root).as_posix()
            except ValueError:
                relative_path = resolved.name
            index.append(_EffectImageIndexEntry(resolved, source, priority, relative_path))

    return index


def _common_suffix_count(left: List[str], right: List[str]) -> int:
    """计算目录部分从右侧开始连续相同的层数。"""

    count = 0
    for left_part, right_part in zip(reversed(left[:-1]), reversed(right[:-1])):
        if left_part != right_part:
            break
        count += 1
    return count


def _score_effect_image_candidate(raw_path: str, entry: _EffectImageIndexEntry) -> _EffectImageMatch:
    raw_parts = _match_path_parts(raw_path)
    candidate_parts = _match_path_parts(entry.relative_path)
    raw_filename = raw_parts[-1] if raw_parts else ""
    raw_stem = _normalize_match_text(os.path.splitext(raw_filename)[0])
    candidate_stem = _normalize_match_text(entry.path.stem)
    stem_similarity = difflib.SequenceMatcher(None, raw_stem, candidate_stem, autojunk=False).ratio()
    contains_stem = bool(raw_stem and raw_stem in candidate_stem)

    raw_tokens = set(_match_tokens(raw_stem))
    candidate_tokens = set(_match_tokens(candidate_stem))
    token_overlap = len(raw_tokens & candidate_tokens) / max(len(raw_tokens), 1)
    path_suffix_matches = _common_suffix_count(raw_parts, candidate_parts)
    raw_dir_count = max(len(raw_parts) - 1, 0)
    path_suffix_score = path_suffix_matches / max(raw_dir_count, 1)

    raw_ext = os.path.splitext(raw_filename)[1].casefold()
    ext_score = 1.0 if raw_ext and raw_ext == entry.path.suffix.casefold() else 0.0
    extra_stem_length = max(0, len(candidate_stem) - len(raw_stem))

    score = (
        stem_similarity * 0.45
        + (0.20 if contains_stem else 0.0)
        + token_overlap * 0.15
        + min(path_suffix_score, 1.0) * 0.15
        + ext_score * 0.05
        - min(extra_stem_length / max(len(raw_stem), 1), 1.0) * 0.05
        + entry.root_priority * 0.002
    )
    if raw_stem == candidate_stem:
        score = 1.0 + entry.root_priority * 0.002

    return _EffectImageMatch(entry, score, stem_similarity, path_suffix_matches, extra_stem_length)


def _find_fuzzy_effect_images(
    raw_path: str,
    project_root: Path,
    workspace_root: Path,
    xlsx_path: Optional[Path],
) -> List[_EffectImageMatch]:
    """按文件名和路径语义排序图片候选。"""

    matches = [
        _score_effect_image_candidate(raw_path, entry)
        for entry in _build_effect_image_index(project_root, workspace_root, xlsx_path)
    ]
    matches.sort(
        key=lambda item: (
            -item.score,
            -item.path_suffix_matches,
            -item.stem_similarity,
            item.extra_stem_length,
            -item.entry.root_priority,
            _normalize_match_text(item.entry.relative_path),
        )
    )
    return matches


def resolve_effect_path_details(
    raw_path: str,
    project_root: Path,
    workspace_root: Path,
    xlsx_path: Optional[Path],
) -> EffectPathResolution:
    """解析效果图路径，并在相对路径精确失败时执行一次模糊匹配。"""

    value = _clean_effect_path(raw_path)
    if not value:
        return EffectPathResolution(status="未配置", reason="UIPerfectPath 未填写")

    configured = Path(value)
    if configured.is_absolute():
        candidate = _safe_resolve(configured)
        if candidate.is_file():
            return EffectPathResolution(
                status="已找到",
                # 绝对路径按填写值直接使用，不改写成工作区相对路径。
                display_path=str(candidate),
                absolute_path=str(candidate),
                path_source="absolute",
                match_mode="exact",
                confidence=1.0,
                candidates=[str(candidate)],
                reason="绝对路径已找到文件",
            )
        return EffectPathResolution(
            status="未配置",
            path_source="absolute",
            match_mode="exact",
            reason="绝对路径未找到，按未配置路径处理；请检查路径是否正确",
        )

    # 相对路径严格按当前工作区、向上回退一层、向上回退两层依次精确查找。
    current_workspace = _safe_resolve(project_root)
    exact_roots = [("workspace_relative", current_workspace)]
    exact_roots.extend(_ancestor_relative_roots(current_workspace, max_levels=2))
    seen_exact = set()
    for source, base in exact_roots:
        candidate = _safe_resolve(base / configured)
        key = os.path.normcase(str(candidate))
        if key in seen_exact:
            continue
        seen_exact.add(key)
        if candidate.is_file():
            return EffectPathResolution(
                status="已找到",
                display_path=_display_workspace_path(candidate, workspace_root),
                absolute_path=str(candidate),
                path_source=source,
                match_mode="exact",
                confidence=1.0,
                candidates=[_display_workspace_path(candidate, workspace_root)],
                reason="相对路径已找到文件",
            )

    fuzzy_matches = _find_fuzzy_effect_images(value, project_root, workspace_root, xlsx_path)
    displayed_candidates = [
        _display_workspace_path(item.entry.path, workspace_root)
        for item in fuzzy_matches[:20]
    ]
    if not fuzzy_matches:
        return EffectPathResolution(
            status="未配置",
            match_mode="fuzzy",
            candidates=[],
            reason="相对路径精确查找和图片名模糊匹配均未找到，按未配置路径处理；请检查路径是否正确",
        )

    qualified_matches = [item for item in fuzzy_matches if item.score >= FUZZY_MIN_EFFECT_SCORE]
    if not qualified_matches:
        return EffectPathResolution(
            status="未配置",
            match_mode="fuzzy",
            confidence=fuzzy_matches[0].score,
            candidates=displayed_candidates,
            reason="模糊匹配候选存在但匹配度过低，按未配置路径处理；请检查路径是否正确",
        )

    best = qualified_matches[0]
    second = qualified_matches[1] if len(qualified_matches) > 1 else None
    if second is not None and best.score - second.score <= FUZZY_TIE_EPSILON:
        return EffectPathResolution(
            status="未配置",
            match_mode="fuzzy",
            confidence=best.score,
            candidates=displayed_candidates,
            reason="模糊匹配最高候选并列或差异过小，按未配置路径处理；请检查路径是否正确",
        )

    return EffectPathResolution(
        status="已找到",
        display_path=displayed_candidates[0],
        absolute_path=str(best.entry.path),
        path_source=best.entry.source,
        match_mode="fuzzy",
        confidence=best.score,
        candidates=displayed_candidates,
        reason="相对路径未命中，已使用最高匹配度图片候选",
    )


def resolve_effect_path(
    raw_path: str,
    project_root: Path,
    workspace_root: Path,
    xlsx_path: Optional[Path],
) -> Tuple[str, str]:
    """兼容旧调用方，仅返回 ``(状态, 展示路径)``。"""

    result = resolve_effect_path_details(raw_path, project_root, workspace_root, xlsx_path)
    return result.status, result.absolute_path or result.display_path


def discover_ui_logic_manager(project_root: Path) -> Tuple[Optional[Path], UILogicManagerParser]:
    """在项目根目录下动态查找 UILogicManager 文件，优先返回 `.bytes`。"""
    ignored_dirs = {".git", ".svn", "Library", "Temp", "Logs", "obj", ".vs", "Build", "Builds"}
    candidates: List[Path] = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [name for name in dirs if name not in ignored_dirs]
        for filename in files:
            base_name = filename.casefold().split(".", 1)[0]
            if base_name == "uilogicmanager" and Path(filename).suffix.casefold() != ".meta":
                candidates.append(Path(root) / filename)

    candidates.sort(key=lambda path: (
        0 if path.suffix.casefold() == ".bytes" else 1,
        len(path.relative_to(project_root).parts),
        str(path.relative_to(project_root)).casefold(),
    ))

    # `.bytes` 是项目运行时的权威表数据。即使它不能按文本读取，也不能
    # 退回到同名旧文本或直接把它当作缺失；应保留路径，交给 Unity 运行时解码。
    byte_candidates = [path for path in candidates if path.suffix.casefold() == ".bytes"]
    if byte_candidates:
        selected_path = byte_candidates[0]
        selected_manager = UILogicManagerParser(selected_path)
        if selected_manager.entries:
            print(f"[INFO] 动态找到可读取的 UILogicManager.bytes: {selected_path.relative_to(project_root)}")
        else:
            print(
                f"[INFO] 动态找到 UILogicManager.bytes: {selected_path.relative_to(project_root)}；"
                "需使用 Unity 运行时解密和反序列化"
            )
        return selected_path, selected_manager

    parsed = []
    for candidate in candidates:
        manager = UILogicManagerParser(candidate)
        if manager.entries:
            parsed.append((candidate, manager))

    if not parsed:
        if candidates:
            selected_path = candidates[0]
            print(
                f"[INFO] 动态找到 UILogicManager 候选文件: {selected_path.relative_to(project_root)}；"
                "文本解析没有可解析的数据，需使用 Unity 运行时解密和反序列化"
            )
            return selected_path, UILogicManagerParser(selected_path)
        else:
            print("[WARN] 未找到名称匹配 UILogicManager 的文件")
        return None, UILogicManagerParser(None)

    if len(parsed) > 1:
        relative_candidates = [str(path.relative_to(project_root)) for path, _ in parsed]
        print(f"[WARN] 找到多个可解析的 UILogicManager，使用 {relative_candidates[0]}；候选={relative_candidates}")
    selected_path, selected_manager = parsed[0]
    print(f"[INFO] 动态找到 UILogicManager: {selected_path.relative_to(project_root)}")
    return selected_path, selected_manager


def main():
    parser = argparse.ArgumentParser(description="UI 快速参考图谱扫描器")
    parser.add_argument("keyword", help="搜索关键字（UIName / 描述）")
    parser.add_argument("--feature-id", "-f", default=None, help="强制指定 feature_id")
    parser.add_argument("--out-dir", "-o", default=None, help="输出目录（默认写入 ui-quick-reference/references/）")
    parser.add_argument("--project-root", "-p", default=None, help="当前工作区目录路径")
    parser.add_argument("--runtime-ui-id", default=None, help="Unity 运行时解析得到的 UIID")
    parser.add_argument("--runtime-ui-name", default=None, help="Unity 运行时解析得到的 UIName")
    parser.add_argument("--runtime-canvas-index", default=None, help="Unity 运行时解析得到的 CanvasIndex")
    parser.add_argument("--runtime-ui-desc", default=None, help="Unity 运行时解析得到的 UIDes")
    parser.add_argument("--runtime-open-close-list", default=None, help="Unity 运行时解析得到的 open_close_List")
    parser.add_argument("--runtime-ui-type", default=None, help="Unity 运行时解析得到的 UIType")
    args = parser.parse_args()

    # 确定当前工作区
    project_root = Path(args.project_root) if args.project_root else find_project_root()
    os.chdir(project_root)
    print(f"[INFO] 工作区目录: {project_root}")

    # Step 1: 动态查找 UILogicManager；`.bytes` 优先由 Unity 运行时解析
    manager_path, manager = discover_ui_logic_manager(project_root)
    runtime_entry = build_runtime_entry(args)
    if runtime_entry:
        if manager_path and manager_path.suffix.casefold() == ".bytes":
            print(f"[INFO] 使用 Unity 运行时解析结果覆盖 {manager_path.relative_to(project_root)} 的文本解析结果")
        else:
            print("[INFO] 使用 Unity 运行时解析结果")
        manager.entries = [runtime_entry] + [
            item for item in manager.entries if item.ui_name != runtime_entry.ui_name
        ]
    if not manager.entries:
        if manager_path:
            print(
                f"[ERROR] 已找到 UILogicManager 候选文件 {manager_path.name}，但没有收到 Unity 运行时解析结果；"
                "禁止生成未知 UIID/CanvasIndex 的参考文档。请先调用 Unity evaluate，再传入 --runtime-* 参数"
            )
            sys.exit(1)
        if args.keyword.startswith("UI_"):
            print("[WARN] UILogicManager 缺失或无数据，使用明确 UIName 直接扫描")
            entry = UIEntry({
                "ID": "unknown",
                "UIName": args.keyword,
                "UIDes": "",
                "canvasIndex": "unknown",
                "open_close_List": "",
                "UIType": "",
            })
            manager.entries = [entry]
        else:
            print("[ERROR] UILogicManager 解析失败或无数据；请传入明确 UIName（如 UI_XXX）或补充可解析的 UILogicManager 文件")
            sys.exit(1)

    # 匹配 UI
    keyword = args.keyword
    # 先精确匹配 UIName
    entry = manager.find_by_uiname(keyword)
    if entry:
        print(f"[OK] 精确匹配 UIName: {entry.ui_name} (ID={entry.id})")
    else:
        # 模糊匹配
        results = manager.find_by_keyword(keyword)
        if not results:
            print(f"[ERROR] 未找到匹配 '{keyword}' 的 UI")
            print("  候选列表（前 20）:")
            for e in manager.entries[:20]:
                print(f"    ID={e.id} {e.ui_name} — {e.ui_desc}")
            sys.exit(1)
        if len(results) == 1:
            entry = results[0]
            print(f"[OK] 模糊匹配: {entry.ui_name} (ID={entry.id}) — {entry.ui_desc}")
        else:
            print(f"[INFO] 找到 {len(results)} 个匹配:")
            for i, e in enumerate(results):
                print(f"  [{i}] ID={e.id} {e.ui_name} — {e.ui_desc}")
            # 默认取第一个
            entry = results[0]
            print(f"[INFO] 自动选择第一个: {entry.ui_name}")

    # 确定 feature_id
    feature_id = args.feature_id if args.feature_id else entry.feature_id
    print(f"[INFO] feature_id: {feature_id}")

    # Step 2: 查找子 UI（通过 UILogicManager 中关联的 UI）
    # 策略：从 UIName 中提取功能名关键词（如 DrawCard），匹配其他含相同关键词的 UI
    sub_uis = []
    base_name = entry.ui_name
    if base_name.startswith("UI_"):
        base_name = base_name[3:]
    base_parts = base_name.split("_")
    if base_parts:
        main_keyword = base_parts[0]
        for e in manager.entries:
            if e.ui_name == entry.ui_name:
                continue
            if main_keyword in e.ui_name:
                sub_uis.append(e)
    print(f"[INFO] 发现 {len(sub_uis)} 个子 UI: {[s.ui_name for s in sub_uis]}")

    # Step 3: 扫描 Prefab
    prefab_dir = resolve_path(UI_PREFAB_ROOT / entry.ui_name, project_root)
    prefab_scanner = PrefabScanner(prefab_dir)
    prefab_info = prefab_scanner.extract_node_tree()
    print(f"[INFO] Prefab: {prefab_scanner.prefab_file}")
    print(f"[INFO] Prefab 节点路径映射: {len(prefab_scanner.node_path_map)} 个节点")

    # Step 4: 解析 AutoGen（传入 prefab 节点路径映射，生成完整路径）
    logic_dir = resolve_path(UI_LOGIC_ROOT / entry.ui_name, project_root)
    auto_gen_file = logic_dir / f"{entry.ui_name}_AutoGen.cs"
    auto_gen_parser = AutoGenParser(auto_gen_file, prefab_scanner.node_path_map)
    print(f"[INFO] AutoGen 字段: {len(auto_gen_parser.fields)} 个")

    # Step 5: 解析 Logic
    logic_file = logic_dir / f"{entry.ui_name}_Logic.cs"
    logic_parser = LogicParser(logic_file)
    print(f"[INFO] Logic 回调: {len(logic_parser.callbacks)} 个")
    print(f"[INFO] Logic 字段: {len(logic_parser.key_fields)} 个")

    # Step 6: 生成文档
    generator = ReferenceDocGenerator(entry, feature_id)
    generator.sub_uis = sub_uis
    generator.auto_gen_fields = auto_gen_parser.fields
    generator.logic_callbacks = logic_parser.callbacks
    generator.key_fields = logic_parser.key_fields
    generator.prefab_info = prefab_info

    # 输出边界：本扫描器只允许写入离线静态 reference 目录。
    # 运行时 reference 必须由 unity-functiontest 基于 PlayMode 实测维护。
    static_reference_dir = resolve_path(SKILL_REFERENCES, project_root).resolve()
    output_dir = resolve_path(Path(args.out_dir), project_root).resolve() if args.out_dir else static_reference_dir
    try:
        output_dir.relative_to(static_reference_dir)
    except ValueError:
        print(
            "[ERROR] ui-quick-reference 只能写入本 Skill 的 references/ 目录；"
            "禁止覆盖 unity-functiontest 的运行时 reference。"
        )
        sys.exit(2)

    out_dirs = [output_dir]

    written_files = []
    for out_dir in out_dirs:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{feature_id}.md"

        existing_content = ""
        if out_file.exists():
            existing_content = out_file.read_text(encoding="utf-8")
            print(f"[INFO] 已有文件: {out_file}，将增量更新")

        doc_content = generator.generate(existing_content)
        out_file.write_text(doc_content, encoding="utf-8")
        written_files.append(out_file)
        print(f"\n[OK] 参考文档已生成: {out_file}")

    print(f"[INFO] 输出文件数: {len(written_files)}")
    print(f"[SUMMARY] UI={entry.ui_name} feature_id={feature_id} fields={len(auto_gen_parser.fields)} callbacks={len(logic_parser.callbacks)}")


if __name__ == "__main__":
    main()
