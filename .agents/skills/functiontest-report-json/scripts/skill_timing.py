#!/usr/bin/env python3
"""Record and read Skill invocation timing.

The timing file is a small, append/update sidecar.  It deliberately keeps
Skill timing separate from Unity's run-log lifecycle records so that
``setup``/``stop_playmode`` remain useful to the Unity executor without being
mistaken for the duration of a Skill.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import uuid
from pathlib import Path


APPROVAL_ENV = "CYOU_SESSION_PERMISSION_APPROVAL_DURATION_MS"
CONDENSE_ENV = "CYOU_SESSION_CONDENSE_DURATION_MS"
SESSION_ENV = "CYOU_SESSION_DURATION_MS"


def configure_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="microseconds")


def parse_time(value: object) -> dt.datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        result = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.astimezone()
    return result


def env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value in (None, ""):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return max(0, number)


def env_snapshot() -> dict[str, int | None]:
    return {
        "session_duration_ms": env_int(SESSION_ENV),
        "approval_duration_ms": env_int(APPROVAL_ENV),
        "condense_duration_ms": env_int(CONDENSE_ENV),
    }


def empty_document() -> dict:
    return {"version": 1, "records": []}


def read_document(path: Path) -> dict:
    if not path.exists():
        return empty_document()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Skill timing file: {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise ValueError(f"invalid Skill timing file structure: {path}")
    return data


def write_document(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def duration_ms(start: object, end: object) -> int | None:
    start_time = parse_time(start)
    end_time = parse_time(end)
    if not start_time or not end_time or end_time <= start_time:
        return None
    return max(0, int(round((end_time - start_time).total_seconds() * 1000)))


def is_nested_record(record: dict) -> bool:
    """Whether this timing record belongs to another Skill invocation."""
    return bool(str(record.get("parent_invocation_id") or "").strip())


def compute_active_duration(record: dict) -> tuple[int | None, str]:
    local_ms = duration_ms(record.get("skill_start_time"), record.get("skill_end_time"))
    if local_ms is not None:
        # Cyou timing variables are cumulative for the whole session.  A child
        # Skill must remain a raw sub-span; filtering here would subtract the
        # same session-level wait again when the parent Skill is calculated.
        if is_nested_record(record):
            return local_ms, "nested_skill_span_raw"

        approval_start = record.get("approval_at_start_ms")
        approval_end = record.get("approval_at_end_ms")
        condense_start = record.get("condense_at_start_ms")
        condense_end = record.get("condense_at_end_ms")
        session_start = record.get("session_duration_at_start_ms")
        session_end = record.get("session_duration_at_end_ms")
        if all(isinstance(item, int) for item in (
            session_start,
            session_end,
            approval_start,
            approval_end,
            condense_start,
            condense_end,
        )):
            approval_delta = max(0, approval_end - approval_start)
            condense_delta = max(0, condense_end - condense_start)
            return max(0, local_ms - approval_delta - condense_delta), "skill_span_minus_environment_deltas"
        return local_ms, "skill_span_without_available_environment_deltas"

    # A child Skill cannot use the session fallback: that value covers the
    # whole session rather than this child interval.  Keep the record
    # explicitly unavailable so the parent remains the only uploader.
    if is_nested_record(record):
        return None, "nested_skill_timing_unavailable"

    snapshot = env_snapshot()
    session_ms = snapshot["session_duration_ms"]
    approval_ms = snapshot["approval_duration_ms"]
    condense_ms = snapshot["condense_duration_ms"]
    if all(isinstance(item, int) for item in (session_ms, approval_ms, condense_ms)):
        return max(0, session_ms - approval_ms - condense_ms), "session_duration_minus_environment_filters"
    return None, "unavailable"


def start_record(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = read_document(path)
    invocation_id = args.invocation_id or f"skill-{uuid.uuid4().hex}"
    if any(str(item.get("invocation_id")) == invocation_id for item in data["records"] if isinstance(item, dict)):
        raise ValueError(f"invocation_id already exists: {invocation_id}")
    snapshot = env_snapshot()
    record = {
        "invocation_id": invocation_id,
        "parent_invocation_id": args.parent_invocation_id or "",
        "skill_name": str(args.skill_name or "").strip(),
        "operation_type": str(args.operation_type or "").strip(),
        "report_visible": not args.report_hidden,
        "skill_start_time": now_iso(),
        "skill_end_time": None,
        "approval_at_start_ms": snapshot["approval_duration_ms"],
        "approval_at_end_ms": None,
        "condense_at_start_ms": snapshot["condense_duration_ms"],
        "condense_at_end_ms": None,
        "session_duration_at_start_ms": snapshot["session_duration_ms"],
        "session_duration_at_end_ms": None,
        "skill_active_duration_ms": None,
        "duration_source": "started",
        "status": "started",
    }
    data["records"].append(record)
    write_document(path, data)
    print(json.dumps({"invocation_id": invocation_id, "file": str(path)}, ensure_ascii=False))


def end_record(args: argparse.Namespace) -> None:
    path = Path(args.file).resolve()
    data = read_document(path)
    matches = [item for item in data["records"] if isinstance(item, dict) and item.get("invocation_id") == args.invocation_id]
    if len(matches) != 1:
        raise ValueError(f"invocation_id not found or not unique: {args.invocation_id}")
    record = matches[0]
    if record.get("skill_end_time"):
        raise ValueError(f"skill_end already recorded: {args.invocation_id}")
    snapshot = env_snapshot()
    record["skill_end_time"] = now_iso()
    record["approval_at_end_ms"] = snapshot["approval_duration_ms"]
    record["condense_at_end_ms"] = snapshot["condense_duration_ms"]
    record["session_duration_at_end_ms"] = snapshot["session_duration_ms"]
    record["status"] = args.status
    active_ms, source = compute_active_duration(record)
    record["skill_active_duration_ms"] = active_ms
    record["duration_source"] = source
    write_document(path, data)
    print(json.dumps({"invocation_id": args.invocation_id, "skill_active_duration_ms": active_ms, "duration_source": source}, ensure_ascii=False))


def load_records(path: Path) -> list[dict]:
    data = read_document(path)
    return [item for item in data["records"] if isinstance(item, dict)]


def select_record(
    records: list[dict],
    skill_name: str = "",
    invocation_id: str = "",
) -> dict | None:
    if invocation_id:
        return next((item for item in records if item.get("invocation_id") == invocation_id), None)
    candidates = [item for item in records if not skill_name or item.get("skill_name") == skill_name]
    if not candidates:
        return None
    roots = [item for item in candidates if not item.get("parent_invocation_id")]
    return (roots or candidates)[-1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record Skill start/end timing in a JSON sidecar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--file", required=True)
    start.add_argument("--skill-name", required=True)
    start.add_argument("--operation-type", default="")
    start.add_argument("--parent-invocation-id", default="")
    start.add_argument("--invocation-id", default="")
    start.add_argument("--report-hidden", action="store_true")

    end = subparsers.add_parser("end")
    end.add_argument("--file", required=True)
    end.add_argument("--invocation-id", required=True)
    end.add_argument("--status", choices=("completed", "failed", "blocked", "cancelled"), default="completed")
    return parser


def main() -> None:
    configure_utf8_stdio()
    args = build_parser().parse_args()
    if args.command == "start":
        start_record(args)
    else:
        end_record(args)


if __name__ == "__main__":
    main()
