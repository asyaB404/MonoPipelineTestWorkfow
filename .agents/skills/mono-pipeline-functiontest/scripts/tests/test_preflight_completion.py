"""Created: 2026-11-05; Author: Codex.
Purpose: reproduce preflight gaps and verify explicit business-completion waits.
Parameters: isolated temporary cases, configuration and in-memory Player fixture only.
"""
from __future__ import annotations

import unittest
import contextlib
import io
import json
import time
from pathlib import Path
from typing import cast
from unittest.mock import patch

from ..cli import main
from ..contracts import InputError, JsonObject, JsonValue, Limits, strict_json
from ..evidence import record_data
from ..inputs import OriginalCase
from ..session import PLAN_SCHEMA, SUITE_SCHEMA, Session, check_request_contract
from . import test_case_plan as plan_fixtures
from .support import Fixture, counter_case, readonly_case


# Build an existing-format read-only case; parameters identify the real fixture source and expected value.
def readonly_body(fixture: Fixture, case_id: str, tag: str, value: int = 3) -> JsonObject:
    source: OriginalCase = fixture.original.case(case_id)
    read: JsonObject = {"command_id": "read-" + tag, "observation_id": "obs-" + tag,
        "script": str(fixture.script("read-" + tag)), "scope": "step", "index": source.steps[0].index,
        "original_text": source.steps[0].text, "purpose": "step", "covers_step": True,
        "target": fixture.world.target, "read_only_review": "Isolated fixture: read business facts only.",
        "reason": "Read the original fixture step."}
    expected: JsonObject = fixture.comparison("expected-" + tag, "obs-" + tag, "/counter", value, case_id=case_id)
    steps: list[JsonValue] = [{"operation": "start-case", "request": {"case_id": case_id}},
        {"operation": "observe", "request": read}]
    if source.preconditions:
        steps.append({"operation": "compare", "request": fixture.comparison(
            "pre-" + tag, "obs-" + tag, "/enabled", True, "precondition",
            index=source.preconditions[0].index, case_id=case_id)})
    steps.extend([{"operation": "compare", "request": expected},
                  {"operation": "final", "request": {"status": "passed"}}])
    return {"case_id": case_id, "steps": steps}


# Reuse the existing fully guarded action fixture; parameters keep command identifiers unique per case.
def action_body(fixture: Fixture, case_id: str, suffix: str = "") -> JsonObject:
    builder: plan_fixtures.CasePlanTests = plan_fixtures.CasePlanTests("test_plan_runs_whole_case_in_one_connection")
    return builder.case_plan(fixture, case_id, suffix=suffix)


class PreflightCompletionTests(unittest.TestCase):
    """Static rejection must happen before source registration or Player contact."""

    # Create a private fixture; parameters are complete original cases and optional polling limits.
    def fixture(self, cases: list[JsonObject], limits: JsonObject | None = None) -> Fixture:
        fixture: Fixture = Fixture(cases=cases, limits=limits)
        self.addCleanup(fixture.cleanup)
        return fixture

    # Verify all three missing-index categories without relying on future runtime matching.
    def test_passed_declarations_reject_each_coverage_gap_without_side_effects(self) -> None:
        for missing in ("steps", "expected", "preconditions"):
            with self.subTest(missing=missing):
                source: JsonObject = readonly_case()
                source["preconditions"] = ["The test resource is available."]
                fixture: Fixture = self.fixture([source])
                body: JsonObject = readonly_body(fixture, "R-1", "missing")
                steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
                if missing == "steps":
                    cast(JsonObject, steps[1]["request"])["covers_step"] = False
                else:
                    scope: str = "expected" if missing == "expected" else "precondition"
                    body["steps"] = [step for step in steps if not (
                        step["operation"] == "compare" and cast(JsonObject, step["request"]).get("scope") == scope)]
                plan: JsonObject = {"schema": PLAN_SCHEMA, **body}
                path: Path = fixture.write_json("incomplete.json", plan)
                with fixture.session() as session:
                    before: int = len(session.journal.records)
                    with self.assertRaisesRegex(InputError, "覆盖声明"):
                        session.check_plan(plan)
                    with self.assertRaises(InputError):
                        session.invoke_plan(plan, path)
                    self.assertEqual(len(session.journal.records), before)
                self.assertEqual(fixture.world.transport_count, 0)

    # An action covers its actual original step without requiring redundant read coverage.
    def test_action_coverage_and_configuration_baseline_pass_preflight(self) -> None:
        fixture: Fixture = self.fixture([counter_case()])
        body: JsonObject = action_body(fixture, "C-1")
        for step in cast(list[JsonObject], body["steps"]):
            if step["operation"] == "observe":
                cast(JsonObject, step["request"])["covers_step"] = False
        with fixture.session() as session:
            result: JsonObject = session.check_plan({"schema": PLAN_SCHEMA, **body})
            self.assertEqual(result["kind"], "plan")
        self.assertEqual(fixture.world.transport_count, 0)

    # The discovery template must be a real request, with tutorial-only keys kept outside JSON.
    def test_observe_template_is_accepted_by_the_existing_request_contract(self) -> None:
        root: Path = Path(__file__).resolve().parents[2]
        template: Path = root / "assets/templates/observe.json"
        request: JsonObject = cast(JsonObject, strict_json(template.read_bytes(), Limits().input_bytes))
        check_request_contract("observe", request, None, Limits(), template.parent)

    # A batch can reuse a baseline registered by an earlier case without registering it twice.
    def test_batch_reuses_an_earlier_independent_baseline(self) -> None:
        fixture: Fixture = self.fixture([counter_case("C-1"), counter_case("C-2")])
        first: JsonObject = action_body(fixture, "C-1", "-a")
        second: JsonObject = action_body(fixture, "C-2", "-b")
        second["steps"] = [step for step in cast(list[JsonObject], second["steps"]) if step["operation"] != "baseline"]
        for step in cast(list[JsonObject], second["steps"]):
            request: JsonObject = cast(JsonObject, step["request"])
            if step["operation"] == "compare" and isinstance(request.get("basis"), dict) and cast(JsonObject, request["basis"]).get("kind") == "baseline":
                cast(JsonObject, request["basis"])["reference_id"] = "configuration-a"
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [first, second]}
        path: Path = fixture.write_json("shared-baseline.json", suite)
        with fixture.session() as session:
            session.check_plan(suite)
            session.invoke("attach", {})
            self.assertEqual(session.invoke_suite(suite, path)["statuses"], ["passed", "passed"])
            session.invoke("close", {})
            session.invoke("audit", {})

    # A known unmet precondition is sufficient for blocked; original action steps remain unexecuted.
    def test_blocked_needs_no_fake_step_coverage(self) -> None:
        source: JsonObject = readonly_case()
        source["preconditions"] = ["The test resource is available."]
        fixture: Fixture = self.fixture([source])
        body: JsonObject = readonly_body(fixture, "R-1", "blocked")
        steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
        read: JsonObject = cast(JsonObject, steps[1]["request"])
        read.update({"scope": "precondition", "purpose": "precondition", "covers_step": False,
                     "original_text": fixture.original.case("R-1").preconditions[0].text})
        body["steps"] = steps[:3] + [{"operation": "final", "request": {
            "status": "blocked", "category": "critical_precondition", "reason": "The independently read resource is unavailable."}}]
        plan: JsonObject = {"schema": PLAN_SCHEMA, **body}
        path: Path = fixture.write_json("blocked.json", plan)
        fixture.world.missing_target = True
        with fixture.session() as session:
            session.check_plan(plan)
            session.invoke("attach", {})
            result: JsonObject = session.invoke_plan(plan, path)
            final: JsonObject = cast(JsonObject, result["last_result"])
            self.assertEqual(final["status"], "blocked")
            self.assertEqual(cast(JsonObject, final["coverage"])["missing_steps"], [1])
            session.invoke("close", {})
            session.invoke("audit", {})
        self.assertEqual(fixture.world.action_count, 0)

    # Reading alone cannot satisfy the existing not_constructible runtime action prerequisite.
    def test_not_constructible_without_attempt_is_rejected_statically(self) -> None:
        fixture: Fixture = self.fixture([readonly_case()])
        body: JsonObject = readonly_body(fixture, "R-1", "attempt")
        cast(JsonObject, cast(list[JsonObject], body["steps"])[-1])["request"] = {
            "status": "test_inconclusive", "category": "not_constructible", "reason": "No construction attempt exists."}
        with fixture.session() as session:
            before: int = len(session.journal.records)
            with self.assertRaisesRegex(InputError, "构造尝试"):
                session.check_plan({"schema": PLAN_SCHEMA, **body})
            self.assertEqual(len(session.journal.records), before)
        self.assertEqual(fixture.world.transport_count, 0)

    # Other statically impossible final declarations must also fail before any Player operation.
    def test_impossible_failure_and_block_declarations_are_rejected_statically(self) -> None:
        declarations: list[JsonObject] = [
            {"status": "failed"},
            {"status": "blocked", "category": "critical_precondition", "reason": "No precondition comparison."},
            {"status": "blocked", "category": "environment", "reason": "No environment record."},
            {"status": "blocked", "category": "permission", "required_permission": "script_execute", "reason": "The permission is already granted."},
        ]
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                fixture: Fixture = self.fixture([readonly_case()])
                body: JsonObject = readonly_body(fixture, "R-1", "impossible")
                body["steps"] = [step for step in cast(list[JsonObject], body["steps"]) if step["operation"] != "compare"]
                cast(list[JsonObject], body["steps"])[-1]["request"] = declaration
                with fixture.session() as session:
                    before: int = len(session.journal.records)
                    with self.assertRaises(InputError):
                        session.check_plan({"schema": PLAN_SCHEMA, **body})
                    self.assertEqual(len(session.journal.records), before)
                self.assertEqual(fixture.world.transport_count, 0)

    # Opposite literals on the same observed original precondition are a construction error.
    def test_conflicting_preconditions_reject_only_the_same_observation(self) -> None:
        source: JsonObject = readonly_case()
        source["preconditions"] = ["The test resource is available."]
        fixture: Fixture = self.fixture([source])
        body: JsonObject = readonly_body(fixture, "R-1", "conflict")
        steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
        opposite: JsonObject = fixture.comparison("opposite", "obs-conflict", "/enabled", False,
                                                  "precondition", case_id="R-1")
        steps.insert(3, {"operation": "compare", "request": opposite})
        with fixture.session() as session:
            with self.assertRaisesRegex(InputError, "互斥"):
                session.check_plan({"schema": PLAN_SCHEMA, **body})
            second_read: JsonObject = {**cast(JsonObject, steps[1]["request"]),
                "command_id": "later-read", "observation_id": "later-observation"}
            steps.insert(3, {"operation": "observe", "request": second_read})
            opposite["observation_id"] = "later-observation"
            session.check_plan({"schema": PLAN_SCHEMA, **body})
        self.assertEqual(fixture.world.transport_count, 0)

    # Float signed zero is equal at runtime; construction checks must preserve that typed equality.
    def test_precondition_literal_equivalence_matches_runtime_scalar_equality(self) -> None:
        source: JsonObject = readonly_case()
        source["preconditions"] = ["The floating-point position equals zero."]
        fixture: Fixture = self.fixture([source])
        body: JsonObject = readonly_body(fixture, "R-1", "zero")
        steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
        first: JsonObject = cast(JsonObject, steps[2]["request"])
        first["field"] = "/position"
        cast(JsonObject, first["basis"])["value"] = 0.0
        second: JsonObject = fixture.comparison("negative-zero", "obs-zero", "/position", -0.0,
                                                "precondition", case_id="R-1")
        steps.insert(3, {"operation": "compare", "request": second})
        with fixture.session() as session:
            session.check_plan({"schema": PLAN_SCHEMA, **body})
            cast(JsonObject, second["basis"])["value"] = False
            with self.assertRaisesRegex(InputError, "互斥"):
                session.check_plan({"schema": PLAN_SCHEMA, **body})
        self.assertEqual(fixture.world.transport_count, 0)

    # Configuration references and raw hashes must be checked before batch execution.
    def test_missing_or_mismatched_baselines_are_rejected_before_registration(self) -> None:
        for mistake in ("missing", "sha256"):
            with self.subTest(mistake=mistake):
                fixture: Fixture = self.fixture([counter_case()])
                body: JsonObject = action_body(fixture, "C-1")
                steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
                if mistake == "missing":
                    body["steps"] = [step for step in steps if step["operation"] != "baseline"]
                else:
                    cast(JsonObject, steps[1]["request"])["sha256"] = "0" * 64
                with fixture.session() as session:
                    before: int = len(session.journal.records)
                    with self.assertRaisesRegex(InputError, "基线"):
                        session.check_plan({"schema": PLAN_SCHEMA, **body})
                    self.assertEqual(len(session.journal.records), before)
                self.assertEqual(fixture.world.transport_count, 0)

    # Current and finished cases must be reported and rejected before another start-case is registered.
    def test_status_and_preflight_separate_active_finished_and_unstarted_cases(self) -> None:
        fixture: Fixture = self.fixture([readonly_case("R-1"), readonly_case("R-2")])
        one: JsonObject = {"schema": PLAN_SCHEMA, **readonly_body(fixture, "R-1", "one")}
        two: JsonObject = {"schema": PLAN_SCHEMA, **readonly_body(fixture, "R-2", "two")}
        with fixture.session() as session:
            session.invoke("start-case", {"case_id": "R-1"})
            self.assertEqual(session.invoke("status", {})["remaining_case_ids"], ["R-2"])
            before: int = len(session.journal.records)
            for plan in (one, two):
                with self.assertRaises(InputError):
                    session.check_plan(plan)
            self.assertEqual(len(session.journal.records), before)
            session.invoke("final", {"status": "blocked", "category": "user_stop", "reason": "Isolated stop fixture."})
            with self.assertRaises(InputError):
                session.check_plan(one)
            session.check_plan(two)
            self.assertEqual(session.invoke("status", {})["remaining_case_ids"], ["R-2"])
            session.invoke("close", {"interrupted_reason": "The isolated second case was not started."})
            with self.assertRaises(InputError):
                session.check_plan(two)


class RequiredCompletionTests(unittest.TestCase):
    """Explicit completion waits must not create premature product failures or replay actions."""

    # Create a bounded polling fixture; cases are synthetic and never contact a real Player.
    def fixture(self, cases: list[JsonObject] | None = None, budget_ms: int = 1000) -> Fixture:
        fixture: Fixture = Fixture(cases=cases, limits={"poll_budget_ms": budget_ms, "poll_interval_ms": 1, "poll_samples": 3})
        self.addCleanup(fixture.cleanup)
        return fixture

    # Prepare one real fixture action with existing guards and an independent baseline.
    def prepare_action(self, fixture: Fixture, session: Session) -> None:
        session.invoke("attach", {})
        session.invoke("start-case", {"case_id": "C-1"})
        fixture.baseline(session)
        fixture.observe(session)
        fixture.action(session, fixture.guards(session))

    # Timeout must skip later assertions/actions, close this case honestly, and keep independent reads usable.
    def test_required_wait_skips_remaining_case_actions_and_keeps_batch_auditable(self) -> None:
        first: JsonObject = counter_case()
        first["steps"] = ["触发一次计数增加", "执行后续测试操作"]
        second: JsonObject = readonly_case("R-2")
        second["expected"] = ["当前计数为4"]
        fixture: Fixture = self.fixture([first, second])
        body: JsonObject = action_body(fixture, "C-1")
        steps: list[JsonObject] = cast(list[JsonObject], body["steps"])
        after: JsonObject = cast(JsonObject, steps[6]["request"])
        after["poll"] = {"field": "/counter", "operator": "eq", "value": 99, "require_match": True}
        guard: JsonObject = fixture.comparison("cleanup-guard", "after", "/enabled", True, "guard", index=2)
        guard["step_indices"] = [2]
        cleanup: JsonObject = {**cast(JsonObject, steps[5]["request"]), "command_id": "cleanup-action",
            "index": 2, "original_text": fixture.original.case("C-1").item("step", 2).text,
            "before_observation_id": "after", "guard_comparison_ids": ["cleanup-guard"]}
        steps[-1:-1] = [{"operation": "compare", "request": guard}, {"operation": "action", "request": cleanup}]
        suite: JsonObject = {"schema": SUITE_SCHEMA, "cases": [body, readonly_body(fixture, "R-2", "second", 4)]}
        path: Path = fixture.write_json("required-suite.json", suite)
        with fixture.session() as session:
            session.invoke("attach", {})
            result: JsonObject = session.invoke_suite(suite, path)
            self.assertEqual(result["statuses"], ["test_inconclusive", "passed"])
            self.assertFalse(session.state.frozen)
            self.assertEqual(session.state.cases["C-1"].failed_comparisons, [])
            self.assertFalse(any(record["event"] == "comparison" and record["case_id"] == "C-1"
                and record_data(record)["binding"]["scope"] == "expected" for record in session.journal.records))
            session.invoke("close", {})
            session.invoke("report", {})
        self.assertEqual(fixture.world.action_count, 1)
        self.assertEqual(fixture.world.stock, 16)

    # A later confirmed read clears the pending condition; earlier comparisons stay inconclusive in audit.
    def test_unready_comparison_is_inconclusive_and_later_completion_can_be_verified(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            self.prepare_action(fixture, session)
            result: JsonObject = fixture.observe(session, "pending", "pending-obs", "action-one",
                poll={"field": "/counter", "operator": "eq", "value": 99, "require_match": True})
            self.assertFalse(result["poll_matched"])
            early: JsonObject = session.invoke("compare", fixture.comparison("early", "pending-obs", "/counter", 999))
            self.assertEqual(early["status"], "test_inconclusive")
            self.assertEqual(session.state.cases["C-1"].failed_comparisons, [])
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})
            fixture.observe(session, "ready", "ready-obs", "action-one",
                poll={"field": "/counter", "operator": "eq", "value": 4, "require_match": True})
            fixture.assert_changes(session, "ready-obs", "before")
            self.assertEqual(session.invoke("final", {"status": "passed"})["status"], "passed")
            session.invoke("close", {})
            session.invoke("report", {})
        self.assertEqual(fixture.world.action_count, 1)

    # Confirmation must still satisfy the condition, even after the sampling loop briefly matched.
    def test_required_wait_rechecks_the_final_confirmation_frame(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            self.prepare_action(fixture, session)
            ready: JsonObject = fixture.world.business()
            changed: JsonObject = {**ready, "counter": 5}
            with patch.object(fixture.world, "business", side_effect=[ready, changed]):
                result: JsonObject = fixture.observe(session, "changed", "changed-obs", "action-one",
                    poll={"field": "/counter", "operator": "eq", "value": 4, "require_match": True})
            self.assertFalse(result["poll_matched"])
            self.assertEqual(session.invoke("final", {"status": "test_inconclusive",
                "category": "insufficient_observation", "reason": "Completion changed before confirmation."})["status"], "test_inconclusive")
            session.invoke("close", {})
            session.invoke("report", {})

    # Existing early-stop polling remains compatible when require_match is absent.
    def test_legacy_optional_polling_keeps_independent_comparison_semantics(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            self.prepare_action(fixture, session)
            result: JsonObject = fixture.observe(session, "optional", "optional-obs", "action-one",
                poll={"field": "/counter", "operator": "eq", "value": 99})
            self.assertFalse(result["poll_matched"])
            fixture.assert_changes(session, "optional-obs", "before")
            self.assertEqual(session.invoke("final", {"status": "passed"})["status"], "passed")
            session.invoke("close", {})
            session.invoke("report", {})

    # Once completion is confirmed, a real wrong resource delta must remain a product failure.
    def test_completed_wrong_cost_still_latches_failed(self) -> None:
        fixture: Fixture = self.fixture()
        fixture.world.charge_multiplier = 2
        with fixture.session() as session:
            self.prepare_action(fixture, session)
            result: JsonObject = fixture.observe(session, "finished", "finished-obs", "action-one",
                poll={"field": "/counter", "operator": "eq", "value": 4, "require_match": True})
            self.assertTrue(result["poll_matched"])
            fixture.assert_changes(session, "finished-obs", "before")
            self.assertEqual(session.invoke("final", {"status": "passed"})["status"], "failed")
            session.invoke("close", {})
            session.invoke("report", {})

    # Codex: real evidence I/O can exhaust a short fixture budget; never infer completion from one confirmation.
    def test_evidence_io_deadline_stays_inconclusive_and_generous_budget_keeps_counterexample(self) -> None:
        for budget, matched in ((80, False), (1000, True)):
            with self.subTest(budget_ms=budget):
                fixture: Fixture = self.fixture(budget_ms=budget)
                fixture.world.charge_multiplier = 2
                with fixture.session() as session:
                    self.prepare_action(fixture, session)
                    original_store = session.journal.store

                    # Delay only isolated wrapper evidence; no real Player or production timeout is changed.
                    def slow_store(kind: str, content: bytes, source: JsonObject,
                                   case_id: str | None = None, extension: str = ".json") -> JsonObject:
                        if kind == "script_wrapper":
                            time.sleep(0.12)
                        return original_store(kind, content, source, case_id, extension)

                    with patch.object(session.journal, "store", side_effect=slow_store):
                        result: JsonObject = fixture.observe(session, "io-wait", "io-ready", "action-one",
                            poll={"field": "/counter", "operator": "eq", "value": 4, "require_match": True})
                    self.assertIs(result["poll_matched"], matched)
                    self.assertFalse(result["frozen"])
                    fixture.assert_changes(session, "io-ready", "before")
                    final: JsonObject = session._plan_step("final", {"status": "passed"})
                    self.assertEqual(final["status"], "failed" if matched else "test_inconclusive")
                    session.invoke("close", {})
                    session.invoke("audit", {})
                self.assertEqual(fixture.world.action_count, 1)

    # A transport failure remains globally frozen even when the read has a completion condition.
    def test_required_wait_does_not_downgrade_unknown_execution(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            self.prepare_action(fixture, session)
            fixture.world.fail_next = "disconnect"
            result: JsonObject = fixture.observe(session, "unknown", "unknown-obs", "action-one",
                poll={"field": "/counter", "operator": "eq", "value": 4, "require_match": True})
            self.assertTrue(result["frozen"])
            self.assertTrue(session.state.frozen)
            with self.assertRaises(InputError):
                session.invoke("final", {"status": "passed"})
            session.invoke("final", {"status": "test_inconclusive", "category": "insufficient_observation",
                "reason": "The fixture transport result is unknown; no replay."})
            session.invoke("close", {})
            session.invoke("audit", {})
        self.assertEqual(fixture.world.action_count, 1)

    # Completion mode requires a boolean flag and a real prior action association.
    def test_completion_mode_rejects_invalid_flag_or_missing_action_binding(self) -> None:
        fixture: Fixture = self.fixture()
        body: JsonObject = action_body(fixture, "C-1")
        after: JsonObject = cast(JsonObject, cast(list[JsonObject], body["steps"])[6]["request"])
        for invalid in (1, "true", None):
            with self.subTest(invalid=invalid), fixture.session() as session:
                after["poll"] = {"field": "/counter", "operator": "eq", "value": 4, "require_match": invalid}
                with self.assertRaisesRegex(InputError, "布尔值"):
                    session.check_plan({"schema": PLAN_SCHEMA, **body})
        after["poll"] = {"field": "/counter", "operator": "eq", "value": 4, "require_match": True}
        after.pop("after_command_id")
        with fixture.session() as session, self.assertRaisesRegex(InputError, "after_command_id"):
            session.check_plan({"schema": PLAN_SCHEMA, **body})
        self.assertEqual(fixture.world.transport_count, 0)

    # The real CLI must distinguish a successful read from an unconfirmed business completion.
    def test_cli_returns_inconclusive_without_freezing_for_an_unconfirmed_completion(self) -> None:
        fixture: Fixture = self.fixture()
        with fixture.session() as session:
            self.prepare_action(fixture, session)
        request: JsonObject = {"command_id": "cli-wait", "observation_id": "cli-wait-observation",
            "script": str(fixture.script("cli-wait")), "scope": "step", "index": 1,
            "original_text": fixture.original.case("C-1").item("step", 1).text,
            "purpose": "after", "after_command_id": "action-one", "target": fixture.world.target,
            "read_only_review": "Isolated fixture: read facts only.", "reason": "Wait for the fixture completion fact.",
            "poll": {"field": "/counter", "operator": "eq", "value": 99, "require_match": True}}
        path: Path = fixture.write_json("cli-wait.json", request)
        output: io.StringIO = io.StringIO()

        # Open the production session with only the fixture's existing identity and transport dependencies.
        def fixture_session(root: Path) -> Session:
            return Session(root, fixture.hooks, fixture.world.transport)

        with patch("scripts.cli.Session", side_effect=fixture_session), contextlib.redirect_stdout(output):
            code: int = main(["observe", "--run", str(fixture.run), "--request", str(path)])
        result: JsonObject = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual(code, 4)
        self.assertTrue(result["ok"])
        self.assertFalse(cast(JsonObject, result["result"])["poll_matched"])
        self.assertFalse(cast(JsonObject, result["result"])["frozen"])


if __name__ == "__main__":
    unittest.main()
