#!/usr/bin/env python3
import argparse
import datetime as dt
import ipaddress
import json
import os
import re
import socket
import sys
from pathlib import Path

from skill_timing import load_records as load_skill_timing_records
from skill_timing import select_record as select_skill_timing_record


ALLOWED_UPLOAD_TOP_LEVEL = {"tool_stats_payload", "user_stats_payload"}
DEFAULT_OPERATION_TYPE = "主动测试工作流"
DEFAULT_AI_MODEL = "暂无数据"
AI_MODEL_ENV_VARS = (
    "CYOU_AI_MODEL",
    "CYOU_MODEL",
    "AI_MODEL",
    "MODEL_NAME",
)
OPERATION_TYPES = {
    "主动测试工作流",
    "质量部生成用例",
    "本地生成用例",
    "UI快速分析",
    "独立Unity功能测试",
}
OPERATION_SKILL_NAMES = {
    "主动测试工作流": "functiontest-workflow",
    "质量部生成用例": "testcase-mcp-complete",
    "本地生成用例": "testcase-gen",
    "UI快速分析": "ui-quick-reference",
    "独立Unity功能测试": "unity-functiontest",
}
WORKFLOW_CONFIG_PATH = Path(__file__).resolve().parents[2] / "functiontest-workflow" / "config.json"


def remove_unreported_top_level_fields(payload: dict) -> list[str]:
    """Keep the local upload artifact aligned with the two-field upload contract."""
    extra = sorted(set(payload) - ALLOWED_UPLOAD_TOP_LEVEL)
    for key in extra:
        payload.pop(key, None)
    return extra


def configure_utf8_stdio() -> None:
    """Keep Windows terminals from corrupting Chinese paths in script output."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def local_report_time() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def validate_operation_type(operation_type: str) -> str:
    value = str(operation_type or "").strip()
    if value not in OPERATION_TYPES:
        allowed = "、".join(sorted(OPERATION_TYPES))
        raise ValueError(f"操作类型必须是固定中文枚举之一：{allowed}；实际值={operation_type!r}")
    return value


def resolve_ai_model(args, current: str = "") -> str:
    """Resolve the model from an explicit value, then the runtime environment.

    The generated placeholder must not mask a model injected by the Cyou
    runtime during the later spend-merge step.
    """
    explicit = str(getattr(args, "ai_model", "") or "").strip()
    if explicit and explicit != DEFAULT_AI_MODEL:
        return explicit
    existing = str(current or "").strip()
    if existing and existing != DEFAULT_AI_MODEL:
        return existing
    for env_name in AI_MODEL_ENV_VARS:
        value = (os.getenv(env_name) or "").strip()
        if value:
            return value
    return DEFAULT_AI_MODEL


def ensure_operation_type(payload: dict, operation_type: str | None = None) -> str:
    user_metrics = payload["user_stats_payload"]["items"][0]["custom_metrics"]
    value = str(user_metrics.get("operation_type") or operation_type or DEFAULT_OPERATION_TYPE).strip()
    value = validate_operation_type(value)
    user_metrics["operation_type"] = value
    return value


def _env_float(name: str) -> float:
    value = os.getenv(name)
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _env_int(name: str) -> int:
    return int(_env_float(name))


def cyou_spend_snapshot() -> dict:
    return {
        "cyou_session_id": os.getenv("CYOU_SESSION_ID") or "",
        "cyou_task_id": os.getenv("CYOU_TASK_ID") or "",
        "cyou_turn_id": os.getenv("CYOU_TURN_ID") or "",
        "cyou_litellm_call_id": os.getenv("CYOU_LITELLM_CALL_ID") or "",
        "api_key_alias": os.getenv("CYOU_API_KEY_ALIAS") or "",
        "team_alias": os.getenv("CYOU_TEAM_ALIAS") or "",
        "session_spend_usd": _env_float("CYOU_SESSION_SPEND_USD"),
        "session_total_tokens": _env_int("CYOU_SESSION_TOTAL_TOKENS"),
        "session_duration_ms": _env_int("CYOU_SESSION_DURATION_MS"),
        "session_approval_duration_ms": _env_int("CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS"),
        "session_condense_duration_ms": _env_int("CYOU_SESSION_CONDENSE_DURATION_MS"),
    }


def _optional_env_ms(name: str) -> int | None:
    value = os.getenv(name)
    if value in (None, ""):
        return None
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return None


def cyou_filtered_session_duration_ms() -> int | None:
    """Return session time after both Cyou environment filters.

    The three timing variables are treated as one complete set.  If any of
    them is unavailable or invalid, there is no Cyou fallback value.
    """
    values = (
        _optional_env_ms("CYOU_SESSION_DURATION_MS"),
        _optional_env_ms("CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS"),
        _optional_env_ms("CYOU_SESSION_CONDENSE_DURATION_MS"),
    )
    if not all(isinstance(item, int) for item in values):
        return None
    session_ms, approval_ms, condense_ms = values
    return max(0, session_ms - approval_ms - condense_ms)


def resolve_timing_file(args, run_dir: Path | None = None) -> Path | None:
    explicit = str(getattr(args, "timing_file", "") or "").strip()
    if explicit:
        path = Path(explicit).resolve()
        return path if path.is_file() else None
    if run_dir is None:
        return None
    direct = run_dir / f"{run_dir.name}-skill-timing.json"
    if direct.is_file():
        return direct
    candidates = sorted(run_dir.glob("*-skill-timing.json"))
    return candidates[-1] if candidates else None


def timing_duration_ms(args, run_dir: Path | None = None) -> int | None:
    timing_file = resolve_timing_file(args, run_dir)
    if not timing_file:
        return None
    try:
        records = load_skill_timing_records(timing_file)
    except (OSError, ValueError):
        return None
    skill_name = str(getattr(args, "skill_name", "") or "").strip()
    if not skill_name:
        skill_name = OPERATION_SKILL_NAMES.get(str(getattr(args, "operation_type", "") or "").strip(), "")
    invocation_id = str(getattr(args, "invocation_id", "") or "").strip()
    record = select_skill_timing_record(records, skill_name=skill_name, invocation_id=invocation_id)
    if not record:
        return None
    value = record.get("skill_active_duration_ms")
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def set_duration_metrics(payload: dict, duration_ms: int) -> None:
    duration_seconds = round(max(0, int(duration_ms)) / 1000, 3)
    payload["tool_stats_payload"]["stats"]["duration_ms"] = max(0, int(duration_ms))
    payload["user_stats_payload"]["items"][0]["stats"]["duration_ms"] = max(0, int(duration_ms))
    payload["tool_stats_payload"]["custom_metrics"]["total_duration_seconds"] = duration_seconds
    payload["user_stats_payload"]["items"][0]["custom_metrics"]["test_duration_seconds"] = duration_seconds


def apply_existing_payload_duration(payload: dict, run_dir: Path, timing_file: str = "") -> None:
    """Refresh timing on an existing JSON without changing its case metrics."""
    user_metrics = payload["user_stats_payload"]["items"][0]["custom_metrics"]
    operation_type = str(user_metrics.get("operation_type") or DEFAULT_OPERATION_TYPE)
    timing_args = type(
        "TimingArgs",
        (),
        {
            "timing_file": timing_file,
            "skill_name": OPERATION_SKILL_NAMES.get(operation_type, ""),
            "invocation_id": "",
            "duration_ms": None,
            "operation_type": operation_type,
        },
    )()
    local_ms = timing_duration_ms(timing_args, run_dir)
    if local_ms is not None:
        set_duration_metrics(payload, local_ms)
        return
    set_duration_metrics(payload, cyou_filtered_session_duration_ms() or 0)


def resolve_skill_duration_ms(args, run_dir: Path | None = None) -> int:
    local_ms = timing_duration_ms(args, run_dir)
    if local_ms is not None:
        return local_ms
    return cyou_filtered_session_duration_ms() or 0


def read_workflow_config() -> dict:
    """Read optional workflow identity fallbacks without blocking uploads."""
    try:
        with WORKFLOW_CONFIG_PATH.open("r", encoding="utf-8-sig") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return config if isinstance(config, dict) else {}


def resolve_identity(field: str, environment_name: str) -> str:
    environment_value = (os.getenv(environment_name) or "").strip()
    if environment_value:
        return environment_value
    config_value = str(read_workflow_config().get(field) or "").strip()
    return config_value or "无"


def apply_cyou_spend(payload: dict, ai_model: str = "") -> dict:
    remove_unreported_top_level_fields(payload)
    ensure_operation_type(payload)
    snap = cyou_spend_snapshot()
    tool_metrics = payload["tool_stats_payload"]["custom_metrics"]
    user_metrics = payload["user_stats_payload"]["items"][0]["custom_metrics"]
    if "feature_count" not in user_metrics:
        user_metrics["feature_count"] = int(user_metrics.get("success_count", 0)) + int(user_metrics.get("failure_count", 0))
    for target in (tool_metrics, user_metrics):
        target["total_cost_usd"] = snap["session_spend_usd"]
        target["total_tokens"] = snap["session_total_tokens"]
    user_metrics["tester_account"] = resolve_identity("tester_account", "CYOU_API_KEY_ALIAS")
    user_metrics["project_group"] = resolve_identity("project_group", "CYOU_TEAM_ALIAS")
    model_args = type("ModelArgs", (), {"ai_model": ai_model})()
    user_metrics["ai_model"] = resolve_ai_model(model_args, user_metrics.get("ai_model"))
    return payload


def merge_cyou_spend_into_json(path: Path, ai_model: str = "", timing_file: str = "") -> Path:
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or "tool_stats_payload" not in payload or "user_stats_payload" not in payload:
        raise ValueError(f"not a functiontest upload json: {path}")
    apply_cyou_spend(payload, ai_model=ai_model)
    if timing_file:
        apply_existing_payload_duration(payload, path.parent, timing_file=timing_file)
    validate_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return path


def parse_datetime(value: str):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def detect_ip() -> str:
    candidates = []
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            candidates.append(item[4][0])
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            candidates.insert(0, s.getsockname()[0])
    except OSError:
        pass
    for candidate in candidates:
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if not ip.is_loopback and not ip.is_link_local:
            return str(ip)
    return "127.0.0.1"


def resolve_report(input_path: Path):
    path = input_path.resolve()
    if path.is_file():
        report = path
        run_dir = report.parent
    elif path.is_dir():
        run_dir = path
        run_name = run_dir.name
        report = run_dir / f"{run_name}-unity-functiontest-report.md"
    else:
        raise FileNotFoundError(f"input path not found: {input_path}")
    if not report.is_file():
        raise FileNotFoundError(f"functiontest report not found: {report}")
    validate_output_run_dir(run_dir)
    return report, run_dir


def validate_output_run_dir(run_dir: Path) -> None:
    parts = list(run_dir.resolve().parts)
    output_indexes = [i for i, part in enumerate(parts) if part.lower() == "output"]
    if not output_indexes:
        raise ValueError(
            "FunctionTest input must be under Doc/AI开发文档/output/{feature_id}/{run_dir}: "
            f"{run_dir}"
        )
    output_index = output_indexes[-1]
    if output_index + 2 >= len(parts):
        raise ValueError(
            "FunctionTest output path must contain feature_id and run_dir after output: "
            f"{run_dir}"
        )
    feature_id = parts[output_index + 1]
    run_name = parts[output_index + 2]
    if run_dir.name != run_name or not run_name.startswith(feature_id + "-"):
        raise ValueError(
            "FunctionTest output path must be output/{feature_id}/{feature_id}-{seq4}: "
            f"{run_dir}"
        )


def infer_run_name(report: Path, run_dir: Path) -> str:
    suffix = "-unity-functiontest-report.md"
    if report.name.endswith(suffix):
        return report.name[: -len(suffix)]
    return run_dir.name


def infer_feature_name(report_text: str, run_name: str) -> str:
    match = re.search(r"feature_id[：:]\s*([A-Za-z0-9_.-]+)", report_text)
    if match:
        return match.group(1)
    match = re.match(r"^(.*)-\d{4}$", run_name)
    if match:
        return match.group(1)
    return run_name


def parse_counts(report_text: str):
    # New reports expose all four canonical verdicts. Keep the three-count
    # patterns below for older reports, where test_inconclusive did not exist
    # as an independent report status.
    four_status_patterns = [
        r"functional\s+passed\s*=\s*(\d+).*?failed\s*=\s*(\d+).*?blocked\s*=\s*(\d+).*?test_inconclusive\s*=\s*(\d+)",
        r"passed\s*=\s*(\d+).*?failed\s*=\s*(\d+).*?blocked\s*=\s*(\d+).*?test_inconclusive\s*=\s*(\d+)",
        r"passed\s*[：:]\s*(\d+).*?failed\s*[：:]\s*(\d+).*?blocked\s*[：:]\s*(\d+).*?test_inconclusive\s*[：:]\s*(\d+)",
    ]
    for pattern in four_status_patterns:
        match = re.search(pattern, report_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return tuple(int(match.group(i)) for i in range(1, 5))

    patterns = [
        r"functional\s+passed\s*=\s*(\d+).*?failed\s*=\s*(\d+).*?blocked\s*=\s*(\d+)",
        r"passed\s*=\s*(\d+).*?failed\s*=\s*(\d+).*?blocked\s*=\s*(\d+)",
        r"passed\s*[：:]\s*(\d+).*?failed\s*[：:]\s*(\d+).*?blocked\s*[：:]\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, report_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return tuple(int(match.group(i)) for i in range(1, 4)) + (0,)
    raise ValueError("cannot parse passed/failed/blocked/test_inconclusive counts from report")


def parse_total_cases(report_text: str):
    match = re.search(r"用例总数[：:]\s*(\d+)", report_text)
    if match:
        return int(match.group(1))
    return None


def parse_functional_total(report_text: str):
    match = re.search(r"functional\s*=\s*(\d+)", report_text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def resolve_total_case_count(
    report_text: str,
    passed: int,
    failed: int,
    blocked: int,
    inconclusive: int,
) -> int:
    """Resolve the uploaded total for the four functional verdict buckets.

    The Markdown headline may also include non-functional scope. When the
    report exposes a functional total, use that value; otherwise the explicit
    total must equal the four verdict counts. This keeps the upload invariant
    true instead of mixing non-functional scope into case verdict totals.
    """
    counted_cases = passed + failed + blocked + inconclusive
    functional_total = parse_functional_total(report_text)
    reported_total = parse_total_cases(report_text)
    expected_total = functional_total if functional_total is not None else reported_total
    if expected_total is not None and expected_total != counted_cases:
        raise ValueError(
            "report case total does not match verdict counts: "
            f"reported_functional_total={expected_total}, "
            f"passed={passed}, failed={failed}, blocked={blocked}, "
            f"test_inconclusive={inconclusive}"
        )
    return counted_cases


def parse_issue_counts(report_text: str):
    bug_match = re.search(r"定位Bug数[：:]\s*(\d+)", report_text)
    fixed_match = re.search(r"修复问题数[：:]\s*(\d+)", report_text)
    if not bug_match or not fixed_match:
        raise ValueError("report is missing real 定位Bug数/修复问题数 statistics")
    return int(bug_match.group(1)), int(fixed_match.group(1))


def parse_fix_round_count(report_text: str) -> int:
    match = re.search(r"自动修复轮次[：:]\s*(\d+)", report_text)
    return int(match.group(1)) if match else 0


def validate_non_empty_report(
    report_text: str,
    passed: int,
    failed: int,
    blocked: int,
    inconclusive: int,
    report: Path,
) -> int:
    total_cases = resolve_total_case_count(
        report_text, passed, failed, blocked, inconclusive
    )
    if total_cases == 0:
        raise ValueError(
            "refusing to convert empty FunctionTest report: "
            f"passed=0, failed=0, blocked=0, test_inconclusive=0, "
            f"total_case_count={total_cases}; report={report}"
        )
    return total_cases


def is_report_success(passed: int, failed: int, blocked: int, inconclusive: int) -> bool:
    # validate_non_empty_report has already proved that a usable report exists.
    # Upload-level success/failure is report generation success, not case verdict.
    return True


def build_payload(args):
    report, run_dir = resolve_report(Path(args.input))
    run_name = infer_run_name(report, run_dir)
    report_text = report.read_text(encoding="utf-8", errors="replace")
    feature_name = args.feature_name or infer_feature_name(report_text, run_name)
    passed, failed, blocked, inconclusive = parse_counts(report_text)
    bug_count, fixed_issue_count = parse_issue_counts(report_text)
    fix_round_count = parse_fix_round_count(report_text)
    total_case_count = validate_non_empty_report(
        report_text, passed, failed, blocked, inconclusive, report
    )
    is_passed = is_report_success(passed, failed, blocked, inconclusive)
    duration_ms = resolve_skill_duration_ms(args, run_dir)
    duration_seconds = round(duration_ms / 1000, 3)
    client_ip = args.client_ip or detect_ip()
    report_time = args.report_time or local_report_time()

    return {
        "tool_stats_payload": {
            "tool_code": "UnityFunctionTest",
            "user_ip": client_ip,
            "report_time": report_time,
            "stats": {
                "usage_count": 1,
                "duration_ms": duration_ms,
            },
            "custom_metrics": {
                "test_run_count": 1,
                "report_success_count": 1 if is_passed else 0,
                "report_failure_count": 0 if is_passed else 1,
                "bug_count": bug_count,
                "fixed_issue_count": fixed_issue_count,
                "fix_round_count": fix_round_count,
                "total_duration_seconds": duration_seconds,
                "total_cost_usd": args.total_cost,
                "total_tokens": 0,
            },
        },
        "user_stats_payload": {
            "tool_code": "UnityFunctionTest",
            "report_time": report_time,
            "items": [
                {
                    "stats": {
                        "usage_count": 1,
                        "duration_ms": duration_ms,
                    },
                    "custom_metrics": {
                        "tester_account": resolve_identity("tester_account", "CYOU_API_KEY_ALIAS"),
                        "project_group": resolve_identity("project_group", "CYOU_TEAM_ALIAS"),
                        "operation_type": validate_operation_type(args.operation_type),
                        "client_ip": client_ip,
                        "feature_count": (1 if is_passed else 0) + (0 if is_passed else 1),
                        "feature_name": feature_name,
                        "test_duration_seconds": duration_seconds,
                        "success_case_count": passed,
                        "failure_case_count": failed,
                        "block_case_count": blocked,
                        "invalid_case_count": inconclusive,
                        "total_case_count": total_case_count,
                        "bug_count": bug_count,
                        "fixed_issue_count": fixed_issue_count,
                        "fix_round_count": fix_round_count,
                        "success_count": 1 if is_passed else 0,
                        "failure_count": 0 if is_passed else 1,
                        "total_cost_usd": args.total_cost,
                        "total_tokens": 0,
                        "ai_model": resolve_ai_model(args),
                    },
                }
            ],
        },
    }, report, run_dir, run_name


def build_operation_payload(args):
    operation_type = validate_operation_type(args.operation_type)
    report_time = args.report_time or local_report_time()
    duration_ms = resolve_skill_duration_ms(args)
    duration_seconds = round(duration_ms / 1000, 3)
    client_ip = args.client_ip or detect_ip()
    feature_name = args.feature_name or operation_type
    return {
        "tool_stats_payload": {
            "tool_code": "UnityFunctionTest",
            "user_ip": client_ip,
            "report_time": report_time,
            "stats": {"usage_count": 1, "duration_ms": duration_ms},
            "custom_metrics": {
                "test_run_count": 0,
                "report_success_count": 0,
                "report_failure_count": 0,
                "bug_count": 0,
                "fixed_issue_count": 0,
                "fix_round_count": 0,
                "total_duration_seconds": duration_seconds,
                "total_cost_usd": args.total_cost,
                "total_tokens": 0,
            },
        },
        "user_stats_payload": {
            "tool_code": "UnityFunctionTest",
            "report_time": report_time,
            "items": [{
                "stats": {"usage_count": 1, "duration_ms": duration_ms},
                "custom_metrics": {
                    "tester_account": resolve_identity("tester_account", "CYOU_API_KEY_ALIAS"),
                    "project_group": resolve_identity("project_group", "CYOU_TEAM_ALIAS"),
                    "operation_type": operation_type,
                    "client_ip": client_ip,
                    "feature_count": 0,
                    "feature_name": feature_name,
                    "test_duration_seconds": duration_seconds,
                    "success_case_count": 0,
                    "failure_case_count": 0,
                    "block_case_count": 0,
                    "invalid_case_count": 0,
                    "total_case_count": 0,
                    "bug_count": 0,
                    "fixed_issue_count": 0,
                    "fix_round_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_cost_usd": args.total_cost,
                    "total_tokens": 0,
                    "ai_model": resolve_ai_model(args),
                },
            }],
        },
    }


def validate_payload(payload):
    if set(payload) != ALLOWED_UPLOAD_TOP_LEVEL:
        extra = sorted(set(payload) - ALLOWED_UPLOAD_TOP_LEVEL)
        missing = sorted(ALLOWED_UPLOAD_TOP_LEVEL - set(payload))
        raise ValueError(
            "upload JSON top-level keys must be exactly tool_stats_payload and user_stats_payload; "
            f"extra={extra}, missing={missing}"
        )
    tool = payload["tool_stats_payload"]
    user = payload["user_stats_payload"]["items"][0]
    required_tool = {
        "test_run_count",
        "report_success_count",
        "report_failure_count",
        "bug_count",
        "fixed_issue_count",
        "fix_round_count",
        "total_duration_seconds",
        "total_cost_usd",
        "total_tokens",
    }
    required_user = {
        "tester_account",
        "project_group",
        "operation_type",
        "client_ip",
        "feature_count",
        "feature_name",
        "test_duration_seconds",
        "success_case_count",
        "failure_case_count",
        "block_case_count",
        "invalid_case_count",
        "total_case_count",
        "bug_count",
        "fixed_issue_count",
        "fix_round_count",
        "success_count",
        "failure_count",
        "total_cost_usd",
        "total_tokens",
        "ai_model",
    }
    if set(tool["custom_metrics"].keys()) != required_tool:
        raise ValueError("tool custom_metrics keys do not match schema")
    if set(user["custom_metrics"].keys()) != required_user:
        raise ValueError("user custom_metrics keys do not match schema")
    metrics = user["custom_metrics"]
    counted_cases = (
        metrics["success_case_count"]
        + metrics["failure_case_count"]
        + metrics["block_case_count"]
        + metrics["invalid_case_count"]
    )
    if counted_cases != metrics["total_case_count"]:
        raise ValueError(
            "success_case_count + failure_case_count + block_case_count + "
            f"invalid_case_count must equal total_case_count; counted={counted_cases}, "
            f"total={metrics['total_case_count']}"
        )
    if round(tool["stats"]["duration_ms"] / 1000, 3) != user["custom_metrics"]["test_duration_seconds"]:
        raise ValueError("stats.duration_ms must match test_duration_seconds")
    validate_operation_type(user["custom_metrics"]["operation_type"])


def handle_json_input(args) -> bool:
    input_path = Path(args.input).resolve()
    if input_path.suffix.lower() != ".json":
        return False
    if not input_path.is_file():
        raise FileNotFoundError(f"upload json not found: {input_path}")
    validate_output_run_dir(input_path.parent)
    with input_path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "tool_stats_payload" not in data or "user_stats_payload" not in data:
        raise SystemExit(
            "[ERROR] 输入的是测试用例 JSON，不是 FunctionTest Markdown 报告或已生成的 functiontest-upload.json。\n"
            "[INFO] 请使用 functiontest-workflow 编排 skill 先执行 unity-functiontest 生成 md 报告，再调用本脚本转换 JSON。"
        )
    validate_payload(data)
    print(str(input_path))
    return True


def apply_positional_args(args):
    if not args.positional:
        return
    if len(args.positional) == 1:
        args.input = args.positional[0]
        return
    raise SystemExit("positional input must be: input_path")

def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("positional", nargs="*", help="input_path")
    parser.add_argument("--input", help="FunctionTest report file or run directory")
    parser.add_argument("--output", help="Output upload JSON path")
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow replacing an existing output JSON; only valid for an explicitly requested retest/overwrite",
    )
    parser.add_argument("--tester-account", default="无")
    parser.add_argument("--client-ip")
    parser.add_argument("--feature-name")
    parser.add_argument("--report-time")
    parser.add_argument(
        "--timing-file",
        help="Skill timing sidecar JSON；优先读取已闭合的 skill_start/skill_end 记录",
    )
    parser.add_argument(
        "--skill-name",
        help="要读取的 Skill 名称；未传入时按 operation_type 推断",
    )
    parser.add_argument("--invocation-id", help="要读取的唯一 Skill invocation_id")
    parser.add_argument("--total-cost", type=float, default=0.0)
    parser.add_argument(
        "--ai-model",
        default="",
        help="AI模型；优先使用显式值，其次读取 CYOU_AI_MODEL/CYOU_MODEL/AI_MODEL/MODEL_NAME，均不可用时写入暂无数据",
    )
    parser.add_argument(
        "--operation-type",
        choices=sorted(OPERATION_TYPES),
        default=DEFAULT_OPERATION_TYPE,
        help="固定中文操作类型；普通报告默认为主动测试工作流",
    )
    parser.add_argument(
        "--operation-only",
        action="store_true",
        help="生成单独 Skill 的最小上报 JSON，不读取 Markdown 报告，测试统计全部为 0",
    )
    parser.add_argument("--merge-cyou-spend", action="store_true", help="merge current Cyou spend env snapshot into upload json")
    args = parser.parse_args()
    apply_positional_args(args)

    if args.merge_cyou_spend:
        if not args.input:
            parser.error("--merge-cyou-spend requires input upload json")
        input_path = Path(args.input).resolve()
        if input_path.suffix.lower() != ".json":
            parser.error("--merge-cyou-spend requires functiontest-upload.json input")
        validate_output_run_dir(input_path.parent)
        print(str(merge_cyou_spend_into_json(input_path, ai_model=args.ai_model, timing_file=args.timing_file or "")))
        return

    if args.operation_only:
        if args.input:
            parser.error("--operation-only does not accept --input")
        if not args.output:
            parser.error("--operation-only requires --output")
        if args.operation_type == "独立Unity功能测试":
            parser.error("独立Unity功能测试必须基于 Markdown 报告转换，不能使用 --operation-only")
        payload = build_operation_payload(args)
        apply_cyou_spend(payload)
        validate_payload(payload)
        output = Path(args.output).resolve()
        validate_output_run_dir(output.parent)
        if output.exists() and not args.allow_overwrite:
            raise SystemExit(
                "[ERROR] output already exists; refusing to overwrite without explicit retest/overwrite permission: "
                f"{output}"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json.loads(output.read_text(encoding="utf-8"))
        print(str(output))
        return

    if not args.input:
        parser.error("input is required: input_path")

    if handle_json_input(args):
        return

    payload, report, run_dir, run_name = build_payload(args)
    apply_cyou_spend(payload)
    validate_payload(payload)
    output = Path(args.output).resolve() if args.output else run_dir / f"{run_name}-functiontest-upload.json"
    validate_output_run_dir(output.parent)
    if output.parent != run_dir:
        raise SystemExit(f"[ERROR] output JSON must be in the same output run directory as the report: {output}")
    if output.exists() and not args.allow_overwrite:
        raise SystemExit(
            "[ERROR] output already exists; refusing to overwrite without explicit retest/overwrite permission. "
            f"input_report={report} output_json={output}"
        )
    if output == report:
        raise SystemExit(f"[ERROR] input report and output JSON must be different paths: {report}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(output.read_text(encoding="utf-8"))
    print(str(output))


if __name__ == "__main__":
    main()
