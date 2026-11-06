"""创建日期：2026-10-28；作者：Cyou。
功能：复现被动描述符在人工间隔后与连接前新鲜度核验互锁，验证安全探活与不重放。
参数：短目录假包、只读 ACL/身份 hooks 及协议响应；不连接实际 Player、不修改历史轮次。
"""
from __future__ import annotations

import base64
import json
import threading
import time
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from ..contracts import EnvironmentBlocked, FrozenSession, InputError, JsonObject, JsonValue, Limits, canonical, object_value, strict_json
from ..inputs import TargetConfig, parse_target
from ..pipeline import CATALOG_PATH, EXEC_PATH, HttpResponse, IdentityHooks, Pipeline, Transport, verify_target, verify_target_identity
from ..session import Session
from .support import FakeTransport, Fixture

STATUS_ENDPOINT = "/api/status"


class PassiveFixture(Fixture):
    """描述符仅在状态请求到达时更新；ACL 和进程查询不改磁盘。"""

    # 功能：构造无自动心跳的协议夹具；参数无，所有文件由原 Fixture 临时目录持有。
    def __init__(self) -> None:
        super().__init__()
        self.target: TargetConfig = parse_target(strict_json(self.target_file.read_bytes(), Limits().input_bytes), self.root)
        self.status_calls: int = 0
        self.status_code: int = 200
        self.persist_heartbeat: bool = True
        self.on_status: Callable[[], None] | None = None
        self.status_payload: JsonObject | None = None

    # 功能：返回只读 ACL 证据；参数 path/timeout_ms 不触发心跳或任何文件更新。
    def acl(self, path: Path, timeout_ms: int) -> JsonObject:
        return {"checked": True, "policy": "current_user_system_administrators_only",
                "owner": "fixture-owner", "principal": "fixture-owner", "readable_sids": ["fixture-owner"]}

    # 功能：只让最后心跳停在指定过去；参数 seconds 为已知测试间隔，不等待实际进程。
    def idle(self, seconds: int) -> None:
        document: JsonObject = object_value(strict_json(self.descriptor.read_bytes(), Limits().descriptor_bytes), "fixture descriptor")
        document["lastHeartbeat"] = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()
        self.descriptor.write_bytes(canonical(document))

    # 功能：创建一次内存传输；参数必须与本夹具显式端口及描述符凭据匹配。
    def transport(self, port: int, token: str, limits: Limits) -> Transport:
        if port != self.target.port or token != self.world.token:
            raise AssertionError("未使用本夹具已经核验的端口/凭据")
        self.world.transport_count += 1
        return PassiveTransport(self, limits, port)

    # 功能：重新打开同一真实宿主根且保留被动协议；参数无，不恢复冻结会话。
    def session(self) -> Session:
        return Session(self.run, self.hooks, self.transport)


class PassiveTransport(FakeTransport):
    """复用正常命令回执，只为真实基本状态端点实现请求驱动心跳。"""

    # 功能：持有本例协议状态；参数 limits/port 与正式 Pipeline 传输构造相同。
    def __init__(self, fixture: PassiveFixture, limits: Limits, port: int) -> None:
        super().__init__(fixture.world, limits, port)
        self.fixture: PassiveFixture = fixture

    # 功能：状态请求才刷新描述符，其他命令保持原协议；参数不会发送真实 HTTP。
    def request(self, path: str, body: JsonObject | None, timeout_ms: int) -> HttpResponse:
        if path != STATUS_ENDPOINT:
            return super().request(path, body, timeout_ms)
        self.world.requests.append((path, body, timeout_ms))
        self.fixture.status_calls += 1
        heartbeat: str = datetime.now(timezone.utc).isoformat()
        if self.fixture.persist_heartbeat:
            document: JsonObject = object_value(strict_json(self.fixture.descriptor.read_bytes(), self.limits.descriptor_bytes), "fixture descriptor")
            document["lastHeartbeat"] = heartbeat
            self.fixture.descriptor.write_bytes(canonical(document))
        if self.fixture.on_status is not None:
            self.fixture.on_status()
        payload: JsonObject = self.fixture.status_payload if self.fixture.status_payload is not None else {
            "status": "ready", "lastHeartbeat": heartbeat, "capabilities": ["exec.argv", "exec.commandLine"]}
        return HttpResponse(self.fixture.status_code, payload)


class DescriptorHeartbeatTests(unittest.TestCase):
    """覆盖首次/后续闲置、假成功和门禁失败，不由身份 hook 修复被测状态。"""

    # 功能：创建独立被动心跳夹具；参数 self 为测试实例，结束自动清理自有目录。
    def fixture(self) -> PassiveFixture:
        fixture: PassiveFixture = PassiveFixture()
        self.addCleanup(fixture.cleanup)
        return fixture

    # 功能：既有 ACL 夹具不得写心跳，避免掩盖真实故障；参数 self 为测试实例。
    def test_shared_acl_hook_does_not_refresh_heartbeat(self) -> None:
        fixture: Fixture = Fixture()
        self.addCleanup(fixture.cleanup)
        original: bytes = fixture.descriptor.read_bytes()
        fixture.acl(fixture.descriptor, Limits().identity_timeout_ms)
        self.assertEqual(fixture.descriptor.read_bytes(), original)

    # 功能：静置 60 秒后仅用认证状态刷新并完成正常握手；参数 self 为测试实例，不运行业务求值。
    def test_initial_connect_after_idle_60_seconds(self) -> None:
        fixture: PassiveFixture = self.fixture()
        fixture.idle(60)
        pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
        self.addCleanup(pipeline.close)
        identity: JsonObject = pipeline.connect()
        self.assertEqual(fixture.status_calls, 1)
        self.assertTrue(identity["authenticated"])
        self.assertEqual(fixture.world.eval_count, 0)
        self.assertEqual(fixture.world.requests[0][0], STATUS_ENDPOINT)

    # 功能：同一合法连接闲置 5 分钟后发送前核验仍可工作；参数 self 为测试实例，无重连或脚本重放。
    def test_preflight_after_idle_300_seconds(self) -> None:
        fixture: PassiveFixture = self.fixture()
        pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
        self.addCleanup(pipeline.close)
        pipeline.connect()
        fixture.idle(300)
        pipeline.preflight()
        self.assertEqual(fixture.status_calls, 2)
        self.assertEqual(fixture.world.transport_count, 1)
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：只读探活未授权也不能重试或发送求值；参数 self 为测试实例。
    def test_status_401_rejects_without_eval_or_retry(self) -> None:
        fixture: PassiveFixture = self.fixture()
        fixture.idle(60)
        fixture.status_code = 401
        pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
        with self.assertRaises(EnvironmentBlocked):
            pipeline.connect()
        self.assertEqual(fixture.status_calls, 1)
        self.assertEqual(fixture.world.eval_count, 0)
        self.assertIsNone(pipeline.transport)

    # 功能：HTTP 声称成功但落盘心跳没更新必须拒绝；参数 self 为测试实例，不降低新鲜度门槛。
    def test_probe_does_not_replace_persisted_freshness_check(self) -> None:
        fixture: PassiveFixture = self.fixture()
        fixture.idle(60)
        fixture.persist_heartbeat = False
        pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
        with self.assertRaises(EnvironmentBlocked):
            pipeline.connect()
        self.assertEqual(fixture.status_calls, 1)
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：严格本地核验仍拒绝过期，离线静态身份只作准备诊断；参数 self 为测试实例。
    def test_strict_verifier_stays_strict_while_preparation_is_local(self) -> None:
        fixture: PassiveFixture = self.fixture()
        fixture.idle(60)
        with self.assertRaises(EnvironmentBlocked):
            verify_target(fixture.target, fixture.hooks)
        prepared = verify_target_identity(fixture.target, fixture.hooks)
        self.assertFalse(prepared.evidence["descriptor_fresh"])
        self.assertEqual(fixture.world.transport_count, 0)

    # 功能：初始描述符的任何非心跳身份错误在探活前拒绝；参数 self 为测试实例，覆盖凭据/构建/时序。
    def test_invalid_descriptor_never_receives_probe(self) -> None:
        changes: list[tuple[str, JsonValue]] = [
            ("pid", 123457), ("port", 7902), ("evalToken", "not-base64"), ("buildGuid", "another-build"),
            ("unityVersion", "another-version"), ("platform", "LinuxPlayer"), ("workingDirectory", "not-this-package"),
            ("lastHeartbeat", "2000-01-01T00:00:00+00:00"),
            ("lastHeartbeat", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()),
        ]
        for key, value in changes:
            with self.subTest(field=key, value_index=changes.index((key, value))):
                fixture: PassiveFixture = self.fixture()
                fixture.idle(60)
                document: JsonObject = object_value(strict_json(fixture.descriptor.read_bytes(), Limits().descriptor_bytes), "fixture descriptor")
                document[key] = value
                fixture.descriptor.write_bytes(canonical(document))
                pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
                with self.assertRaises((EnvironmentBlocked, InputError)):
                    pipeline.connect()
                self.assertEqual(fixture.world.transport_count, 0)
                self.assertEqual(fixture.status_calls, 0)

    # 功能：探活后描述符改写/删除不被心跳更新掩盖；参数 self 为测试实例，非心跳变化只允许拒绝。
    def test_probe_rejects_descriptor_rewrite_or_delete(self) -> None:
        for field in ("startedAt", "evalToken", "capabilities", "delete"):
            with self.subTest(field=field):
                fixture: PassiveFixture = self.fixture()
                fixture.idle(60)
                # 功能：模拟探活过程中的外部文件变化；参数从本轮夹具捕获，不接触实际描述符。
                def changed() -> None:
                    if field == "delete":
                        fixture.descriptor.unlink()
                        return
                    document: JsonObject = object_value(strict_json(fixture.descriptor.read_bytes(), Limits().descriptor_bytes), "fixture descriptor")
                    replacement: JsonValue = (datetime.fromisoformat(fixture.created) + timedelta(seconds=1)).isoformat()
                    if field == "evalToken":
                        replacement = base64.b64encode(bytes(reversed(range(32)))).decode("ascii")
                    elif field == "capabilities":
                        replacement = ["changed-capability"]
                    document[field] = replacement
                    fixture.descriptor.write_bytes(canonical(document))
                fixture.on_status = changed
                pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
                with self.assertRaises(EnvironmentBlocked):
                    pipeline.connect()
                self.assertEqual(fixture.status_calls, 1)
                self.assertEqual(fixture.world.eval_count, 0)
                self.assertIsNone(pipeline.transport)

    # 功能：同目标凭据改变时不把旧连接用于刷新新身份；参数 self 为测试实例。
    def test_preflight_identity_change_is_rejected_before_probe(self) -> None:
        fixture: PassiveFixture = self.fixture()
        pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
        pipeline.connect()
        fixture.idle(60)
        document: JsonObject = object_value(strict_json(fixture.descriptor.read_bytes(), Limits().descriptor_bytes), "fixture descriptor")
        document["evalToken"] = base64.b64encode(bytes(reversed(range(32)))).decode("ascii")
        fixture.descriptor.write_bytes(canonical(document))
        with self.assertRaises(EnvironmentBlocked):
            pipeline.preflight()
        self.assertEqual(fixture.status_calls, 1)
        self.assertEqual(fixture.world.eval_count, 0)
        self.assertIsNone(pipeline.transport)

    # 功能：畸形/敏感响应及超时只发送一次状态请求；参数 self 为测试实例，不依赖后续回执掩盖错误。
    def test_bad_probe_protocol_and_timeout_do_not_retry(self) -> None:
        responses: list[JsonObject] = [{}, {"status": "error", "lastHeartbeat": datetime.now(timezone.utc).isoformat()},
            {"status": "ready", "lastHeartbeat": "not-a-time"},
            {"status": "ready", "lastHeartbeat": datetime.now(timezone.utc).isoformat(), "capabilities": None},
            {"status": "ready", "lastHeartbeat": datetime.now(timezone.utc).isoformat(), "unexpected": True}]
        for payload in responses:
            with self.subTest(keys=sorted(payload)):
                fixture: PassiveFixture = self.fixture()
                fixture.status_payload = payload
                pipeline: Pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
                with self.assertRaises(EnvironmentBlocked):
                    pipeline.connect()
                self.assertEqual(fixture.status_calls, 1)
                self.assertEqual(fixture.world.eval_count, 0)
        fixture = self.fixture()
        # 功能：返回包含假令牌的传输异常供脱敏验证；参数无，不发送实际网络。
        def timeout() -> None:
            raise TimeoutError(fixture.world.token)
        fixture.on_status = timeout
        pipeline = Pipeline(fixture.target, fixture.hooks, fixture.transport)
        with self.assertRaises(EnvironmentBlocked) as caught:
            pipeline.connect()
        self.assertNotIn(fixture.world.token, str(caught.exception))
        self.assertEqual(fixture.status_calls, 1)
        self.assertEqual(fixture.world.eval_count, 0)

    # 功能：重新打开 CLI 等价 Session 后，5 分钟人工间隔不会冻结合法读取；参数 self 为测试实例。
    def test_reloaded_session_idle_keeps_reading_without_business_action(self) -> None:
        fixture: PassiveFixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
            fixture.observe(session)
        fixture.idle(300)
        with fixture.session() as session:
            observed: JsonObject = fixture.observe(session, "read-next", "next")
            samples = observed["samples"]
            self.assertIsInstance(samples, list)
            self.assertTrue(samples[-1]["observation_valid"])
            self.assertFalse(session.state.frozen)
        # 每条 CLI 命令只握手一次：同命令内的后续步骤复用已核验连接；每条命令仍各自重连并重验身份。
        self.assertEqual(fixture.status_calls, 2)
        # 读取次数与业务副作用不受影响：两次命令仍各发一次真实读取，且无任何业务动作。
        self.assertEqual(fixture.world.eval_count, 3)
        self.assertEqual(fixture.world.action_count, 0)

    # 功能：已附加会话探活失败仍永久冻结，后续修好服务也不恢复；参数 self 为测试实例。
    def test_failed_handshake_stays_frozen_and_closes_locally(self) -> None:
        fixture: PassiveFixture = self.fixture()
        with fixture.session() as session:
            session.invoke("attach", {})
            session.invoke("start-case", {"case_id": "C-1"})
        fixture.idle(60)
        fixture.status_code = 401
        with fixture.session() as session:
            with self.assertRaises(EnvironmentBlocked):
                fixture.observe(session)
            self.assertTrue(session.state.frozen)
        count: int = fixture.world.eval_count
        status_count: int = fixture.status_calls
        fixture.status_code = 200
        with fixture.session() as session:
            with self.assertRaises(FrozenSession):
                fixture.observe(session, "blocked-next", "blocked-next")
            session.invoke("close", {"interrupted_reason": "fixture authentication status failed; no replay"})
        self.assertEqual(fixture.status_calls, status_count)
        self.assertEqual(fixture.world.eval_count, count)

    # 功能：真实标准库 HTTP 在静置 60 秒后按归档认证/被动心跳协议继续；参数 self 为测试实例，身份为内存假包。
    def test_local_http_wire_after_actual_60_second_idle(self) -> None:
        fixture: PassiveFixture = self.fixture()

        class Handler(BaseHTTPRequestHandler):
            """专属临时 loopback 服务，先认证再路由，不是 Unity Player。"""

            # 功能：禁止 HTTP 访问日志回显请求头；参数与标准库签名一致。
            def log_message(self, format: str, *args: object) -> None:
                return None

            # 功能：发送有界 JSON，无凭据落盘；参数 result 为本次协议回执。
            def send(self, result: HttpResponse) -> None:
                raw: bytes = canonical(result.payload)
                self.send_response(result.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            # 功能：复现归档中认证先于路由的 GET；参数无，只有状态请求刷新心跳。
            def do_GET(self) -> None:
                if self.headers.get("Authorization") != "Bearer " + fixture.world.token:
                    self.send(HttpResponse(401, {"error": "unauthorized"}))
                    return
                transport: PassiveTransport = PassiveTransport(fixture, fixture.target.limits, fixture.target.port)
                self.send(transport.request(self.path, None, fixture.target.limits.identity_timeout_ms))

            # 功能：仅接受正常运行状态命令，测试不发送 eval；参数无，按实际外层协议返回。
            def do_POST(self) -> None:
                if self.headers.get("Authorization") != "Bearer " + fixture.world.token:
                    self.send(HttpResponse(401, {"error": "unauthorized"}))
                    return
                length: int = int(self.headers.get("Content-Length", "0"))
                body: JsonObject = object_value(strict_json(self.rfile.read(length), fixture.target.limits.input_bytes), "fixture HTTP body")
                if self.path != EXEC_PATH or body.get("command") != "runtime_status":
                    self.send(HttpResponse(400, {"error": "not a read-only wire command"}))
                    return
                transport: PassiveTransport = PassiveTransport(fixture, fixture.target.limits, fixture.target.port)
                self.send(transport.request(self.path, body, fixture.target.limits.identity_timeout_ms))

        server: ThreadingHTTPServer = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # 隔离调用层使用 OS 分配的临时端口；正式 parse_target/CLI 的 7900..7949 约束不修改。
        fixture.target = replace(fixture.target, port=server.server_port)
        descriptor: JsonObject = object_value(strict_json(fixture.descriptor.read_bytes(), Limits().descriptor_bytes), "fixture descriptor")
        descriptor["port"] = server.server_port
        fixture.descriptor.write_bytes(canonical(descriptor))
        worker: threading.Thread = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            first: Pipeline = Pipeline(fixture.target, fixture.hooks)
            first.connect()
            first.close()
            initial: bytes = fixture.descriptor.read_bytes()
            started: float = time.perf_counter()
            time.sleep(60)
            self.assertGreaterEqual(time.perf_counter() - started, 60)
            self.assertEqual(fixture.descriptor.read_bytes(), initial)
            second: Pipeline = Pipeline(fixture.target, fixture.hooks)
            try:
                verified: JsonObject = second.connect()
                self.assertTrue(verified["authenticated"])
                self.assertFalse(verified["heartbeat_handshake"]["pre_descriptor_fresh"])
                self.assertTrue(verified["heartbeat_handshake"]["post_descriptor_fresh"])
            finally:
                second.close()
            self.assertEqual(fixture.status_calls, 2)
            self.assertEqual(fixture.world.eval_count, 0)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

