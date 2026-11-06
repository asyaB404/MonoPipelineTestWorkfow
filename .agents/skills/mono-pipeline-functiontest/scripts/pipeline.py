"""创建日期：2026-10-26；作者：Cyou。
更新日期：2026-11-05；更新人：Codex；新增兼容历史格式的有界返回投影。
功能：单目标 Mono 静态包/Windows 身份/ACL 门禁、本机 HTTP、包装及真实回执分类。
参数：显式 TargetConfig；测试可在调用层注入身份/传输，正式 CLI 不提供旁路。
边界：不启动/结束进程、不安装、不猜端口、不自动恢复，不是真正脚本沙箱。
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import socket
import stat
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, cast

from .contracts import (
    SCHEMA, EnvironmentBlocked, InputError, IntegrityError, JsonObject, JsonValue, Limits,
    SecretGuard, canonical, digest, hash_value, integer, keys_only, object_value,
    read_regular, reject_links, script_text, strict_json, text,
)
from .inputs import TargetConfig, utc_datetime

DESCRIPTOR_NAME = ".unity-pipeline-runtime-port"
STATUS_PATH = "/api/status"
CATALOG_PATH = "/api/commands?detail=compact&limit=1000"
EXEC_PATH = "/api/exec"
EXEC_KEYS = frozenset({"success", "command", "result", "executionTimeMs", "status", "retryable", "errorCode",
                       "argProblems", "commandSchema", "parameters", "busyReason", "dialogsDuringExecution",
                       "dialogs", "message", "warnings", "error", "errorDetails", "executedAt"})
EVAL_KEYS = EXEC_KEYS | {"output", "diagnostics"}
STATUS_KEYS = frozenset({"UnityVersion", "Platform", "BuildGuid", "Version", "IsPlaying", "TargetFrameRate",
                         "TimeScale", "RealTimeSinceStartup", "FrameCount", "LoadedLevelName", "LoadedLevelBuildIndex",
                         "Performance", "PipelineDriver", "Timestamp"})
DESCRIPTOR_KEYS = frozenset({"pid", "port", "platform", "unityVersion", "buildGuid", "startedAt", "lastHeartbeat",
                            "workingDirectory", "evalToken", "capabilities"})
HOST_VALUE_KEYS = frozenset({"host", "run_id", "case_id", "command_id", "frame", "build_guid", "value"})
WRAPPER_V2_MARKER = b"// mono-pipeline-wrapper/2\n"
RETURN_VALUE_ERRORS = frozenset({"unsupported_return_type", "return_value_budget", "non_finite_return_number",
                                 "return_projection_failed"})
BRIDGE_KEYS = frozenset({"bridge", "frame", "build_guid", "value", "error", "target"})


# 功能：通过固定 Windows PowerShell 查询只读元数据；参数 script 不含凭据。
def _powershell(script: str, timeout_ms: int, maximum: int = 64 * 1024) -> JsonObject:
    if os.name != "nt" or "SystemRoot" not in os.environ:
        raise EnvironmentBlocked("正式身份/ACL 核验要求 Windows")
    powershell: Path = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    try:
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            [str(powershell), "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout_ms / 1000, check=True,
        )
        return object_value(strict_json(result.stdout, maximum, bom=True), "Windows 查询")
    except (OSError, subprocess.SubprocessError, InputError):
        raise EnvironmentBlocked("Windows 只读元数据查询失败；原始输出已排除") from None


# 功能：构造进程/端口/ACL 三合一探测脚本；参数 pid/port/path 均来自显式目标，不扫描或猜目标。
def _probe_script(pid: int, port: int, path: Path) -> str:
    escaped: str = str(path).replace("'", "''")
    return (
        "$ErrorActionPreference='Stop';[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}';"
        "if($null -eq $p){throw 'missing'};"
        f"$c=@(Get-NetTCPConnection -State Listen -LocalPort {port});"
        f"$a=Get-Acl -LiteralPath '{escaped}';"
        "if($null -eq $a){throw 'acl missing'};"
        "$sid=[System.Security.Principal.SecurityIdentifier];"
        "$me=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "$rules=@($a.GetAccessRules($true,$true,$sid)|ForEach-Object{"
        "@{sid=$_.IdentityReference.Value;type=$_.AccessControlType.ToString();rights=[long]$_.FileSystemRights}});"
        "@{process=@{pid=[int]$p.ProcessId;exe=$p.ExecutablePath;"
        "created=$p.CreationDate.ToUniversalTime().ToString('o')};"
        "listeners=@($c|ForEach-Object{@{pid=[int]$_.OwningProcess;address=$_.LocalAddress}});"
        "acl=@{principal=$me;owner=$a.GetOwner($sid).Value;rules=$rules}}|ConvertTo-Json -Compress -Depth 6"
    )


# 功能：一次 PowerShell 取回进程、端口与描述符 ACL；参数 exe 只参与后续精确比较，纯性能等价变换。
def windows_probe(pid: int, exe: Path, port: int, path: Path, timeout_ms: int) -> JsonObject:
    payload: JsonObject = _powershell(_probe_script(pid, port, path), timeout_ms)
    keys_only(payload, {"process", "listeners", "acl"}, "windows probe", {"process", "listeners", "acl"})
    return payload


# 功能：判断缓存探测是否超出同命令复用窗口；参数 window_ms 来自集中 limits，超窗即视为过期。
def _probe_expired(probe: JsonObject, window_ms: int) -> bool:
    stamp: JsonValue = probe.get("probed_monotonic_ns")
    if type(stamp) is not int:
        return True
    return (time.perf_counter_ns() - stamp) / 1_000_000 > window_ms


# 功能：读取明确 PID 的路径及创建时间；参数 exe 只参与后续精确比较。
def windows_process(pid: int, exe: Path, timeout_ms: int) -> JsonObject:
    script: str = (
        "$ErrorActionPreference='Stop';[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}';"
        "if($null -eq $p){throw 'missing'};"
        "@{pid=[int]$p.ProcessId;exe=$p.ExecutablePath;"
        "created=$p.CreationDate.ToUniversalTime().ToString('o')}|ConvertTo-Json -Compress"
    )
    return _powershell(script, timeout_ms)


# 功能：读取端口独占所有者；参数 pid/port 均来自显式目标，不扫描或猜端口。
def windows_port(pid: int, port: int, timeout_ms: int) -> JsonObject:
    script: str = (
        "$ErrorActionPreference='Stop';[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        f"$c=@(Get-NetTCPConnection -State Listen -LocalPort {port});"
        "@{listeners=@($c|ForEach-Object{@{pid=[int]$_.OwningProcess;address=$_.LocalAddress}})}"
        "|ConvertTo-Json -Compress -Depth 4"
    )
    return _powershell(script, timeout_ms)


# 功能：从原始 ACL 载荷核验可读授权并生成证据；参数 payload 来自真实 Get-Acl 输出。
def _acl_evidence(payload: JsonObject) -> JsonObject:
    keys_only(payload, {"principal", "owner", "rules"}, "descriptor.acl", {"principal", "owner", "rules"})
    principal: str = text(payload["principal"], "ACL principal")
    allowed: set[str] = {principal, "S-1-5-18", "S-1-5-32-544"}
    if payload["owner"] not in allowed:
        raise EnvironmentBlocked("描述符 owner 不属于当前用户/SYSTEM/Administrators")
    rules: JsonValue = payload["rules"]
    if not isinstance(rules, list) or not rules:
        raise EnvironmentBlocked("描述符 DACL 缺失；拒绝把落盘令牌视为安全")
    readable: set[str] = set()
    for raw in rules:
        rule: JsonObject = object_value(raw, "ACL rule")
        keys_only(rule, {"sid", "type", "rights"}, "ACL rule", {"sid", "type", "rights"})
        rights: JsonValue = rule["rights"]
        if type(rights) is not int or rule["type"] not in {"Allow", "Deny"}:
            raise EnvironmentBlocked("描述符 ACL 规则不可核验")
        if rule["type"] == "Allow" and rights & (1 | 0x80000000 | 0x10000000):
            identity: str = text(rule["sid"], "ACL SID")
            if identity not in allowed:
                raise EnvironmentBlocked("描述符存在范围过宽的读取授权")
            readable.add(identity)
    if not readable or principal not in readable:
        raise EnvironmentBlocked("描述符未明确授予当前用户读取，拒绝猜测有效权限")
    return {"checked": True, "owner": payload["owner"], "principal": principal,
            "readable_sids": sorted(readable), "rule_sha256": digest(canonical(payload)),
            "policy": "current_user_system_administrators_only"}


# 功能：实际核验描述符 DACL 的可读授权；参数 path 指向确实含令牌的落盘文件。
def windows_acl(path: Path, timeout_ms: int) -> JsonObject:
    escaped: str = str(path).replace("'", "''")
    script: str = (
        "$ErrorActionPreference='Stop';[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        f"$a=Get-Acl -LiteralPath '{escaped}';"
        "if($null -eq $a){throw 'acl missing'};"
        "$sid=[System.Security.Principal.SecurityIdentifier];"
        "$me=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;"
        "$rules=@($a.GetAccessRules($true,$true,$sid)|ForEach-Object{"
        "@{sid=$_.IdentityReference.Value;type=$_.AccessControlType.ToString();rights=[long]$_.FileSystemRights}});"
        "@{principal=$me;owner=$a.GetOwner($sid).Value;rules=$rules}|ConvertTo-Json -Compress -Depth 5"
    )
    return _acl_evidence(_powershell(script, timeout_ms))


@dataclass(frozen=True)
class IdentityHooks:
    """仅在 Python 调用层注入系统查询，正式 CLI 始终使用本类默认实现。"""

    process: Callable[[int, Path, int], JsonObject] = windows_process
    port: Callable[[int, int, int], JsonObject] = windows_port
    acl: Callable[[Path, int], JsonObject] = windows_acl


# 功能：判断是否全部使用包内默认 Windows 探测；参数 hooks 为调用层注入实现时返回 False。
def _default_probes(hooks: IdentityHooks) -> bool:
    return hooks.process is windows_process and hooks.port is windows_port and hooks.acl is windows_acl


# 功能：流式核验静态包成员字节及文件身份，保留空成员摘要；参数 maximum 是集中单文件上限。
def _file_hash(path: Path, maximum: int) -> tuple[str, int]:
    reject_links(path)
    before: os.stat_result = path.stat()
    if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
        raise EnvironmentBlocked("静态包成员类型或字节大小非法")
    checksum: hashlib._Hash = hashlib.sha256()
    count: int = 0
    try:
        with path.open("rb") as stream:
            while True:
                chunk: bytes = stream.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > maximum:
                    raise EnvironmentBlocked("静态包成员超出预算")
                checksum.update(chunk)
            held: os.stat_result = os.fstat(stream.fileno())
        after: os.stat_result = path.stat()
    except OSError:
        raise EnvironmentBlocked("静态包成员读取失败") from None
    if len({(item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns) for item in (before, held, after)}) != 1 or count != before.st_size:
        raise EnvironmentBlocked("静态包在核验期间变化")
    return checksum.hexdigest(), count


# 功能：按清单顺序并行核验多个静态包成员；参数 names 已去重且顺序即首个失败顺序，不改变单成员语义。
def _file_hashes(root: Path, names: list[str], maximum: int) -> dict[str, tuple[str, int]]:
    if len(names) < 2:
        return {name: _file_hash(root / Path(name), maximum) for name in names}
    workers: int = min(8, max(2, os.cpu_count() or 2))
    results: dict[str, tuple[str, int]] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending: list[tuple[str, Future[tuple[str, int]]]] = [
            (name, pool.submit(_file_hash, root / Path(name), maximum)) for name in names]
        for name, future in pending:
            results[name] = future.result()
    return results


# 功能：identity_only 口径的静态包核验；参数 target 为唯一目标，只验包声明身份、必要标记与 EXE，不逐成员比对字节。
def _verify_package_identity_only(target: TargetConfig) -> JsonObject:
    limits: Limits = target.limits
    license_bytes: bytes = read_regular(target.license_path, limits.source_bytes)
    if digest(license_bytes) != target.license_sha256:
        raise EnvironmentBlocked("许可文件原字节摘要不匹配")
    manifest_bytes: bytes = read_regular(target.package_manifest, limits.input_bytes)
    manifest: JsonObject = object_value(strict_json(manifest_bytes, limits.input_bytes, limits, bom=True), "package manifest")
    keys_only(manifest, {"schema", "backend", "development", "complete", "exe", "build_guid", "unity_version", "platform", "files", "_comment"},
              "package manifest", {"schema", "backend", "development", "complete", "exe", "build_guid", "unity_version", "platform", "files"})
    if manifest["schema"] != "mono-pipeline-package/1" or manifest["backend"] != "mono" or manifest["development"] is not True or manifest["complete"] is not True:
        raise EnvironmentBlocked("必须提供完整 Mono Development 静态包清单")
    if any(manifest[key] != value for key, value in {
        "exe": target.exe.name, "build_guid": target.build_guid, "unity_version": target.unity_version,
        "platform": target.platform,
    }.items()):
        raise EnvironmentBlocked("静态包声明与明确目标不一致")
    root: Path = target.exe.parent
    data_name: str = target.exe.stem + "_Data"
    if (root / "GameAssembly.dll").exists() or (root / data_name / "il2cpp_data").exists():
        raise EnvironmentBlocked("静态包存在 IL2CPP/冲突标记，禁止连接")
    files: JsonValue = manifest["files"]
    if not isinstance(files, list) or not files or len(files) > limits.package_entries:
        raise EnvironmentBlocked("静态包清单成员数非法")
    with target.exe.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise EnvironmentBlocked("明确 EXE 缺少 Windows 可执行标记")
    # EXE 摘要按 1MB 分块流式计算，不把整个 EXE 读入内存（2026-11-03 修复）。
    exe_sha256: str = _file_hash(target.exe, limits.package_file_bytes)[0]
    return {"backend": "mono", "development_declaration": True, "complete_static_files": False,
            "integrity_mode": "identity_only", "file_count": len(files),
            "manifest_sha256": digest(manifest_bytes), "exe_sha256": exe_sha256,
            "license_sha256": digest(license_bytes), "license_scope": target.license_scope, "runtime_verified": False}


# 功能：核验完整 Mono 静态包及固定清单，不把文件存在当运行验收；参数 target 为唯一目标，probe_cache 仅复用已验证成员摘要。
def verify_package(target: TargetConfig, probe_cache: dict[str, tuple[str, int]] | None = None) -> JsonObject:
    limits: Limits = target.limits
    # identity_only 跳过逐成员全包 sha256：仍核验许可、包声明身份、IL2CPP 冲突标记与 EXE 可执行标记。
    if target.integrity_mode == "identity_only":
        return _verify_package_identity_only(target)
    license_bytes: bytes = read_regular(target.license_path, limits.source_bytes)
    if digest(license_bytes) != target.license_sha256:
        raise EnvironmentBlocked("许可文件原字节摘要不匹配")
    manifest_bytes: bytes = read_regular(target.package_manifest, limits.input_bytes)
    manifest: JsonObject = object_value(strict_json(manifest_bytes, limits.input_bytes, limits, bom=True), "package manifest")
    keys_only(manifest, {"schema", "backend", "development", "complete", "exe", "build_guid", "unity_version", "platform", "files", "_comment"},
              "package manifest", {"schema", "backend", "development", "complete", "exe", "build_guid", "unity_version", "platform", "files"})
    if manifest["schema"] != "mono-pipeline-package/1" or manifest["backend"] != "mono" or manifest["development"] is not True or manifest["complete"] is not True:
        raise EnvironmentBlocked("必须提供完整 Mono Development 静态包清单")
    if any(manifest[key] != value for key, value in {
        "exe": target.exe.name, "build_guid": target.build_guid, "unity_version": target.unity_version,
        "platform": target.platform,
    }.items()):
        raise EnvironmentBlocked("静态包声明与明确目标不一致")
    root: Path = target.exe.parent
    data_name: str = target.exe.stem + "_Data"
    if (root / "GameAssembly.dll").exists() or (root / data_name / "il2cpp_data").exists():
        raise EnvironmentBlocked("静态包存在 IL2CPP/冲突标记，禁止连接")
    files: JsonValue = manifest["files"]
    if not isinstance(files, list) or not files or len(files) > limits.package_entries:
        raise EnvironmentBlocked("静态包清单成员数非法")
    declared: dict[str, JsonObject] = {}
    folded: set[str] = set()
    for raw in files:
        entry: JsonObject = object_value(raw, "package file")
        keys_only(entry, {"path", "bytes", "sha256"}, "package file", {"path", "bytes", "sha256"})
        name: str = text(entry["path"], "package file.path")
        relative: Path = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or name.casefold() in folded or name == DESCRIPTOR_NAME:
            raise EnvironmentBlocked("静态包成员路径重复、越界或包含敏感运行描述符")
        folded.add(name.casefold())
        declared[name] = entry
    reusable: dict[str, tuple[str, int]] = probe_cache if probe_cache is not None else {}
    pending: list[str] = [name for name in declared if name not in reusable]
    computed: dict[str, tuple[str, int]] = _file_hashes(root, pending, limits.package_file_bytes)
    for name, entry in declared.items():
        actual_hash, actual_size = reusable.get(name) or computed[name]
        if actual_hash != hash_value(entry["sha256"], "package file.sha256") or actual_size != integer(entry["bytes"], "package file.bytes", 0, limits.package_file_bytes):
            raise EnvironmentBlocked("完整静态包成员摘要或大小不匹配")
        reusable[name] = (actual_hash, actual_size)
    required: set[str] = {
        target.exe.name, "UnityPlayer.dll", data_name + "/globalgamemanagers", data_name + "/boot.config",
        data_name + "/Managed/Assembly-CSharp.dll", data_name + "/Managed/Unity.Pipeline.dll",
        "MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll",
    }
    if not required <= set(declared):
        raise EnvironmentBlocked("静态包缺失必要 Mono/Unity/Pipeline 成员")
    for name in sorted(required):
        if declared[name]["bytes"] == 0:
            raise EnvironmentBlocked("静态包必要成员为空: " + name)
    with target.exe.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise EnvironmentBlocked("明确 EXE 缺少 Windows 可执行标记")
    actual: set[str] = set()
    entries: int = 0
    for directory, dirs, filenames in os.walk(root, followlinks=False):
        for name in dirs + filenames:
            entries += 1
            if entries > limits.package_entries:
                raise EnvironmentBlocked("静态包扫描超过集中成员预算")
            reject_links(Path(directory) / name)
        for filename in filenames:
            path: Path = Path(directory) / filename
            if path == target.package_manifest or path == root / DESCRIPTOR_NAME:
                continue
            actual.add(path.relative_to(root).as_posix())
    if actual != set(declared):
        raise EnvironmentBlocked("完整静态包有未登记或缺失文件；运行日志/截图应在包外")
    return {"backend": "mono", "development_declaration": True, "complete_static_files": True,
            "file_count": len(declared), "manifest_sha256": digest(manifest_bytes),
            "exe_sha256": declared[target.exe.name]["sha256"], "license_sha256": digest(license_bytes),
            "license_scope": target.license_scope, "runtime_verified": False}


@dataclass(frozen=True)
class VerifiedIdentity:
    """令牌确实从本地描述符读取；repr 与公共证据永远排除此敏感字段。"""

    pid: int
    port: int
    created: str
    build_guid: str
    unity_version: str
    platform: str
    token: str = field(repr=False)
    evidence: JsonObject = field(default_factory=dict)


# 功能：在任何网络请求前核验完整静态身份，心跳年龄仅作诊断；参数 package=False 仅用于同目标后续本地核验，package 为字典时复用已核验成员摘要，probe_cache 复用同命令内已验证探测。
def verify_target_identity(target: TargetConfig, hooks: IdentityHooks, package: bool | dict[str, tuple[str, int]] = True,
                           probe_cache: dict[str, JsonObject] | None = None) -> VerifiedIdentity:
    if not {"attach", "script_execute"} <= target.permissions:
        raise EnvironmentBlocked("附加及所有脚本读取/断言均要求 attach + script_execute 明确许可")
    static_evidence: JsonObject = ({} if package is False
                                   else verify_package(target, package if isinstance(package, dict) else None))
    descriptor_path: Path = target.exe.parent / DESCRIPTOR_NAME
    reject_links(descriptor_path)
    process: JsonObject | None = None
    listeners: JsonValue = None
    acl: JsonObject | None = None
    if _default_probes(hooks):
        probe: JsonObject | None = None if probe_cache is None else probe_cache.get("windows")
        if probe is not None and _probe_expired(probe, target.limits.identity_cache_ms):
            probe = None
            probe_cache.pop("windows", None) if probe_cache is not None else None
        if probe is None:
            probe = windows_probe(target.pid, target.exe, target.port, descriptor_path, target.limits.identity_timeout_ms)
            # 记录真实探测时刻，超窗后强制重新查询，不做跨命令保活。
            probe["probed_monotonic_ns"] = time.perf_counter_ns()
            if probe_cache is not None:
                probe_cache["windows"] = probe
        process = object_value(probe["process"], "probe process")
        listeners = probe["listeners"]
        acl = _acl_evidence(object_value(probe["acl"], "probe acl"))
    else:
        acl = hooks.acl(descriptor_path, target.limits.identity_timeout_ms)
    if acl.get("checked") is not True or acl.get("policy") != "current_user_system_administrators_only":
        raise EnvironmentBlocked("描述符 Windows ACL 未获实际核验")
    raw: bytes = read_regular(descriptor_path, target.limits.descriptor_bytes)
    descriptor: JsonObject = object_value(strict_json(raw, target.limits.descriptor_bytes, target.limits, bom=True), "runtime descriptor")
    keys_only(descriptor, DESCRIPTOR_KEYS, "runtime descriptor", DESCRIPTOR_KEYS - {"capabilities"})
    if descriptor["pid"] != target.pid or descriptor["port"] != target.port or type(descriptor["pid"]) is not int or type(descriptor["port"]) is not int:
        raise EnvironmentBlocked("描述符 PID/端口不属于唯一明确目标")
    if descriptor["platform"] != target.platform or descriptor["unityVersion"] != target.unity_version or descriptor["buildGuid"] != target.build_guid:
        raise EnvironmentBlocked("描述符 BuildGuid/UnityVersion/Platform 不匹配")
    working: str = text(descriptor["workingDirectory"], "descriptor.workingDirectory")
    if os.path.normcase(str(Path(working).absolute())) != os.path.normcase(str(target.working_directory)):
        raise EnvironmentBlocked("描述符工作目录与明确目标不一致")
    token: str = text(descriptor["evalToken"], "descriptor credential")
    try:
        decoded: bytes = base64.b64decode(token, validate=True)
    except ValueError:
        raise EnvironmentBlocked("描述符凭据格式非法；原文已排除") from None
    if len(decoded) != 32:
        raise EnvironmentBlocked("描述符凭据长度非法；原文已排除")
    created_time: datetime = utc_datetime(target.process_created_utc, "process created")
    started: datetime = utc_datetime(descriptor["startedAt"], "descriptor startedAt")
    heartbeat: datetime = utc_datetime(descriptor["lastHeartbeat"], "descriptor lastHeartbeat")
    now: datetime = datetime.now(timezone.utc)
    if started < created_time or heartbeat < started or (heartbeat - now).total_seconds() * 1000 > target.limits.clock_tolerance_ms:
        raise EnvironmentBlocked("描述符时间身份不成立；不允许用探活修正非法时间")
    actual_process: JsonObject = process if process is not None else hooks.process(target.pid, target.exe, target.limits.identity_timeout_ms)
    keys_only(actual_process, {"pid", "exe", "created"}, "process identity", {"pid", "exe", "created"})
    if type(actual_process["pid"]) is not int or actual_process["pid"] != target.pid or utc_datetime(actual_process["created"], "actual created") != created_time:
        raise EnvironmentBlocked("PID 创建时间不匹配；禁止重连到复用 PID")
    if os.path.normcase(str(Path(text(actual_process["exe"], "actual exe")).absolute())) != os.path.normcase(str(target.exe)):
        raise EnvironmentBlocked("PID 实际 EXE 与明确目标不匹配")
    if listeners is None:
        ports: JsonObject = hooks.port(target.pid, target.port, target.limits.identity_timeout_ms)
        keys_only(ports, {"listeners"}, "port identity", {"listeners"})
        listeners = ports["listeners"]
    if not isinstance(listeners, list) or not listeners:
        raise EnvironmentBlocked("明确端口没有监听者，不猜其他端口")
    for entry in listeners:
        listener: JsonObject = object_value(entry, "listener")
        keys_only(listener, {"pid", "address"}, "listener", {"pid", "address"})
        if type(listener["pid"]) is not int or listener["pid"] != target.pid or listener["address"] not in {"127.0.0.1", "0.0.0.0", "::", "::1"}:
            raise EnvironmentBlocked("明确端口非目标 PID 独占或监听地址异常")
    age_ms: float = (datetime.now(timezone.utc) - heartbeat).total_seconds() * 1000
    descriptor_binding: JsonObject = {key: value for key, value in descriptor.items() if key != "lastHeartbeat"}
    evidence: JsonObject = {"pid": target.pid, "port": target.port, "created": target.process_created_utc,
                            "exe": str(target.exe), "build_guid": target.build_guid, "unity_version": target.unity_version,
                            "platform": target.platform, "acl": acl, "listeners": listeners,
                            "static_package": static_evidence, "credential_storage": "descriptor_contains_token_on_disk",
                            "descriptor_started_utc": started.isoformat(), "descriptor_heartbeat_utc": heartbeat.isoformat(),
                            "descriptor_age_ms": age_ms, "descriptor_fresh": age_ms <= target.limits.descriptor_age_ms,
                            "descriptor_identity_sha256": digest(canonical(descriptor_binding))}
    SecretGuard((token,)).check(evidence)
    return VerifiedIdentity(target.pid, target.port, target.process_created_utc, target.build_guid,
                            target.unity_version, target.platform, token, evidence)


# 功能：保持公共严格新鲜度核验，不自行连接或刷新；参数 package 控制是否再次流式读取已验证静态包，probe_cache 复用同命令探测。
def verify_target(target: TargetConfig, hooks: IdentityHooks, package: bool | dict[str, tuple[str, int]] = True,
                  probe_cache: dict[str, JsonObject] | None = None) -> VerifiedIdentity:
    identity: VerifiedIdentity = verify_target_identity(target, hooks, package, probe_cache)
    if identity.evidence["descriptor_fresh"] is not True:
        raise EnvironmentBlocked("描述符心跳过期；必须先经过已确认身份的认证状态握手")
    return identity


# 功能：核验探活前后的不可变描述符及目标绑定；参数 token 仅在内存比较，不自动接管新凭据。
def same_target_identity(expected: VerifiedIdentity, current: VerifiedIdentity) -> None:
    if (current.token != expected.token or current.created != expected.created
            or current.evidence["descriptor_identity_sha256"] != expected.evidence["descriptor_identity_sha256"]):
        raise EnvironmentBlocked("连接期间目标或描述符身份变化；禁止自动接管")


@dataclass(frozen=True)
class HttpResponse:
    """有界严格 JSON 回执；不保存原 HTTP headers 或凭据。"""

    status: int
    payload: JsonObject


class Transport(Protocol):
    """本机正常 HTTP 传输契约；注入实现同样经过公共回执分类。"""

    # 功能：发送一次请求；参数 timeout_ms 为本次剩余总预算。
    def request(self, path: str, body: JsonObject | None, timeout_ms: int) -> HttpResponse: ...

    # 功能：仅断开本次连接；参数无，不结束进程。
    def close(self) -> None: ...


class LocalHttp:
    """仅连 127.0.0.1，单次请求有总截止时间，任何错误不重试。"""

    # 功能：保存已经核验的端口和内存凭据；参数 limits 为集中预算，构造不连接。
    def __init__(self, port: int, token: str, limits: Limits) -> None:
        self._port: int = port
        self._token: str = token
        self._limits: Limits = limits
        self._connection: http.client.HTTPConnection | None = None
        self._closed: bool = False

    # 功能：停止本次连接；参数无，不表示 Player 内代码已经停止。
    def close(self) -> None:
        connection: http.client.HTTPConnection | None = self._connection
        self._connection = None
        self._closed = True
        self._token = ""
        if connection is not None:
            if connection.sock is not None:
                try:
                    connection.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            connection.close()

    # 功能：发送一次认证请求并有界读取；参数 body 使用结构化 JSON，无命令行脚本。
    def request(self, path: str, body: JsonObject | None, timeout_ms: int) -> HttpResponse:
        if self._closed or path not in {STATUS_PATH, CATALOG_PATH, EXEC_PATH}:
            raise EnvironmentBlocked("HTTP 连接关闭或路径不在固定 API 契约内")
        effective: int = integer(timeout_ms, "request timeout", 1, max(self._limits.identity_timeout_ms, self._limits.max_timeout_ms))
        connection: http.client.HTTPConnection = http.client.HTTPConnection("127.0.0.1", self._port, timeout=effective / 1000)
        self._connection = connection
        expired: threading.Event = threading.Event()

        # 功能：关闭超出总预算的 socket；参数无，不声称终止远端代码。
        def deadline() -> None:
            expired.set()
            self.close()

        timer: threading.Timer = threading.Timer(effective / 1000, deadline)
        timer.daemon = True
        encoded: bytes | None = canonical(body) if body is not None else None
        headers: dict[str, str] = {"Authorization": "Bearer " + self._token, "Accept": "application/json"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"
        timer.start()
        try:
            connection.request("POST" if encoded is not None else "GET", path, encoded, headers)
            response: http.client.HTTPResponse = connection.getresponse()
            if response.getheader("Content-Encoding") not in (None, "identity"):
                raise EnvironmentBlocked("HTTP 不接受压缩或未知编码响应")
            declared: str | None = response.getheader("Content-Length")
            if declared is not None and (not declared.isdigit() or int(declared) > self._limits.response_bytes):
                raise EnvironmentBlocked("HTTP 响应声明字节数越界")
            chunks: list[bytes] = []
            size: int = 0
            while True:
                if expired.is_set():
                    raise EnvironmentBlocked("HTTP 总预算耗尽；结果未知")
                chunk: bytes = response.read1(min(8192, self._limits.response_bytes + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > self._limits.response_bytes:
                    raise EnvironmentBlocked("HTTP 响应字节大小越界")
                chunks.append(chunk)
            if expired.is_set() or (declared is not None and size != int(declared)):
                raise EnvironmentBlocked("HTTP 回执超时或字节不完整；结果未知")
            payload: JsonObject = object_value(strict_json(b"".join(chunks), self._limits.response_bytes, self._limits), "HTTP response")
            return HttpResponse(int(response.status), payload)
        except (OSError, http.client.HTTPException, InputError, EnvironmentBlocked, ValueError):
            self.close()
            raise EnvironmentBlocked("本机 HTTP 请求未取得可靠回执；可能仍在执行，原异常已排除") from None
        finally:
            timer.cancel()
            connection.close()
            self._connection = None


@dataclass(frozen=True)
class EvalReceipt:
    """编译未执行、成功和未知阶段；value 不直接形成产品 verdict。"""

    state: str
    phase: str
    value: JsonValue
    diagnostic: str
    diagnostics: tuple[JsonObject, ...] = ()

    # 功能：输出已排除敏感原文的分类；参数无。
    def to_json(self) -> JsonObject:
        return {"state": self.state, "phase": self.phase, "value": self.value,
                "diagnostic": self.diagnostic, "diagnostics": list(self.diagnostics),
                "execution_terminated": False if self.state == "unknown" else None}


# 功能：固定外/内层真实回执分类；参数 expected_command 为 eval 或 eval_file，禁止递归猜测。
def classify_eval(response: HttpResponse, expected_command: str, limits: Limits,
                  guard: SecretGuard | None = None) -> EvalReceipt:
    secrecy: SecretGuard = guard if guard is not None else SecretGuard()
    try:
        payload: JsonObject = object_value(response.payload, "eval outer")
        if len(canonical(payload)) > limits.response_bytes:
            raise InputError("回执超出预算")
        keys_only(payload, EXEC_KEYS, "eval outer", {"success", "command", "result"})
        if type(response.status) is not int or response.status != 200 or payload["success"] is not True or payload["command"] != expected_command or payload.get("error") or payload.get("errorDetails"):
            return EvalReceipt("unknown", "execution", None, "外层未确认本次求值；不得重放")
        evaluation: JsonObject = object_value(payload["result"], "eval inner")
        keys_only(evaluation, EVAL_KEYS, "eval inner", {"success", "diagnostics"})
        if type(evaluation["success"]) is not bool or evaluation.get("command", "eval") != "eval":
            raise InputError("内层命令或成功字段非法")
        raw_diagnostics: JsonValue = evaluation["diagnostics"]
        if not isinstance(raw_diagnostics, list) or len(raw_diagnostics) > 256:
            raise InputError("求值诊断结构非法")
        diagnostics: list[JsonObject] = []
        has_error: bool = False
        for raw in raw_diagnostics:
            diagnostic: JsonObject = object_value(raw, "eval diagnostic")
            keys_only(diagnostic, {"severity", "message", "line", "column", "id"}, "eval diagnostic", {"severity"})
            severity: str = text(diagnostic["severity"], "diagnostic.severity").lower()
            if severity not in {"error", "warning", "info", "hidden"}:
                raise InputError("未知诊断等级")
            for name in ("line", "column"):
                if name in diagnostic:
                    integer(diagnostic[name], "diagnostic position", 0)
            for name in ("id", "message"):
                if name in diagnostic and not isinstance(diagnostic[name], str):
                    raise InputError("求值诊断文本字段非法")
            has_error = has_error or severity == "error"
            diagnostics.append({**diagnostic, "message": secrecy.diagnostic(diagnostic.get("message", "")),
                                "id": secrecy.diagnostic(diagnostic.get("id", ""))})
        raw_error: JsonValue = evaluation.get("error")
        raw_details: JsonValue = evaluation.get("errorDetails")
        if (raw_error is not None and not isinstance(raw_error, str)) or (raw_details is not None and not isinstance(raw_details, str)):
            raise InputError("求值错误字段必须为 null 或文本")
        # 协议中的 null 表示未提供错误文本，不能被 diagnostic() 的缺诊断提示变成一个假运行错误。
        error: str = "" if raw_error is None else secrecy.diagnostic(raw_error)
        details: str = "" if raw_details is None else secrecy.diagnostic(raw_details)
        if evaluation["success"] is False:
            # 只有真实编译失败标记 + error 诊断 + 无结果才明确未执行。
            if evaluation.get("error") == "Compilation Failed" and has_error and evaluation.get("result") is None and not evaluation.get("output"):
                return EvalReceipt("compile_failed", "compilation_not_executed", None, details or error, tuple(diagnostics))
            # 外层已确认本次求值、内层无结果且**未标记为运行期异常**：可判为脚本自身缺陷（如反射类型不一致），
            # 用独立 phase=script_failed 与外层未确认/协议失真/传输中断区分，供上层只影响该用例而非整轮。
            # 显式 "Runtime Error" 可能已部分执行副作用，仍按整轮冻结处理，绝不降级。
            if evaluation.get("result") is None and not has_error and not error and details:
                return EvalReceipt("unknown", "script_failed", None, details, tuple(diagnostics))
            return EvalReceipt("unknown", "execution", None, details or error or "运行异常；可能部分执行", tuple(diagnostics))
        if has_error or "result" not in evaluation or evaluation.get("error") or evaluation.get("errorDetails"):
            raise InputError("求值成功回执矛盾或缺值")
        secrecy.check(payload)
        if len(canonical(evaluation["result"])) > limits.value_bytes:
            raise InputError("实际值超出预算")
        return EvalReceipt("succeeded", "completed", evaluation["result"], "", tuple(diagnostics))
    except IntegrityError:
        return EvalReceipt("unknown", "sensitive_result", None, "敏感回执被拒收；原文未保存")
    except (InputError, ValueError, TypeError, RecursionError):
        return EvalReceipt("unknown", "protocol", None, "求值回执不符合有界严格契约；不得重放")


# 功能：识别已冻结包装的格式；参数 raw 仍须通过摘要及逐字节再生核验，标记自身不构成信任。
def wrapper_format(raw: bytes) -> int:
    return 2 if raw.startswith(WRAPPER_V2_MARKER) else 1


# 功能：将用户片段包入独立方法体；参数 version=1 保留历史原字节，2 由 Codex 增加有界 JSON 投影。
def wrap_script(raw: bytes, run_id: str, case_id: str, command_id: str, limits: Limits,
                guard: SecretGuard, version: int = 2) -> bytes:
    if type(version) is not int or version not in {1, 2}:
        raise InputError("未知宿主包装格式")
    code: str = script_text(raw, limits, guard)
    literals: list[str] = [json.dumps(value, ensure_ascii=True) for value in (SCHEMA, run_id, case_id, command_id)]
    wrapper: str = (
        "// 创建日期：2026-10-26；作者：Cyou；功能：固定本轮身份与真实帧；参数：用户方法体。\n"
        "System.Func<object> __mpft_body = delegate() {\n" + code + "\n};\n"
        "object __mpft_value = __mpft_body();\n"
    )
    if version == 2:
        # 只复制标准容器；不执行返回委托、不遍历任意对象属性。预算为外层回执和证据留出空间。
        projection: str = (
            "string __mpft_error = null;\n"
            "int __mpft_nodes = 0;\n"
            f"long __mpft_bytes = {512 + 6 * sum(len(value) for value in (SCHEMA, run_id, case_id, command_id))};\n"
            "System.Action<long> __mpft_charge = delegate(long amount) {\n"
            "    __mpft_bytes += amount;\n"
            f"    if (__mpft_bytes > {limits.value_bytes}) {{ __mpft_error = \"return_value_budget\"; throw new System.InvalidOperationException(); }}\n"
            "};\n"
            "System.Func<object,int,object> __mpft_json = null;\n"
            "__mpft_json = delegate(object item, int depth) {\n"
            "    __mpft_nodes++;\n"
            f"    if (__mpft_nodes > {max(0, limits.json_nodes - 256)} || depth > {max(0, limits.json_depth - 12)}) {{\n"
            "        __mpft_error = \"return_value_budget\"; throw new System.InvalidOperationException();\n"
            "    }\n"
            "    __mpft_charge(2);\n"
            "    if (item == null) { __mpft_charge(4); return null; }\n"
            "    System.Type kind = item.GetType();\n"
            "    if (kind == typeof(string)) { __mpft_charge(6L * ((string)item).Length + 2); return item; }\n"
            "    if (kind == typeof(bool) || kind == typeof(byte) || kind == typeof(sbyte) || kind == typeof(short)\n"
            "        || kind == typeof(ushort) || kind == typeof(int) || kind == typeof(uint) || kind == typeof(long)\n"
            "        || kind == typeof(ulong) || kind == typeof(decimal)) { __mpft_charge(32); return item; }\n"
            "    if (kind == typeof(double) || kind == typeof(float)) {\n"
            "        double number = System.Convert.ToDouble(item, System.Globalization.CultureInfo.InvariantCulture);\n"
            "        if (System.Double.IsNaN(number) || System.Double.IsInfinity(number)) {\n"
            "            __mpft_error = \"non_finite_return_number\"; throw new System.InvalidOperationException();\n"
            "        } __mpft_charge(32); return item;\n"
            "    }\n"
            "    bool dictionary = kind == typeof(System.Collections.Hashtable) || (kind.IsGenericType\n"
            "        && kind.GetGenericTypeDefinition() == typeof(System.Collections.Generic.Dictionary<,>)\n"
            "        && kind.GetGenericArguments()[0] == typeof(string));\n"
            "    if (dictionary) {\n"
            "        System.Collections.Generic.Dictionary<string, object> copy = new System.Collections.Generic.Dictionary<string, object>();\n"
            "        foreach (System.Collections.DictionaryEntry entry in (System.Collections.IDictionary)item) {\n"
            "            if (!(entry.Key is string)) { __mpft_error = \"unsupported_return_type\"; throw new System.InvalidOperationException(); }\n"
            "            string key = (string)entry.Key; __mpft_charge(6L * key.Length + 4);\n"
            "            copy.Add(key, __mpft_json(entry.Value, depth + 1));\n"
            "        } return copy;\n"
            "    }\n"
            "    if ((kind.IsArray && ((System.Array)item).Rank == 1) || kind == typeof(System.Collections.ArrayList)\n"
            "        || (kind.IsGenericType && kind.GetGenericTypeDefinition() == typeof(System.Collections.Generic.List<>))) {\n"
            "        System.Collections.Generic.List<object> copy = new System.Collections.Generic.List<object>();\n"
            "        foreach (object child in (System.Collections.IEnumerable)item) { copy.Add(__mpft_json(child, depth + 1)); }\n"
            "        return copy;\n"
            "    }\n"
            "    __mpft_error = \"unsupported_return_type\"; throw new System.InvalidOperationException();\n"
            "};\n"
            "try { __mpft_value = __mpft_json(__mpft_value, 0); }\n"
            "catch (System.Exception) {\n"
            "    __mpft_value = null; if (__mpft_error == null) { __mpft_error = \"return_projection_failed\"; }\n"
            "}\n"
        )
        wrapper = (WRAPPER_V2_MARKER.decode("ascii")
                   + "// Updated: 2026-11-05; Author: Codex; bounded return projection before serialization.\n"
                   + wrapper + projection)
    wrapper += (
        "return new System.Collections.Generic.Dictionary<string, object> {\n"
        f'{{"host", {literals[0]}}}, {{"run_id", {literals[1]}}}, {{"case_id", {literals[2]}}},\n'
        f'{{"command_id", {literals[3]}}}, {{"frame", UnityEngine.Time.frameCount}},\n'
        '{"build_guid", UnityEngine.Application.buildGUID}, {"value", __mpft_value}'
        + (', {"value_error", __mpft_error}' if version == 2 else "") + "\n};\n"
    )
    encoded: bytes = wrapper.encode("utf-8")
    if len(encoded) > limits.wrapper_bytes:
        raise InputError("实际包装字节超过集中预算")
    guard.check_bytes(encoded)
    return encoded


# 功能：核验宿主包装身份并单层可选桥接解包；参数 expected_target 为本例当前目标。
def observed_value(receipt: EvalReceipt, run_id: str, case_id: str, command_id: str, build_guid: str,
                   value_format: str, expected_target: JsonValue, limits: Limits,
                   wrapper_version: int = 1) -> tuple[int, JsonValue, str]:
    try:
        if type(wrapper_version) is not int or wrapper_version not in {1, 2}:
            raise InputError("未知宿主包装格式")
        envelope: JsonObject = object_value(receipt.value, "host envelope")
        fields: frozenset[str] = HOST_VALUE_KEYS | {"value_error"} if wrapper_version == 2 else HOST_VALUE_KEYS
        keys_only(envelope, fields, "host envelope", fields)
        frame: int = integer(envelope["frame"], "Unity frame", 0)
    except InputError:
        raise IntegrityError("宿主包装协议/真实帧不可靠") from None
    if any(envelope[key] != value for key, value in {"host": SCHEMA, "run_id": run_id, "case_id": case_id,
                                                    "command_id": command_id, "build_guid": build_guid}.items()):
        raise IntegrityError("求值回执的 run/case/command/build 身份不匹配")
    value: JsonValue = envelope["value"]
    if wrapper_version == 2:
        value_error: JsonValue = envelope["value_error"]
        if value_error is not None:
            if not isinstance(value_error, str) or value_error not in RETURN_VALUE_ERRORS or value is not None:
                raise IntegrityError("返回值错误与已验证包装契约不一致")
            return frame, None, "return_value_contract:" + value_error
    if value_format == "json":
        return frame, value, ""
    if value_format != "bridge":
        raise InputError("实际值格式只能为 json 或 bridge")
    try:
        bridge: JsonObject = object_value(strict_json(value.encode("utf-8"), limits.value_bytes, limits)
                                        if isinstance(value, str) else value, "bridge envelope")
        keys_only(bridge, BRIDGE_KEYS, "bridge envelope", BRIDGE_KEYS)
        bridge_frame: int = integer(bridge["frame"], "bridge frame", 0)
        if bridge["error"] is not None and not isinstance(bridge["error"], str):
            raise InputError("bridge error 必须为 null 或文本")
    except InputError:
        raise IntegrityError("桥接返回未知/缺失协议字段或非法实际帧") from None
    if bridge["bridge"] != SCHEMA or bridge["build_guid"] != build_guid or bridge_frame != frame:
        raise IntegrityError("桥接版本/build/frame 与宿主回执不一致")
    if bridge["target"] != expected_target or expected_target is None:
        raise InputError("桥接没有唯一匹配的当前目标")
    if bridge["error"] not in (None, ""):
        return frame, None, "桥接返回目标/字段/业务错误，不能变成默认值"
    return frame, bridge["value"], ""


class Pipeline:
    """每个 CLI 可重建正常连接，但必须重验身份；任何未知回执不在此自动恢复。"""

    # 功能：保存无副作用依赖；参数 hooks/factory 仅供 Python 隔离调用层注入，probe_cache 限定同命令复用。
    def __init__(self, target: TargetConfig, hooks: IdentityHooks | None = None,
                 factory: Callable[[int, str, Limits], Transport] = LocalHttp,
                 probe_cache: dict[str, JsonObject] | None = None) -> None:
        self.target: TargetConfig = target
        self.hooks: IdentityHooks = hooks if hooks is not None else IdentityHooks()
        self.factory: Callable[[int, str, Limits], Transport] = factory
        self.identity: VerifiedIdentity | None = None
        self.transport: Transport | None = None
        self.guard: SecretGuard = SecretGuard()
        # 同命令探测缓存只存活于单个 Pipeline 生命周期，不跨 CLI 复用陈旧身份。
        self.probe_cache: dict[str, JsonObject] = probe_cache if probe_cache is not None else {}
        # 首次连接核验完整静态包并登记成员摘要；同一命令内后续重连复用该摘要。
        self.static_cache: dict[str, tuple[str, int]] = {}

    # 功能：仅对已确认的同目标发一次认证状态读取并复核落盘新鲜度；参数 identity 不允许目标/凭据变化。
    def _status_handshake(self, identity: VerifiedIdentity) -> tuple[VerifiedIdentity, JsonObject]:
        transport: Transport | None = self.transport
        if transport is None:
            raise EnvironmentBlocked("只读状态握手缺少已确认目标的连接")
        try:
            response: HttpResponse = transport.request(STATUS_PATH, None, self.target.limits.identity_timeout_ms)
            self.guard.check(response.payload)
            keys_only(response.payload, {"status", "lastHeartbeat", "capabilities"}, "basic runtime status",
                      {"status", "lastHeartbeat"})
            if type(response.status) is not int or response.status != 200 or response.payload["status"] != "ready":
                raise EnvironmentBlocked("认证状态读取未确认服务可用；不重试")
            heartbeat: datetime = utc_datetime(response.payload["lastHeartbeat"], "status heartbeat")
            now: datetime = datetime.now(timezone.utc)
            if ((now - heartbeat).total_seconds() * 1000 > self.target.limits.descriptor_age_ms
                    or (heartbeat - now).total_seconds() * 1000 > self.target.limits.clock_tolerance_ms
                    or heartbeat < utc_datetime(identity.evidence["descriptor_heartbeat_utc"], "before heartbeat")):
                raise EnvironmentBlocked("状态读取心跳过期、未来或倒退；不重试")
            capabilities: JsonValue = response.payload.get("capabilities")
            if "capabilities" in response.payload and (not isinstance(capabilities, list)
                    or any(not isinstance(item, str) or not item for item in capabilities)
                    or len(set(cast(list[str], capabilities))) != len(capabilities)):
                raise EnvironmentBlocked("基本状态能力字段不符合实际协议")
            current: VerifiedIdentity = verify_target(self.target, self.hooks, package=False, probe_cache=self.probe_cache)
            same_target_identity(identity, current)
            if utc_datetime(current.evidence["descriptor_heartbeat_utc"], "after heartbeat") < heartbeat:
                raise EnvironmentBlocked("状态读取的心跳未可靠写入同目标描述符")
            proof: JsonObject = {"endpoint": STATUS_PATH, "attempts": 1,
                                 "timeout_ms": self.target.limits.identity_timeout_ms,
                                 "pre_descriptor_age_ms": identity.evidence["descriptor_age_ms"],
                                 "pre_descriptor_fresh": identity.evidence["descriptor_fresh"],
                                 "post_descriptor_fresh": True, "identity_unchanged": True,
                                 "background_keepalive": False}
            return current, proof
        except (Exception, KeyboardInterrupt):
            raise EnvironmentBlocked("已确认目标的认证状态握手失败；未发业务脚本，不重试，原始回执/异常已排除") from None

    # 功能：静态身份通过后认证探活、复核描述符及运行能力，再建立正常连接；参数无，同命令内复用已核验静态摘要与限时探测。
    def connect(self) -> JsonObject:
        # 首次连接对全部成员流式核验并登记摘要；同一 Pipeline 后续连接复用该摘要与限时探测缓存。
        identity: VerifiedIdentity = verify_target_identity(self.target, self.hooks, self.static_cache, self.probe_cache)
        self.identity = identity
        self.guard = SecretGuard((identity.token,))
        try:
            self.transport = self.factory(identity.port, identity.token, self.target.limits)
            current: VerifiedIdentity
            handshake: JsonObject
            current, handshake = self._status_handshake(identity)
            self.identity = current
            catalog: HttpResponse = self.transport.request(CATALOG_PATH, None, self.target.limits.identity_timeout_ms)
            if catalog.status != 200:
                raise EnvironmentBlocked("命令目录请求失败")
            document: JsonObject = catalog.payload
            keys_only(document, {"commands", "count", "total", "offset", "limit", "server"}, "command catalog",
                      {"commands", "count", "total", "offset", "limit", "server"})
            entries: JsonValue = document["commands"]
            if not isinstance(entries, list) or len(entries) > 1000 or document["count"] != len(entries) or document["total"] != len(entries) or document["offset"] != 0 or document["limit"] != 1000:
                raise EnvironmentBlocked("命令目录有截断/重复/计数或边界错误")
            names: set[str] = set()
            for raw in entries:
                entry: JsonObject = object_value(raw, "command catalog entry")
                keys_only(entry, {"name", "description", "tags", "package"}, "command catalog entry", {"name"})
                name: str = text(entry["name"], "command name")
                if name in names:
                    raise EnvironmentBlocked("命令目录重复")
                names.add(name)
            server: JsonObject = object_value(document["server"], "catalog server")
            keys_only(server, {"version", "port", "startTime"}, "catalog server", {"port"})
            if server["port"] != self.target.port or not {"runtime_status", "eval", "eval_file"} <= names:
                raise EnvironmentBlocked("命令目录的端口或双求值能力不成立")
            status: HttpResponse = self.transport.request(EXEC_PATH, {
                "command": "runtime_status", "parameters": {}, "timeout": self.target.limits.max_timeout_ms,
                "verbose": True,
            }, self.target.limits.identity_timeout_ms)
            outer: JsonObject = status.payload
            keys_only(outer, EXEC_KEYS, "runtime_status outer", {"success", "command", "result"})
            if status.status != 200 or outer["success"] is not True or outer["command"] != "runtime_status" or outer.get("error") or outer.get("errorDetails"):
                raise EnvironmentBlocked("runtime_status 未确认运行身份")
            actual: JsonObject = object_value(outer["result"], "runtime_status result")
            keys_only(actual, STATUS_KEYS, "runtime_status result", {"BuildGuid", "UnityVersion", "Platform", "IsPlaying", "FrameCount"})
            if actual["BuildGuid"] != identity.build_guid or actual["UnityVersion"] != identity.unity_version or actual["Platform"] != identity.platform or actual["IsPlaying"] is not True:
                raise EnvironmentBlocked("runtime_status PascalCase 实际身份不匹配")
            integer(actual["FrameCount"], "runtime frame", 0)
            driver: JsonValue = actual.get("PipelineDriver")
            if driver is not None:
                details: JsonObject = object_value(driver, "PipelineDriver")
                keys_only(details, {"IsServerRunning", "ActualPort", "EnableInBuilds", "RequestTimeoutMs", "EnableAuditLogging", "AutoStart", "MaxWorkItemsPerFrame"}, "PipelineDriver")
                if details.get("IsServerRunning") is not True or details.get("ActualPort") != identity.port:
                    raise EnvironmentBlocked("PipelineDriver 实际端口/服务状态不匹配")
            evidence: JsonObject = {**current.evidence, "static_package": identity.evidence["static_package"],
                                    "heartbeat_handshake": handshake, "runtime_status": actual,
                                    "capabilities": sorted(names), "authenticated": True,
                                    "business_ready": "需要本例独立观测"}
            self.guard.check(evidence)
            return evidence
        except BaseException:
            self.close()
            raise

    # 功能：在脚本发送前再次重验正常身份；参数无，令牌变更绝不自动接管，探测仅在限时窗口内复用。
    def preflight(self) -> None:
        if self.identity is None or self.transport is None:
            raise EnvironmentBlocked("正常连接尚未建立")
        try:
            current: VerifiedIdentity = verify_target_identity(self.target, self.hooks, package=False,
                                                               probe_cache=self.probe_cache)
            same_target_identity(self.identity, current)
            if current.evidence["descriptor_fresh"] is not True:
                _proof: JsonObject
                current, _proof = self._status_handshake(current)
            self.identity = current
        except BaseException:
            self.close()
            raise

    # 功能：发送已冻结包装一次并走公共分类；参数 file_path 非空时使用 eval_file。
    def execute(self, wrapper: bytes, timeout_ms: int, file_path: Path | None = None) -> EvalReceipt:
        if self.transport is None:
            return EvalReceipt("unknown", "transport", None, "连接不存在；请求状态未知")
        command: str = "eval_file" if file_path is not None else "eval"
        parameters: JsonObject = {"timeout": timeout_ms}
        if file_path is None:
            parameters["code"] = wrapper.decode("utf-8")
        else:
            parameters["file"] = str(file_path.absolute())
        try:
            response: HttpResponse = self.transport.request(EXEC_PATH, {
                "command": command, "parameters": parameters, "timeout": timeout_ms, "verbose": True,
            }, timeout_ms)
            return classify_eval(response, command, self.target.limits, self.guard)
        except (Exception, KeyboardInterrupt):
            return EvalReceipt("unknown", "transport", None, "超时/断连/非法传输回执；可能仍在执行，未重试")

    # 功能：关闭仅本次正常连接；参数无，不启动、结束或重启 Player。
    def close(self) -> None:
        transport: Transport | None = self.transport
        self.transport = None
        self.identity = None
        if transport is not None:
            transport.close()
        self.guard = SecretGuard()
