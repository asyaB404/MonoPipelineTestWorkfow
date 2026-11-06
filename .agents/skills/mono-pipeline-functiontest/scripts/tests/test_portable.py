"""创建日期：2026-10-26；作者：Cyou。
功能：导入无副作用、正式 CLI 无测试旁路、文档/模板与阻断原工程的实际迁移验证。
参数：仅本目录、临时目录和隔离 CPython 子进程；不启动/连接 Unity 或 Player。
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from ..cli import main
from ..contracts import JsonObject, JsonValue, Limits, canonical, strict_json
from .support import Fixture, readonly_case

SKILL_ROOT: Path = Path(__file__).resolve().parents[2]

IMPORT_DRIVER = '''# 创建日期：2026-10-26；作者：Cyou；功能：隔离导入审查；参数：当前 Skill 根。
import sys, importlib, json
root: str = sys.argv[1]
sys.path.insert(0, root)
hits: list[str] = []
# 功能：拒绝导入期网络/进程副作用；参数 event/args 是 Python 审计事件。
def guard(event: str, args: tuple[object, ...]) -> None:
    if event.startswith("socket.") or event == "subprocess.Popen" or event == "os.system":
        hits.append(event)
        raise RuntimeError("forbidden import side effect")
sys.addaudithook(guard)
names: list[str] = ["contracts", "inputs", "pipeline", "session", "evidence", "report", "cli", "delivery"]
for name in names:
    importlib.import_module("scripts." + name)
print(json.dumps({"modules": len(names), "side_effects": hits}))
'''

RELOCATION_DRIVER = '''# 创建日期：2026-10-26；作者：Cyou；功能：原项目不可访问迁移验证；参数：复制根/原根/临时输入和输出。
import sys, json, pathlib, contextlib, io, importlib
new_root, old_root, cases, target, output = sys.argv[1:]
blocked: list[str] = []
side_effects: list[str] = []
# 功能：真正阻断原工程和任何真实网络/进程操作；参数 event/args 是 Python 审计事件。
def guard(event: str, args: tuple[object, ...]) -> None:
    if event == "open" and args and isinstance(args[0], str):
        path = str(pathlib.Path(args[0]).absolute()).casefold()
        if path.startswith(str(pathlib.Path(old_root).absolute()).casefold()):
            blocked.append("old_project")
            raise PermissionError("old project access forbidden")
    if event.startswith("socket.") or event == "subprocess.Popen" or event == "os.system":
        side_effects.append(event)
        raise RuntimeError("real network/process operation forbidden")
sys.addaudithook(guard)
try:
    open(str(pathlib.Path(old_root) / "must_not_be_accessible"), "rb")
except PermissionError:
    pass
else:
    raise AssertionError("old root was not blocked")
sys.path.insert(0, new_root)
from scripts.cli import main
from scripts.contracts import JsonObject
# 功能：实际调用持久 CLI 并解析安全结果；参数 args 是本次有效 CLI 参数。
def call(args: list[str]) -> tuple[int, JsonObject]:
    stream: io.StringIO = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main(args)
    value = json.loads(stream.getvalue().splitlines()[-1])
    return code, value
code, initialized = call(["init", "--cases", cases, "--target", target, "--output", output])
assert code == 0 and initialized["ok"]
run = initialized["result"]["run"]
assert call(["status", "--run", run])[0] == 0
assert call(["start-case", "--run", run, "--case-id", "R-1"])[0] == 0
final = pathlib.Path(output).parent / "relocated-final.json"
final.write_text(json.dumps({"status":"blocked", "category":"permission", "required_permission":"script_execute", "reason":"temporary fixture has no script permission"}), encoding="utf-8")
code, finished = call(["final", "--run", run, "--request", str(final)])
assert code == 3 and finished["result"]["status"] == "blocked"
assert call(["close", "--run", run])[0] == 0
code, audited = call(["audit", "--run", run])
assert code == 0 and audited["result"]["counts"]["blocked"] == 1
code, report = call(["report", "--run", run])
assert code == 0
report_path = pathlib.Path(run) / report["result"]["report"]["path"]
assert report_path.is_file()
for name in ["contracts", "inputs", "pipeline", "session", "evidence", "report", "cli", "delivery"]:
    module = importlib.import_module("scripts." + name)
    assert pathlib.Path(module.__file__).is_relative_to(pathlib.Path(new_root))
print(json.dumps({"counts":audited["result"]["counts"], "blocked_old_project":len(blocked), "side_effects":side_effects, "report":str(report_path)}))
'''


# 功能：以当前 py -3.13 解析出的真实 CPython 执行隔离驱动；参数 driver/args 都在临时目录。
def execute_driver(directory: Path, content: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    path: Path = directory / "isolated-driver.py"
    path.write_text(content, encoding="utf-8")
    environment: dict[str, str] = dict(os.environ)
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-I", "-B", str(path), *arguments], cwd=directory,
                          env=environment, encoding="utf-8", capture_output=True, timeout=45, check=False)


class PortableTests(unittest.TestCase):
    # 功能：所有运行时模块导入不建立网络/子进程；参数 self 为测试实例。
    def test_import_has_no_network_or_process_side_effect(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mpft-import-") as directory:
            result: subprocess.CompletedProcess[str] = execute_driver(Path(directory), IMPORT_DRIVER, [str(SKILL_ROOT)])
            self.assertEqual(result.returncode, 0, result.stderr)
            value: JsonObject = json.loads(result.stdout)
            self.assertEqual(value["modules"], 8)
            self.assertEqual(value["side_effects"], [])

    # 功能：整文件夹复制后真实拒绝原项目访问，仍能 CLI 初始化/审计/唯一报告；参数 self 为测试实例。
    def test_relocation_old_project_unavailable_cli_audit_report(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()], permissions=[])
        self.addCleanup(fixture.cleanup)
        with tempfile.TemporaryDirectory(prefix="mpft-new-project-") as directory:
            temporary: Path = Path(directory)
            copied: Path = temporary / "mono-pipeline-functiontest"
            shutil.copytree(SKILL_ROOT, copied, ignore=shutil.ignore_patterns("__pycache__"))
            old_project: Path = SKILL_ROOT.parents[2]
            result: subprocess.CompletedProcess[str] = execute_driver(temporary, RELOCATION_DRIVER,
                [str(copied), str(old_project), str(fixture.cases_file), str(fixture.target_file), str(temporary / "outputs")])
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            value: JsonObject = json.loads(result.stdout)
            self.assertEqual(value["blocked_old_project"], 1)
            self.assertEqual(value["side_effects"], [])
            self.assertEqual(value["counts"]["blocked"], 1)
            self.assertEqual(value["counts"]["passed"], 0)
            self.assertTrue(Path(value["report"]).is_file())

    # 功能：正式 CLI 没有任何测试/身份/传输旁路，误传令牌不回显；参数 self 为测试实例。
    def test_cli_rejects_bypass_and_token_arguments(self) -> None:
        for flag in ("--bypass", "--test-mode", "--host", "--port", "--token"):
            stream: io.StringIO = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code: int = main(["status", "--run", "not-a-run", flag, "private-argument-value"])
            self.assertEqual(code, 2)
            self.assertNotIn("private-argument-value", stream.getvalue())

    # 功能：公共模块仅 8、显式类型、无旧项目导入和绝对工程路径；参数 self 为测试实例。
    def test_runtime_module_boundaries_and_types(self) -> None:
        paths: list[Path] = [path for path in (SKILL_ROOT / "scripts").glob("*.py") if path.name != "__init__.py"]
        self.assertEqual(len(paths), 8)
        self.assertIn("delivery.py", [path.name for path in paths])
        for path in paths:
            with self.subTest(path=path.name):
                source: str = path.read_text(encoding="utf-8")
                tree: ast.Module = ast.parse(source)
                self.assertIn("2026-10-26", source.splitlines()[0])
                self.assertIn("Cyou", source[:150])
                self.assertNotIn("Tools/AI", source)
                self.assertNotIn("GameClient", source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        self.assertFalse(node.module is not None and node.module.startswith(("Tools", "functiontest_runtime", "unity_functiontest")))
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        self.assertNotIn(node.id, {"var", "any", "Any"})
                    if isinstance(node, ast.AnnAssign):
                        self.assertFalse(any(isinstance(child, ast.Name) and child.id == "Any" for child in ast.walk(node.annotation)))

    # 功能：核心 YAML 仅 name/description，正文少于 500 行，所有 Markdown 文件链接真实包内；参数 self 为测试实例。
    def test_skill_frontmatter_and_markdown_links(self) -> None:
        path: Path = SKILL_ROOT / "SKILL.md"
        source: str = path.read_text(encoding="utf-8")
        pieces: list[str] = source.split("---", 2)
        self.assertEqual(pieces[0], "")
        keys: set[str] = {line.split(":", 1)[0].strip() for line in pieces[1].splitlines() if ":" in line}
        self.assertEqual(keys, {"name", "description"})
        self.assertLess(len(pieces[2].splitlines()), 500)
        self.assertNotIn("[TODO:", source)
        for document in SKILL_ROOT.rglob("*.md"):
            if "scripts/tests" in document.as_posix() or document.is_relative_to(SKILL_ROOT / "assets/dependencies"):
                continue
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in link or link.startswith("#"):
                    self.fail("公共说明必须是包内相对引用")
                target: str = unquote(re.sub(r":\d+$", "", link))
                destination: Path = (document.parent / target).resolve()
                self.assertTrue(destination.is_relative_to(SKILL_ROOT))
                self.assertTrue(destination.is_file(), document.name + " -> " + link)

    # 功能：模板 JSON 真实严格解析、有头注释且默认没有目标/业务授权；参数 self 为测试实例。
    def test_templates_are_strict_and_unauthorized_by_default(self) -> None:
        for path in (SKILL_ROOT / "assets/templates").glob("*.json"):
            value: JsonValue = strict_json(path.read_bytes(), Limits().input_bytes)
            self.assertIsInstance(value, dict)
            self.assertIn("2026-10-26", value["_comment"])
            self.assertIn("Cyou", value["_comment"])
        target: JsonObject = json.loads((SKILL_ROOT / "assets/templates/target.json").read_text(encoding="utf-8"))
        self.assertFalse(target["license"]["accepted"])
        self.assertEqual(target["permissions"], [])
        self.assertNotIn("token", target)
        self.assertNotIn("evalToken", target)
