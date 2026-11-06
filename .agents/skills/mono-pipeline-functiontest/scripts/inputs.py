"""创建日期：2026-10-26；作者：Cyou。
功能：完整原用例、整理来源、明确单目标及原索引解析；不生成静态动作映射。
参数：严格 JSON 原字节、本地来源及权限；完整保留未知业务字段。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .contracts import (
    InputError, IntegrityError, JsonObject, JsonValue, Limits, PERMISSIONS, SecretGuard, canonical,
    digest, hash_value, integer, keys_only, local_path, object_value, read_regular, strict_json, text,
)

# 完整性口径：full = 逐成员核验全包 sha256 与静态清单；identity_only = 只验 EXE 路径/PID 创建时间/
# build_guid/端口独占/描述符绑定，不逐成员比对包内文件字节。identity_only 由操作者显式声明并记入本轮 journal。
INTEGRITY_MODES: frozenset[str] = frozenset({"full", "identity_only"})


@dataclass(frozen=True)
class SourceItem:
    """原索引、原文本及原字段的不可变索引视图，不替换完整输入。"""

    index: int
    text: str
    original: JsonValue

    # 功能：输出索引视图；参数无，original 未做删减。
    def to_json(self) -> JsonObject:
        return {"index": self.index, "text": self.text, "original": self.original}


# 功能：保留字符串/文本条目及显式索引；参数 allow_empty 仅用于无前置条件。
def source_items(raw: JsonValue, label: str, allow_empty: bool = False) -> tuple[SourceItem, ...]:
    if raw == "" and allow_empty:
        return ()
    values: list[JsonValue] = raw if isinstance(raw, list) else [raw]
    if not values and not allow_empty:
        raise InputError(label + " 不能为空")
    result: list[SourceItem] = []
    indexes: set[int] = set()
    for position, value in enumerate(values, 1):
        if isinstance(value, str):
            item: SourceItem = SourceItem(position, text(value, label, trim=False), value)
        else:
            document: JsonObject = object_value(value, label)
            index: int = integer(document.get("index", position), label + ".index")
            item = SourceItem(index, text(document.get("text"), label + ".text", trim=False), value)
        if item.index in indexes:
            raise InputError(label + " 含重复原索引")
        indexes.add(item.index)
        result.append(item)
    return tuple(result)


@dataclass(frozen=True)
class OriginalCase:
    """完整用例及可查原索引；raw 包括所有未识别的业务字段。"""

    case_id: str
    title: str
    preconditions: tuple[SourceItem, ...]
    steps: tuple[SourceItem, ...]
    expected: tuple[SourceItem, ...]
    raw: JsonObject

    # 功能：按原索引查找文本；参数 scope 为 expected/precondition/guard/step。
    def item(self, scope: str, index: int) -> SourceItem:
        collection: tuple[SourceItem, ...] = self.expected if scope == "expected" else (
            self.preconditions if scope == "precondition" else self.steps
        )
        matches: list[SourceItem] = [item for item in collection if item.index == index]
        if len(matches) != 1:
            raise InputError("绑定引用了不存在的原索引")
        return matches[0]


@dataclass(frozen=True)
class CaseInput:
    """原字节摘要与完整输入；初始化不包含执行计划或动作映射。"""

    raw_bytes: bytes
    raw_sha256: str
    document: JsonValue
    cases: tuple[OriginalCase, ...]

    # 功能：查找原 CaseId；参数 case_id 不做重命名。
    def case(self, case_id: str) -> OriginalCase:
        matches: list[OriginalCase] = [case for case in self.cases if case.case_id == case_id]
        if len(matches) != 1:
            raise InputError("CaseId 不属于完整原用例")
        return matches[0]


# 功能：严格解析完整原用例；参数 raw 为必须保存摘要的原字节。
def parse_cases(raw: bytes, limits: Limits | None = None) -> CaseInput:
    budget: Limits = limits if limits is not None else Limits()
    document: JsonValue = strict_json(raw, budget.input_bytes, budget, bom=True)
    SecretGuard().check(document)
    entries: JsonValue = document
    if isinstance(document, dict):
        if "cases" in document and "case_id" in document:
            raise InputError("原输入同时存在单例及 cases 容器，归属不清")
        entries = document.get("cases") if "cases" in document else [document]
    if not isinstance(entries, list) or not entries:
        raise InputError("原用例必须为非空数组、单例或清晰 cases 容器")
    cases: list[OriginalCase] = []
    identities: set[str] = set()
    required: set[str] = {"case_id", "title", "preconditions", "steps", "expected"}
    for entry in entries:
        item: JsonObject = object_value(entry, "原用例")
        if not required <= set(item):
            raise InputError("原用例缺失必需字段")
        case_id: str = text(item.get("case_id"), "case_id")
        if len(case_id) > 256 or "\n" in case_id or "\r" in case_id:
            raise InputError("CaseId 长度或字符非法")
        if case_id.casefold() in identities:
            raise InputError("原用例含重复编号")
        identities.add(case_id.casefold())
        cases.append(OriginalCase(case_id, text(item.get("title"), "title", trim=False),
                                  source_items(item.get("preconditions"), "preconditions", True),
                                  source_items(item.get("steps"), "steps"),
                                  source_items(item.get("expected"), "expected"), item))
    return CaseInput(raw, digest(raw), document, tuple(cases))


# 功能：校验来源时间且归一到 UTC；参数 value 为显式身份时间，不生成执行耗时。
def utc_datetime(value: JsonValue, label: str) -> datetime:
    encoded: str = text(value, label)
    try:
        parsed: datetime = datetime.fromisoformat(encoded.replace("Z", "+00:00"))
    except ValueError:
        raise InputError(label + " 不是 ISO 8601 时间") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError(label + " 必须包含时区")
    return parsed.astimezone(timezone.utc)


WORKFLOW_START_FIELDS = ("invocation_id", "parent_invocation_id", "skill_name", "operation_type", "report_visible",
                         "skill_start_time", "approval_at_start_ms", "condense_at_start_ms", "session_duration_at_start_ms")


# 功能：读取统一计时器已创建的唯一记录；参数 path/identity 为明确本地 sidecar 和原编号，不创建或补填计时。
def workflow_record(path: Path, identity: str, limits: Limits) -> JsonObject:
    document: JsonObject = object_value(strict_json(read_regular(path, limits.input_bytes), limits.input_bytes, limits, bom=True), "workflow timing")
    SecretGuard().check(document)
    records: JsonValue = document.get("records")
    if document.get("version") != 1 or not isinstance(records, list):
        raise InputError("统一父计时必须来自 version=1 的实际计时文件")
    matches: list[JsonObject] = [object_value(value, "timing record") for value in records
                               if isinstance(value, dict) and value.get("invocation_id") == identity]
    if len(matches) != 1:
        raise InputError("统一计时编号缺失或不唯一")
    record: JsonObject = matches[0]
    if not set(WORKFLOW_START_FIELDS) <= set(record):
        raise InputError("统一计时缺少原起点字段")
    utc_datetime(record["skill_start_time"], "workflow start")
    text(record["skill_name"], "workflow skill")
    if record.get("skill_end_time") is not None:
        if utc_datetime(record["skill_end_time"], "workflow end") < utc_datetime(record["skill_start_time"], "workflow start"):
            raise InputError("统一计时结束早于开始")
    return record


# 功能：绑定现有父/子计时的不可变起点；参数不授予任何运行权限，不接受包内父上下文混用。
def bind_workflow(path: Path, parent_id: str, child_id: str, limits: Limits) -> JsonObject:
    resolved: Path = local_path(str(path), Path.cwd())
    parent: JsonObject = workflow_record(resolved, text(parent_id, "workflow parent id"), limits)
    child: JsonObject = workflow_record(resolved, text(child_id, "workflow child id"), limits)
    if parent.get("parent_invocation_id") or parent["skill_name"] != "functiontest-workflow":
        raise InputError("只接受原统一工作流的唯一根计时")
    if child.get("parent_invocation_id") != parent_id or child["skill_name"] != "mono-pipeline-functiontest":
        raise InputError("Mono 子计时必须属于本次统一父编号")
    if parent.get("skill_end_time") is not None or child.get("skill_end_time") is not None:
        raise InputError("初始化必须绑定尚未闭合的实际父/子计时")
    if utc_datetime(child["skill_start_time"], "child start") < utc_datetime(parent["skill_start_time"], "parent start"):
        raise InputError("子计时早于统一父起点")
    return {"schema": "mono-pipeline-workflow-binding/1", "timing_file": str(resolved),
            "parent_start": {name: parent[name] for name in WORKFLOW_START_FIELDS},
            "child_start": {name: child[name] for name in WORKFLOW_START_FIELDS}}


# 功能：复核父/子起点及闭合顺序；参数 binding 为 journal 内已登记起点，require_closed 仅报告阶段启用。
def verify_workflow(binding: JsonObject, limits: Limits, run_start: JsonValue, run_end: JsonValue = None,
                    require_closed: bool = False) -> JsonObject:
    keys_only(binding, {"schema", "timing_file", "parent_start", "child_start"}, "workflow binding",
              {"schema", "timing_file", "parent_start", "child_start"})
    if binding["schema"] != "mono-pipeline-workflow-binding/1":
        raise IntegrityError("统一父交接格式被修改")
    path: Path = local_path(text(binding["timing_file"], "workflow timing path"), Path.cwd())
    parent_start: JsonObject = object_value(binding["parent_start"], "parent start snapshot")
    child_start: JsonObject = object_value(binding["child_start"], "child start snapshot")
    parent: JsonObject = workflow_record(path, text(parent_start.get("invocation_id"), "parent id"), limits)
    child: JsonObject = workflow_record(path, text(child_start.get("invocation_id"), "child id"), limits)
    if {name: parent[name] for name in WORKFLOW_START_FIELDS} != parent_start or {name: child[name] for name in WORKFLOW_START_FIELDS} != child_start:
        raise IntegrityError("统一父/子原起点或来源身份被改写")
    if parent["skill_name"] != "functiontest-workflow" or child["skill_name"] != "mono-pipeline-functiontest":
        raise IntegrityError("当前统一交接只接受 Workflow 直接调用新 Mono，旧 PC 父记录已停用")
    if child["parent_invocation_id"] != parent["invocation_id"] or parent["parent_invocation_id"]:
        raise IntegrityError("统一父/子归属被修改")
    start: datetime = utc_datetime(run_start, "run start")
    if utc_datetime(parent["skill_start_time"], "parent start") > utc_datetime(child["skill_start_time"], "child start") or utc_datetime(child["skill_start_time"], "child start") > start:
        raise IntegrityError("统一父/子时间不包围宿主起点")
    if require_closed and (parent.get("skill_end_time") is None or child.get("skill_end_time") is None or run_end is None):
        raise InputError("先闭合宿主、原 Mono 子计时及统一父计时，再生成唯一报告")
    if run_end is not None and child.get("skill_end_time") is not None:
        if utc_datetime(run_end, "run end") > utc_datetime(child["skill_end_time"], "child end"):
            raise IntegrityError("Mono 子计时未包含宿主收口")
    if parent.get("skill_end_time") is not None:
        if child.get("skill_end_time") is None or utc_datetime(child["skill_end_time"], "child end") > utc_datetime(parent["skill_end_time"], "parent end"):
            raise IntegrityError("统一父计时未在 Mono 子计时之后闭合")
    return {"timing_file": str(path), "parent": parent, "child": child,
            "closed": parent.get("skill_end_time") is not None and child.get("skill_end_time") is not None,
            "source": "existing_shared_skill_timing_no_backfill"}


@dataclass(frozen=True)
class TargetConfig:
    """明确附加目标；描述符令牌不属于配置，也不通过 CLI 接收。"""

    exe: Path
    pid: int
    port: int
    process_created_utc: str
    build_guid: str
    unity_version: str
    platform: str
    working_directory: Path
    package_manifest: Path
    license_path: Path
    license_sha256: str
    license_scope: str
    permissions: frozenset[str]
    evidence_roots: tuple[Path, ...]
    limits: Limits
    # 完整性口径：full = 逐成员全包 sha256；identity_only = 只验 EXE 路径/PID 创建时间/build_guid/端口独占，
    # 不比对包内文件字节。identity_only 由操作者显式声明并记入本轮 journal，牺牲包完整性证明换取启动速度。
    integrity_mode: str = "full"

    # 功能：输出无凭据的固定目标配置；参数无。
    def to_json(self) -> JsonObject:
        return {
            "schema": "mono-pipeline-target/1", "exe": str(self.exe), "pid": self.pid, "port": self.port,
            "process_created_utc": self.process_created_utc, "build_guid": self.build_guid,
            "unity_version": self.unity_version, "platform": self.platform,
            "working_directory": str(self.working_directory), "package_manifest": str(self.package_manifest),
            "license": {"path": str(self.license_path), "sha256": self.license_sha256,
                        "accepted": True, "scope": self.license_scope},
            "permissions": sorted(self.permissions), "evidence_roots": [str(path) for path in self.evidence_roots],
            "limits": self.limits.to_json(), "integrity_mode": self.integrity_mode,
        }


# 功能：纯解析目标及许可，不探测进程或连接；参数 base 为目标配置所在目录。
def parse_target(document: JsonValue, base: Path) -> TargetConfig:
    item: JsonObject = object_value(document, "target")
    fields: set[str] = {"schema", "exe", "pid", "port", "process_created_utc", "build_guid", "unity_version",
                        "platform", "working_directory", "package_manifest", "license", "permissions",
                        "evidence_roots", "limits", "integrity_mode"}
    required: set[str] = fields - {"working_directory", "evidence_roots", "limits", "integrity_mode"}
    keys_only(item, fields, "target", required)
    SecretGuard().check(item)
    if item["schema"] != "mono-pipeline-target/1" or item["platform"] != "WindowsPlayer":
        raise InputError("目标 schema/platform 不匹配 Windows Player 契约")
    permissions: JsonValue = item["permissions"]
    if not isinstance(permissions, list) or any(not isinstance(value, str) or value not in PERMISSIONS for value in permissions):
        raise InputError("目标权限只能来自已知显式许可")
    if len(set(permissions)) != len(permissions):
        raise InputError("目标权限重复")
    exe: Path = local_path(text(item["exe"], "exe"), base)
    if exe.suffix.lower() != ".exe" or not exe.is_file():
        raise InputError("目标必须为明确存在的 Windows EXE")
    created: datetime = utc_datetime(item["process_created_utc"], "process_created_utc")
    license_info: JsonObject = object_value(item["license"], "license")
    keys_only(license_info, {"path", "sha256", "accepted", "scope"}, "license", {"path", "sha256", "accepted", "scope"})
    if license_info["accepted"] is not True:
        raise InputError("必须明确接受本轮许可范围")
    roots: JsonValue = item.get("evidence_roots", [])
    if not isinstance(roots, list) or len(roots) > 8:
        raise InputError("evidence_roots 必须为不超过八个明确本地目录")
    evidence_roots: tuple[Path, ...] = tuple(local_path(text(root, "evidence_root"), base) for root in roots)
    if any(not root.is_dir() for root in evidence_roots):
        raise InputError("evidence_root 必须为已存在的本地目录")
    integrity_mode: str = text(item.get("integrity_mode", "full"), "integrity_mode")
    if integrity_mode not in INTEGRITY_MODES:
        raise InputError("integrity_mode 只能为 full 或 identity_only")
    return TargetConfig(
        exe, integer(item["pid"], "pid"), integer(item["port"], "port", 7900, 7949),
        created.isoformat(), text(item["build_guid"], "build_guid"), text(item["unity_version"], "unity_version"),
        "WindowsPlayer", local_path(text(item.get("working_directory", str(exe.parent)), "working_directory"), base),
        local_path(text(item["package_manifest"], "package_manifest"), base),
        local_path(text(license_info["path"], "license.path"), base),
        hash_value(license_info["sha256"], "license.sha256"), text(license_info["scope"], "license.scope", trim=False),
        frozenset(str(value) for value in permissions), evidence_roots, Limits.from_json(item.get("limits")),
        integrity_mode,
    )


# 功能：全量验证 Agent 整理来源；参数 document 的 case_ids 必须等于原全集且顺序一致。
def parse_provenance(document: JsonValue, cases: CaseInput, base: Path, limits: Limits) -> list[JsonObject]:
    item: JsonObject = object_value(document, "provenance")
    keys_only(item, {"schema", "sources", "review"}, "provenance", {"schema", "sources", "review"})
    if item["schema"] != "mono-pipeline-provenance/1":
        raise InputError("provenance schema 不匹配")
    review: JsonObject = object_value(item["review"], "provenance.review")
    keys_only(review, {"reviewer", "complete", "case_ids", "statement"}, "provenance.review",
              {"reviewer", "complete", "case_ids", "statement"})
    if review["reviewer"] != "current_agent" or review["complete"] is not True:
        raise InputError("整理来源必须由当前 Agent 声明全量审核")
    if review["case_ids"] != [case.case_id for case in cases.cases]:
        raise InputError("来源审核编号不等于原全集")
    text(review["statement"], "review.statement", trim=False)
    sources: JsonValue = item["sources"]
    if not isinstance(sources, list) or not sources:
        raise InputError("整理来源不能为空")
    result: list[JsonObject] = []
    identities: set[str] = set()
    for raw in sources:
        source: JsonObject = object_value(raw, "provenance.source")
        keys_only(source, {"path", "sha256"}, "provenance.source", {"path", "sha256"})
        path: Path = local_path(text(source["path"], "source.path"), base)
        if str(path).casefold() in identities:
            raise InputError("整理来源重复")
        identities.add(str(path).casefold())
        content: bytes = read_regular(path, limits.source_bytes)
        if digest(content) != hash_value(source["sha256"], "source.sha256"):
            raise InputError("整理来源原字节摘要不匹配")
        result.append({"path": str(path), "sha256": digest(content), "bytes": len(content)})
    return result


# 功能：生成只含原内容的索引快照；参数 cases 未映射动作，不改变自然语言预期。
def case_index(cases: CaseInput) -> JsonObject:
    return {
        "schema": "mono-pipeline-cases/1", "raw_sha256": cases.raw_sha256,
        "document_sha256": digest(canonical(cases.document)), "case_ids": [case.case_id for case in cases.cases],
        "indexes": [{"case_id": case.case_id, "preconditions": [item.to_json() for item in case.preconditions],
                     "steps": [item.to_json() for item in case.steps], "expected": [item.to_json() for item in case.expected]}
                    for case in cases.cases],
    }
