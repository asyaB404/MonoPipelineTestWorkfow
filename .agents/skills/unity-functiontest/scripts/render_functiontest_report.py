#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_TIMING_DIR = Path(__file__).resolve().parents[2] / "functiontest-report-json" / "scripts"
if str(SKILL_TIMING_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_TIMING_DIR))
from skill_timing import env_snapshot as skill_timing_env_snapshot
from skill_timing import duration_ms as skill_timing_duration_ms
from skill_timing import load_records as load_skill_timing_records
from skill_timing import select_record as select_skill_timing_record


PASS_STATUSES = {"passed"}
FAIL_STATUSES = {"failed"}
BLOCK_STATUSES = {"blocked", "environment_blocked"}
# Compatibility aliases from older run-logs. New records use the four
# canonical verdicts: passed, failed, blocked, test_inconclusive.
INCONCLUSIVE_STATUSES = {"test_inconclusive", "data_blocked", "skipped", "non_comparable"}
BEIJING_TZ = timezone(timedelta(hours=8))
CYOU_TIME_ENV_NAMES = (
    "CYOU_SESSION_DURATION_MS",
    "CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS",
    "CYOU_SESSION_CONDENSE_DURATION_MS",
)
CYOU_TIME_ENV_FIELDS = (
    ("CYOU_SESSION_DURATION_MS", "session_duration_ms", "session_duration_at_start_ms", "session_duration_at_end_ms"),
    ("CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS", "approval_duration_ms", "approval_at_start_ms", "approval_at_end_ms"),
    ("CYOU_SESSION_CONDENSE_DURATION_MS", "condense_duration_ms", "condense_at_start_ms", "condense_at_end_ms"),
)


def configure_utf8_stdio() -> None:
    """Keep Windows terminals from corrupting Chinese paths in script output."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
            if isinstance(data, dict):
                records.append(data)
    return records


def ui_image_diff_reports(run_dir: Path) -> list[Path]:
    """Return effect-image comparison reports produced by this test run only."""
    diff_dir = run_dir / "ui-image-diff"
    if not diff_dir.is_dir():
        return []
    return sorted(
        (path for path in diff_dir.glob("*.md") if path.is_file()),
        key=lambda path: path.name.casefold(),
    )


def ui_image_diff_events(records: list[dict]) -> list[dict]:
    """Return structured effect-image comparison/skip events from the run log."""
    return [
        record
        for record in records
        if value(record, "event", "a", "") in {
            "ui_image_diff",
            "effect_diff",
            "effect_diff_skipped",
            "ui_image_diff_skipped",
        }
    ]


def value(record: dict, key: str, legacy: str = "", default=""):
    if key in record and record[key] not in (None, ""):
        return record[key]
    if legacy and legacy in record and record[legacy] not in (None, ""):
        return record[legacy]
    return default


def details(record: dict) -> dict:
    item = record.get("details")
    return item if isinstance(item, dict) else {}


def infer_run_dir(input_path: Path) -> Path:
    path = input_path.resolve()
    if path.is_dir():
        run_dir = path
        validate_output_run_dir(run_dir)
        return run_dir
    if path.is_file():
        run_dir = path.parent
        validate_output_run_dir(run_dir)
        return run_dir
    raise FileNotFoundError(
        "render precondition failed: run directory or log path not found. "
        "This renderer only accepts an initialized and executed current run_dir/log. "
        "If this is a new test run, create the run_dir and write the current run-log during unity-functiontest execution first; "
        f"input={input_path}"
    )


def validate_output_run_dir(run_dir: Path) -> None:
    parts = list(run_dir.resolve().parts)
    output_indexes = [i for i, part in enumerate(parts) if part.lower() == "output"]
    if not output_indexes:
        raise ValueError(
            "FunctionTest run directory must be under Doc/AI开发文档/output/{feature_id}/{run_dir}: "
            f"{run_dir}"
        )
    output_index = output_indexes[-1]
    if output_index + 2 >= len(parts):
        raise ValueError(f"FunctionTest output path is incomplete: {run_dir}")
    feature_id = parts[output_index + 1]
    run_name = parts[output_index + 2]
    if run_dir.name != run_name or not run_name.startswith(feature_id + "-"):
        raise ValueError(
            "FunctionTest output path must be output/{feature_id}/{feature_id}-{seq4}: "
            f"{run_dir}"
        )


def infer_feature_id(run_name: str, records: list[dict]) -> str:
    for record in records:
        item = details(record).get("feature_id")
        if item:
            return str(item)
    match = re.match(r"^(.*)-\d{4}$", run_name)
    return match.group(1) if match else run_name


def parse_time(text: str):
    if not text:
        return None
    text = str(text)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(text)
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=BEIJING_TZ)
    return result


def format_time(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.astimezone(BEIJING_TZ).isoformat()


def record_duration_ms(record: dict) -> int:
    try:
        return int(value(record, "duration_ms", "d", 0) or 0)
    except (TypeError, ValueError):
        return 0


def lifecycle_bounds(records: list[dict]):
    first_record = records[0] if records else {}
    # PlayMode start/stop no longer writes lifecycle records. query_logs is
    # collected before the actual stop call, so the final run-log record is
    # the complete pre-stop evidence rather than a synthetic stop marker.
    last_record = records[-1] if records else {}
    first_event = value(first_record, "event", "a", "")
    if first_event != "setup":
        raise ValueError(
            "refusing to render FunctionTest report without lifecycle boundary records: "
            f"first event must be setup (actual={first_event or 'missing'})"
        )

    first_start = parse_time(value(first_record, "start_time", "ts"))
    last_end = parse_time(value(last_record, "end_time", "te"))
    if not first_start or not last_end:
        raise ValueError(
            "refusing to render FunctionTest report with invalid lifecycle timestamps: "
            "the first record start_time and last record end_time are required"
        )
    if last_end < first_start:
        raise ValueError("refusing to render FunctionTest report with lifecycle end before start")
    start_text = format_time(first_start)
    end_text = format_time(last_end)
    return start_text, end_text


def validate_query_log_contract(records: list[dict]) -> None:
    """Keep runtime log records directly consumable by the Markdown renderer."""
    for record in records:
        if value(record, "event", "a", "") != "query_logs":
            continue
        item = details(record)
        for key in ("type", "message", "stack_trace"):
            # New writers always emit these fields.  Keep rendering compatible
            # with historical logs that predate the contract; only reject a
            # field that is present with a conflicting type.
            if key in item and not isinstance(item.get(key), str):
                raise ValueError("refusing to render query_logs with non-string details." + key)


def resolve_skill_timing_file(run_dir: Path, timing_file: Path | None) -> Path | None:
    if timing_file:
        path = timing_file.resolve()
        return path if path.is_file() else None
    direct = run_dir / f"{run_dir.name}-skill-timing.json"
    if direct.is_file():
        return direct
    candidates = sorted(run_dir.glob("*-skill-timing.json"))
    return candidates[-1] if candidates else None


def skill_timing_summary(
    run_dir: Path,
    timing_file: Path | None,
    skill_name: str,
) -> tuple[dict | None, list[dict], Path | None]:
    path = resolve_skill_timing_file(run_dir, timing_file)
    if not path:
        return None, [], None
    try:
        records = load_skill_timing_records(path)
    except (OSError, ValueError):
        return None, [], path
    root = select_skill_timing_record(records, skill_name=skill_name)
    visible = [item for item in records if item.get("report_visible", True) and item.get("skill_end_time")]
    return root, visible, path


def cyou_time_environment_values() -> tuple[int, int, int] | None:
    """Return the complete Cyou timing set, or None when it is unavailable."""
    snapshot = skill_timing_env_snapshot()
    values = tuple(snapshot.get(key) for key in (
        "session_duration_ms",
        "approval_duration_ms",
        "condense_duration_ms",
    ))
    if not all(isinstance(item, int) for item in values):
        return None
    return values  # type: ignore[return-value]


def cyou_fallback_duration_ms() -> int | None:
    values = cyou_time_environment_values()
    if values is None:
        return None
    session_ms, approval_ms, condense_ms = values
    return max(0, session_ms - approval_ms - condense_ms)


def record_skill_duration_ms(record: dict | None) -> int | None:
    if not record:
        return None
    value_ms = record.get("skill_active_duration_ms")
    try:
        return max(0, int(value_ms)) if value_ms is not None else None
    except (TypeError, ValueError):
        return None


def report_duration_ms(record: dict | None) -> int:
    """Return the same duration that JSON conversion can upload."""
    local_ms = record_skill_duration_ms(record)
    if local_ms is not None:
        return local_ms
    if is_nested_timing_record(record):
        return 0
    return cyou_fallback_duration_ms() or 0


def report_duration_source(record: dict | None) -> str:
    if record_skill_duration_ms(record) is not None:
        return timing_source_text(record)
    if is_nested_timing_record(record):
        return "嵌套子 Skill 时间无效，不使用会话总时间冒充"
    if cyou_fallback_duration_ms() is not None:
        return "本地 Skill 时间无效，按会话总时间扣除两个环境过滤时间"
    return "本地 Skill 时间和会话时长均不可用，上报 0"


def format_ms_value(value_ms) -> str:
    if value_ms is None:
        return "未读取"
    try:
        number = max(0, int(value_ms))
    except (TypeError, ValueError):
        return "无效值"
    return f"{number} ms（{round(number / 1000, 3)} 秒）"


def is_nested_timing_record(record: dict | None) -> bool:
    return bool(record and str(record.get("parent_invocation_id") or "").strip())


def timing_env_detail(record: dict | None, current_key: str, start_key: str, end_key: str) -> str:
    if record:
        start_value = record.get(start_key)
        end_value = record.get(end_key)
        if start_value is None and end_value is None:
            return "未读取（未参与本地耗时计算）"
        if start_value is None or end_value is None:
            return "起止值不完整（未参与本地耗时计算）"
        start_text = format_ms_value(start_value)
        end_text = format_ms_value(end_value)
        try:
            delta = max(0, int(end_value) - int(start_value))
            delta_text = f"；本次变化量={format_ms_value(delta)}"
        except (TypeError, ValueError):
            delta_text = "；本次变化量无法计算"
        if is_nested_timing_record(record):
            delta_text += "（子 Skill 不扣除该变化量，由父 Skill 统一处理）"
        return f"开始={start_text}；结束={end_text}{delta_text}"

    current_value = skill_timing_env_snapshot().get(current_key)
    return f"当前值={format_ms_value(current_value)}"


def raw_skill_span_text(record: dict | None) -> str:
    if not record:
        return "不可用"
    raw_ms = skill_timing_duration_ms(
        record.get("skill_start_time"),
        record.get("skill_end_time"),
    )
    return format_ms_value(raw_ms) if raw_ms is not None else "不可用"


def timing_calculation_formula(record: dict | None, final_ms: int) -> str:
    raw_ms = None
    if record:
        raw_ms = skill_timing_duration_ms(
            record.get("skill_start_time"),
            record.get("skill_end_time"),
        )
    if raw_ms is not None:
        source = str(record.get("duration_source") or "")
        if source == "nested_skill_span_raw":
            return f"{raw_ms} ms = {final_ms} ms（子 Skill 原始耗时，环境过滤由父 Skill 统一处理）"
        if source == "skill_span_minus_environment_deltas":
            approval_start = record.get("approval_at_start_ms")
            approval_end = record.get("approval_at_end_ms")
            condense_start = record.get("condense_at_start_ms")
            condense_end = record.get("condense_at_end_ms")
            if all(isinstance(item, int) for item in (
                approval_start,
                approval_end,
                condense_start,
                condense_end,
            )):
                approval_delta = max(0, approval_end - approval_start)
                condense_delta = max(0, condense_end - condense_start)
                return f"max(0, {raw_ms} ms - {approval_delta} ms - {condense_delta} ms) = {final_ms} ms"
        return f"{raw_ms} ms = {final_ms} ms"

    if is_nested_timing_record(record):
        return "子 Skill 起止时间不可用，不使用会话累计时间，最终为 0 ms"

    values = cyou_time_environment_values()
    if values is not None:
        session_ms, approval_ms, condense_ms = values
        return f"max(0, {session_ms} ms - {approval_ms} ms - {condense_ms} ms) = {final_ms} ms"
    return "无有效 Skill 时间，也无可用会话时间，最终为 0 ms"


def timing_source_text(record: dict | None) -> str:
    if not record:
        return "未找到有效的 Skill 时间记录"
    source = str(record.get("duration_source") or "")
    if source == "nested_skill_span_raw":
        return "子 Skill 原始起止时间，环境过滤由父 Skill 统一处理"
    if source == "nested_skill_timing_unavailable":
        return "子 Skill 起止时间无效，不使用会话总时间回退"
    if source == "skill_span_minus_environment_deltas":
        return "已扣除本时间段内的审批等待和上下文压缩时间"
    if source == "skill_span_without_available_environment_deltas":
        return "未读取到完整 Cyou 时间环境变量，按本地 Skill 时间计算，未做扣除"
    if source == "session_duration_minus_environment_filters":
        return "本地 Skill 时间无效，使用会话总时间并扣除两个环境过滤时间"
    if source == "session_duration_fallback":
        return "历史计时记录使用未过滤的 CYOU_SESSION_DURATION_MS 回退值"
    if source == "unavailable":
        return "本地 Skill 时间和会话时长均不可用"
    if source == "started":
        return "Skill 尚未结束，暂未计算"
    return source or "未说明"


def timing_calculation_reason(record: dict | None) -> str:
    env_text = "、".join(f"`{name}`" for name in CYOU_TIME_ENV_NAMES)
    active_ms = record_skill_duration_ms(record)

    if is_nested_timing_record(record):
        if active_ms is None:
            return (
                "本记录属于 Workflow 的嵌套子 Skill，未形成有效的 `skill_start` 和 `skill_end`；"
                "由于会话环境变量覆盖整个会话，不能用会话总时间冒充该子 Skill，最终不计入耗时。"
            )
        return (
            "本记录属于 Workflow 的嵌套子 Skill，报告只展示其完整的本地起止时间；"
            "会话环境变量不在子 Skill 层扣除，统一由父 Skill 在最终上报时处理。"
        )

    # The converter uses the Cyou session values when a local Skill duration
    # is missing or invalid.  The report must explain that same fallback and
    # must never display a misleading "无法确定" message for an upload that
    # will actually receive a numeric duration.
    if active_ms is None:
        if cyou_fallback_duration_ms() is not None:
            return (
                f"本次没有形成有效的 `skill_start` 和 `skill_end`，但读取到 {env_text} 三个环境变量；"
                "因此改用会话总时间，并扣除审批等待和上下文压缩时间。"
            )
        return (
            f"本次没有形成有效的 `skill_start` 和 `skill_end`，也未读取到 {env_text} 三个环境变量；"
            "因此日志上报耗时记为 0。"
        )

    source = str(record.get("duration_source") or "") if record else ""
    if source == "skill_span_minus_environment_deltas":
        return (
            f"本次已正常记录 `skill_start` 和 `skill_end`，并读取到 {env_text} 三个环境变量；"
            "因此以上报的 Skill 起止时间为基础，扣除了本时间段内的审批等待和上下文压缩时间。"
        )
    if source == "skill_span_without_available_environment_deltas":
        return (
            f"本次已正常记录 `skill_start` 和 `skill_end`，但未读取到完整的 {env_text}；"
            "因此直接使用完整的本地 Skill 时间，没有进行环境时间过滤。"
        )
    if source == "session_duration_minus_environment_filters":
        return (
            f"本次没有形成有效的 `skill_start` 和 `skill_end`，但读取到 {env_text} 三个环境变量；"
            "因此改用会话总时间，并扣除审批等待和上下文压缩时间。"
        )
    if source == "session_duration_fallback":
        return "本次使用了历史计时记录中的会话总时间回退值。"
    return f"本次按 timing JSON 中标记的 `{source or '未知'}` 方式计算。"


def status_bucket(status: str) -> str:
    status = str(status or "").strip()
    if status in PASS_STATUSES:
        return "passed"
    if status in FAIL_STATUSES:
        return "failed"
    if status in BLOCK_STATUSES:
        return "blocked"
    if status in INCONCLUSIVE_STATUSES:
        return "test_inconclusive"
    return "blocked" if status else "blocked"


def final_case_records(records: list[dict]) -> dict[str, dict]:
    result = {}
    for record in records:
        case_id = str(value(record, "case_id", "c", "") or "")
        if not case_id:
            continue
        result[case_id] = record
    return result


def expected_functional_case_ids(records: list[dict]) -> set[str] | None:
    """Return the input-derived functional CaseId baseline if the run logged one."""
    for record in records:
        if value(record, "event", "a", "") != "classify":
            continue
        item = details(record)
        raw = (
            item.get("functional_case_ids")
            or item.get("functional_cases")
            or item.get("case_ids")
            or item.get("cases")
        )
        if isinstance(raw, list):
            return {str(case_id) for case_id in raw if str(case_id).strip()}
        if isinstance(raw, str):
            parts = re.split(r"[,;\s]+", raw)
            return {part for part in parts if part}
    return None


def evidence_items(record: dict) -> list[str]:
    result: list[str] = []
    for key in ("evidence", "evidence_path", "evidence_paths", "screenshot", "snapshot"):
        item = record.get(key)
        if isinstance(item, list):
            result.extend(str(x) for x in item if x)
        elif item:
            result.append(str(item))
    ev = record.get("ev")
    if isinstance(ev, list):
        result.extend(str(x) for x in ev if x)
    elif ev:
        result.append(str(ev))
    item = details(record)
    for key in ("evidence", "evidence_path", "screenshot", "snapshot", "scene_snapshot"):
        value_item = item.get(key)
        if isinstance(value_item, list):
            result.extend(str(x) for x in value_item if x)
        elif value_item:
            result.append(str(value_item))
    return [x.strip() for x in result if str(x).strip()]


def case_assertion_markers(record: dict) -> list[str]:
    item = details(record)
    markers = []
    for key in (
        "actual", "expected", "assertion", "assertions", "run_tc", "run_tc_result",
        "ops", "ops_executed", "operation", "before", "after", "state_delta",
        "click_result", "verify_result", "mcp_result",
    ):
        if item.get(key):
            markers.append(key)
    return markers


def case_mapped_batch_assertion(record: dict) -> bool:
    """Accept display/read-only cases that map a shared batch read to a case target."""
    action = str(value(record, "event", "a", "") or "").strip()
    if action not in {"verify", "snapshot", "read", "inspect"}:
        return False
    target = str(value(record, "target", "t", "") or "").strip()
    reason = str(value(record, "reason", "why", "") or "").strip()
    evidence = evidence_items(record)
    if not target or not evidence:
        return False
    text = " ".join(evidence + [reason, target]).lower()
    weak_targets = {"ui", "root", "summary", "group", "state", "verify"}
    if target.lower() in weak_targets:
        return False
    return bool(reason or any(sep in text for sep in ("=", ":", "|", ";", ",")))


def validate_case_records(case_records: dict[str, dict]) -> tuple[dict[str, dict], list[dict]]:
    """Downgrade impossible passed records before counting.

    The renderer is the last gate before Markdown/upload JSON. A passed case must have
    evidence mapped to its case. Display/read-only cases may share one batch read when
    each record names its own target/assertion; interaction cases still need operation
    or state-change markers.
    """
    evidence_owner: dict[str, set[str]] = defaultdict(set)
    for case_id, record in case_records.items():
        if status_bucket(value(record, "status", "r", "")) != "passed":
            continue
        for evidence in evidence_items(record):
            evidence_owner[evidence].add(case_id)

    validated: dict[str, dict] = {}
    issues: list[dict] = []
    for case_id, record in case_records.items():
        copied = dict(record)
        if status_bucket(value(record, "status", "r", "")) == "passed":
            evidence = evidence_items(record)
            duplicate_evidence = [item for item in evidence if len(evidence_owner[item]) > 1]
            markers = case_assertion_markers(record)
            mapped_batch = case_mapped_batch_assertion(record)
            weak_reasons = []
            if not evidence and not markers and not mapped_batch:
                weak_reasons.append("passed 缺少 case-scoped 证据和断言明细")
            if duplicate_evidence and not markers and not mapped_batch:
                weak_reasons.append("passed 复用同一证据且缺少独立断言明细")
            summary = str(details(record).get("summary", "") or "")
            if summary and not evidence and not markers and not mapped_batch:
                weak_reasons.append("仅有分组 summary，不能证明单用例通过")
            if weak_reasons:
                copied["status"] = "blocked"
                copied["reason"] = "; ".join(weak_reasons)
                copied.setdefault("details", {})
                if isinstance(copied["details"], dict):
                    copied["details"] = dict(copied["details"])
                    copied["details"]["renderer_guard"] = "downgraded_from_passed"
                issues.append({"case_id": case_id, "reason": copied["reason"]})
        validated[case_id] = copied
    return validated, issues


def pipe_field(text: object, field: str) -> str:
    text = "" if text is None else str(text)
    marker = f"{field}="
    for part in text.split("|"):
        if part.startswith(marker):
            return part[len(marker):].strip()
    return ""


def evidence_summary(record: dict) -> str:
    reason = str(value(record, "reason", "why", "") or "")
    status = status_bucket(value(record, "status", "r", ""))
    if reason:
        return reason
    if status in {"failed", "blocked", "test_inconclusive"}:
        return "AI失败归因缺失：最终记录未写入自然语言原因"
    item = details(record)
    for key in ("summary", "actual", "result", "compile_result", "invoke"):
        if item.get(key):
            return str(item[key])
    event = value(record, "event", "a", "")
    target = value(record, "target", "t", "")
    status = value(record, "status", "r", "")
    text = " / ".join(str(x) for x in (event, target, status) if x)
    return text or "无"


def icon_status(status: str) -> str:
    bucket = status_bucket(status)
    if bucket == "passed":
        return "passed"
    if bucket == "failed":
        return "failed"
    if bucket == "test_inconclusive":
        return "test_inconclusive"
    return "blocked"


def md_escape(text) -> str:
    text = "" if text is None else str(text)
    return text.replace("|", "\\|").replace("\n", "<br>")


def case_sort_key(case_id: str):
    numbers = re.findall(r"\d+", case_id)
    return [int(x) for x in numbers] if numbers else [case_id]


def repair_round_records(records: list[dict]) -> list[tuple[int, dict]]:
    """Return one record per completed repair round in this run.

    A completed repair round is represented by one verified `event=fix` record.
    Compile and rerun/retry records belong to that round and must not increment
    it again. An attempted but unverified repair is deliberately excluded.
    When the orchestration supplies a positive details.fix_round, use that
    run-level number to deduplicate multiple records from the same round.
    """
    candidates = []
    for record in records:
        event = str(value(record, "event", "a", "") or "").strip().lower()
        if event != "fix":
            continue
        item = details(record)
        issue_action = str(item.get("issue_action", "") or "").strip().lower()
        fix_verified = item.get("fix_verified", False)
        status = status_bucket(value(record, "status", "r", ""))
        if issue_action != "fixed" or fix_verified is not True or status != "passed":
            continue
        round_value = item.get("fix_round", 0)
        try:
            round_value = int(round_value or 0)
        except (TypeError, ValueError):
            round_value = 0
        candidates.append((round_value, record))

    explicit = [(round_value, record) for round_value, record in candidates if round_value > 0]
    if explicit:
        grouped = {}
        for round_value, record in explicit:
            grouped.setdefault(round_value, record)
        return sorted(grouped.items(), key=lambda item: item[0])

    return [(index, record) for index, (_, record) in enumerate(candidates, 1)]


def repair_round_count(records: list[dict]) -> int:
    rounds = repair_round_records(records)
    return len(rounds)


def structured_issue_records(records: list[dict]) -> list[dict]:
    """Return complete issue events that are associated with a real verdict.

    A blocked or inconclusive event describes an execution limitation, not a
    Bug. A located issue is tied to a failed observation; a fix event may be a
    failed repair attempt or a passed verification. This also permits several
    issue IDs to point to the same failed Case.
    """
    result = []
    for record in records:
        item = details(record)
        event = str(value(record, "event", "a", "") or "").strip().lower()
        issue_id = str(item.get("issue_id", "") or "").strip()
        action = str(item.get("issue_action", "") or "").strip().lower()
        issue_description = str(
            item.get("issue_description") or value(record, "reason", "why", "") or ""
        ).strip()
        root_cause = str(item.get("root_cause", "") or "").strip()
        target = str(value(record, "target", "t", "") or "").strip()
        evidence = value(record, "evidence", "e", [])
        if isinstance(evidence, str):
            has_evidence = bool(evidence.strip())
        elif isinstance(evidence, list):
            has_evidence = any(str(entry or "").strip() for entry in evidence)
        else:
            has_evidence = bool(evidence)
        status = status_bucket(value(record, "status", "r", ""))
        valid_status = (action == "located" and status == "failed") or (
            action == "fixed" and status in {"failed", "passed"}
        )
        if (
            event not in {"verify", "fix"}
            or not issue_id
            or action not in {"located", "fixed"}
            or not issue_description
            or not root_cause
            or not target
            or not has_evidence
            or not valid_status
        ):
            continue
        result.append(record)
    return result


def issue_counts(records: list[dict]) -> tuple[int, int]:
    """Count located and verified-fixed issue IDs separately."""
    located_ids = set()
    fixed_ids = set()
    for record in structured_issue_records(records):
        item = details(record)
        issue_id = str(item.get("issue_id", "") or "").strip()
        action = str(item.get("issue_action", "") or "").strip().lower()
        if action == "located":
            located_ids.add(issue_id)
        verified = item.get("fix_verified") is True or str(item.get("fix_verified", "")).lower() == "true"
        if action == "fixed" and verified and status_bucket(value(record, "status", "r", "")) == "passed":
            fixed_ids.add(issue_id)
    return len(located_ids), len(fixed_ids)


def history_summary(
    run_dir: Path,
    feature_id: str,
    passed: int,
    failed: int,
    blocked: int,
    inconclusive: int,
) -> str:
    match = re.match(r"^(.*)-(\d{4})$", run_dir.name)
    if not match:
        return "无法对比（当前目录名不含序号）"
    prefix, seq_text = match.groups()
    current_seq = int(seq_text)
    candidates = []
    for item in run_dir.parent.glob(f"{prefix}-[0-9][0-9][0-9][0-9]"):
        m = re.match(rf"^{re.escape(prefix)}-(\d{{4}})$", item.name)
        if item.is_dir() and m and int(m.group(1)) < current_seq:
            candidates.append((int(m.group(1)), item))
    if not candidates:
        return "无可对比历史运行"
    _, previous = sorted(candidates)[-1]
    records = read_jsonl(previous / f"{previous.name}-run-log.json")
    if not records:
        return f"上一轮 {previous.name} 无 run-log，无法对比"
    raw_cases = final_case_records(records)
    cases, _ = validate_case_records(raw_cases)
    stats = Counter(status_bucket(value(record, "status", "r", "")) for record in cases.values())
    dp = passed - stats["passed"]
    df = failed - stats["failed"]
    db = blocked - stats["blocked"]
    di = inconclusive - stats["test_inconclusive"]
    return (
        f"对比 {previous.name}：passed {stats['passed']}→{passed} ({dp:+d})，"
        f"failed {stats['failed']}→{failed} ({df:+d})，"
        f"blocked {stats['blocked']}→{blocked} ({db:+d})，"
        f"test_inconclusive {stats['test_inconclusive']}→{inconclusive} ({di:+d})"
    )


def blocked_category(record: dict) -> str:
    text = " ".join(
        str(x or "") for x in (
            value(record, "reason", "why", ""),
            details(record).get("assertion", ""),
            details(record).get("run_tc_result", ""),
        )
    )
    if any(key in text for key in ("强关联", "上游用例", "前置用例失败", "依赖用例")):
        return "强关联前置用例失败"
    if any(key in text for key in ("编译", "PlayMode", "MCP", "环境不可用", "工具不可用", "登录失败")):
        return "环境或关键前置不可用"
    if any(key in text for key in ("detail_open=false", "详情", "HeroGrow")):
        return "详情链路未验证"
    if any(key in text for key in ("前置", "数据", "边界", "不满足")):
        return "关键前置条件不足"
    if any(key in text for key in ("断言", "no case-scoped", "无法构造")):
        return "独立断言不足"
    if any(key in text for key in ("not_found", "root_not_found", "路径", "节点未找到")):
        return "路径或节点定位问题"
    if any(key in text for key in ("timeout", "超时", "等待")):
        return "等待或异步状态未达成"
    return "其他阻塞"


def blocked_category_summary(case_records: dict[str, dict]) -> dict[str, list[tuple[str, dict]]]:
    result: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for case_id, record in case_records.items():
        if status_bucket(value(record, "status", "r", "")) == "blocked":
            result[blocked_category(record)].append((case_id, record))
    return result


def correction_suggestion(category: str) -> str:
    suggestions = {
        "强关联前置用例失败": "先处理上游 failed 用例；其直接依赖用例保持 blocked，待上游修复并复测后再执行。",
        "环境或关键前置不可用": "恢复编译、PlayMode、登录或 MCP 等关键执行条件后复测。",
        "详情链路未验证": "优先修正英雄卡牌点击路径或改用 Logic 回调，并补充详情页 active/字段断言后复测详情组。",
        "关键前置条件不足": "先准备可构造的测试账号数据或 GM 前置；若目标异常/边界条件仍无法合理构造，应改记 test_inconclusive。",
        "独立断言不足": "为该组补 before/after 状态差异、运行时字段读取或 RunTC 断言，避免只用界面存在性判定。",
        "路径或节点定位问题": "更新 UI 参考路径或 TestHelper opMap，运行时确认节点后再复测。",
        "等待或异步状态未达成": "将触发动作与状态确认拆成跨帧短轮询，记录真实超时与最终状态。",
        "其他阻塞": "人工复核 blocked reason，确认是否能转成可执行断言或需要保持 blocked。",
    }
    return suggestions.get(category, suggestions["其他阻塞"])


def render_report(
    run_dir: Path,
    output: Path | None = None,
    allow_overwrite: bool = False,
    timing_file: Path | None = None,
    skill_name: str = "unity-functiontest",
) -> Path:
    run_name = run_dir.name
    run_log = run_dir / f"{run_name}-run-log.json"
    known_issues = run_dir / f"{run_name}-known-issues.json"
    report_path = output or run_dir / f"{run_name}-unity-functiontest-report.md"
    if report_path.exists() and not allow_overwrite:
        raise ValueError(
            "refusing to overwrite existing FunctionTest report without explicit retest/overwrite permission: "
            f"run_dir={run_dir} output={report_path}"
        )

    records = read_jsonl(run_log)
    if not records:
        raise ValueError(f"run-log has no records: {run_log}")

    # Guard against accidentally rendering an apparently successful but empty report.
    # This usually means the executor wrote events to a mojibake/wrong path or failed
    # to append realtime per-case records before invoking the renderer. Producing a
    # zero-case "通过" report is dangerous because downstream conversion/upload treats
    # it as a valid result. Fail fast instead so the workflow stops at report render.
    case_event_count = sum(1 for r in records if value(r, "case_id", "c", ""))
    has_classification_count = any(
        value(r, "event", "a", "") == "classify"
        and int(details(r).get("total") or details(r).get("functional") or 0) > 0
        for r in records
    )
    if case_event_count == 0 and not has_classification_count:
        raise ValueError(
            "refusing to render empty FunctionTest report: "
            f"run-log has {len(records)} event(s), no case_id records, and no non-empty classify summary: {run_log}"
        )

    feature_id = infer_feature_id(run_name, records)
    raw_case_records = final_case_records(records)
    expected_cases = expected_functional_case_ids(records)
    if expected_cases is None and raw_case_records:
        raise ValueError(
            "refusing to render FunctionTest report without classify baseline: "
            "run-log has case records but no event=classify details.functional_case_ids. "
            "Run unity-functiontest from input-case parsing and write the input-derived case baseline first."
        )
    if expected_cases:
        missing_cases = sorted(expected_cases - set(raw_case_records), key=case_sort_key)
        if missing_cases:
            preview = ", ".join(missing_cases[:20])
            if len(missing_cases) > 20:
                preview += f" ... (+{len(missing_cases) - 20})"
            raise ValueError(
                "refusing to render partial FunctionTest report: "
                f"{len(missing_cases)} functional case(s) from classify baseline have no realtime final record: {preview}"
            )
    case_records, guard_issues = validate_case_records(raw_case_records)
    case_counts = Counter(status_bucket(value(record, "status", "r", "")) for record in case_records.values())
    event_counts = Counter(status_bucket(value(record, "status", "r", "")) for record in records)
    classify_details = next(
        (details(record) for record in records if value(record, "event", "a", "") == "classify"),
        {},
    )
    non_functional_ids = classify_details.get("non_functional_case_ids") or classify_details.get("non_functional_cases") or []
    if isinstance(non_functional_ids, list):
        non_functional = len([case_id for case_id in non_functional_ids if str(case_id).strip()])
    else:
        non_functional = int(classify_details.get("non_functional") or 0)
    functional_total = len(case_records)
    total_cases = functional_total + non_functional
    blocked_total = case_counts["blocked"]
    failed_total = case_counts["failed"]
    passed_total = case_counts["passed"]
    inconclusive_total = case_counts["test_inconclusive"]

    lifecycle_start, lifecycle_end = lifecycle_bounds(records)
    validate_query_log_contract(records)
    root_timing, timing_records, resolved_timing_file = skill_timing_summary(
        run_dir, timing_file, skill_name
    )
    compile_records = [r for r in records if value(r, "event", "a") == "compile"]
    compile_status = value(compile_records[-1], "status", "r", "未记录") if compile_records else "未记录"
    if failed_total > 0:
        overall = "失败" if passed_total == 0 else "部分通过"
    elif blocked_total > 0:
        overall = "阻塞" if passed_total == 0 else "部分通过"
    elif inconclusive_total > 0:
        overall = "测试结论不完整"
    else:
        overall = "通过"
    fix_records = repair_round_records(records)
    fix_round_count = repair_round_count(records)
    bug_count, fixed_issue_count = issue_counts(records)
    issue_records = structured_issue_records(records)
    history_text = history_summary(
        run_dir, feature_id, passed_total, failed_total, blocked_total, inconclusive_total
    )
    blocked_categories = blocked_category_summary(case_records)
    inconclusive_records = [
        (case_id, record)
        for case_id, record in case_records.items()
        if status_bucket(value(record, "status", "r", "")) == "test_inconclusive"
    ]
    diff_reports = ui_image_diff_reports(run_dir)
    diff_events = ui_image_diff_events(records)

    lines = []
    lines.append("# Functional Test Report")
    lines.append("")
    lines.append("## 1. 任务概览")
    first_details = details(records[0])
    input_display = first_details.get("input") or first_details.get("input_path") or value(records[0], "target", "t", "")
    lines.append(f"- 输入：{md_escape(input_display)}")
    lines.append(f"- feature_id：{feature_id}")
    lines.append(f"- run_dir：{run_name}")
    lines.append(
        f"- 用例总数：{total_cases}（functional = {functional_total} / 非功能测试范围 = {non_functional} / "
        f"passed = {passed_total} / failed = {failed_total} / blocked = {blocked_total} / "
        f"test_inconclusive = {inconclusive_total}）"
    )
    lines.append(f"- 启动前编译检查：{compile_status}")
    upload_duration_ms = report_duration_ms(root_timing)
    upload_duration_text = f"{round(upload_duration_ms / 1000, 3)} 秒"
    if root_timing:
        lines.append(f"- Skill 开始时间：{md_escape(root_timing.get('skill_start_time', '')) or '未记录'}")
        lines.append(f"- Skill 结束时间：{md_escape(root_timing.get('skill_end_time', '')) or '未记录'}")
        lines.append(f"- Skill 有效耗时：{upload_duration_text}（{report_duration_source(root_timing)}）")
    else:
        lines.append(f"- Skill 有效耗时：{upload_duration_text}（{report_duration_source(None)}）")
    if guard_issues:
        lines.append(f"- 证据门禁：已将 {len(guard_issues)} 条缺少独立证据的 passed 记录降级为 blocked")
    lines.append(f"- 自动修复轮次：{fix_round_count}")
    lines.append(f"- 定位Bug数：{bug_count}")
    lines.append(f"- 修复问题数：{fixed_issue_count}")
    lines.append(f"- 历史对比：{history_text}")
    lines.append("")
    lines.append("### 1.1 Skill 时间明细")
    lines.append("")
    lines.append("- 根 Skill 的耗时按规则处理环境时间；带有 `parent_invocation_id` 的子 Skill 只展示原始起止时间，环境过滤由父 Skill 统一处理。")
    lines.append("")
    if timing_records:
        lines.append("| Skill | 开始时间 | 结束时间 | 有效耗时 | 时长来源 | 状态 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in timing_records:
            value_ms = item.get("skill_active_duration_ms")
            value_text = "未计算" if value_ms is None else f"{round(int(value_ms) / 1000, 3)} 秒"
            lines.append(
                f"| {md_escape(item.get('skill_name', ''))} | "
                f"{md_escape(item.get('skill_start_time', ''))} | "
                f"{md_escape(item.get('skill_end_time', ''))} | {value_text} | "
                f"{md_escape(timing_source_text(item))} | {md_escape(item.get('status', ''))} |"
            )
    else:
        lines.append("- 未记录业务 Skill 时间。")
    lines.append("")
    lines.append("### 1.2 日志上报耗时计算")
    lines.append("")
    lines.append(f"- 本次上报业务 Skill：`{md_escape(skill_name)}`")
    if root_timing:
        start_text = md_escape(root_timing.get("skill_start_time", "")) or "未记录"
        end_text = md_escape(root_timing.get("skill_end_time", "")) or "未记录"
    else:
        start_text = "未记录"
        end_text = "未记录"
    lines.append(f"- Skill 开始时间：{start_text}")
    lines.append(f"- Skill 结束时间：{end_text}")
    lines.append(f"- Skill 原始耗时（结束时间 - 开始时间）：{raw_skill_span_text(root_timing)}")
    for env_name, current_key, start_key, end_key in CYOU_TIME_ENV_FIELDS:
        lines.append(f"- `{env_name}`：{timing_env_detail(root_timing, current_key, start_key, end_key)}")
    lines.append(f"- 本次实际用于上报的耗时：{upload_duration_text}")
    lines.append(f"- 计算过程：{timing_calculation_formula(root_timing, upload_duration_ms)}")
    lines.append(f"- 本次计算原因：{md_escape(timing_calculation_reason(root_timing))}")
    lines.append("- run-log 生命周期记录和各步骤 `duration_ms` 不参与日志上报耗时计算。")
    lines.append("")
    lines.append("### 1.3 用例分类说明（必须）")
    lines.append("")
    lines.append("| 分类 | 数量 | 含义 | 处理方式 |")
    lines.append("|------|------|------|----------|")
    lines.append(f"| functional | {functional_total} | UI 交互/状态验证/操作流程 | 按运行日志记录渲染 |")
    lines.append(f"| 非功能测试范围 | {non_functional} | 纯逻辑/数据公式、多端同步、响应时间测量 | 不属于 UI 功能测试，MCP 不执行 |")
    lines.append(f"| blocked | {blocked_total} | 环境、数据、路径或执行条件阻塞 | 标记为 blocked 并保留原因 |")
    lines.append(f"| test_inconclusive | {inconclusive_total} | 测试条件无法合理构建，当前证据不足以下结论 | 上报为 invalid_case_count，不计入 failure_case_count |")
    lines.append("")
    lines.append("## 2. 用例与结果（逐条列出，按分组排序，一目了然）")
    lines.append("")
    lines.append("| 分组 | CaseId | Verdict | 关键证据 |")
    lines.append("| --- | --- | --- | --- |")
    by_group = defaultdict(list)
    for case_id, record in case_records.items():
        group = details(record).get("group") or details(record).get("group_id") or "default"
        by_group[str(group)].append((case_id, record))
    for group in sorted(by_group):
        first = True
        for case_id, record in sorted(by_group[group], key=lambda item: case_sort_key(item[0])):
            group_text = group if first else ""
            first = False
            status = icon_status(value(record, "status", "r", ""))
            lines.append(f"| {md_escape(group_text)} | {md_escape(case_id)} | {status} | {md_escape(evidence_summary(record))} |")
    lines.append("")
    lines.append(
        f"> 汇总：functional passed = {passed_total} 条，failed = {failed_total} 条，"
        f"blocked = {blocked_total} 条，test_inconclusive = {inconclusive_total} 条；"
        f"非功能测试范围 = {non_functional} 条（不执行）"
    )
    lines.append("")
    lines.append("### 2.1 分组汇总（分组 → 用例数量 + verdict 统计）")
    lines.append("")
    lines.append("| 分组 | 用例数 | passed | failed | blocked | test_inconclusive | 说明 |")
    lines.append("|------|--------|--------|--------|---------|-------------------|------|")
    for group in sorted(by_group):
        stats = Counter(status_bucket(value(record, "status", "r", "")) for _, record in by_group[group])
        lines.append(
            f"| {md_escape(group)} | {len(by_group[group])} | {stats['passed']} | {stats['failed']} | "
            f"{stats['blocked']} | {stats['test_inconclusive']} | 来自 run-log |"
        )
    if not by_group:
        lines.append("| default | 0 | 0 | 0 | 0 | 0 | run-log 未记录 case |")
    lines.append("")
    lines.append("## 3. 节点证据摘要（每用例关键 Unity 元素状态）")
    lines.append("")
    lines.append("| CaseId | UI节点 | activeInHierarchy | GameText | 子节点数 | 备注 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for case_id, record in sorted(case_records.items(), key=lambda item: case_sort_key(item[0])):
        item = details(record)
        lines.append(
            f"| {md_escape(case_id)} | {md_escape(value(record, 'target', 't', ''))} | {md_escape(item.get('node_active', ''))} | {md_escape(item.get('game_text', ''))} | {md_escape(item.get('child_count', ''))} | {md_escape(evidence_summary(record))} |"
        )
    if not case_records:
        lines.append("| 无 | 无 |  |  |  | run-log 未记录 case |")
    lines.append("")
    lines.append("### 3.1 效果图对比")
    lines.append("")
    lines.append("效果图与 UILogicManager.xlsx 均按当前 UIName 和当前工作区实时定位；reference 不提供任何表格或效果图路径缓存。")
    if diff_reports:
        lines.append("本轮已生成以下对比报告（每个 UI 最多一份）：")
        lines.append("")
        lines.append("| UI | 对比报告 |")
        lines.append("| --- | --- |")
        for diff_report in diff_reports:
            try:
                relative_report = diff_report.relative_to(run_dir).as_posix()
            except ValueError:
                relative_report = diff_report.as_posix()
            lines.append(f"| {md_escape(diff_report.stem)} | `{md_escape(relative_report)}` |")
    elif diff_events:
        lines.append("本轮未生成有效对比报告，记录的处理结果如下：")
        for record in diff_events:
            item = details(record)
            ui_name = item.get("ui_name") or value(record, "target", "t", "") or "未识别 UI"
            reason = item.get("reason") or item.get("skip_reason") or evidence_summary(record)
            lines.append(f"- {md_escape(ui_name)}：{md_escape(reason)}")
    else:
        lines.append("本轮未生成效果图对比报告：可能未开启效果图对比、未配置有效基准图，或未形成可比较的稳定截图。")
    lines.append("")
    lines.append("## 4. 问题、阻塞与未定论归因")
    problem_records = [
        r for r in records
        if value(r, "event", "a", "") not in {"verify", "fix"}
        and (
            status_bucket(value(r, "status", "r", "")) in {"failed", "blocked"}
            or int(value(r, "duration_ms", "d", 0) or 0) > 8000
        )
    ]
    for issue in guard_issues:
        problem_records.append({
            "case_id": issue["case_id"],
            "event": "renderer_guard",
            "status": "blocked",
            "reason": issue["reason"],
            "duration_ms": 0,
        })
    if problem_records:
        for record in problem_records:
            lines.append(
                f"- {md_escape(value(record, 'case_id', 'c', '') or value(record, 'step_id', 'id', ''))}：{md_escape(evidence_summary(record))} / status={md_escape(value(record, 'status', 'r', ''))}"
            )
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("### 4.1 结构化 Bug 记录")
    lines.append("Bug 数量按已定位事件中去重后的 issue_id 统计；fixed 事件不重复增加 Bug 数，blocked 和 test_inconclusive 不计入。一个 failed Case 可以关联多个 issue_id。")
    if issue_records:
        lines.append("| issue_id | 关联 Case | 问题描述 | 根因 | 事件状态 | 证据 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for record in issue_records:
            item = details(record)
            source_case_id = item.get("source_case_id") or value(record, "case_id", "c", "") or "运行级"
            description = item.get("issue_description") or value(record, "reason", "why", "")
            lines.append(
                f"| {md_escape(item.get('issue_id', ''))} | {md_escape(source_case_id)} | "
                f"{md_escape(description)} | {md_escape(item.get('root_cause', ''))} | "
                f"{md_escape(value(record, 'status', 'r', ''))} | {md_escape(evidence_summary(record))} |"
            )
    else:
        lines.append("- 无结构化 Bug 记录")
    lines.append("")
    lines.append("### 4.2 自动修复记录（有 failed 用例时必填）")
    if fix_records:
        lines.append("| 轮次 | CaseId | 失败原因 | 修复说明 | 重测 verdict | 备注 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for round_value, record in fix_records:
            lines.append(f"| 第{round_value}轮 | {md_escape(value(record, 'case_id', 'c', ''))} | {md_escape(value(record, 'reason', 'why', ''))} | {md_escape(evidence_summary(record))} | {md_escape(value(record, 'status', 'r', ''))} | 来自 run-log |")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("### 4.3 阻塞原因分类")
    if blocked_categories:
        lines.append("| 分类 | 数量 | 示例 CaseId | 处理建议 |")
        lines.append("| --- | --- | --- | --- |")
        for category in sorted(blocked_categories):
            items = sorted(blocked_categories[category], key=lambda item: case_sort_key(item[0]))
            examples = ", ".join(case_id for case_id, _ in items[:5])
            if len(items) > 5:
                examples += " ..."
            lines.append(f"| {md_escape(category)} | {len(items)} | {md_escape(examples)} | {md_escape(correction_suggestion(category))} |")
    else:
        lines.append("- 无 blocked 用例")
    lines.append("")
    lines.append("### 4.4 测试条件不足（test_inconclusive）")
    if inconclusive_records:
        lines.append("| CaseId | 原因 | 处理口径 |")
        lines.append("| --- | --- | --- |")
        for case_id, record in sorted(inconclusive_records, key=lambda item: case_sort_key(item[0])):
            lines.append(
                f"| {md_escape(case_id)} | {md_escape(evidence_summary(record))} | "
                "仅在本报告保留，不计入 success/failure/block 上报统计 |"
            )
    else:
        lines.append("- 无 test_inconclusive 用例")
    lines.append("")
    lines.append("### 4.5 下一轮可矫正项")
    if blocked_categories:
        for category in sorted(blocked_categories):
            lines.append(f"- {md_escape(category)}：{md_escape(correction_suggestion(category))}")
    else:
        lines.append("- 当前无 blocked 用例，无需矫正复测。")
    lines.append("")
    lines.append("## 5. 结论")
    lines.append(f"- 总体状态：{overall}")
    lines.append(
        f"- 汇总：passed = {passed_total}，failed = {failed_total}，blocked = {blocked_total}，"
        f"test_inconclusive = {inconclusive_total}（上报为 invalid_case_count）"
    )
    lines.append(f"- 历史对比：{history_text}")
    if blocked_categories:
        lines.append("- 下一步：优先处理 §4.3 中的可矫正项；未新增证据能力前，不建议仅重复复测。")
    else:
        lines.append("- 下一步：无阻塞项，按回归策略处理。")
    lines.append("")
    lines.append("## 6. 运行时错误日志")
    query_log_records = [r for r in records if value(r, "event", "a", "") == "query_logs"]
    if query_log_records:
        lines.append("| 序号 | 时间 | 类型 | 消息 | 堆栈 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for index, record in enumerate(query_log_records, 1):
            item = details(record)
            lines.append(f"| {index} | {md_escape(value(record, 'start_time', 'ts', ''))} | {md_escape(item.get('type', ''))} | {md_escape(item.get('message') or evidence_summary(record))} | {md_escape(item.get('stack_trace', ''))} |")
    else:
        lines.append("无错误日志或未记录 query_logs。")
    lines.append("")
    lines.append("## 7. 产物")
    lines.append(f"- run-log：{run_log}")
    lines.append(f"- known-issues：{known_issues}")
    lines.append(f"- report：{report_path}")
    for diff_report in diff_reports:
        lines.append(f"- ui-image-diff：{diff_report}")
    if resolved_timing_file:
        lines.append(f"- skill-timing：{resolved_timing_file}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Render Unity FunctionTest markdown report from fixed JSONL logs.")
    parser.add_argument("run_dir_or_log", help="Run directory or run-log path")
    parser.add_argument("--output", help="Optional output markdown path")
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow replacing an existing report; only valid for an explicitly requested retest/overwrite",
    )
    parser.add_argument(
        "--timing-file",
        help="Skill timing sidecar JSON；未指定时读取当前 run_dir 下的 *-skill-timing.json",
    )
    parser.add_argument(
        "--skill-name",
        default="unity-functiontest",
        help="报告主 Skill 名称；Workflow 报告应传 functiontest-workflow",
    )
    args = parser.parse_args()

    run_dir = infer_run_dir(Path(args.run_dir_or_log))
    output = Path(args.output).resolve() if args.output else None
    timing_file = Path(args.timing_file).resolve() if args.timing_file else None
    print(render_report(run_dir, output, args.allow_overwrite, timing_file, args.skill_name))


if __name__ == "__main__":
    main()
