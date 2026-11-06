"""创建日期：2026-11-03；作者：Cyou。
功能：回归真实日志中的登记前漏检、旧 before 守卫、原地覆盖、单例冻结与审计不一致。
参数：生产 Session 和隔离身份/传输夹具；不启动 Player，不把夹具通过当作实机验收。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from ..contracts import InputError, IntegrityError, JsonObject, JsonValue, Limits, SecretGuard, canonical
from ..evidence import record_data
from ..cli import result_exit
from ..pipeline import wrap_script
from ..session import PLAN_SCHEMA, SUITE_SCHEMA, Session, builtin_observation
from .support import Fixture, counter_case, readonly_case


class SubmissionRepairTests(unittest.TestCase):
    """同一通用宿主同时检查结构错误的早拒绝和有效原始证据的不可变性。"""

    # 功能：创建独立夹具并登记清理；参数 cases 为完整原例，默认是按配置扣费的通用动作例。
    def fixture(self, cases: list[JsonObject] | None = None) -> Fixture:
        fixture: Fixture = Fixture(cases=cases)
        self.addCleanup(fixture.cleanup)
        return fixture

    # 功能：生成与实际原例绑定的只读计划；参数 fixture/case_id/tag 保持各例观察和命令 ID 唯一。
    def readonly_plan(self, fixture: Fixture, case_id: str, tag: str) -> JsonObject:
        source = fixture.original.case(case_id)
        observation: JsonObject = {"command_id": "read-" + tag, "observation_id": "obs-" + tag,
            "script": str(fixture.script("read-" + tag)), "scope": "step", "index": 1,
            "original_text": source.item("step", 1).text, "covers_step": True, "purpose": "step",
            "target": fixture.world.target, "read_only_review": "当前 Agent 核对本片段只读实际计数", "reason": "精确读取原例计数"}
        comparison: JsonObject = fixture.comparison("compare-" + tag, "obs-" + tag, "/counter", 3, case_id=case_id)
        return {"case_id": case_id, "steps": [
            {"operation": "start-case", "request": {"case_id": case_id}},
            {"operation": "observe", "request": observation},
            {"operation": "compare", "request": comparison},
            {"operation": "final", "request": {"status": "passed"}}]}

    # Codex: construct a fixed click request using only a path from the current observation.
    def click_request(self, fixture: Fixture, before: str = "buttons", command: str = "click-one") -> JsonObject:
        return {"command_id": command, "builtin": "click_button", "builtin_options": {"path": "FixtureRoot/Container/Button"},
            "scope": "step", "index": 1, "original_text": fixture.original.case("B-1").item("step", 1).text,
            "target": fixture.world.target, "before_observation_id": before, "guard_comparison_ids": ["button-unique", "button-enabled"],
            "target_review": "仅夹具：当前后代按钮的真实实例和交互状态已核对", "reason": "原步骤授权内一次调用，不用方法回执断言产品"}

    # Codex: read actual synthetic button rows through the production builtin source path.
    def read_buttons(self, fixture: Fixture, session: Session, observation: str = "buttons") -> None:
        request: JsonObject = {"command_id": "read-" + observation, "observation_id": observation,
            "builtin": "buttons", "builtin_options": {"root": "FixtureRoot/Container"}, "scope": "discovery", "purpose": "before",
            "target": fixture.world.target, "read_only_review": "仅夹具：读取当前按钮实例", "reason": "选择真实后代按钮"}
        session.invoke("observe", request)
        for suffix, field, expected in (("unique", "/count", 1), ("enabled", "/nodes/0/interactable", True)):
            session.invoke("compare", fixture.comparison("button-" + suffix, observation, field, expected, "guard", case_id="B-1"))

    # Codex: the fixed click must use existing guards, execute once and require independent results.
    def test_builtin_click_keeps_one_action_and_independent_product_verdict(self) -> None:
        for actual_count, expected_status in ((4, "passed"), (5, "failed")):
            with self.subTest(actual_count=actual_count):
                fixture: Fixture = self.fixture([{"case_id": "B-1", "title": "独立按钮计数", "preconditions": [],
                    "steps": ["点击一次实际按钮"], "expected": ["按钮点击后当前计数为4"]}])
                with fixture.session() as session:
                    attached: JsonObject = session.invoke("attach", {})
                    self.assertFalse(attached["business_ready"])
                    self.assertIsNotNone(attached["discovery"])
                    session.invoke("start-case", {"case_id": "B-1"})
                    self.read_buttons(fixture, session)
                    request: JsonObject = self.click_request(fixture)
                    result: JsonObject = session.invoke("action", request)
                    self.assertEqual(cast(JsonObject, result["receipt"])["state"], "succeeded")
                    fixture.world.counter = actual_count
                    fixture.observe(session, "read-after-click", "after-click", "click-one")
                    session.invoke("compare", fixture.comparison("button-result", "after-click", "/counter", 4, case_id="B-1"))
                    self.assertEqual(session.invoke("final", {"status": "passed"})["status"], expected_status)
                    session.invoke("close", {})
                    session.invoke("audit", {})
                self.assertEqual(fixture.world.action_count, 1)

    # Codex: values with a spoofed op cannot replace a host-generated buttons observation.
    def test_builtin_click_rejects_handwritten_button_values_without_sending(self) -> None:
        fixture: Fixture = self.fixture([{"case_id": "B-1", "title": "按钮来源", "preconditions": [],
            "steps": ["点击一次实际按钮"], "expected": ["按钮点击后当前计数为4"]}])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "B-1"})
            self.read_buttons(fixture, session)
            fixture.world.returned_value = session.state.cases["B-1"].observations["buttons"]["value"]
            fixture.world.override_read = True
            # New IDs are required for this separate, deliberately handwritten before.
            session.invoke("observe", {"command_id": "spoof-read", "observation_id": "spoof",
                "script": str(fixture.script("spoof")), "scope": "discovery", "purpose": "before", "target": fixture.world.target,
                "read_only_review": "隔离的伪同名值反例", "reason": "验证来源而非只检查 op 名称"})
            for suffix, field, expected in (("unique", "/count", 1), ("enabled", "/nodes/0/interactable", True)):
                session.invoke("compare", fixture.comparison("spoof-" + suffix, "spoof", field, expected, "guard", case_id="B-1"))
            request: JsonObject = {**self.click_request(fixture, "spoof"), "guard_comparison_ids": ["spoof-unique", "spoof-enabled"]}
            evaluations: int = fixture.world.eval_count
            with self.assertRaisesRegex(InputError, "不能采用手写"):
                session.invoke("action", request)
            self.assertEqual(fixture.world.eval_count, evaluations)
            self.assertEqual(fixture.world.action_count, 0)

    # Codex: a batch using the same fixed entry is accepted; a non-buttons before is rejected.
    def test_builtin_click_plan_is_checked_before_registration(self) -> None:
        fixture: Fixture = self.fixture([{"case_id": "B-1", "title": "按钮计划", "preconditions": [],
            "steps": ["点击一次实际按钮"], "expected": ["按钮点击后当前计数为4"]}])
        before: JsonObject = {"command_id": "read-buttons", "observation_id": "buttons", "builtin": "buttons",
            "builtin_options": {"root": "FixtureRoot/Container"}, "scope": "discovery", "purpose": "before",
            "target": fixture.world.target, "read_only_review": "仅夹具：读取按钮", "reason": "原步骤真实按钮"}
        after: JsonObject = {"command_id": "read-result", "observation_id": "result", "script": str(fixture.script("read-result")),
            "scope": "discovery", "purpose": "after", "after_command_id": "click-one", "target": fixture.world.target,
            "read_only_review": "仅夹具：独立结果计数", "reason": "独立读取点击后的业务字段"}
        steps: list[JsonObject] = [
            {"operation": "start-case", "request": {"case_id": "B-1"}}, {"operation": "observe", "request": before},
            *[{"operation": "compare", "request": fixture.comparison("button-" + suffix, "buttons", field, expected, "guard", case_id="B-1")}
              for suffix, field, expected in (("unique", "/count", 1), ("enabled", "/nodes/0/interactable", True))],
            {"operation": "action", "request": self.click_request(fixture)}, {"operation": "observe", "request": after},
            {"operation": "compare", "request": fixture.comparison("expected", "result", "/counter", 4, case_id="B-1")},
            {"operation": "final", "request": {"status": "passed"}}]
        plan: JsonObject = {"schema": PLAN_SCHEMA, "case_id": "B-1", "steps": steps}
        path: Path = fixture.write_json("click-plan.json", plan)
        with fixture.session() as session:
            session.check_plan(plan)
            steps[1]["request"] = {**before, "builtin": "chain"}
            with self.assertRaisesRegex(InputError, "builtin:buttons"):
                session.check_plan(plan)
            steps[1]["request"] = before
            session.invoke("attach", {})
            self.assertEqual(cast(JsonObject, session.invoke_plan(plan, path)["last_result"])["status"], "passed")
            session.invoke("close", {})
            session.invoke("report", {})

    # 功能：缺关键字段或比较值误放顶层必须在计划登记前拒绝；参数 self 不提供 Player 旁路。
    def test_plan_rejects_bad_comparison_before_registration(self) -> None:
        for mistake in ("missing_field", "top_level_value", "bad_pointer", "wrong_schema"):
            with self.subTest(mistake=mistake):
                fixture: Fixture = self.fixture([readonly_case()])
                body: JsonObject = self.readonly_plan(fixture, "R-1", mistake)
                steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
                request: JsonObject = cast(JsonObject, steps[2]["request"])
                if mistake == "missing_field":
                    request.pop("field")
                elif mistake == "top_level_value":
                    request["value"] = 3
                elif mistake == "bad_pointer":
                    request["field"] = "/bad~2field"
                else:
                    request["schema"] = "incorrect/1"
                plan: JsonObject = {"schema": PLAN_SCHEMA, **body}
                path: Path = fixture.write_json("plan.json", plan)
                with fixture.session() as session:
                    before: int = len(session.journal.records)
                    with self.assertRaises(InputError):
                        session.check_plan(plan)
                    with self.assertRaises(InputError):
                        session.invoke_plan(plan, path)
                    self.assertEqual(len(session.journal.records), before)
                self.assertEqual(fixture.world.transport_count, 0)

    # 功能：错误原文不登记来源，草稿修正不会冻结，但有效登记后的改写仍冻结；参数 self 保留所有真实源字节。
    def test_invalid_draft_is_not_registered_and_published_source_remains_immutable(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            request: JsonObject = fixture.comparison("guard-one", "before", "/unique_count", 1, "guard")
            request["original_text"] = "误用了前置原文"
            draft: Path = fixture.write_json("draft.json", request)
            before: int = len(session.journal.records)
            with self.assertRaises(InputError):
                session.check_request("compare", request)
            self.assertEqual(len(session.journal.records), before)
            with self.assertRaises(InputError):
                session.invoke("compare", request, draft)
            self.assertFalse(any(record["event"] == "request_registered" for record in session.journal.records))
            request["original_text"] = fixture.original.case("C-1").item("guard", 1).text
            draft.write_bytes(canonical(request))
            directory: Path = fixture.root / "published"
            one: Path = session.publish_request("compare", request, directory)
            two: Path = session.publish_request("compare", request, directory)
            self.assertNotEqual(one, two)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            self.assertTrue(session.invoke("compare", request, one)["matched"])
            self.assertFalse(session.state.frozen)
            one.write_bytes(canonical({**request, "original_text": "登记后改写"}))
            self.assertTrue(session.invoke("status", {})["frozen"])

    # 功能：守卫引用旧 before 时在普通请求登记前拒绝，不触发动作；参数 self 精确复现登录链路错绑。
    def test_current_guard_mismatch_is_rejected_before_request_registration(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.observe(session, "new-read", "new-before")
            request: JsonObject = {"command_id": "bad-action", "script": str(fixture.script("bad-action", "ACTION")),
                "scope": "step", "index": 1, "original_text": fixture.original.case("C-1").item("step", 1).text,
                "target": fixture.world.target, "before_observation_id": "new-before", "guard_comparison_ids": guards,
                "target_review": "当前 Agent 审核唯一目标", "reason": "复现错绑守卫"}
            path: Path = fixture.write_json("bad-action.json", request)
            with self.assertRaisesRegex(InputError, "同一当前目标 before"):
                session.invoke("action", request, path)
            self.assertFalse(any(record["event"] == "request_registered" for record in session.journal.records))
            self.assertFalse(session.state.frozen)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：已观测但旧帧无效仍是诚实未定论，执行、close、audit、report 判据必须一致；参数 self 不伪造通过。
    def test_invalid_actual_observation_can_close_and_report_inconclusive(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.missing_target = True
            fixture.observe(session, marker="BRIDGE", covers=True)
            self.assertFalse(any(value["valid"] is True for value in session.state.cases["R-1"].observations.values()))
            session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation", "reason": "真实桥接目标缺失，不形成产品反例"})
            session.invoke("close", {})
            result: JsonObject = session.invoke("report", {})
            self.assertEqual(cast(JsonObject, cast(JsonObject, result["audit"])["counts"])["test_inconclusive"], 1)

    # 功能：只读脚本失败后计划真实收口本例，下一例继续；参数 self 使用生产分类器和 journal 审计。
    def test_read_script_failure_closes_one_case_and_keeps_other_cases_executable(self) -> None:
        fixture: Fixture = self.fixture([readonly_case("R-1"), readonly_case("R-2")])
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [self.readonly_plan(fixture, "R-1", "one"), self.readonly_plan(fixture, "R-2", "two")]}
        path: Path = fixture.write_json("suite.json", suite)
        with fixture.session() as session:
            session.invoke("attach", {})
            fixture.world.fail_next = "script"
            result: JsonObject = session.invoke_suite(suite, path)
            self.assertEqual(result["statuses"], ["test_inconclusive", "passed"])
            self.assertFalse(session.state.frozen)
            self.assertTrue(session.state.cases["R-1"].frozen)
            self.assertEqual(sum(record["event"] == "case_final" for record in session.journal.records), 2)
            session.invoke("close", {})
            session.invoke("report", {})

    # Codex: a trusted return projection failure stops this case, then the batch continues.
    def test_return_contract_failure_keeps_other_cases_and_report_executable(self) -> None:
        fixture: Fixture = self.fixture([readonly_case("R-1"), readonly_case("R-2")])
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [self.readonly_plan(fixture, "R-1", "one"), self.readonly_plan(fixture, "R-2", "two")]}
        path: Path = fixture.write_json("suite.json", suite)
        with fixture.session() as session:
            session.invoke("attach", {})
            fixture.world.fail_next = "return_contract"
            result: JsonObject = session.invoke_suite(suite, path)
            self.assertEqual(result["statuses"], ["test_inconclusive", "passed"])
            self.assertFalse(session.state.frozen)
            self.assertTrue(session.state.cases["R-1"].frozen)
            first: JsonObject = record_data(session.state.results["read-one"])
            self.assertEqual(cast(JsonObject, first["receipt"])["state"], "succeeded")
            self.assertIsNotNone(first["observation_ref"])
            self.assertFalse(first["observation_valid"])
            self.assertFalse(first["not_executed"])
            session.invoke("close", {})
            self.assertEqual(cast(JsonObject, session.invoke("report", {})["audit"])["final_count"], 2)

    # Codex: single-step output and replay preserve the case-only stop and exit code 4.
    def test_return_contract_read_exits_inconclusive_and_persists_after_reopen(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.fail_next = "return_contract"
            result: JsonObject = fixture.observe(session, covers=True)
            self.assertEqual(result_exit("observe", result), 4)
            self.assertTrue(result["case_frozen"])
            self.assertFalse(result["frozen"])
        with fixture.session() as session:
            self.assertTrue(session.state.cases["R-1"].frozen)
            session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation", "reason": "真实返回契约错误"})
            session.invoke("close", {})
            session.invoke("audit", {})

    # Codex: the isolated legacy generation still audits and reports under the new host.
    def test_legacy_seven_field_wrapper_is_still_auditable(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])

        # Generate the previous exact wrapper without changing production version selection.
        def legacy(raw: bytes, run: str, case: str, command: str, limits: Limits, guard: SecretGuard) -> bytes:
            return wrap_script(raw, run, case, command, limits, guard, 1)

        with patch("scripts.session.wrap_script", side_effect=legacy), fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            session.invoke("compare", fixture.comparison("legacy-count", "before", "/counter", 3, case_id="R-1"))
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            session.invoke("report", {})

    # Codex: a later trusted return error cannot erase an independently observed failure.
    def test_return_contract_failure_keeps_existing_failed_latch(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.counter = 4
            fixture.observe(session, covers=True)
            session.invoke("compare", fixture.comparison("wrong-count", "before", "/counter", 3, case_id="R-1"))
            fixture.world.fail_next = "return_contract"
            fixture.observe(session, "later-read", "later")
            result: JsonObject = session._plan_step("final", {"status": "passed"})
            self.assertEqual(result["status"], "failed")
            session.invoke("close", {})
            session.invoke("audit", {})

    # Codex: the same error on an action or with an invalid identity still stops the run.
    def test_return_contract_action_or_invalid_identity_still_freezes_run(self) -> None:
        for action in (False, True):
            with self.subTest(action=action):
                fixture: Fixture = self.fixture()
                with fixture.session() as session:
                    session.invoke("attach", {})
                    session.invoke("start-case", {"case_id": "C-1"})
                    if action:
                        fixture.observe(session)
                        guards: list[JsonValue] = fixture.guards(session)
                    else:
                        fixture.world.wrong_envelope_identity = True
                    fixture.world.fail_next = "return_contract"
                    result: JsonObject = fixture.action(session, guards) if action else fixture.observe(session)
                    self.assertTrue(session.state.frozen)
                    self.assertFalse(session.state.cases["C-1"].frozen)
                    if action:
                        session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation", "reason": "动作未知，保留整轮冻结"})
                    session.invoke("close", {} if action else {"interrupted_reason": "身份不可靠，没有有效观察，不补造 final"})
                    session.invoke("audit", {})

    # Codex: an invented case-freeze event cannot qualify for a formal report.
    def test_case_freeze_requires_a_corresponding_read_error(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            session._freeze_case("R-1", "return_value_contract:unsupported_return_type", "return_value_contract", "read-before")
            with self.assertRaises(IntegrityError):
                session.invoke("audit", {})

    # 功能：相同 script_failed 回执若来自动作，仍全轮冻结且审计不能误认只读失败；参数 self 保留可能部分副作用。
    def test_action_script_failure_still_freezes_entire_run_and_audits(self) -> None:
        fixture: Fixture = self.fixture([counter_case("C-1"), readonly_case("R-2")])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
            guards: list[JsonValue] = fixture.guards(session)
            fixture.world.fail_next = "script"
            fixture.action(session, guards)
            self.assertTrue(session.state.frozen)
            self.assertFalse(session.state.cases["C-1"].frozen)
            session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation", "reason": "动作副作用未知，整轮停止且不重放"})
            session.invoke("close", {"interrupted_reason": "动作结果未知，未执行第二例"})
            self.assertEqual(session.invoke("audit", {})["final_count"], 1)
        self.assertEqual(fixture.world.action_count, 1)

    # 功能：结构选项类型错误必须是 InputError 而非宿主冻结；参数 self 覆盖 JSON 合法但控制类型非法。
    def test_non_text_control_is_an_input_error_without_registration(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("start-case", {"case_id": "C-1"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": {"invalid": True}})
            self.assertFalse(session.state.frozen)

    # 功能：通用观测必须支持自定义按钮、真实热更实例类型和完整路径，不退化为字符串或业务硬编码；参数 self 静态检查生成体。
    def test_builtins_use_custom_controls_instance_types_and_strict_scalar_values(self) -> None:
        buttons: str = builtin_observation("buttons", {"root": "Root/UI"}).decode("utf-8")
        logic: str = builtin_observation("logic_field", {"logic_type": "Example.Logic", "field": "_counter", "root": "Root/UI"}).decode("utf-8")
        chain: str = builtin_observation("chain", {"root": "Root/UI"}).decode("utf-8")
        self.assertIn('"GameButton"', buttons)
        self.assertIn('"m_MonoInvocationAdapter"', logic)
        self.assertIn("__inst.GetType()", logic)
        self.assertIn('"instance_count"', logic)
        self.assertIn("__path(__t)", chain)
        for body in (buttons, logic, chain):
            self.assertNotIn("var ", body)
            self.assertNotIn("DrawCard", body)

    # 功能：现有 baseline 可直接登记真实配置观察文件；参数 self 不复制 UI 实际值为预期。
    def test_configuration_observation_can_be_registered_as_an_existing_baseline(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.override_read = True
            fixture.world.returned_value = {"configuration": {"required_count": 3}}
            observed: JsonObject = fixture.observe(session, "read-config", "config", scope="discovery")
            reference: JsonObject = cast(JsonObject, cast(list[JsonObject], observed["samples"])[-1]["observation_ref"])
            session.invoke("baseline", {"reference_id": "configuration", "kind": "configuration",
                "path": str(fixture.run / str(reference["path"])), "sha256": reference["sha256"],
                "review": "隔离配置原值 required_count=3，不来自 UI 当前计数；直接登记宿主保存的观察原文件"})
            fixture.world.override_read = False
            fixture.observe(session, "read-ui", "ui", covers=True)
            comparison: JsonObject = fixture.comparison("config-vs-ui", "ui", "/counter", 3, case_id="R-1")
            comparison["basis"] = {"kind": "baseline", "reference_id": "configuration",
                "field": "/value/configuration/required_count", "reviewer": "current_agent",
                "statement": "使用先行配置读取的独立原值", "semantic_review": "UI 计数按配置要求比较，不反推预期"}
            self.assertTrue(session.invoke("compare", comparison)["matched"])
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            self.assertEqual(cast(JsonObject, session.invoke("report", {})["audit"])["final_count"], 1)

    # 功能：配置与 UI 独立读取不掩盖反例；参数 self 保留错误 UI 值产生的失败锁存。
    def test_observation_baseline_keeps_wrong_ui_values_failed(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.world.override_read = True
            fixture.world.returned_value = {"configuration": {"required_count": 3}}
            observed: JsonObject = fixture.observe(session, "read-config", "config", scope="discovery")
            reference: JsonObject = cast(JsonObject, cast(list[JsonObject], observed["samples"])[-1]["observation_ref"])
            session.invoke("baseline", {"reference_id": "configuration", "kind": "configuration",
                "path": str(fixture.run / str(reference["path"])), "sha256": reference["sha256"],
                "review": "配置来源为先行只读观察，不使用错误 UI 值修改基线"})
            fixture.world.override_read = False
            fixture.world.counter = 4
            fixture.observe(session, "read-wrong-ui", "wrong-ui", covers=True)
            comparison: JsonObject = fixture.comparison("config-vs-wrong-ui", "wrong-ui", "/counter", 3, case_id="R-1")
            comparison["basis"] = {"kind": "baseline", "reference_id": "configuration",
                "field": "/value/configuration/required_count", "reviewer": "current_agent",
                "statement": "独立配置要求为3，UI当前为4", "semantic_review": "不按当前 UI 值重写预期"}
            result: JsonObject = session.invoke("compare", comparison)
            self.assertTrue(result["valid"])
            self.assertFalse(result["matched"])
            self.assertEqual(session.invoke("final", {"status": "passed"})["status"], "failed")
            session.invoke("close", {})
            session.invoke("audit", {})
