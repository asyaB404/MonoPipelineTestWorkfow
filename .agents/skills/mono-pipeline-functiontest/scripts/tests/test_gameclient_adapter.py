"""创建日期：2026-10-26；作者：Cyou。
功能：同包可选 GameClient 菜单/原管线增量与配置范围重载的静态回归。
基础参数：只读取同包模板，不扫描维护 Assets，不编译或执行 Unity/Player。
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from .. import delivery
from ..contracts import IntegrityError
from .test_unity_payload import method_body

ROOT: Path = Path(__file__).resolve().parents[2]
ADAPTER: Path = ROOT / "assets/adapters/GameClient"


class GameClientAdapterStaticTests(unittest.TestCase):
    # 功能：每例读取固定同包模板；参数无，不读取维护工程。
    def setUp(self) -> None:
        self.source: str = (ADAPTER / "GlobalMonoPipelineGameClientBuild.cs").read_text(encoding="utf-8-sig")

    # 功能：模板仅可选且明确类型/文件头齐全；参数不证明不同项目零适配。
    def test_optional_source_headers_and_explicit_types(self) -> None:
        self.assertIn("2026-10-26", self.source.splitlines()[0])
        self.assertIn("Cyou", self.source.splitlines()[0])
        self.assertIn("基础参数", self.source[:350])
        self.assertNotRegex(self.source, r"\b(?:var|any|dynamic)\s+\w+")
        self.assertTrue((ADAPTER / "README.md").is_file())
        self.assertTrue((ADAPTER / "GlobalMonoPipelineGameClientBuild.cs.meta").is_file())

    # 功能：打开窗口无构建/配置副作用；参数仅固定方法体文本。
    def test_open_menu_is_inert(self) -> None:
        body: str = method_body(self.source, "public static void OpenBuildWindow(")
        self.assertIn("GetWindow<MonoPipelineGameClientBuildWindow>", body)
        self.assertNotIn("Build(", body)
        self.assertNotIn("PrepareDisabledConfiguration", body)
        self.assertIn("MenuItem(MenuPath", self.source)
        self.assertIn("BuildAppWindowMonoPipeline", self.source)

    # 功能：独立原管线/平台/单次真构建调用，旧路由隔离；参数不是完整游戏验收。
    def test_original_pipeline_single_real_build_and_no_legacy_route(self) -> None:
        self.assertEqual(self.source.count("BuildPipelineX.BuildAppWithProfiler("), 1)
        self.assertEqual(self.source.count("UnityEditor.BuildPipeline.BuildPlayer"), 1)
        self.assertIn("new MonoPipelineWindowPlatform(option", self.source)
        self.assertIn("AppBuilderWindowNoSDK", self.source)
        self.assertIn("new AppBuilderResult(true,", self.source)
        self.assertNotIn("Cyou.PcFunctionTest", self.source)
        self.assertNotIn("Export_PC_TestAgent", self.source)
        self.assertNotIn("RegisterBuilder", self.source)
        self.assertIn('"PC_TEST_AGENT", "DEBUG_AUTO_TEST"', self.source)

    # 功能：明确批准/平台/新外部路径/新目录和保留失败；参数只查同包源。
    def test_approval_external_output_and_no_automatic_run(self) -> None:
        self.assertIn("if (!approved || !ValidateMenu())", self.source)
        self.assertIn("activeBuildTarget != BuildTarget.StandaloneWindows64", self.source)
        self.assertIn("output_must_be_outside_project_and_not_its_ancestor", self.source)
        self.assertIn("new_output_already_exists", self.source)
        self.assertIn("Directory.Move(staging, output)", self.source)
        self.assertNotRegex(self.source, r"Process\s*\.\s*Start|StartPlayer|AutoRunPlayer\s*\|")

    # 功能：独立恢复设置与保存原资产，未知配置改动保留；参数不承诺域重载恢复。
    def test_snapshot_restore_and_original_config_guard(self) -> None:
        for item in ("m_Backend", "m_Defines", "m_CodeGeneration", "m_Development", "m_ConnectProfiler", "m_AllowDebugging", "m_HybridEnabled"):
            self.assertIn(item, self.source)
        self.assertIn("snapshot.Restore();", self.source)
        self.assertIn("AssetDatabase.SaveAssets();", self.source)
        self.assertIn("new_configuration_changed_externally_preserved_at_", self.source)
        self.assertIn("AggregateException", self.source)

    # 功能：保留未压缩资源并按真实库存核验，补丁只四文件增量；参数只读模板。
    def test_complete_copy_and_minimal_framework_overloads(self) -> None:
        self.assertIn("CopyPackage(Option.VersionInstallTempPath, package)", self.source)
        self.assertIn("copied_package_has_extra_or_missing_files", self.source)
        self.assertIn("FileHash(file) != (string)token[\"sha256\"]", self.source)
        body: str = method_body(self.source, "public override void OnPostBuild(")
        self.assertNotIn("base.OnPostBuild", body)
        patch: str = (ADAPTER / "framework-overloads.patch").read_text(encoding="utf-8-sig")
        self.assertEqual(len(re.findall(r"(?m)^--- a/", patch)), 4)
        self.assertIn("Func<BuildOption, IAppBuilderPlatform> platformFactory", patch)
        self.assertIn("return AppBuilder.Build(option, platform);", patch)
        self.assertIn("BuildAppWindowMonoPipeline = BuildAppWindowTestAgent", patch)

    # 功能：既有启用/自动端口仅明确范围审批放宽，默认仍拒绝；参数检查公共源而不执行配置。
    def test_existing_enabled_configuration_explicit_scoped_overload(self) -> None:
        source: str = (ROOT / "assets/unity/Editor/MonoPipelineBuildSupport.cs").read_text(encoding="utf-8-sig")
        self.assertIn("InspectConfigurationSha256(int runtimePort, bool approvedExistingEnabled)", source)
        self.assertIn("externalBackupDirectory, inventoryOutput, null, false", source)
        self.assertIn("runtimePort, bool approvedExistingEnabled", source)
        self.assertIn("runtimePort.HasValue", source)
        self.assertIn("configuration[\"port\"] = runtimePort.Value", source)
        self.assertIn("ReplaceKnown(configPath, Sha256(scoped), before)", source)
        self.assertEqual(source.count("originalPipeline(prepared)"), 1)

    # 功能：仅四个已批准可选接线成员进入清单，未知适配/凭据/输出仍拒收；参数只测试布局分类。
    def test_optional_layout_is_exact_not_generic_allowance(self) -> None:
        adaptations: frozenset[str] = delivery.adaptation_files(ROOT)
        self.assertEqual(len(adaptations), 4)
        for name in adaptations:
            self.assertEqual(delivery.payload_kind(name, adaptations), "project_adaptation")
        for name in ("assets/adapters/GameClient/unknown.cs", "assets/adapters/OtherGame/adapter.cs",
                     "assets/adapters/GameClient/target.json", "assets/adapters/GameClient/output/report.md"):
            with self.assertRaises(IntegrityError):
                delivery.payload_kind(name, adaptations)
        invalid: list[list[str]] = [[], ["assets/adapters/Sample/adapter.cs"] * 2,
            ["assets/adapters/Sample/adapter.cs", "assets/adapters/sample/adapter.cs"],
            ["assets/adapters/Sample/target.json"], ["assets/adapters/output/adapter.cs"],
            ["scripts/adapter.cs"]]
        with tempfile.TemporaryDirectory(prefix="mpft-adaptation-catalog-") as temporary:
            root: Path = Path(temporary)
            catalog: Path = root / delivery.ADAPTATION_CATALOG
            catalog.parent.mkdir(parents=True)
            for files in invalid:
                catalog.write_text(json.dumps({"schema": "mono-pipeline-adaptation-catalog/1", "files": files}), encoding="utf-8")
                with self.assertRaises(IntegrityError):
                    delivery.adaptation_files(root)
