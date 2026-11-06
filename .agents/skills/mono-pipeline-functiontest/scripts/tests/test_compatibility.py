"""创建日期：2026-10-26；创建人：Cyou。
功能：检查可迁移公共模块符合声明的 Python 3.10 语法基线。
基础参数：本目录所属 scripts；只解析本地源码，不执行 Player 或网络操作。
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


class CompatibilityTests(unittest.TestCase):
    """核对语法基线，避免只在维护机器较新解释器上通过。"""

    # 功能：用 Python 3.10 文法解析公共源码；参数无，测试不写源码或执行游戏。
    def test_public_modules_accept_python_310_grammar(self) -> None:
        script_root: Path = Path(__file__).resolve().parent.parent
        sources: list[Path] = sorted(script_root.glob("*.py"))
        self.assertTrue(sources)
        for source in sources:
            with self.subTest(module=source.name):
                content: str = source.read_text(encoding="utf-8-sig")
                ast.parse(content, filename=source.name, feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
