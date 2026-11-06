"""创建日期：2026-11-03；创建人：Cyou。
功能：回归首例之前的独立共享链路、不可变来源、准备权限和业务统计隔离。
参数：生产 Session 与本包隔离夹具；不启动真实 Player，不以夹具替代实机验收。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import cast

from ..contracts import EnvironmentBlocked, InputError, JsonObject, JsonValue, canonical
from ..session import CHAIN_SCHEMA, CONTROL_CASE, Session
from .support import Fixture, readonly_case


class ChainContextTests(unittest.TestCase):
    """共享准备仍走同一发送/守卫/新帧门禁，只不加入原业务用例总数。"""

    # 功能：创建独立真实宿主夹具；参数 permissions 可精确移除准备许可，默认使用夹具既定授权。
    def fixture(self, permissions: list[JsonValue] | None = None) -> Fixture:
        fixture: Fixture = Fixture(cases=[readonly_case()], permissions=permissions)
        self.addCleanup(fixture.cleanup)
        return fixture

    # 功能：生成独立准备来源；参数 action=True 添加一次准备步骤及其精确预期，不复用业务原文。
    def source(self, action: bool = False) -> JsonObject:
        return {"schema": CHAIN_SCHEMA, "title": "隔离共享准备", "preconditions": [],
                "steps": ["读取全场景准备事实", "执行一次获准的准备操作"] if action else ["读取全场景准备事实"],
                "expected": ["准备后的当前计数为 4"] if action else ["准备时当前计数为 3"],
                "reviewer": "current_agent", "review": "仅夹具：明确准备操作与独立预期，不扩充原业务全集或运行权限"}

    # 功能：生成首次命名观测；参数 tag 保持命令唯一，covers 只用于独立来源中的真实读取步骤。
    def read(self, fixture: Fixture, tag: str, covers: bool = True) -> JsonObject:
        request: JsonObject = {"command_id": "chain-read-" + tag, "observation_id": "chain-obs-" + tag,
                              "builtin": "chain", "builtin_options": {"depth": 2, "max_nodes": 600},
                              "scope": "step" if covers else "discovery", "purpose": "step" if covers else "after",
                              "target": fixture.world.target, "read_only_review": "仅夹具：命名观测只读取事实",
                              "reason": "独立共享准备的新帧读取", "covers_step": covers}
        if covers:
            request.update({"index": 1, "original_text": "读取全场景准备事实"})
        return request

    # 功能：绑定共享来源而非业务用例的比较；参数 scope/index/field/value 均是明确独立语义。
    def comparison(self, session: Session, tag: str, observation: str, scope: str = "expected",
                   index: int = 1, field: str = "/counter", value: JsonValue = 3) -> JsonObject:
        original = session.original_case(CONTROL_CASE)
        return {"schema": "mono-pipeline-comparison/1", "comparison_id": "chain-cmp-" + tag,
                "scope": scope, "index": index, "original_text": original.item(scope, index).text,
                "step_indices": [index] if scope == "guard" else [2] if len(original.steps) > 1 else [1],
                "observation_id": observation, "field": field, "operator": "eq",
                "basis": {"kind": "literal", "value": value, "reviewer": "current_agent",
                          "statement": "隔离来源声明的精确准备事实", "semantic_review": "实际字段与本条准备条件语义一致"}}

    # 功能：构造一次共享准备动作；参数 before/guard 均必须属于当前目标和最新观测。
    def action(self, fixture: Fixture, before: str, guard: str) -> JsonObject:
        return {"command_id": "chain-action-one", "script": str(fixture.script("chain-action", "ACTION")),
                "scope": "step", "index": 2, "original_text": "执行一次获准的准备操作",
                "target": fixture.world.target, "before_observation_id": before, "guard_comparison_ids": [guard],
                "target_review": "仅夹具：唯一准备目标及独立通过守卫", "reason": "只发送一次获准准备操作"}

    # 功能：完整只读链路先行，业务总数仍为1；参数 self 核验真实发布、重建、close、audit、report。
    def test_shared_chain_before_first_case_does_not_inflate_business_counts(self) -> None:
        fixture: Fixture = self.fixture()
        directory: Path = fixture.root / "requests"
        with fixture.session() as session:
            session.invoke("attach", {})
            before: int = len(session.journal.records)
            session.check_request("chain-start", self.source())
            self.assertEqual(len(session.journal.records), before)
            session.submit("chain-start", self.source(), directory)
            session.submit("observe", self.read(fixture, "one"), directory)
            session.submit("compare", self.comparison(session, "one", "chain-obs-one"), directory)
            session.submit("chain-end", {}, directory)
            self.assertIsNone(session.state.current)
            self.assertTrue(session.invoke("status", {})["chain_ready"])
            self.assertEqual(session.invoke("status", {})["finals"], {})
        with fixture.session() as session:
            session.invoke("start-case", {"case_id": "R-1"})
            fixture.observe(session, covers=True)
            session.invoke("compare", fixture.comparison("original-cmp", "before", "/counter", 3, case_id="R-1"))
            session.invoke("final", {"status": "passed"})
            session.invoke("close", {})
            result: JsonObject = session.invoke("report", {})
            audit: JsonObject = cast(JsonObject, result["audit"])
            self.assertEqual(audit["input_count"], 1)
            self.assertEqual(audit["final_count"], 1)
            self.assertEqual(cast(JsonObject, audit["counts"])["passed"], 1)
            self.assertTrue(audit["chain_ready"])
            self.assertFalse(any(record["event"] == "case_final" and record["case_id"] == CONTROL_CASE for record in session.journal.records))

    # 功能：不允许先试探单节点、未证明就绪、提前开始业务或伪造 final；参数 self 无任何实际动作。
    def test_unverified_chain_cannot_be_closed_or_turned_into_original_case(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", self.source())
            with self.assertRaises(InputError):
                session.invoke("chain-end", {})
            with self.assertRaises(InputError):
                session.invoke("start-case", {"case_id": "R-1"})
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})
            request: JsonObject = {**self.read(fixture, "bad"), "builtin": "buttons"}
            with self.assertRaisesRegex(InputError, "builtin:chain"):
                session.invoke("observe", request)
            self.assertFalse(session.state.frozen)
            self.assertEqual(fixture.world.eval_count, 1)

    # 功能：共享来源登记后的改写仍永久冻结；参数 self 仅修改专用临时夹具来源。
    def test_registered_chain_source_stays_immutable(self) -> None:
        fixture: Fixture = self.fixture()
        source: JsonObject = self.source()
        path: Path = fixture.write_json("chain-source.json", source)
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", source, path)
            path.write_bytes(canonical({**source, "review": "登记后改写"}))
            self.assertTrue(session.invoke("status", {})["frozen"])

    # 功能：共享步骤必须使用 setup_action 许可，不能借 business_action；参数 self 无准备权限且不发送动作。
    def test_chain_action_requires_setup_permission(self) -> None:
        fixture: Fixture = self.fixture(["attach", "script_execute", "business_action"])
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", self.source(True))
            session.invoke("observe", self.read(fixture, "one"))
            guard: JsonObject = self.comparison(session, "guard", "chain-obs-one", "guard", 2, "/enabled", True)
            session.invoke("compare", guard)
            with self.assertRaises(EnvironmentBlocked):
                session.invoke("action", self.action(fixture, "chain-obs-one", "chain-cmp-guard"))
            self.assertEqual(fixture.world.action_count, 0)

    # 功能：共享动作仍拒绝旧守卫并要求动作后新帧；参数 self 不重放已发送命令。
    def test_chain_action_guards_and_fresh_frame_are_not_relaxed(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", self.source(True))
            session.invoke("observe", self.read(fixture, "one"))
            session.invoke("compare", self.comparison(session, "old", "chain-obs-one", "guard", 2, "/enabled", True))
            session.invoke("observe", self.read(fixture, "two"))
            with self.assertRaises(InputError):
                session.invoke("action", self.action(fixture, "chain-obs-two", "chain-cmp-old"))
            session.invoke("compare", self.comparison(session, "new", "chain-obs-two", "guard", 2, "/enabled", True))
            session.invoke("action", self.action(fixture, "chain-obs-two", "chain-cmp-new"))
            fixture.world.old_frame = True
            after: JsonObject = {**self.read(fixture, "after", False), "after_command_id": "chain-action-one"}
            observed: JsonObject = session.invoke("observe", after)
            self.assertFalse(cast(JsonObject, cast(list[JsonValue], observed["samples"])[-1])["observation_valid"])
            session.invoke("compare", self.comparison(session, "after", "chain-obs-after", value=4))
            with self.assertRaises(InputError):
                session.invoke("chain-end", {})
            with self.assertRaises(InputError):
                session.invoke("action", self.action(fixture, "chain-obs-two", "chain-cmp-new"))
            self.assertEqual(fixture.world.action_count, 1)

    # 功能：共享动作未知仍全轮冻结并禁止原用例；参数 self 保留真实部分副作用和0条业务 final。
    def test_unknown_chain_action_freezes_run_without_fake_business_final(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", self.source(True))
            session.invoke("observe", self.read(fixture, "one"))
            session.invoke("compare", self.comparison(session, "guard", "chain-obs-one", "guard", 2, "/enabled", True))
            fixture.world.fail_next = "runtime"
            session.invoke("action", self.action(fixture, "chain-obs-one", "chain-cmp-guard"))
            self.assertTrue(session.state.frozen)
            with self.assertRaises(InputError):
                session.invoke("start-case", {"case_id": "R-1"})
            with self.assertRaises(InputError):
                session.invoke("chain-end", {})
            session.invoke("close", {"interrupted_reason": "共享准备动作结果未知，禁止进入业务原例"})
            self.assertEqual(session.invoke("audit", {})["final_count"], 0)

    # 功能：已经开始业务或已经建立共享准备时拒绝重新开始；参数 self 不以新上下文绕过已登记状态。
    def test_chain_is_unique_and_cannot_start_after_business_case(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "R-1"})
            with self.assertRaises(InputError):
                session.invoke("chain-start", self.source())
        second: Fixture = self.fixture()
        with second.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", self.source())
            with self.assertRaises(InputError):
                session.invoke("chain-start", self.source())

    # 功能：共享比较不得用业务原文伪装准备来源；参数 self 验证登记前拒绝并不冻结。
    def test_chain_binding_cannot_borrow_original_business_text(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", self.source())
            session.invoke("observe", self.read(fixture, "one"))
            request: JsonObject = self.comparison(session, "bad", "chain-obs-one")
            request["original_text"] = fixture.original.case("R-1").item("expected", 1).text
            with self.assertRaises(InputError):
                session.invoke("compare", request)
            self.assertFalse(session.state.frozen)
