"""创建日期：2026-10-28；作者：Cyou。
功能：复现另一个模型 10-27 日志中的输出路径、guard 原文和来源修改后的收尾卡点。
参数：当前生产宿主及隔离身份/内存传输夹具；不连接真实 Player，不修改历史运行或游戏包。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
import uuid
from pathlib import Path
from typing import cast

from ..contracts import InputError, IntegrityError, JsonObject, JsonValue, canonical
from ..evidence import REPORT_NAME, record_data
from ..cli import main
from ..report import render_parent
from ..session import close_parent, initialize, initialize_parent
from .support import Fixture, counter_case


class OrchestrationFailureTests(unittest.TestCase):
    """要求初始化先拒绝超限，合法更正不重放，来源失效仅能本地中断而不能恢复业务。"""

    # 功能：创建本例独立夹具；参数 cases 保持原始业务字段，不预生成动作映射。
    def fixture(self, cases: list[JsonObject] | None = None) -> Fixture:
        fixture: Fixture = Fixture(cases=cases)
        self.addCleanup(fixture.cleanup)
        return fixture

    # 功能：复现日志 148 字符运行根，最长证据会超出 Windows 普通路径；参数 self 为测试实例。
    @unittest.skipUnless(os.name == "nt", "Windows MAX_PATH initialization guard")
    def test_long_output_rejected_before_any_run_creation(self) -> None:
        fixture: Fixture = self.fixture()
        run_id_units: int = len("run-" + uuid.uuid4().hex)
        padding: int = max(1, 148 - len(str(fixture.root)) - run_id_units - 2)
        output: Path = fixture.root / ("p" * padding)
        before: int = fixture.world.eval_count
        with self.assertRaisesRegex(InputError, "证据路径"):
            initialize(fixture.cases_file, fixture.target_file, output)
        self.assertFalse(output.exists())
        self.assertEqual(fixture.world.eval_count, before)

    # 功能：真实 CLI 在初始化前给出可消费的路径预算及拒绝退出码；参数 self 为测试实例，不连接目标。
    @unittest.skipUnless(os.name == "nt", "Windows output-check CLI")
    def test_output_check_cli_rejects_long_root_without_files(self) -> None:
        fixture: Fixture = self.fixture()
        output: Path = fixture.root / ("p" * 100)
        capture: io.StringIO = io.StringIO()
        with contextlib.redirect_stdout(capture):
            code: int = main(["output-check", "--output", str(output), "--run-prefix", "run"])
        result: JsonObject = cast(JsonObject, json.loads(capture.getvalue()))
        self.assertEqual(code, 3)
        self.assertFalse(cast(JsonObject, result["result"])["supported"])
        self.assertFalse(output.exists())
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：原前置与原步骤守卫返回各自真实索引，不让 Agent 猜原文；参数 self 为测试实例。
    def test_start_exposes_distinct_precondition_and_guard_sources(self) -> None:
        case: JsonObject = counter_case()
        case["preconditions"] = [{"index": 7, "text": "库存满足独立配置成本"}]
        case["steps"] = [{"index": 3, "text": "触发一次计数增加"}]
        fixture: Fixture = self.fixture([case])
        with fixture.session() as session:
            result: JsonObject = session.invoke("start-case", {"case_id": "C-1"})
            self.assertIn("binding_sources", result)
            sources: JsonObject = cast(JsonObject, result["binding_sources"])
            self.assertEqual(cast(list[JsonObject], sources["precondition"])[0]["index"], 7)
            self.assertEqual(cast(list[JsonObject], sources["guard"])[0]["index"], 3)
            self.assertEqual(cast(list[JsonObject], sources["guard"])[0]["original_text"], "触发一次计数增加")
            self.assertEqual(session.invoke("status", {})["binding_sources"], sources)
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：被拒请求保留原字节，使用新文件和比较 ID 可继续；参数 self 为测试实例。
    def test_rejected_binding_corrected_in_new_file_without_freeze(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            bad: JsonObject = fixture.comparison("bad-guard", "before", "/unique_count", 1, "guard")
            bad["original_text"] = "已登录并进入入口"
            original_bytes: bytes = canonical(bad)
            old: Path = fixture.write_json("rejected-guard.json", bad)
            with self.assertRaises(InputError):
                session.invoke("compare", bad, old)
            good: JsonObject = fixture.comparison("good-guard", "before", "/unique_count", 1, "guard")
            new: Path = fixture.write_json("corrected-guard.json", good)
            self.assertTrue(session.invoke("compare", good, new)["matched"])
            self.assertFalse(session.state.frozen)
            self.assertEqual(old.read_bytes(), original_bytes)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：一次绑定错误用新文件修正后完成真实宿主单次动作/新帧比较/唯一报告；参数 self 为测试实例。
    def test_corrected_request_completes_normal_single_action_report(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.baseline(session)
            fixture.observe(session)
            bad: JsonObject = fixture.comparison("wrong-binding", "before", "/unique_count", 1, "guard")
            bad["original_text"] = "误用了前置原文"
            path: Path = fixture.write_json("wrong-binding.json", bad)
            with self.assertRaises(InputError):
                session.invoke("compare", bad, path)
            good: JsonObject = fixture.comparison("corrected-binding", "before", "/unique_count", 1, "guard")
            corrected: Path = fixture.write_json("new-binding.json", good)
            session.invoke("compare", good, corrected)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.action(session, guards)
            fixture.observe(session, "read-after", "after", "action-one")
            fixture.assert_changes(session)
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            report: JsonObject = session.invoke("report", {})
            self.assertEqual(cast(JsonObject, cast(JsonObject, report["audit"])["counts"])["passed"], 1)
        self.assertEqual(fixture.world.action_count, 1)

    # 功能：来源原地改写仍冻结，但本地状态与明确中断关闭不再死锁；参数 self 为测试实例。
    def test_modified_registered_request_can_close_locally_without_report(self) -> None:
        fixture: Fixture = self.fixture()
        original_bytes: bytes
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            bad: JsonObject = fixture.comparison("bad-guard", "before", "/unique_count", 1, "guard")
            request: Path = fixture.write_json("registered-guard.json", bad)
            original_bytes = request.read_bytes()
            self.assertTrue(session.invoke("compare", bad, request)["matched"])
            bad["original_text"] = "改写已成功登记的原文仍必须冻结"
            request.write_bytes(canonical(bad))
            transports: int = fixture.world.transport_count
            status: JsonObject = session.invoke("status", {})
            self.assertTrue(status["frozen"])
            self.assertFalse(status["source_integrity_valid"])
            with self.assertRaises(IntegrityError):
                fixture.observe(session, "forbidden-read", "forbidden")
            with self.assertRaises(InputError):
                session.invoke("close", {})
            closed: JsonObject = session.invoke("close", {"interrupted_reason": "编排改写已登记来源，本地中断，不接触 Player"})
            self.assertTrue(closed["closed"])
            self.assertFalse(closed["formal_report_eligible"])
            self.assertEqual(closed["missing_case_ids"], ["C-1"])
            self.assertEqual(fixture.world.transport_count, transports)
            summary: Path = fixture.run / str(closed["interruption_summary"])
            self.assertIn("不是正式测试报告", summary.read_text(encoding="utf-8"))
            registered: JsonObject = next(record_data(record) for record in session.journal.records if record["event"] == "request_registered")
            snapshot: JsonObject = cast(JsonObject, cast(JsonObject, registered["request_origin"])["snapshot"])
            self.assertEqual(session.journal.verify_ref(snapshot), original_bytes)
            with self.assertRaises(IntegrityError):
                session.invoke("report", {})
            self.assertFalse((fixture.run / REPORT_NAME).exists())
            request.write_bytes(original_bytes)
        with fixture.session() as resumed:
            self.assertTrue(resumed.invoke("status", {})["closed"])
            with self.assertRaises(IntegrityError):
                resumed.invoke("report", {})
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：输入原文件删除也只允许中断收口，不假补结果；参数 self 为测试实例。
    def test_missing_external_source_can_close_without_synthetic_finals(self) -> None:
        fixture: Fixture = self.fixture()
        fixture.cases_file.unlink()
        with fixture.session() as session:
            closed: JsonObject = session.invoke("close", {"interrupted_reason": "原始用例外部来源缺失，禁止继续"})
            self.assertFalse(closed["complete"])
            self.assertFalse(closed["formal_report_eligible"])
            self.assertFalse(any(record["event"] == "case_final" for record in session.journal.records))
            self.assertIsNotNone(session.state.timing)
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：包内独立父也能关闭无效子计时，但父报告保持拒绝；参数 self 为测试实例。
    def test_parent_closes_interrupted_child_without_formal_report(self) -> None:
        fixture: Fixture = self.fixture()
        parent: Path = initialize_parent(fixture.root / "parent-output")
        fixture.run = initialize(fixture.cases_file, fixture.target_file, fixture.root / "child-output", parent_root=parent)
        fixture.cases_file.unlink()
        with fixture.session() as session:
            session.invoke("close", {"interrupted_reason": "外部原来源缺失，完整报告无效"})
        closed: JsonObject = close_parent(parent)
        self.assertTrue(closed["closed"])
        self.assertFalse(closed["formal_report_eligible"])
        with self.assertRaises(IntegrityError):
            render_parent(parent)
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：私有快照坏字节不得借本地关闭旁路；参数 self 为测试实例。
    def test_corrupt_private_snapshot_still_rejects_local_close(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            initial: JsonObject = record_data(session.journal.records[0])
            origin: JsonObject = cast(JsonObject, initial["case_input"])
            snapshot: JsonObject = cast(JsonObject, origin["snapshot"])
            (fixture.run / str(snapshot["path"])).write_bytes(b"corrupted private snapshot")
            with self.assertRaises(IntegrityError):
                session.invoke("close", {"interrupted_reason": "不能信任私有证据"})
            self.assertIsNone(session.state.closed)
        self.assertEqual(fixture.world.eval_count, 0)
