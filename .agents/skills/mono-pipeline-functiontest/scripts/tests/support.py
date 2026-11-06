"""创建日期：2026-10-26；作者：Cyou。
功能：有真实负向回执和副作用计数的隔离夹具；参数：临时文件、身份 hooks、内存 HTTP。
说明：包成员是明确的测试字节，不是 Unity 可运行包；不编译、不连接真实进程。
"""
from __future__ import annotations

import base64
import json
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, cast

from ..contracts import SCHEMA, JsonObject, JsonValue, Limits, canonical, digest, object_value
from ..inputs import parse_cases
from ..pipeline import CATALOG_PATH, EXEC_PATH, STATUS_PATH, HttpResponse, IdentityHooks, Transport
from ..session import Session, initialize


# 功能：创建完整通用计数用例；参数 case_id 保留，步骤和两个数值预期均未映射动作。
def counter_case(case_id: str = "C-1") -> JsonObject:
    return {"case_id": case_id, "title": "计数与按配置扣减", "preconditions": [],
            "steps": ["触发一次计数增加"], "expected": ["计数严格增加 1", "库存扣减等于独立配置成本"],
            "priority": "P1", "metadata": {"preserve": [False, 0, "完整原字段"]}}


# 功能：创建纯只读用例；参数 case_id 不与动作例共用 final。
def readonly_case(case_id: str = "R-1") -> JsonObject:
    return {"case_id": case_id, "title": "读取当前计数", "preconditions": [],
            "steps": ["读取当前计数"], "expected": ["当前计数为 3"]}


# 功能：构造真实外/内层 eval 格式；参数 command 外层区分 eval_file，内层固定 eval。
def eval_response(command: str, value: JsonValue = None, state: str = "succeeded",
                  diagnostic: str = "fixture diagnostic") -> HttpResponse:
    evaluation: JsonObject = {"command": "eval", "success": state == "succeeded", "diagnostics": [],
                              "result": value, "output": None, "error": None, "errorDetails": None}
    if state == "compile_failed":
        evaluation.update({"success": False, "error": "Compilation Failed", "errorDetails": diagnostic,
                           "diagnostics": [{"severity": "error", "id": "CS0246", "message": diagnostic, "line": 0, "column": 0}]})
    elif state == "runtime_error":
        evaluation.update({"success": False, "error": "Runtime Error", "errorDetails": diagnostic})
    elif state == "script_failed":
        evaluation.update({"success": False, "error": None, "errorDetails": diagnostic})
    return HttpResponse(200, {"command": command, "success": True, "result": evaluation,
                              "executionTimeMs": 1, "error": None, "errorDetails": None})


@dataclass
class World:
    """可增加计数、扣错费、编译失败、部分生效后异常/断连以及返回旧帧的内存世界。"""

    build_guid: str = "fixture-build-v1"
    unity_version: str = "2022.3.62f3"
    target: str = "fixture.target"
    counter: int = 3
    stock: int = 20
    cost: int = 4
    charge_multiplier: int = 1
    frame: int = 10
    action_count: int = 0
    setup_count: int = 0
    eval_count: int = 0
    fail_next: str = ""
    old_frame: bool = False
    missing_target: bool = False
    returned_value: JsonValue = None
    override_read: bool = False
    mono: bool = True
    development: bool = True
    wrong_runtime_identity: bool = False
    wrong_envelope_identity: bool = False
    return_value_error: str | None = None
    transport_count: int = 0
    close_count: int = 0
    requests: list[tuple[str, JsonObject | None, int]] = field(default_factory=list)
    token: str = field(default_factory=lambda: base64.b64encode(bytes(range(32))).decode("ascii"), repr=False)
    heartbeat_writer: Callable[[], str] | None = field(default=None, repr=False)
    # 读取求值的模拟耗时（秒）；0 表示即时返回。超过本次请求 timeout_ms 时按真实传输超时抛出，用于复现小剩余预算样本超时（2026-11-04）。
    read_delay_s: float = 0.0

    # 功能：返回当前业务字段；参数无，不提供 success/assertion 伪断言。
    def business(self) -> JsonObject:
        return {"counter": self.counter, "stock": self.stock, "unique_count": 1,
                "enabled": not self.missing_target, "loaded_types": ["Fixture.Business"]}

    # 功能：从实际包装读取固定宿主身份；参数 code 是通过真实冻结文件读取的字节文本。
    def host(self, code: str, value: JsonValue) -> JsonObject:
        identity: JsonObject = {"host": SCHEMA, "frame": self.frame, "build_guid": self.build_guid, "value": value}
        if code.startswith("// mono-pipeline-wrapper/2\n"):
            identity["value_error"] = self.return_value_error
            if self.return_value_error is not None:
                identity["value"] = None
        for key in ("run_id", "case_id", "command_id"):
            match: re.Match[str] | None = re.search(r'\{"' + key + r'", ("(?:[^"\\]|\\.)*")\}', code)
            if match is None:
                raise AssertionError("实际发送包装缺少固定身份")
            identity[key] = json.loads(match.group(1))
        if self.wrong_envelope_identity:
            identity["build_guid"] = "wrong-fixture-build"
        return identity

    # 功能：提供注入传输，仍走生产 Pipeline 和公共回执分类；参数 token 不写入 requests。
    def transport(self, port: int, token: str, limits: Limits) -> Transport:
        if token != self.token:
            raise AssertionError("宿主未使用描述符内存凭据")
        self.transport_count += 1
        return FakeTransport(self, limits, port)


class FakeTransport:
    """不建立 socket 的有限状态 HTTP 回执提供者，包含真正的失败分类输入。"""

    # 功能：保存内存世界；参数 limits/port 与正式已验证目标相同。
    def __init__(self, world: World, limits: Limits, port: int) -> None:
        self.world: World = world
        self.limits: Limits = limits
        self.port: int = port

    # 功能：只释放注入传输；参数无，不启动或结束进程。
    def close(self) -> None:
        self.world.close_count += 1

    # 功能：返回实际固定 API 结构及负向回执；参数 body 是正式宿主真正发送的一次请求。
    def request(self, path: str, body: JsonObject | None, timeout_ms: int) -> HttpResponse:
        self.world.requests.append((path, body, timeout_ms))
        if path == STATUS_PATH:
            heartbeat: str = self.world.heartbeat_writer() if self.world.heartbeat_writer is not None else datetime.now(timezone.utc).isoformat()
            return HttpResponse(200, {"status": "ready", "lastHeartbeat": heartbeat,
                                       "capabilities": ["exec.argv", "exec.commandLine"]})
        if path == CATALOG_PATH:
            commands: list[JsonValue] = [{"name": name, "description": "fixture", "tags": [], "package": "fixture"}
                                         for name in ("runtime_status", "eval", "eval_file")]
            return HttpResponse(200, {"commands": commands, "count": 3, "total": 3, "offset": 0, "limit": 1000,
                                      "server": {"port": self.port, "version": "fixture", "startTime": datetime.now(timezone.utc).isoformat()}})
        if path != EXEC_PATH or body is None:
            raise AssertionError("请求没有走真实固定 API")
        command: str = str(body["command"])
        if command == "runtime_status":
            return HttpResponse(200, {"success": True, "command": command, "result": {
                "BuildGuid": "wrong-build" if self.world.wrong_runtime_identity else self.world.build_guid,
                "UnityVersion": self.world.unity_version, "Platform": "WindowsPlayer", "IsPlaying": True,
                "FrameCount": self.world.frame, "PipelineDriver": {"IsServerRunning": True, "ActualPort": self.port},
            }})
        parameters: JsonObject = object_value(body["parameters"], "parameters")
        code: str = str(parameters["code"]) if command == "eval" else Path(str(parameters["file"])).read_bytes().decode("utf-8")
        action_code: bool = "MPFT_TEST_ACTION" in code or "// mono-pipeline-builtin-click/1" in code
        self.world.eval_count += 1
        probe: bool = "System.Type.GetType(\"Mono.Runtime\")" in code
        if probe:
            self.world.frame += 1
            return eval_response(command, self.world.host(code, {"mono": self.world.mono, "development": self.world.development,
                "discovery": {"op": "chain", "count": 1, "truncated": False,
                    "nodes": [{"path": "FixtureRoot", "name": "FixtureRoot", "active": True}]}}))
        failure: str = self.world.fail_next
        self.world.fail_next = ""
        if failure == "compile":
            return eval_response(command, state="compile_failed", diagnostic="CS0246: fixture business metadata unavailable")
        if failure in {"runtime", "script", "disconnect", "timeout", "unexpected_exception", "keyboard"}:
            if action_code:
                self.world.action_count += 1
                self.world.counter += 1
                self.world.stock -= self.world.cost
            if failure == "runtime":
                return eval_response(command, state="runtime_error", diagnostic="部分副作用之后的测试运行异常")
            if failure == "script":
                return eval_response(command, state="script_failed", diagnostic="本次求值已确认，片段反射实例类型不一致")
            if failure == "unexpected_exception":
                raise RuntimeError(self.world.token)
            if failure == "keyboard":
                raise KeyboardInterrupt()
            if failure == "timeout":
                raise TimeoutError(self.world.token)
            raise OSError(self.world.token)
        if failure == "invalid_response":
            return HttpResponse(200, {"success": True, "command": command, "result": {"success": True, "diagnostics": []}})
        if self.world.read_delay_s > 0 and not action_code and "MPFT_TEST_SETUP" not in code:
            if self.world.read_delay_s * 1000 > timeout_ms:
                time.sleep(timeout_ms / 1000)
                raise TimeoutError(self.world.token)
            time.sleep(self.world.read_delay_s)
        if not self.world.old_frame:
            self.world.frame += 1
        if action_code:
            self.world.action_count += 1
            self.world.counter += 1
            self.world.stock -= self.world.cost * self.world.charge_multiplier
            value: JsonValue = {"success": True, "assertion": True}
        elif "MPFT_TEST_SETUP" in code:
            self.world.setup_count += 1
            self.world.stock = 20
            value = "setup_called"
        else:
            value = self.world.returned_value if self.world.override_read else self.world.business()
            if not self.world.override_read and '{"op", "buttons"}' in code:
                value = {"op": "buttons", "count": 1, "truncated": False, "nodes": [{
                    "path": "FixtureRoot/Container/Button", "active": True, "enabled": True,
                    "interactable": not self.world.missing_target, "effective_interactable": not self.world.missing_target,
                    "button_count": 1, "node_instance_id": -30, "instance_id": -31,
                    "component_type": "GameButton", "click_method": "InvokeOnClickListener", "text": "Synthetic Button"}]}
        if "MPFT_TEST_BRIDGE" in code:
            value = canonical({"bridge": SCHEMA, "frame": self.world.frame, "build_guid": self.world.build_guid,
                               "value": value, "error": "target_missing" if self.world.missing_target else None,
                               "target": self.world.target}).decode("utf-8")
        envelope: JsonObject = self.world.host(code, value)
        if failure == "return_contract":
            envelope.update({"value": None, "value_error": "unsupported_return_type"})
        return eval_response(command, envelope)


class Fixture:
    """每个测试专属临时目录，只清理自己创建的临时文件，不接触旧资产。"""

    # 功能：构造完整静态测试包、来源与假身份；参数 cases/permissions/limits 可产生负向环境。
    def __init__(self, cases: list[JsonValue] | None = None, permissions: list[JsonValue] | None = None,
                 limits: JsonObject | None = None) -> None:
        self.temporary: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="mpft-isolated-")
        self.root: Path = Path(self.temporary.name)
        self.package: Path = self.root / "package"
        self.package.mkdir()
        self.world: World = World()
        self.exe: Path = self.package / "Fixture.exe"
        members: dict[str, bytes] = {
            "Fixture.exe": b"MZ-isolated-not-a-runnable-player",
            "UnityPlayer.dll": b"isolated-placeholder",
            "Fixture_Data/globalgamemanagers": b"isolated-global",
            "Fixture_Data/boot.config": b"player-connection-debug=1\n",
            "Fixture_Data/Managed/Assembly-CSharp.dll": b"isolated-bridge-placeholder",
            "Fixture_Data/Managed/Unity.Pipeline.dll": b"isolated-pipeline-placeholder",
            "MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll": b"isolated-mono-placeholder",
        }
        for name, raw in members.items():
            path: Path = self.package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.manifest: Path = self.write_json("package-manifest.json", {
            "schema": "mono-pipeline-package/1", "backend": "mono", "development": True, "complete": True,
            "exe": self.exe.name, "build_guid": self.world.build_guid, "unity_version": self.world.unity_version,
            "platform": "WindowsPlayer", "files": [{"path": name, "bytes": len(raw), "sha256": digest(raw)} for name, raw in members.items()],
        })
        self.license: Path = self.root / "license.txt"
        self.license.write_text("创建日期：2026-10-26；作者：Cyou；仅为隔离测试的临时许可夹具。", encoding="utf-8")
        self.created: str = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.descriptor: Path = self.package / ".unity-pipeline-runtime-port"
        self.refresh_descriptor()
        self.world.heartbeat_writer = self.refresh_descriptor
        self.target_file: Path = self.write_json("target.json", {
            "schema": "mono-pipeline-target/1", "exe": str(self.exe), "pid": 123456, "port": 7901,
            "process_created_utc": self.created, "build_guid": self.world.build_guid, "unity_version": self.world.unity_version,
            "platform": "WindowsPlayer", "package_manifest": str(self.manifest),
            "license": {"path": str(self.license), "sha256": digest(self.license.read_bytes()), "accepted": True, "scope": "isolated_fixture_only"},
            "permissions": permissions if permissions is not None else ["attach", "script_execute", "business_action", "setup_action", "log_read", "screenshot"],
            "evidence_roots": [str(self.root)], "limits": limits if limits is not None else {},
        })
        self.cases_file: Path = self.write_json("cases.json", {"cases": cases if cases is not None else [counter_case()],
                                                                "source_metadata": {"must_preserve": {"revision": 7}}})
        self.original = parse_cases(self.cases_file.read_bytes())
        self.run: Path = initialize(self.cases_file, self.target_file, self.root / "output")
        self.hooks: IdentityHooks = IdentityHooks(self.process, self.port, self.acl)

    # 功能：清理仅本夹具临时目录；参数无，不清理项目文件。
    def cleanup(self) -> None:
        self.temporary.cleanup()

    # 功能：生成临时严格 JSON 原文件；参数 value 保持所有输入字段。
    def write_json(self, name: str, value: JsonValue) -> Path:
        path: Path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical(value))
        return path

    # 功能：生成临时用户方法体片段；参数 marker 仅由内存后端识别，不执行真实 C#。
    def script(self, name: str, marker: str = "READ") -> Path:
        path: Path = self.root / (name + ".cs")
        path.write_bytes(("// 创建日期：2026-10-26；作者：Cyou；功能：隔离传输夹具；参数：内存 marker。\n"
                          "// MPFT_TEST_" + marker + "\nreturn null;\n").encode("utf-8"))
        return path

    # 功能：刷新仅临时假描述符并返回同一落盘时间；参数无，真实身份查询从不执行。
    def refresh_descriptor(self) -> str:
        now: str = datetime.now(timezone.utc).isoformat()
        self.descriptor.write_bytes(canonical({"pid": 123456, "port": 7901, "platform": "WindowsPlayer",
                                                "unityVersion": self.world.unity_version, "buildGuid": self.world.build_guid,
                                                "startedAt": self.created, "lastHeartbeat": now,
                                                "workingDirectory": str(self.package), "evalToken": self.world.token}))
        return now

    # 功能：返回测试调用层假进程身份；参数必须精确对应临时声明。
    def process(self, pid: int, exe: Path, timeout_ms: int) -> JsonObject:
        return {"pid": pid, "exe": str(exe), "created": self.created}

    # 功能：返回假端口独占所有者；参数仅测试明确端口，绝不访问 TCP。
    def port(self, pid: int, port: int, timeout_ms: int) -> JsonObject:
        return {"listeners": [{"pid": pid, "address": "0.0.0.0"}]}

    # 功能：只读注入描述符 ACL 元数据，绝不刷新心跳；参数 path 是本夹具文件。
    def acl(self, path: Path, timeout_ms: int) -> JsonObject:
        return {"checked": True, "policy": "current_user_system_administrators_only",
                "owner": "fixture-owner", "principal": "fixture-owner", "readable_sids": ["fixture-owner"]}

    # 功能：打开生产 Session 仅替换身份/传输依赖；参数无。
    def session(self) -> Session:
        return Session(self.run, self.hooks, self.world.transport)

    # 功能：按现场需要构建一次读取请求；参数 after 必须明确对应本例最后动作。
    def observe(self, session: Session, command_id: str = "read-before", observation_id: str = "before",
                after: str | None = None, covers: bool = False, marker: str = "READ",
                scope: str = "step", index: int = 1, poll: JsonObject | None = None, purpose: str | None = None) -> JsonObject:
        case_id: str = str(session.state.current)
        original = self.original.case(case_id)
        request: JsonObject = {"command_id": command_id, "observation_id": observation_id,
                               "script": str(self.script(command_id, marker)), "send": "eval_file", "scope": scope,
                               "purpose": "after" if after is not None else "step" if covers else "before",
                               "target": self.world.target, "read_only_review": "当前 Agent 审核：本片段只返回业务字段",
                               "reason": "依据当前字段动态定位，不是预制动作映射", "covers_step": covers,
                               "value_format": "bridge" if "BRIDGE" in marker else "json"}
        if scope != "discovery":
            request.update({"index": index, "original_text": original.item(scope, index).text})
        if after is not None:
            request["after_command_id"] = after
        if poll is not None:
            request["poll"] = poll
        if purpose is not None:
            request["purpose"] = purpose
        return session.invoke("observe", request)

    # 功能：构建一条原预期/前置/守卫比较；参数 expected 是独立原文解释，不来自动作回执。
    def comparison(self, comparison_id: str, observation_id: str, field: str, expected: JsonValue,
                   scope: str = "expected", index: int = 1, operator: str = "eq", before: str | None = None,
                   case_id: str = "C-1") -> JsonObject:
        original = self.original.case(case_id)
        result: JsonObject = {"schema": "mono-pipeline-comparison/1", "comparison_id": comparison_id,
                              "scope": scope, "index": index, "original_text": original.item(scope, index).text,
                              "step_indices": [original.steps[0].index], "observation_id": observation_id,
                              "field": field, "operator": operator, "basis": {
                                  "kind": "literal", "value": expected, "reviewer": "current_agent",
                                  "statement": "独立原用例文本要求的精确值/增量，不使用实际值反推",
                                  "semantic_review": "当前 Agent 全量核对原文到本条业务比较；不声明机器证明语义",
                              }}
        if before is not None:
            result["before"] = {"observation_id": before, "field": field}
        return result

    # 功能：以实际唯一目标及可操作值注册动作守卫；参数 observation_id 必须为本例 before。
    def guards(self, session: Session, observation_id: str = "before", prefix: str = "guard") -> list[JsonValue]:
        case_id: str = str(session.state.current)
        identifiers: list[JsonValue] = []
        for suffix, field, expected in (("unique", "/unique_count", 1), ("enabled", "/enabled", True)):
            comparison_id: str = prefix + "-" + suffix
            session.invoke("compare", self.comparison(comparison_id, observation_id, field, expected,
                                                       "guard", case_id=case_id))
            identifiers.append(comparison_id)
        return identifiers

    # 功能：构建并执行一次现场动作；参数 index/scope 绑定原步骤或合法前置。
    def action(self, session: Session, guards: list[JsonValue], command_id: str = "action-one",
               before: str = "before", scope: str = "step", index: int = 1,
               correction_of: str | None = None, script_file: Path | None = None) -> JsonObject:
        case_id: str = str(session.state.current)
        original = self.original.case(case_id)
        script: Path = script_file if script_file is not None else self.script(command_id, "ACTION" if scope == "step" else "SETUP")
        request: JsonObject = {"command_id": command_id, "script": str(script),
                               "send": "eval_file", "scope": scope, "index": index, "original_text": original.item(scope, index).text,
                               "target": self.world.target, "before_observation_id": before, "guard_comparison_ids": guards,
                               "target_review": "当前唯一目标计数为 1，实际 enabled 守卫已独立通过",
                               "reason": "授权内只触发一次，之后必须返回宿主独立新帧观察"}
        if correction_of is not None:
            request.update({"correction_of": correction_of, "correction_reason": "仅修正明确未执行的片段编译问题，不变更原绑定"})
        return session.invoke("action", request)

    # 功能：登记独立配置基线；参数 cost 未从 after 值导出。
    def baseline(self, session: Session) -> None:
        path: Path = self.write_json("configuration.json", {"cost": self.world.cost})
        session.invoke("baseline", {"reference_id": "configuration", "kind": "configuration", "path": str(path),
                                    "sha256": digest(path.read_bytes()), "review": "需求指定按当前独立配置成本扣减；临时夹具原字节已审核"})

    # 功能：按原预期验证本例两个精确增量；参数 after/before 是独立读取 ID。
    def assert_changes(self, session: Session, after: str = "after", before: str = "before") -> tuple[JsonObject, JsonObject]:
        case_id: str = str(session.state.current)
        counter: JsonObject = session.invoke("compare", self.comparison("expect-counter", after, "/counter", 1, operator="delta", before=before, case_id=case_id))
        cost: JsonObject = self.comparison("expect-stock", after, "/stock", -self.world.cost, index=2, operator="delta", before=before, case_id=case_id)
        cost["basis"] = {"kind": "baseline", "reference_id": "configuration", "field": "/cost", "factor": -1,
                          "reviewer": "current_agent", "statement": "扣费必须来自独立配置原字节，而非点击成功或输出本身",
                          "semantic_review": "库存 after-before 应为配置成本的负值，与原预期逐字核对"}
        stock: JsonObject = session.invoke("compare", cost)
        return counter, stock

    # 功能：完成无预制映射的最小主动闭环；参数不生成静态计划，逐次消费返回值。
    def execute_counter(self, session: Session) -> tuple[JsonObject, JsonObject]:
        session.invoke("attach", {})
        session.invoke("start-case", {"case_id": self.original.cases[0].case_id})
        self.baseline(session)
        self.observe(session)
        guards: list[JsonValue] = self.guards(session)
        self.action(session, guards)
        self.observe(session, "read-after", "after", "action-one")
        return self.assert_changes(session)
