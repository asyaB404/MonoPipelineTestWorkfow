"""创建日期：2026-10-26；作者：Cyou。
更新日期：2026-11-05；更新人：Codex；增加不修改原结果的可选简洁显示。
功能：可迁移的持久逐条 CLI，所有有效会话操作都真实调用包内宿主并写同一 journal。
参数：init 的完整原用例/目标/输出；其余命令的 --run 与按需 --request 本地 JSON。
退出码：0 完成；1 有效反例；2 输入非法；3 明确未执行/环境阻塞；4 未定论/冻结；5 完整性错误。
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import cast

# 直接执行同样禁用依赖模块字节码，避免首次 --help 自行污染严格交付目录；不改变调用方其他解释器设置。
sys.dont_write_bytecode = True

# 直接执行文件与包内执行共用同一实现，根只从当前文件定位，不回原项目查找。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "scripts"

from .contracts import (
    EnvironmentBlocked, FrozenSession, HostError, InputError, IntegrityError, JsonObject, JsonValue,
    Limits, SecretGuard, canonical, local_path, object_value, read_regular, strict_json, digest,
    reject_links,
)
from .evidence import Journal, local_cli_call, new_id, record_data, run_path_budget
from . import delivery
from .report import audit_parent, render_parent
from .session import Session, close_parent, initialize, initialize_parent


class SafeParser(argparse.ArgumentParser):
    """不回显无效 argv（可能含误传凭据），禁止缩写和未登记测试旁路。"""

    # 功能：以固定安全错误拒绝无效参数；参数 message 不向 stdout/stderr 回显。
    def error(self, message: str) -> None:
        raise InputError("CLI 参数非法；使用 --help 查看固定接口，凭据不得通过命令行传入")


# 功能：构造真实 CLI；参数无，不提供 bypass/test-mode/host/port/token/launch 旁路。
def build_parser() -> SafeParser:
    parser: SafeParser = SafeParser(description="Mono Pipeline 逐条主动功能测试宿主（附加单目标、本地报告）", allow_abbrev=False)
    # 本机测试口径：跳过工具自身 91 成员清单核验（约 149ms/命令）。默认仍严格核验；
    # 包内文件字节是否逐成员比对由 target.json 的 integrity_mode 决定，二者独立。
    parser.add_argument("--no-self-check", action="store_true", help="本机测试跳过工具自身交付清单核验；不改变包完整性口径")
    parser.add_argument("--compact", action="store_true", help="仅精简 stdout 的重复观察信封与中间轮询值；journal、末样本、错误和退出码保持完整")
    commands: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(dest="operation", required=True)
    init: argparse.ArgumentParser = commands.add_parser("init", allow_abbrev=False, help="离线登记完整原用例、明确目标和输出")
    init.add_argument("--cases", required=True)
    init.add_argument("--target", required=True)
    init.add_argument("--output", required=True)
    init.add_argument("--provenance")
    init.add_argument("--parent")
    init.add_argument("--workflow-timing")
    init.add_argument("--workflow-parent-id")
    init.add_argument("--workflow-child-id")
    init.add_argument("--run-prefix", default="run", help="Agent 的明确功能编号前缀；统一统计时输出根为对应 feature 目录")
    output: argparse.ArgumentParser = commands.add_parser("output-check", allow_abbrev=False, help="只读核验候选输出的完整证据路径预算，不初始化或附加")
    output.add_argument("--output", required=True)
    output.add_argument("--run-prefix", default="run")
    start: argparse.ArgumentParser = commands.add_parser("start-case", allow_abbrev=False, help="开始一条原用例，无预制动作映射")
    start.add_argument("--run", required=True)
    start.add_argument("--case-id", required=True)
    start.add_argument("--group-id", default="ungrouped")
    for name in ("attach", "status", "audit", "report"):
        command: argparse.ArgumentParser = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--run", required=True)
    for name in ("chain-start", "chain-end", "observe", "action", "compare", "final", "attribute", "baseline", "reference", "collect-evidence", "note", "close"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--run", required=True)
        command.add_argument("--request", required=name != "close", help="当前 Agent 的本次请求 JSON；每次登记后不得改写")
    case: argparse.ArgumentParser = commands.add_parser(
        "run-case", allow_abbrev=False,
        help="在一条命令内顺序执行单例计划的全部步骤；校验与单命令完全一致，只省去重复建连与重复重放")
    case.add_argument("--run", required=True)
    case.add_argument("--plan", required=True, help="当前 Agent 的单例计划 JSON；登记后不得改写")
    suite: argparse.ArgumentParser = commands.add_parser(
        "run-suite", allow_abbrev=False,
        help="在一条命令、一次连接内顺序执行多例计划；每例仍独立 start-case/final，只省去重复建连与重复重放")
    suite.add_argument("--run", required=True)
    suite.add_argument("--plan", required=True, help="当前 Agent 的多例计划 JSON；登记后不得改写")
    check: argparse.ArgumentParser = commands.add_parser(
        "plan-check", allow_abbrev=False,
        help="只读静态校验单例/多例计划，不建连、不写业务事件、不消耗命令 ID；用于接触 Player 前一次性排错")
    check.add_argument("--run", required=True)
    check.add_argument("--plan", required=True, help="待校验的单例或多例计划 JSON；本命令不登记、不冻结")
    for name in ("request-check", "request-publish"):
        request_check: argparse.ArgumentParser = commands.add_parser(name, allow_abbrev=False, help="登记前核验单请求；publish 独占新建不可变请求，不执行 Player 动作")
        request_check.add_argument("--run", required=True)
        request_check.add_argument("--for-operation", required=True, choices=("chain-start", "chain-end", "observe", "action", "compare", "final", "start-case", "baseline", "note"))
        request_check.add_argument("--request", required=True)
        if name == "request-publish":
            request_check.add_argument("--output-dir", required=True)
    parent: argparse.ArgumentParser = commands.add_parser("context-init", allow_abbrev=False, help="创建由包内 writer 计时的明确父上下文")
    parent.add_argument("--output", required=True)
    for name in ("context-status", "context-close", "context-audit", "context-report"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--run", required=True)
    verify: argparse.ArgumentParser = commands.add_parser("delivery-verify", allow_abbrev=False, help="只读核验完整同包目录或 ZIP，失败不重建清单")
    verify.add_argument("--zip")
    export: argparse.ArgumentParser = commands.add_parser("delivery-export", allow_abbrev=False, help="新建完整可拖拽目录和可选 ZIP，不覆盖")
    export.add_argument("--output", required=True)
    export.add_argument("--zip")
    refresh: argparse.ArgumentParser = commands.add_parser("delivery-refresh", allow_abbrev=False, help="维护者显式离线生成/刷新清单")
    refresh.add_argument("--maintainer-approved", action="store_true")
    refresh.add_argument("--previous-manifest-sha256")
    preview: argparse.ArgumentParser = commands.add_parser("unity-preview", allow_abbrev=False, help="明确 Unity 根的只读首次接入预览")
    preview.add_argument("--project", required=True)
    preview.add_argument("--plan-output")
    apply: argparse.ArgumentParser = commands.add_parser("unity-apply", allow_abbrev=False, help="批准摘要+独立批准+项目/工具外新备份的文件接入，不编译/构建")
    apply.add_argument("--project", required=True)
    apply.add_argument("--approve-plan-sha256", required=True)
    apply.add_argument("--approved", action="store_true")
    apply.add_argument("--backup", required=True)
    scan: argparse.ArgumentParser = commands.add_parser("package-scan", allow_abbrev=False, help="真实扫描只生成 candidate，未确认完整交付")
    scan.add_argument("--exe", required=True)
    scan.add_argument("--output", required=True)
    manifest: argparse.ArgumentParser = commands.add_parser("package-manifest", allow_abbrev=False, help="成功 BuildReport 库存+明确完整交付审阅生成严格静态清单")
    manifest.add_argument("--exe", required=True)
    manifest.add_argument("--inventory", required=True)
    manifest.add_argument("--inventory-sha256", required=True)
    manifest.add_argument("--approval", required=True)
    manifest.add_argument("--output", required=True)
    prepare: argparse.ArgumentParser = commands.add_parser("target-prepare", allow_abbrev=False, help="明确 EXE/PID/许可，只读身份与公开配置准备，不连接 Player")
    prepare.add_argument("--exe", required=True)
    prepare.add_argument("--pid", required=True, type=int)
    prepare.add_argument("--permission-record", required=True)
    prepare.add_argument("--package-manifest")
    prepare.add_argument("--integrity-mode", default="full", choices=("full", "identity_only"),
                         help="full=逐成员核验全包字节；identity_only=只验 EXE/PID 创建时间/build_guid/端口独占")
    prepare.add_argument("--output", required=True)
    return parser


# 功能：解析本地 CLI 路径；参数 optional=True 允许未启用的 provenance/parent。
def argument_path(value: object, optional: bool = False, missing_leaf: bool = False) -> Path | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise InputError("CLI 必须提供明确本地路径")
    return local_path(value, Path.cwd(), missing_leaf)


# 功能：读取本次请求原字节；参数 path 在进入本轮 writer 后调用，文件不会成为静态全集计划。
def read_request(path: Path, limits: Limits) -> JsonObject:
    raw: bytes = read_regular(path, limits.input_bytes)
    result: JsonObject = object_value(strict_json(raw, limits.input_bytes, limits, bom=True), "CLI request")
    SecretGuard().check(result)
    return result


# 功能：基于公共四状态/回执选择退出码；参数 result 不改变已写入 journal 的结果。
def result_exit(operation: str, result: JsonObject) -> int:
    if operation == "output-check" and result.get("supported") is not True:
        return 3
    if operation == "unity-preview" and result.get("conflicts"):
        return 3
    if operation in {"final", "compare"}:
        return {"passed": 0, "failed": 1, "blocked": 3, "test_inconclusive": 4}.get(str(result.get("status")), 0)
    if operation == "run-case":
        # 单例计划以本例 final 收口；退出码沿用该 final 的四状态口径，不新增旁路语义。
        last: JsonValue = result.get("last_result")
        if isinstance(last, dict) and result.get("last_operation") == "final":
            return {"passed": 0, "failed": 1, "blocked": 3, "test_inconclusive": 4}.get(str(last.get("status")), 0)
    if operation == "run-suite":
        # 多例计划按"最差状态"取退出码：任一 failed 优先，其次 blocked，再其次 test_inconclusive，全 passed 才 0。
        statuses: JsonValue = result.get("statuses")
        if isinstance(statuses, list):
            for level in ("failed", "blocked", "test_inconclusive"):
                if level in statuses:
                    return {"failed": 1, "blocked": 3, "test_inconclusive": 4}[level]
            return 0
    receipt: JsonValue = result.get("receipt")
    if operation == "observe":
        if result.get("case_frozen") is True:
            return 4
        samples: JsonValue = result.get("samples")
        if isinstance(samples, list) and samples:
            receipt = object_value(samples[-1], "sample").get("receipt")
    if isinstance(receipt, dict):
        if operation == "observe" and receipt.get("state") == "succeeded" and result.get("completion_required") is True and result.get("poll_matched") is not True:
            return 4
        return {"unknown": 4, "compile_failed": 3, "not_sent": 3}.get(str(receipt.get("state")), 0)
    return 0


# 功能：生成面向 Agent 的简洁显示副本；参数原结果/journal 不修改，末样本与错误原文仍按原契约保留。
def compact_result(operation: str, result: JsonObject) -> JsonObject:
    display: JsonObject = dict(result)
    if operation == "observe" and isinstance(result.get("samples"), list):
        originals: list[JsonValue] = cast(list[JsonValue], result["samples"])
        samples: list[JsonValue] = []
        for index, raw in enumerate(originals):
            if not isinstance(raw, dict):
                samples.append(raw)
                continue
            sample: JsonObject = dict(raw)
            receipt: JsonValue = sample.get("receipt")
            if sample.get("observation_valid") is True and not sample.get("observation_error") and "value" in sample and isinstance(sample.get("observation_ref"), dict) and isinstance(receipt, dict) and receipt.get("state") == "succeeded":
                sample["receipt"] = {key: value for key, value in receipt.items() if key != "value"}
                sample["receipt_value_omitted"] = "duplicate envelope; see observation_ref"
                if index != len(originals) - 1:
                    sample.pop("value", None)
                    sample["value_omitted"] = "intermediate sample; see observation_ref"
            samples.append(sample)
        display["samples"] = samples
    return display


# 功能：从明确 argv 解析必须路径；参数 missing_leaf 只供新输出/备份，绝不猜测项目。
def required_path(value: object, missing_leaf: bool = False) -> Path:
    path: Path | None = argument_path(value, missing_leaf=missing_leaf)
    if path is None:
        raise InputError("离线命令缺少明确路径")
    return path


# 功能：分派同包离线交付/接入/准备命令；参数没有测试/身份/网络旁路，不进入 Player 会话。
def offline_command(operation: str, args: argparse.Namespace) -> JsonObject:
    root: Path = delivery.skill_root()
    if operation == "output-check":
        from .contracts import identifier
        prefix: str = identifier(args.run_prefix, "run prefix")
        output: Path = required_path(args.output, True)
        if output.is_relative_to(root):
            raise InputError("候选输出不能污染严格交付根")
        return run_path_budget(output / new_id(prefix))
    if operation == "delivery-verify":
        archive: Path | None = argument_path(args.zip, optional=True)
        return delivery.verify_delivery(root) if archive is None else delivery.verify_zip(archive)
    if operation == "delivery-export":
        return delivery.export_delivery(root, required_path(args.output, True), argument_path(args.zip, True, True))
    if operation == "delivery-refresh":
        return delivery.refresh_manifest(root, args.maintainer_approved, args.previous_manifest_sha256)
    if operation == "unity-preview":
        project: Path = required_path(args.project)
        result: JsonObject = delivery.unity_preview(root, project)
        output: Path | None = argument_path(args.plan_output, optional=True, missing_leaf=True)
        if output is not None:
            delivery.new_external(output, (root, project))
            delivery.write_new(output, canonical(result) + b"\n")
        return result
    if operation == "unity-apply":
        return delivery.unity_apply(root, required_path(args.project), args.approve_plan_sha256, args.approved, required_path(args.backup, True))
    if operation == "package-scan":
        return delivery.package_candidate(root, required_path(args.exe), required_path(args.output, True))
    if operation == "package-manifest":
        return delivery.prepare_package_manifest(root, required_path(args.exe), required_path(args.inventory), args.inventory_sha256,
                                                 required_path(args.approval), required_path(args.output, True))
    if operation == "target-prepare":
        return delivery.prepare_target(root, required_path(args.exe), args.pid, required_path(args.permission_record), required_path(args.output, True),
                                       argument_path(args.package_manifest, optional=True), None, args.integrity_mode)
    raise InputError("未登记离线命令")


# 功能：执行父本地状态/审计命令；参数 operation 不会导致子/父重复报告。
def parent_local(operation: str, root: Path) -> JsonObject:
    if operation == "context-close":
        return close_parent(root)
    if operation == "context-report":
        return render_parent(root)
    with Journal(root) as journal, local_cli_call(journal, operation) as response:
        if operation == "context-audit":
            result, paths = audit_parent(journal, require_closed=any(record["event"] == "parent_closed" for record in journal.records))
        else:
            if not journal.records or journal.records[0]["event"] != "parent_init":
                raise InputError("不是包内父上下文")
            result: JsonObject = {"invocation_id": journal.run_id,
                                  "closed": any(record["event"] == "parent_closed" for record in journal.records),
                                  "children": [record_data(record) for record in journal.records if record["event"] == "child_registered"]}
        response["result"] = result
        return result


# 功能：实际 CLI 主入口；参数 argv 仅供 Python 调用层测试，正式参数无任何身份/传输旁路。
def main(argv: list[str] | None = None) -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        args: argparse.Namespace = build_parser().parse_args(argv)
        operation: str = cast(str, args.operation)
        reject_links(Path(__file__).absolute())
        if operation not in {"delivery-refresh", "delivery-verify", "delivery-export", "unity-preview", "unity-apply", "package-scan", "package-manifest", "target-prepare"}:
            if not getattr(args, "no_self_check", False):
                delivery.verify_delivery(delivery.skill_root())
        if operation in {"output-check", "delivery-verify", "delivery-export", "delivery-refresh", "unity-preview", "unity-apply", "package-scan", "package-manifest", "target-prepare"}:
            result: JsonObject = offline_command(operation, args)
        elif operation == "init":
            cases: Path | None = argument_path(args.cases)
            target: Path | None = argument_path(args.target)
            output: Path | None = argument_path(args.output, missing_leaf=True)
            if cases is None or target is None or output is None:
                raise InputError("初始化缺少完整原用例/目标/输出")
            if output.is_relative_to(delivery.skill_root()):
                raise InputError("会话输出不能污染严格交付根")
            root: Path = initialize(cases, target, output, argument_path(args.provenance, True), argument_path(args.parent, True),
                                    argument_path(args.workflow_timing, True), args.workflow_parent_id, args.workflow_child_id, args.run_prefix)
            result: JsonObject = {"run": str(root), "run_id": root.name, "attached": False}
        elif operation == "context-init":
            output = argument_path(args.output, missing_leaf=True)
            if output is None:
                raise InputError("父上下文输出根缺失")
            if output.is_relative_to(delivery.skill_root()):
                raise InputError("父上下文输出不能污染严格交付根")
            root = initialize_parent(output)
            result = {"run": str(root), "invocation_id": root.name, "report_owner": "parent"}
        else:
            path: Path | None = argument_path(args.run)
            if path is None:
                raise InputError("本轮 --run 缺失")
            if operation.startswith("context-"):
                result = parent_local(operation, path)
            else:
                with Session(path) as session:
                    request_path: Path | None = None
                    request: JsonObject = {}
                    try:
                        if operation in {"run-case", "run-suite", "plan-check"}:
                            plan_path: Path | None = argument_path(args.plan)
                            if plan_path is None:
                                raise InputError("待处理计划路径缺失")
                            plan: JsonObject = read_request(plan_path, session.journal.limits)
                            session._request_base = plan_path.parent
                            if operation == "plan-check":
                                result = session.check_plan(plan)
                            elif operation == "run-case":
                                result = session.invoke_plan(plan, plan_path)
                            else:
                                result = session.invoke_suite(plan, plan_path)
                        elif operation in {"request-check", "request-publish"}:
                            request_path = required_path(args.request)
                            request = read_request(request_path, session.journal.limits)
                            result = session.check_request(args.for_operation, request, request_path.parent)
                            if operation == "request-publish":
                                published: Path = session.publish_request(args.for_operation, request, required_path(args.output_dir, True), request_path.parent)
                                result = {**result, "published_path": str(published), "sha256": digest(read_regular(published, session.journal.limits.input_bytes))}
                        elif operation == "start-case":
                            request = {"case_id": args.case_id, "group_id": args.group_id}
                        elif getattr(args, "request", None) is not None:
                            request_path = argument_path(args.request)
                            if request_path is None:
                                raise InputError("本次请求路径缺失")
                            request = read_request(request_path, session.journal.limits)
                    except HostError as exc:
                        if operation not in {"run-case", "run-suite", "plan-check", "request-check", "request-publish"}:
                            call_id = new_id("call")
                            session.journal.append("cli_begin", {"operation": operation, "call_id": call_id})
                            session.journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": False,
                                                                  "error_kind": type(exc).__name__, "message": str(exc)})
                        raise
                    # run-case/run-suite/plan-check 已在上面直接执行；其余单步命令才走普通 invoke。
                    if operation not in {"run-case", "run-suite", "plan-check", "request-check", "request-publish"}:
                        result = session.invoke(operation, request, request_path)
        SecretGuard().check(result)
        print(canonical({"ok": True, "operation": operation, "result": compact_result(operation, result) if args.compact else result}).decode("utf-8"))
        return result_exit(operation, result)
    except HostError as exc:
        message: str = SecretGuard().diagnostic(str(exc))
        print(canonical({"ok": False, "error_kind": type(exc).__name__, "message": message}).decode("utf-8"))
        return 5 if isinstance(exc, IntegrityError) else 4 if isinstance(exc, FrozenSession) else 3 if isinstance(exc, EnvironmentBlocked) else 2
    except (OSError, ValueError, TypeError, KeyError, MemoryError):
        print(canonical({"ok": False, "error_kind": "HostFailure", "message": "本地宿主输入/产物操作失败；原异常已排除"}).decode("utf-8"))
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
