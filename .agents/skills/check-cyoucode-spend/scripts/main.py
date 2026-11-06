import os
import sys

# Windows 下 Python 默认 stdout 编码为 GBK（取决于系统代码页），而 Cyou 终端为 UTF-8，
# 直接输出中文（如 API Key 别名）会乱码。此处强制 stdout 使用 UTF-8 编码。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

session_id = os.getenv("CYOU_SESSION_ID")
task_id = os.getenv("CYOU_TASK_ID")
turn_id = os.getenv("CYOU_TURN_ID")
tool_call_id = os.getenv("CYOU_TOOL_CALL_ID")
litellm_call_id = os.getenv("CYOU_LITELLM_CALL_ID")
api_key_alias = os.getenv("CYOU_API_KEY_ALIAS")
team_alias = os.getenv("CYOU_TEAM_ALIAS")
session_spend_usd = os.getenv("CYOU_SESSION_SPEND_USD")
session_total_tokens = os.getenv("CYOU_SESSION_TOTAL_TOKENS")
session_duration_ms = os.getenv("CYOU_SESSION_DURATION_MS")
session_approval_duration_ms = os.getenv("CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS")
session_condense_duration_ms = os.getenv("CYOU_SESSION_CONDENSE_DURATION_MS")
session_usage_status = os.getenv("CYOU_SESSION_USAGE_STATUS")
session_pending_calls = os.getenv("CYOU_SESSION_PENDING_CALLS")

print({
    "session_id": session_id,
    "task_id": task_id,
    "turn_id": turn_id,
    "tool_call_id": tool_call_id,
    "litellm_call_id": litellm_call_id,
    "api_key_alias": api_key_alias,
    "team_alias": team_alias,
    "session_spend_usd": session_spend_usd,
    "session_total_tokens": session_total_tokens,
    "session_duration_ms": session_duration_ms,
    "session_approval_duration_ms": session_approval_duration_ms,
    "session_condense_duration_ms": session_condense_duration_ms,
    "session_usage_status": session_usage_status,
    "session_pending_calls": session_pending_calls,
})
