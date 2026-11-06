"""创建日期：2026-10-26；作者：Cyou。
功能：实际 Pipeline 格式分类、身份门禁、本机假 HTTP 与 Windows 文件冻结测试。
参数：本包临时静态字节、注入身份和有界内存回执；无真实游戏网络。
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .. import pipeline as pipeline_module
from ..contracts import SCHEMA, EnvironmentBlocked, InputError, IntegrityError, JsonObject, JsonValue, Limits, SecretGuard, canonical, digest, read_regular, strict_json
from ..evidence import Journal, protected_file, record_data
from ..inputs import parse_target
from ..pipeline import CATALOG_PATH, EXEC_PATH, EvalReceipt, HttpResponse, IdentityHooks, LocalHttp, Pipeline, classify_eval, observed_value, verify_package, verify_target, windows_acl, wrap_script, wrapper_format
from .support import FakeTransport, Fixture, eval_response


class PipelineTests(unittest.TestCase):
    # 功能：建立测试专属临时夹具；参数 self 为测试实例。
    def setUp(self) -> None:
        self.fixture: Fixture = Fixture()
        self.addCleanup(self.fixture.cleanup)
        self.target = parse_target(strict_json(self.fixture.target_file.read_bytes(), Limits().input_bytes), self.fixture.root)

    # 功能：完整 Mono 静态包核验不代表运行验证；参数 self 为测试实例。
    def test_complete_static_package_verified(self) -> None:
        result: JsonObject = verify_package(self.target)
        self.assertTrue(result["complete_static_files"])
        self.assertFalse(result["runtime_verified"])

    # 功能：静态包修改/多余文件均在连接前拒绝；参数 self 为测试实例。
    def test_package_tamper_prevents_connection(self) -> None:
        (self.fixture.package / "UnityPlayer.dll").write_bytes(b"tampered")
        with self.assertRaises(EnvironmentBlocked):
            Pipeline(self.target, self.fixture.hooks, self.fixture.world.transport).connect()
        self.assertEqual(self.fixture.world.transport_count, 0)

    # 功能：IL2CPP 冲突标记禁止降级或猜目标；参数 self 为测试实例。
    def test_il2cpp_conflict_prevents_connection(self) -> None:
        (self.fixture.package / "GameAssembly.dll").write_bytes(b"conflict")
        with self.assertRaises(EnvironmentBlocked):
            verify_package(self.target)

    # 功能：identity_only 跳过逐成员字节比对但保留 IL2CPP 标记/包声明身份核验；参数 self 为测试实例。
    def test_identity_only_skips_member_bytes_but_keeps_declared_identity(self) -> None:
        document: JsonObject = strict_json(self.fixture.target_file.read_bytes(), Limits().input_bytes)
        document["integrity_mode"] = "identity_only"
        loose = parse_target(document, self.fixture.root)
        self.assertEqual(verify_package(loose)["integrity_mode"], "identity_only")
        (self.fixture.package / "UnityPlayer.dll").write_bytes(b"tampered")
        # identity_only 不再逐成员比对，因此篡改字节不阻断；这是该口径的已知代价。
        self.assertFalse(verify_package(loose)["complete_static_files"])
        # 但 IL2CPP 冲突与包声明身份仍必须拒绝。
        (self.fixture.package / "GameAssembly.dll").write_bytes(b"conflict")
        with self.assertRaises(EnvironmentBlocked):
            verify_package(loose)

    # 功能：有界读取只按实际大小申请缓冲，超大上限不得触发 MemoryError/OverflowError；参数 self 为测试实例。
    def test_read_regular_does_not_preallocate_maximum(self) -> None:
        path: Path = self.fixture.root / "small-regular.bin"
        path.write_bytes(b"0123456789")
        self.assertEqual(read_regular(path, 1 << 62), b"0123456789")
        with self.assertRaises(InputError):
            read_regular(path, 9)

    # 功能：identity_only 的 EXE 摘要流式计算且等于原字节摘要，不整读 EXE；参数 self 为测试实例。
    def test_identity_only_exe_hash_streams_without_full_read(self) -> None:
        document: JsonObject = strict_json(self.fixture.target_file.read_bytes(), Limits().input_bytes)
        document["integrity_mode"] = "identity_only"
        loose = parse_target(document, self.fixture.root)
        with patch.object(pipeline_module, "read_regular", wraps=pipeline_module.read_regular) as spy:
            result: JsonObject = verify_package(loose)
        self.assertNotIn(loose.exe, [call.args[0] for call in spy.call_args_list])
        self.assertEqual(result["exe_sha256"], digest(loose.exe.read_bytes()))

    # 功能：journal 刷新按实际大小读取，超大预算不预分配；参数 self 为测试实例。
    def test_journal_refresh_does_not_preallocate_budget(self) -> None:
        with Journal(self.fixture.run, Limits(journal_bytes=1 << 62)) as journal:
            self.assertGreaterEqual(len(journal.records), 1)

    # 功能：连接期本机内存不足归为环境阻塞，不以 host_failure 冻结整轮且可重试；参数 self 为测试实例。
    def test_memory_error_during_connect_is_environment_blocked(self) -> None:
        with self.fixture.session() as session:
            with patch.object(Pipeline, "connect", side_effect=MemoryError), self.assertRaises(EnvironmentBlocked):
                session.invoke("attach", {})
            self.assertFalse(session.state.frozen)
            events: list[str] = [str(record["event"]) for record in session.journal.records]
            self.assertIn("environment_blocked", events)
            self.assertNotIn("session_frozen", events)
            blocked: JsonObject = [record_data(record) for record in session.journal.records if record["event"] == "environment_blocked"][-1]
            self.assertEqual(blocked["error_kind"], "MemoryError")
            session.invoke("attach", {})
            self.assertTrue(session.state.attached)

    # 功能：读取同样要求 script_execute；参数 self 为测试实例。
    def test_read_requires_script_execute_permission(self) -> None:
        fixture: Fixture = Fixture(permissions=["attach"])
        self.addCleanup(fixture.cleanup)
        with fixture.session() as session, self.assertRaises(EnvironmentBlocked):
            session.invoke("attach", {})
        self.assertEqual(fixture.world.transport_count, 0)

    # 功能：PID 创建时间变化在任何 HTTP 前拒绝；参数 self 为测试实例。
    def test_process_creation_identity_mismatch(self) -> None:
        # 功能：提供复用 PID 的错误创建时间；参数来自静态测试目标。
        def wrong_process(pid: int, exe: Path, timeout: int) -> JsonObject:
            return {"pid": pid, "exe": str(exe), "created": "2000-01-01T00:00:00+00:00"}
        hooks: IdentityHooks = IdentityHooks(wrong_process, self.fixture.port, self.fixture.acl)
        with self.assertRaises(EnvironmentBlocked):
            Pipeline(self.target, hooks, self.fixture.world.transport).connect()
        self.assertEqual(self.fixture.world.transport_count, 0)

    # 功能：端口所有者不唯一或不匹配拒绝连接；参数 self 为测试实例。
    def test_port_owner_mismatch(self) -> None:
        # 功能：返回不属于目标的监听 PID；参数仅测试静态门禁。
        def wrong_port(pid: int, port: int, timeout: int) -> JsonObject:
            return {"listeners": [{"pid": pid + 1, "address": "0.0.0.0"}]}
        with self.assertRaises(EnvironmentBlocked):
            Pipeline(self.target, IdentityHooks(self.fixture.process, wrong_port, self.fixture.acl), self.fixture.world.transport).connect()
        self.assertEqual(self.fixture.world.transport_count, 0)

    # 功能：未核验实际 ACL 时拒绝连接；参数 self 为测试实例。
    def test_acl_gate_precedes_http(self) -> None:
        # 功能：模拟 ACL 核验失败；参数 path 不读取真实凭据。
        def wrong_acl(path: Path, timeout: int) -> JsonObject:
            return {"checked": False}
        with self.assertRaises(EnvironmentBlocked):
            Pipeline(self.target, IdentityHooks(self.fixture.process, self.fixture.port, wrong_acl), self.fixture.world.transport).connect()
        self.assertEqual(self.fixture.world.transport_count, 0)

    # 功能：ACL 分类拒绝 Everyone 读取令牌；参数 self 为测试实例。
    def test_acl_rejects_broad_read_authorization(self) -> None:
        payload: JsonObject = {"principal": "S-1-5-21-1", "owner": "S-1-5-21-1",
                                "rules": [{"sid": "S-1-5-21-1", "type": "Allow", "rights": 1},
                                          {"sid": "S-1-1-0", "type": "Allow", "rights": 1}]}
        with patch("scripts.pipeline._powershell", return_value=payload), self.assertRaises(EnvironmentBlocked):
            windows_acl(self.fixture.descriptor, 1000)

    # 功能：核对 runtime_status 实际 PascalCase 字段；参数 self 为测试实例。
    def test_runtime_pascalcase_identity(self) -> None:
        self.fixture.world.wrong_runtime_identity = True
        with self.assertRaises(EnvironmentBlocked):
            Pipeline(self.target, self.fixture.hooks, self.fixture.world.transport).connect()
        self.assertEqual(self.fixture.world.eval_count, 0)

    # 功能：命令目录同时要求 eval/eval_file，缺项不降级；参数 self 为测试实例。
    def test_both_eval_capabilities_required(self) -> None:
        original_request = FakeTransport.request
        # 功能：删除实际命令目录的一项，其他请求走原假 HTTP；参数来自生产连接。
        def missing_eval_file(transport: FakeTransport, path: str, body: JsonObject | None, timeout: int) -> HttpResponse:
            response: HttpResponse = original_request(transport, path, body, timeout)
            if path == CATALOG_PATH:
                response.payload["commands"] = [entry for entry in response.payload["commands"] if entry["name"] != "eval_file"]
                response.payload["count"] = 2
                response.payload["total"] = 2
            return response
        with patch.object(FakeTransport, "request", missing_eval_file), self.assertRaises(EnvironmentBlocked):
            Pipeline(self.target, self.fixture.hooks, self.fixture.world.transport).connect()

    # 功能：真实编译回执明确未执行；参数 self 为测试实例。
    def test_real_compile_receipt_not_executed(self) -> None:
        result = classify_eval(eval_response("eval_file", state="compile_failed"), "eval_file", Limits())
        self.assertEqual((result.state, result.phase), ("compile_failed", "compilation_not_executed"))
        self.assertEqual(result.diagnostics[0]["id"], "CS0246")

    # 功能：运行异常即使携带 error 诊断也不能改判编译未执行；参数 self 为测试实例。
    def test_runtime_receipt_is_unknown_not_compile(self) -> None:
        response: HttpResponse = eval_response("eval", state="runtime_error")
        response.payload["result"]["diagnostics"] = [{"severity": "error", "message": "runtime diagnostic"}]
        result = classify_eval(response, "eval", Limits())
        self.assertEqual(result.state, "unknown")
        self.assertFalse(result.to_json()["execution_terminated"])

    # 功能：命令、内层结果、未知关键字段或矛盾回执冻结；参数 self 为测试实例。
    def test_malformed_and_unknown_receipts(self) -> None:
        responses: list[HttpResponse] = [HttpResponse(200, {"success": True, "command": "eval", "result": {"success": True, "diagnostics": []}}),
                                         HttpResponse(200, {"success": True, "command": "wrong", "result": {}}),
                                         HttpResponse(400, {"success": False, "command": "eval", "result": {}})]
        unknown: HttpResponse = eval_response("eval", 1)
        unknown.payload["unknown_critical"] = True
        responses.append(unknown)
        for response in responses:
            with self.subTest(response=response.status):
                self.assertEqual(classify_eval(response, "eval", Limits()).state, "unknown")

    # 功能：敏感结果和超界值不能保存或形成结论；参数 self 为测试实例。
    def test_sensitive_and_oversize_receipts(self) -> None:
        self.assertEqual(classify_eval(eval_response("eval", {"password": "private"}), "eval", Limits()).phase, "sensitive_result")
        self.assertEqual(classify_eval(eval_response("eval", "x" * 1000), "eval", Limits(value_bytes=32)).state, "unknown")

    # 功能：包装保存身份且不采用用户返回 success/assertion；参数 self 为测试实例。
    def test_wrapper_uses_fully_qualified_func_and_identity(self) -> None:
        raw: bytes = b'return new object();\r\n'
        wrapped: bytes = wrap_script(raw, "run-fixture", "C-1", "cmd-1", Limits(), SecretGuard())
        self.assertIn(b"System.Func<object>", wrapped)
        self.assertIn(b"UnityEngine.Time.frameCount", wrapped)
        self.assertIn(b'"command_id", "cmd-1"', wrapped)
        self.assertNotEqual(digest(raw), digest(wrapped))

    # Codex: version 1 must regenerate the exact bytes audited before this repair.
    def test_legacy_wrapper_preserves_the_prechange_golden_digest(self) -> None:
        wrapped: bytes = wrap_script(b"return null;\n", "run-fixture", "C-1", "cmd-1", Limits(), SecretGuard(), 1)
        self.assertEqual(len(wrapped), 517)
        self.assertEqual(digest(wrapped), "00d83ff3b8a9872fd14bd84b46e3987559aa801fd6d3d8db0fd487c918258d02")
        self.assertEqual(wrapper_format(wrapped), 1)

    # Codex: only a known error inside the exact new identity envelope is recoverable.
    def test_return_contract_error_does_not_relax_identity_or_error_schema(self) -> None:
        envelope: JsonObject = {"host": SCHEMA, "run_id": "run-fixture", "case_id": "C-1",
            "command_id": "cmd-1", "frame": 5, "build_guid": "fixture-build-v1", "value": None,
            "value_error": "unsupported_return_type"}
        receipt: EvalReceipt = EvalReceipt("succeeded", "completed", envelope, "")
        frame, value, error = observed_value(receipt, "run-fixture", "C-1", "cmd-1", "fixture-build-v1", "json", "target", Limits(), 2)
        self.assertEqual((frame, value, error), (5, None, "return_value_contract:unsupported_return_type"))
        for changed in ({"build_guid": "wrong"}, {"frame": None}, {"value": 0}, {"value_error": "untrusted"}, {"value_error": {}}):
            with self.subTest(changed=changed), self.assertRaises(IntegrityError):
                observed_value(EvalReceipt("succeeded", "completed", {**envelope, **changed}, ""),
                    "run-fixture", "C-1", "cmd-1", "fixture-build-v1", "json", "target", Limits(), 2)
        with self.assertRaises(IntegrityError):
            observed_value(receipt, "run-fixture", "C-1", "cmd-1", "fixture-build-v1", "json", "target", Limits(), 1)

    # 功能：发送期间真正持有 FILE_SHARE_READ，禁止写入和替换；参数 self 为测试实例。
    def test_windows_file_share_read_blocks_write_and_replace(self) -> None:
        path: Path = self.fixture.script("protected")
        other: Path = self.fixture.script("replacement")
        content: bytes = path.read_bytes()
        with protected_file(path, Limits().script_bytes, digest(content)) as held:
            self.assertEqual(held, content)
            with self.assertRaises(OSError):
                path.write_bytes(b"changed")
            with self.assertRaises(OSError):
                os.replace(other, path)

    # 功能：冻结摘要变化在发送前拒绝；参数 self 为测试实例。
    def test_protected_file_digest_mismatch(self) -> None:
        path: Path = self.fixture.script("digest")
        with self.assertRaises(IntegrityError), protected_file(path, Limits().script_bytes, "0" * 64):
            self.fail("不应进入发送期间")

    # 功能：本机 HTTP 拒重复键/非有限 JSON，异常不回显令牌；参数 self 为测试实例。
    def test_fake_http_strict_json_no_token_echo(self) -> None:
        for content in (b'{"x":1,"x":2}', b'{"x":NaN}', b'not-json'):
            connection: MemoryConnection = MemoryConnection(content)
            with patch("scripts.pipeline.http.client.HTTPConnection", return_value=connection):
                client: LocalHttp = LocalHttp(7901, self.fixture.world.token, Limits())
                with self.assertRaises(EnvironmentBlocked) as caught:
                    client.request(EXEC_PATH, {"command": "eval"}, 1000)
                self.assertNotIn(self.fixture.world.token, str(caught.exception))
                self.assertEqual(connection.host_assertion, "127.0.0.1")


class MemoryResponse:
    """单次内存 HTTP 字节流，无 socket。"""

    # 功能：保存原响应字节；参数 content 可以是非法或越界 JSON。
    def __init__(self, content: bytes) -> None:
        self.content: bytes = content
        self.offset: int = 0
        self.status: int = 200

    # 功能：返回有界内容长度；参数 name 是真实 HTTP header 名称。
    def getheader(self, name: str) -> str | None:
        return str(len(self.content)) if name == "Content-Length" else None

    # 功能：有界读取内存字节；参数 maximum 与正式宿主预算一致。
    def read1(self, maximum: int) -> bytes:
        result: bytes = self.content[self.offset:self.offset + maximum]
        self.offset += len(result)
        return result


class MemoryConnection:
    """仅用于替代标准库 HTTPConnection，不进行真实网络连接。"""

    # 功能：构造假 HTTP 连接；参数 content 为本次假响应。
    def __init__(self, content: bytes) -> None:
        self.response: MemoryResponse = MemoryResponse(content)
        self.sock: None = None
        self.host_assertion: str = "127.0.0.1"

    # 功能：记录结构化请求存在但不外发；参数与标准库 request 对齐。
    def request(self, method: str, path: str, body: bytes | None, headers: dict[str, str]) -> None:
        if path != EXEC_PATH or "Authorization" not in headers:
            raise AssertionError("缺固定 API 或认证 header")

    # 功能：返回内存 HTTPResponse；参数无。
    def getresponse(self) -> MemoryResponse:
        return self.response

    # 功能：关闭内存连接；参数无，没有任何进程/网络副作用。
    def close(self) -> None:
        return None
