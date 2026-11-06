"""创建日期：2026-10-26；作者：Cyou。
功能：清单/ZIP/导出/离线接入/库存/公开目标准备和原目录不可访问的真实隔离测试。
参数：临时假 Unity 根、内存身份与不可运行假包；真实原归档只解析或复制到临时目录，不安装/编译/连接 Player。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, cast
from unittest import mock

from .. import delivery
from ..cli import main
from ..contracts import EnvironmentBlocked, InputError, IntegrityError, JsonObject, JsonValue, canonical, digest
from ..inputs import parse_target
from ..pipeline import IdentityHooks, verify_package
from .support import Fixture

SKILL_ROOT: Path = Path(__file__).resolve().parents[2]


# 功能：生成内存 ZIP 的攻击/合法样本；参数 members 只在隔离内存使用，不写项目。
def archive_bytes(members: list[tuple[str | zipfile.ZipInfo, bytes]]) -> bytes:
    stream: io.BytesIO = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)
    return stream.getvalue()


class DeliveryFixture:
    """自有临时交付/假 Unity 根；小型 ZIP 是明确隔离夹具，真实原归档的验证单独保留。"""

    # 功能：复制完整同包源码并可替换为微型纯测试归档；参数 real_archives=True 才保留真实已授权归档。
    def __init__(self, real_archives: bool = False) -> None:
        self.temporary: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="mpft-delivery-isolated-")
        self.directory: Path = Path(self.temporary.name)
        self.source: Path = self.directory / "source" / delivery.NAME
        self.source.parent.mkdir()
        ignored: tuple[str, ...] = ("__pycache__",) if real_archives else ("__pycache__", "*.zip")
        shutil.copytree(SKILL_ROOT, self.source, ignore=shutil.ignore_patterns(*ignored))
        self.project: Path = self.directory / "fake-unity"
        for name in ("Assets", "Packages", "ProjectSettings"):
            (self.project / name).mkdir(parents=True)
        (self.project / "ProjectSettings/ProjectVersion.txt").write_bytes(b"m_EditorVersion: 2022.3.62f3\n")
        catalog: JsonObject = json.loads((self.source / delivery.CATALOG).read_text(encoding="utf-8"))
        if not real_archives:
            for value in cast(list[JsonValue], catalog["packages"]):
                package: JsonObject = cast(JsonObject, value)
                metadata: bytes = canonical({"name": package["name"], "version": package["version"], "description": "isolated non-runnable package fixture"})
                payload: dict[str, bytes] = {"package.json": metadata}
                for value in cast(list[JsonValue], package["license_files"]):
                    name: str = str(value)
                    payload[name] = ("fileFormatVersion: 2\nguid: " + digest((str(package["name"]) + "/" + name).encode())[:32] + "\n").encode() if name.endswith(".meta") else b"isolated fake license; no actual installation permission"
                content: bytes = archive_bytes(list(payload.items()))
                archive: JsonObject = cast(JsonObject, package["archive"])
                (self.source / str(archive["path"])).write_bytes(content)
                archive["bytes"] = len(content)
                archive["sha256"] = digest(content)
                package["files"] = [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in payload.items()]
                for name, copy in zip(cast(list[str], package["license_files"]), cast(list[str], package["readable_license_files"])):
                    (self.source / copy).write_bytes(payload[name])
            (self.source / delivery.CATALOG).write_bytes(canonical(catalog))
        self.catalog: JsonObject = catalog
        self.upm: JsonObject = {"dependencies": catalog["engine_modules"], "scopedRegistries": [], "fixture": "preserve this exact unrelated field"}
        self.write_upm()
        self.refresh()

    # 功能：清理自有临时目录；参数无，不清理维护项目或旧资产。
    def cleanup(self) -> None:
        self.temporary.cleanup()

    # 功能：写临时明确 UPM 声明；参数无，其他字段用于精确增量保护测试。
    def write_upm(self) -> None:
        (self.project / "Packages/manifest.json").write_bytes(canonical(self.upm))

    # 功能：测试明确批准维护动作，不因失败自动修复；参数无，只操作临时源。
    def refresh(self) -> JsonObject:
        path: Path = self.source / delivery.MANIFEST
        previous: str | None = digest(path.read_bytes()) if path.exists() else None
        return delivery.refresh_manifest(self.source, True, previous)

    # 功能：运行正常只读预览；参数无，不构建/启动 Unity。
    def preview(self) -> JsonObject:
        return delivery.unity_preview(self.source, self.project)

    # 功能：在自有假 Unity 根批准当前真实计划；参数 backup_name 指向项目/工具之外新目录。
    def apply(self, backup_name: str = "backup") -> JsonObject:
        plan: JsonObject = self.preview()
        return delivery.unity_apply(self.source, self.project, str(plan["plan_sha256"]), True, self.directory / backup_name)


RELOCATION_DRIVER = '''# 创建日期：2026-10-26；作者：Cyou；功能：独立交付的隔离 CLI 验证；参数：新根、不可访问旧根、假项目和输出父目录。
import sys, pathlib, json, io, contextlib, importlib
root, original, moved, old_project, project, directory = sys.argv[1:]
blocked = []
side_effects = []
# 功能：阻断旧根/维护项目及真实网络/进程行为；参数 event/args 是标准库审计事件。
def guard(event: str, args: tuple[object, ...]) -> None:
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        value = str(pathlib.Path(args[0]).absolute()).casefold()
        for forbidden in (original, moved, old_project):
            if value.startswith(str(pathlib.Path(forbidden).absolute()).casefold()):
                blocked.append(value)
                raise PermissionError("source unavailable")
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        side_effects.append(event)
        raise RuntimeError("real network/process forbidden")
sys.addaudithook(guard)
try:
    open(str(pathlib.Path(moved) / "SKILL.md"), "rb")
except PermissionError:
    pass
else:
    raise AssertionError("old source was not denied")
sys.path.insert(0, root)
from scripts.cli import main
# 功能：正常 CLI 调用，不注入运行时旁路；参数 args 为明确离线接口。
def call(args: list[str]) -> dict[str, object]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main(args)
    output = json.loads(stream.getvalue().splitlines()[-1])
    assert code == 0, output
    return output["result"]
print("RELOCATION_STAGE verify", file=sys.stderr, flush=True)
verified = call(["delivery-verify"])
export = pathlib.Path(directory) / "second" / "mono-pipeline-functiontest"
export.parent.mkdir()
print("RELOCATION_STAGE export", file=sys.stderr, flush=True)
exported = call(["delivery-export", "--output", str(export), "--zip", str(pathlib.Path(directory) / "second.zip")])
print("RELOCATION_STAGE preview", file=sys.stderr, flush=True)
preview = call(["unity-preview", "--project", project])
assert not preview["conflicts"]
print("RELOCATION_STAGE apply", file=sys.stderr, flush=True)
applied = call(["unity-apply", "--project", project, "--approve-plan-sha256", preview["plan_sha256"], "--approved", "--backup", str(pathlib.Path(directory) / "external-backup")])
print("RELOCATION_STAGE recheck", file=sys.stderr, flush=True)
again = call(["unity-preview", "--project", project])
assert not again["conflicts"]
assert all(item["mode"] == "skip" for item in again["operations"])
for name in ("contracts", "inputs", "pipeline", "session", "evidence", "report", "cli", "delivery"):
    module = importlib.import_module("scripts." + name)
    assert pathlib.Path(module.__file__).is_relative_to(pathlib.Path(root))
print(json.dumps({"verified":verified["dependency_members"], "exported":str(export), "applied":applied["applied"], "old_denied":len(blocked), "side_effects":side_effects}))
'''


class DeliveryTests(unittest.TestCase):
    # 功能：登记临时夹具清理；参数 real 控制是否解析/复制真实原归档。
    def fixture(self, real: bool = False) -> DeliveryFixture:
        result: DeliveryFixture = DeliveryFixture(real)
        self.addCleanup(result.cleanup)
        return result

    # 功能：核验当前真实同包归档/版本/来源与精确规模；参数无，不解压到当前 Unity 工程。
    def test_real_authorized_archives_complete_and_exact_scale(self) -> None:
        result: JsonObject = delivery.verify_delivery(SKILL_ROOT)
        catalog, expanded = delivery.dependency_catalog(SKILL_ROOT)
        self.assertEqual(result["dependency_archives"], 7)
        self.assertEqual(result["dependency_members"], 2599)
        self.assertEqual(result["dependency_expanded_bytes"], 30336422)
        self.assertEqual(sum(cast(int, cast(JsonObject, value)["archive"]["bytes"]) for value in cast(list[JsonValue], catalog["packages"])), 9245072)
        self.assertNotIn("com.code-philosophy.hybridclr", expanded)
        self.assertNotIn("com.unity.textmeshpro", expanded)

    # 功能：改写/额外/缺失内容严格拒收；参数每个攻击只改自有临时源码。
    def test_manifest_rejects_rewrite_extra_and_missing(self) -> None:
        for attack in ("rewrite", "extra", "missing"):
            fixture: DeliveryFixture = self.fixture()
            path: Path = fixture.source / "scripts/inputs.py"
            if attack == "rewrite":
                path.write_bytes(path.read_bytes() + b"\n# changed\n")
            elif attack == "extra":
                (fixture.source / "target.json").write_bytes(b"{}")
            else:
                path.unlink()
            with self.subTest(attack=attack), self.assertRaises(IntegrityError):
                delivery.verify_delivery(fixture.source)

    # 功能：清单重复/大小写/绝对/穿越/未知字段均拒绝；参数不让生成动作掩盖失败。
    def test_manifest_rejects_control_and_path_attacks(self) -> None:
        for attack in ("duplicate", "case", "absolute", "traversal", "unknown"):
            fixture: DeliveryFixture = self.fixture()
            path: Path = fixture.source / delivery.MANIFEST
            value: JsonObject = json.loads(path.read_bytes())
            records: list[JsonValue] = cast(list[JsonValue], value["files"])
            if attack in {"duplicate", "case"}:
                item: JsonObject = dict(cast(JsonObject, records[0]))
                if attack == "case": item["path"] = str(item["path"]).upper()
                records.append(item)
            elif attack == "unknown":
                value["auto_repair"] = True
            else:
                cast(JsonObject, records[0])["path"] = "C:/forbidden" if attack == "absolute" else "../forbidden"
            path.write_bytes(canonical(value))
            with self.subTest(attack=attack), self.assertRaises((InputError, IntegrityError)):
                delivery.verify_delivery(fixture.source)

    # 功能：刷新需要明确维护者批准和原 SHA；参数在临时源验证失败不会自动刷新。
    def test_refresh_requires_separate_approval_and_existing_hash(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        old: str = digest((fixture.source / delivery.MANIFEST).read_bytes())
        with self.assertRaises(InputError): delivery.refresh_manifest(fixture.source, False, old)
        with self.assertRaises(IntegrityError): delivery.refresh_manifest(fixture.source, True, "0" * 64)
        with self.assertRaises(IntegrityError): delivery.refresh_manifest(fixture.source, True)
        (fixture.source / "scripts/inputs.py").write_bytes((fixture.source / "scripts/inputs.py").read_bytes() + b"\n# isolated maintainer change\n")
        with self.assertRaises(IntegrityError): delivery.verify_delivery(fixture.source)
        self.assertEqual(digest((fixture.source / delivery.MANIFEST).read_bytes()), old)
        delivery.refresh_manifest(fixture.source, True, old)
        delivery.verify_delivery(fixture.source)

    # 功能：ZIP 成员穿越/绝对/重复/大小写/链接拒收；参数全部在内存。
    def test_zip_path_duplicate_case_and_symlink_attacks(self) -> None:
        symlink: zipfile.ZipInfo = zipfile.ZipInfo("link")
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        attacks: list[list[tuple[str | zipfile.ZipInfo, bytes]]] = [
            [("../escape", b"x")], [("C:/escape", b"x")], [("/escape", b"x")], [("a\\b", b"x")],
            [("one", b"x"), ("one", b"y")], [("a/x", b"x"), ("A/y", b"y")],
            [("one", b"x"), ("one/child", b"y")], [(symlink, b"target")],
        ]
        for index, attack in enumerate(attacks):
            raw: bytes = archive_bytes(attack)
            if index == 3:
                # Windows ZIP writer 会预先规范化字符串，改写等长中心目录/本地头才是真实原名称攻击。
                raw = archive_bytes([("a/b", b"x")]).replace(b"a/b", b"a\\b")
            with self.subTest(index=index), self.assertRaises((InputError, IntegrityError)):
                delivery.zip_members(raw)

    # 功能：ZIP 实际摘要/额外/缺失成员拒收；参数严格清单来源是独立预期。
    def test_zip_digest_extra_and_missing(self) -> None:
        expected: dict[str, JsonObject] = {"one": {"path": "one", "bytes": 1, "sha256": digest(b"x")}}
        for members in ([('one', b'y')], [('one', b'x'), ('extra', b'x')], [('other', b'x')]):
            with self.assertRaises(IntegrityError): delivery.zip_members(archive_bytes(members), expected)

    # 功能：目录与 ZIP 新导出完整且同摘要；参数输出仅在临时根。
    def test_export_directory_zip_and_no_overwrite_or_nested_destination(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        parent: Path = fixture.directory / "export"
        parent.mkdir()
        destination: Path = parent / delivery.NAME
        zip_path: Path = fixture.directory / "export.zip"
        result: JsonObject = delivery.export_delivery(fixture.source, destination, zip_path)
        self.assertEqual(delivery.verify_delivery(destination)["manifest_sha256"], result["manifest_sha256"])
        self.assertEqual(delivery.verify_zip(zip_path)["manifest_sha256"], result["manifest_sha256"])
        with self.assertRaises(InputError): delivery.export_delivery(fixture.source, destination)
        with self.assertRaises(InputError): delivery.export_delivery(fixture.source, fixture.source / delivery.NAME)
        with self.assertRaises(InputError): delivery.export_delivery(fixture.source, fixture.directory / "wrong-root")

    # 功能：仅目录导出遭遇一次已确认 Windows 发布拒绝后仍完整发布；参数只影响自有暂存目录。
    @unittest.skipUnless(os.name == "nt", "Windows directory publication regression requires Windows")
    def test_export_directory_only_handles_transient_publish_denial(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        parent: Path = fixture.directory / "export-only"
        parent.mkdir()
        destination: Path = parent / delivery.NAME
        original: Callable[[Path, Path], None] = delivery.os.rename
        attempts: int = 0

        # 功能：仅第一次改名返回拒绝，后续调用真实文件系统；参数为本测试暂存/新目的地。
        def rename(source: Path, target: Path) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise PermissionError(13, "isolated publication denial", str(source), 5, str(target))
            original(source, target)

        with mock.patch.object(delivery.os, "rename", side_effect=rename):
            result: JsonObject = delivery.export_delivery(fixture.source, destination)
        self.assertEqual(attempts, 2)
        self.assertIsNone(result["zip"])
        self.assertEqual(delivery.verify_delivery(destination)["manifest_sha256"], result["manifest_sha256"])

    # 功能：备份目录暂时共享冲突不导致重复写入目标；参数仅为自有假项目和外部新备份。
    @unittest.skipUnless(os.name == "nt", "Windows directory publication regression requires Windows")
    def test_apply_backup_handles_transient_publication_lock(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        original: Callable[[Path, Path], None] = delivery.os.rename
        attempts: int = 0

        # 功能：仅备份第一次发布返回共享冲突，其后真实改名；参数不触碰维护项目。
        def rename(source: Path, target: Path) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise PermissionError(13, "isolated publication lock", str(source), 32, str(target))
            original(source, target)

        with mock.patch.object(delivery.os, "rename", side_effect=rename):
            result: JsonObject = fixture.apply()
        self.assertEqual(attempts, 2)
        self.assertTrue(result["applied"])
        self.assertEqual(result["added_or_patched"], len(fixture.preview()["operations"]))
        self.assertTrue(all(item["mode"] == "skip" for item in fixture.preview()["operations"]))

    # 功能：发布锁等待只有一个总起点，预算耗尽保留暂存和不发布；参数为毫秒级纯测试时钟。
    @unittest.skipUnless(os.name == "nt", "Windows directory publication regression requires Windows")
    def test_directory_publication_wait_budget_does_not_restart(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        source: Path = fixture.directory / "private-stage"
        source.mkdir()
        destination: Path = fixture.directory / "new-directory"
        elapsed: list[float] = [0.0]
        error: PermissionError = PermissionError(13, "isolated publication lock", str(source), 32, str(destination))

        # 功能：只推进本测试虚拟时钟；参数 duration 是本次宿主侧等待，不睡眠或推进游戏。
        def sleep(duration: float) -> None:
            elapsed[0] += duration

        with mock.patch.object(delivery, "DIRECTORY_PUBLISH_TIMEOUT_MS", 5), \
                mock.patch.object(delivery, "DIRECTORY_PUBLISH_INTERVAL_MS", 2), \
                mock.patch.object(delivery.time, "perf_counter", side_effect=lambda: elapsed[0]), \
                mock.patch.object(delivery.time, "sleep", side_effect=sleep), \
                mock.patch.object(delivery.os, "rename", side_effect=error) as rename:
            with self.assertRaises(IntegrityError):
                delivery.publish_directory(source, destination)
        self.assertLessEqual(elapsed[0], 0.005)
        self.assertLessEqual(rename.call_count, 4)
        self.assertTrue(source.is_dir())
        self.assertFalse(destination.exists())

    # 功能：等待期间被外部占用的新路径必须保留，不覆盖或清除；参数仅为自有临时目录。
    @unittest.skipUnless(os.name == "nt", "Windows directory publication regression requires Windows")
    def test_directory_publication_wait_preserves_external_destination(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        source: Path = fixture.directory / "private-stage"
        source.mkdir()
        destination: Path = fixture.directory / "occupied-directory"

        # 功能：模拟第一次拒绝时外部独立创建目的地；参数仍为本测试临时路径。
        def occupied(stage: Path, target: Path) -> None:
            target.mkdir()
            (target / "external.txt").write_bytes(b"external content must be preserved")
            raise PermissionError(13, "isolated publication lock", str(stage), 5, str(target))

        with mock.patch.object(delivery.time, "sleep"), \
                mock.patch.object(delivery.os, "rename", side_effect=occupied) as rename:
            with self.assertRaises(IntegrityError):
                delivery.publish_directory(source, destination)
        self.assertEqual(rename.call_count, 1)
        self.assertEqual((destination / "external.txt").read_bytes(), b"external content must be preserved")
        self.assertTrue(source.is_dir())

    # 功能：路径预算按 UTF-16 单位而非 Python 字符数核对；参数仅计算候选名，不创建超长路径。
    @unittest.skipUnless(os.name == "nt", "Windows compatible path budget requires Windows")
    def test_windows_path_budget_counts_utf16_units(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        delivery.require_windows_path_budget(fixture.project / "Assets/short.txt", temporary_file=True)
        parent: Path = fixture.directory / ("界" * 30 + "\U0001f9ea" * 80)
        self.assertLess(len(str(parent)), 247)
        with self.assertRaises(EnvironmentBlocked) as rejected:
            delivery.require_windows_path_budget(parent / "file.txt")
        self.assertIn("UTF-16", str(rejected.exception))

    # 功能：备份落点的暂存路径超限时，在复制任何文件之前明确阻塞并清理空暂存目录。
    @unittest.skipUnless(os.name == "nt", "Windows compatible path budget requires Windows")
    def test_apply_backup_path_budget_blocks_before_file_writes(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        length: int = 190 - len(str(fixture.directory)) - 1
        self.assertGreater(length, 0)
        parent: Path = fixture.directory / ("b" * length)
        parent.mkdir()
        backup: Path = parent / "new-backup"
        before: dict[str, bytes] = {path.relative_to(fixture.project).as_posix(): path.read_bytes()
                                   for path in fixture.project.rglob("*") if path.is_file()}
        plan: JsonObject = fixture.preview()
        stream: io.StringIO = io.StringIO()
        with mock.patch.object(delivery, "skill_root", return_value=fixture.source), contextlib.redirect_stdout(stream):
            code: int = main(["unity-apply", "--project", str(fixture.project), "--approve-plan-sha256", str(plan["plan_sha256"]),
                              "--approved", "--backup", str(backup)])
        result: JsonObject = json.loads(stream.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(result["error_kind"], "EnvironmentBlocked")
        self.assertIn("Windows", result["message"])
        self.assertFalse(backup.exists())
        self.assertEqual(list(parent.iterdir()), [])
        after: dict[str, bytes] = {path.relative_to(fixture.project).as_posix(): path.read_bytes()
                                  for path in fixture.project.rglob("*") if path.is_file()}
        self.assertEqual(after, before)

    # 功能：长工程路径在预览前置检查阶段阻塞，不生成可批准的假成功计划或复制目标文件。
    @unittest.skipUnless(os.name == "nt", "Windows compatible path budget requires Windows")
    def test_preview_project_path_budget_blocks_before_integration(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        length: int = 180 - len(str(fixture.directory)) - 1
        self.assertGreater(length, 0)
        project: Path = fixture.directory / ("p" * length)
        for folder in ("Assets", "Packages", "ProjectSettings"):
            (project / folder).mkdir(parents=True)
        (project / "ProjectSettings/ProjectVersion.txt").write_bytes(b"m_EditorVersion: 2022.3.62f3\n")
        (project / "Packages/manifest.json").write_bytes(canonical(fixture.upm))
        with self.assertRaises(EnvironmentBlocked):
            delivery.unity_preview(fixture.source, project)
        self.assertEqual(len([path for path in project.rglob("*") if path.is_file()]), 2)
        self.assertEqual(list((project / "Assets").iterdir()), [])

    # 功能：发布失败不留下半成品，源变化不能继续；参数模拟只影响临时目录。
    def test_export_publish_failure_and_source_change_cleanup(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        parent: Path = fixture.directory / "export"
        parent.mkdir()
        destination: Path = parent / delivery.NAME
        with mock.patch.object(delivery.os, "rename", side_effect=OSError("isolated publish failure")):
            with self.assertRaises(OSError): delivery.export_delivery(fixture.source, destination)
        self.assertFalse(destination.exists())
        self.assertEqual(list(parent.iterdir()), [])
        original: object = delivery.verify_delivery
        count: int = 0
        # 功能：在已暂存后改变源；参数 root 决定只改临时源，不修改维护目录。
        def changed(root: Path) -> JsonObject:
            nonlocal count
            count += 1
            result: JsonObject = cast(object, original)(root)
            if count == 2:
                path: Path = fixture.source / "scripts/inputs.py"
                path.write_bytes(path.read_bytes() + b"\n# changed during export\n")
            return result
        with mock.patch.object(delivery, "verify_delivery", side_effect=changed):
            with self.assertRaises(IntegrityError): delivery.export_delivery(fixture.source, destination)
        self.assertFalse(destination.exists())

    # 功能：Windows junction 重解析点不能被导出/接入；参数仅为自有临时目录，不需要安装工具。
    @unittest.skipUnless(os.name == "nt", "Windows junction assertion requires Windows")
    def test_windows_junction_rejected(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        link: Path = fixture.source / "scripts/junction"
        target: Path = fixture.directory / "link-target"
        target.mkdir()
        result: subprocess.CompletedProcess[str] = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            with self.assertRaises(InputError): delivery.verify_delivery(fixture.source)
        finally:
            link.rmdir()

    # 功能：UPM 增量保留 BOM/未知顶层/原值字节；参数新依赖不重写锁或全文件。
    def test_precise_upm_patch_preserves_unrelated_bytes(self) -> None:
        raw: bytes = b'\xef\xbb\xbf{\r\n  "other" : [1, 2],\r\n  "dependencies": {"com.unity.pipeline" : "0.6.0-exp.1-unity2022"},\r\n  "tail": "preserve spacing"\r\n}\r\n'
        changed: bytes = delivery.patch_dependencies(raw, {"com.unity.pipeline": "file:com.unity.pipeline", "com.unity.ugui": "file:com.unity.ugui"})
        self.assertTrue(changed.startswith(b'\xef\xbb\xbf{\r\n  "other" : [1, 2],\r\n'))
        self.assertTrue(changed.endswith(b',\r\n  "tail": "preserve spacing"\r\n}\r\n'))
        self.assertEqual(json.loads(changed.decode("utf-8-sig"))["dependencies"]["com.unity.ugui"], "file:com.unity.ugui")

    # 功能：预览不写，apply 精确接入后兼容跳过且锁文件原字节不变；参数只操作假 Unity 根。
    def test_preview_readonly_apply_backup_then_compatible_skip(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        lock: Path = fixture.project / "Packages/packages-lock.json"
        lock.write_bytes(b'{"dependencies":{}, "isolated":true}\r\n')
        before: bytes = (fixture.project / "Packages/manifest.json").read_bytes()
        original_lock: bytes = lock.read_bytes()
        plan: JsonObject = fixture.preview()
        self.assertEqual(plan["conflicts"], [])
        self.assertFalse((fixture.project / delivery.UNITY_ROOT).exists())
        self.assertEqual((fixture.project / "Packages/manifest.json").read_bytes(), before)
        result: JsonObject = fixture.apply()
        self.assertTrue(result["applied"])
        self.assertFalse(result["unity_compiled_or_player_verified"])
        self.assertEqual(lock.read_bytes(), original_lock)
        self.assertEqual((fixture.directory / "backup/original/Packages/manifest.json").read_bytes(), before)
        again: JsonObject = fixture.preview()
        self.assertEqual(again["conflicts"], [])
        self.assertTrue(all(cast(JsonObject, value)["mode"] == "skip" for value in cast(list[JsonValue], again["operations"])))
        skipped: JsonObject = fixture.apply("backup-skipped")
        self.assertFalse(skipped["applied"])
        self.assertFalse((fixture.directory / "backup-skipped").exists())

    # 功能：无额外批准/错误摘要/目标变化/源变化均停止；参数不触碰当前工程。
    def test_apply_requires_approval_and_rejects_plan_target_source_changes(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        plan: JsonObject = fixture.preview()
        backup: Path = fixture.directory / "backup"
        with self.assertRaises(InputError): delivery.unity_apply(fixture.source, fixture.project, str(plan["plan_sha256"]), False, backup)
        with self.assertRaises(IntegrityError): delivery.unity_apply(fixture.source, fixture.project, "0" * 64, True, backup)
        (fixture.project / "Assets/new.cs").write_bytes(b"// isolated newly appeared source\n")
        with self.assertRaises(IntegrityError): delivery.unity_apply(fixture.source, fixture.project, str(plan["plan_sha256"]), True, backup)
        (fixture.project / "Assets/new.cs").unlink()
        (fixture.source / "assets/unity/GlobalMonoPipelineTest.cs").write_bytes(b"// isolated source changed\n")
        with self.assertRaises(IntegrityError): delivery.unity_apply(fixture.source, fixture.project, str(plan["plan_sha256"]), True, backup)
        self.assertFalse(backup.exists())

    # 功能：既有备份/源内或项目内备份均拒绝；参数只试临时路径。
    def test_backup_location_and_existing_protection(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        plan: JsonObject = fixture.preview()
        existed: Path = fixture.directory / "existing"
        existed.mkdir()
        for backup in (existed, fixture.project / "backup", fixture.source / "backup"):
            with self.assertRaises(InputError): delivery.unity_apply(fixture.source, fixture.project, str(plan["plan_sha256"]), True, backup)

    # 功能：旧/未知同名包、布局、双入口和祖先定义保守冲突；参数每次均独立假项目。
    def test_unknown_old_custom_duplicate_and_ancestor_conflicts(self) -> None:
        for attack in ("old", "custom", "duplicate", "ancestor", "metadata"):
            fixture: DeliveryFixture = self.fixture()
            if attack == "old":
                cast(JsonObject, fixture.upm["dependencies"])["com.unity.pipeline"] = "0.5.0"
                fixture.write_upm()
            elif attack == "custom":
                directory: Path = fixture.project / "Packages/custom-pipeline"
                directory.mkdir()
                (directory / "package.json").write_bytes(canonical({"name": "com.unity.pipeline", "version": "0.6.0-exp.1-unity2022"}))
            elif attack == "duplicate":
                (fixture.project / "Assets/other.cs").write_bytes(b"public static class GlobalMonoPipelineTest {}")
            elif attack == "ancestor":
                (fixture.project / "Assets/root.asmdef").write_bytes(b'{"name":"isolated-ancestor"}')
            else:
                directory = fixture.project / delivery.UNITY_ROOT
                directory.mkdir()
                (directory / "GlobalMonoPipelineTest.cs.meta").write_bytes(b"fileFormatVersion: 2\nguid: 11111111111111111111111111111111\n")
            plan: JsonObject = fixture.preview()
            with self.subTest(attack=attack):
                self.assertTrue(plan["conflicts"])
                with self.assertRaises(EnvironmentBlocked): fixture.apply()

    # 功能：写入中失败只恢复自有字节，保留原 manifest 和外部备份审计；参数故障仅注入临时调用。
    def test_apply_failure_restores_owned_files(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        before: bytes = (fixture.project / "Packages/manifest.json").read_bytes()
        original = delivery.publish_file
        count: int = 0
        # 功能：第三次发布前注入故障；参数只指向本夹具计划文件。
        def fail(path: Path, content: bytes, expected: str | None) -> None:
            nonlocal count
            count += 1
            if count == 3: raise OSError("isolated write failure")
            original(path, content, expected)
        with mock.patch.object(delivery, "publish_file", side_effect=fail):
            with self.assertRaises(OSError): fixture.apply()
        self.assertFalse((fixture.project / delivery.UNITY_ROOT).exists())
        self.assertEqual((fixture.project / "Packages/manifest.json").read_bytes(), before)
        result: JsonObject = json.loads((fixture.directory / "backup/result.json").read_bytes())
        self.assertEqual(result["status"], "failed_restore_attempted")
        self.assertGreater(len(cast(list[JsonValue], result["restored"])), 0)

    # 功能：失败恢复检测外部修改不覆写/删除；参数外部字节仅为模拟并保留在假项目。
    def test_apply_failure_preserves_external_changes(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        original = delivery.publish_file
        first: list[Path] = []
        # 功能：第一次成功后改变其字节再失败；参数不接触维护目录。
        def fail(path: Path, content: bytes, expected: str | None) -> None:
            if first:
                first[0].write_bytes(b"external change must remain")
                raise OSError("isolated external interference")
            original(path, content, expected)
            first.append(path)
        with mock.patch.object(delivery, "publish_file", side_effect=fail):
            with self.assertRaises(OSError): fixture.apply()
        self.assertEqual(first[0].read_bytes(), b"external change must remain")
        result: JsonObject = json.loads((fixture.directory / "backup/result.json").read_bytes())
        self.assertIn(first[0].relative_to(fixture.project).as_posix(), result["external_changes_preserved"])

    # 功能：manifest 增量已提交后失败仍按外部原备份恢复，新增包/源只删自有字节；参数仅为假项目最后回执故障。
    def test_apply_failure_after_manifest_patch_restores_original_bytes(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        original = delivery.publish_file
        before: bytes = (fixture.project / "Packages/manifest.json").read_bytes()
        # 功能：阻断最终接入回执；参数此前 manifest 确已变化，不操作维护项目。
        def fail(path: Path, content: bytes, expected: str | None) -> None:
            if path.name == delivery.INTEGRATION_RECEIPT:
                self.assertNotEqual((fixture.project / "Packages/manifest.json").read_bytes(), before)
                raise OSError("isolated receipt failure after manifest patch")
            original(path, content, expected)
        with mock.patch.object(delivery, "publish_file", side_effect=fail):
            with self.assertRaises(OSError): fixture.apply()
        self.assertEqual((fixture.project / "Packages/manifest.json").read_bytes(), before)
        self.assertFalse((fixture.project / delivery.UNITY_ROOT).exists())
        self.assertFalse((fixture.project / "Packages/com.unity.pipeline").exists())
        result: JsonObject = json.loads((fixture.directory / "backup/result.json").read_bytes())
        self.assertIn("Packages/manifest.json", result["restored"])

    # 功能：非法既有包 JSON 和无 GUID 元数据作为明确路径冲突返回；参数只改临时项目。
    def test_malformed_existing_package_and_guid_report_conflicts(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        directory: Path = fixture.project / "Packages/unknown-package"
        directory.mkdir()
        (directory / "package.json").write_bytes(b'{"name":')
        (fixture.project / "Assets/invalid.meta").write_bytes(b"fileFormatVersion: 2\n")
        plan: JsonObject = fixture.preview()
        paths: set[str] = {str(cast(JsonObject, item)["path"]) for item in cast(list[JsonValue], plan["conflicts"])}
        self.assertIn("Packages/unknown-package/package.json", paths)
        self.assertIn("Assets/invalid.meta", paths)

    # 功能：旧/改写接入记录不能接管；参数只改假项目成功记录。
    def test_receipt_and_compatible_source_tampering_rejected(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        fixture.apply()
        path: Path = fixture.project / delivery.INTEGRATION_RECEIPT
        receipt: JsonObject = json.loads(path.read_bytes())
        receipt["delivery_sha256"] = "0" * 64
        path.write_bytes(canonical(receipt))
        self.assertTrue(fixture.preview()["conflicts"])
        path.unlink()
        (fixture.project / delivery.UNITY_ROOT / "GlobalMonoPipelineTest.cs").write_bytes(b"// unknown replacement\n")
        self.assertTrue(fixture.preview()["conflicts"])

    # 功能：真实归档交付移动原临时根并阻断维护项目后 CLI 独立 verify/export/preview/apply；参数无真实 Unity/Player。
    def test_real_relocation_source_moved_unavailable_independent_cli(self) -> None:
        fixture: DeliveryFixture = self.fixture(real=True)
        parent: Path = fixture.directory / "first"
        parent.mkdir()
        relocated: Path = parent / delivery.NAME
        delivery.export_delivery(fixture.source, relocated)
        original: Path = fixture.source
        moved: Path = fixture.source.with_name("unavailable-source")
        fixture.source.rename(moved)
        driver: Path = fixture.directory / "isolation-driver.py"
        driver.write_text(RELOCATION_DRIVER, encoding="utf-8")
        result: subprocess.CompletedProcess[str] = subprocess.run([sys.executable, "-I", "-B", str(driver), str(relocated), str(original), str(moved),
            str(SKILL_ROOT.parents[2]), str(fixture.project), str(fixture.directory)], cwd=fixture.directory,
            capture_output=True, encoding="utf-8", timeout=360, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        value: JsonObject = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(value["verified"], 2599)
        self.assertTrue(value["applied"])
        self.assertEqual(value["old_denied"], 1)
        self.assertEqual(value["side_effects"], [])

    # 功能：正常薄 bat 用显式当前解释器，不使用维护机路径或安装；参数只执行离线 verify。
    @unittest.skipUnless(os.name == "nt", "Windows bat assertion requires Windows")
    def test_windows_bat_explicit_python_and_offline_cli(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        environment: dict[str, str] = dict(os.environ)
        environment["MONO_PIPELINE_PYTHON"] = sys.executable
        result: subprocess.CompletedProcess[str] = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(fixture.source / "mono-pipeline-test.bat"), "delivery-verify"],
            cwd=fixture.directory, env=environment, encoding="utf-8", capture_output=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout.splitlines()[-1])["ok"])

    # 功能：仅扫描实际目录始终 candidate，缺构建来源拒 complete；参数是假包和包外新输出。
    def test_package_scan_stays_candidate_without_build_origin(self) -> None:
        tool: DeliveryFixture = self.fixture()
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        output: Path = fixture.root / "candidate.json"
        result: JsonObject = delivery.package_candidate(tool.source, fixture.exe, output)
        candidate: JsonObject = json.loads(output.read_bytes())
        self.assertFalse(candidate["complete"])
        self.assertIsNone(candidate["build_guid"])
        self.assertIn("successful_build_report_or_authorized_inventory_missing", candidate["acceptance_gaps"])
        self.assertFalse(result["complete"])
        with self.assertRaises(InputError): delivery.package_candidate(tool.source, fixture.exe, fixture.package / "candidate.json")

    # 功能：成功构建库存仍需明确批准并核验全文件；参数 BuildReport/游戏只为不可运行夹具，真实 C# 未执行。
    def test_package_manifest_requires_bound_complete_approval_and_real_hashes(self) -> None:
        tool: DeliveryFixture = self.fixture()
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        records, _ = delivery.package_snapshot(fixture.exe)
        inventory: JsonObject = {"schema": "mono-pipeline-build-inventory/1", "source": "BuildReport", "build_result": "Succeeded", "exe": fixture.exe.name,
            "build_guid": "112233445566778899aabbccddeeff00", "unity_version": "2022.3.62f3", "platform": "WindowsPlayer", "backend": "mono", "development": True,
            "files": records, "report_files": [{**cast(JsonObject, value), "role": "isolated"} for value in records], "report_total_size": sum(cast(int, cast(JsonObject, value)["bytes"]) for value in records),
            "complete_game_delivery": False, "acceptance_gaps": ["isolated not a real build report"]}
        for value in cast(list[JsonValue], inventory["report_files"]): cast(JsonObject, value).pop("sha256")
        inventory_file: Path = fixture.write_json("inventory.json", inventory)
        checksum: str = digest(inventory_file.read_bytes())
        approval: JsonObject = {"schema": "mono-pipeline-package-approval/1", "inventory_sha256": checksum, "accepted": False,
                               "complete_game_delivery": False, "reviewer": "current_agent", "statement": "isolated explicit approval only; no real Unity build acceptance"}
        approval_file: Path = fixture.write_json("approval.json", approval)
        output: Path = fixture.package / delivery.PACKAGE_MANIFEST
        with self.assertRaises(InputError): delivery.prepare_package_manifest(tool.source, fixture.exe, inventory_file, checksum, approval_file, output)
        approval.update({"accepted": True, "complete_game_delivery": True})
        approval_file.write_bytes(canonical(approval))
        with self.assertRaises(IntegrityError): delivery.prepare_package_manifest(tool.source, fixture.exe, inventory_file, "0" * 64, approval_file, output)
        result: JsonObject = delivery.prepare_package_manifest(tool.source, fixture.exe, inventory_file, checksum, approval_file, output)
        manifest: JsonObject = json.loads(output.read_bytes())
        self.assertTrue(manifest["complete"])
        self.assertFalse(result["runtime_verified"])
        target_document: JsonObject = json.loads(fixture.target_file.read_bytes())
        target_document["package_manifest"] = str(output)
        target_document["build_guid"] = manifest["build_guid"]
        self.assertTrue(verify_package(parse_target(target_document, fixture.root))["complete_static_files"])
        with self.assertRaises(InputError): delivery.prepare_package_manifest(tool.source, fixture.exe, inventory_file, checksum, approval_file, output)

    # 功能：静置一分钟的目标准备只保留许可/公开身份及心跳待握手状态，不连接、不回显 token；参数是假 PID/描述符。
    def test_target_prepare_reads_public_identity_no_player_connection_or_auto_permissions(self) -> None:
        tool: DeliveryFixture = self.fixture()
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        request_root: Path = fixture.root / "requests"
        evidence_root: Path = fixture.root / "evidence"
        request_root.mkdir()
        evidence_root.mkdir()
        target_document: JsonObject = json.loads(fixture.target_file.read_bytes())
        permission: JsonObject = {"schema": "mono-pipeline-target-permission/1", "exe": str(fixture.exe), "pid": 123456,
            "license": target_document["license"], "permissions": ["attach", "script_execute"], "evidence_roots": [str(evidence_root)],
            "request_root": str(request_root), "reviewer": "current_agent", "statement": "only temporary fake identity permitted; no Player connection"}
        record: Path = fixture.write_json("permission.json", permission)
        output: Path = fixture.root / "prepared-target.json"
        descriptor: JsonObject = json.loads(fixture.descriptor.read_bytes())
        descriptor["lastHeartbeat"] = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        idle_bytes: bytes = canonical(descriptor)
        fixture.descriptor.write_bytes(idle_bytes)
        result: JsonObject = delivery.prepare_target(tool.source, fixture.exe, 123456, record, output, fixture.manifest, fixture.hooks)
        prepared: JsonObject = json.loads(output.read_bytes())
        self.assertFalse(result["player_connected"])
        self.assertTrue(result["heartbeat_handshake_required"])
        self.assertFalse(result["identity"]["descriptor_fresh"])
        self.assertEqual(fixture.descriptor.read_bytes(), idle_bytes)
        self.assertEqual(prepared["permissions"], ["attach", "script_execute"])
        self.assertTrue(prepared["license"]["accepted"])
        self.assertEqual(prepared["process_created_utc"], fixture.created)
        self.assertNotIn(fixture.world.token, canonical(result).decode())
        self.assertNotIn(fixture.world.token, output.read_text(encoding="utf-8"))
        self.assertEqual(fixture.world.transport_count, 0)
        permission["license"] = {**cast(JsonObject, permission["license"]), "accepted": False}
        record.write_bytes(canonical(permission))
        with self.assertRaises(InputError): delivery.prepare_target(tool.source, fixture.exe, 123456, record, fixture.root / "not-approved.json", fixture.manifest, fixture.hooks)

    # 功能：静态包错误应先拒绝，未授权或 PID 错误不能读描述符；参数记录 hook 调用次数。
    def test_target_prepare_rejects_static_change_before_descriptor_or_identity(self) -> None:
        tool: DeliveryFixture = self.fixture()
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        permissions: JsonObject = {"schema": "mono-pipeline-target-permission/1", "exe": str(fixture.exe), "pid": 123456,
            "license": json.loads(fixture.target_file.read_bytes())["license"], "permissions": ["attach", "script_execute"],
            "evidence_roots": [str(fixture.root)], "request_root": str(fixture.root), "reviewer": "current_agent", "statement": "isolated only"}
        record: Path = fixture.write_json("permission-check.json", permissions)
        calls: list[str] = []
        # 功能：不应被调用的身份/ACL hook；参数只统计，不查询进程或网络。
        def unexpected(*arguments: object) -> JsonObject:
            calls.append("called")
            raise AssertionError("identity called before static rejection")
        (fixture.package / "UnityPlayer.dll").write_bytes(b"changed")
        with self.assertRaises(IntegrityError): delivery.prepare_target(tool.source, fixture.exe, 123456, record, fixture.root / "refused.json", fixture.manifest, IdentityHooks(unexpected, unexpected, unexpected))
        self.assertEqual(calls, [])

    # 功能：正式离线 CLI 可用且未批准 apply 拒绝；参数默认 API 没有新网络旁路。
    def test_offline_cli_dispatch_and_unapproved_apply_exit(self) -> None:
        fixture: DeliveryFixture = self.fixture()
        with mock.patch.object(delivery, "skill_root", return_value=fixture.source):
            stream: io.StringIO = io.StringIO()
            with contextlib.redirect_stdout(stream): code: int = main(["delivery-verify"])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(stream.getvalue())["ok"])
            plan: JsonObject = fixture.preview()
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream): code = main(["unity-apply", "--project", str(fixture.project), "--approve-plan-sha256", str(plan["plan_sha256"]), "--backup", str(fixture.directory / "never-written")])
            self.assertEqual(code, 2)
            self.assertFalse((fixture.directory / "never-written").exists())
