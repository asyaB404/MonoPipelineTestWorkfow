"""创建日期：2026-10-27；作者：Cyou。
功能：包库存和附加前核验的空成员一致性回归，保留核心非空、摘要、完整集合和预算守卫。
基础参数：临时假静态包/同包 C# 源；不构建、连接、启动或修改真实游戏包。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import cast

from .. import delivery
from ..contracts import EnvironmentBlocked, JsonObject, JsonValue, Limits, canonical, digest, object_value, strict_json
from ..inputs import parse_target
from ..pipeline import _file_hash, verify_package
from .support import Fixture
from .test_unity_payload import method_body

ROOT: Path = Path(__file__).resolve().parents[2]


class EmptyPackageMemberTests(unittest.TestCase):
    # 功能：准备每例独享临时包与明确目标；参数无，不使用真实进程。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture()
        self.addCleanup(self.fixture.cleanup)
        self.target = parse_target(strict_json(self.fixture.target_file.read_bytes(), Limits().input_bytes), self.fixture.root)

    # 功能：仅在夹具写入成员及一致清单；参数 name 为相对名，content 为本例精确字节。
    def record_member(self, name: str, content: bytes) -> Path:
        path: Path = self.fixture.package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        manifest: JsonObject = object_value(strict_json(self.fixture.manifest.read_bytes(), Limits().input_bytes), "fixture manifest")
        files: list[JsonValue] = [item for item in cast(list[JsonValue], manifest["files"])
                                 if object_value(item, "fixture member")["path"] != name]
        files.append({"path": name, "bytes": len(content), "sha256": digest(content)})
        manifest["files"] = files
        self.fixture.manifest.write_bytes(canonical(manifest))
        return path

    # 功能：可选空成员纳入扫描/摘要/附加前静态核验；参数为临时标记，不证明业务资源有效。
    def test_optional_empty_member_is_included_hashed_and_verified(self) -> None:
        name: str = "Fixture_Data/StreamingAssets/empty.marker"
        path: Path = self.record_member(name, b"")
        checksum, size = _file_hash(path, Limits().package_file_bytes)
        self.assertEqual((checksum, size), (digest(b""), 0))
        records, gaps = delivery.package_snapshot(self.fixture.exe)
        entries: dict[str, JsonObject] = delivery.entries(records)
        self.assertEqual((entries[name]["bytes"], entries[name]["sha256"]), (0, digest(b"")))
        self.assertEqual(gaps, [])
        self.assertTrue(verify_package(self.target)["complete_static_files"])
        self.assertEqual(self.fixture.world.transport_count, 0)

    # 功能：一致清单也不能把空核心库判为完整包；参数仅临时 Unity 主库。
    def test_empty_required_member_remains_blocked(self) -> None:
        self.record_member("UnityPlayer.dll", b"")
        with self.assertRaisesRegex(EnvironmentBlocked, "静态包必要成员为空"):
            verify_package(self.target)
        _, gaps = delivery.package_snapshot(self.fixture.exe)
        self.assertIn("zero_byte_required_member:UnityPlayer.dll", gaps)

    # 功能：空 EXE 保留关键成员和 MZ 缺口；参数只写不可执行的夹具文件。
    def test_empty_executable_remains_blocked(self) -> None:
        self.record_member(self.fixture.exe.name, b"")
        with self.assertRaises(EnvironmentBlocked):
            verify_package(self.target)
        _, gaps = delivery.package_snapshot(self.fixture.exe)
        self.assertIn("zero_byte_required_member:" + self.fixture.exe.name, gaps)
        self.assertIn("exe_has_no_windows_mz_signature", gaps)

    # 功能：空成员变为非空但旧清单不变仍拒绝；参数不允许修改摘要绕过。
    def test_empty_member_tamper_remains_blocked(self) -> None:
        path: Path = self.record_member("optional.marker", b"")
        path.write_bytes(b"changed")
        with self.assertRaises(EnvironmentBlocked):
            verify_package(self.target)

    # 功能：未登记空成员仍属于额外文件；参数不跳过空文件集合核验。
    def test_undeclared_empty_member_remains_blocked(self) -> None:
        (self.fixture.package / "unregistered.marker").write_bytes(b"")
        with self.assertRaisesRegex(EnvironmentBlocked, "未登记或缺失"):
            verify_package(self.target)

    # 功能：不提高真实预算，小型模拟超额文件仍拒绝；参数本例上限为 1 字节。
    def test_file_byte_ceiling_remains_enforced(self) -> None:
        path: Path = self.record_member("over.marker", b"ab")
        with self.assertRaises(EnvironmentBlocked):
            _file_hash(path, 1)

    # 功能：公共库存源使用非负大小并提供路径/实际字节/上限；参数只是源静态契约。
    def test_csharp_inventory_preserves_empty_members_and_diagnostics(self) -> None:
        source: str = (ROOT / "assets/unity/Editor/MonoPipelineBuildSupport.cs").read_text(encoding="utf-8-sig")
        body: str = method_body(source, "private static List<object> ScanPackage(")
        self.assertIn("bytes < 0 || bytes > MaximumPackageFileBytes", body)
        self.assertIn('"path", relative', body)
        self.assertIn('"bytes", bytes', body)
        self.assertIn('"sha256", FileHash(path)', body)
        self.assertIn("package_member_byte_budget_invalid: path=", body)
        self.assertIn('"; bytes="', body)
        self.assertIn('"; max="', body)
