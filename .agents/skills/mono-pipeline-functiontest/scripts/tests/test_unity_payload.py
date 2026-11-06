"""创建日期：2026-10-26；作者：Cyou。
功能：公共 C# API/启动守卫/平台依赖、精确反射、日志/截图元数据和原构建范围的静态检查。
参数：同包源与原 ZIP、内存预处理符号；仅静态分析，不执行 C# 编译、Unity 或 Player，不能替代运行验收。
"""
from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

from ..delivery import dependency_catalog
from ..pipeline import BRIDGE_KEYS

ROOT: Path = Path(__file__).resolve().parents[2]
UNITY: Path = ROOT / "assets/unity"


# 功能：解析纯预处理布尔表达式，不执行脚本；参数 symbols 为静态假编译符号。
def expression_value(expression: str, symbols: set[str]) -> bool:
    source: str = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", lambda match: "True" if match.group(0) in symbols else "False", expression)
    source = source.replace("&&", " and ").replace("||", " or ").replace("!", " not ").strip()
    tree: ast.Expression = ast.parse(source, mode="eval")
    # 功能：只接受 bool 常量/与或非；参数 node 不运行 Python/C# 任意代码。
    def visit(node: ast.AST) -> bool:
        if isinstance(node, ast.Expression): return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) is bool: return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return not visit(node.operand)
        if isinstance(node, ast.BoolOp):
            values: list[bool] = [visit(value) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        raise AssertionError("unsupported preprocessor expression")
    return visit(tree)


# 功能：纯文本预处理覆盖平台/开发/宏组合；参数源只含标准 if/else/endif，绝不编译/运行 Unity。
def preprocess(source: str, symbols: set[str]) -> str:
    active: bool = True
    stack: list[tuple[bool, bool]] = []
    result: list[str] = []
    for line in source.splitlines():
        stripped: str = line.strip()
        if stripped.startswith("#if "):
            condition: bool = expression_value(stripped[4:], symbols)
            stack.append((active, condition))
            active = active and condition
        elif stripped == "#else":
            parent, selected = stack[-1]
            active = parent and not selected
        elif stripped == "#endif":
            parent, selected = stack.pop()
            active = parent
        elif active:
            result.append(line)
    if stack: raise AssertionError("unbalanced directives")
    return "\n".join(result)


# 功能：从已命中方法声明抽取完整花括号体；参数仅做有界源文本检查，不执行 C#。
def method_body(source: str, declaration: str) -> str:
    start: int = source.index(declaration)
    opening: int = source.index("{", start)
    depth: int = 0
    for index in range(opening, len(source)):
        if source[index] == "{": depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0: return source[opening:index + 1]
    raise AssertionError("method body missing")


class UnityPayloadStaticTests(unittest.TestCase):
    # 功能：读取同包文本；参数 name 为固定已知源，不扫描维护 Assets。
    def source(self, name: str) -> str:
        return (UNITY / name).read_text(encoding="utf-8-sig")

    # 功能：公共新增源不超过四个，日期/作者/功能参数与明确类型齐全；参数只扫描包内新源。
    def test_four_sources_headers_explicit_types_and_no_business_hardcoding(self) -> None:
        paths: list[Path] = sorted(UNITY.rglob("*.cs"))
        self.assertEqual(len(paths), 4)
        for path in paths:
            source: str = path.read_text(encoding="utf-8-sig")
            with self.subTest(file=path.name):
                self.assertIn("2026-10-26", source.splitlines()[0])
                self.assertIn("Cyou", source.splitlines()[0])
                self.assertIn("基础参数", source[:350])
                self.assertIsNone(re.search(r"\b(?:var|any|dynamic)\s+\w+", source))
                self.assertNotRegex(source, r"GameFramework|CyStarRoad|TestBoot|TestHelper|UI_Toy|UI_Hero|LoginAccount|GMCommand")
                self.assertNotRegex(source, r"Assembly\s*\.\s*(?:Load|LoadFile|LoadFrom)\s*\(|Process\s*\.\s*Start\s*\(|Thread\s*\.\s*Sleep\s*\(")
                lines: list[str] = source.splitlines()
                for index, line in enumerate(lines):
                    if re.search(r"(?:public|private|internal)\s+(?:static\s+)?(?:void|object|bool|int|string|BuildReport|BuildPlayerOptions|GameObject|Type|Component|JObject|IEnumerator|Dictionary<|List<).+\(", line):
                        self.assertTrue(any("功能：" in before and "参数" in before for before in lines[max(0, index - 4):index]), f"method header missing: {path.name}:{index + 1}")

    # 功能：桥接返回严格六字段且使用当前帧/构建/原选择器；参数不是假 runtime 验收。
    def test_bridge_envelope_exact_host_contract_and_actual_values(self) -> None:
        body: str = method_body(self.source("GlobalMonoPipelineTest.cs"), "internal static Dictionary<string, object> Envelope(")
        keys: set[str] = set(re.findall(r'\{\s*"([a-z_]+)"\s*,', body))
        self.assertEqual(keys, set(BRIDGE_KEYS))
        self.assertIn('"frame", Time.frameCount', body)
        self.assertIn('"build_guid", Application.buildGUID', body)
        self.assertIn('"target", target', body)
        self.assertIn('"error", error', body)

    # 功能：静态确认早期配置读取在 SubsystemRegistration，未授权关闭内存配置；参数不启动服务。
    def test_early_gate_subsystem_before_pipeline_before_scene_load(self) -> None:
        source: str = self.source("GlobalMonoPipelineTest.cs")
        self.assertIn("RuntimeInitializeLoadType.SubsystemRegistration", source)
        self.assertIn("Unity.Pipeline.Config.RuntimePipelineConfig.Load()", source)
        self.assertIn("config.enableInBuilds = false", source)
        self.assertIn("config.autoStart = false", source)
        self.assertLess(source.index("config.enableInBuilds = false"), source.index("if (s_Active)"))
        self.assertNotIn("pipeline_config_assembly_budget_exceeded", source)
        self.assertIn('RuntimeSwitch = "-mono-pipeline-test"', source)
        self.assertIn('Type.GetType("Mono.Runtime")', source)
        self.assertIn("Debug.isDebugBuild", source)
        _, expanded = dependency_catalog(ROOT)
        bootstrap: str = expanded["com.unity.pipeline"]["Runtime/PlayerSupport/RuntimePipelineBootstrap.cs"].decode("utf-8-sig")
        self.assertIn("RuntimeInitializeLoadType.BeforeSceneLoad", bootstrap)
        self.assertIn("config == null || !config.enableInBuilds", bootstrap)

    # 功能：编辑器/普通包/移动/IL2CPP 不开启取证/调用；参数只对文本预处理，不证明 Unity 编译。
    def test_platform_macro_development_and_editor_guards(self) -> None:
        disabled: list[set[str]] = [set(), {"UNITY_ANDROID", "DEVELOPMENT_BUILD", "MONO_PIPELINE_FUNCTIONTEST"},
            {"UNITY_STANDALONE_WIN", "DEVELOPMENT_BUILD"}, {"UNITY_STANDALONE_WIN", "MONO_PIPELINE_FUNCTIONTEST"},
            {"UNITY_STANDALONE_WIN", "DEVELOPMENT_BUILD", "MONO_PIPELINE_FUNCTIONTEST", "ENABLE_IL2CPP"},
            {"UNITY_EDITOR", "UNITY_STANDALONE_WIN", "DEVELOPMENT_BUILD", "MONO_PIPELINE_FUNCTIONTEST"}]
        for symbols in disabled:
            with self.subTest(symbols=symbols):
                combined: str = "\n".join(preprocess(path.read_text(encoding="utf-8-sig"), symbols) for path in sorted(UNITY.rglob("*.cs")) if "Editor" not in path.parts)
                self.assertNotIn("public static Dictionary<string, object> InvokeComponent(", combined)
                self.assertNotIn("CaptureScreenshotAsTexture()", combined)
                self.assertNotIn("logMessageReceivedThreaded +=", combined)
                self.assertNotRegex(combined, r"using\s+Unity\.Pipeline")
                if "UNITY_STANDALONE_WIN" not in symbols or "UNITY_EDITOR" in symbols:
                    self.assertNotIn("Unity.Pipeline.Config.RuntimePipelineConfig.Load()", combined)
        active: set[str] = {"UNITY_STANDALONE_WIN", "DEVELOPMENT_BUILD", "MONO_PIPELINE_FUNCTIONTEST"}
        enabled: str = preprocess(self.source("GlobalMonoPipelineTest.cs"), active)
        self.assertIn("public static Dictionary<string, object> InvokeComponent(", enabled)
        self.assertIn("switched && !Application.isEditor", enabled)
        mobile_editor: str = preprocess(self.source("Editor/MonoPipelineBuildSupport.cs"), {"UNITY_ANDROID"})
        self.assertNotIn("using Unity.Pipeline", mobile_editor)

    # 功能：节点来自真实加载场景，显式 inactive/预算/稳定候选/实例重新定位；参数没有资源扫描兜底。
    def test_loaded_scene_nodes_inactive_budget_uniqueness_and_relocation(self) -> None:
        source: str = self.source("MonoPipelineReflection.cs")
        self.assertIn("SceneManager.GetSceneAt(index)", source)
        self.assertIn("scene.GetRootGameObjects()", source)
        self.assertIn("node.scene.IsValid()", source)
        self.assertIn("node.scene.isLoaded", source)
        self.assertIn("includeInactive", source)
        self.assertIn("MaximumNodes = 32768", source)
        self.assertIn("selector_ambiguous", source)
        self.assertIn("target_missing", source)
        self.assertIn("target_rebuilt_relocate_required", source)
        self.assertIn("found.GetInstanceID() != instanceId", source)
        self.assertIn("Uri.EscapeDataString", source)
        self.assertNotIn("Resources.FindObjectsOfTypeAll", source)

    # 功能：反射只解析当前集合/MVID/唯一类型和精确签名，再一次调用；参数不注册编译器引用。
    def test_loaded_type_mvid_exact_method_and_single_invocation(self) -> None:
        source: str = self.source("MonoPipelineReflection.cs")
        self.assertIn("AppDomain.CurrentDomain.GetAssemblies()", source)
        self.assertIn("loaded_type_ambiguous", source)
        self.assertIn("ModuleVersionId", source)
        self.assertIn("found.Assembly.FullName != assemblyFullName", source)
        body: str = method_body(source, "internal static object Invoke(")
        self.assertIn("BindingFlags.DeclaredOnly", body)
        self.assertIn("ParameterType.FullName != parameterTypes[index]", body)
        self.assertIn("IsInstanceOfType(arguments[index])", body)
        self.assertEqual(body.count("selected.Invoke(owner, arguments)"), 1)
        self.assertIn("!behaviour.isActiveAndEnabled", body)
        self.assertIn("!selectable.IsInteractable()", body)
        self.assertIn('"roslyn_metadata_registration_performed", false', source)

    # 功能：getter/歧义/复杂值错误不能默默变 false/0；参数静态检查读取和 JSON 投影边界。
    def test_member_getter_missing_ambiguity_and_json_errors_preserved(self) -> None:
        source: str = self.source("MonoPipelineReflection.cs")
        body: str = method_body(source, "private static object ReadMember(")
        self.assertIn("member_owner_missing", body)
        self.assertIn("member_ambiguous", body)
        self.assertIn("member_missing_or_not_readable", body)
        self.assertIn("property.GetValue(source, null)", body)
        self.assertNotIn("catch", body)
        self.assertNotRegex(body, r"return\s+(?:false|0)\s*;")
        self.assertIn("actual_value_type_requires_explicit_member_projection", source)
        self.assertIn("non_finite_actual_value", source)

    # 功能：标准控件只触发一次并检查可操作；参数定制按钮不能被通用接口重复派发。
    def test_controls_once_current_operability_no_duplicate_dispatch(self) -> None:
        source: str = self.source("MonoPipelineReflection.cs")
        button: str = method_body(source, "internal static object ClickButton(")
        toggle: str = method_body(source, "internal static object SetToggle(")
        self.assertEqual(button.count("button.onClick.Invoke()"), 1)
        self.assertIn("!button.IsInteractable()", button)
        self.assertIn("!node.activeInHierarchy", button)
        self.assertEqual(toggle.count("toggle.isOn = value"), 1)
        self.assertIn("toggle.isOn == value ? 0 : 1", toggle)
        self.assertNotIn("GameButton", source)
        self.assertIn("component.GetType() != type", source)

    # 功能：结构化日志有界/显式开关并披露丢失/截断/后台帧；参数不声称无异常。
    def test_logs_structured_bounded_and_incomplete_explicit(self) -> None:
        source: str = self.source("MonoPipelineEvidence.cs")
        self.assertIn("MaximumLogRecords = 512", source)
        self.assertIn("MaximumMessageCharacters = 4096", source)
        self.assertIn("MaximumStackCharacters = 8192", source)
        self.assertIn("logMessageReceivedThreaded", source)
        self.assertIn('"seq", ++s_Sequence', source)
        for field in ("severity", "message", "stack", "utc", "frame", "frame_exact", "truncated", "dropped_total", "disabled_intervals", "complete"):
            self.assertIn('"' + field + '"', source)
        self.assertIn("last_main_thread_sample", source)
        self.assertIn("!droppedWindow && !windowTruncated", source)
        self.assertNotIn("no_exceptions", source)

    # 功能：单次截图/新帧完成/真实摘要/帧区分与十字段附件；参数不运行渲染或自动审阅。
    def test_screenshot_ticket_new_frame_sha_and_exact_evidence_metadata(self) -> None:
        source: str = self.source("MonoPipelineEvidence.cs")
        artifact: str = method_body(source, "private static Dictionary<string, object> Artifact(")
        keys: set[str] = set(re.findall(r'\{\s*"([a-z_][a-z0-9_]*)"\s*,', artifact))
        self.assertEqual(keys, {"path", "sha256", "bytes", "kind", "run_id", "case_id", "command_id", "build_guid", "frame", "privacy"})
        self.assertIn("VerifyFile(path, hash, bytes)", artifact)
        self.assertIn('"frame", Time.frameCount', artifact)
        self.assertIn('context.public_reviewed ? "public_reviewed" : "unreviewed"', artifact)
        self.assertIn("MaximumTickets = 8", source)
        self.assertIn("FileMode.CreateNew", source)
        self.assertIn("FileAttributes.ReparsePoint", source)
        self.assertIn("Time.frameCount <= ticket.RequestFrame", source)
        self.assertIn('"render_frame", null', source)
        self.assertIn('"render_frame_known", false', source)
        self.assertIn('"capture_request_frame"', source)
        self.assertIn('"completion_check_frame"', source)
        capture: str = method_body(source, "private static IEnumerator Capture(")
        self.assertEqual(capture.count("CaptureScreenshotAsTexture()"), 1)
        self.assertIn("ticket.Error = exception.GetType().FullName", capture)
        self.assertIn("ticket.Build != context.build_guid", source)
        self.assertNotRegex(source, r"public_reviewed\s*=\s*true")

    # 功能：依赖 asmdef 保留实际平台和解释器/Roslyn/InputSystem；参数读取原 ZIP，不修改/编译。
    def test_original_dependency_platform_and_reference_closure_not_trimmed(self) -> None:
        _, expanded = dependency_catalog(ROOT)
        pipeline: dict[str, bytes] = expanded["com.unity.pipeline"]
        runtime: dict[str, object] = json.loads(pipeline["Runtime/Unity.Pipeline.asmdef"])
        interpreter: dict[str, object] = json.loads(pipeline["Runtime/IlInterpreter/Unity.Pipeline.IlInterpreter.asmdef"])
        self.assertEqual(runtime["includePlatforms"], ["Editor", "WindowsStandalone64"])
        self.assertEqual(interpreter["includePlatforms"], ["Editor", "WindowsStandalone64"])
        self.assertIn("Unity.InputSystem", runtime["references"])
        self.assertIn("Unity.Pipeline.IlInterpreter", runtime["references"])
        for name in ("Microsoft.CodeAnalysis.dll", "Microsoft.CodeAnalysis.CSharp.dll", "System.Reflection.Metadata.dll", "Newtonsoft.Json.dll"):
            self.assertIn(name, runtime["precompiledReferences"])
            self.assertTrue(any(member.endswith("/" + name) for payload in expanded.values() for member in payload))

    # 功能：编辑器辅助显式批准/备份/配置恢复/原管线与真实 BuildReport 库存；参数不构建固定场景。
    def test_editor_original_pipeline_configuration_scope_and_candidate_inventory(self) -> None:
        source: str = self.source("Editor/MonoPipelineBuildSupport.cs")
        self.assertIn("EditorUtility.DisplayDialog", source)
        self.assertIn("if (!approved", source)
        self.assertIn("PlayerSettings.GetScriptingBackend", source)
        self.assertIn("original.extraScriptingDefines = defines", source)
        self.assertIn("original.options |= BuildOptions.Development", source)
        self.assertIn("EditorUserBuildSettings.development = previousDevelopment", source)
        self.assertIn("ReplaceKnown(configPath, Sha256(scoped), before)", source)
        self.assertEqual(source.count("originalPipeline(prepared)"), 1)
        self.assertNotIn("BuildPipeline.BuildPlayer", source)
        self.assertNotIn("PlayerSettings.SetScriptingBackend", source)
        self.assertIn("summary.result != BuildResult.Succeeded", source)
        self.assertIn("summary.guid.ToString()", source)
        self.assertIn("report.GetFiles()", source)
        self.assertIn('"complete_game_delivery", false', source)
        self.assertIn("build_inventory_must_be_outside_static_package", source)

    # 功能：薄 bat 没有固定维护机路径/版本或安装启动行为；参数静态检查同包入口定位。
    def test_windows_entry_thin_local_explicit_python_without_installer(self) -> None:
        source: str = (ROOT / "mono-pipeline-test.bat").read_text(encoding="utf-8-sig")
        self.assertIn('%~dp0scripts\\cli.py', source)
        self.assertIn("MONO_PIPELINE_PYTHON", source)
        self.assertIn("py -3 -I -B", source)
        self.assertNotIn("py -3.13", source)
        self.assertNotRegex(source, r"(?i)pip\s+install|start\s+.*\.exe|https?://|[A-Z]:\\Users\\")
