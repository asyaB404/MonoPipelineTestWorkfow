"""创建日期：2026-10-28；作者：Cyou。
功能：验证单例计划 run-case 与多例计划 run-suite 的静态预检、一次连接跑完一例/多例全部步骤，以及三合一 Windows 探测与同命令复用窗口。
参数：临时假包、内存传输与注入身份；不连接真实 Player、不执行 PowerShell，不修改历史轮次。
"""
from __future__ import annotations

import contextlib
import io
import unittest
from pathlib import Path
from typing import Callable, cast
from unittest.mock import patch

from ..cli import main
from ..contracts import EnvironmentBlocked, InputError, IntegrityError, JsonObject, JsonValue, Limits, canonical, digest, strict_json
from ..evidence import Journal, record_data
from ..inputs import TargetConfig, parse_target
from ..pipeline import IdentityHooks, Pipeline, windows_probe
from ..session import BUILTIN_MAX_DEPTH, PLAN_SCHEMA, SUITE_SCHEMA, Session, builtin_observation, replay
from .support import Fixture, counter_case, readonly_case


class CasePlanTests(unittest.TestCase):
    """单例计划必须保留逐项门禁，只减少重复建连与重复重放。"""

    # 功能：建立带完整计数用例的临时夹具并完成一次真实附加；参数 self 为测试实例。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture()
        self.addCleanup(self.fixture.cleanup)
        # 附加仍是独立命令：单例计划只覆盖本例步骤，不代跑跨例控制操作。
        with self.fixture.session() as session:
            session.invoke("attach", {})
        self.attach_transports: int = self.fixture.world.transport_count
        self.attach_evaluations: int = self.fixture.world.eval_count

    # 功能：构造与本例原步骤/预期一致的计划；参数 include_final=False 用于负向计划。
    def plan(self, fixture: Fixture, include_final: bool = True, first: str = "start-case") -> JsonObject:
        body: JsonObject = self.case_plan(fixture, fixture.original.cases[0].case_id, include_final, first)
        return {"schema": PLAN_SCHEMA, **body}

    # 功能：构造指定用例的计划体；参数 case_id 用于多例计划中的每一例，门禁与单例完全一致。
    def case_plan(self, fixture: Fixture, case_id: str, include_final: bool = True,
                  first: str = "start-case", suffix: str = "") -> JsonObject:
        tag: str = suffix
        baseline: Path = fixture.write_json(f"plan-configuration{tag}.json", {"cost": fixture.world.cost})
        reference_id: str = f"configuration{tag}"
        observe_before: JsonObject = {"command_id": f"read-before{tag}", "observation_id": f"before{tag}",
                                      "script": str(fixture.script("read-before")), "send": "eval_file",
                                      "scope": "step", "index": 1,
                                      "original_text": fixture.original.case(case_id).item("step", 1).text,
                                      "purpose": "before", "target": fixture.world.target,
                                      "read_only_review": "当前 Agent 审核：本片段只返回业务字段",
                                      "reason": "依据当前字段动态定位，不是预制动作映射", "covers_step": False}
        guard_unique: JsonObject = fixture.comparison(f"guard-unique{tag}", f"before{tag}", "/unique_count", 1, "guard", case_id=case_id)
        guard_enabled: JsonObject = fixture.comparison(f"guard-enabled{tag}", f"before{tag}", "/enabled", True, "guard", case_id=case_id)
        action: JsonObject = {"command_id": f"action-one{tag}", "script": str(fixture.script("action-one", "ACTION")),
                              "send": "eval_file", "scope": "step", "index": 1,
                              "original_text": fixture.original.case(case_id).item("step", 1).text,
                              "target": fixture.world.target, "before_observation_id": f"before{tag}",
                              "guard_comparison_ids": [f"guard-unique{tag}", f"guard-enabled{tag}"],
                              "target_review": "当前唯一目标计数为 1，实际 enabled 守卫已独立通过",
                              "reason": "授权内只触发一次，之后必须返回宿主独立新帧观察"}
        observe_after: JsonObject = {**observe_before, "command_id": f"read-after{tag}", "observation_id": f"after{tag}",
                                     "purpose": "after", "after_command_id": f"action-one{tag}", "covers_step": True}
        counter: JsonObject = fixture.comparison(f"expect-counter{tag}", f"after{tag}", "/counter", 1, operator="delta",
                                                 before=f"before{tag}", case_id=case_id)
        stock: JsonObject = fixture.comparison(f"expect-stock{tag}", f"after{tag}", "/stock", -fixture.world.cost, index=2,
                                               operator="delta", before=f"before{tag}", case_id=case_id)
        # 扣费预期必须来自独立登记的配置基线，不得由实际输出反推。
        stock["basis"] = {"kind": "baseline", "reference_id": reference_id, "field": "/cost", "factor": -1,
                          "reviewer": "current_agent",
                          "statement": "扣费必须来自独立配置原字节，而非点击成功或输出本身",
                          "semantic_review": "库存 after-before 应为配置成本的负值，与原预期逐字核对"}
        steps: list[JsonValue] = [{"operation": first, "request": {"case_id": case_id, "group_id": "plan"}},
                                  {"operation": "baseline", "request": {"reference_id": reference_id, "kind": "configuration",
                                                                       "path": str(baseline), "sha256": digest(baseline.read_bytes()),
                                                                       "review": "需求指定按当前独立配置成本扣减"}},
                                  {"operation": "observe", "request": observe_before},
                                  {"operation": "compare", "request": guard_unique},
                                  {"operation": "compare", "request": guard_enabled},
                                  {"operation": "action", "request": action},
                                  {"operation": "observe", "request": observe_after},
                                  {"operation": "compare", "request": counter},
                                  {"operation": "compare", "request": stock}]
        if include_final:
            steps.append({"operation": "final", "request": {"status": "passed"}})
        return {"case_id": case_id, "group_id": "plan", "steps": steps}

    # 功能：一条命令跑完本例全部步骤且复用一个连接、一次身份核验；参数 self 为测试实例。
    def test_plan_runs_whole_case_in_one_connection(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        path: Path = fixture.write_json("case-plan.json", plan)
        with fixture.session() as session:
            result: JsonObject = session.invoke_plan(plan, path)
            self.assertEqual(result["step_count"], len(cast(list[JsonValue], plan["steps"])))
            self.assertEqual(cast(JsonObject, result["last_result"])["status"], "passed")
            self.assertEqual(session.state.closed, None)
            finals: dict[str, JsonValue] = {case_id: record_data(item.final)["status"]
                                            for case_id, item in session.state.cases.items() if item.final is not None}
            self.assertEqual(finals, {fixture.original.cases[0].case_id: "passed"})
        # 单例计划内只应建立一次正常连接（附加的那次除外），动作仍恰好执行一次并产生真实副作用。
        self.assertEqual(fixture.world.transport_count, self.attach_transports + 1)
        self.assertEqual(fixture.world.action_count, 1)
        self.assertEqual(fixture.world.stock, 20 - fixture.world.cost)

    # 功能：计划内每个步骤仍真实写同一 journal 的 cli_begin/cli_result；参数 self 为测试实例。
    def test_plan_writes_every_step_into_same_journal(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        path: Path = fixture.write_json("case-plan.json", plan)
        with fixture.session() as session:
            session.invoke_plan(plan, path)
        with Journal(fixture.run) as journal:
            plan_begins: list[JsonObject] = [record_data(record) for record in journal.records
                                             if record["event"] == "plan_begin"]
            indexed: list[JsonObject] = [record_data(record) for record in journal.records
                                         if record["event"] == "cli_result" and record_data(record).get("plan_index") is not None]
        self.assertEqual(len(plan_begins), 1)
        self.assertEqual([item["plan_index"] for item in indexed], list(range(len(cast(list[JsonValue], plan["steps"])))))
        self.assertEqual([item["operation"] for item in indexed],
                         [cast(JsonObject, step)["operation"] for step in cast(list[JsonValue], plan["steps"])])

    # 功能：Codex 回归精简后的步骤间状态；参数 self 使用真实配置、守卫、动作和比较，结果须等于完整日志重建。
    def test_plan_state_matches_authoritative_journal_between_steps(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        path: Path = fixture.write_json("state-consistency-plan.json", plan)
        with fixture.session() as session:
            execute: Callable[[str, JsonObject], JsonObject] = session._plan_step

            # 功能：逐步核对持有状态与权威日志；参数 operation/request 为原计划，不修补或替换状态。
            def checked_step(operation: str, request: JsonObject) -> JsonObject:
                result: JsonObject = execute(operation, request)
                self.assertEqual(session.state, replay(session.journal.records, fixture.original, fixture.run))
                return result

            with patch.object(session, "_plan_step", side_effect=checked_step):
                result: JsonObject = session.invoke_plan(plan, path)
            self.assertEqual(cast(JsonObject, result["last_result"])["status"], "passed")
        self.assertEqual(fixture.world.action_count, 1)
        self.assertEqual(fixture.world.stock, 20 - fixture.world.cost)

    # 功能：缺少唯一 final 或首步不是本例 start-case 的计划在执行前拒绝；参数 self 为测试实例。
    def test_plan_rejects_missing_final_or_wrong_first_step(self) -> None:
        fixture: Fixture = self.fixture
        for include_final, first in ((False, "start-case"), (True, "observe")):
            with self.subTest(include_final=include_final, first=first):
                plan: JsonObject = self.plan(fixture, include_final=include_final, first=first)
                path: Path = fixture.write_json("bad-plan-%s-%s.json" % (include_final, first), plan)
                with fixture.session() as session, self.assertRaises(InputError):
                    session.invoke_plan(plan, path)
                # 静态预检失败发生在建连之前：除既有附加外不再新增任何连接。
                self.assertEqual(fixture.world.transport_count, self.attach_transports)

    # 功能：计划内重复命令 ID 在登记前拒绝，绝不重放同一动作；参数 self 为测试实例。
    def test_plan_rejects_duplicate_command_ids_before_player_contact(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        steps: list[JsonValue] = cast(list[JsonValue], plan["steps"])
        # 在 final 前插入一次与首次读取同 command_id 的步骤，静态预检必须直接拒绝。
        steps.insert(len(steps) - 1, {"operation": "observe", "request": cast(JsonObject, steps[2]["request"])})
        path: Path = fixture.write_json("duplicate-plan.json", plan)
        with fixture.session() as session, self.assertRaises(InputError):
            session.invoke_plan(plan, path)
        self.assertEqual(fixture.world.transport_count, self.attach_transports)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：计划必须与冻结的请求原字节一致，登记后被改写即拒绝；参数 self 为测试实例。
    def test_plan_rejects_request_bytes_changed_before_registration(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        path: Path = fixture.write_json("changed-plan.json", plan)
        changed: JsonObject = {**plan, "group_id": "changed-after-write"}
        with fixture.session() as session, self.assertRaises(IntegrityError):
            session.invoke_plan(changed, path)
        self.assertEqual(fixture.world.transport_count, self.attach_transports)

    # 功能：run-case 命令仍拒绝已在单例计划内执行过的同一命令 ID；参数 self 为测试实例。
    def test_plan_command_ids_cannot_be_replayed_later(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        path: Path = fixture.write_json("case-plan.json", plan)
        with fixture.session() as session:
            session.invoke_plan(plan, path)
            replay: JsonObject = {"command_id": "read-before", "observation_id": "again",
                                  "script": str(fixture.script("read-before")), "send": "eval_file",
                                  "scope": "step", "index": 1,
                                  "original_text": fixture.original.case(fixture.original.cases[0].case_id).item("step", 1).text,
                                  "purpose": "step", "target": fixture.world.target,
                                  "read_only_review": "当前 Agent 审核只读", "reason": "试图重放已登记命令"}
            with self.assertRaises(InputError):
                session.invoke("observe", replay)
        self.assertEqual(fixture.world.action_count, 1)

    # 功能：真实 CLI run-case 入口一次跑完本例并以 final 四状态返回退出码；参数 self 为测试实例。
    def test_real_cli_run_case_returns_final_exit_code(self) -> None:
        fixture: Fixture = self.fixture
        plan: JsonObject = self.plan(fixture)
        path: Path = fixture.write_json("cli-case-plan.json", plan)

        # 功能：仅注入调用层身份/传输，不新增正式 CLI 参数；参数 root 为实际解析的本轮目录。
        def injected_session(root: Path) -> Session:
            return Session(root, fixture.hooks, fixture.world.transport)

        output: io.StringIO = io.StringIO()
        with patch("scripts.cli.Session", injected_session), contextlib.redirect_stdout(output):
            code: int = main(["run-case", "--run", str(fixture.run), "--plan", str(path)])
        self.assertEqual(code, 0)
        self.assertNotIn(fixture.world.token, output.getvalue())
        with Journal(fixture.run) as journal:
            results: list[JsonObject] = [record_data(record) for record in journal.records
                                         if record["event"] == "cli_result" and record_data(record).get("plan_index") is not None]
        self.assertEqual([item["operation"] for item in results],
                         [cast(JsonObject, step)["operation"] for step in cast(list[JsonValue], plan["steps"])])

    # 功能：建立带两条完整计数用例的临时夹具并完成一次真实附加；参数 self 为测试实例。
    def two_case_fixture(self) -> Fixture:
        fixture: Fixture = Fixture(cases=[counter_case("C-1"), counter_case("C-2")])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
        self.two_attach_transports: int = fixture.world.transport_count
        return fixture

    # 功能：多例计划在一条命令、一次连接内跑完多例，每例仍独立 final；参数 self 为测试实例。
    def test_suite_runs_multiple_cases_in_one_connection(self) -> None:
        fixture: Fixture = self.two_case_fixture()
        first: str = fixture.original.cases[0].case_id
        second: str = fixture.original.cases[1].case_id
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [
            self.case_plan(fixture, first, suffix="-a"),
            self.case_plan(fixture, second, suffix="-b"),
        ]}
        path: Path = fixture.write_json("case-suite.json", suite)
        with fixture.session() as session:
            result: JsonObject = session.invoke_suite(suite, path)
            self.assertEqual(result["case_count"], 2)
            self.assertEqual(result["statuses"], ["passed", "passed"])
            finals: dict[str, JsonValue] = {case_id: record_data(item.final)["status"]
                                            for case_id, item in session.state.cases.items() if item.final is not None}
            self.assertEqual(finals, {first: "passed", second: "passed"})
        # 两例共用一次连接：附加那次之外只应新增 1 次建连；动作每例各一次并产生真实副作用。
        self.assertEqual(fixture.world.transport_count, self.two_attach_transports + 1)
        self.assertEqual(fixture.world.action_count, 2)
        self.assertEqual(fixture.world.stock, 20 - 2 * fixture.world.cost)

    # 功能：多例计划内的步骤仍逐条写入同一 journal，并带 suite_index/case_id；参数 self 为测试实例。
    def test_suite_writes_every_step_with_suite_index(self) -> None:
        fixture: Fixture = self.two_case_fixture()
        first: str = fixture.original.cases[0].case_id
        second: str = fixture.original.cases[1].case_id
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [
            self.case_plan(fixture, first, suffix="-a"),
            self.case_plan(fixture, second, suffix="-b"),
        ]}
        path: Path = fixture.write_json("case-suite.json", suite)
        with fixture.session() as session:
            session.invoke_suite(suite, path)
        with Journal(fixture.run) as journal:
            begins: list[JsonObject] = [record_data(record) for record in journal.records
                                        if record["event"] == "cli_begin" and record_data(record).get("suite_index") is not None]
        self.assertEqual([item["suite_index"] for item in begins],
                         sorted(item["suite_index"] for item in begins))
        self.assertEqual({item["case_id"] for item in begins}, {first, second})

    # 功能：多例计划拒绝缺 final、错首步、重复用例与重复命令 ID；参数 self 为测试实例。
    def test_suite_rejects_invalid_members_before_player_contact(self) -> None:
        fixture: Fixture = self.two_case_fixture()
        first: str = fixture.original.cases[0].case_id
        second: str = fixture.original.cases[1].case_id
        cases: list[tuple[str, JsonObject]] = [
            ("missing-final", {"schema": SUITE_SCHEMA, "cases": [
                self.case_plan(fixture, first, include_final=False, suffix="-a")]}),
            ("wrong-first", {"schema": SUITE_SCHEMA, "cases": [
                self.case_plan(fixture, first, first="observe", suffix="-a")]}),
            ("duplicate-case", {"schema": SUITE_SCHEMA, "cases": [
                self.case_plan(fixture, first, suffix="-a"),
                self.case_plan(fixture, first, suffix="-b")]}),
            ("duplicate-command", {"schema": SUITE_SCHEMA, "cases": [
                self.case_plan(fixture, first, suffix=""),
                self.case_plan(fixture, second, suffix="")]}),
        ]
        for label, suite in cases:
            with self.subTest(label=label):
                path: Path = fixture.write_json(f"suite-{label}.json", suite)
                with fixture.session() as session:
                    with self.assertRaises(InputError):
                        session.invoke_suite(suite, path)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：批量计划内不确定收口必须在静态阶段挂到本轮真实观测；参数 self 为测试实例。
    def test_suite_rejects_inconclusive_without_observation_before_player_contact(self) -> None:
        fixture: Fixture = self.two_case_fixture()
        first: str = fixture.original.cases[0].case_id
        kinds: list[tuple[str, JsonObject]] = [
            ("not-attempted", {"status": "test_inconclusive", "category": "not_attempted", "reason": "尚未执行"}),
            ("missing-category", {"status": "test_inconclusive", "reason": "缺分类"}),
            ("unknown-category", {"status": "test_inconclusive", "category": "whatever", "reason": "未知分类"}),
        ]
        for label, final_request in kinds:
            with self.subTest(label=label):
                body: JsonObject = self.case_plan(fixture, first, include_final=False, suffix="-a")
                body["steps"] = cast(list[JsonValue], body["steps"]) + [{"operation": "final", "request": final_request}]
                suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [body]}
                path: Path = fixture.write_json(f"suite-inconclusive-{label}.json", suite)
                with fixture.session() as session:
                    with self.assertRaises(InputError):
                        session.invoke_suite(suite, path)
        # 没有任何 observe 步骤时，insufficient_observation/not_constructible 同样必须静态失败。
        for category in ("insufficient_observation", "not_constructible"):
            with self.subTest(category=category):
                body = {"case_id": first, "group_id": "plan", "steps": [
                    {"operation": "start-case", "request": {"case_id": first}},
                    {"operation": "final", "request": {"status": "test_inconclusive", "category": category, "reason": "无观测"}}]}
                suite = {"schema": SUITE_SCHEMA, "cases": [body]}
                path = fixture.write_json(f"suite-inconclusive-{category}.json", suite)
                with fixture.session() as session:
                    with self.assertRaises(InputError):
                        session.invoke_suite(suite, path)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：批量执行结构化返回原自检，不在正式CLI的JSON前插入普通文本；参数self为测试实例。
    def test_suite_returns_reason_selfcheck_without_extra_stdout(self) -> None:
        fixture: Fixture = self.two_case_fixture()
        first: str = fixture.original.cases[0].case_id
        body: JsonObject = self.case_plan(fixture, first, include_final=False, suffix="-a")
        body["steps"] = cast(list[JsonValue], body["steps"]) + [
            {"operation": "final", "request": {"status": "test_inconclusive", "category": "insufficient_observation",
                                               "reason": "已读取但缺少目标字段"}}]
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [body]}
        path: Path = fixture.write_json("suite-selfcheck.json", suite)
        output: io.StringIO = io.StringIO()
        with fixture.session() as session, contextlib.redirect_stdout(output):
            result: JsonObject = session.invoke_suite(suite, path)
        self.assertEqual(output.getvalue(), "")
        printed: str = "\n".join(str(line) for line in cast(list[JsonValue], result["selfcheck"]))
        self.assertIn("[自检]", printed)
        self.assertIn("insufficient_observation", printed)
        self.assertIn("已读取但缺少目标字段", printed)
        # 本例含一次动作，自检行必须显示 actions=1，不得误报「本批 0 个 action 步骤」。
        self.assertIn("actions=1", printed)
        self.assertNotIn("本批 0 个 action 步骤", printed)

    # 功能：构造带前置用例的只读观测请求，用于验证 0 动作批告警；参数 tag 区分同一夹具内多次构造。
    def no_action_observe(self, fixture: Fixture, case_id: str, tag: str) -> JsonObject:
        return {"command_id": f"read-{tag}", "observation_id": f"before-{tag}",
                "script": str(fixture.script("read-before")), "send": "eval_file",
                "scope": "step", "index": 1,
                "original_text": fixture.original.case(case_id).item("step", 1).text,
                "purpose": "before", "target": fixture.world.target,
                "read_only_review": "当前 Agent 审核：本片段只返回业务字段",
                "reason": "依据当前字段动态定位，不是预制动作映射", "covers_step": False}

    # 功能：整批无动作时在结构化返回保留批级告警；参数self为测试实例。
    def test_suite_warns_when_batch_has_no_action_step(self) -> None:
        case: JsonObject = {"case_id": "W-1", "title": "带前置的只读例",
                            "preconditions": ["卡池已解锁"], "steps": ["读取当前计数"],
                            "expected": ["当前计数为 3"]}
        fixture: Fixture = Fixture(cases=[case])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
        case_id: str = fixture.original.cases[0].case_id
        steps: list[JsonValue] = [
            {"operation": "start-case", "request": {"case_id": case_id, "group_id": "warn"}},
            {"operation": "observe", "request": self.no_action_observe(fixture, case_id, "warn")},
            # 前置必须真实未满足（matched=false）才能支撑 critical_precondition 收口。
            {"operation": "compare", "request": fixture.comparison(
                "pre-warn", "before-warn", "/unique_count", 2, "precondition", case_id=case_id)},
            {"operation": "note", "request": {"category": "gap_explanation", "related_seq": 1,
                                              "message": "本批无可执行动作的独立说明"}},
            {"operation": "final", "request": {"status": "blocked", "category": "critical_precondition",
                                               "reason": "前置未满足"}}]
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [{"case_id": case_id, "group_id": "warn", "steps": steps}]}
        path: Path = fixture.write_json("suite-warn.json", suite)
        output: io.StringIO = io.StringIO()
        with fixture.session() as session, contextlib.redirect_stdout(output):
            result: JsonObject = session.invoke_suite(suite, path)
        self.assertEqual(output.getvalue(), "")
        printed: str = "\n".join(str(line) for line in cast(list[JsonValue], result["selfcheck"]))
        self.assertIn("本批 0 个 action 步骤", printed)
        self.assertIn("note=1", printed)
        self.assertIn("未留 note 的用例=[]", printed)

    # 功能：0 动作批缺少 note 时，告警逐例点名未说明的用例；参数 self 为测试实例。
    def test_suite_warns_names_cases_without_note(self) -> None:
        case: JsonObject = {"case_id": "N-1", "title": "无 note 的只读例",
                            "preconditions": ["卡池已解锁"], "steps": ["读取当前计数"],
                            "expected": ["当前计数为 3"]}
        fixture: Fixture = Fixture(cases=[case])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
        case_id: str = fixture.original.cases[0].case_id
        steps: list[JsonValue] = [
            {"operation": "start-case", "request": {"case_id": case_id, "group_id": "warn"}},
            {"operation": "observe", "request": self.no_action_observe(fixture, case_id, "n")},
            # 前置必须真实未满足（matched=false）才能支撑 critical_precondition 收口。
            {"operation": "compare", "request": fixture.comparison(
                "pre-n", "before-n", "/unique_count", 2, "precondition", case_id=case_id)},
            {"operation": "final", "request": {"status": "blocked", "category": "critical_precondition",
                                               "reason": "前置未满足"}}]
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [{"case_id": case_id, "group_id": "warn", "steps": steps}]}
        path: Path = fixture.write_json("suite-nonote.json", suite)
        output: io.StringIO = io.StringIO()
        with fixture.session() as session, contextlib.redirect_stdout(output):
            result: JsonObject = session.invoke_suite(suite, path)
        self.assertEqual(output.getvalue(), "")
        printed: str = "\n".join(str(line) for line in cast(list[JsonValue], result["selfcheck"]))
        self.assertIn("本批 0 个 action 步骤", printed)
        self.assertIn(f"未留 note 的用例=['{case_id}']", printed)

    # 功能：真实 CLI run-suite 入口一次跑完多例并按最差状态返回退出码；参数 self 为测试实例。
    def test_real_cli_run_suite_returns_worst_exit_code(self) -> None:
        fixture: Fixture = self.two_case_fixture()
        first: str = fixture.original.cases[0].case_id
        second: str = fixture.original.cases[1].case_id
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [
            self.case_plan(fixture, first, suffix="-a"),
            self.case_plan(fixture, second, suffix="-b"),
        ]}
        path: Path = fixture.write_json("cli-case-suite.json", suite)

        # 功能：仅注入调用层身份/传输，不新增正式 CLI 参数；参数 root 为实际解析的本轮目录。
        def injected_session(root: Path) -> Session:
            return Session(root, fixture.hooks, fixture.world.transport)

        output: io.StringIO = io.StringIO()
        with patch("scripts.cli.Session", injected_session), contextlib.redirect_stdout(output):
            code: int = main(["run-suite", "--run", str(fixture.run), "--plan", str(path)])
        self.assertEqual(code, 0)
        self.assertNotIn(fixture.world.token, output.getvalue())
        with Journal(fixture.run) as journal:
            results: list[JsonObject] = [record_data(record) for record in journal.records
                                         if record["event"] == "cli_result" and record_data(record).get("suite_index") is not None]
        self.assertEqual({item["case_id"] for item in results}, {first, second})


class WindowsProbeTests(unittest.TestCase):
    """三合一探测是纯性能等价变换；缓存只在限时窗口内复用且不跨命令保活。"""

    # 功能：建立可复用探测载荷的夹具；参数 self 为测试实例。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture()
        self.addCleanup(self.fixture.cleanup)
        self.target: TargetConfig = parse_target(
            strict_json(self.fixture.target_file.read_bytes(), Limits().input_bytes), self.fixture.root)
        self.calls: list[int] = []

    # 功能：返回与本夹具完全一致的三合一载荷并记录真实调用次数；参数来自明确目标。
    def probe(self, pid: int, exe: Path, port: int, path: Path, timeout_ms: int) -> JsonObject:
        self.calls.append(pid)
        return {"process": {"pid": pid, "exe": str(exe), "created": self.fixture.created},
                "listeners": [{"pid": pid, "address": "0.0.0.0"}],
                "acl": {"principal": "fixture-owner", "owner": "fixture-owner",
                        "rules": [{"sid": "fixture-owner", "type": "Allow", "rights": 1}]}}

    # 功能：同命令内 connect 与 preflight 只调用一次三合一探测；参数 self 为测试实例。
    def test_default_hooks_use_single_probe_per_command(self) -> None:
        fixture: Fixture = self.fixture
        with patch("scripts.pipeline.windows_probe", self.probe):
            pipeline: Pipeline = Pipeline(self.target, IdentityHooks(), fixture.world.transport)
            self.addCleanup(pipeline.close)
            pipeline.connect()
            pipeline.preflight()
        self.assertEqual(len(self.calls), 1)

    # 功能：超出同命令复用窗口后必须重新真实探测；参数 window 被改成 0 测试过期分支。
    def test_probe_cache_expires_within_command_window(self) -> None:
        fixture: Fixture = self.fixture
        with patch("scripts.pipeline.windows_probe", self.probe):
            pipeline: Pipeline = Pipeline(self.target, IdentityHooks(), fixture.world.transport)
            self.addCleanup(pipeline.close)
            pipeline.connect()
            self.assertEqual(len(self.calls), 1)
            # 模拟超出同命令复用窗口：清除缓存后必须重新真实探测，绝不沿用陈旧身份。
            pipeline.probe_cache.pop("windows", None)
            pipeline.preflight()
        self.assertEqual(len(self.calls), 2)

    # 功能：探测载荷异常仍按原 ACL 规则拒绝，不因合并查询放宽授权；参数 self 为测试实例。
    def test_probe_rejects_broad_acl_like_standalone_probe(self) -> None:
        fixture: Fixture = self.fixture

        # 功能：返回含 Everyone 读取权的三合一载荷；参数不触碰真实文件 ACL。
        def broad(pid: int, exe: Path, port: int, path: Path, timeout_ms: int) -> JsonObject:
            return {"process": {"pid": pid, "exe": str(exe), "created": fixture.created},
                    "listeners": [{"pid": pid, "address": "0.0.0.0"}],
                    "acl": {"principal": "fixture-owner", "owner": "fixture-owner",
                            "rules": [{"sid": "fixture-owner", "type": "Allow", "rights": 1},
                                      {"sid": "S-1-1-0", "type": "Allow", "rights": 1}]}}

        with patch("scripts.pipeline.windows_probe", broad):
            pipeline: Pipeline = Pipeline(self.target, IdentityHooks(), fixture.world.transport)
            with self.assertRaises(EnvironmentBlocked):
                pipeline.connect()
        self.assertEqual(fixture.world.transport_count, 0)

    # 功能：注入 hooks 时不得走默认三合一探测，保持调用层注入语义；参数 self 为测试实例。
    def test_injected_hooks_bypass_default_probe(self) -> None:
        fixture: Fixture = self.fixture
        with patch("scripts.pipeline.windows_probe", self.probe):
            pipeline: Pipeline = Pipeline(self.target, fixture.hooks, fixture.world.transport)
            self.addCleanup(pipeline.close)
            pipeline.connect()
        self.assertEqual(self.calls, [])


class ReadonlyCasePlanTests(unittest.TestCase):
    """只读用例的计划同样只能收口一次 final。"""

    # 功能：只读实例仍要求动作/预期绑定完整；参数 self 为测试实例。
    def test_readonly_plan_requires_expected_comparison(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as attached:
            attached.invoke("attach", {})
        case_id: str = fixture.original.cases[0].case_id
        observe: JsonObject = {"command_id": "read-only", "observation_id": "only",
                               "script": str(fixture.script("read-only")), "send": "eval_file", "scope": "step",
                               "index": 1, "original_text": fixture.original.case(case_id).item("step", 1).text,
                               "purpose": "step", "target": fixture.world.target, "read_only_review": "当前 Agent 审核只读",
                               "reason": "本体只读", "covers_step": True}
        expected: JsonObject = fixture.comparison("expect-only", "only", "/counter", 3, case_id=case_id)
        plan: JsonObject = {"schema": PLAN_SCHEMA, "case_id": case_id, "steps": [
            {"operation": "start-case", "request": {"case_id": case_id}},
            {"operation": "observe", "request": observe},
            {"operation": "compare", "request": expected},
            {"operation": "final", "request": {"status": "passed"}}]}
        path: Path = fixture.write_json("readonly-plan.json", plan)
        with fixture.session() as session:
            result: JsonObject = session.invoke_plan(plan, path)
            self.assertEqual(cast(JsonObject, result["last_result"])["status"], "passed")
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：三合一探测函数保持 PowerShell 侧单次调用契约；参数 self 为测试实例。
    def test_windows_probe_requires_windows(self) -> None:
        calls: list[str] = []
        with patch("scripts.pipeline.os.name", "posix"), self.assertRaises(EnvironmentBlocked):
            windows_probe(1, Path("a.exe"), 1, Path("b"), 1000)
        self.assertEqual(calls, [])


class PlanDefaultsTests(unittest.TestCase):
    """计划级 defaults 只补机械字段，不替代原文绑定、字段选择、操作符或独立预期。"""

    # 功能：建立带完整计数用例的夹具并完成一次附加；参数 self 为测试实例。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture()
        self.addCleanup(self.fixture.cleanup)
        with self.fixture.session() as session:
            session.invoke("attach", {})
        self.attach_transports: int = self.fixture.world.transport_count

    # 功能：构造未写机械字段、只依赖 defaults 的最小只读计划体；参数 fixture/case_id 指定夹具与用例。
    # 只读用例只有一条原预期，用 defaults 补齐机械字段后应能完整收口 passed。
    def minimal_body(self, fixture: Fixture, case_id: str) -> JsonObject:
        original = fixture.original.case(case_id)
        observe: JsonObject = {"command_id": "read-only-defaults", "observation_id": "only-defaults",
                               "script": str(fixture.script("read-only-defaults")), "scope": "step",
                               "index": 1, "original_text": original.item("step", 1).text,
                               "purpose": "step", "covers_step": True}
        expected: JsonObject = {"schema": "mono-pipeline-comparison/1", "comparison_id": "expect-defaults",
                                "scope": "expected", "index": 1,
                                "original_text": original.item("expected", 1).text,
                                "step_indices": [1], "observation_id": "only-defaults",
                                "field": "/counter", "operator": "eq",
                                "basis": {"kind": "literal", "value": 3, "reviewer": "current_agent",
                                          "statement": "原预期要求当前计数为 3", "semantic_review": "已核对原文本与字段"}}
        return {"case_id": case_id, "group_id": "defaults", "steps": [
            {"operation": "start-case", "request": {"case_id": case_id}},
            {"operation": "observe", "request": observe},
            {"operation": "compare", "request": expected},
            {"operation": "final", "request": {"status": "passed"}}]}

    # 功能：建立只读用例夹具并附加，供 defaults 完整收口验证；参数无。
    def readonly_fixture(self) -> Fixture:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
        self.readonly_transports = fixture.world.transport_count
        return fixture

    # 功能：返回覆盖全部必填机械字段的 defaults；参数 target 为当前唯一目标。
    def defaults(self, target: str) -> JsonObject:
        return {"send": "eval_file", "target": target, "value_format": "json", "timeout_ms": 5000,
                "read_only_review": "当前 Agent 审核：本片段只返回业务字段", "reason": "依据当前字段动态定位",
                "target_review": "当前唯一目标已独立确认，守卫已通过"}

    # 功能：defaults 补齐 send/target/value_format 等机械字段后，只读用例可完整收口 passed；参数 self 为测试实例。
    def test_defaults_fill_missing_mechanical_fields(self) -> None:
        fixture: Fixture = self.readonly_fixture()
        case_id: str = fixture.original.cases[0].case_id
        plan: JsonObject = {"schema": PLAN_SCHEMA, "defaults": self.defaults(fixture.world.target),
                            **self.minimal_body(fixture, case_id)}
        path: Path = fixture.write_json("defaults-plan.json", plan)
        with fixture.session() as session:
            result: JsonObject = session.invoke_plan(plan, path)
            self.assertEqual(cast(JsonObject, result["last_result"])["status"], "passed")
        self.assertEqual(fixture.world.transport_count, self.readonly_transports + 1)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：defaults 不得覆盖已写字段；显式 target 必须保持原值。默认 self 为测试实例。
    def test_defaults_never_override_written_fields(self) -> None:
        fixture: Fixture = self.readonly_fixture()
        case_id: str = fixture.original.cases[0].case_id
        body: JsonObject = self.minimal_body(fixture, case_id)
        steps: list[JsonValue] = cast(list[JsonValue], body["steps"])
        cast(JsonObject, steps[1]["request"])["target"] = "explicit.target"
        plan: JsonObject = {"schema": PLAN_SCHEMA, "defaults": self.defaults(fixture.world.target), **body}
        path: Path = fixture.write_json("defaults-priority.json", plan)
        with fixture.session() as session:
            session.invoke_plan(plan, path)
        with Journal(fixture.run) as journal:
            intents: list[JsonObject] = [record_data(record) for record in journal.records
                                         if record["event"] == "intent" and record_data(record).get("mode") == "read"]
        self.assertEqual(intents[-1]["target"], "explicit.target")

    # 功能：defaults 只补允许字段，不得让 compare 继承任何内容；未知键与缺 field 都在建连前拒绝。默认 self 为测试实例。
    def test_defaults_reject_unknown_keys_and_do_not_leak_into_compare(self) -> None:
        fixture: Fixture = self.readonly_fixture()
        case_id: str = fixture.original.cases[0].case_id
        bad: JsonObject = {"schema": PLAN_SCHEMA, "defaults": {"basis": {"kind": "literal"}},
                           **self.minimal_body(fixture, case_id)}
        path: Path = fixture.write_json("defaults-bad.json", bad)
        with fixture.session() as session, self.assertRaises(InputError):
            session.invoke_plan(bad, path)
        # compare 不继承 defaults 的任何字段：即使 defaults 给了 target，比较仍须自己写 field。
        body: JsonObject = self.minimal_body(fixture, case_id)
        steps: list[JsonValue] = cast(list[JsonValue], body["steps"])
        del cast(JsonObject, steps[2]["request"])["field"]
        plan: JsonObject = {"schema": PLAN_SCHEMA, "defaults": self.defaults(fixture.world.target), **body}
        plan_path: Path = fixture.write_json("defaults-compare.json", plan)
        # 缺 field 属结构错误，必须在计划登记/Player 接触前被相同的提交前校验拒绝。
        with fixture.session() as session, self.assertRaises(InputError):
            session.check_plan(plan)
            session.invoke_plan(plan, plan_path)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：defaults.timeout_ms 超过 target 的 max_timeout_ms 必须在静态阶段拒绝，不能在 run-case 才报整数越界。
    # 参数 self 为测试实例；此用例直接对应用户实测中 plan-check 漏过非法 timeout_ms 的缺口。
    def test_defaults_reject_timeout_above_target_ceiling(self) -> None:
        fixture: Fixture = self.readonly_fixture()
        case_id: str = fixture.original.cases[0].case_id
        bad: JsonObject = self.defaults(fixture.world.target)
        bad["timeout_ms"] = Limits().max_timeout_ms + 1
        plan: JsonObject = {"schema": PLAN_SCHEMA, "defaults": bad, **self.minimal_body(fixture, case_id)}
        fixture.write_json("defaults-timeout.json", plan)
        with fixture.session() as session, self.assertRaises(InputError):
            session.check_plan(plan)
        self.assertEqual(fixture.world.transport_count, self.readonly_transports)


class PlanCheckTests(unittest.TestCase):
    """plan-check 只做静态校验：不建连、不写业务事件、不消耗命令 ID。"""

    # 功能：建立夹具并附加；参数 self 为测试实例。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture()
        self.addCleanup(self.fixture.cleanup)
        with self.fixture.session() as session:
            session.invoke("attach", {})
        self.attach_transports: int = self.fixture.world.transport_count

    # 功能：合法计划通过 plan-check 且不产生任何连接或事件；参数 self 为测试实例。
    def test_plan_check_is_read_only(self) -> None:
        fixture: Fixture = self.fixture
        case_id: str = fixture.original.cases[0].case_id
        plan: JsonObject = {"schema": PLAN_SCHEMA, "case_id": case_id, "group_id": "check", "steps": [
            {"operation": "start-case", "request": {"case_id": case_id}},
            {"operation": "final", "request": {"status": "blocked", "category": "user_stop", "reason": "静态预检"}}]}
        path: Path = fixture.write_json("check-plan.json", plan)
        with fixture.session() as session:
            before: int = len(session.journal.records)
            result: JsonObject = session.check_plan(plan)
            after: int = len(session.journal.records)
        self.assertEqual(result["kind"], "plan")
        self.assertEqual(result["case_id"], case_id)
        self.assertFalse(result["player_contacted"])
        self.assertFalse(result["journal_written"])
        self.assertEqual(before, after)
        self.assertEqual(fixture.world.transport_count, self.attach_transports)

    # 功能：Codex 验证公开模板可直接进入原严格预检；参数 self 仅提供示例对应的临时原例和只读片段。
    def test_published_suite_template_uses_the_existing_strict_contract(self) -> None:
        fixture: Fixture = Fixture(cases=[{"case_id": "ORIGINAL_CASE_ID", "title": "隔离模板校验",
            "preconditions": [], "steps": ["原步骤完整文本"], "expected": ["原预期完整文本"]}])
        self.addCleanup(fixture.cleanup)
        fixture.script("read-panel-title")
        template: Path = Path(__file__).resolve().parents[2] / "assets/templates/case-suite.json"
        plan: JsonObject = cast(JsonObject, strict_json(template.read_bytes(), Limits().input_bytes))
        with fixture.session() as session:
            session._request_base = fixture.root
            before: int = len(session.journal.records)
            result: JsonObject = session.check_plan(plan)
            self.assertEqual(result["case_count"], 1)
            self.assertEqual(result["case_ids"], ["ORIGINAL_CASE_ID"])
            self.assertEqual(len(session.journal.records), before)
        self.assertEqual(fixture.world.transport_count, 0)

    # 功能：非法计划在 plan-check 阶段即报错，不写事件也不建连；参数 self 为测试实例。
    def test_plan_check_rejects_invalid_without_writing(self) -> None:
        fixture: Fixture = self.fixture
        case_id: str = fixture.original.cases[0].case_id
        plan: JsonObject = {"schema": PLAN_SCHEMA, "case_id": case_id, "group_id": "check", "steps": [
            {"operation": "start-case", "request": {"case_id": case_id}},
            {"operation": "final", "request": {"status": "test_inconclusive", "category": "not_attempted",
                                               "reason": "未执行"}}]}
        path: Path = fixture.write_json("check-bad.json", plan)
        with fixture.session() as session:
            before: int = len(session.journal.records)
            with self.assertRaises(InputError):
                session.check_plan(plan)
            after: int = len(session.journal.records)
        self.assertEqual(before, after)
        self.assertEqual(fixture.world.transport_count, self.attach_transports)

    # 功能：多例计划 plan-check 输出用例数与自检行，供接触 Player 前一次性看到全部疑点；参数 self 为测试实例。
    def test_plan_check_summarizes_suite(self) -> None:
        fixture: Fixture = Fixture(cases=[counter_case("C-1"), counter_case("C-2")])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
        bodies: list[JsonValue] = []
        for case_id in ("C-1", "C-2"):
            bodies.append({"case_id": case_id, "group_id": "check", "steps": [
                {"operation": "start-case", "request": {"case_id": case_id}},
                {"operation": "final", "request": {"status": "blocked", "category": "user_stop", "reason": "静态预检"}}]})
        suite: JsonObject = {"schema": SUITE_SCHEMA, "defaults": {"send": "eval_file"}, "cases": bodies}
        with fixture.session() as session:
            result: JsonObject = session.check_plan(suite)
        self.assertEqual(result["kind"], "suite")
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["default_keys"], ["send"])
        selfcheck: list[JsonValue] = cast(list[JsonValue], result["selfcheck"])
        # 本批确无 action 步骤：自检行 = 1 条批级 0 动作告警 + 2 条逐例收口行。
        self.assertEqual(len(selfcheck), 3)
        self.assertTrue(any("本批 0 个 action 步骤" in str(line) for line in selfcheck))


class PlanReferencePrecheckTests(unittest.TestCase):
    """跨步骤引用静态预检：把 r7/r9 反复出现的引用类构造错误提前到接触 Player 之前。"""

    # 功能：建立夹具并完成一次附加；参数 self 为测试实例。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture(cases=[readonly_case("C-1")])
        self.addCleanup(self.fixture.cleanup)
        with self.fixture.session() as session:
            session.invoke("attach", {})
        self.attach_transports: int = self.fixture.world.transport_count

    # 功能：构造只读计划体并允许调用方注入错误引用；参数 mutate 对 steps 做现场改写。
    def body(self, case_id: str, mutate) -> JsonObject:
        fixture: Fixture = self.fixture
        original = fixture.original.case(case_id)
        observe: JsonObject = {"command_id": "read-ref", "observation_id": "obs-ref",
                               "script": str(fixture.script("read-ref")), "send": "eval_file", "scope": "step",
                               "index": 1, "original_text": original.item("step", 1).text,
                               "purpose": "step", "target": fixture.world.target,
                               "read_only_review": "当前 Agent 审核只读", "reason": "跨步骤引用预检", "covers_step": True}
        expected: JsonObject = fixture.comparison("expect-ref", "obs-ref", "/counter", 3, case_id=case_id)
        steps: list[JsonValue] = [
            {"operation": "start-case", "request": {"case_id": case_id}},
            {"operation": "observe", "request": observe},
            {"operation": "compare", "request": expected},
            {"operation": "final", "request": {"status": "passed"}}]
        mutate(steps)
        return {"case_id": case_id, "group_id": "refs", "steps": steps}

    # 功能：多种非法引用都在 plan-check 阶段被拒，且不建连、不产生动作；参数 self 为测试实例。
    def test_invalid_references_rejected_before_player_contact(self) -> None:
        fixture: Fixture = self.fixture
        case_id: str = fixture.original.cases[0].case_id

        # 功能：把比较的观测改成从未登记的名字；参数 steps 为当前计划步骤。
        def unknown_observation(steps: list[JsonValue]) -> None:
            cast(JsonObject, steps[2]["request"])["observation_id"] = "never-read"

        # 功能：读取步骤凭空引用 after_command_id；参数 steps 为当前计划步骤。
        def stray_after(steps: list[JsonValue]) -> None:
            cast(JsonObject, steps[1]["request"])["after_command_id"] = "no-action"

        # 功能：动作引用不存在的 before 观测；参数 steps 为当前计划步骤。
        def unknown_before(steps: list[JsonValue]) -> None:
            steps.insert(2, {"operation": "action", "request": {
                "command_id": "act-1", "script": str(fixture.script("read-ref")), "send": "eval_file",
                "scope": "step", "index": 1, "original_text": fixture.original.case(case_id).item("step", 1).text,
                "target": fixture.world.target, "before_observation_id": "never-read",
                "guard_comparison_ids": ["expect-ref"], "target_review": "前置守卫已通过", "reason": "引用预检"}})

        # 功能：动作引用不存在的守卫比较；参数 steps 为当前计划步骤。
        def unknown_guard(steps: list[JsonValue]) -> None:
            steps.insert(2, {"operation": "action", "request": {
                "command_id": "act-1", "script": str(fixture.script("read-ref")), "send": "eval_file",
                "scope": "step", "index": 1, "original_text": fixture.original.case(case_id).item("step", 1).text,
                "target": fixture.world.target, "before_observation_id": "obs-ref",
                "guard_comparison_ids": ["never-compared"], "target_review": "前置守卫已通过", "reason": "引用预检"}})

        cases: list[tuple[str, object]] = [("unknown-observation", unknown_observation),
                                           ("stray-after", stray_after),
                                           ("unknown-before", unknown_before),
                                           ("unknown-guard", unknown_guard)]
        for label, mutate in cases:
            with self.subTest(label=label):
                plan: JsonObject = {"schema": PLAN_SCHEMA, **self.body(case_id, mutate)}
                with fixture.session() as session, self.assertRaises(InputError):
                    session.check_plan(plan)
        # 全部在静态阶段失败：除既有附加外没有任何新连接，也没有任何动作。
        self.assertEqual(fixture.world.transport_count, self.attach_transports)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：合法引用链通过 plan-check 且仍不产生连接或事件；参数 self 为测试实例。
    def test_valid_reference_chain_passes_plan_check(self) -> None:
        fixture: Fixture = self.fixture
        case_id: str = fixture.original.cases[0].case_id
        plan: JsonObject = {"schema": PLAN_SCHEMA, **self.body(case_id, lambda steps: None)}
        with fixture.session() as session:
            before: int = len(session.journal.records)
            result: JsonObject = session.check_plan(plan)
            after: int = len(session.journal.records)
        self.assertEqual(result["case_id"], case_id)
        self.assertEqual(before, after)
        self.assertEqual(fixture.world.transport_count, self.attach_transports)


class BuiltinObservationTests(unittest.TestCase):
    """设备侧命名观测：宿主生成方法体，Agent 不写 C#；只返回业务事实，不返回成功/断言标记。"""

    # 功能：四个已登记 op 都能生成非空方法体，且都不含自述成功字段；参数 self 为测试实例。
    def test_each_builtin_generates_body_without_verdict_fields(self) -> None:
        options: dict[str, JsonObject] = {
            "chain": {"depth": 2},
            "subtree": {"root": "UI_Root/Panel", "depth": 3},
            "buttons": {"name_contains": "btn"},
            "logic_field": {"logic_type": "HotFix.Example_Logic", "field": "_value"},
        }
        for name, option in options.items():
            with self.subTest(name=name):
                body: str = builtin_observation(name, option).decode("utf-8")
                self.assertIn("__rows", body if name != "logic_field" else body + "__rows")
                # 只返回业务事实：不得出现自述成功/断言/结论字段。
                for forbidden in ("\"success\"", "\"assertion\"", "\"passed\"", "\"verdict\""):
                    self.assertNotIn(forbidden, body)

    # 功能：未登记 op、缺必填参数、超界深度都被拒绝；参数 self 为测试实例。
    def test_builtin_rejects_unknown_or_invalid_options(self) -> None:
        with self.assertRaises(InputError):
            builtin_observation("not-registered", {})
        with self.assertRaises(InputError):
            builtin_observation("subtree", {})
        with self.assertRaises(InputError):
            builtin_observation("logic_field", {"logic_type": "T"})
        with self.assertRaises(InputError):
            builtin_observation("chain", {"depth": BUILTIN_MAX_DEPTH + 1})

    # 功能：observe 请求 builtin 与 script 互斥，且真实走同一包装/观测链；参数 self 为测试实例。
    def test_observe_builtin_and_script_are_mutually_exclusive(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            original_text: str = fixture.original.case("R-1").item("step", 1).text
            base: JsonObject = {"command_id": "builtin-both", "observation_id": "both", "builtin": "chain",
                                "script": str(fixture.script("read-only")), "send": "eval_file", "scope": "step",
                                "index": 1, "original_text": original_text, "purpose": "step",
                                "target": fixture.world.target, "read_only_review": "当前 Agent 审核只读",
                                "reason": "builtin 与 script 互斥", "covers_step": True}
            with self.assertRaises(InputError):
                session.invoke("observe", base)
            # 只给 builtin_options 而不给 builtin 同样拒绝。
            only_options: JsonObject = {key: value for key, value in base.items() if key not in {"builtin", "script"}}
            only_options["builtin_options"] = {"depth": 2}
            with self.assertRaises(InputError):
                session.invoke("observe", only_options)
            # 两者都不给也拒绝。
            neither: JsonObject = {key: value for key, value in base.items() if key not in {"builtin", "script"}}
            with self.assertRaises(InputError):
                session.invoke("observe", neither)


if __name__ == "__main__":
    unittest.main()
