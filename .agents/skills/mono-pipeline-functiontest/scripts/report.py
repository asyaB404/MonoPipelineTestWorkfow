"""创建日期：2026-10-26；作者：Cyou。
更新日期：2026-11-09；更新人：Codex；回算同一步不同内置按钮的身份与不重放约束。
功能：包内独立回算审计、writer 计时校验与唯一固定 Markdown 报告。
参数：本轮 journal 及明确父上下文；统计只来自本轮唯一 final，不联网/操作 Player。
"""
from __future__ import annotations

import html
from dataclasses import replace
from pathlib import Path
from typing import cast
from urllib.parse import quote

from .contracts import (
    SCHEMA, VERDICTS, HostError, InputError, IntegrityError, JsonObject, JsonValue,
    SecretGuard, canonical, compare_values, digest, field_value, integer, keys_only,
    object_value, strict_json, text,
)
from .evidence import (
    JOURNAL_NAME, REPORT_NAME, Journal, local_cli_call, new_id, record_data, record_int, write_new,
)
from .inputs import OriginalCase, case_index, verify_workflow
from .pipeline import EvalReceipt, observed_value, wrap_script, wrapper_format
from .session import CONTROL_CASE, CaseState, Session, builtin_button_click, builtin_button_row, case_coverage

INTENT_FIELDS = frozenset({"command_id", "mode", "scope", "index", "original_text", "target", "value_format", "purpose",
                           "observation_id", "after_command_id", "covers_step", "reason", "read_only_review",
                           "before_observation_id", "guard_comparison_ids", "request_origin", "script_original", "script_wrapper",
                           "source_sha256", "sent_sha256", "send", "timeout_ms", "correction_of", "correction_reason"})
RESULT_FIELDS = frozenset({"command_id", "receipt", "frame", "observation_id", "observation_ref", "observation_valid",
                           "observation_error", "not_executed", "effective_timeout_ms"})
COMPARISON_FIELDS = frozenset({"comparison_id", "binding", "request_origin", "actual_observation_id", "actual_field", "actual",
                               "before_value", "expected_value", "computed_value", "valid", "matched", "status", "diagnostic",
                               "semantic_equivalence", "assertion_strength", "evidence"})
FINAL_FIELDS = frozenset({"status", "requested_status", "reason", "category", "required_permission", "coverage", "comparison_ids", "observation_ids",
                          "action_command_ids", "group_id", "start_seq", "start_hash", "request_origin", "evidence"})
EVENT_FIELDS: dict[str, frozenset[str]] = {
    "run_init": frozenset({"case_input", "case_index", "sources", "target", "parent", "workflow", "report_owner", "case_ids", "mode", "upload"}),
    # 单例/多例计划在一条 CLI 内串行多步，plan_index/suite_index/case_id 只标注归属，不新增任何业务语义。
    # default_keys 只记录本次实际使用过的计划级共享字段名，用于审计可见性，不含任何业务判定。
    "plan_begin": frozenset({"case_id", "group_id", "step_count", "plan_sha256", "plan_path", "default_keys"}),
    "suite_begin": frozenset({"case_count", "case_ids", "step_count", "plan_sha256", "plan_path", "default_keys"}),
    "cli_begin": frozenset({"operation", "call_id", "plan_index", "suite_index", "case_id", "step_sha256"}),
    "cli_result": frozenset({"operation", "call_id", "ok", "result", "error_kind", "message", "plan_index", "suite_index", "case_id"}),
    "request_registered": frozenset({"operation", "call_id", "request_origin"}),
    "connection_checked": frozenset({"identity"}),
    "environment_blocked": frozenset({"reason", "stage", "error_kind"}),
    "session_attached": frozenset({"probe_command_id", "frame", "mono", "development", "business_ready"}),
    "session_frozen": frozenset({"reason", "phase", "command_id", "execution_terminated"}),
    # 用例级冻结：仅由脚本自身缺陷触发，只影响该例，本轮其余用例继续。
    "case_frozen": frozenset({"reason", "phase", "command_id", "execution_terminated"}),
    "source_integrity_interrupted": frozenset({"reason", "snapshot_only", "formal_report_eligible", "execution_terminated", "evidence"}),
    "case_started": frozenset({"title", "group_id"}),
    "chain_started": frozenset({"source", "source_kind", "group_id", "request_origin", "evidence"}),
    "chain_closed": frozenset({"ready", "coverage", "comparison_ids", "observation_ids", "action_command_ids",
                               "start_seq", "start_hash", "request_origin", "evidence"}),
    "intent": INTENT_FIELDS,
    "command_result": RESULT_FIELDS,
    "comparison": COMPARISON_FIELDS,
    "case_final": FINAL_FIELDS,
    "baseline_registered": frozenset({"reference_id", "kind", "review", "origin", "request_origin"}),
    "attribution": frozenset({"case_id", "classification", "issue_id", "description", "root_cause", "verification", "comparison_ids", "observation_ids",
                              "request_origin", "product_status_unchanged", "fix_executed", "evidence"}),
    "reference_recorded": frozenset({"case_id", "description", "target", "observation_ids", "comparison_ids", "source_lookup", "build_guid", "request_origin", "scope", "evidence"}),
    "artifact_collected": frozenset({"observation_id", "field", "evidence", "request_origin", "privacy_review"}),
    "poll_started": frozenset({"poll_id", "budget_ms", "condition"}),
    "poll_closed": frozenset({"poll_id", "start_seq", "sample_count", "matched", "last_observation_id", "diagnostic"}),
    "case_note": frozenset({"case_id", "category", "message", "related_seq", "related_hash", "request_origin"}),
    "audit_complete": frozenset({"audit", "head_before"}),
    "session_closed": frozenset({"complete", "missing_case_ids", "unfinished_case", "interrupted_reason", "frozen", "audit_seq", "audit_hash", "process_cleanup"}),
    "timing_closed": frozenset({"scope", "start_seq", "start_hash", "duration_ns"}),
    "report_intent": frozenset({"path", "audit", "audited_head"}),
    "report_rendered": frozenset({"evidence", "intent_seq", "intent_hash"}),
}


# 功能：核验事件主内容与其独占证据完全一致；参数 key 默认指向本例主证据。
def _snapshot_matches(journal: Journal, data: JsonObject, key: str = "evidence") -> None:
    reference: JsonObject = object_value(data.get(key), "event evidence")
    content: JsonValue = strict_json(journal.verify_ref(reference), journal.limits.evidence_bytes, journal.limits, bom=True)
    expected: JsonObject = {name: value for name, value in data.items() if name != key}
    if canonical(content) != canonical(expected):
        raise IntegrityError("事件内容与实时私有证据不一致")


# 功能：独立核验用户和发送包装摘要/身份及动作门禁证据；参数 record 为单次 intent。
def _audit_intent(session: Session, record: JsonObject) -> None:
    if session.target is None or session.cases is None:
        raise IntegrityError("审计缺少原输入和目标")
    data: JsonObject = record_data(record)
    keys_only(data, INTENT_FIELDS, "intent", INTENT_FIELDS)
    original_ref: JsonObject = object_value(data["script_original"], "original script ref")
    wrapper_ref: JsonObject = object_value(data["script_wrapper"], "wrapper script ref")
    evidence_case: str = str(record["case_id"]) if record["case_id"] is not None else "@session"
    raw: bytes = session.journal.verify_ref(original_ref, evidence_case)
    wrapper: bytes = session.journal.verify_ref(wrapper_ref, evidence_case)
    actual: bytes = wrap_script(raw, session.journal.run_id, str(record["case_id"] or ""), str(data["command_id"]),
                                session.target.limits, SecretGuard(), wrapper_format(wrapper))
    if data["source_sha256"] != digest(raw) or data["sent_sha256"] != digest(wrapper) or actual != wrapper:
        raise IntegrityError("用户原字节/实际发送包装或身份摘要不一致")
    if not {"attach", "script_execute"} <= session.target.permissions:
        raise IntegrityError("所有脚本（含只读/断言）必须存在明确执行许可")
    integer(data["timeout_ms"], "intent timeout", 1, session.target.limits.max_timeout_ms)
    if data["send"] not in {"eval", "eval_file"} or data["mode"] not in {"read", "action", "probe"}:
        raise IntegrityError("intent 发送或执行类型非法")
    if record["case_id"] is None:
        if data["mode"] != "probe":
            raise IntegrityError("只有宿主基础探针可不属于业务例")
        return
    case_id: str = str(record["case_id"])
    original: OriginalCase = session.original_case(case_id)
    if data["scope"] != "discovery" and data["original_text"] != original.item(str(data["scope"]), integer(data["index"], "original index")).text:
        raise IntegrityError("执行原索引/原文被修改")
    if data["mode"] == "read":
        text(data["read_only_review"], "read_only_review", trim=False)
        if data["purpose"] == "logs" and "log_read" not in session.target.permissions:
            raise IntegrityError("日志读取缺少 log_read 许可")
        return
    permission: str = "business_action" if data["scope"] == "step" and case_id != CONTROL_CASE else "setup_action"
    if permission not in session.target.permissions:
        raise IntegrityError("动作缺少明确业务/前置许可")
    item: CaseState = session.state.cases[case_id]
    if item.completion_pending(record_int(record, "seq")) is not None:
        raise IntegrityError("业务完成条件未确认期间出现了新的动作")
    before: JsonObject | None = item.observations.get(str(data["before_observation_id"]))
    if before is None or before.get("valid") is not True or before.get("target") != data["target"] or integer(before.get("record_seq"), "before seq") >= record_int(record, "seq"):
        raise IntegrityError("动作没有同例、发送前、当前目标的真实 before")
    earlier_observations: list[JsonObject] = [value for value in item.observations.values() if value.get("target") == data["target"] and integer(value.get("record_seq"), "observation seq") < record_int(record, "seq")]
    if earlier_observations and earlier_observations[-1]["observation_id"] != data["before_observation_id"]:
        raise IntegrityError("动作使用被更新观察覆盖的旧 before/守卫")
    source: JsonObject = object_value(original_ref["source"], "action source")
    if source.get("kind") == "builtin_action":
        before_source: JsonObject = object_value(object_value(record_data(session.state.commands[str(before["command_id"])])["script_original"], "button original")["source"], "button source")
        if source.get("path") != "builtin:click_button" or before_source.get("kind") != "builtin_observation" or before_source.get("path") != "builtin:buttons":
            raise IntegrityError("内置点击缺少本例宿主生成的按钮来源")
        try:
            expected_action: bytes = builtin_button_click(object_value(source.get("options"), "click options"), before)
        except InputError:
            raise IntegrityError("内置点击绑定的按钮身份或状态不完整") from None
        if raw != expected_action:
            raise IntegrityError("内置点击源码不等于原 before 派生的单次调用")
    if data["scope"] == "step":
        for command_id in item.actions:
            prior_record: JsonObject = session.state.commands[command_id]
            prior: JsonObject = record_data(prior_record)
            if record_int(prior_record, "seq") >= record_int(record, "seq") or prior["scope"] != "step" or prior["index"] != data["index"]:
                continue
            prior_source: JsonObject = object_value(object_value(prior["script_original"], "prior script")["source"], "prior source")
            if any(value.get("kind") != "builtin_action" or value.get("path") != "builtin:click_button" for value in (source, prior_source)):
                raise IntegrityError("同一原步骤重复动作不能混用手写脚本")
            current_path: str = text(object_value(source["options"], "click options")["path"], "click path")
            prior_path: str = text(object_value(prior_source["options"], "prior options")["path"], "prior path")
            try:
                current_row: JsonObject = builtin_button_row(current_path, before)
                prior_row: JsonObject = builtin_button_row(prior_path, item.observations[str(prior["before_observation_id"])])
            except InputError:
                raise IntegrityError("同一步多次交互缺少原按钮身份") from None
            if current_path == prior_path or current_row["instance_id"] == prior_row["instance_id"] or current_row["node_instance_id"] == prior_row["node_instance_id"]:
                raise IntegrityError("同一原步骤重复调用相同按钮路径或实例")
    guards: JsonValue = data["guard_comparison_ids"]
    if not isinstance(guards, list) or not guards:
        raise IntegrityError("动作没有独立业务守卫")
    for raw_id in guards:
        guard: JsonObject | None = item.comparisons.get(str(raw_id))
        if guard is None or guard.get("valid") is not True or guard.get("matched") is not True:
            raise IntegrityError("动作守卫不是有效独立通过比较")
        binding: JsonObject = object_value(guard["binding"], "guard binding")
        guard_records: list[JsonObject] = [value for value in session.journal.records if value["event"] == "comparison" and value["case_id"] == case_id and record_data(value).get("comparison_id") == raw_id]
        if binding["scope"] != "guard" or binding["observation_id"] != data["before_observation_id"] or len(guard_records) != 1 or record_int(guard_records[0], "seq") >= record_int(record, "seq"):
            raise IntegrityError("动作守卫来自其他目标/阶段/发送之后")


# 功能：独立核验动作回执与新帧观测，不采用自述断言；参数 result 必须有唯一 intent。
def _audit_result(session: Session, result: JsonObject) -> None:
    if session.target is None:
        raise IntegrityError("结果审计缺少目标")
    data: JsonObject = record_data(result)
    keys_only(data, RESULT_FIELDS, "command result", RESULT_FIELDS)
    intent: JsonObject = session.state.commands[str(data["command_id"])]
    request: JsonObject = record_data(intent)
    receipt_data: JsonObject = object_value(data["receipt"], "receipt")
    keys_only(receipt_data, {"state", "phase", "value", "diagnostic", "diagnostics", "execution_terminated"}, "receipt",
              {"state", "phase", "value", "diagnostic", "diagnostics", "execution_terminated"})
    receipt_state: JsonValue = receipt_data["state"]
    if receipt_state not in {"succeeded", "compile_failed", "unknown", "not_sent"} or data["not_executed"] is not (receipt_state in {"compile_failed", "not_sent"}):
        raise IntegrityError("编译/未发送/未知阶段判定不一致")
    effective: int = integer(data["effective_timeout_ms"], "effective timeout", 0, session.target.limits.max_timeout_ms)
    if effective > integer(request["timeout_ms"], "declared timeout"):
        raise IntegrityError("实际发送突破已登记的剩余总预算")
    diagnostics: JsonValue = receipt_data["diagnostics"]
    if not isinstance(diagnostics, list):
        raise IntegrityError("诊断结构非法")
    if receipt_state == "compile_failed":
        if receipt_data["phase"] != "compilation_not_executed" or receipt_data["value"] is not None or not any(isinstance(value, dict) and value.get("severity", "").lower() == "error" for value in diagnostics):
            raise IntegrityError("编译失败没有明确未执行的真实诊断")
    if receipt_state == "unknown":
        if receipt_data["execution_terminated"] is not False:
            raise IntegrityError("未知结果错误声称执行终止")
        # 脚本自身缺陷只冻结该用例；其余未知阶段必须冻结整轮，两种冻结都必须是真实记录。
        if receipt_data["phase"] == "script_failed" and result["case_id"] is not None and request["mode"] == "read":
            case_id_unknown: str = str(result["case_id"])
            # 用例级冻结记录由宿主在本条 command_result 之后立即写入，属同一用例、同一命令。
            case_frozen: bool = any(record["event"] == "case_frozen" and record["case_id"] == case_id_unknown
                                    and record_data(record).get("command_id") == data["command_id"]
                                    for record in session.journal.records)
            item_unknown: CaseState | None = session.state.cases.get(case_id_unknown)
            if not case_frozen or item_unknown is None or item_unknown.frozen is not True:
                raise IntegrityError("脚本缺陷未知结果没有对应用例级冻结记录")
        elif not session.state.frozen:
            raise IntegrityError("未知结果未冻结整轮")
    if receipt_state != "succeeded":
        if data["observation_ref"] is not None:
            raise IntegrityError("未执行/未知回执不能产生业务观测")
        return
    receipt: EvalReceipt = EvalReceipt("succeeded", "completed", receipt_data["value"], "")
    try:
        frame, actual, error = observed_value(receipt, session.journal.run_id, str(result["case_id"] or ""),
                                             str(data["command_id"]), session.target.build_guid,
                                             str(request["value_format"]), request["target"], session.target.limits,
                                             wrapper_format(session.journal.verify_ref(object_value(request["script_wrapper"], "wrapper ref"))))
    except IntegrityError:
        raise
    except InputError:
        if request["mode"] != "read" or data["observation_valid"] is not False:
            raise IntegrityError("成功回执没有可靠实际身份/观测") from None
        return
    if data["frame"] != frame:
        raise IntegrityError("动作/观测帧不等于真实包装帧")
    if error.startswith("return_value_contract:"):
        matching: list[JsonObject] = [record for record in session.journal.records
            if record["event"] == "case_frozen" and record["case_id"] == result["case_id"]
            and record_data(record).get("command_id") == data["command_id"]
            and record_data(record).get("phase") == "return_value_contract"
            and record_data(record).get("reason") == error and record_int(record, "seq") > record_int(result, "seq")]
        if request["mode"] != "read" or len(matching) != 1 or data["observation_valid"] is not False or data["observation_error"] != error:
            raise IntegrityError("已验证返回值错误没有对应的真实只读隔离记录")
    if request["mode"] != "read":
        if error or data["observation_ref"] is not None:
            raise IntegrityError("动作回执不能作为独立观察或吞掉桥接错误")
        return
    reference: JsonObject = object_value(data["observation_ref"], "observation ref")
    snapshot: JsonObject = object_value(strict_json(session.journal.verify_ref(reference, str(result["case_id"])), session.target.limits.evidence_bytes), "observation snapshot")
    valid: bool = not error and actual is not None
    after_id: JsonValue = request["after_command_id"]
    if after_id is not None:
        after_intent: JsonObject | None = session.state.commands.get(str(after_id))
        after_result: JsonObject | None = session.state.results.get(str(after_id))
        if after_intent is None or after_result is None or after_intent["case_id"] != result["case_id"] or record_data(after_intent)["mode"] != "action":
            raise IntegrityError("跨帧读取没有对应本例动作")
        if object_value(record_data(after_result)["receipt"], "action receipt").get("state") != "succeeded" or record_int(after_result, "seq") >= record_int(intent, "seq"):
            raise IntegrityError("观察在动作完成前或关联未完成动作")
        if frame <= integer(record_data(after_result)["frame"], "action frame", 0):
            valid = False
    if isinstance(actual, dict) and actual and set(actual) <= {"success", "assertion", "passed", "verdict"}:
        valid = False
    expected_snapshot: JsonObject = {
        "schema": SCHEMA, "run_id": session.journal.run_id, "case_id": result["case_id"],
        "observation_id": data["observation_id"], "command_id": data["command_id"],
        "target": request["target"], "purpose": request["purpose"], "step_index": request["index"],
        "frame": frame, "build_guid": session.target.build_guid, "after_command_id": after_id,
        "valid": valid, "error": data["observation_error"], "value": actual,
    }
    if canonical(snapshot) != canonical(expected_snapshot) or data["observation_valid"] is not valid or (not valid and not data["observation_error"]):
        raise IntegrityError("独立观测内容/归属/新帧有效性被改写")


# 功能：取某比较当时的最后成功动作；参数 seq 为精确物理 journal 行号。
def _actions_before(session: Session, item: CaseState, seq: int) -> list[str]:
    return [command_id for command_id in item.actions if record_int(session.state.results[command_id], "seq") < seq]


# 功能：重新根据独立来源与实际业务值回算每条比较；参数 record 不是产品结论的可信输入。
def _audit_comparison(session: Session, record: JsonObject) -> None:
    if session.cases is None or session.target is None:
        raise IntegrityError("比较审计缺少原输入")
    data: JsonObject = record_data(record)
    keys_only(data, COMPARISON_FIELDS, "comparison", COMPARISON_FIELDS)
    case_id: str = str(record["case_id"])
    item: CaseState = session.state.cases[case_id]
    binding: JsonObject = object_value(data["binding"], "binding")
    temporary: CaseState = replace(item, comparisons={key: value for key, value in item.comparisons.items() if key != data["comparison_id"]})
    checked, expected = session._binding(binding, session.original_case(case_id), temporary)
    if canonical(checked) != canonical(binding) or data["comparison_id"] != binding["comparison_id"] or data["actual_observation_id"] != binding["observation_id"] or data["actual_field"] != binding["field"] or canonical(data["expected_value"]) != canonical(expected):
        raise IntegrityError("原预期绑定、实际字段或独立预期被修改")
    observation: JsonObject = item.observations[str(binding["observation_id"])]
    if integer(observation["record_seq"], "observation seq") >= record_int(record, "seq"):
        raise IntegrityError("比较引用未来观测")
    actual: JsonValue = None
    before_value: JsonValue = None
    computed: JsonValue = None
    matched: bool | None = None
    valid: bool = False
    try:
        if binding["scope"] == "expected" and item.completion_pending(record_int(record, "seq")) is not None:
            raise InputError("业务完成条件未确认")
        if observation.get("valid") is not True or observation.get("error") or observation.get("build_guid") != session.target.build_guid:
            raise InputError("无效观测")
        actions: list[str] = _actions_before(session, item, record_int(record, "seq"))
        if actions:
            action_id: str = actions[-1]
            if observation["after_command_id"] != action_id or integer(observation["frame"], "actual frame", 0) <= integer(record_data(session.state.results[action_id])["frame"], "action frame", 0):
                raise InputError("旧阶段观测")
        actual = field_value(observation["value"], str(binding["field"]))
        if binding["operator"] == "delta":
            before_binding: JsonObject = object_value(binding["before"], "before")
            keys_only(before_binding, {"observation_id", "field"}, "before", {"observation_id", "field"})
            previous: JsonObject | None = item.observations.get(str(before_binding["observation_id"]))
            if previous is None or previous.get("valid") is not True or previous["target"] != observation["target"] or previous["build_guid"] != observation["build_guid"] or integer(previous["frame"], "before frame", 0) >= integer(observation["frame"], "after frame", 0):
                raise InputError("delta 前后目标/帧不足")
            if actions and integer(previous["record_seq"], "before seq") >= record_int(session.state.commands[actions[-1]], "seq"):
                raise InputError("before 不在动作之前")
            before_value = field_value(previous["value"], str(before_binding["field"]))
        basis: JsonObject = object_value(binding["basis"], "basis")
        matched, computed = compare_values(str(binding["operator"]), actual, expected, before_value,
                                           basis.get("original_is_text_contains") is True)
        valid = True
    except InputError:
        pass
    status: str = "passed" if valid and matched else "failed" if valid else "test_inconclusive"
    if data["valid"] is not valid or data["matched"] is not matched or data["status"] != status or canonical(data["actual"]) != canonical(actual) or canonical(data["before_value"]) != canonical(before_value) or canonical(data["computed_value"]) != canonical(computed):
        raise IntegrityError("比较结果与原业务值/独立预期回算不一致")
    if data["semantic_equivalence"] != "current_agent_review_not_machine_proof":
        raise IntegrityError("不得声称机器已经证明自然语言语义等价")
    _snapshot_matches(session.journal, data)


# 功能：回算唯一 final 覆盖及四状态；参数 record 不允许覆盖真实有效反例。
def _audit_final(session: Session, record: JsonObject) -> None:
    if session.cases is None or session.target is None:
        raise IntegrityError("final 审计缺少原输入")
    data: JsonObject = record_data(record)
    keys_only(data, FINAL_FIELDS, "case final", FINAL_FIELDS)
    case_id: str = str(record["case_id"])
    item: CaseState = session.state.cases[case_id]
    coverage: JsonObject = case_coverage(session.cases.case(case_id), item)
    if data["coverage"] != coverage or data["comparison_ids"] != list(item.comparisons) or data["observation_ids"] != list(item.observations) or data["action_command_ids"] != item.actions or data["start_seq"] != item.started["seq"] or data["start_hash"] != item.started["hash"]:
        raise IntegrityError("final 与本例实时原步骤/预期/证据覆盖不符")
    if data["status"] not in VERDICTS or data["requested_status"] not in VERDICTS:
        raise IntegrityError("final 四状态非法")
    if item.failed_comparisons and data["status"] != "failed":
        raise IntegrityError("真实反例被错误转成环境阻塞/通过/未定论")
    if data["status"] == "failed" and not item.failed_comparisons:
        raise IntegrityError("缺业务反例却声明产品失败")
    if data["status"] == "passed" and coverage["all_matched"] is not True:
        raise IntegrityError("partial、缺原预期或无效观测被错误判通过")
    if data["status"] == "passed" and any(value["event"] == "session_frozen" and record_int(value, "seq") < record_int(record, "seq") for value in session.journal.records):
        raise IntegrityError("冻结/未知之后被错误声明 passed")
    if data["status"] == "passed" and item.frozen:
        raise IntegrityError("本例脚本失败冻结后被错误声明 passed")
    if data["status"] == "blocked":
        category: JsonValue = data["category"]
        if category == "permission":
            permission: JsonValue = data["required_permission"]
            if permission in session.target.permissions or permission not in {"attach", "script_execute", "business_action", "setup_action", "log_read", "screenshot"}:
                raise IntegrityError("权限阻塞来源不能核验")
        elif category == "environment":
            if not any(value["event"] == "environment_blocked" and record_int(value, "seq") < record_int(record, "seq") for value in session.journal.records):
                raise IntegrityError("环境阻塞缺少真实记录")
        elif category == "critical_precondition":
            if not any(value.get("valid") is True and value.get("matched") is False and object_value(value["binding"], "binding")["scope"] == "precondition" for value in item.comparisons.values()):
                raise IntegrityError("前置阻塞缺少事实")
        elif category != "user_stop":
            raise IntegrityError("blocked 来源未知")
    if data["status"] == "test_inconclusive":
        category = data["category"]
        if category == "not_attempted":
            raise IntegrityError("不确定不得来自未执行")
        if category == "insufficient_observation":
            if not item.observations and not item.frozen:
                raise IntegrityError("观测不足缺少本例真实观测或只读脚本失败记录")
        elif category == "not_constructible":
            attempted: bool = bool(item.actions) or any(value["event"] == "environment_blocked" and record_int(value, "seq") < record_int(record, "seq") for value in session.journal.records)
            if not attempted:
                raise IntegrityError("不可构造缺少真实尝试")
        else:
            raise IntegrityError("不确定来源未知")
    text(data["reason"], "final reason", trim=False)
    _snapshot_matches(session.journal, data)


# 功能：核验 writer 计时闭合与收口审计顺序；参数 require_closed 用于报告门禁。
def _timing(session: Session, require_closed: bool) -> JsonObject:
    if session.state.closed is None or session.state.timing is None:
        if require_closed:
            raise IntegrityError("正式报告要求先收口/审计/计时闭合；不能手填或回退耗时")
        return {"status": "open", "duration_ns": None}
    start: JsonObject = session.journal.records[0]
    finish: JsonObject = session.state.timing
    data: JsonObject = record_data(finish)
    closed: JsonObject = session.state.closed
    closing: JsonObject = record_data(closed)
    audit_seq: int = integer(closing["audit_seq"], "closing audit seq", 1, len(session.journal.records))
    audit: JsonObject = session.journal.records[audit_seq - 1]
    parent: JsonValue = record_data(start).get("parent")
    expected_scope: str = "child" if parent is not None or record_data(start).get("workflow") is not None else "self"
    if audit["event"] != "audit_complete" or audit["hash"] != closing["audit_hash"] or audit_seq >= record_int(closed, "seq") or record_int(finish, "seq") <= record_int(closed, "seq"):
        raise IntegrityError("没有先完成审计/收口再闭合计时")
    duration: int = record_int(finish, "monotonic_ns") - record_int(start, "monotonic_ns")
    if data != {"scope": expected_scope, "start_seq": 1, "start_hash": start["hash"], "duration_ns": duration} or duration < 0:
        raise IntegrityError("计时不是 writer 本轮初始化至闭合的真实时钟")
    return {"status": "closed", "start_time": start["time_utc"], "end_time": finish["time_utc"],
            "duration_ns": duration, "scope": expected_scope, "source": "writer_perf_counter_ns"}


# 功能：扫描具体未解释间隔与超预算命令；参数阈值只来自本轮集中配置。
def _time_warnings(session: Session) -> list[JsonObject]:
    notes: dict[tuple[str, int], str] = {}
    for record in session.journal.records:
        if record["event"] == "case_note":
            data: JsonObject = record_data(record)
            notes[(str(data["category"]), integer(data["related_seq"], "note seq"))] = str(data["message"])
    warnings: list[JsonObject] = []
    last: JsonObject | None = None
    end_seq: int = record_int(session.state.timing, "seq") if session.state.timing is not None else len(session.journal.records)
    for record in session.journal.records[:end_seq]:
        if last is not None:
            interval: int = record_int(record, "monotonic_ns") - record_int(last, "monotonic_ns")
            if interval > session.journal.limits.gap_warning_ms * 1000000:
                explanation: str = notes.get(("gap_explanation", record_int(last, "seq")), "")
                warnings.append({"kind": "interval", "from_seq": last["seq"], "to_seq": record["seq"],
                                 "duration_ns": interval, "explanation": explanation,
                                 "scope": "agent_between_calls" if last["event"] == "cli_result" and record["event"] == "cli_begin" else "host_or_transport"})
        last = record
    for command_id, result in session.state.results.items():
        intent: JsonObject = session.state.commands[command_id]
        duration: int = record_int(result, "monotonic_ns") - record_int(intent, "monotonic_ns")
        if duration > session.journal.limits.overrun_warning_ms * 1000000:
            warnings.append({"kind": "command_overrun", "command_id": command_id, "seq": result["seq"],
                             "duration_ns": duration, "explanation": notes.get(("overrun_reason", record_int(result, "seq")), "")})
    return warnings


# 功能：核验来源失效的本地终止记录，供包内父关闭；参数 session 必须已经关闭/计时，不生成业务计数或正式资格。
def audit_interruption(session: Session) -> JsonObject:
    session.journal.refresh()
    session._refresh()
    if not session.state.integrity_interrupted or session.state.closed is None or session.state.timing is None:
        raise IntegrityError("中断审计必须先有唯一来源失效终止、关闭及 writer 计时")
    session.verify_sources(local_terminal=True)
    for record in session.journal.records:
        event: str = str(record["event"])
        if event not in EVENT_FIELDS:
            raise IntegrityError("中断快照包含未知关键事件")
        keys_only(record_data(record), EVENT_FIELDS[event], "interruption event")
    closing: JsonObject = record_data(session.state.closed)
    if closing.get("complete") is not False or not closing.get("interrupted_reason"):
        raise IntegrityError("来源失效不能宣称完整有效执行")
    return {"formal_eligible": False, "source_integrity_valid": False, "scope": "verified_local_interruption",
            "missing_case_ids": closing["missing_case_ids"], "timing": _timing(session, require_closed=True),
            "upload": "not_executed"}


# 功能：完整包内审计，只读本地证据并独立回算结论；参数 require_closed 控制正式报告门禁。
def audit_run(session: Session, require_closed: bool = True) -> JsonObject:
    session.journal.refresh()
    session._refresh()
    session.verify_sources()
    if session.cases is None or session.target is None:
        raise IntegrityError("审计缺少完整原输入")
    initial: JsonObject = record_data(session.journal.records[0])
    if initial["case_ids"] != [case.case_id for case in session.cases.cases] or initial["mode"] != "mono_exploration" or initial["upload"] != "not_executed":
        raise IntegrityError("原全集/通道/未上传事实被修改")
    index_ref: JsonObject = object_value(initial["case_index"], "case index ref")
    if strict_json(session.journal.verify_ref(index_ref), session.target.limits.evidence_bytes) != case_index(session.cases):
        raise IntegrityError("原索引、原文本或完整字段视图不匹配")
    allowed_cases: set[str] = {case.case_id for case in session.cases.cases}
    if session.state.chain_original is not None:
        allowed_cases.add(CONTROL_CASE)
    cli_calls: dict[str, JsonObject] = {}
    completed_calls: set[str] = set()
    issues: set[str] = set()
    for record in session.journal.records:
        event: str = str(record["event"])
        data: JsonObject = record_data(record)
        if event not in EVENT_FIELDS:
            raise IntegrityError("journal 存在未知关键事件")
        keys_only(data, EVENT_FIELDS[event], "journal event")
        if record["case_id"] is not None and record["case_id"] not in allowed_cases:
            raise IntegrityError("事件引用了原全集之外的用例")
        if event == "cli_begin":
            call_id: str = str(data["call_id"])
            if call_id in cli_calls:
                raise IntegrityError("CLI 调用 ID 重复")
            cli_calls[call_id] = record
        elif event == "cli_result":
            call_id = str(data["call_id"])
            if data.get("operation") != "init" and call_id not in cli_calls:
                raise IntegrityError("CLI 结果没有本轮调用")
            if call_id in completed_calls:
                raise IntegrityError("CLI 结果重复")
            completed_calls.add(call_id)
        elif event == "intent":
            _audit_intent(session, record)
        elif event == "command_result":
            _audit_result(session, record)
        elif event == "case_frozen":
            command: JsonObject | None = session.state.commands.get(str(data.get("command_id")))
            result: JsonObject | None = session.state.results.get(str(data.get("command_id")))
            if command is None or result is None or command["case_id"] != record["case_id"] or record_data(command).get("mode") != "read" or record_int(result, "seq") + 1 != record_int(record, "seq") or data.get("execution_terminated") is not False:
                raise IntegrityError("用例隔离没有对应的实时只读结果")
            result_data: JsonObject = record_data(result)
            receipt: JsonObject = object_value(result_data.get("receipt"), "case freeze receipt")
            if data.get("phase") == "return_value_contract":
                if receipt.get("state") != "succeeded" or not str(result_data.get("observation_error", "")).startswith("return_value_contract:") or data.get("reason") != result_data.get("observation_error"):
                    raise IntegrityError("用例隔离没有已验证的返回契约错误")
            elif data.get("phase") != "script_failed" or receipt.get("state") != "unknown" or receipt.get("phase") != "script_failed" or data.get("reason") != receipt.get("diagnostic"):
                raise IntegrityError("用例隔离缺少真实片段失败分类")
        elif event == "comparison":
            _audit_comparison(session, record)
        elif event == "chain_started":
            if record["case_id"] != CONTROL_CASE or data["source_kind"] != "input":
                raise IntegrityError("共享准备来源归属或类型错误")
            _snapshot_matches(session.journal, data)
        elif event == "chain_closed":
            if record["case_id"] != CONTROL_CASE or session.state.chain_original is None:
                raise IntegrityError("共享链路缺少独立来源")
            chain_item: CaseState = session.state.cases[CONTROL_CASE]
            coverage_chain: JsonObject = case_coverage(session.state.chain_original, chain_item)
            if data["ready"] is not True or data["coverage"] != coverage_chain or coverage_chain["all_matched"] is not True or data["comparison_ids"] != list(chain_item.comparisons) or data["observation_ids"] != list(chain_item.observations) or data["action_command_ids"] != chain_item.actions or data["start_seq"] != chain_item.started["seq"] or data["start_hash"] != chain_item.started["hash"]:
                raise IntegrityError("共享链路就绪与独立步骤/预期证据不一致")
            _snapshot_matches(session.journal, data)
        elif event == "case_final":
            if record["case_id"] == CONTROL_CASE:
                raise IntegrityError("共享准备不能计入业务 final")
            _audit_final(session, record)
        elif event == "artifact_collected":
            item = session.state.cases[str(record["case_id"])]
            observation: JsonObject | None = item.observations.get(str(data["observation_id"]))
            if observation is None or observation.get("valid") is not True:
                raise IntegrityError("附件没有本例有效来源观察")
            metadata: JsonObject = object_value(field_value(observation["value"], str(data["field"])), "artifact metadata")
            reference: JsonObject = object_value(data["evidence"], "artifact ref")
            content: bytes = session.journal.verify_ref(reference, str(record["case_id"]))
            source: JsonObject = object_value(reference["source"], "artifact source")
            if metadata.get("run_id") != session.journal.run_id or metadata.get("case_id") != record["case_id"] or metadata.get("command_id") != observation["command_id"] or metadata.get("build_guid") != session.target.build_guid or metadata.get("frame") != observation["frame"] or metadata.get("privacy") != "public_reviewed" or metadata.get("bytes") != len(content) or metadata.get("sha256") != digest(content):
                raise IntegrityError("附件归属/帧/摘要/敏感审核不匹配")
            if source.get("original_path") != metadata["path"] or source.get("original_sha256") != metadata["sha256"] or source.get("privacy_review") != data["privacy_review"]:
                raise IntegrityError("附件来源与当前 Agent 审核记录不一致")
        elif event in {"attribution", "reference_recorded"}:
            _snapshot_matches(session.journal, data)
            item: CaseState = session.state.cases[str(record["case_id"])]
            for comparison_id in cast(list[JsonValue], data["comparison_ids"]):
                if comparison_id not in item.comparisons:
                    raise IntegrityError("归因/参考比较跨例或缺失")
            for observation_id in cast(list[JsonValue], data["observation_ids"]):
                if observation_id not in item.observations:
                    raise IntegrityError("归因/参考观察跨例或缺失")
            if event == "attribution" and data["classification"] == "product_confirmed":
                issue_id: str = text(data["issue_id"], "issue_id")
                if issue_id in issues or not set(str(value) for value in cast(list[JsonValue], data["comparison_ids"])) & set(item.failed_comparisons):
                    raise IntegrityError("产品问题缺反例、重复 issue 或错误计 Bug")
                issues.add(issue_id)
        elif event == "report_rendered":
            session.journal.verify_ref(object_value(data["evidence"], "report ref"))
    pending_calls: list[JsonObject] = [record for call_id, record in cli_calls.items() if call_id not in completed_calls]
    if pending_calls and (len(pending_calls) != 1 or record_data(pending_calls[0])["operation"] not in {"audit", "close", "report"} or pending_calls[0] is not list(cli_calls.values())[-1]):
        raise IntegrityError("先前 CLI 缺实时结果，不能默默补完或生成正式报告")
    counts: JsonObject = {status: 0 for status in sorted(VERDICTS)}
    coverage: JsonObject = {}
    missing: list[str] = []
    unattributed: list[str] = []
    logs: list[JsonObject] = []
    for original in session.cases.cases:
        item: CaseState | None = session.state.cases.get(original.case_id)
        if item is None or item.final is None:
            missing.append(original.case_id)
        if item is not None:
            coverage[original.case_id] = case_coverage(original, item)
            if item.final is not None:
                status: str = str(record_data(item.final)["status"])
                counts[status] = cast(int, counts[status]) + 1
                if status == "failed" and not any(record["event"] == "attribution" and record["case_id"] == original.case_id for record in session.journal.records):
                    unattributed.append(original.case_id)
            for observation in item.observations.values():
                if observation["purpose"] == "logs":
                    logs.append({"case_id": original.case_id, "observation_id": observation["observation_id"],
                                 "valid": observation["valid"], "value": observation["value"], "evidence": observation["evidence"]})
    if session.state.closed is not None:
        closing: JsonObject = record_data(session.state.closed)
        if closing["missing_case_ids"] != missing or closing["complete"] is not (not missing) or (missing and not closing.get("interrupted_reason")):
            raise IntegrityError("不完整全集被静默宣布完整或未注明中断原因")
    timing: JsonObject = _timing(session, require_closed)
    workflow: JsonObject | None = None
    if initial.get("workflow") is not None:
        if initial.get("parent") is not None or initial.get("report_owner") != "coordinator":
            raise IntegrityError("统一父交接不能混用包内父或子报告拥有者")
        workflow = verify_workflow(object_value(initial["workflow"], "workflow binding"), session.target.limits,
                                   session.journal.records[0]["time_utc"], timing.get("end_time"))
    return {"schema": "mono-pipeline-audit/1", "run_id": session.journal.run_id, "input_count": len(session.cases.cases),
            "final_count": sum(cast(int, value) for value in counts.values()), "counts": counts,
            "missing_case_ids": missing, "coverage": coverage, "frozen": session.state.frozen,
            "unknown_commands": [command_id for command_id, record in session.state.results.items() if object_value(record_data(record)["receipt"], "receipt")["state"] == "unknown"],
            "pending_commands": [command_id for command_id in session.state.commands if command_id not in session.state.results],
            "product_issue_count": len(issues), "unattributed_failed_case_ids": unattributed,
            "time_warnings": _time_warnings(session), "timing": timing, "workflow": workflow,
            "log_status": "case_scoped_observations_only" if logs else "not_collected_unknown",
            "log_observations": logs, "formal_eligible": session.state.closed is not None and session.state.timing is not None,
            "chain_ready": session.state.chain_closed is not None,
            "upload": "not_executed", "semantic_equivalence": "agent_review_not_machine_proof"}


# 功能：转义 Markdown 表格/链接内容；参数原文不会作为代码或 HTML 执行。
def _md(value: JsonValue) -> str:
    encoded: str = canonical(value).decode("utf-8") if isinstance(value, (dict, list)) else str(value if value is not None else "未记录")
    return html.escape(encoded, quote=False).replace("\\", "\\\\").replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;").replace("`", "&#96;").replace("\r", "").replace("\n", "<br>")


# 功能：构建可点击的真实相对文件/物理行引用；参数 path 仅来自已审计本轮产物。
def _link(label: JsonValue, path: str, line: int = 1) -> str:
    return "[" + _md(label) + "](" + quote(path, safe="/.-_") + ":" + str(line) + ")"


# 功能：构建实际私有证据链接；参数 reference 必须先通过 audit。
def _ref(label: JsonValue, reference: JsonObject) -> str:
    return _link(label, str(reference["path"]))


# 功能：仅按 final 及明确缺口形成运行结论；参数 counts 不含动作回执统计。
def _overall(counts: JsonObject, missing: bool) -> str:
    if cast(int, counts["failed"]):
        return "存在有效反例，失败保持失败"
    if missing or cast(int, counts["test_inconclusive"]):
        return "测试结论不完整"
    if cast(int, counts["blocked"]):
        return "存在环境/权限/关键前置阻塞"
    return "已收口用例全部通过（仅 Mono 探索及本轮原预期范围）"


# 功能：生成固定原可读口径报告正文；参数 audit 已由包内回算，不修改任何 final。
def _body(session: Session, audit: JsonObject) -> list[str]:
    if session.cases is None:
        raise IntegrityError("报告缺原用例")
    initial: JsonObject = record_data(session.journal.records[0])
    source: JsonObject = object_value(object_value(initial["case_input"], "case input")["snapshot"], "input snapshot")
    index_ref: JsonObject = object_value(initial["case_index"], "index ref")
    counts: JsonObject = object_value(audit["counts"], "counts")
    timing: JsonObject = object_value(audit["timing"], "timing")
    identity_checks: int = sum(1 for record in session.journal.records if record["event"] == "connection_checked")
    lines: list[str] = [
        "# Mono 探索功能测试报告", "",
        "<!-- 创建日期：2026-10-26；作者：Cyou；功能：本轮实时证据、原预期及唯一 final 的固定报告；参数：已审计 journal 与 writer 闭合计时；不含网络上报。 -->", "",
        "## 1. 运行概览", "",
        "- 原完整输入：" + _ref("原字节及全部字段", source),
        "- 运行：" + _link(session.journal.run_id, JOURNAL_NAME),
        f"- 原全集 {audit['input_count']} 条；唯一 final {audit['final_count']} 条；未收口缺口 {len(cast(list[JsonValue], audit['missing_case_ids']))} 条。",
        "- 唯一 final 数仅表示结论已收口，不代表每条原步骤和预期均完成验证。",
        "- 含实际动作的原用例数：" + str(sum(1 for original in session.cases.cases
            if original.case_id in session.state.cases and session.state.cases[original.case_id].actions))
        + "；完成条件未确认的原用例数：" + str(sum(1 for original in session.cases.cases
            if original.case_id in session.state.cases and session.state.cases[original.case_id].completion_pending() is not None)) + "。",
        f"- 用例总数：{audit['input_count']}；functional={audit['input_count']}；functional passed={counts['passed']} failed={counts['failed']} blocked={counts['blocked']} test_inconclusive={counts['test_inconclusive']}",
        f"- 定位Bug数：{audit['product_issue_count']}；修复问题数：0；自动修复轮次：0",
        "- 四状态（只从 final 计算）：" + "；".join(_link(status, JOURNAL_NAME) + " = " + str(counts[status]) for status in ("passed", "failed", "blocked", "test_inconclusive")),
        "- 通道：Mono 探索；不证明 IL2CPP 的 AOT 泛型、托管裁剪或 HybridCLR 元数据。",
        "- 独立执行开始：" + _md(timing["start_time"]) + "；结束：" + _md(timing["end_time"]) + f"；writer 有效跨度 {cast(int, timing['duration_ns']) / 1000000000:.6f} 秒。",
        "- 时间包含本轮 Agent 调用间隔/门禁/执行/收口；分项不累加冒充总耗时。",
        "- 上报：未执行；没有上报耗时。宿主未执行编辑器编译、包构建、重启或自修；Player 启动由父工作流负责，片段与登录/前置动作见本轮命令证据。",
        (f"- 连接：本轮成功身份重验 {identity_checks} 次；描述符令牌确实落盘，核验记录只含公共 ACL/身份摘要，不复制令牌原文。"
         if identity_checks else "- 连接：本轮没有成功附加身份核验；不声称 Player/实际描述符 ACL 已通过。描述符令牌落盘必须经过 ACL 门禁。"),
        "- 脚本不是沙箱；只读性质、业务入口合法性及自然语言到比较的语义由当前 Agent 审核。", "",
        "## 2. 逐例结果与分组", "",
        "| 分组 | 原 CaseId / 标题 | 唯一结果 | 原步骤/预期缺口及原因 |",
        "| --- | --- | --- | --- |",
    ]
    if session.state.chain_original is not None:
        chain_item: CaseState = session.state.cases[CONTROL_CASE]
        chain_source: JsonObject = record_data(chain_item.started)
        chain_evidence: JsonObject = object_value(chain_source["evidence"], "chain source evidence")
        lines[lines.index("## 2. 逐例结果与分组"):lines.index("## 2. 逐例结果与分组")] = [
            "- 共享链路来源：" + _ref("独立准备步骤、预期与审核", chain_evidence) + "；不加入原业务用例总数或通过数。",
            "- 共享链路就绪：" + _md(session.state.chain_closed is not None) + "；准备动作数：" + str(len(chain_item.actions)) + "。", "",
        ]
    for original in session.cases.cases:
        item: CaseState | None = session.state.cases.get(original.case_id)
        if item is None or item.final is None:
            lines.append("| " + _md(item.group_id if item else "未分组") + " | " + _ref(original.case_id + " / " + original.title, source) + " | 未收口，不补造 final | " + _md(case_coverage(original, item) if item else "未开始；原完整用例仍保留") + " |")
        else:
            final: JsonObject = record_data(item.final)
            reference: JsonObject = object_value(final["evidence"], "final evidence")
            lines.append("| " + _md(item.group_id) + " | " + _ref(original.case_id + " / " + original.title, source) + " | " + _ref(final["status"], reference) + " | " + _ref(final["reason"], reference) + "；" + _ref(final["coverage"], reference) + " |")
    lines += ["", "## 3. 原预期绑定、节点与业务证据", "",
              "| 原 CaseId | 原范围/索引/原文 | 比较规则 / 独立预期依据 | 实际观察 ID / 字段 / 值 | 比较与强度 |",
              "| --- | --- | --- | --- | --- |"]
    for original in session.cases.cases:
        item = session.state.cases.get(original.case_id)
        bound: set[int] = set()
        if item is not None:
            for comparison in item.comparisons.values():
                binding: JsonObject = object_value(comparison["binding"], "binding")
                evidence: JsonObject = object_value(comparison["evidence"], "comparison evidence")
                if binding["scope"] == "expected":
                    bound.add(integer(binding["index"], "expected index"))
                actual_text: JsonObject = {"observation_id": binding["observation_id"], "field": binding["field"],
                                           "actual": comparison["actual"], "before": comparison["before_value"], "computed": comparison["computed_value"]}
                lines.append("| " + _ref(original.case_id, source) + " | " + _ref(str(binding["scope"]) + " / " + str(binding["index"]) + " / " + str(binding["original_text"]), source)
                             + " | " + _ref(binding["operator"], evidence) + "；" + _ref(binding["basis"], evidence)
                             + " | " + _ref(actual_text, evidence) + " | " + _ref(comparison["status"], evidence)
                             + "；" + _ref(comparison["assertion_strength"], evidence) + "；" + _ref(comparison["diagnostic"], evidence) + " |")
        for expected in original.expected:
            if expected.index not in bound:
                lines.append("| " + _ref(original.case_id, source) + " | " + _ref("expected / " + str(expected.index) + " / " + expected.text, source) + " | 未绑定 | 无有效独立比较 | 缺口，不能通过 |")
    lines += ["", "- 语义边界：程序审计结构、类型、原索引、来源、帧及证据；不假称机器证明了原自然语言语义等价。文本包含或仅节点状态的绑定全部展示，不隐藏弱断言。", "",
              "| 原 CaseId / 观察 | 当前目标 / Unity 帧 | 实际业务值 | 有效性 / 异常 |", "| --- | --- | --- | --- |"]
    for case_id, item in session.state.cases.items():
        for observation in item.observations.values():
            evidence = object_value(observation["evidence"], "observation evidence")
            lines.append("| " + _ref(case_id + " / " + str(observation["observation_id"]), evidence) + " | " + _ref(observation["target"], evidence) + " / " + _ref(observation["frame"], evidence) + " | " + _ref(observation["value"], evidence) + " | " + _ref({"valid": observation["valid"], "error": observation["error"]}, evidence) + " |")
    artifacts: list[JsonObject] = [record for record in session.journal.records if record["event"] == "artifact_collected"]
    if artifacts:
        lines += ["", "| 原 CaseId / 来源观察 | 类别 / 实际帧 | 私有附件 | 原摘要 / 敏感审查 |", "| --- | --- | --- | --- |"]
        for artifact in artifacts:
            artifact_data: JsonObject = record_data(artifact)
            artifact_ref: JsonObject = object_value(artifact_data["evidence"], "artifact ref")
            artifact_source: JsonObject = object_value(artifact_ref["source"], "artifact source")
            lines.append("| " + _ref(str(artifact["case_id"]) + " / " + str(artifact_data["observation_id"]), artifact_ref)
                         + " | " + _ref(artifact_source["artifact_kind"], artifact_ref) + " / " + _ref(artifact_source["frame"], artifact_ref)
                         + " | " + _ref(artifact_ref["path"], artifact_ref)
                         + " | " + _ref({"sha256": artifact_source["original_sha256"], "review": artifact_data["privacy_review"]}, artifact_ref) + " |")
    else:
        lines += ["", "- 附件未收取，不声明截图或附件日志已覆盖本轮。"]
    lines += ["", "| 原 CaseId / 命令 | 用途 / 原索引 | 用户原字节 | 实际包装字节 | 回执阶段 / 帧 |", "| --- | --- | --- | --- | --- |"]
    for command_id, intent in session.state.commands.items():
        data: JsonObject = record_data(intent)
        result: JsonObject | None = session.state.results.get(command_id)
        receipt: JsonValue = record_data(result)["receipt"] if result is not None else {"state": "unknown", "phase": "lost_receipt"}
        lines.append("| " + _link(str(intent["case_id"] or "宿主探针") + " / " + command_id, JOURNAL_NAME, record_int(intent, "seq")) + " | " + _link({"mode": data["mode"], "scope": data["scope"], "index": data["index"]}, JOURNAL_NAME, record_int(intent, "seq")) + " | " + _ref(data["source_sha256"], object_value(data["script_original"], "script ref")) + " | " + _ref(data["sent_sha256"], object_value(data["script_wrapper"], "wrapper ref")) + " | " + _link(receipt, JOURNAL_NAME, record_int(result or intent, "seq")) + " |")
    lines += ["", "## 4. 问题、阻塞、未归因及流程风险", "",
              f"- 已确认产品问题 {audit['product_issue_count']} 个；未归因失败：" + _md(audit["unattributed_failed_case_ids"]) + "。未归因不改变失败，也不计入已定位 Bug。"]
    for record in session.journal.records:
        if record["event"] in {"attribution", "reference_recorded", "case_note", "environment_blocked", "session_frozen"}:
            lines.append("- " + _link({"case_id": record["case_id"], "event": record["event"], **record_data(record)}, JOURNAL_NAME, record_int(record, "seq")))
    for warning in cast(list[JsonValue], audit["time_warnings"]):
        lines.append("- 真实时间间隔/超限：" + _link(warning, JOURNAL_NAME, integer(object_value(warning, "time warning").get("from_seq", object_value(warning, "time warning").get("seq")), "warning seq")))
    if session.state.closed is not None:
        lines.append("- 收口：" + _link(record_data(session.state.closed), JOURNAL_NAME, record_int(session.state.closed, "seq")))
    lines += ["", "## 5. 结论", "", "- " + _overall(counts, bool(audit["missing_case_ids"])),
              "- 全集/原预期/四状态/证据摘要/归属和 writer 时间已回算；覆盖缺口与流程警告保留，不写成全集通过。",
              "- 未知命令及阶段：" + _link({"unknown": audit["unknown_commands"], "pending": audit["pending_commands"], "frozen": audit["frozen"]}, JOURNAL_NAME), "",
              "## 6. 异常日志", "", "- 游戏日志状态：" + _md(audit["log_status"]) + "。缺失、部分、未知或未配置都不等于无异常。"]
    for log in cast(list[JsonValue], audit["log_observations"]):
        item_log: JsonObject = object_value(log, "log observation")
        lines.append("- 本例实际日志观测（非全进程无异常证明）：" + _ref(item_log["value"], object_value(item_log["evidence"], "log evidence")))
    for command_id, result in session.state.results.items():
        receipt_object: JsonObject = object_value(record_data(result)["receipt"], "receipt")
        if receipt_object["state"] != "succeeded" or receipt_object["diagnostics"]:
            lines.append("- " + _link({"command_id": command_id, **receipt_object}, JOURNAL_NAME, record_int(result, "seq")))
    lines += ["", "## 7. 产物", "", "- " + _link(JOURNAL_NAME, JOURNAL_NAME),
              "- " + _link(REPORT_NAME, REPORT_NAME), "- " + _ref("原输入索引及全部原文", index_ref),
              "- 本例原脚本、发送包装、观察、比较、final、归因及附件均使用上方已审计私有链接；没有复制运行时描述符/密码/令牌。"]
    return lines


# 功能：在审计/计时闭合之后独占渲染唯一正式报告；参数 session 必须持有本轮 writer。
def render_run(session: Session) -> JsonObject:
    initial: JsonObject = record_data(session.journal.records[0])
    if initial["report_owner"] not in {"self", "coordinator"}:
        raise InputError("父上下文是唯一报告拥有者；子会话不得渲染重复正式报告")
    audit: JsonObject = audit_run(session, require_closed=True)
    prefix: list[str] = []
    if initial["report_owner"] == "coordinator":
        if session.target is None:
            raise IntegrityError("统一报告缺目标预算")
        workflow: JsonObject = verify_workflow(object_value(initial.get("workflow"), "workflow binding"), session.target.limits,
                                               object_value(audit["timing"], "timing")["start_time"],
                                               object_value(audit["timing"], "timing")["end_time"], True)
        audit["workflow"] = workflow
        parent: JsonObject = object_value(workflow["parent"], "workflow parent")
        prefix = ["<!-- 统一 PC 编排拥有报告；由 Mono 已审计正文渲染一次，不再调用旧 PC 报告器。 -->",
                  "- 统一父技能：" + _md(parent["skill_name"]) + "；父编号：" + _md(parent["invocation_id"]),
                  "- 统一父开始：" + _md(parent["skill_start_time"]) + "；结束：" + _md(parent["skill_end_time"]),
                  "- 统一计时来源：" + _md(workflow["timing_file"]) + "；有效时长由原计时器/统计组件读取，子分项不累加。", ""]
    if session.state.report_intent or (session.journal.root / REPORT_NAME).exists():
        raise IntegrityError("正式报告已登记或存在；禁止覆盖/自动重渲染")
    content: bytes = ("\n".join(prefix + _body(session, audit)) + "\n").encode("utf-8")
    SecretGuard().check_bytes(content)
    intent: JsonObject = session.journal.append("report_intent", {"path": REPORT_NAME, "audit": audit,
                                                                "audited_head": session.journal.records[-1]["hash"]})
    write_new(session.journal.root / REPORT_NAME, content)
    reference: JsonObject = {"evidence_id": new_id("report"), "path": REPORT_NAME, "sha256": digest(content),
                             "bytes": len(content), "kind": "report", "case_id": None,
                             "source": {"kind": "fixed_report", "intent_seq": intent["seq"], "intent_hash": intent["hash"]}}
    session.journal.append("report_rendered", {"evidence": reference, "intent_seq": intent["seq"], "intent_hash": intent["hash"]})
    return {"report": reference, "audit": audit}


# 功能：父摘要只保存子日志身份，私有引用仍由子根独立审计；参数 audit 为完整子审计。
def child_audit_summary(audit: JsonObject) -> JsonObject:
    logs: JsonValue = audit.get("log_observations", [])
    if not isinstance(logs, list):
        raise IntegrityError("子日志审计结构非法")
    summary: JsonObject = {key: value for key, value in audit.items() if key != "log_observations"}
    summary["log_observation_ids"] = [{"case_id": object_value(log, "child log")["case_id"],
                                       "observation_id": object_value(log, "child log")["observation_id"]} for log in logs]
    return summary


# 功能：审计父/子唯一归属及 writer 时间包围关系；参数 journal 不接触真实目标。
def audit_parent(journal: Journal, require_closed: bool = True) -> tuple[JsonObject, list[Path]]:
    journal.refresh()
    if not journal.records or journal.records[0]["event"] != "parent_init":
        raise InputError("不是包内父上下文")
    children: list[JsonObject] = [record_data(record) for record in journal.records if record["event"] == "child_registered"]
    if not children or len({str(child["run_id"]) for child in children}) != len(children):
        raise IntegrityError("父上下文必须包含唯一登记的完整子会话")
    endings: list[JsonObject] = [record for record in journal.records if record["event"] == "timing_closed"]
    closes: list[JsonObject] = [record for record in journal.records if record["event"] == "parent_closed"]
    if require_closed and (len(endings) != 1 or len(closes) != 1):
        raise IntegrityError("父报告要求子收口/审计后父计时唯一闭合")
    finish: JsonObject | None = endings[0] if endings else None
    if finish is not None:
        duration: int = record_int(finish, "monotonic_ns") - record_int(journal.records[0], "monotonic_ns")
        if record_data(finish) != {"scope": "parent", "start_seq": 1, "start_hash": journal.records[0]["hash"], "duration_ns": duration} or record_int(closes[0], "seq") >= record_int(finish, "seq"):
            raise IntegrityError("父时间被手填或未在子收口后闭合")
    counts: JsonObject = {status: 0 for status in sorted(VERDICTS)}
    paths: list[Path] = []
    summaries: list[JsonObject] = []
    input_count: int = 0
    missing_count: int = 0
    for child in children:
        path: Path = Path(str(child["root"]))
        with Session(path) as session:
            if session.journal.run_id != child["run_id"] or session.journal.records[0]["hash"] != child["init_hash"]:
                raise IntegrityError("登记的子初始化摘要/身份不一致")
            initial: JsonObject = record_data(session.journal.records[0])
            parent: JsonObject = object_value(initial["parent"], "child parent")
            if parent != {"root": str(journal.root), "invocation_id": journal.run_id,
                          "init_hash": journal.records[0]["hash"], "report_owner": "parent"} or session.state.report_intent:
                raise IntegrityError("父/子报告拥有者不一致或子已经渲染")
            audit: JsonObject = audit_run(session, require_closed=require_closed)
            if record_int(session.journal.records[0], "monotonic_ns") < record_int(journal.records[0], "monotonic_ns") or (finish is not None and session.state.timing is not None and record_int(session.state.timing, "monotonic_ns") > record_int(finish, "monotonic_ns")):
                raise IntegrityError("父 writer 时间没有包围当前子执行")
            input_count += integer(audit["input_count"], "input_count")
            missing_count += len(cast(list[JsonValue], audit["missing_case_ids"]))
            child_counts: JsonObject = object_value(audit["counts"], "child counts")
            for status in VERDICTS:
                counts[status] = cast(int, counts[status]) + cast(int, child_counts[status])
            summaries.append(child_audit_summary(audit))
            paths.append(path)
    for record in journal.records:
        journal.verify_references(record_data(record))
    return {"invocation_id": journal.run_id, "counts": counts, "input_count": input_count,
            "missing_count": missing_count, "children": summaries, "closed": finish is not None,
            "timing": {"start_time": journal.records[0]["time_utc"], "end_time": finish["time_utc"] if finish else None,
                       "duration_ns": record_data(finish)["duration_ns"] if finish else None}, "upload": "not_executed"}, paths


# 功能：渲染父拥有的唯一合并报告；参数 root 的子会话不会产生第二份正式报告。
def render_parent(root: Path) -> JsonObject:
    with Journal(root) as journal, local_cli_call(journal, "context-report") as response:
        audit, paths = audit_parent(journal, require_closed=True)
        if any(record["event"] == "report_intent" for record in journal.records) or (root / REPORT_NAME).exists():
            raise IntegrityError("父正式报告已经存在或登记；禁止重复渲染")
        timing: JsonObject = object_value(audit["timing"], "parent timing")
        lines: list[str] = ["# Mono 探索父上下文唯一报告", "",
                            "<!-- 创建日期：2026-10-26；作者：Cyou；功能：明确父拥有者的唯一固定汇总报告；参数：包内父/子 journal 及 writer 计时。 -->", "",
                            "- 父计时：" + _md(timing) + "；子分项不累加冒充父耗时。",
                            "- 原输入 " + str(audit["input_count"]) + " 条；未收口缺口 " + str(audit["missing_count"]) + " 条；四状态只累加各子唯一 final：" + _md(audit["counts"]),
                            "- 上报：未执行；没有上报耗时。父/子不同时渲染报告。", ""]
        for path in paths:
            with Session(path) as session:
                child_audit: JsonObject = audit_run(session, require_closed=True)
                body: list[str] = _body(session, child_audit)
                relative: str = Path(os_relative(path, root)).as_posix()
                for line in body:
                    if line == "- " + _link(REPORT_NAME, REPORT_NAME):
                        continue
                    if line.startswith("# "):
                        lines.append("# 子会话 " + _md(session.journal.run_id))
                    else:
                        # 已知生成器只输出相对产物链接，统一添加该子根前缀。
                        import re
                        lines.append(re.sub(r"\]\(([^)]+)\)", lambda match: "](" + relative + "/" + match.group(1) + ")", line))
        lines += ["", "- 父物理日志：" + _link(JOURNAL_NAME, JOURNAL_NAME), "- 唯一正式产物：" + _link(REPORT_NAME, REPORT_NAME)]
        content: bytes = ("\n".join(lines) + "\n").encode("utf-8")
        SecretGuard().check_bytes(content)
        intent: JsonObject = journal.append("report_intent", {"path": REPORT_NAME, "audit": audit,
                                                             "audited_head": journal.records[-1]["hash"]})
        write_new(root / REPORT_NAME, content)
        reference: JsonObject = {"evidence_id": new_id("report"), "path": REPORT_NAME, "sha256": digest(content),
                                 "bytes": len(content), "kind": "report", "case_id": None,
                                 "source": {"kind": "fixed_parent_report", "intent_hash": intent["hash"]}}
        journal.append("report_rendered", {"evidence": reference, "intent_seq": intent["seq"], "intent_hash": intent["hash"]})
        result: JsonObject = {"report": reference, "audit": audit}
        response["result"] = result
        return result


# 功能：取得跨目录相对路径，不依赖原工程绝对位置；参数 source/base 必须同一本地驱动器。
def os_relative(source: Path, base: Path) -> str:
    import os
    try:
        return os.path.relpath(source, base)
    except ValueError:
        raise InputError("父/子输出必须在同一驱动器以保持可点击相对证据链接") from None
