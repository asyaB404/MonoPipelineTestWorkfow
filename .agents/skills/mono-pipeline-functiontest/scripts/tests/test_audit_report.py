"""创建日期：2026-10-26；作者：Cyou。
功能：证据/日志/来源/绑定篡改拒绝、真实覆盖/计时、父子唯一报告与敏感排除测试。
参数：临时文件、有限状态内存后端；不连接 Player，不生成实际游戏验收结论。
"""
from __future__ import annotations

import struct
import time
import unittest
import zlib
from pathlib import Path
from typing import cast

from ..contracts import FrozenSession, InputError, IntegrityError, JsonObject, JsonValue, canonical, digest
from ..evidence import JOURNAL_NAME, REPORT_NAME, Journal, record_data
from ..report import audit_parent, audit_run, render_parent
from ..session import Session, close_parent, initialize, initialize_parent
from .support import Fixture, counter_case, readonly_case


# 功能：构造真实可解析的 1 像素 PNG，不是假装游戏截图；参数无。
def tiny_png() -> bytes:
    # 功能：构造有 CRC 的 PNG chunk；参数 name/data 为类型和完整字节。
    def chunk(name: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff")) + chunk(b"IEND", b"")


# 功能：完成本例并真实关闭 writer 时间；参数 fixture 可提供失败成本配置。
def closed_counter(fixture: Fixture, status: str = "passed") -> None:
    with fixture.session() as session:
        fixture.execute_counter(session)
        session.invoke("final", {"status": status})
        session.invoke("close", {})


class AuditReportTests(unittest.TestCase):
    # 功能：摘要链真实合法仍拒绝手填计时，不只依赖字节改写检测；参数 self 为测试实例。
    def test_hand_filled_duration_rejected_with_valid_hash_chain(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            fixture.execute_counter(session)
            session.invoke("final", {"status": "passed"})
            audit: JsonObject = session.journal.append("audit_complete", {"audit": {}, "head_before": session.journal.records[-1]["hash"]})
            session.journal.append("session_closed", {"complete": True, "missing_case_ids": [], "unfinished_case": None,
                                                       "interrupted_reason": None, "frozen": False, "audit_seq": audit["seq"],
                                                       "audit_hash": audit["hash"], "process_cleanup": "not_executed"})
            session.journal.append("timing_closed", {"scope": "self", "start_seq": 1,
                                                      "start_hash": session.journal.records[0]["hash"], "duration_ns": 0})
            session.journal.refresh()
            with self.assertRaises(IntegrityError):
                session.invoke("report", {})
        self.assertFalse((fixture.run / REPORT_NAME).exists())

    # 功能：没有收口/计时不能渲染正式报告；参数 self 为测试实例。
    def test_report_requires_real_close_and_timing(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            fixture.execute_counter(session)
            session.invoke("final", {"status": "passed"})
            with self.assertRaises(IntegrityError):
                session.invoke("report", {})
        self.assertFalse((fixture.run / REPORT_NAME).exists())

    # 功能：缺原全集 final 必须明确中断，不补造结果；参数 self 为测试实例。
    def test_full_coverage_close_rejects_or_explicit_interrupt(self) -> None:
        fixture: Fixture = Fixture(cases=[counter_case(), counter_case("C-2")])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            fixture.execute_counter(session)
            session.invoke("final", {"status": "passed"})
            with self.assertRaises(InputError):
                session.invoke("close", {})
            close: JsonObject = session.invoke("close", {"interrupted_reason": "仅在隔离测试中主动保留第二条缺口"})
            self.assertFalse(close["complete"])
            result: JsonObject = session.invoke("report", {})
            self.assertEqual(result["audit"]["missing_case_ids"], ["C-2"])
            self.assertEqual(result["audit"]["final_count"], 1)
            self.assertEqual(result["audit"]["counts"]["passed"], 1)

    # 功能：正式报告唯一且无缺失日志假称无异常；参数 self 为测试实例。
    def test_unique_report_and_unknown_log_status(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        closed_counter(fixture)
        with fixture.session() as session:
            result: JsonObject = session.invoke("report", {})
            self.assertEqual(result["audit"]["log_status"], "not_collected_unknown")
            with self.assertRaises(IntegrityError):
                session.invoke("report", {})
        report: str = (fixture.run / REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn("上报：未执行", report)
        self.assertIn("not_collected_unknown", report)
        self.assertIn("计数严格增加 1", report)
        self.assertNotIn("本轮无异常", report)
        self.assertNotIn(fixture.world.token, report)

    # 功能：计时准确来自 writer，不以手填分项累加；参数 self 为测试实例。
    def test_report_time_is_writer_span(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        closed_counter(fixture)
        with fixture.session() as session:
            audit: JsonObject = audit_run(session)
            if session.state.timing is None:
                self.fail("缺少真实闭合计时")
            expected: int = cast(int, session.state.timing["monotonic_ns"]) - cast(int, session.journal.records[0]["monotonic_ns"])
            self.assertEqual(audit["timing"]["duration_ns"], expected)
            self.assertEqual(audit["timing"]["source"], "writer_perf_counter_ns")
            self.assertGreater(expected, 0)

    # 功能：私有证据改写拒绝正式报告；参数 self 为测试实例。
    def test_evidence_tamper_rejects_report(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        closed_counter(fixture)
        with fixture.session() as session:
            evidence: JsonObject = session.state.cases["C-1"].observations["after"]["evidence"]
        path: Path = fixture.run / str(evidence["path"])
        path.write_bytes(path.read_bytes() + b" ")
        with fixture.session() as session, self.assertRaises(IntegrityError):
            session.invoke("report", {})
        self.assertFalse((fixture.run / REPORT_NAME).exists())

    # 功能：journal 任意修改破坏摘要链，拒绝打开或报告；参数 self 为测试实例。
    def test_journal_rewrite_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        closed_counter(fixture)
        path: Path = fixture.run / JOURNAL_NAME
        content: bytes = path.read_bytes()
        path.write_bytes(content.replace(b'"status":"passed"', b'"status":"failed"', 1))
        with self.assertRaises(IntegrityError), fixture.session():
            self.fail("被改写日志不应打开")

    # 功能：末尾截断也由独立 head 锚点发现；参数 self 为测试实例。
    def test_journal_suffix_truncation_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        closed_counter(fixture)
        path: Path = fixture.run / JOURNAL_NAME
        lines: list[bytes] = path.read_bytes().splitlines(keepends=True)
        path.write_bytes(b"".join(lines[:-1]))
        with self.assertRaises(IntegrityError), fixture.session():
            self.fail("截断日志不应打开")

    # 功能：源字节恢复也不能解除已触发的会话冻结；参数 self 为测试实例。
    def test_source_change_freezes_and_never_auto_recovers(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        original: bytes = fixture.cases_file.read_bytes()
        fixture.cases_file.write_bytes(original + b" ")
        with fixture.session() as session:
            status: JsonObject = session.invoke("status", {})
            self.assertTrue(status["frozen"])
            self.assertFalse(status["source_integrity_valid"])
            with self.assertRaises(IntegrityError):
                session.invoke("audit", {})
            self.assertEqual(fixture.world.eval_count, 0)
        fixture.cases_file.write_bytes(original)
        with fixture.session() as session:
            self.assertTrue(session.invoke("status", {})["frozen"])
            with self.assertRaises(FrozenSession):
                session.invoke("attach", {})

    # 功能：CLI 已登记比较文件不得改写，正式报告拒绝；参数 self 为测试实例。
    def test_registered_binding_source_change_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            binding: JsonObject = fixture.comparison("bound-guard", "before", "/enabled", True, "guard")
            path: Path = fixture.write_json("registered-binding.json", binding)
            session.invoke("compare", binding, path)
            path.write_bytes(path.read_bytes() + b" ")
            status: JsonObject = session.invoke("status", {})
            self.assertTrue(status["frozen"])
            self.assertFalse(status["source_integrity_valid"])
            with self.assertRaises(IntegrityError):
                session.invoke("audit", {})
            with self.assertRaises(IntegrityError):
                session.invoke("compare", {**binding, "comparison_id": "forbidden-after-source-change"})

    # 功能：基线被改写时不继续使用新的假独立预期；参数 self 为测试实例。
    def test_baseline_change_rejected(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.baseline(session)
            fixture.write_json("configuration.json", {"cost": 0})
            status: JsonObject = session.invoke("status", {})
            self.assertTrue(status["frozen"])
            self.assertFalse(status["source_integrity_valid"])
            with self.assertRaises(IntegrityError):
                session.invoke("audit", {})
            with self.assertRaises(IntegrityError):
                session.invoke("compare", fixture.comparison("forbidden-baseline", "before", "/stock", 0))

    # 功能：观察异常后即使早先覆盖完整也不能 passed；参数 self 为测试实例。
    def test_frozen_after_coverage_cannot_pass(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=False)
            session.invoke("compare", fixture.comparison("read-expect", "before", "/counter", 3, case_id="R-1"))
            fixture.world.fail_next = "runtime"
            fixture.observe(session, "extra-discovery", "extra", scope="discovery")
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})
            session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                                     "reason": "额外执行已产生未知阶段"})
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["passed"], 0)

    # 功能：截图从本轮本例本次观测帧导入私有证据；参数 self 为测试实例。
    def test_private_artifact_identity_and_integrity(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        image: Path = fixture.root / "one-pixel.png"
        raw: bytes = tiny_png()
        image.write_bytes(raw)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.override_read = True
            fixture.world.returned_value = {"counter": 3, "screenshot": {"path": str(image), "bytes": len(raw), "sha256": digest(raw), "kind": "screenshot",
                                                                        "run_id": session.journal.run_id, "case_id": "R-1", "command_id": "artifact-read",
                                                                        "build_guid": fixture.world.build_guid, "frame": fixture.world.frame + 1, "privacy": "public_reviewed"}}
            fixture.observe(session, "artifact-read", "artifact-observation", covers=True)
            reference: JsonObject = session.invoke("collect-evidence", {"observation_id": "artifact-observation", "field": "/screenshot",
                                                                          "privacy_review": {"reviewer": "current_agent", "statement": "仅临时单像素 PNG，无账号/密码/令牌像素"}})
            self.assertEqual(session.journal.verify_ref(reference, "R-1"), raw)
            session.invoke("compare", fixture.comparison("artifact-expect", "artifact-observation", "/counter", 3, case_id="R-1"))
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["passed"], 1)
            session.invoke("report", {})
            self.assertIn(str(reference["path"]), (fixture.run / REPORT_NAME).read_text(encoding="utf-8"))

    # 功能：老例/老帧附件即使摘要正确也不能收取；参数 self 为测试实例。
    def test_artifact_foreign_case_rejected(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        raw: bytes = tiny_png()
        image: Path = fixture.root / "foreign.png"
        image.write_bytes(raw)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.override_read = True
            fixture.world.returned_value = {"screenshot": {"path": str(image), "bytes": len(raw), "sha256": digest(raw), "kind": "screenshot",
                                                            "run_id": session.journal.run_id, "case_id": "OTHER", "command_id": "foreign-read",
                                                            "build_guid": fixture.world.build_guid, "frame": fixture.world.frame + 1, "privacy": "public_reviewed"}}
            fixture.observe(session, "foreign-read", "foreign")
            with self.assertRaises(IntegrityError):
                session.invoke("collect-evidence", {"observation_id": "foreign", "field": "/screenshot",
                                                    "privacy_review": {"reviewer": "current_agent", "statement": "审查后仍必须通过程序的归属检查"}})

    # 功能：敏感内层桥接值不写脚本结果/报告/文件；参数 self 为测试实例。
    def test_nested_sensitive_bridge_value_never_persisted(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        secret: str = "fixture-private-password-value"
        fixture.world.override_read = True
        fixture.world.returned_value = {"password": secret}
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            result: JsonObject = fixture.observe(session, marker="BRIDGE_READ")
            self.assertEqual(result["samples"][0]["receipt"]["state"], "unknown")
        for path in fixture.run.rglob("*"):
            if path.is_file():
                self.assertNotIn(secret.encode("utf-8"), path.read_bytes())

    # 功能：原预期与弱字段绑定在报告中都展示，不能隐藏原含义；参数 self 为测试实例。
    def test_report_shows_weak_binding_and_unbound_expectation(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session, covers=False)
            weak: JsonObject = fixture.comparison("weak-binding", "before", "/enabled", True)
            session.invoke("compare", weak)
            session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                                     "reason": "弱绑定不证明原增量，另一个原预期没有绑定"})
            session.invoke("close", {})
            session.invoke("report", {})
        content: str = (fixture.run / REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn("计数严格增加 1", content)
        self.assertIn("/enabled", content)
        self.assertIn("库存扣减等于独立配置成本", content)
        self.assertIn("未绑定", content)
        self.assertIn("不假称机器证明", content)

    # 功能：父 writer 包围子时间且只父能渲染报告；参数 self 为测试实例。
    def test_parent_child_single_report_and_real_timing(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        parent: Path = initialize_parent(fixture.root / "parents")
        child: Path = initialize(fixture.cases_file, fixture.target_file, fixture.root / "children", parent_root=parent)
        fixture.run = child
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            session.invoke("compare", fixture.comparison("parent-expect", "before", "/counter", 3, case_id="R-1"))
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            with self.assertRaises(InputError):
                session.invoke("report", {})
        close_parent(parent)
        result: JsonObject = render_parent(parent)
        self.assertEqual(result["audit"]["counts"]["passed"], 1)
        self.assertFalse((child / REPORT_NAME).exists())
        self.assertTrue((parent / REPORT_NAME).is_file())
        with Journal(parent) as journal:
            audit, paths = audit_parent(journal)
            child_time: int = cast(int, audit["children"][0]["timing"]["duration_ns"])
            self.assertGreaterEqual(audit["timing"]["duration_ns"], child_time)
        with self.assertRaises(IntegrityError):
            render_parent(parent)

    # 功能：父摘要不把子私有日志链接误解析到父根，真实子引用仍被审计；参数 self 为测试实例。
    def test_parent_report_with_child_log_evidence(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        parent: Path = initialize_parent(fixture.root / "parents")
        fixture.run = initialize(fixture.cases_file, fixture.target_file, fixture.root / "children", parent_root=parent)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            fixture.observe(session, "read-logs", "logs", purpose="logs")
            session.invoke("compare", fixture.comparison("log-expect", "before", "/counter", 3, case_id="R-1"))
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
        close_parent(parent)
        self.assertEqual(render_parent(parent)["audit"]["counts"]["passed"], 1)

    # 功能：现有真实反例即使新观察恢复也不能覆成通过；参数 self 为测试实例。
    def test_failed_latch_survives_later_matching_observation(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        fixture.world.charge_multiplier = 2
        with fixture.session() as session:
            fixture.execute_counter(session)
            fixture.world.stock = 16
            fixture.observe(session, "late-read", "late", "action-one")
            corrected: JsonObject = fixture.comparison("late-stock", "late", "/stock", -4, index=2, operator="delta", before="before")
            self.assertTrue(session.invoke("compare", corrected)["matched"])
            self.assertEqual(session.invoke("final", {"status": "passed"})["status"], "failed")

    # 功能：短轮询总预算不会每样本重置，不重放动作；参数 self 为测试实例。
    def test_poll_total_budget_and_late_frame_only(self) -> None:
        fixture: Fixture = Fixture(limits={"script_timeout_ms": 100, "max_timeout_ms": 100, "poll_budget_ms": 200, "poll_interval_ms": 1})
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.action(session, guards)
            fixture.world.old_frame = True
            start: float = time.perf_counter()
            result: JsonObject = fixture.observe(session, "budget-read", "budget", "action-one", poll={"field": "/counter", "operator": "eq", "value": 4})
            duration: float = time.perf_counter() - start
            self.assertFalse(result["poll_matched"])
            self.assertLess(duration, 2.0)
            self.assertEqual(fixture.world.action_count, 1)
            intents: list[JsonObject] = [record_data(record) for record in session.journal.records if record["event"] == "intent" and record_data(record)["mode"] == "read" and record_data(record)["after_command_id"] == "action-one"]
            self.assertTrue(all(cast(int, intent["timeout_ms"]) <= 100 for intent in intents))

    # 功能：轮询结束后以计划声明的观察 ID 做一次确认读取，后续比较可直接引用该 ID；参数 self 为测试实例。
    def test_poll_confirm_read_keeps_declared_observation_id(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.action(session, guards)
            result: JsonObject = fixture.observe(session, "poll-after", "after", "action-one", poll={"field": "/counter", "operator": "eq", "value": 4})
            self.assertTrue(result["poll_matched"])
            self.assertEqual(result["last_observation_id"], "after")
            self.assertIn("after", session.state.cases["C-1"].observations)
            self.assertEqual(fixture.world.action_count, 1)
            self.assertTrue(session.invoke("compare", fixture.comparison("after-counter", "after", "/counter", 1, operator="delta", before="before"))["matched"])

    # 功能：剩余总预算不足以完成下一样本时提前转确认读取，不发送注定超时的样本、不冻结整轮；参数 self 为测试实例。
    def test_poll_short_remaining_budget_goes_to_confirm_read_without_freeze(self) -> None:
        fixture: Fixture = Fixture(limits={"poll_budget_ms": 1000, "poll_interval_ms": 1})
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.action(session, guards)
            fixture.world.read_delay_s = 0.6
            result: JsonObject = fixture.observe(session, "poll-after", "after", "action-one",
                                                 poll={"field": "/counter", "operator": "eq", "value": 99, "stable_samples": 8})
            self.assertFalse(session.state.frozen)
            self.assertFalse(result["poll_matched"])
            self.assertEqual(result["last_observation_id"], "after")
            self.assertEqual(fixture.world.action_count, 1)
            closed: list[JsonObject] = [record_data(record) for record in session.journal.records if record["event"] == "poll_closed"]
            self.assertTrue(closed)
            self.assertIn("剩余总预算不足", str(closed[-1]["diagnostic"]))
            fixture.world.read_delay_s = 0.0
            self.assertTrue(session.invoke("compare", fixture.comparison("after-counter", "after", "/counter", 1, operator="delta", before="before"))["matched"])

    # 功能：writer 独占锁使同轮第二 writer 拒绝，不产生交叉 seq；参数 self 为测试实例。
    def test_writer_exclusive_lock(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with Journal(fixture.run), self.assertRaises(IntegrityError), Journal(fixture.run):
            self.fail("第二 writer 不应获得独占锁")
