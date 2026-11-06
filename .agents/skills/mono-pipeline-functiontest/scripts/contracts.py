"""创建日期：2026-10-26；作者：Cyou。
功能：宿主的严格 JSON、类型、预算、路径、敏感信息及独立比较契约。
参数：输入字节、显式配置及原预期绑定；仅依赖标准库，导入无外部副作用。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Union, cast

JsonValue = Union[None, bool, int, float, str, list["JsonValue"], dict[str, "JsonValue"]]
JsonObject = dict[str, JsonValue]

SCHEMA = "mono-pipeline-functiontest/1"
VERDICTS = frozenset({"passed", "failed", "blocked", "test_inconclusive"})
PERMISSIONS = frozenset({"attach", "script_execute", "business_action", "setup_action", "log_read", "screenshot"})
OPERATORS = frozenset({"eq", "ne", "gt", "ge", "lt", "le", "contains", "delta"})
REPARSE_POINT = 0x400
ZERO_HASH = "0" * 64
SECRET_KEYS = frozenset({"token", "evaltoken", "password", "passwd", "pwd", "bearer", "secret", "authorization", "credential", "credentials", "accesstoken", "apikey"})
TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{43}=(?![A-Za-z0-9+/=])")
CREDENTIAL_PATTERN = re.compile(r"(?i)(?:password|passwd|evaltoken|authorization|api[_-]?key|access[_-]?token)[\"']?\s*[:=]\s*[\"']?[^\s,;\"'}]{4,}")
FORBIDDEN_SCRIPT = re.compile(
    r"\b(?:Thread\s*\.\s*Sleep|Assembly\s*\.\s*(?:Load|LoadFrom|LoadFile)|"
    r"Process\s*\.\s*(?:Start|GetProcesses)|Environment\s*\.\s*Exit)\s*\("
)


class HostError(Exception):
    """可安全公开的宿主错误；调用方不得把原始传输异常作为 message 传入。"""


class InputError(HostError):
    """结构或参数错误，不代表产品反例。"""


class IntegrityError(HostError):
    """来源、日志、绑定或证据不完整，拒绝执行及正式报告。"""


class EnvironmentBlocked(HostError):
    """身份、权限或关键环境不具备；不会自动降级。"""


class FrozenSession(HostError):
    """存在可能已执行的未知结果，整轮禁止再次接触 Player。"""


@dataclass(frozen=True)
class Limits:
    """统一预算；字段均为整数，CLI 不允许超出本类声明的硬上限。"""

    input_bytes: int = 8 * 1024 * 1024
    source_bytes: int = 16 * 1024 * 1024
    script_bytes: int = 256 * 1024
    wrapper_bytes: int = 288 * 1024
    response_bytes: int = 4 * 1024 * 1024
    value_bytes: int = 1024 * 1024
    evidence_bytes: int = 16 * 1024 * 1024
    journal_bytes: int = 64 * 1024 * 1024
    json_depth: int = 48
    json_nodes: int = 100000
    package_entries: int = 16384
    package_file_bytes: int = 1024 * 1024 * 1024
    descriptor_bytes: int = 64 * 1024
    descriptor_age_ms: int = 15000
    identity_timeout_ms: int = 10000
    identity_cache_ms: int = 2000
    script_timeout_ms: int = 5000
    max_timeout_ms: int = 8000
    poll_budget_ms: int = 8000
    poll_interval_ms: int = 200
    poll_samples: int = 48
    gap_warning_ms: int = 2000
    overrun_warning_ms: int = 8000
    clock_tolerance_ms: int = 2000

    # 功能：从已知整数覆盖项构建预算；参数 raw 为可选 limits 对象。
    @classmethod
    def from_json(cls, raw: JsonValue) -> Limits:
        document: JsonObject = {} if raw is None else object_value(raw, "limits")
        defaults: Limits = cls()
        names: set[str] = {field.name for field in fields(cls)}
        keys_only(document, names, "limits")
        values: dict[str, int] = {}
        for field in fields(cls):
            cap: int = int(getattr(defaults, field.name))
            value: JsonValue = document.get(field.name, cap)
            if type(value) is not int or not 1 <= value <= cap:
                raise InputError("limits 字段必须为不超过硬上限的正整数")
            values[field.name] = value
        result: Limits = cls(**values)
        if result.script_timeout_ms > result.max_timeout_ms or result.poll_interval_ms > result.poll_budget_ms:
            raise InputError("limits 超时或轮询间隔关系非法")
        if result.identity_cache_ms > result.identity_timeout_ms:
            raise InputError("limits 同命令探测缓存窗口不得超过身份核验超时")
        if result.script_bytes >= result.wrapper_bytes or result.value_bytes > result.response_bytes:
            raise InputError("limits 源码、包装或输出预算关系非法")
        return result

    # 功能：输出可审计的集中配置；参数无。
    def to_json(self) -> JsonObject:
        return {field.name: int(getattr(self, field.name)) for field in fields(self)}


# 功能：计算原字节摘要；参数 content 为未经转码的字节。
def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# 功能：验证摘要字符串；参数 value 为外部值，label 仅使用固定位置名。
def hash_value(value: JsonValue, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise InputError(label + " 必须为小写 SHA256")
    return value


# 功能：验证 JSON 对象且不丢弃字段；参数 value 为已解析值。
def object_value(value: object, label: str) -> JsonObject:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise InputError(label + " 必须为对象")
    return cast(JsonObject, value)


# 功能：拒绝未知或缺失关键字段；参数 allowed/required 为固定字段集合。
def keys_only(value: JsonObject, allowed: set[str] | frozenset[str], label: str,
              required: set[str] | frozenset[str] = frozenset()) -> None:
    if not set(value) <= (set(allowed) | {"_comment"}) or not required <= set(value):
        raise InputError(label + " 存在未知或缺失关键字段")


# 功能：验证非空原文；参数 trim=False 时保留原文本全部空白。
def text(value: JsonValue, label: str, trim: bool = True) -> str:
    if not isinstance(value, str) or not value.strip() or (trim and value != value.strip()):
        raise InputError(label + " 必须为非空文本")
    if "\x00" in value:
        raise InputError(label + " 含非法字符")
    return value


# 功能：校验命令/观察等宿主 ID；参数 value 不用于猜测目标或编号。
def identifier(value: JsonValue, label: str) -> str:
    result: str = text(value, label)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", result) is None:
        raise InputError(label + " 必须为 1—96 字符的安全 ID")
    return result


# 功能：验证整数且排除 bool；参数下界/上界为显式闭区间。
def integer(value: JsonValue, label: str, minimum: int = 1, maximum: int = 2**31 - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise InputError(label + " 整数范围非法")
    return value


# 功能：递归核验有限 JSON 与深度/节点预算；参数 limits 为集中限制。
def validate_json(value: object, limits: Limits) -> JsonValue:
    stack: list[tuple[object, int]] = [(value, 0)]
    count: int = 0
    while stack:
        current, depth = stack.pop()
        count += 1
        if count > limits.json_nodes or depth > limits.json_depth:
            raise InputError("JSON 结构超过预算")
        if current is None or type(current) in (bool, int, str):
            continue
        if type(current) is float:
            if not math.isfinite(cast(float, current)):
                raise InputError("JSON 不接受非有限数字")
            continue
        if isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
            continue
        if isinstance(current, dict) and all(isinstance(key, str) for key in current):
            stack.extend((child, depth + 1) for child in current.values())
            continue
        raise InputError("值不是严格 JSON 类型")
    return cast(JsonValue, value)


# 功能：严格读取 JSON，拒重复键/NaN/Infinity/无界输入；参数 bom 仅供本地来源使用。
def strict_json(content: bytes, maximum: int, limits: Limits | None = None, bom: bool = False) -> JsonValue:
    budget: Limits = limits if limits is not None else Limits()
    if not content or len(content) > maximum:
        raise InputError("JSON 字节大小越界")

    # 功能：保留顺序并拒重复键；参数 pairs 来自 JSON 解码器。
    def unique_pairs(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
        result: JsonObject = {}
        for key, value in pairs:
            if key in result:
                raise InputError("JSON 含重复键")
            result[key] = value
        return result

    # 功能：拒非标准常量；参数 value 不回显到异常。
    def reject_constant(value: str) -> JsonValue:
        raise InputError("JSON 含非标准数字常量")

    try:
        decoded: str = content.decode("utf-8-sig" if bom else "utf-8", errors="strict")
        parsed: object = json.loads(decoded, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
        return validate_json(parsed, budget)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InputError("输入不是有界的严格 UTF-8 JSON") from None


# 功能：确定性序列化，拒非有限数字；参数 value 必须为已核验 JSON。
def canonical(value: JsonValue) -> bytes:
    validate_json(value, Limits())
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


# 功能：验证本地路径全链无链接/重解析点；参数 missing_leaf 仅供新目录使用。
def reject_links(path: Path, missing_leaf: bool = False) -> None:
    absolute: Path = path.absolute()
    if str(absolute).startswith(("\\\\", "//")):
        raise InputError("仅接受本机路径，不接受 UNC 或设备路径")
    current: Path = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            information: os.stat_result = current.lstat()
        except FileNotFoundError:
            if missing_leaf:
                continue
            raise InputError("本地路径不存在") from None
        except OSError:
            raise InputError("本地路径不可访问") from None
        if stat.S_ISLNK(information.st_mode) or getattr(information, "st_file_attributes", 0) & REPARSE_POINT:
            raise InputError("拒绝符号链接或重解析点")


# 功能：按明确基目录解析路径；参数 path 不允许隐藏上溯。
def local_path(path: str, base: Path, missing_leaf: bool = False) -> Path:
    if not path or "\x00" in path or ".." in Path(path).parts:
        raise InputError("本地路径非法")
    candidate: Path = Path(path)
    if not candidate.is_absolute():
        candidate = base / candidate
    reject_links(candidate, missing_leaf)
    return candidate.absolute()


# 功能：有界读取普通文件并检查读取期间身份/长度；参数 path 不跟随链接，maximum 仅作上限校验。
# 注意：读缓冲按已校验的实际大小 +1 申请，不按 maximum 预分配（2026-11-03 修复 1GiB 预分配触发 MemoryError）。
def read_regular(path: Path, maximum: int) -> bytes:
    reject_links(path)
    before: os.stat_result = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size < 1 or before.st_size > maximum:
        raise InputError("普通文件字节大小越界")
    try:
        with path.open("rb") as stream:
            content: bytes = stream.read(before.st_size + 1)
            held: os.stat_result = os.fstat(stream.fileno())
        after: os.stat_result = path.stat()
    except OSError:
        raise InputError("普通文件读取失败") from None
    identities: set[tuple[int, int, int, int]] = {
        (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns) for item in (before, held, after)
    }
    if len(identities) != 1 or len(content) != before.st_size:
        raise IntegrityError("文件在读取期间被修改或替换")
    return content


# 功能：按严格 JSON Pointer 提取字段；参数 pointer 不允许缺字段变默认值。
def field_value(value: JsonValue, pointer: str) -> JsonValue:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise InputError("字段必须为 JSON Pointer")
    current: JsonValue = value
    for token in pointer[1:].split("/"):
        if re.search(r"~(?:[^01]|$)", token) is not None:
            raise InputError("JSON Pointer 转义非法")
        key: str = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if key not in current:
                raise InputError("实际观测缺少目标字段")
            current = current[key]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", key) is not None:
            index: int = int(key)
            if index >= len(current):
                raise InputError("实际观测数组索引越界")
            current = current[index]
        else:
            raise InputError("实际观测字段类型不符")
    return current


# 功能：校验有限业务标量，null 不作为缺目标的正常结果；参数 value 为实际或独立预期。
def scalar(value: JsonValue) -> bool | int | float | str:
    if type(value) not in (bool, int, float, str):
        raise InputError("比较需要非空、有限、严格类型的业务标量")
    if type(value) is float and not math.isfinite(cast(float, value)):
        raise InputError("比较不接受非有限数字")
    return cast(bool | int | float | str, value)


# 功能：独立比较业务值；参数 actual/expected 均不是动作成功标记。
def compare_values(operator: str, actual: JsonValue, expected: JsonValue,
                   before: JsonValue = None, text_contains: bool = False) -> tuple[bool, JsonValue]:
    left: bool | int | float | str = scalar(actual)
    right: bool | int | float | str = scalar(expected)
    if operator == "delta":
        previous: bool | int | float | str = scalar(before)
        if type(left) not in (int, float) or type(previous) is not type(left) or type(right) is not type(left):
            raise InputError("delta 需要同类型的 before/after/独立预期数值")
        delta: JsonValue = cast(int | float, left) - cast(int | float, previous)
        if isinstance(delta, float) and not math.isfinite(delta):
            raise InputError("delta 运算溢出，不能比较或保存为默认数值")
        return delta == right, delta
    if operator in {"eq", "ne"}:
        if type(left) is not type(right):
            raise InputError("eq/ne 类型不符，禁止隐式转换")
        return (left == right if operator == "eq" else left != right), actual
    if operator in {"gt", "ge", "lt", "le"}:
        if type(left) not in (int, float) or type(right) is not type(left):
            raise InputError("数值大小比较需要同类型数值，不接受 bool、文本或隐式转换")
        numeric_left: int | float = cast(int | float, left)
        numeric_right: int | float = cast(int | float, right)
        matches: dict[str, bool] = {"gt": numeric_left > numeric_right, "ge": numeric_left >= numeric_right,
                                    "lt": numeric_left < numeric_right, "le": numeric_left <= numeric_right}
        return matches[operator], actual
    if operator == "contains":
        if not text_contains or not isinstance(left, str) or not isinstance(right, str):
            raise InputError("contains 仅限已审核的原文本包含预期")
        return right in left, actual
    raise InputError("未知比较规则")


class SecretGuard:
    """保守拒收凭据；已知描述符令牌只保存在内存，不序列化此对象。"""

    # 功能：保存内存中已知敏感值；参数 secrets 由身份核验返回，不写磁盘。
    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        self._secrets: tuple[str, ...] = tuple(item for item in secrets if item)

    # 功能：检出保守的凭据文本；参数 content 可为脚本或证据原字节。
    def check_bytes(self, content: bytes) -> None:
        decoded: str = content.decode("utf-8", errors="replace")
        if any(item in decoded for item in self._secrets) or TOKEN_PATTERN.search(decoded) or CREDENTIAL_PATTERN.search(decoded):
            raise IntegrityError("敏感内容被拒收；未保存原文")

    # 功能：递归拒绝敏感结果字段和文本；参数 value 为待记录 JSON。
    def check(self, value: JsonValue) -> None:
        self.check_bytes(canonical(value))
        stack: list[JsonValue] = [value]
        while stack:
            current: JsonValue = stack.pop()
            if isinstance(current, dict):
                for key, child in current.items():
                    normalized: str = re.sub(r"[^a-z0-9]", "", key.lower())
                    if normalized in SECRET_KEYS:
                        raise IntegrityError("敏感结果字段被拒收；未保存原文")
                    stack.append(child)
            elif isinstance(current, list):
                stack.extend(current)

    # 功能：输出不泄密的编译/运行诊断；参数 value 为外部文本，不回显凭据。
    def diagnostic(self, value: JsonValue) -> str:
        if not isinstance(value, str):
            return "未提供文本诊断"
        result: str = value
        for secret in self._secrets:
            result = result.replace(secret, "[敏感内容已排除]")
        result = TOKEN_PATTERN.sub("[敏感内容已排除]", result)
        result = CREDENTIAL_PATTERN.sub("[敏感内容已排除]", result)
        return result[:4096]


# 功能：校验方法体片段及最低限度禁止项；参数 raw 为用户原字节。
def script_text(raw: bytes, limits: Limits, guard: SecretGuard) -> str:
    if not raw or len(raw) > limits.script_bytes:
        raise InputError("用户脚本大小越界")
    guard.check_bytes(raw)
    try:
        result: str = raw.decode("utf-8-sig", errors="strict")
    except UnicodeError:
        raise InputError("用户脚本必须为 UTF-8 方法体片段") from None
    if not result.strip() or FORBIDDEN_SCRIPT.search(result):
        raise InputError("脚本为空或包含明确禁止的阻塞/加载/进程操作")
    return result
