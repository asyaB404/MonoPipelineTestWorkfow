#!/usr/bin/env python3
"""每次实时读取 UILogicManager.xlsx 中指定 UI 的效果图路径。

该脚本只输出当前查询结果，不写入 ui-quick-reference/reference 缓存文件。
"""

import argparse
import contextlib
import json
import re
import sys
from pathlib import Path

from scan_ui_references import (
    _display_workspace_path,
    UILogicManagerXlsxParser,
    discover_ui_logic_manager_xlsx,
    find_workspace_root,
    resolve_effect_path_details,
)


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def load_xlsx(project_root: Path):
    """每次按当前工作区动态定位并重新读取 UILogicManager.xlsx。"""

    workspace_root = find_workspace_root(project_root)
    discovered, parser, _, table_project_root = discover_ui_logic_manager_xlsx(project_root)
    return discovered, parser, workspace_root, table_project_root, "dynamic"


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="实时读取 UI 效果图路径")
    parser.add_argument("ui_name", help="精确 UIName，例如 UI_TDHeroAll")
    parser.add_argument(
        "--project-root",
        default=None,
        help="当前 AI 工作区目录；未传入时使用当前目录",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd().resolve()
    with contextlib.redirect_stdout(sys.stderr):
        xlsx_path, xlsx_parser, workspace_root, table_project_root, table_path_source = load_xlsx(project_root)
    result = {
        "ui_name": args.ui_name,
        "status": "config_not_found",
        "field": xlsx_parser.effect_path_field or "UIPerfectPath",
        "configured_path": "",
        "resolved_path": "",
        "resolved_absolute_path": "",
        "path_source": "",
        "match_mode": "",
        "match_confidence": 0.0,
        "candidates": [],
        "workspace_root": str(workspace_root),
        "table_project_root": str(table_project_root),
        "config_source": _display_workspace_path(xlsx_path, table_project_root) if xlsx_path else "",
        "table_path_source": table_path_source,
    }

    if xlsx_path is None:
        result["reason"] = "工作区、上一级和上两级的标准表路径均未命中，项目根目录模糊搜索也未找到 UILogicManager.xlsx"
    elif xlsx_parser.parse_error:
        result["status"] = "config_parse_failed"
        result["reason"] = xlsx_parser.parse_error
    else:
        entry = xlsx_parser.find_by_uiname(args.ui_name)
        if entry is None:
            result["status"] = "ui_not_found"
            result["reason"] = "配置表中未找到该 UIName"
        else:
            result["field"] = entry.ui_perfect_path_field or xlsx_parser.effect_path_field or "UIPerfectPath"
            result["configured_path"] = entry.ui_perfect_path
            if not entry.ui_perfect_path:
                result["status"] = "not_configured"
                result["reason"] = "该 UI 未配置效果图路径"
            else:
                resolution = resolve_effect_path_details(
                    entry.ui_perfect_path,
                    project_root,
                    workspace_root,
                    xlsx_path,
                )
                result["status"] = "found" if resolution.status == "已找到" else "not_configured"
                # resolved_path 供下游工具直接打开，必须使用已验证的绝对路径；
                # display_path 仍保留在解析结果中用于候选展示和审计。
                result["resolved_path"] = resolution.absolute_path or resolution.display_path
                result["resolved_absolute_path"] = resolution.absolute_path
                result["path_source"] = resolution.path_source
                result["match_mode"] = resolution.match_mode
                result["match_confidence"] = round(resolution.confidence, 4)
                result["candidates"] = resolution.candidates
                result["reason"] = resolution.reason or (
                    "效果图路径已配置并找到文件"
                    if resolution.status == "已找到"
                    else "效果图路径未找到，按未配置路径处理"
                )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
