"""创建日期：2026-10-26；作者：Cyou。
功能：生产 CLI/Session 逐条调用、独立新帧、合法前置、四状态及冻结/不重放隔离测试。
参数：内存后端返回真实外/内 eval 回执，不连接实际 Unity。
"""
from __future__ import annotations

import contextlib
import io
import json
import time
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from ..cli import build_parser, compact_result, main, result_exit
from ..contracts import EnvironmentBlocked, FrozenSession, InputError, IntegrityError, JsonObject, JsonValue, canonical
from ..evidence import Journal, record_data
from ..report import audit_run
from ..session import RULE_BASIS, Session, expand_rule_basis
from .support import Fixture, counter_case, readonly_case


class SessionTests(unittest.TestCase):
    # Codex: compact display changes only copies, preserving final facts, diagnostics and references.
    def test_compact_display_preserves_last_value_errors_exit_and_original_result(self) -> None:
        values: list[JsonObject] = [{"counter": number, "items": ["evidence" * 100]} for number in (3, 4, 5)]
        samples: list[JsonObject] = [{"command_id": "read-" + str(index), "frame": index + 10,
            "observation_id": "obs-" + str(index), "observation_valid": True, "observation_error": "",
            "observation_ref": {"path": "evidence/" + str(index), "sha256": "0" * 64}, "value": value,
            "receipt": {"state": "succeeded", "phase": "completed", "value": {"value": value}, "diagnostics": []}}
            for index, value in enumerate(values)]
        original: JsonObject = {"samples": samples, "last_observation_id": "obs-2", "frozen": False,
            "completion_required": True, "poll_matched": False}
        encoded: bytes = canonical(original)
        display: JsonObject = compact_result("observe", original)
        self.assertEqual(canonical(original), encoded)
        compact_samples: list[JsonObject] = cast(list[JsonObject], display["samples"])
        self.assertNotIn("value", compact_samples[0])
        self.assertEqual(compact_samples[-1]["value"], values[-1])
        for index, sample in enumerate(compact_samples):
            self.assertEqual(sample["frame"], samples[index]["frame"])
            self.assertEqual(sample["observation_ref"], samples[index]["observation_ref"])
            self.assertNotIn("value", cast(JsonObject, sample["receipt"]))
        self.assertLess(len(canonical(display)), len(encoded) // 2)
        self.assertEqual(result_exit("observe", original), result_exit("observe", display))
        samples[-1]["observation_valid"] = False
        samples[-1]["observation_error"] = "controlled or unknown diagnostic"
        self.assertEqual(cast(list[JsonObject], compact_result("observe", original)["samples"])[-1], samples[-1])
        self.assertFalse(build_parser().parse_args(["status", "--run", "sample"]).compact)
        self.assertTrue(build_parser().parse_args(["--compact", "status", "--run", "sample"]).compact)

    # Codex: the actual CLI keeps a full journal while printing compact samples and the same exit code.
    def test_compact_cli_keeps_full_journal_and_reliable_read_error_exit(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
        request: JsonObject = {"command_id": "compact-read", "observation_id": "compact-obs", "script": str(fixture.script("compact-read")),
            "scope": "discovery", "purpose": "before", "target": fixture.world.target,
            "read_only_review": "仅夹具：当前独立读取", "reason": "验证简洁 stdout 和完整 journal"}

        # Inject only the existing isolated identity and transport at the Python call boundary.
        def fixture_session(root: Path) -> Session:
            return Session(root, fixture.hooks, fixture.world.transport)

        with patch("scripts.cli.Session", side_effect=fixture_session):
            for index, mode in enumerate(("default", "compact", "error")):
                current: JsonObject = {**request, "command_id": "compact-read-" + str(index), "observation_id": "compact-obs-" + str(index)}
                path: Path = fixture.write_json("compact-" + mode + ".json", current)
                if mode == "error":
                    fixture.world.fail_next = "return_contract"
                output: io.StringIO = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code: int = main((["--compact"] if mode != "default" else []) + ["observe", "--run", str(fixture.run), "--request", str(path)])
                document: JsonObject = json.loads(output.getvalue().splitlines()[-1])
                result: JsonObject = cast(JsonObject, document["result"])
                sample: JsonObject = cast(list[JsonObject], result["samples"])[-1]
                self.assertEqual(code, 4 if mode == "error" else 0)
                self.assertEqual("value" in cast(JsonObject, sample["receipt"]), mode != "compact")
                if mode == "error":
                    self.assertTrue(result["case_frozen"])
                with Journal(fixture.run) as journal:
                    stored: JsonObject = [record_data(record) for record in journal.records if record["event"] == "cli_result"][-1]
                    full: JsonObject = cast(JsonObject, stored["result"])
                    self.assertIn("value", cast(JsonObject, cast(list[JsonObject], full["samples"])[-1]["receipt"]))
        self.assertNotIn(fixture.world.token, output.getvalue())

    # Codex: attaching discovers the current scene once and does not close the preparation chain.
    def test_attach_returns_initial_names_without_claiming_chain_readiness(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            result: JsonObject = session.invoke("attach", {})
            self.assertFalse(result["business_ready"])
            self.assertIsNone(session.state.chain_closed)
            self.assertEqual(fixture.world.eval_count, 1)
            self.assertEqual(cast(JsonObject, result["discovery"])["nodes"], [{"path": "FixtureRoot", "name": "FixtureRoot", "active": True}])

    # 功能：即使返回其它业务字段也不能把 success/assertion 绑定为产品预期；参数 self 为测试实例。
    def test_self_reported_success_field_binding_rejected(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        fixture.world.override_read = True
        fixture.world.returned_value = {"counter": 3, "success": True, "assertion": True}
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            for field in ("/success", "/assertion"):
                with self.assertRaises(InputError):
                    session.invoke("compare", fixture.comparison("self-claim", "before", field, True, case_id="R-1"))

    # 功能：验证无静态映射的逐条主动闭环及真实 passed；参数 self 为测试实例。
    def test_unmapped_live_read_action_assert_passed(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            counter, stock = fixture.execute_counter(session)
            self.assertEqual(counter["computed_value"], 1)
            self.assertEqual(stock["computed_value"], -4)
            self.assertTrue(counter["matched"])
            self.assertTrue(stock["matched"])
            final: JsonObject = session.invoke("final", {"status": "passed"})
            self.assertEqual(final["status"], "passed")
            session.invoke("close", {})
            audit: JsonObject = audit_run(session)
            self.assertEqual(audit["counts"]["passed"], 1)
            self.assertEqual(fixture.world.action_count, 1)

    # 功能：扣费反例在公共分类/判定/审计中保持 failed，不转环境阻塞；参数 self 为测试实例。
    def test_real_negative_failed_not_environment_blocked(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        fixture.world.charge_multiplier = 2
        with fixture.session() as session:
            counter, stock = fixture.execute_counter(session)
            self.assertTrue(counter["matched"])
            self.assertTrue(stock["valid"])
            self.assertFalse(stock["matched"])
            self.assertEqual(stock["status"], "failed")
            final: JsonObject = session.invoke("final", {"status": "blocked", "category": "environment", "reason": "反例仍应保持失败"})
            self.assertEqual(final["status"], "failed")
            session.invoke("close", {})
            audit: JsonObject = audit_run(session)
            self.assertEqual(audit["counts"]["failed"], 1)
            self.assertEqual(audit["counts"]["blocked"], 0)

    # 功能：没有执行许可的用例明确 blocked 且从未连接；参数 self 为测试实例。
    def test_permission_blocked_without_fake_execution(self) -> None:
        fixture: Fixture = Fixture(permissions=[])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("start-case", {"case_id": "C-1"})
            final: JsonObject = session.invoke("final", {"status": "blocked", "category": "permission", "required_permission": "script_execute", "reason": "本轮没有脚本许可"})
            self.assertEqual(final["status"], "blocked")
            self.assertEqual(final["action_command_ids"], [])
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["blocked"], 1)
        self.assertEqual(fixture.world.transport_count, 0)

    # 功能：旧帧不能通过，保留 test_inconclusive；参数 self 为测试实例。
    def test_old_frame_is_inconclusive(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.action(session, guards)
            fixture.world.old_frame = True
            observed: JsonObject = fixture.observe(session, "read-old", "old", "action-one")
            self.assertFalse(observed["samples"][0]["observation_valid"])
            comparison: JsonObject = session.invoke("compare", fixture.comparison("old-assert", "old", "/counter", 1, operator="delta", before="before"))
            self.assertEqual(comparison["status"], "test_inconclusive")
            final: JsonObject = session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                                                        "reason": "没有取得晚于动作帧的业务观测"})
            self.assertEqual(final["status"], "test_inconclusive")
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["test_inconclusive"], 1)

    # 功能：test_inconclusive 必须显式分类；未执行、无观测、无尝试分别被拒绝；参数 self 为测试实例。
    def test_inconclusive_requires_category_and_evidence(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        # 未执行任何动作/读取时，任何不确定分类都不得收口。
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "test_inconclusive", "reason": "缺 category"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "test_inconclusive", "category": "not_attempted", "reason": "尚未执行"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation", "reason": "无观测"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "test_inconclusive", "category": "not_constructible", "reason": "无尝试"})
        # 已真实观测后，观测不足可收口；不可构造仍需要真实尝试。
        fixture2: Fixture = Fixture()
        self.addCleanup(fixture2.cleanup)
        with fixture2.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture2.observe(session)
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "test_inconclusive", "category": "not_constructible", "reason": "仅读取未尝试"})
            final: JsonObject = session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                                                         "reason": "已读取但字段不足"})
            self.assertEqual(final["status"], "test_inconclusive")
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["test_inconclusive"], 1)

    # 功能：rule 简写展开与手写 basis 逐字节等价，未知规则被拒绝；参数 self 为测试实例。
    def test_rule_shorthand_expands_equivalent_and_rejects_unknown(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            manual: JsonObject = fixture.comparison("manual-read", "before", "/counter", 3, case_id="R-1")
            shorthand: JsonObject = {"schema": "mono-pipeline-comparison/1", "comparison_id": "rule-read",
                                     "scope": "expected", "index": 1, "original_text": manual["original_text"],
                                     "step_indices": [1], "observation_id": "before",
                                     "rule": "count_compare", "op": "eq", "target": "/counter", "value": 3}
            expanded: JsonObject = expand_rule_basis(shorthand)
            self.assertNotIn("rule", expanded)
            self.assertEqual(expanded["field"], manual["field"])
            self.assertEqual(expanded["operator"], manual["operator"])
            self.assertEqual(expanded["basis"]["value"], manual["basis"]["value"])
            self.assertEqual(expanded["basis"]["reviewer"], "current_agent")
            self.assertEqual(expanded["basis"]["statement"], RULE_BASIS["count_compare"]["statement"])
            result: JsonObject = session.invoke("compare", shorthand)
            self.assertEqual(result["status"], "passed")
            with self.assertRaises(InputError):
                expand_rule_basis({**shorthand, "comparison_id": "rule-bad", "rule": "unknown_rule"})
            partial: JsonObject = {key: value for key, value in shorthand.items() if key not in {"target", "value"}}
            with self.assertRaises(InputError):
                expand_rule_basis({**partial, "comparison_id": "rule-partial"})
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["passed"], 1)

    # 功能：纯只读例无需动作但仍独立比较原预期；参数 self 为测试实例。
    def test_readonly_case_can_pass_without_action(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            session.invoke("compare", fixture.comparison("readonly-expect", "before", "/counter", 3, case_id="R-1"))
            final: JsonObject = session.invoke("final", {"status": "passed"})
            self.assertEqual(final["action_command_ids"], [])
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["passed"], 1)

    # 功能：重复动作 ID 与换 ID 重复原步骤都不能重放；参数 self 为测试实例。
    def test_duplicate_command_and_step_never_replayed(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            fixture.execute_counter(session)
            with self.assertRaises(InputError):
                fixture.action(session, ["guard-unique", "guard-enabled"])
            with self.assertRaises(InputError):
                fixture.action(session, ["guard-unique", "guard-enabled"], "another-id")
            self.assertEqual(fixture.world.action_count, 1)

    # 功能：明确编译未执行允许新 ID 的显式字节更正；参数 self 为测试实例。
    def test_compile_failure_explicit_correction(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.world.fail_next = "compile"
            failed: JsonObject = fixture.action(session, guards, "compile-attempt")
            self.assertTrue(failed["not_executed"])
            self.assertEqual(failed["receipt"]["phase"], "compilation_not_executed")
            self.assertFalse(session.state.frozen)
            self.assertEqual(fixture.world.action_count, 0)
            with self.assertRaises(InputError):
                fixture.action(session, guards, "compile-attempt")
            corrected: Path = fixture.script("corrected", "ACTION")
            corrected.write_bytes(corrected.read_bytes().replace(b"return null;", b"return (object)null;"))
            actual: JsonObject = fixture.action(session, guards, "corrected-command", correction_of="compile-attempt", script_file=corrected)
            self.assertEqual(actual["receipt"]["state"], "succeeded")
            self.assertEqual(fixture.world.action_count, 1)
            first: JsonObject = record_data(session.state.commands["compile-attempt"])
            second: JsonObject = record_data(session.state.commands["corrected-command"])
            self.assertNotEqual(first["source_sha256"], second["source_sha256"])

    # 功能：部分生效后的运行异常冻结整轮，新 CLI 也不能恢复；参数 self 为测试实例。
    def test_runtime_unknown_freezes_persistent_session(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.world.fail_next = "runtime"
            result: JsonObject = fixture.action(session, guards)
            self.assertEqual(result["receipt"]["state"], "unknown")
            self.assertFalse(result["receipt"]["execution_terminated"])
            self.assertEqual(fixture.world.action_count, 1)
        transports: int = fixture.world.transport_count
        with fixture.session() as resumed:
            self.assertTrue(resumed.invoke("status", {})["frozen"])
            with self.assertRaises(FrozenSession):
                resumed.invoke("attach", {})
            with self.assertRaises(FrozenSession):
                fixture.observe(resumed, "forbidden-read", "forbidden", "action-one")
            resumed.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                                     "reason": "运行阶段未知，不能声称动作代码已停止"})
            resumed.invoke("close", {})
        self.assertEqual(fixture.world.transport_count, transports)

    # 功能：断连/意外传输异常/中断都走公共未知分类且不泄露令牌；参数 self 为测试实例。
    def test_transport_unknown_and_token_exclusion(self) -> None:
        for failure in ("disconnect", "timeout", "unexpected_exception", "keyboard", "invalid_response"):
            with self.subTest(failure=failure):
                fixture: Fixture = Fixture()
                try:
                    with fixture.session() as session:
                        session.invoke("attach", {})
                        session.invoke("start-case", {"case_id": "C-1"})
                        fixture.observe(session)
                        guards: list[JsonValue] = fixture.guards(session)
                        fixture.world.fail_next = failure
                        result: JsonObject = fixture.action(session, guards)
                        self.assertEqual(result["receipt"]["state"], "unknown")
                        self.assertTrue(session.state.frozen)
                    for path in fixture.run.rglob("*"):
                        if path.is_file():
                            self.assertNotIn(fixture.world.token.encode("ascii"), path.read_bytes())
                finally:
                    fixture.cleanup()

    # 功能：已发送 intent 丢失回执后开新 CLI 必须冻结，不自动恢复；参数 self 为测试实例。
    def test_lost_intent_freezes_without_replay(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("start-case", {"case_id": "C-1"})
            session.journal.append("intent", {"command_id": "lost-command", "mode": "read"}, "C-1")
        with fixture.session() as resumed:
            self.assertTrue(resumed.invoke("status", {})["frozen"])
            with self.assertRaises(FrozenSession):
                resumed.invoke("attach", {})
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：partial 覆盖或未绑定原预期不能 final passed；参数 self 为测试实例。
    def test_partial_steps_or_expected_cannot_pass(self) -> None:
        case: JsonObject = counter_case()
        case["steps"] = ["触发一次计数增加", "验证另一个未执行步骤"]
        fixture: Fixture = Fixture(cases=[case])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            fixture.execute_counter(session)
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})
            final: JsonObject = session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                                                         "reason": "第二原步骤没有真实执行关联"})
            self.assertEqual(final["coverage"]["missing_steps"], [2])
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["passed"], 0)

    # 功能：原预期文本和未登记基线不能静默替换；参数 self 为测试实例。
    def test_original_expected_binding_is_immutable(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            binding: JsonObject = fixture.comparison("weak", "before", "/counter", 3)
            binding["original_text"] = "页面存在即可"
            with self.assertRaises(InputError):
                session.invoke("compare", binding)

    # 功能：动作 success/assertion 本身不能形成产品通过；参数 self 为测试实例。
    def test_acknowledgement_not_independent_assertion(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            result: JsonObject = fixture.action(session, guards)
            self.assertTrue(result["receipt"]["value"]["value"]["success"])
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})

    # 功能：先读不足前置、授权精确构造、新帧回读后再单次原动作；参数 self 为测试实例。
    def test_legal_precondition_setup_and_independent_reread(self) -> None:
        case: JsonObject = counter_case()
        case["preconditions"] = ["库存满足独立配置成本"]
        fixture: Fixture = Fixture(cases=[case])
        self.addCleanup(fixture.cleanup)
        fixture.world.stock = 0
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.baseline(session)
            fixture.observe(session)
            condition: JsonObject = fixture.comparison("pre-before", "before", "/stock", 4, "precondition", operator="ge")
            self.assertFalse(session.invoke("compare", condition)["matched"])
            guards: list[JsonValue] = fixture.guards(session)
            with self.assertRaises(EnvironmentBlocked):
                fixture.action(session, guards)
            fixture.action(session, guards, "setup-one", scope="precondition")
            with self.assertRaises(InputError):
                fixture.action(session, guards, "too-early")
            fixture.observe(session, "read-setup", "setup-after", "setup-one", scope="precondition")
            condition = fixture.comparison("pre-after", "setup-after", "/stock", 4, "precondition", operator="ge")
            self.assertTrue(session.invoke("compare", condition)["matched"])
            ready: list[JsonValue] = fixture.guards(session, "setup-after", "ready")
            fixture.action(session, ready, "business-one", "setup-after")
            fixture.observe(session, "read-business", "business-after", "business-one")
            counter, cost = fixture.assert_changes(session, "business-after", "setup-after")
            self.assertTrue(counter["matched"] and cost["matched"])
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            self.assertEqual(audit_run(session)["counts"]["passed"], 1)
        self.assertEqual((fixture.world.setup_count, fixture.world.action_count), (1, 1))

    # 功能：缺目标/字段/类型不足不变默认值通过；参数 self 为测试实例。
    def test_missing_field_or_null_cannot_pass(self) -> None:
        for value in (None, {}, {"counter": "3"}, {"success": True, "assertion": True}):
            with self.subTest(value=value):
                fixture: Fixture = Fixture(cases=[readonly_case()])
                try:
                    fixture.world.override_read = True
                    fixture.world.returned_value = value
                    with fixture.session() as session:
                        session.invoke("attach", {})
                        session.invoke("start-case", {"case_id": "R-1"})
                        fixture.observe(session, covers=True)
                        result: JsonObject = session.invoke("compare", fixture.comparison("expect-read", "before", "/counter", 3, case_id="R-1"))
                        self.assertEqual(result["status"], "test_inconclusive")
                        with self.assertRaises(InputError):
                            session.invoke("final", {"status": "passed"})
                finally:
                    fixture.cleanup()

    # 功能：可选桥接值解包不成为基础读取硬依赖；参数 self 为测试实例。
    def test_bridge_envelope_observation(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            result: JsonObject = fixture.observe(session, covers=True, marker="BRIDGE_READ")
            self.assertEqual(result["samples"][0]["value"]["counter"], 3)
            self.assertTrue(result["samples"][0]["observation_valid"])

    # 功能：宿主构建身份错误导致全轮冻结；参数 self 为测试实例。
    def test_wrong_envelope_identity_freezes(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.world.wrong_envelope_identity = True
            result: JsonObject = fixture.observe(session)
            self.assertEqual(result["samples"][0]["receipt"]["state"], "unknown")
            self.assertTrue(session.state.frozen)

    # 功能：每次 CLI 重新构造 Session 仍实际执行/记录，测试旁路仅在 Python patch 层；参数 self 为测试实例。
    def test_real_cli_persistent_step_by_step(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        # 功能：替换仅调用层依赖，不增加正式 CLI 参数；参数 root 是每次 CLI 解析的真实本轮。
        def injected_session(root: Path) -> Session:
            return Session(root, fixture.hooks, fixture.world.transport)
        output: io.StringIO = io.StringIO()
        observe: JsonObject = {"command_id": "cli-read", "observation_id": "cli-observation", "script": str(fixture.script("cli-read")),
                               "purpose": "step", "scope": "step", "index": 1, "original_text": "读取当前计数",
                               "target": fixture.world.target, "read_only_review": "当前 Agent 审核只读", "reason": "当前原步骤实际读取", "covers_step": True}
        observe_file: Path = fixture.write_json("cli-observe.json", observe)
        compare_file: Path = fixture.write_json("cli-compare.json", fixture.comparison("cli-expect", "cli-observation", "/counter", 3, case_id="R-1"))
        final_file: Path = fixture.write_json("cli-final.json", {"status": "passed"})
        commands: list[list[str]] = [["attach"], ["start-case", "--case-id", "R-1"],
                                    ["observe", "--request", str(observe_file)], ["compare", "--request", str(compare_file)],
                                    ["final", "--request", str(final_file)], ["close"], ["audit"], ["report"]]
        with patch("scripts.cli.Session", injected_session), contextlib.redirect_stdout(output):
            for command in commands:
                self.assertEqual(main(command + ["--run", str(fixture.run)]), 0)
        with Journal(fixture.run) as journal:
            operations: list[JsonValue] = [record_data(record)["operation"] for record in journal.records if record["event"] == "cli_result"]
            self.assertTrue(all(command[0] in operations for command in commands))
        self.assertNotIn(fixture.world.token, output.getvalue())

    # 功能：新 CLI 正常身份重验，未知后不自动连接；参数 self 为测试实例。
    def test_normal_new_cli_revalidates_identity(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
        first: int = fixture.world.transport_count
        with fixture.session() as session:
            fixture.observe(session, covers=True)
        self.assertEqual(fixture.world.transport_count, first + 1)

    # 功能：唯一 final 不允许任意覆盖或本例重跑；参数 self 为测试实例。
    def test_final_is_unique(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            fixture.execute_counter(session)
            session.invoke("final", {"status": "passed"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})
            with self.assertRaises(InputError):
                session.invoke("start-case", {"case_id": "C-1"})
