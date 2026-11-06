#!/usr/bin/env python3
"""创建日期：2026-10-09；创建人：Cyou。
功能：PC FunctionTest 唯一公共 CLI 包装；参数：透传 functiontest_runtime.cli，不导入时启动。
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
AI_TOOLS = Path(__file__).resolve().parents[4] / "Tools" / "AI"
if str(AI_TOOLS) not in sys.path:
    sys.path.insert(0, str(AI_TOOLS))
from functiontest_runtime.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
