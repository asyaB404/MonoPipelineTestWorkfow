"""Created: 2026-11-09; Author: Codex.
Purpose: cross-domain navigation, prerequisite and plan-review regression tests.
Parameters: original-format plans, temporary files and in-memory UI only; no real account or Player.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import patch

from ..cli import main
from ..contracts import EnvironmentBlocked, InputError, JsonObject, JsonValue
from ..session import PLAN_SCHEMA, SUITE_SCHEMA
from .support import Fixture, World, counter_case, readonly_case
from . import test_chain_context as chain_fixtures
from .test_preflight_completion import readonly_body


@dataclass
class PanelWorld(World):
    """Two distinct required controls, with alias and wrong-result counterexamples."""

    paths: tuple[str, str] = ("Inventory/Open", "Inventory/Notice/Continue")
    alias_instance: bool = False
    wrong_result: bool = False

    # Return raw final fields only; the independent expected quantity is in the original case.
    def business(self) -> JsonObject:
        return {"ready": self.action_count >= 2, "quantity": 8 if self.wrong_result else 7}

    # Feed the production wrapper an isolated button row for its current UI phase.
    def host(self, code: str, value: JsonValue) -> JsonObject:
        if '{"op", "buttons"}' in code and "// mono-pipeline-builtin-click/1" not in code:
            phase: int = min(self.action_count, 1)
            identity: int = 0 if self.alias_instance else phase
            value = {"op": "buttons", "count": 1, "truncated": False, "nodes": [{
                "path": self.paths[phase], "active": True, "enabled": True, "interactable": True,
                "effective_interactable": True, "button_count": 1, "node_instance_id": -30 - identity,
                "instance_id": -40 - identity, "component_type": "GameButton",
                "click_method": "InvokeOnClickListener"}]}
        return super().host(code, value)


class FlowPatternTests(unittest.TestCase):
    """Real Session parsing, execution and audit; no feature-specific production branch."""

    # Build a complete original case; names/paths select inventory or settings independently.
    def fixture(self, name: str = "Inventory", paths: tuple[str, str] | None = None) -> Fixture:
        source: JsonObject = {"case_id": "FLOW-1", "title": name + " required interaction",
            "preconditions": [], "steps": ["Open the panel and complete its required visible interaction.",
                "Read the completed panel and its quantity."],
            "expected": ["The panel is ready.", "The quantity is exactly 7."]}
        fixture: Fixture = Fixture(cases=[source], limits={"poll_budget_ms": 1000, "poll_interval_ms": 1})
        self.addCleanup(fixture.cleanup)
        fixture.world = PanelWorld(paths=paths or (name + "/Open", name + "/Notice/Continue"))
        fixture.world.heartbeat_writer = fixture.refresh_descriptor
        return fixture

    # Generate the existing plan schema; two required clicks belong to the same original step.
    def plan(self, fixture: Fixture) -> JsonObject:
        source = fixture.original.case("FLOW-1")
        world: PanelWorld = cast(PanelWorld, fixture.world)
        steps: list[JsonValue] = [{"operation": "start-case", "request": {"case_id": "FLOW-1"}}]
        for phase, path in enumerate(world.paths):
            before: str = "buttons-" + str(phase)
            read: JsonObject = {"command_id": "read-" + before, "observation_id": before,
                "builtin": "buttons", "builtin_options": {"root": path}, "scope": "step", "index": 1,
                "original_text": source.steps[0].text, "purpose": "before",
                "target": world.target, "read_only_review": "Read only the current synthetic control.",
                "reason": "Read the next required interaction."}
            if phase:
                read["after_command_id"] = "click-0"
            steps.extend([{"operation": "observe", "request": read},
                {"operation": "compare", "request": fixture.comparison(
                    "guard-" + str(phase), before, "/nodes/0/effective_interactable", True,
                    "guard", case_id="FLOW-1")},
                {"operation": "action", "request": {
                    "command_id": "click-" + str(phase), "builtin": "click_button",
                    "builtin_options": {"path": path}, "scope": "step", "index": 1,
                    "original_text": source.steps[0].text, "target": world.target,
                    "before_observation_id": before, "guard_comparison_ids": ["guard-" + str(phase)],
                    "target_review": "Distinct currently visible required control, never a transaction retry.",
                    "reason": "Perform this required UI interaction once."}}])
        steps.extend([{"operation": "observe", "request": {
            "command_id": "read-result", "observation_id": "result",
            "script": str(fixture.script("result")), "scope": "step", "index": 2,
            "original_text": source.steps[1].text, "purpose": "after", "covers_step": True,
            "after_command_id": "click-1", "target": world.target,
            "read_only_review": "Read raw panel status and quantity only.",
            "reason": "Required interaction is complete; now wait for the final phase.",
            "poll": {"field": "/ready", "operator": "eq", "value": True,
                "stable_samples": 2, "require_match": True}}},
            {"operation": "compare", "request": fixture.comparison(
                "expected-ready", "result", "/ready", True, case_id="FLOW-1")},
            {"operation": "compare", "request": fixture.comparison(
                "expected-quantity", "result", "/quantity", 7, index=2, case_id="FLOW-1")},
            {"operation": "final", "request": {"status": "passed"}}])
        return {"schema": PLAN_SCHEMA, "case_id": "FLOW-1", "steps": steps}

    # Two non-gacha domains use the same parser, connection, action rules and independent audit.
    def test_distinct_required_controls_in_one_step_finish_without_cleanup(self) -> None:
        for name in ("Inventory", "Settings"):
            with self.subTest(domain=name):
                fixture: Fixture = self.fixture(name)
                plan: JsonObject = self.plan(fixture)
                path: Path = fixture.write_json("flow.json", plan)
                with fixture.session() as session:
                    session.check_plan(plan)
                    session.invoke("attach", {})
                initial_connections: int = fixture.world.transport_count
                with fixture.session() as session:
                    result: JsonObject = session.invoke_plan(plan, path)
                    self.assertEqual(cast(JsonObject, result["last_result"])["status"], "passed")
                    self.assertEqual(fixture.world.transport_count - initial_connections, 1)
                    self.assertEqual(fixture.world.action_count, 2)
                    self.assertEqual(session.state.cases["FLOW-1"].actions, ["click-0", "click-1"])
                    session.invoke("close", {})
                    self.assertEqual(cast(JsonObject, session.invoke("audit", {})["counts"])["passed"], 1)
                self.assertTrue(cast(PanelWorld, fixture.world).business()["ready"])

    # Same path is still a duplicate original action even if its command ID is different.
    def test_same_path_repeat_is_rejected_before_plan_registration(self) -> None:
        fixture: Fixture = self.fixture(paths=("Panel/Submit", "Panel/Submit"))
        with fixture.session() as session:
            count: int = len(session.journal.records)
            with self.assertRaisesRegex(InputError, "重复"):
                session.check_plan(self.plan(fixture))
            self.assertEqual(len(session.journal.records), count)
        self.assertEqual(fixture.world.transport_count, 0)

    # Mixing an opaque script into a multi-click original step remains rejected at preflight.
    def test_multiclick_step_cannot_mix_handwritten_scripts(self) -> None:
        fixture: Fixture = self.fixture()
        plan: JsonObject = self.plan(fixture)
        second: JsonObject = cast(JsonObject, cast(list[JsonObject], plan["steps"])[6]["request"])
        del second["builtin"]
        del second["builtin_options"]
        second["script"] = str(fixture.script("opaque-action", "ACTION"))
        with fixture.session() as session:
            with self.assertRaisesRegex(InputError, "重复"):
                session.check_plan(plan)
        self.assertEqual(fixture.world.transport_count, 0)

    # A final-condition timeout still stops subsequent actions; it is not a modal-dismiss bypass.
    def test_pending_completion_does_not_allow_following_modal_actions(self) -> None:
        fixture: Fixture = self.fixture()
        plan: JsonObject = self.plan(fixture)
        steps: list[JsonObject] = cast(list[JsonObject], plan["steps"])
        early_wait: JsonObject = copy.deepcopy(cast(JsonObject, steps[7]["request"]))
        early_wait.update({"command_id": "early-wait", "observation_id": "early",
            "index": 1, "original_text": fixture.original.case("FLOW-1").steps[0].text,
            "covers_step": False, "after_command_id": "click-0"})
        steps.insert(4, {"operation": "observe", "request": early_wait})
        with fixture.session() as session:
            session.invoke("attach", {})
            result: JsonObject = session.invoke_plan(plan, fixture.write_json("pending.json", plan))
            self.assertEqual(cast(JsonObject, result["last_result"])["status"], "test_inconclusive")
            self.assertEqual(fixture.world.action_count, 1)
            self.assertNotIn("click-1", session.state.commands)
            session.invoke("close", {})
            session.invoke("audit", {})

    # A completed shared chain does not prohibit a legitimate per-case prerequisite setup.
    def test_case_can_prepare_its_own_precondition_after_shared_chain_closed(self) -> None:
        source: JsonObject = counter_case()
        source["preconditions"] = ["Inventory must cover the independent configured cost."]
        fixture: Fixture = Fixture(cases=[source])
        self.addCleanup(fixture.cleanup)
        chain: chain_fixtures.ChainContextTests = chain_fixtures.ChainContextTests()
        fixture.world.stock = 0
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("chain-start", chain.source())
            session.invoke("observe", chain.read(fixture, "initial"))
            session.invoke("compare", chain.comparison(session, "initial", "chain-obs-initial"))
            session.invoke("chain-end", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.baseline(session)
            fixture.observe(session)
            self.assertFalse(session.invoke("compare", fixture.comparison(
                "unmet", "before", "/stock", 4, "precondition", operator="ge"))["matched"])
            guards: list[JsonValue] = fixture.guards(session)
            with self.assertRaises(EnvironmentBlocked):
                fixture.action(session, guards)
            fixture.action(session, guards, "prepare", scope="precondition")
            fixture.observe(session, "read-prepared", "prepared", "prepare", scope="precondition")
            session.invoke("compare", fixture.comparison("met", "prepared", "/stock", 4, "precondition", operator="ge"))
            fixture.action(session, fixture.guards(session, "prepared", "prepared"), "execute", "prepared")
            fixture.observe(session, "read-completed", "completed", "execute")
            fixture.assert_changes(session, "completed", "prepared")
            self.assertEqual(session.invoke("final", {"status": "passed"})["status"], "passed")
            session.invoke("close", {})
            session.invoke("audit", {})
        self.assertEqual((fixture.world.setup_count, fixture.world.action_count), (1, 1))

    # Different path labels must not disguise the same Unity component or node instance.
    def test_alias_instance_does_not_send_the_second_click(self) -> None:
        fixture: Fixture = self.fixture()
        cast(PanelWorld, fixture.world).alias_instance = True
        plan: JsonObject = self.plan(fixture)
        with fixture.session() as session:
            session.invoke("attach", {})
            with self.assertRaisesRegex(InputError, "重复|实例"):
                session.invoke_plan(plan, fixture.write_json("alias.json", plan))
            self.assertEqual(fixture.world.action_count, 1)
            self.assertNotIn("click-1", session.state.commands)

    # Successfully completing navigation must not turn an incorrect business value into passed.
    def test_completed_navigation_with_wrong_value_remains_failed(self) -> None:
        fixture: Fixture = self.fixture()
        cast(PanelWorld, fixture.world).wrong_result = True
        plan: JsonObject = self.plan(fixture)
        with fixture.session() as session:
            session.invoke("attach", {})
            result: JsonObject = session.invoke_plan(plan, fixture.write_json("wrong-result.json", plan))
            self.assertEqual(cast(JsonObject, result["last_result"])["status"], "failed")
            session.invoke("close", {})
            self.assertEqual(cast(JsonObject, session.invoke("audit", {})["counts"])["failed"], 1)

    # Runtime single-step calls enforce the same path rule, not only plan-check.
    def test_single_step_cannot_replay_a_button_with_a_new_id(self) -> None:
        fixture: Fixture = self.fixture(paths=("Panel/Submit", "Panel/Submit"))
        steps: list[JsonObject] = cast(list[JsonObject], self.plan(fixture)["steps"])
        with fixture.session() as session:
            session.invoke("attach", {})
            for step in steps[:6]:
                session.invoke(str(step["operation"]), cast(JsonObject, step["request"]))
            with self.assertRaisesRegex(InputError, "重复"):
                session.invoke(str(steps[6]["operation"]), cast(JsonObject, steps[6]["request"]))
            self.assertEqual(fixture.world.action_count, 1)

    # Plan-review facts are visible before any network, source registration or verdict decision.
    def test_plan_review_exposes_terminal_paths_and_exact_precondition_binding(self) -> None:
        source: JsonObject = readonly_case()
        source["preconditions"] = ["The free allowance equals one."]
        fixture: Fixture = Fixture(cases=[source])
        self.addCleanup(fixture.cleanup)
        body: JsonObject = readonly_body(fixture, "R-1", "review")
        steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
        binding: JsonObject = cast(JsonObject, steps[2]["request"])
        binding["field"] = "/ticket_balance"
        cast(JsonObject, binding["basis"])["value"] = 1
        body["steps"] = steps[:3] + [{"operation": "final", "request": {
            "status": "blocked", "category": "critical_precondition", "reason": "Original condition not met."}}]
        with fixture.session() as session:
            count: int = len(session.journal.records)
            result: JsonObject = session.check_plan({"schema": PLAN_SCHEMA, **body})
            summary: JsonObject = cast(JsonObject, result["planning_summary"])
            self.assertEqual(summary["terminal_only_case_ids"], ["R-1"])
            self.assertEqual(summary["status_counts"], {"blocked": 1})
            review: JsonObject = cast(list[JsonObject], summary["cases"])[0]
            actual_binding: JsonObject = cast(list[JsonObject], review["precondition_bindings"])[0]
            self.assertEqual(actual_binding["original_text"], "The free allowance equals one.")
            self.assertEqual(actual_binding["field"], "/ticket_balance")
            self.assertEqual(actual_binding["value"], 1)
            self.assertEqual(len(session.journal.records), count)
        self.assertEqual(fixture.world.transport_count, 0)

    # Keep one JSON-compatible structured return, not narrative text before the CLI JSON.
    def test_suite_selfcheck_does_not_print_extra_stdout(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [readonly_body(fixture, "R-1", "quiet")]}
        stream: io.StringIO = io.StringIO()
        with fixture.session() as session, contextlib.redirect_stdout(stream):
            session.invoke("attach", {})
            result: JsonObject = session.invoke_suite(suite, fixture.write_json("quiet.json", suite))
            self.assertEqual(result["statuses"], ["passed"])
            self.assertIn("selfcheck", result)
        self.assertEqual(stream.getvalue(), "")

    # Parse the entire real CLI output as one JSON document, including a zero-action warning.
    def test_real_cli_suite_emits_one_json_document(self) -> None:
        fixture: Fixture = Fixture(cases=[readonly_case()])
        self.addCleanup(fixture.cleanup)
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [readonly_body(fixture, "R-1", "json")]}
        path: Path = fixture.write_json("single-json.json", suite)
        with fixture.session() as session:
            session.invoke("attach", {})
        stream: io.StringIO = io.StringIO()
        with patch("scripts.cli.Session", lambda root: fixture.session()), contextlib.redirect_stdout(stream):
            code: int = main(["--compact", "run-suite", "--run", str(fixture.run), "--plan", str(path)])
        document: JsonObject = json.loads(stream.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(document["operation"], "run-suite")
        self.assertTrue(cast(JsonObject, document["result"])["selfcheck"])
