"""创建日期：2026-10-26；作者：Cyou。
功能：独占的实时 journal、序号/摘要链/头锚、writer 计时及私有证据。
参数：明确运行目录、集中预算、原字节及证据来源；不会启动或连接 Player。
"""
from __future__ import annotations

import ctypes
import os
import stat
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator, cast

from .contracts import (
    SCHEMA, ZERO_HASH, EnvironmentBlocked, HostError, InputError, IntegrityError, JsonObject, JsonValue,
    Limits, SecretGuard, canonical, digest, hash_value, integer, keys_only, object_value,
    read_regular, reject_links, strict_json, text,
)

JOURNAL_NAME = "journal.jsonl"
ANCHOR_NAME = ".journal-head.json"
LOCK_NAME = ".writer.lock"
REPORT_NAME = "functiontest-report.md"
INTERRUPTION_SUMMARY_NAME = "functiontest-interrupted-summary.md"
WINDOWS_FILE_PATH_UNITS = 259
REF_KEYS = frozenset({"evidence_id", "path", "sha256", "bytes", "kind", "case_id", "source"})
RECORD_KEYS = frozenset({"schema", "run_id", "seq", "event", "case_id", "data", "time_utc", "time_ns", "monotonic_ns", "prev_hash", "hash"})
EVIDENCE_KINDS = frozenset({"input", "index", "target", "binding", "script_original", "script_wrapper",
                           "observation", "comparison", "final", "attribution", "baseline",
                           "runtime_reference", "artifact", "audit"})
PRIVATE_KINDS = EVIDENCE_KINDS - {"input", "index", "target", "baseline", "audit"}


# 功能：生成唯一安全 ID；参数 prefix 为包内固定前缀。
def new_id(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex


# 功能：父本地操作共用唯一 CLI 结果 writer，包括失败；参数 result["result"] 由调用者填写。
@contextmanager
def local_cli_call(journal: Journal, operation: str) -> Iterator[JsonObject]:
    call_id: str = new_id("call")
    journal.append("cli_begin", {"operation": operation, "call_id": call_id})
    result: JsonObject = {}
    try:
        yield result
        payload: JsonObject = object_value(result.get("result"), "local CLI result")
        journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": True, "result": payload})
    except HostError as exc:
        journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": False,
                                      "error_kind": type(exc).__name__, "message": SecretGuard().diagnostic(str(exc))})
        raise
    except (Exception, KeyboardInterrupt):
        journal.append("cli_result", {"operation": operation, "call_id": call_id, "ok": False,
                                      "error_kind": "HostFailure", "message": "本地父操作异常，原文已排除；未操作 Player"})
        raise IntegrityError("本地父操作失败；不得覆盖产物或手填时钟") from None


# 功能：独占创建并 fsync 字节文件；参数 path 必须位于本轮私有目录。
def write_new(path: Path, content: bytes) -> None:
    reject_links(path.parent)
    try:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise IntegrityError("拒绝覆盖既有本轮产物") from None
    except OSError:
        raise IntegrityError("产物独占写入或 fsync 失败") from None


# 功能：由 writer 读取真实时钟；参数无，不接受调用方填写时间或时长。
def writer_stamp() -> JsonObject:
    wall: int = time.time_ns()
    monotonic: int = time.perf_counter_ns()
    utc: str = datetime.fromtimestamp(wall / 1000000000, timezone.utc).isoformat(timespec="microseconds")
    return {"time_utc": utc, "time_ns": wall, "monotonic_ns": monotonic}


# 功能：取得记录整数；参数 name 为固定字段，错误按完整性问题处理。
def record_int(record: JsonObject, name: str) -> int:
    value: JsonValue = record.get(name)
    if type(value) is not int or value < 0:
        raise IntegrityError("journal 整数或时钟字段非法")
    return value


# 功能：获取记录内容；参数 record 来自已验证物理行。
def record_data(record: JsonObject) -> JsonObject:
    return object_value(record.get("data"), "journal.data")


# 功能：生成每例私有目录名；参数 CaseId 保持原文、不直接作为文件名。
def case_directory(case_id: str) -> str:
    return "case-" + digest(case_id.encode("utf-8"))


# 功能：按真实证据命名计算最长 Windows UTF-16 路径预算；参数 root 是尚未创建的候选运行根。
def run_path_budget(root: Path) -> JsonObject:
    absolute: Path = root.absolute()
    evidence_id: str = new_id("ev")
    candidates: list[Path] = [absolute / "evidence" / case_directory(absolute.name) /
                              (kind + "-" + evidence_id + ".json") for kind in EVIDENCE_KINDS]
    longest: Path = max(candidates, key=lambda path: len(str(path).encode("utf-16-le")))
    longest_units: int = len(str(longest).encode("utf-16-le")) // 2
    output_units: int = len(str(absolute.parent).encode("utf-16-le")) // 2
    return {"supported": os.name != "nt" or longest_units <= WINDOWS_FILE_PATH_UNITS,
            "candidate_root": str(absolute), "longest_evidence_units": longest_units,
            "windows_limit_units": WINDOWS_FILE_PATH_UNITS,
            "maximum_output_root_units": WINDOWS_FILE_PATH_UNITS - (longest_units - output_units),
            "unit": "UTF-16 code units", "created": False, "player_contacted": False}


# 功能：保护实际发送文件免于写入/替换；参数 expected_digest 为冻结原字节摘要。
@contextmanager
def protected_file(path: Path, maximum: int, expected_digest: str | None = None) -> Iterator[bytes]:
    if os.name != "nt":
        raise EnvironmentBlocked("发送保护要求 Windows FILE_SHARE_READ；未发送")
    from ctypes import wintypes

    reject_links(path)
    information: os.stat_result = path.stat()
    if not stat.S_ISREG(information.st_mode) or not 0 < information.st_size <= maximum:
        raise InputError("受保护文件大小或类型非法")
    kernel: ctypes.CDLL = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
    kernel.GetFileSizeEx.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # GENERIC_READ / FILE_SHARE_READ / OPEN_EXISTING / FILE_FLAG_OPEN_REPARSE_POINT。
    handle: int = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value or handle is None:
        raise EnvironmentBlocked("无法取得只读共享句柄；未发送")
    try:
        size: ctypes.c_longlong = ctypes.c_longlong()
        if not kernel.GetFileSizeEx(handle, ctypes.byref(size)) or not 0 < size.value <= maximum:
            raise IntegrityError("受保护文件大小校验失败；未发送")
        buffer: ctypes.Array[ctypes.c_char] = ctypes.create_string_buffer(maximum + 1)
        count: wintypes.DWORD = wintypes.DWORD()
        if not kernel.ReadFile(handle, buffer, maximum + 1, ctypes.byref(count), None):
            raise IntegrityError("受保护文件读取失败；未发送")
        content: bytes = buffer.raw[:count.value]
        reject_links(path)
        if len(content) != size.value or (expected_digest is not None and digest(content) != expected_digest):
            raise IntegrityError("受保护文件在发送前变化；未发送")
        yield content
    finally:
        kernel.CloseHandle(handle)


class Journal:
    """所有 CLI 共用的唯一 writer；OS 锁仅覆盖本次调用，intent 跨调用永久保留。"""

    # 功能：保存运行目录和预算；参数 root 必须为明确本轮目录。
    def __init__(self, root: Path, limits: Limits | None = None) -> None:
        self.root: Path = root.absolute()
        self.limits: Limits = limits if limits is not None else Limits()
        self.records: list[JsonObject] = []
        self.run_id: str = ""
        self._lock: BinaryIO | None = None
        self._guard: SecretGuard = SecretGuard()
        self._bytes: int = 0
        # 本进程内已真实读盘的证据摘要：键含文件身份，替换或改写即失效并回到严格重读。
        self._digest_memo: dict[tuple[str, int, int, int], str] = {}

    # 功能：创建空白本轮目录和头锚；参数 root 不得已存在，不删除旧运行。
    @classmethod
    def create(cls, root: Path, limits: Limits | None = None) -> Journal:
        reject_links(root.parent)
        try:
            root.mkdir(exist_ok=False)
        except OSError:
            raise IntegrityError("本轮目录必须独占新建") from None
        journal: Journal = cls(root, limits)
        write_new(root / JOURNAL_NAME, b"")
        write_new(root / LOCK_NAME, b"0")
        write_new(root / ANCHOR_NAME, canonical({"schema": SCHEMA, "run_id": "", "seq": 0,
                                               "head": ZERO_HASH, "journal_bytes": 0, "init_hash": ZERO_HASH}))
        return journal

    # 功能：取得独占 OS writer 锁并核验物理日志；参数无，锁冲突不等待/不抢占。
    def __enter__(self) -> Journal:
        if self._lock is not None:
            raise IntegrityError("writer 不允许重复进入")
        reject_links(self.root)
        reject_links(self.root / LOCK_NAME)
        try:
            stream: BinaryIO = (self.root / LOCK_NAME).open("r+b")
            if os.fstat(stream.fileno()).st_size != 1:
                stream.close()
                raise IntegrityError("writer 锁文件被改写")
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock = stream
            self.refresh()
        except OSError:
            if "stream" in locals():
                stream.close()
            raise IntegrityError("本轮 writer 已被占用或无法取得独占锁") from None
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    # 功能：释放本次 OS 锁；参数异常信息不落盘、不回显。
    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        stream: BinaryIO | None = self._lock
        self._lock = None
        if stream is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    # 功能：加入本次连接的内存凭据防泄漏检查；参数 guard 不可被序列化。
    def use_guard(self, guard: SecretGuard) -> None:
        self._guard = guard

    # 功能：核验序号、字节范围、摘要链、头锚和 writer 时间；参数无。
    def refresh(self) -> None:
        if self._lock is None:
            raise IntegrityError("journal 读取必须持有唯一 writer 锁")
        reject_links(self.root / JOURNAL_NAME)
        try:
            with (self.root / JOURNAL_NAME).open("rb") as stream:
                # 按持锁后的实际大小申请读缓冲，不按 journal_bytes 上限预分配（2026-11-03 修复）。
                size: int = os.fstat(stream.fileno()).st_size
                if size > self.limits.journal_bytes:
                    raise IntegrityError("journal 越界或末尾物理行不完整")
                raw: bytes = stream.read(size + 1)
        except OSError:
            raise IntegrityError("journal 缺失或不可读取") from None
        if len(raw) > self.limits.journal_bytes or (raw and not raw.endswith(b"\n")):
            raise IntegrityError("journal 越界或末尾物理行不完整")
        anchor: JsonObject = object_value(strict_json(read_regular(self.root / ANCHOR_NAME, 4096), 4096), "journal.head")
        keys_only(anchor, {"schema", "run_id", "seq", "head", "journal_bytes", "init_hash"}, "journal.head",
                  {"schema", "run_id", "seq", "head", "journal_bytes", "init_hash"})
        records: list[JsonObject] = []
        previous: str = ZERO_HASH
        run_id: str = ""
        last_mono: int = 0
        for seq, line in enumerate(raw.splitlines(), 1):
            record: JsonObject = object_value(strict_json(line, self.limits.evidence_bytes, self.limits), "journal.line")
            keys_only(record, RECORD_KEYS, "journal.line", RECORD_KEYS)
            actual_hash: str = hash_value(record["hash"], "journal.hash")
            unhashed: JsonObject = {key: value for key, value in record.items() if key != "hash"}
            if actual_hash != digest(canonical(unhashed)) or record["prev_hash"] != previous:
                raise IntegrityError("journal 摘要链被改写")
            if record["seq"] != seq or record["schema"] != SCHEMA:
                raise IntegrityError("journal 序号或版本非法")
            if seq == 1:
                run_id = text(record["run_id"], "run_id")
            if record["run_id"] != run_id or not isinstance(record["event"], str):
                raise IntegrityError("journal 运行身份或事件非法")
            if record["case_id"] is not None and not isinstance(record["case_id"], str):
                raise IntegrityError("journal 本例归属非法")
            record_data(record)
            monotonic: int = record_int(record, "monotonic_ns")
            wall: int = record_int(record, "time_ns")
            if monotonic < last_mono:
                raise IntegrityError("writer 单调时间被修改或系统已重启")
            try:
                utc: datetime = datetime.fromisoformat(text(record["time_utc"], "time_utc"))
            except ValueError:
                raise IntegrityError("writer 时间非法") from None
            if utc.tzinfo is None or abs(utc.timestamp() * 1000000000 - wall) > 2000:
                raise IntegrityError("writer 时间与原时钟不一致")
            self._guard.check(record)
            last_mono = monotonic
            previous = actual_hash
            records.append(record)
        if anchor != {"schema": SCHEMA, "run_id": run_id, "seq": len(records), "head": previous,
                      "journal_bytes": len(raw), "init_hash": records[0]["hash"] if records else ZERO_HASH}:
            raise IntegrityError("journal 头锚与物理日志不一致；不自动修复或恢复")
        self.records = records
        self.run_id = run_id
        self._bytes = len(raw)

    # 功能：原子更新头锚；参数 record 为已经 fsync 的唯一新增记录。
    def _update_anchor(self, record: JsonObject) -> None:
        anchor: JsonObject = {"schema": SCHEMA, "run_id": self.run_id, "seq": len(self.records),
                              "head": record["hash"], "journal_bytes": self._bytes,
                              "init_hash": self.records[0]["hash"]}
        temporary: Path = self.root / (".head-next-" + uuid.uuid4().hex)
        write_new(temporary, canonical(anchor))
        try:
            os.replace(temporary, self.root / ANCHOR_NAME)
        except OSError:
            raise IntegrityError("journal 已写入但头锚未闭合；停止且不自动恢复") from None

    # 功能：立即追加并 fsync 唯一事件；参数数据不允许手填 writer 时钟。
    def append(self, event: str, data: JsonObject, case_id: str | None = None,
               run_id: str | None = None) -> JsonObject:
        return self._append(event, data, case_id, run_id, writer_stamp())

    # 功能：内部固定时钟事件写入；参数 stamp 仅来自 writer 自身。
    def _append(self, event: str, data: JsonObject, case_id: str | None,
                run_id: str | None, stamp: JsonObject) -> JsonObject:
        if self._lock is None:
            raise IntegrityError("事件写入必须持有唯一 writer 锁")
        if not self.records:
            self.run_id = text(run_id, "run_id")
        elif run_id is not None and run_id != self.run_id:
            raise IntegrityError("拒绝混写运行身份")
        if self.records and record_int(stamp, "monotonic_ns") < record_int(self.records[-1], "monotonic_ns"):
            raise IntegrityError("writer 时钟已回退；不自动恢复")
        record: JsonObject = {"schema": SCHEMA, "run_id": self.run_id, "seq": len(self.records) + 1,
                              "event": event, "case_id": case_id, "data": data, **stamp,
                              "prev_hash": self.records[-1]["hash"] if self.records else ZERO_HASH}
        self._guard.check(record)
        record["hash"] = digest(canonical(record))
        encoded: bytes = canonical(record) + b"\n"
        if self._bytes + len(encoded) > self.limits.journal_bytes:
            raise IntegrityError("journal 已达集中大小预算；停止后续动作")
        try:
            with (self.root / JOURNAL_NAME).open("ab") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            raise IntegrityError("journal 追加或 fsync 失败；不得发送或重放动作") from None
        self.records.append(record)
        self._bytes += len(encoded)
        self._update_anchor(record)
        return record

    # 功能：在收口后闭合 writer 计时；参数 start 为本轮/父上下文的初始化事件。
    def finish_timing(self, start: JsonObject, scope: str) -> JsonObject:
        stamp: JsonObject = writer_stamp()
        duration: int = record_int(stamp, "monotonic_ns") - record_int(start, "monotonic_ns")
        if duration < 0:
            raise IntegrityError("writer 计时回退")
        return self._append("timing_closed", {"scope": scope, "start_seq": start["seq"],
                                             "start_hash": start["hash"], "duration_ns": duration},
                            None, None, stamp)

    # 功能：保存原字节和来源，按本例私有归属隔离；参数 kind 为固定证据类别。
    def store(self, kind: str, content: bytes, source: JsonObject,
              case_id: str | None = None, extension: str = ".json") -> JsonObject:
        if self._lock is None or kind not in EVIDENCE_KINDS or extension not in {".json", ".cs", ".bin", ".png", ".log"}:
            raise InputError("证据写入类别或 writer 状态非法")
        if kind in PRIVATE_KINDS and case_id is None:
            raise IntegrityError("本例证据不得共享或缺失归属")
        if not content or len(content) > self.limits.evidence_bytes:
            raise InputError("证据大小越界")
        self._guard.check_bytes(content)
        if extension == ".json":
            try:
                parsed: JsonValue = strict_json(content, self.limits.evidence_bytes, self.limits, bom=True)
            except InputError:
                parsed = None
            if parsed is not None:
                self._guard.check(parsed)
        self._guard.check(source)
        directory: Path = self.root / ("inputs" if case_id is None else "evidence/" + case_directory(case_id))
        directory.mkdir(parents=True, exist_ok=True)
        reject_links(directory)
        evidence_id: str = new_id("ev")
        path: Path = directory / (kind + "-" + evidence_id + extension)
        write_new(path, content)
        reference: JsonObject = {"evidence_id": evidence_id, "path": path.relative_to(self.root).as_posix(),
                                 "sha256": digest(content), "bytes": len(content), "kind": kind,
                                 "case_id": case_id, "source": source}
        self.verify_ref(reference, case_id)
        return reference

    # 功能：核验证据私有路径、原大小/摘要/来源；参数 expected_case 指定本例归属。
    def verify_ref(self, reference: JsonObject, expected_case: str | None = None) -> bytes:
        self._verify_ref_shape(reference, expected_case)
        relative: Path = Path(text(reference["path"], "evidence.path"))
        content: bytes = read_regular(self.root / relative, self.limits.evidence_bytes)
        checksum: str = digest(content)
        if len(content) != integer(reference["bytes"], "evidence.bytes", 1, self.limits.evidence_bytes) or checksum != hash_value(reference["sha256"], "evidence.sha256"):
            raise IntegrityError("证据原字节大小或摘要被修改")
        self._digest_memo.update(self._identity_key(relative, checksum))
        self._guard.check_bytes(content)
        return content

    # 功能：核验证据摘要，命中本进程已读盘结果即跳过重读；参数 reference 必须已通过结构核验。
    def verify_ref_digest(self, reference: JsonObject, expected_case: str | None = None) -> str:
        self._verify_ref_shape(reference, expected_case)
        relative: Path = Path(text(reference["path"], "evidence.path"))
        declared: str = hash_value(reference["sha256"], "evidence.sha256")
        declared_bytes: int = integer(reference["bytes"], "evidence.bytes", 1, self.limits.evidence_bytes)
        try:
            information: os.stat_result = (self.root / relative).stat()
        except OSError:
            raise IntegrityError("证据原字节缺失或不可读取") from None
        if not stat.S_ISREG(information.st_mode):
            raise IntegrityError("证据必须为普通文件")
        key: tuple[str, int, int, int] = (str(relative), information.st_size, information.st_mtime_ns, information.st_ino)
        remembered: str | None = self._digest_memo.get(key)
        if remembered is not None and remembered == declared and information.st_size == declared_bytes:
            return remembered
        content: bytes = read_regular(self.root / relative, self.limits.evidence_bytes)
        checksum: str = digest(content)
        if len(content) != declared_bytes or checksum != declared:
            raise IntegrityError("证据原字节大小或摘要被修改")
        self._digest_memo[key] = checksum
        return checksum

    # 功能：生成证据文件身份键；参数 relative 为本轮相对路径，checksum 为已核验摘要。
    def _identity_key(self, relative: Path, checksum: str) -> dict[tuple[str, int, int, int], str]:
        try:
            information: os.stat_result = (self.root / relative).stat()
        except OSError:
            return {}
        return {(str(relative), information.st_size, information.st_mtime_ns, information.st_ino): checksum}

    # 功能：核验证据引用的路径/类别/归属结构；参数 expected_case 指定本例归属，不读取字节。
    def _verify_ref_shape(self, reference: JsonObject, expected_case: str | None = None) -> None:
        keys_only(reference, REF_KEYS, "evidence", REF_KEYS)
        path_text: str = text(reference["path"], "evidence.path")
        relative: Path = Path(path_text)
        if relative.is_absolute() or ".." in relative.parts or "\\" in path_text:
            raise IntegrityError("证据引用必须为本轮相对路径")
        case_id: JsonValue = reference["case_id"]
        if case_id is not None and not isinstance(case_id, str):
            raise IntegrityError("证据本例身份非法")
        if expected_case is not None and case_id != expected_case:
            raise IntegrityError("拒绝跨例复用证据")
        kind: str = text(reference["kind"], "evidence.kind")
        if kind == "report":
            if path_text != REPORT_NAME or case_id is not None:
                raise IntegrityError("正式报告位置必须唯一")
        elif kind == "interruption_summary":
            if path_text != INTERRUPTION_SUMMARY_NAME or case_id is not None:
                raise IntegrityError("中断诊断摘要必须为唯一固定本地落点")
        elif kind not in EVIDENCE_KINDS:
            raise IntegrityError("证据类别非法")
        elif case_id is None:
            if kind in PRIVATE_KINDS or len(relative.parts) != 2 or relative.parts[0] != "inputs":
                raise IntegrityError("共享目录只允许原输入/独立基线")
        elif len(relative.parts) != 3 or relative.parts[:2] != ("evidence", case_directory(case_id)):
            raise IntegrityError("证据不在本例私有目录")
        source: JsonObject = object_value(reference["source"], "evidence.source")
        if not source or "kind" not in source:
            raise IntegrityError("证据缺失可核验来源")

    # 功能：核验本轮所有引用，包括报告文件；参数 value 为事件内容树，摘要命中即不重复读盘。
    def verify_references(self, value: JsonValue) -> None:
        stack: list[JsonValue] = [value]
        while stack:
            current: JsonValue = stack.pop()
            if isinstance(current, dict):
                if REF_KEYS <= set(current):
                    self.verify_ref_digest(cast(JsonObject, current))
                else:
                    stack.extend(current.values())
            elif isinstance(current, list):
                stack.extend(current)

    # 功能：登记不可静默修改的外部来源；参数 path 的原字节与快照同时保留。
    def origin(self, path: Path, content: bytes, kind: str = "input", case_id: str | None = None) -> JsonObject:
        source: JsonObject = {"kind": "local_file", "path": str(path.absolute()),
                              "sha256": digest(content), "bytes": len(content)}
        snapshot: JsonObject = self.store(kind, content, source, case_id)
        return {**source, "snapshot": snapshot}

    # 功能：核验外部原来源及登记绑定未变；参数 origin 包含真实原字节摘要与私有快照。
    def verify_origin(self, origin: JsonObject) -> None:
        keys_only(origin, {"kind", "path", "sha256", "bytes", "snapshot"}, "origin",
                  {"kind", "path", "sha256", "bytes", "snapshot"})
        if origin["kind"] != "local_file":
            raise IntegrityError("来源类型非法")
        path: Path = Path(text(origin["path"], "origin.path"))
        if not path.is_absolute():
            raise IntegrityError("已登记外部来源必须为明确本地路径")
        content: bytes = read_regular(path, self.limits.source_bytes)
        snapshot: JsonObject = object_value(origin["snapshot"], "origin.snapshot")
        frozen: bytes = self.verify_ref(snapshot)
        if digest(content) != origin["sha256"] or len(content) != origin["bytes"] or frozen != content:
            raise IntegrityError("原来源或已登记绑定被修改；拒绝静默继续")


# 功能：读取并核验物理运行快照；参数 root 不会连接或操作 Player。
def read_records(root: Path) -> list[JsonObject]:
    with Journal(root) as journal:
        return list(journal.records)
