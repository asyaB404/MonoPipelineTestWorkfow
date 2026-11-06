"""创建日期：2026-10-26；作者：Cyou。
功能：标准库隔离测试入口，输出实际通过/失败/错误/跳过数量；参数：可选 unittest 名称。
边界：仅本包临时文件及内存/假 HTTP，无 Unity/Player/安装/上传。
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

# 入口在导入任何包内模块前禁用字节码，避免未带 -B 运行时生成 __pycache__ 导致交付自检拒绝全部 CLI 命令。
sys.dont_write_bytecode = True

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.tests"


# 功能：真正执行隔离测试并给出数量；参数 argv 可指定包内测试名，不启用运行时旁路。
def main(argv: list[str] | None = None) -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")
    names: list[str] = sys.argv[1:] if argv is None else argv
    loader: unittest.TestLoader = unittest.TestLoader()
    suite: unittest.TestSuite = loader.loadTestsFromNames(names) if names else loader.discover(
        str(Path(__file__).parent), pattern="test_*.py", top_level_dir=str(Path(__file__).resolve().parents[2]),
    )
    result: unittest.TestResult = unittest.TextTestRunner(verbosity=2).run(suite)
    failures: int = len(result.failures)
    errors: int = len(result.errors)
    skipped: int = len(result.skipped)
    passed: int = result.testsRun - failures - errors - skipped
    print(f"ISOLATED_RESULT total={result.testsRun} passed={passed} failures={failures} errors={errors} skipped={skipped}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
