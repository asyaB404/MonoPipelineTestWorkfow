"""创建日期：2026-10-27；作者：Cyou。
功能：原共享计时器与新 Mono 宿主的真实父/子绑定、唯一报告及统计字段兼容回归。
参数：实际公共计时/转换源码与不可运行夹具；不运行生成服务、真实 Player、Unity 或上传。
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import cast

from ..contracts import InputError, IntegrityError, JsonObject, Limits, canonical
from ..evidence import REPORT_NAME, record_data
from ..delivery import export_delivery
from ..inputs import WORKFLOW_START_FIELDS, verify_workflow
from ..session import initialize, initialize_parent
from .support import Fixture, counter_case

SKILL_ROOT: Path = Path(__file__).resolve().parents[2]
COMMON: Path = SKILL_ROOT.parent / "functiontest-report-json/scripts"


# 功能：加载本机明确公共源码；参数 name/path 不搜索私人环境或其他工程。
def common_module(name: str, path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise AssertionError("公共源码不可加载")
    module: ModuleType = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@unittest.skipUnless((COMMON / "skill_timing.py").is_file(), "shared workflow timing is an optional installed component")
class WorkflowIntegrationTests(unittest.TestCase):
    """验证实际交接，不把模拟业务或静态文件称为真实 PC 测试。"""

    # 功能：准备公共计时器；参数 self 为本例独有测试实例。
    def setUp(self) -> None:
        self.timer: ModuleType = common_module("workflow_shared_timing_test", COMMON / "skill_timing.py")

    # 功能：由公共计时器真实创建父/子编号；参数 fixture 提供临时根，parent_skill 仅用于旧父拒绝回归。
    def timing(self, fixture: Fixture, parent_skill: str = "functiontest-workflow") -> tuple[Path, str, str]:
        path: Path = fixture.root / "workflow-timing.json"
        identities: list[str] = []
        for skill in (parent_skill, "mono-pipeline-functiontest"):
            output: io.StringIO = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.timer.start_record(argparse.Namespace(file=str(path), invocation_id="", skill_name=skill,
                    operation_type="主动测试工作流", parent_invocation_id=identities[0] if identities else "", report_hidden=False))
            identities.append(str(json.loads(output.getvalue())["invocation_id"]))
        return path, identities[0], identities[1]

    # 功能：调用原计时器真实闭合记录；参数 path/identity 为本次实际返回值。
    def end(self, path: Path, identity: str) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.timer.end_record(argparse.Namespace(file=str(path), invocation_id=identity, status="completed"))

    # 功能：将现有夹具重建为统一父交接子会话；参数 cases 可用于完整覆盖缺口回归。
    def fixture(self, cases: list[JsonObject] | None = None, statistical_output: bool = False) -> tuple[Fixture, Path, str, str]:
        fixture: Fixture = Fixture(cases=cases)
        self.addCleanup(fixture.cleanup)
        path, parent, child = self.timing(fixture)
        output: Path = fixture.root / "output/workflow" if statistical_output else fixture.root / "workflow-output"
        fixture.run = initialize(fixture.cases_file, fixture.target_file, output, workflow_timing=path,
                                 workflow_parent_id=parent, workflow_child_id=child,
                                 run_prefix="workflow" if statistical_output else "run")
        return fixture, path, parent, child

    # 功能：实际父/子闭合前拒绝报告，闭合后渲染一次；参数 self 为测试实例。
    def test_actual_shared_timer_owns_single_report_after_root_close(self) -> None:
        fixture, path, parent, child = self.fixture()
        before: int = fixture.world.counter
        with fixture.session() as session:
            self.assertEqual(record_data(session.journal.records[0])["report_owner"], "coordinator")
            fixture.execute_counter(session)
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            with self.assertRaises(InputError):
                session.invoke("report", {})
        self.end(path, child)
        with fixture.session() as session, self.assertRaises(InputError):
            session.invoke("report", {})
        self.end(path, parent)
        with fixture.session() as session:
            result: JsonObject = session.invoke("report", {})
            self.assertEqual(cast(JsonObject, result["audit"])["counts"], {"blocked": 0, "failed": 0, "passed": 1, "test_inconclusive": 0})
            with self.assertRaises(IntegrityError):
                session.invoke("report", {})
        report: str = (fixture.run / REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn(parent, report)
        self.assertIn("functional passed=1 failed=0 blocked=0 test_inconclusive=0", report)
        records: list[JsonObject] = json.loads(path.read_bytes())["records"]
        self.assertEqual(len([record for record in records if not record["parent_invocation_id"]]), 1)
        self.assertEqual(fixture.world.counter - before, 1)
        self.assertNotIn(fixture.world.token, report)

    # 功能：原时间起点不能被后续 sidecar 修改覆盖；参数 self 为测试实例。
    def test_changed_parent_start_snapshot_rejects_before_any_player_call(self) -> None:
        fixture, path, parent, child = self.fixture()
        before: int = fixture.world.counter
        document: JsonObject = json.loads(path.read_bytes())
        cast(list[JsonObject], document["records"])[0]["operation_type"] = "changed after binding"
        path.write_bytes(canonical(document))
        with fixture.session() as session, self.assertRaises(IntegrityError):
            session.invoke("status", {})
        self.assertEqual(fixture.world.counter, before)

    # 功能：父先于子收口不允许冒充完整父跨度；参数 self 为测试实例。
    def test_root_closed_before_child_rejects(self) -> None:
        fixture, path, parent, child = self.fixture()
        self.end(path, parent)
        with fixture.session() as session, self.assertRaises(IntegrityError):
            session.invoke("status", {})

    # 功能：子已结束时禁止继续未收口宿主；参数 self 为测试实例。
    def test_child_closed_while_host_open_rejects(self) -> None:
        fixture, path, parent, child = self.fixture()
        self.end(path, child)
        with fixture.session() as session, self.assertRaises(IntegrityError):
            session.invoke("status", {})

    # 功能：包内第二父与不完整共享参数均拒绝；参数 self 为测试实例。
    def test_second_parent_or_partial_shared_parameters_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        path, parent, child = self.timing(fixture)
        second: Path = initialize_parent(fixture.root / "second-parent")
        with self.assertRaises(InputError):
            initialize(fixture.cases_file, fixture.target_file, fixture.root / "bad-mixed", parent_root=second,
                       workflow_timing=path, workflow_parent_id=parent, workflow_child_id=child)
        with self.assertRaises(InputError):
            initialize(fixture.cases_file, fixture.target_file, fixture.root / "bad-partial", workflow_timing=path)

    # 功能：错误父/子归属不允许新建业务运行；参数 self 为测试实例。
    def test_wrong_child_parent_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        path, parent, child = self.timing(fixture)
        document: JsonObject = json.loads(path.read_bytes())
        cast(list[JsonObject], document["records"])[1]["parent_invocation_id"] = "other-root"
        path.write_bytes(canonical(document))
        with self.assertRaises(InputError):
            initialize(fixture.cases_file, fixture.target_file, fixture.root / "bad-parent", workflow_timing=path,
                       workflow_parent_id=parent, workflow_child_id=child)

    # 功能：旧 PC 技能名的实际计时记录不能初始化新宿主；参数 self 为测试实例，未加载旧技能。
    def test_deprecated_pc_parent_rejected_before_run_creation(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        path, parent, child = self.timing(fixture, "pc-batch-test")
        output: Path = fixture.root / "deprecated-parent-output"
        before: int = fixture.world.counter
        with self.assertRaises(InputError):
            initialize(fixture.cases_file, fixture.target_file, output, workflow_timing=path,
                       workflow_parent_id=parent, workflow_child_id=child)
        self.assertFalse(output.exists())
        self.assertEqual(fixture.world.counter, before)

    # 功能：曾绑定旧 PC 父的历史格式也不能重载继续；参数 self 为测试实例，只验证公共计时与快照。
    def test_existing_deprecated_parent_binding_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        path, parent, child = self.timing(fixture, "pc-batch-test")
        document: JsonObject = json.loads(path.read_bytes())
        records: list[JsonObject] = cast(list[JsonObject], document["records"])
        binding: JsonObject = {"schema": "mono-pipeline-workflow-binding/1", "timing_file": str(path),
            "parent_start": {name: records[0][name] for name in WORKFLOW_START_FIELDS},
            "child_start": {name: records[1][name] for name in WORKFLOW_START_FIELDS}}
        with self.assertRaises(IntegrityError):
            verify_workflow(binding, Limits(), records[1]["skill_start_time"])

    # 功能：独立移动宿主经真实 CLI 绑定原父/子，无运行身份探测；参数 self 为测试实例。
    def test_cold_relocated_cli_init_inherits_shared_timing(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        before: int = fixture.world.counter
        path, parent, child = self.timing(fixture)
        relocated: Path = fixture.root / "mono-pipeline-functiontest"
        export_delivery(SKILL_ROOT, relocated)
        result: subprocess.CompletedProcess[str] = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(relocated / "scripts/cli.py"), "init",
            "--cases", str(fixture.cases_file), "--target", str(fixture.target_file), "--output", str(fixture.root / "cold-output"),
            "--workflow-timing", str(path), "--workflow-parent-id", parent, "--workflow-child-id", child],
            cwd=fixture.root, capture_output=True, encoding="utf-8", timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        document: JsonObject = json.loads(result.stdout)
        self.assertIs(cast(JsonObject, document["result"])["attached"], False)
        fixture.run = Path(str(cast(JsonObject, document["result"])["run"]))
        with fixture.session() as session:
            initial: JsonObject = record_data(session.journal.records[0])
            self.assertEqual(initial["report_owner"], "coordinator")
            self.assertEqual(cast(JsonObject, cast(JsonObject, initial["workflow"])["parent_start"])["invocation_id"], parent)
            self.assertFalse(session.state.attached)
        self.assertEqual(fixture.world.counter, before)

    # 功能：真实旧转换器接受新四状态/问题数并拒绝缺 final 总数；参数 self 为测试实例。
    @unittest.skipUnless((COMMON / "convert_functiontest_report.py").is_file(), "shared conversion is optional")
    def test_existing_converter_reads_real_counts_and_rejects_missing_final(self) -> None:
        previous: ModuleType | None = sys.modules.get("skill_timing")
        sys.modules["skill_timing"] = self.timer
        try:
            converter: ModuleType = common_module("workflow_report_converter_test", COMMON / "convert_functiontest_report.py")
        finally:
            if previous is None:
                sys.modules.pop("skill_timing", None)
            else:
                sys.modules["skill_timing"] = previous
        for missing in (False, True):
            cases: list[JsonObject] | None = [counter_case(), counter_case("C-2")] if missing else None
            fixture, path, parent, child = self.fixture(cases, True)
            with fixture.session() as session:
                fixture.execute_counter(session)
                session.invoke("final", {"status": "passed"})
                session.invoke("close", {"interrupted_reason": "isolated missing final"} if missing else {})
            self.end(path, child)
            self.end(path, parent)
            with fixture.session() as session:
                session.invoke("report", {})
            text: str = (fixture.run / REPORT_NAME).read_text(encoding="utf-8")
            counts: tuple[int, ...] = converter.parse_counts(text)
            self.assertEqual(counts, (1, 0, 0, 0))
            self.assertEqual(converter.parse_issue_counts(text), (0, 0))
            if missing:
                with self.assertRaises(ValueError):
                    converter.resolve_total_case_count(text, *counts)
            else:
                self.assertEqual(converter.resolve_total_case_count(text, *counts), 1)
                arguments: argparse.Namespace = argparse.Namespace(input=str(fixture.run / REPORT_NAME), feature_name="workflow",
                    client_ip="127.0.0.1", report_time=None, timing_file=str(path), skill_name="functiontest-workflow",
                    invocation_id=parent, total_cost=0.0, operation_type=converter.DEFAULT_OPERATION_TYPE, ai_model="isolated_no_model_call")
                payload, report, run_dir, run_name = converter.build_payload(arguments)
                converter.validate_payload(payload)
                self.assertEqual(payload["user_stats_payload"]["items"][0]["custom_metrics"]["total_case_count"], 1)
                self.assertEqual(payload["user_stats_payload"]["items"][0]["custom_metrics"]["success_case_count"], 1)
                self.assertEqual(payload["tool_stats_payload"]["stats"]["duration_ms"],
                                 self.timer.select_record(self.timer.load_records(path), invocation_id=parent)["skill_active_duration_ms"])

    # 功能：2026-11-05 Codex，真实复用现有转换CLI且不改报告/旧JSON；参数 self 仅使用隔离计数夹具。
    @unittest.skipUnless((COMMON / "convert_functiontest_report.py").is_file(), "shared conversion is optional")
    def test_existing_converter_cli_accepts_the_unique_mono_report_and_refuses_overwrite(self) -> None:
        fixture, timing, parent, child = self.fixture(statistical_output=True)
        with fixture.session() as session:
            fixture.execute_counter(session)
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
        self.end(timing, child)
        self.end(timing, parent)
        with fixture.session() as session:
            session.invoke("report", {})
        report: Path = fixture.run / REPORT_NAME
        original: bytes = report.read_bytes()
        output: Path = fixture.run / (fixture.run.name + "-functiontest-upload.json")
        command: list[str] = [sys.executable, "-B", "-X", "utf8", str(COMMON / "convert_functiontest_report.py"),
            "--input", str(report), "--output", str(output), "--timing-file", str(timing),
            "--skill-name", "functiontest-workflow", "--invocation-id", parent,
            "--feature-name", "workflow", "--client-ip", "127.0.0.1", "--ai-model", "isolated_no_model_call"]
        result: subprocess.CompletedProcess[str] = subprocess.run(command, cwd=fixture.root, capture_output=True,
            encoding="utf-8", timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload: JsonObject = json.loads(output.read_bytes())
        metrics: JsonObject = payload["user_stats_payload"]["items"][0]["custom_metrics"]
        self.assertEqual(metrics["total_case_count"], 1)
        self.assertEqual(metrics["success_case_count"], 1)
        self.assertEqual(report.read_bytes(), original)
        self.assertEqual([path.name for path in fixture.run.glob("*.md")], [REPORT_NAME])
        first_json: bytes = output.read_bytes()
        repeated: subprocess.CompletedProcess[str] = subprocess.run(command, cwd=fixture.root, capture_output=True,
            encoding="utf-8", timeout=30, check=False)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertIn("refusing to overwrite", repeated.stdout + repeated.stderr)
        self.assertEqual(output.read_bytes(), first_json)
        self.assertEqual(report.read_bytes(), original)
