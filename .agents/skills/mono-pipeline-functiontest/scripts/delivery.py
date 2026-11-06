"""创建日期：2026-10-26；作者：Cyou。
功能：第8公共模块；同包完整性/ZIP/原子导出、显式 Unity 文件接入、成功构建库存和单目标公开配置准备。
参数：本 Skill 根、明确本地目标/新输出、批准摘要/额外批准/外部新备份及显式许可记录。
边界：仅标准库和包内模块；不安装/下载/构建/启动/连接 Player，不自动刷新失败清单。
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import stat
import tempfile
import time
import uuid
import zipfile
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast

from .contracts import (
    EnvironmentBlocked, InputError, IntegrityError, JsonObject, JsonValue, Limits, PERMISSIONS,
    SecretGuard, canonical, digest, hash_value, integer, keys_only, local_path, object_value,
    read_regular, reject_links, strict_json, text,
)
from .inputs import INTEGRITY_MODES, TargetConfig, parse_target
from .pipeline import DESCRIPTOR_KEYS, DESCRIPTOR_NAME, IdentityHooks, verify_package, verify_target_identity

NAME = "mono-pipeline-functiontest"
VERSION = "1.0.0"
MANIFEST = "delivery-manifest.json"
CATALOG = "assets/dependencies/catalog.json"
INTERNAL_LICENSE = "references/internal-license.md"
UNITY_ROOT = "Assets/MonoPipelineFunctionTest"
INTEGRATION_RECEIPT = ".mono-pipeline-functiontest-integration.json"
PACKAGE_MANIFEST = "package-manifest.json"
MAX_MEMBERS = 32768
MAX_TARGET_MEMBERS = 131072
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_UPM_BYTES = 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
MAX_ZIP_RATIO = 1000
DIRECTORY_PUBLISH_TIMEOUT_MS = 5000
DIRECTORY_PUBLISH_INTERVAL_MS = 100
DIRECTORY_PUBLISH_WINDOWS_ERRORS = frozenset({5, 32, 33})
WINDOWS_MAX_FILE_UNITS = 259
WINDOWS_MAX_DIRECTORY_UNITS = 247
TEMPORARY_FILE_PREFIX = ".mono-pipeline-"
TEMPORARY_FILE_SUFFIX = ".tmp"
TEMPORARY_FILE_ID_LENGTH = 32
PUBLIC_MODULES = frozenset({"contracts", "inputs", "pipeline", "session", "evidence", "report", "cli", "delivery"})
ADAPTATION_CATALOG = "assets/adapters/catalog.json"
PACKAGE_NAMES = frozenset({"com.unity.pipeline", "com.unity.nuget.mono-cecil", "com.unity.ugui",
                           "com.unity.inputsystem", "com.unity.nuget.newtonsoft-json", "com.unity.test-framework", "com.unity.ext.nunit"})
WINDOWS_RESERVED = frozenset({"con", "prn", "aux", "nul"} | {f"com{index}" for index in range(1, 10)} | {f"lpt{index}" for index in range(1, 10)})
ESSENTIALS = frozenset({"SKILL.md", "mono-pipeline-test.bat", "scripts/__init__.py", "scripts/tests/run_tests.py",
                        "scripts/tests/test_compatibility.py", CATALOG, INTERNAL_LICENSE,
                        "references/host-contract.md", "references/bridge-contract.md", "references/delivery-contract.md",
                        "assets/unity.meta", "assets/unity/GlobalMonoPipelineTest.cs", "assets/unity/MonoPipelineReflection.cs",
                        "assets/unity/MonoPipelineEvidence.cs", "assets/unity/Editor/MonoPipelineBuildSupport.cs",
                        "assets/unity/GlobalMonoPipelineTest.cs.meta", "assets/unity/MonoPipelineReflection.cs.meta",
                        "assets/unity/MonoPipelineEvidence.cs.meta", "assets/unity/Editor.meta", "assets/unity/Editor/MonoPipelineBuildSupport.cs.meta"}
                       | {"assets/templates/" + name for name in {"action.json", "case-suite.json", "cases.json", "compare.json", "observe.json", "package-manifest.json",
                                                                 "provenance.json", "read-basic.cs", "target.json", "package-approval.json", "target-permission.json", "bridge-evidence-context.json"}}
                       | {"scripts/" + name + ".py" for name in PUBLIC_MODULES})


# 功能：从当前模块定位同包根；参数无，不读取维护工程或环境配置。
def skill_root() -> Path:
    root: Path = Path(__file__).absolute().parent.parent
    reject_links(root)
    return root


# 功能：严格 root 相对路径；参数拒绝 Windows/ZIP 绝对路径、上溯、非规范名、保留设备名和大小写歧义基础。
def relative_name(value: JsonValue) -> str:
    name: str = text(value, "relative path")
    parts: list[str] = name.split("/")
    if PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive or "\\" in name:
        raise InputError("交付/ZIP 路径必须为规范 root 相对路径")
    if any(part in {"", ".", ".."} or part != part.rstrip(" .") or ":" in part
           or any(ord(character) < 32 for character in part) or part.split(".", 1)[0].casefold() in WINDOWS_RESERVED for part in parts):
        raise InputError("交付/ZIP 路径含上溯、设备名或非规范成员")
    return name


# 功能：登记目录和文件名并拒重复/大小写或文件祖先冲突；参数 seen 为整次扫描共享集合。
def register_name(name: str, seen: dict[str, str]) -> None:
    normalized: str = relative_name(name)
    folded: str = normalized.casefold()
    if folded in seen and seen[folded] != normalized:
        raise IntegrityError("路径存在大小写冲突")
    seen[folded] = normalized
    parts: list[str] = normalized.split("/")
    for index in range(1, len(parts)):
        parent: str = "/".join(parts[:index])
        key: str = parent.casefold()
        if key in seen and seen[key] != parent:
            raise IntegrityError("路径祖先存在大小写冲突")
        seen[key] = parent


# 功能：全链无链接的有界目录清点；参数 maximum 同时限制目录和文件，不跟随重解析点。
def walk_files(root: Path, maximum: int = MAX_MEMBERS) -> tuple[dict[str, Path], set[str]]:
    reject_links(root)
    if not root.is_dir():
        raise InputError("明确目录不存在")
    result: dict[str, Path] = {}
    directories: set[str] = set()
    seen: dict[str, str] = {}
    count: int = 0
    for directory, dirs, names in os.walk(root, followlinks=False):
        for member in sorted(dirs + names):
            count += 1
            if count > maximum:
                raise IntegrityError("目录清点超过成员预算")
            path: Path = Path(directory) / member
            reject_links(path)
            relative: str = path.relative_to(root).as_posix()
            register_name(relative, seen)
            mode: int = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                directories.add(relative)
            elif stat.S_ISREG(mode):
                result[relative] = path
            else:
                raise IntegrityError("拒绝非普通文件或目录")
    return result, directories


# 功能：有界流式 SHA/字节/身份核验，允许合法空源码；参数 maximum 为明确硬上限。
def file_record(path: Path, maximum: int = MAX_FILE_BYTES) -> JsonObject:
    reject_links(path)
    before: os.stat_result = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size < 0 or before.st_size > maximum:
        raise IntegrityError("成员类型或字节预算非法")
    checksum: object = hashlib.sha256()
    size: int = 0
    with path.open("rb") as stream:
        while True:
            chunk: bytes = stream.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            if size > maximum:
                raise IntegrityError("成员读取超过字节预算")
            checksum.update(chunk)  # type: ignore[attr-defined]
        held: os.stat_result = os.fstat(stream.fileno())
    after: os.stat_result = path.stat()
    if len({(item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns) for item in (before, held, after)}) != 1 or size != before.st_size:
        raise IntegrityError("成员在核验期间被修改或替换")
    return {"bytes": size, "sha256": checksum.hexdigest()}  # type: ignore[attr-defined]


# 功能：读取严格有界 JSON 控制文件；参数最大值不从外部提升，返回原字节及完整对象。
def json_file(path: Path, maximum: int = MAX_MANIFEST_BYTES) -> tuple[bytes, JsonObject]:
    raw: bytes = read_regular(path, maximum)
    result: JsonObject = object_value(strict_json(raw, maximum, bom=True), "offline control")
    SecretGuard().check(result)
    return raw, result


# 功能：核验带成员 SHA 的严格清单；参数目录和 ZIP 共用同一规范，大小写重复不能静默合并。
def entries(raw: JsonValue, maximum: int = MAX_MEMBERS, file_maximum: int = MAX_TOTAL_BYTES) -> dict[str, JsonObject]:
    if not isinstance(raw, list) or not raw or len(raw) > maximum:
        raise InputError("清单成员数组为空或超过预算")
    result: dict[str, JsonObject] = {}
    seen: dict[str, str] = {}
    folded_files: set[str] = set()
    for value in raw:
        entry: JsonObject = object_value(value, "manifest member")
        keys_only(entry, {"path", "bytes", "sha256", "version", "license", "kind"}, "manifest member", {"path", "bytes", "sha256"})
        name: str = relative_name(entry["path"])
        if name.casefold() in folded_files:
            raise IntegrityError("清单成员重复或大小写冲突")
        folded_files.add(name.casefold())
        register_name(name, seen)
        integer(entry["bytes"], "member.bytes", 0, file_maximum)
        hash_value(entry["sha256"], "member.sha256")
        result[name] = entry
    if any("/".join(name.split("/")[:index]).casefold() in folded_files for name in result for index in range(1, len(name.split("/")))):
        raise IntegrityError("清单文件不能同时作为其他文件祖先")
    return result


# 功能：安全解析 ZIP 实际成员并核验 CRC/摘要；参数 expected 不存在时仍拒穿越、链接、重复和压缩炸弹。
def zip_members(raw: bytes, expected: dict[str, JsonObject] | None = None) -> dict[str, bytes]:
    if not raw or len(raw) > MAX_ARCHIVE_BYTES:
        raise IntegrityError("ZIP 原字节预算非法")
    result: dict[str, bytes] = {}
    seen: dict[str, str] = {}
    folded: set[str] = set()
    total: int = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members: list[zipfile.ZipInfo] = archive.infolist()
            if not members or len(members) > MAX_MEMBERS:
                raise IntegrityError("ZIP 成员数预算非法")
            for member in members:
                # Windows ZipInfo 会先把反斜杠/零字节规范化；必须核验未规范化的原中心目录名称。
                name: str = relative_name(member.orig_filename)
                if name != member.filename:
                    raise IntegrityError("ZIP 原成员名称被运行库规范化，拒绝隐含别名")
                mode: int = member.external_attr >> 16
                if member.is_dir() or stat.S_IFMT(mode) not in {0, stat.S_IFREG} or member.flag_bits & 1:
                    raise IntegrityError("ZIP 不接受目录记录、链接、特殊成员或加密文件")
                if member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED} or member.file_size > MAX_FILE_BYTES:
                    raise IntegrityError("ZIP 压缩方法或成员字节预算非法")
                if member.file_size > max(1, member.compress_size) * MAX_ZIP_RATIO or name.casefold() in folded:
                    raise IntegrityError("ZIP 重复路径或压缩比例超出预算")
                folded.add(name.casefold())
                register_name(name, seen)
                total += member.file_size
                if total > MAX_EXPANDED_BYTES or (expected is not None and name not in expected):
                    raise IntegrityError("ZIP 展开预算超限或存在未登记成员")
                with archive.open(member, "r") as stream:
                    content: bytes = stream.read(member.file_size + 1)
                if len(content) != member.file_size:
                    raise IntegrityError("ZIP 成员实际长度不符")
                if expected is not None and (len(content) != expected[name]["bytes"] or digest(content) != expected[name]["sha256"]):
                    raise IntegrityError("ZIP 成员摘要或大小不匹配")
                result[name] = content
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, OSError):
        raise IntegrityError("ZIP 不是可核验的完整本地归档") from None
    if expected is not None and set(result) != set(expected):
        raise IntegrityError("ZIP 缺失登记成员")
    if any("/".join(name.split("/")[:index]).casefold() in folded for name in result for index in range(1, len(name.split("/")))):
        raise IntegrityError("ZIP 文件/目录祖先冲突")
    return result


# 功能：解析同包依赖并实际核验全部原归档/许可/包元数据；参数不查询维护项目或 Registry。
def dependency_catalog(root: Path) -> tuple[JsonObject, dict[str, dict[str, bytes]]]:
    _, catalog = json_file(root / CATALOG)
    keys_only(catalog, {"schema", "reference_unity", "unity_series", "packages", "engine_modules", "source_inventory_sha256",
                        "source_authority_sha256", "authority_scope", "excluded_project_adaptations", "license_notice"}, "dependency catalog",
              {"schema", "reference_unity", "unity_series", "packages", "engine_modules", "source_inventory_sha256", "source_authority_sha256", "authority_scope", "license_notice"})
    if catalog["schema"] != "mono-pipeline-dependencies/1" or catalog["license_notice"] != INTERNAL_LICENSE:
        raise IntegrityError("依赖清单版本或许可索引不匹配")
    hash_value(catalog["source_inventory_sha256"], "origin inventory")
    hash_value(catalog["source_authority_sha256"], "origin authority")
    if catalog["authority_scope"] != "company-internal-migration-only; preserve-original-licenses; no-public-redistribution-grant":
        raise IntegrityError("依赖内部授权范围不匹配")
    packages: JsonValue = catalog["packages"]
    if not isinstance(packages, list):
        raise InputError("依赖包列表非法")
    expanded: dict[str, dict[str, bytes]] = {}
    total: int = 0
    for value in packages:
        package: JsonObject = object_value(value, "dependency package")
        fields: set[str] = {"name", "version", "target_root", "archive", "license_files", "readable_license_files", "redistribution", "origin", "files"}
        keys_only(package, fields, "dependency package", fields)
        name: str = text(package["name"], "dependency name")
        if name in expanded or name not in PACKAGE_NAMES or package["target_root"] != "Packages/" + name:
            raise IntegrityError("依赖重复、未知名称或目标布局冲突")
        if package["redistribution"] != "authorized-internal-preserve-original-license" or package["origin"] != "authorized-local-archive-2026-10-23":
            raise IntegrityError("依赖来源或再分发范围未知")
        text(package["version"], "dependency version")
        archive: JsonObject = object_value(package["archive"], "dependency archive")
        keys_only(archive, {"path", "bytes", "sha256"}, "dependency archive", {"path", "bytes", "sha256"})
        archive_name: str = relative_name(archive["path"])
        if not archive_name.startswith("assets/dependencies/") or not archive_name.endswith(".zip"):
            raise IntegrityError("依赖归档必须在同包明确目录")
        content: bytes = read_regular(root / archive_name, MAX_ARCHIVE_BYTES)
        if len(content) != archive["bytes"] or digest(content) != hash_value(archive["sha256"], "archive.sha256"):
            raise IntegrityError("依赖原归档摘要或大小不匹配")
        payload: dict[str, bytes] = zip_members(content, entries(package["files"]))
        total += sum(len(item) for item in payload.values())
        if total > MAX_EXPANDED_BYTES:
            raise IntegrityError("依赖总展开预算超限")
        metadata: JsonObject = object_value(strict_json(payload.get("package.json", b""), MAX_UPM_BYTES, bom=True), "UPM package metadata")
        if metadata.get("name") != name or metadata.get("version") != package["version"]:
            raise IntegrityError("依赖包元数据与锁定版本不匹配")
        license_names: JsonValue = package["license_files"]
        readable: JsonValue = package["readable_license_files"]
        if not isinstance(license_names, list) or not license_names or not isinstance(readable, list) or len(readable) != len(license_names):
            raise IntegrityError("依赖原许可/可读许可不完整")
        for license_name, readable_name in zip(license_names, readable):
            member_name: str = relative_name(license_name)
            copy_name: str = relative_name(readable_name)
            if member_name not in payload or not copy_name.startswith("assets/dependencies/licenses/" + name + "/"):
                raise IntegrityError("依赖许可位置未知")
            if read_regular(root / copy_name, MAX_FILE_BYTES) != payload[member_name]:
                raise IntegrityError("可读原许可与归档不一致")
        expanded[name] = payload
    if set(expanded) != PACKAGE_NAMES:
        raise IntegrityError("公共依赖闭包不完整")
    modules: JsonObject = object_value(catalog["engine_modules"], "engine modules")
    if any(not key.startswith("com.unity.modules.") or value != "1.0.0" for key, value in modules.items()):
        raise InputError("引擎模块前置不是明确版本")
    return catalog, expanded


# 功能：限制交付源码布局，排除会话/描述符/机器配置/备份及旧后端；参数只接受本 Skill 必需源码类型。
def payload_kind(name: str, adaptation_paths: frozenset[str] = frozenset()) -> str:
    relative_name(name)
    parts: list[str] = name.split("/")
    if any(part.casefold() in {"__pycache__", "output", "outputs", "sessions", "backup", "backups", ".svn", ".git"} for part in parts):
        raise IntegrityError("运行输出、缓存或备份不能进入交付")
    if name in {"SKILL.md", "mono-pipeline-test.bat"}:
        return "entry"
    if parts[0] == "scripts" and name.endswith(".py"):
        if len(parts) == 2 and parts[1] in {"__init__.py"} | {item + ".py" for item in PUBLIC_MODULES}:
            return "python"
        if len(parts) == 3 and parts[1] == "tests":
            return "isolated_test"
    if len(parts) == 2 and parts[0] == "references" and name.endswith(".md") and parts[1] not in {"README.md", "CHANGELOG.md"}:
        return "reference"
    if len(parts) == 3 and parts[:2] == ["assets", "templates"] and Path(name).suffix in {".json", ".cs"}:
        return "template"
    if name == "assets/unity.meta" or (parts[:2] == ["assets", "unity"] and Path(name).suffix in {".cs", ".meta"}):
        return "unity"
    if name == ADAPTATION_CATALOG:
        return "project_adaptation_catalog"
    if name in adaptation_paths:
        return "project_adaptation"
    if name == CATALOG:
        return "dependency_catalog"
    if len(parts) == 3 and parts[:2] == ["assets", "dependencies"] and name.endswith(".zip"):
        return "dependency_archive"
    if len(parts) >= 5 and parts[:3] == ["assets", "dependencies", "licenses"]:
        return "original_license"
    raise IntegrityError("存在未授权交付布局或额外运行文件")


# 功能：读取同包明确登记的可选适配路径，不内置项目名/接口；参数根可无登记，未知布局/重复/输出仍拒绝。
def adaptation_files(root: Path) -> frozenset[str]:
    path: Path = root / ADAPTATION_CATALOG
    reject_links(path, missing_leaf=True)
    if not path.exists():
        return frozenset()
    _, document = json_file(path, MAX_UPM_BYTES)
    keys_only(document, {"schema", "files"}, "adaptation catalog", {"schema", "files"})
    if document["schema"] != "mono-pipeline-adaptation-catalog/1":
        raise IntegrityError("可选适配索引格式不匹配")
    files: JsonValue = document["files"]
    if not isinstance(files, list) or not files or len(files) > MAX_MEMBERS:
        raise IntegrityError("可选适配索引为空或超过预算")
    result: set[str] = set()
    folded: set[str] = set()
    for value in files:
        name: str = relative_name(value)
        parts: list[str] = name.split("/")
        if (len(parts) != 4 or parts[:2] != ["assets", "adapters"]
            or Path(name).suffix not in {".md", ".cs", ".meta", ".patch"}
            or any(part.casefold() in {"output", "outputs", "sessions", "backup", "backups", "__pycache__"} for part in parts)
            or name.casefold() in folded):
            raise IntegrityError("可选适配索引含未知布局或重复路径")
        result.add(name)
        folded.add(name.casefold())
    return frozenset(result)


# 功能：显式维护者生成/刷新清单；参数 approved 必须 true，已有清单还需原 SHA，不因校验失败自动刷新。
def refresh_manifest(root: Path, approved: bool, previous_sha256: str | None = None) -> JsonObject:
    if not approved:
        raise InputError("生成/刷新清单需要维护者明确离线批准")
    files, directories = walk_files(root)
    old: bytes | None = read_regular(root / MANIFEST, MAX_MANIFEST_BYTES) if MANIFEST in files else None
    if old is not None and (previous_sha256 is None or digest(old) != hash_value(previous_sha256, "previous manifest")):
        raise IntegrityError("刷新必须提供当前既有清单的精确 SHA256")
    if old is None and previous_sha256 is not None:
        raise IntegrityError("不存在可匹配的既有清单")
    files.pop(MANIFEST, None)
    if not ESSENTIALS <= set(files):
        raise IntegrityError("交付必需源码/参考/负载不完整")
    catalog, _ = dependency_catalog(root)
    package_roles: dict[str, tuple[str, str]] = {}
    for value in cast(list[JsonValue], catalog["packages"]):
        package: JsonObject = object_value(value, "package")
        archive: JsonObject = object_value(package["archive"], "archive")
        license_path: str = str(cast(list[JsonValue], package["readable_license_files"])[0])
        package_roles[str(archive["path"])] = (str(package["version"]), license_path)
        for path in cast(list[JsonValue], package["readable_license_files"]):
            package_roles[str(path)] = (str(package["version"]), license_path)
    records: list[JsonValue] = []
    total: int = 0
    adaptations: frozenset[str] = adaptation_files(root)
    if not adaptations <= set(files):
        raise IntegrityError("可选适配索引成员缺失")
    for name, path in sorted(files.items()):
        kind: str = payload_kind(name, adaptations)
        record: JsonObject = file_record(path)
        total += cast(int, record["bytes"])
        if total > MAX_TOTAL_BYTES:
            raise IntegrityError("交付总字节预算超限")
        version, license_path = package_roles.get(name, (VERSION, INTERNAL_LICENSE))
        records.append({"path": name, **record, "version": version, "license": license_path, "kind": kind})
    expected_dirs: set[str] = {"/".join(name.split("/")[:index]) for name in files for index in range(1, len(name.split("/")))}
    if directories != expected_dirs:
        raise IntegrityError("交付包含未登记空目录")
    manifest: JsonObject = {"_comment": "创建日期：2026-10-26；作者：Cyou；功能：整目录原字节完整性清单；参数：root 相对成员、SHA256、字节、版本/许可；自身不循环散列，刷新为维护者明确离线动作。",
                            "schema": "mono-pipeline-delivery/1", "name": NAME, "version": VERSION, "python_minimum": "3.10",
                            "dependencies": CATALOG, "license": INTERNAL_LICENSE, "files": records}
    content: bytes = canonical(manifest) + b"\n"
    if len(content) > MAX_MANIFEST_BYTES:
        raise IntegrityError("交付清单字节预算超限")
    if old is None:
        write_new(root / MANIFEST, content)
    else:
        replace_known(root / MANIFEST, digest(old), content)
    return {"manifest_sha256": digest(content), "file_count": len(records), "bytes": total, "refreshed_explicitly": True}


# 功能：严格核验完整同包内容及必要依赖；参数没有修复/刷新旁路，也不接受可被同权限主体伪造的落盘缓存。
def verify_delivery(root: Path) -> JsonObject:
    raw, manifest = json_file(root / MANIFEST)
    fields: set[str] = {"schema", "name", "version", "python_minimum", "dependencies", "license", "files"}
    keys_only(manifest, fields, "delivery manifest", fields)
    if any(manifest[key] != value for key, value in {"schema": "mono-pipeline-delivery/1", "name": NAME, "version": VERSION,
                                                    "python_minimum": "3.10", "dependencies": CATALOG, "license": INTERNAL_LICENSE}.items()):
        raise IntegrityError("交付名称、版本、Python 基线或根索引不匹配")
    declared: dict[str, JsonObject] = entries(manifest["files"])
    actual, directories = walk_files(root)
    actual.pop(MANIFEST, None)
    if set(actual) != set(declared) or not ESSENTIALS <= set(declared) or MANIFEST in declared:
        raise IntegrityError("交付有额外、缺失或自循环清单成员")
    expected_dirs: set[str] = {"/".join(name.split("/")[:index]) for name in declared for index in range(1, len(name.split("/")))}
    if directories != expected_dirs:
        raise IntegrityError("交付有额外或缺失目录")
    total: int = 0
    adaptations: frozenset[str] = adaptation_files(root)
    if not adaptations <= set(declared):
        raise IntegrityError("可选适配索引成员未登记完整清单")
    for name, entry in declared.items():
        kind: str = payload_kind(name, adaptations)
        keys_only(entry, {"path", "bytes", "sha256", "version", "license", "kind"}, "delivery member",
                  {"path", "bytes", "sha256", "version", "license", "kind"})
        license_path: str = relative_name(entry["license"])
        if license_path not in declared or not isinstance(entry["version"], str) or entry["kind"] != kind:
            raise IntegrityError("交付成员版本/许可/类型缺失或冲突")
        record: JsonObject = file_record(actual[name], MAX_ARCHIVE_BYTES if kind == "dependency_archive" else MAX_FILE_BYTES)
        if record["sha256"] != entry["sha256"] or record["bytes"] != entry["bytes"]:
            raise IntegrityError("交付成员实际摘要或字节不匹配")
        total += cast(int, record["bytes"])
    if total > MAX_TOTAL_BYTES:
        raise IntegrityError("交付总字节预算超限")
    catalog, expanded = dependency_catalog(root)
    expected_metadata: dict[str, tuple[str, str]] = {}
    for value in cast(list[JsonValue], catalog["packages"]):
        package: JsonObject = object_value(value, "package")
        archive: JsonObject = object_value(package["archive"], "archive")
        license_path = str(cast(list[JsonValue], package["readable_license_files"])[0])
        for name in [str(archive["path"]), *[str(item) for item in cast(list[JsonValue], package["readable_license_files"])]]:
            expected_metadata[name] = (str(package["version"]), license_path)
    for name, entry in declared.items():
        version, license_path = expected_metadata.get(name, (VERSION, INTERNAL_LICENSE))
        if entry["version"] != version or entry["license"] != license_path:
            raise IntegrityError("成员版本/原许可位置与固定同包来源不一致")
    return {"name": NAME, "version": VERSION, "manifest_sha256": digest(raw), "file_count": len(declared), "bytes": total,
            "dependency_archives": len(expanded), "dependency_members": sum(len(value) for value in expanded.values()),
            "dependency_expanded_bytes": sum(len(content) for value in expanded.values() for content in value.values()),
            "reference_unity": catalog["reference_unity"], "unity_compiled_or_player_verified": False}


# 功能：创建普通新文件并 fsync；参数路径全链无链接，既有文件不覆盖。
def write_new(path: Path, content: bytes) -> None:
    reject_links(path, missing_leaf=True)
    if not path.parent.is_dir():
        raise InputError("新输出父目录必须已存在")
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


# 功能：执行前核对 Windows 兼容路径预算；参数 path 为明确落点，temporary_file 另核对同父原子临时名。
# 使用 UTF-16 单位计算，不读取或修改系统长路径设置；超限明确阻塞，不尝试部分复制。
def require_windows_path_budget(path: Path, temporary_file: bool = False) -> None:
    if os.name != "nt":
        return
    absolute: Path = path.absolute()
    file_units: int = len(str(absolute).encode("utf-16-le")) // 2
    parent_units: int = len(str(absolute.parent).encode("utf-16-le")) // 2
    if file_units > WINDOWS_MAX_FILE_UNITS or parent_units > WINDOWS_MAX_DIRECTORY_UNITS:
        raise EnvironmentBlocked("Windows 兼容路径超限（UTF-16 单位）：文件 " + str(file_units)
                                 + "/" + str(WINDOWS_MAX_FILE_UNITS) + "，父目录 " + str(parent_units)
                                 + "/" + str(WINDOWS_MAX_DIRECTORY_UNITS) + "；需要更短的明确工程/备份落点")
    if temporary_file:
        candidate: Path = absolute.with_name(TEMPORARY_FILE_PREFIX + "0" * TEMPORARY_FILE_ID_LENGTH + TEMPORARY_FILE_SUFFIX)
        require_windows_path_budget(candidate)


# 功能：仅原 SHA 仍匹配时原子替换小文件；参数不直接重写大型文件或覆盖外部变化。
def replace_known(path: Path, expected: str, content: bytes) -> None:
    if len(content) > MAX_MANIFEST_BYTES or file_record(path, MAX_MANIFEST_BYTES)["sha256"] != expected:
        raise IntegrityError("精确小文件替换的来源摘要已变化")
    temporary: Path = path.with_name(TEMPORARY_FILE_PREFIX + uuid.uuid4().hex + TEMPORARY_FILE_SUFFIX)
    write_new(temporary, content)
    try:
        if file_record(path, MAX_MANIFEST_BYTES)["sha256"] != expected:
            raise IntegrityError("替换前文件发生变化，保留外部修改")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


# 功能：验证新输出位置不与源/项目相交；参数要求父目录存在，不覆写既有交付或备份。
def new_external(path: Path, roots: tuple[Path, ...]) -> None:
    reject_links(path, missing_leaf=True)
    if path.exists() or not path.parent.is_dir():
        raise InputError("目的地必须不存在且父目录已存在")
    for root in roots:
        if path.is_relative_to(root) or root.is_relative_to(path):
            raise InputError("目的地不得位于源/项目内或包含源/项目")


# 功能：原子发布同父自有暂存目录，明确 Windows 拒绝/共享冲突只有一个总等待预算。
# 参数：stage 为已完成核验的暂存目录，destination 必须仍不存在；不修改权限、不重做写入或游戏命令。
def publish_directory(stage: Path, destination: Path) -> int:
    if stage.parent != destination.parent:
        raise InputError("目录原子发布必须使用同父暂存路径")
    deadline: float = time.perf_counter() + DIRECTORY_PUBLISH_TIMEOUT_MS / 1000
    attempts: int = 0
    while True:
        reject_links(stage)
        reject_links(destination, missing_leaf=True)
        if not stage.is_dir():
            raise IntegrityError("自有暂存目录在发布前缺失或被替换")
        if destination.exists():
            raise IntegrityError("发布目的地被外部占用，拒绝覆写或清除")
        attempts += 1
        try:
            os.rename(stage, destination)
            return attempts
        except OSError as error:
            code: int | None = getattr(error, "winerror", None)
            if os.name != "nt" or code not in DIRECTORY_PUBLISH_WINDOWS_ERRORS:
                raise
            remaining: float = deadline - time.perf_counter()
            if remaining <= 0:
                raise IntegrityError("本地目录原子发布持续受阻；Windows 错误 " + str(code)
                                     + "，总等待预算 " + str(DIRECTORY_PUBLISH_TIMEOUT_MS)
                                     + " 毫秒；未改变权限或覆写目的地") from None
            time.sleep(min(DIRECTORY_PUBLISH_INTERVAL_MS / 1000, remaining))


# 功能：核验导出 ZIP 在临时目录独立完整性；参数根必须仍为唯一新 Skill 名，不安装到工程。
def verify_zip(path: Path) -> JsonObject:
    payload: dict[str, bytes] = zip_members(read_regular(path, MAX_ARCHIVE_BYTES))
    if any(not name.startswith(NAME + "/") for name in payload):
        raise IntegrityError("交付 ZIP 必须只有一个正确 Skill 根")
    with tempfile.TemporaryDirectory(prefix="mpft-verify-zip-") as directory:
        root: Path = Path(directory) / NAME
        root.mkdir()
        for name, content in payload.items():
            target: Path = root / relative_name(name[len(NAME) + 1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            write_new(target, content)
        return {**verify_delivery(root), "zip_sha256": str(file_record(path, MAX_ARCHIVE_BYTES)["sha256"])}


# 功能：新建完整可拖拽目录，可选 ZIP；参数先临时核验再逐产物原子发布，不回原项目补文件。
def export_delivery(root: Path, destination: Path, zip_output: Path | None = None) -> JsonObject:
    verified: JsonObject = verify_delivery(root)
    if destination.name != NAME:
        raise InputError("交付根目录必须保持 mono-pipeline-functiontest")
    new_external(destination, (root,))
    if zip_output is not None:
        new_external(zip_output, (root, destination))
        if zip_output.suffix.casefold() != ".zip":
            raise InputError("可选归档必须使用 ZIP 后缀")
    staging: Path = Path(tempfile.mkdtemp(prefix=".mpft-export-", dir=destination.parent))
    zip_stage: Path | None = None
    published: bool = False
    zip_published: bool = False
    try:
        files, _ = walk_files(root)
        for name, source in sorted(files.items()):
            target: Path = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            content: bytes = source.read_bytes() if source.stat().st_size == 0 else read_regular(source, MAX_ARCHIVE_BYTES)
            write_new(target, content)
        staged: JsonObject = verify_delivery(staging)
        if staged["manifest_sha256"] != verified["manifest_sha256"] or verify_delivery(root)["manifest_sha256"] != verified["manifest_sha256"]:
            raise IntegrityError("导出期间源或清单发生变化")
        if zip_output is not None:
            zip_stage = zip_output.with_name(".mpft-export-" + uuid.uuid4().hex + ".zip")
            with zipfile.ZipFile(zip_stage, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                staged_files, _ = walk_files(staging)
                for name, source in sorted(staged_files.items()):
                    archive.write(source, NAME + "/" + name)
            if verify_zip(zip_stage)["manifest_sha256"] != verified["manifest_sha256"]:
                raise IntegrityError("导出 ZIP 与目录摘要不同")
        if destination.exists():
            raise IntegrityError("发布前目的地已经存在")
        publish_attempts: int = publish_directory(staging, destination)
        published = True
        if publish_attempts > 1 and (verify_delivery(destination)["manifest_sha256"] != verified["manifest_sha256"]
                                     or verify_delivery(root)["manifest_sha256"] != verified["manifest_sha256"]):
            raise IntegrityError("目录等待发布期间源或暂存内容发生变化")
        if zip_output is not None and zip_stage is not None:
            if zip_output.exists():
                raise IntegrityError("发布前 ZIP 目的地已经存在")
            os.rename(zip_stage, zip_output)
            zip_published = True
        return {**verified, "delivery_root": str(destination), "zip": str(zip_output) if zip_output is not None else None,
                "published_atomically_per_artifact": True, "directory_publish_attempts": publish_attempts,
                "runtime_source_lookup": False}
    except BaseException:
        if published and destination.exists() and verify_delivery(destination)["manifest_sha256"] == verified["manifest_sha256"]:
            shutil.rmtree(destination)
        if zip_published and zip_output is not None and zip_output.exists():
            zip_output.unlink()
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if zip_stage is not None and zip_stage.exists():
            zip_stage.unlink()


# 功能：定位严格 JSON 对象的值字节位置；参数 source/start 只用于已严格解析的 UPM 小文件。
def object_spans(source: str, start: int) -> tuple[dict[str, tuple[int, int]], int]:
    decoder: json.JSONDecoder = json.JSONDecoder()
    if source[start:start + 1] != "{":
        raise InputError("UPM dependencies 必须为对象")
    position: int = start + 1
    spans: dict[str, tuple[int, int]] = {}
    while True:
        while position < len(source) and source[position].isspace():
            position += 1
        if source[position:position + 1] == "}":
            return spans, position
        key, position = decoder.raw_decode(source, position)
        if not isinstance(key, str):
            raise InputError("UPM JSON 键非法")
        while source[position].isspace():
            position += 1
        if source[position] != ":":
            raise InputError("UPM JSON 语法非法")
        position += 1
        while source[position].isspace():
            position += 1
        value_start: int = position
        _, position = decoder.raw_decode(source, position)
        spans[key] = (value_start, position)
        while source[position].isspace():
            position += 1
        if source[position] == ",":
            position += 1
        elif source[position] != "}":
            raise InputError("UPM JSON 语法非法")


# 功能：只替换明确 dependencies 字符串/插入缺项，保留 BOM 和所有其他原字节；参数 updates 来自固定同包依赖。
def patch_dependencies(raw: bytes, updates: dict[str, str]) -> bytes:
    document: JsonObject = object_value(strict_json(raw, MAX_UPM_BYTES, bom=True), "UPM manifest")
    dependencies: JsonObject = object_value(document.get("dependencies"), "UPM dependencies")
    if not updates:
        return raw
    source: str = raw.decode("utf-8-sig")
    top, _ = object_spans(source, len(source) - len(source.lstrip()))
    if "dependencies" not in top:
        raise InputError("UPM manifest 缺明确 dependencies")
    spans, close = object_spans(source, top["dependencies"][0])
    replacements: list[tuple[int, int, str]] = []
    added: dict[str, str] = {}
    for key, value in sorted(updates.items()):
        if key not in PACKAGE_NAMES or not value.startswith("file:"):
            raise InputError("只能修改明确公共嵌入包依赖")
        if key in spans:
            replacements.append((*spans[key], json.dumps(value, ensure_ascii=True)))
        else:
            added[key] = value
    if added:
        newline: str = "\r\n" if "\r\n" in source else "\n"
        match: re.Match[str] | None = re.search(r'(?m)^([ \t]*)"dependencies"', source)
        base_indent: str = match.group(1) if match is not None else "  "
        indent: str = base_indent + "  "
        values: str = ("," + newline + indent).join(json.dumps(key) + ": " + json.dumps(value) for key, value in added.items())
        if spans:
            insertion: int = max(end for _, end in spans.values())
            replacements.append((insertion, insertion, "," + newline + indent + values))
        else:
            replacements.append((close, close, newline + indent + values + newline + base_indent))
    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]
    result: bytes = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + source.encode("utf-8")
    expected: JsonObject = {**document, "dependencies": {**dependencies, **updates}}
    if strict_json(result, MAX_UPM_BYTES, bom=True) != expected:
        raise IntegrityError("UPM 精确增量核验失败")
    return result


# 功能：提取唯一真实 Unity GUID；参数不接受缺失/大小写不规范元数据。
def meta_guid(content: bytes) -> str:
    matches: list[str] = re.findall(r"(?m)^guid:\s*([0-9a-f]{32})\s*$", content.decode("utf-8-sig", errors="strict"))
    if len(matches) != 1:
        raise IntegrityError("Unity 元数据缺失唯一规范 GUID")
    return matches[0]


# 功能：建立受限源码/元数据/路径清点指纹；参数大资源只取路径，不读取纹理/资源或运行内容。
def tree_fingerprint(files: dict[str, Path], directories: set[str]) -> str:
    checksum: object = hashlib.sha256()
    for name in sorted(set(files) | directories):
        checksum.update((name + "\0").encode("utf-8"))  # type: ignore[attr-defined]
        if name in files and Path(name).suffix in {".cs", ".asmdef", ".asmref", ".meta", ".json"}:
            checksum.update(str(file_record(files[name])["sha256"]).encode("ascii"))  # type: ignore[attr-defined]
    return checksum.hexdigest()  # type: ignore[attr-defined]


# 功能：把具体冲突追加到计划，不静默替换；参数 path 永远给出实际位置。
def conflict(items: list[JsonValue], path: str, reason: str) -> None:
    record: JsonObject = {"path": path, "reason": reason}
    if record not in items:
        items.append(record)


# 功能：计划精确新增/兼容跳过，未知同名文件保守冲突；参数 source/member 指向包内唯一原字节。
def file_operation(project: Path, name: str, source: str, member: str | None, content: bytes, conflicts: list[JsonValue]) -> JsonObject:
    relative_name(name)
    target: Path = project / name
    reject_links(target, missing_leaf=True)
    before: str | None = None
    mode: str = "add"
    if target.exists():
        if not target.is_file():
            mode = "conflict"
        else:
            record: JsonObject = file_record(target)
            before = str(record["sha256"])
            mode = "skip" if record["sha256"] == digest(content) and record["bytes"] == len(content) else "conflict"
        if mode == "conflict":
            conflict(conflicts, name, "既有同名文件/元数据不匹配，禁止覆盖")
    return {"path": name, "mode": mode, "source": source, "member": member, "bytes": len(content),
            "sha256": digest(content), "before_sha256": before}


# 功能：验证已存在包的全部来源成员与无额外文件；参数不把版本字符串相等当作兼容。
def compatible_package(project: Path, location: str, payload: dict[str, bytes], conflicts: list[JsonValue]) -> bool:
    directory: Path = project / location
    files, directories = walk_files(directory, MAX_TARGET_MEMBERS)
    expected_dirs: set[str] = {"/".join(name.split("/")[:index]) for name in payload for index in range(1, len(name.split("/")))}
    if set(files) != set(payload) or directories != expected_dirs:
        conflict(conflicts, location, "既有包有额外/缺失成员或自定义布局，不能仅按版本接管")
        return False
    for name, content in payload.items():
        record: JsonObject = file_record(files[name])
        if record["bytes"] != len(content) or record["sha256"] != digest(content):
            conflict(conflicts, location + "/" + name, "既有包源文件或 GUID/许可摘要不匹配")
            return False
    return True


# 功能：默认只读生成 Unity 接入计划；参数 project 是明确 Unity 根，计划 SHA 包含源版本及当前目标清点。
def unity_preview(root: Path, project: Path) -> JsonObject:
    verified: JsonObject = verify_delivery(root)
    reject_links(project)
    if root.is_relative_to(project / "Assets"):
        raise InputError("Skill 必须位于非自动编译目录，不可拖入 Assets")
    if not project.is_dir() or not (project / "Assets").is_dir() or not (project / "Packages").is_dir() or not (project / "ProjectSettings").is_dir():
        raise InputError("目标必须是明确 Unity 项目根")
    catalog, expanded = dependency_catalog(root)
    for value in cast(list[JsonValue], catalog["packages"]):
        package: JsonObject = object_value(value, "dependency path budget")
        for member in expanded[str(package["name"])]:
            require_windows_path_budget(project / str(package["target_root"]) / member, temporary_file=True)
    conflicts: list[JsonValue] = []
    operations: list[JsonValue] = []
    version_path: Path = project / "ProjectSettings/ProjectVersion.txt"
    version_bytes: bytes = read_regular(version_path, MAX_UPM_BYTES)
    version_match: re.Match[bytes] | None = re.search(rb"(?m)^m_EditorVersion: ([^\r\n]+)", version_bytes)
    unity_version: str = version_match.group(1).decode("ascii") if version_match is not None else "unknown"
    if not unity_version.startswith(str(catalog["unity_series"]) + "."):
        conflict(conflicts, "ProjectSettings/ProjectVersion.txt", "当前负载只静态核对 Unity 2022.3 系列，其他版本需适配验收")
    lock_path: Path = project / "Temp/UnityLockfile"
    reject_links(lock_path, missing_leaf=True)
    if lock_path.exists():
        conflict(conflicts, "Temp/UnityLockfile", "目标编辑器锁存在，文件接入必须先明确关闭目标编辑器")
    assets, asset_directories = walk_files(project / "Assets", MAX_TARGET_MEMBERS)
    packages_files, package_directories = walk_files(project / "Packages", MAX_TARGET_MEMBERS)
    for name in assets:
        if "/" not in name and Path(name).suffix in {".asmdef", ".asmref"}:
            conflict(conflicts, "Assets/" + name, "公共 Global 入口祖先不得有 asmdef/asmref")
        if Path(name).suffix == ".cs" and not name.startswith("MonoPipelineFunctionTest/"):
            content: bytes = read_regular(assets[name], MAX_FILE_BYTES)
            if re.search(rb"\bclass\s+GlobalMonoPipelineTest\b", content):
                conflict(conflicts, "Assets/" + name, "发现另一公共入口，拒绝双接入/自定义布局")
    upm_raw, upm = json_file(project / "Packages/manifest.json", MAX_UPM_BYTES)
    dependencies: JsonObject = object_value(upm.get("dependencies"), "UPM dependencies")
    for name, version in object_value(catalog["engine_modules"], "engine modules").items():
        if dependencies.get(name) != version:
            conflict(conflicts, "Packages/manifest.json#dependencies/" + name, "所需 Unity 引擎模块未明确满足，不安装引擎模块")
    unity_sources, _ = walk_files(root / "assets/unity")
    unity_expected: set[str] = set(unity_sources)
    existing_unity: set[str] = {name[len("MonoPipelineFunctionTest/"):] for name in assets if name.startswith("MonoPipelineFunctionTest/")}
    for name in sorted(existing_unity - unity_expected):
        conflict(conflicts, UNITY_ROOT + "/" + name, "测试源目录存在未知额外文件，不合并旧/自定义接入")
    source_payloads: dict[str, bytes] = {}
    for name, source in sorted(unity_sources.items()):
        content = read_regular(source, MAX_FILE_BYTES)
        source_name: str = "assets/unity/" + name
        source_payloads[UNITY_ROOT + "/" + name] = content
        operations.append(file_operation(project, UNITY_ROOT + "/" + name, source_name, None, content, conflicts))
    folder_content: bytes = read_regular(root / "assets/unity.meta", MAX_UPM_BYTES)
    source_payloads[UNITY_ROOT + ".meta"] = folder_content
    operations.append(file_operation(project, UNITY_ROOT + ".meta", "assets/unity.meta", None, folder_content, conflicts))
    updates: dict[str, str] = {}
    cache_fingerprints: dict[str, str] = {}
    for value in cast(list[JsonValue], catalog["packages"]):
        package: JsonObject = object_value(value, "dependency")
        name = str(package["name"])
        version: str = str(package["version"])
        canonical_location: str = str(package["target_root"])
        known_locations: set[str] = {canonical_location, canonical_location + "@" + version}
        embedded: list[str] = []
        for directory in sorted(path for path in (project / "Packages").iterdir() if path.is_dir()):
            metadata_path: Path = directory / "package.json"
            if metadata_path.exists():
                try:
                    _, metadata = json_file(metadata_path, MAX_UPM_BYTES)
                except (InputError, IntegrityError, UnicodeError):
                    conflict(conflicts, metadata_path.relative_to(project).as_posix(), "既有包元数据非法，无法安全判定来源/同名包")
                    continue
                if metadata.get("name") == name:
                    embedded.append(directory.relative_to(project).as_posix())
            elif directory.name in {name, name + "@" + version}:
                conflict(conflicts, directory.relative_to(project).as_posix(), "同名包缺失元数据")
        if len(embedded) > 1:
            conflict(conflicts, canonical_location, "同一包存在多个嵌入布局，拒绝双接入")
        if any(location not in known_locations for location in embedded):
            conflict(conflicts, canonical_location, "同名包位于未批准自定义布局")
        specification: JsonValue = dependencies.get(name)
        allowed_specs: set[JsonValue] = {None, version} | {"file:" + location[len("Packages/"):] for location in known_locations}
        if not (specification is None or isinstance(specification, str)) or specification not in allowed_specs:
            conflict(conflicts, "Packages/manifest.json#dependencies/" + name, "同名包声明为旧版、未知来源或自定义依赖，禁止替换")
        location: str = embedded[0] if len(embedded) == 1 else canonical_location
        cached: bool = False
        cache_location: str = "Library/PackageCache/" + name + "@" + version
        cache_path: Path = project / cache_location
        reject_links(cache_path, missing_leaf=True)
        if not embedded and specification == version and cache_path.is_dir():
            location = cache_location
            cached = True
        payload: dict[str, bytes] = expanded[name]
        if (project / location).exists():
            compatible_package(project, location, payload, conflicts)
        if cached:
            cache_files, cache_dirs = walk_files(cache_path, MAX_TARGET_MEMBERS)
            cache_fingerprints[cache_location] = tree_fingerprint(cache_files, cache_dirs)
        elif specification != "file:" + location[len("Packages/"):]:
            updates[name] = "file:" + location[len("Packages/"):]
        archive: JsonObject = object_value(package["archive"], "archive")
        for member, content in sorted(payload.items()):
            destination: str = location + "/" + member
            source_payloads[destination] = content
            operations.append(file_operation(project, destination, str(archive["path"]), member, content, conflicts))
    patched: bytes = patch_dependencies(upm_raw, updates)
    operations.append({"path": "Packages/manifest.json", "mode": "patch" if patched != upm_raw else "skip", "source": None,
                       "member": None, "changes": updates, "bytes": len(patched), "sha256": digest(patched), "before_sha256": digest(upm_raw)})
    wanted_guids: dict[str, str] = {}
    for name, content in source_payloads.items():
        if not name.endswith(".meta"):
            continue
        guid: str = meta_guid(content)
        if guid in wanted_guids and wanted_guids[guid] != name:
            conflict(conflicts, name, "同包公共/依赖源存在重复 GUID")
        wanted_guids[guid] = name
    current_meta: dict[str, Path] = {"Assets/" + name: path for name, path in assets.items() if name.endswith(".meta")}
    current_meta.update({"Packages/" + name: path for name, path in packages_files.items() if name.endswith(".meta")})
    for name, path in current_meta.items():
        try:
            guid = meta_guid(read_regular(path, MAX_UPM_BYTES))
        except (InputError, IntegrityError, UnicodeError):
            conflict(conflicts, name, "目标既有元数据缺失唯一规范 GUID，不能安全核对接入冲突")
            continue
        if guid in wanted_guids and wanted_guids[guid] != name:
            conflict(conflicts, name, "目标既有 GUID 与本次接入路径冲突")
    receipt_path: Path = project / INTEGRATION_RECEIPT
    receipt_sha: str | None = None
    if receipt_path.exists():
        receipt_raw, receipt = json_file(receipt_path)
        receipt_sha = digest(receipt_raw)
        receipt_fields: set[str] = {"schema", "project", "delivery_sha256", "plan_sha256", "files"}
        keys_only(receipt, receipt_fields, "integration receipt", receipt_fields)
        if (receipt["schema"] != "mono-pipeline-unity-integration/1" or receipt["project"] != str(project)
                or receipt["delivery_sha256"] != verified["manifest_sha256"]):
            conflict(conflicts, INTEGRATION_RECEIPT, "接入记录不属于当前项目/工具版本，禁止旧版本接管")
        receipt_files: dict[str, JsonObject] = entries(receipt["files"])
        expected_files: dict[str, JsonObject] = {str(object_value(item, "operation")["path"]): object_value(item, "operation") for item in operations}
        if set(receipt_files) != set(expected_files) or any(receipt_files[name]["sha256"] != item["sha256"] or receipt_files[name]["bytes"] != item["bytes"] for name, item in expected_files.items() if name in receipt_files):
            conflict(conflicts, INTEGRATION_RECEIPT, "接入记录成员与当前精确负载不一致")
    lock_manifest: Path = project / "Packages/packages-lock.json"
    reject_links(lock_manifest, missing_leaf=True)
    lock_hash: JsonValue = file_record(lock_manifest)["sha256"] if lock_manifest.exists() else None
    plan: JsonObject = {"schema": "mono-pipeline-unity-plan/1", "project": str(project), "delivery_sha256": verified["manifest_sha256"],
                        "unity_version": unity_version, "project_version_sha256": digest(version_bytes),
                        "asset_scan_sha256": tree_fingerprint(assets, asset_directories), "package_scan_sha256": tree_fingerprint(packages_files, package_directories),
                        "cache_fingerprints": cache_fingerprints, "upm_lock_sha256": lock_hash, "integration_receipt_sha256": receipt_sha,
                        "operations": operations, "conflicts": conflicts, "upm_lock_rewritten": False,
                        "acceptance_gaps": ["UPM resolution not executed", "Unity compilation/build not executed", "Mono Player/runtime gate/business acceptance not executed", "Original game build and hot-update integration requires project adaptation"]}
    return {**plan, "plan_sha256": digest(canonical(plan)), "read_only": True}


# 功能：读取计划的真实批准 SHA；参数避免把显示附加字段重新当作批准摘要输入。
def plan_sha256(plan: JsonObject) -> str:
    return hash_value(plan.get("plan_sha256"), "plan_sha256")


# 功能：从已核验同包负载/精确增量取得新字节；参数不会回维护项目或下载。
def operation_bytes(root: Path, project: Path, operation: JsonObject, expanded: dict[str, dict[str, bytes]], catalog: JsonObject) -> bytes:
    source: JsonValue = operation.get("source")
    member: JsonValue = operation.get("member")
    if source is None and operation["path"] == "Packages/manifest.json":
        raw: bytes = read_regular(project / "Packages/manifest.json", MAX_UPM_BYTES)
        changes: JsonObject = object_value(operation.get("changes"), "manifest changes")
        return patch_dependencies(raw, {key: str(value) for key, value in changes.items()})
    if not isinstance(source, str):
        raise IntegrityError("计划没有明确同包源")
    if member is None:
        return read_regular(root / relative_name(source), MAX_FILE_BYTES)
    for value in cast(list[JsonValue], catalog["packages"]):
        package: JsonObject = object_value(value, "package")
        archive: JsonObject = object_value(package["archive"], "archive")
        if archive["path"] == source:
            name: str = relative_name(member)
            if name not in expanded[str(package["name"])]:
                raise IntegrityError("计划 ZIP 成员不属于固定依赖")
            return expanded[str(package["name"])][name]
    raise IntegrityError("计划依赖源未知")


# 功能：仅创建当前操作所需新目录并记录拥有者；参数 stop 是项目根，不覆盖既有目录或链接。
def owned_parents(path: Path, stop: Path, created: list[Path]) -> None:
    missing: list[Path] = []
    current: Path = path.parent
    while current != stop and not current.exists():
        missing.append(current)
        current = current.parent
    reject_links(path.parent, missing_leaf=True)
    if not current.is_dir() or not path.is_relative_to(stop):
        raise IntegrityError("目标父目录不属于批准项目")
    for directory in reversed(missing):
        directory.mkdir()
        created.append(directory)


# 功能：精确文件级原子发布；参数 before=None 只新增，已有小 manifest 还需原摘要一致。
def publish_file(path: Path, content: bytes, before: str | None) -> None:
    reject_links(path, missing_leaf=True)
    if before is not None:
        replace_known(path, before, content)
        return
    if path.exists():
        raise IntegrityError("新增目标被外部创建，拒绝覆写")
    temporary: Path = path.with_name(TEMPORARY_FILE_PREFIX + uuid.uuid4().hex + TEMPORARY_FILE_SUFFIX)
    write_new(temporary, content)
    try:
        # 硬链接新建是原子 no-replace，完成后移除临时名；最终成员不保留多重链接。
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


# 功能：明确批准后在外部备份保护下接入精确文件；参数旧计划/源/目标变化、未知冲突或既有备份拒绝。
def unity_apply(root: Path, project: Path, approved_sha256: str, approved: bool, backup: Path) -> JsonObject:
    if not approved:
        raise InputError("apply 还需要独立明确批准，不只提供预览摘要")
    expected: str = hash_value(approved_sha256, "approved plan")
    new_external(backup, (root, project))
    plan: JsonObject = unity_preview(root, project)
    if plan_sha256(plan) != expected:
        raise IntegrityError("批准计划已经变化；不自动重新批准")
    if plan["conflicts"]:
        raise EnvironmentBlocked("接入计划存在精确冲突，禁止写目标")
    catalog, expanded = dependency_catalog(root)
    operations: list[JsonObject] = [object_value(item, "operation") for item in cast(list[JsonValue], plan["operations"])]
    changes: list[JsonObject] = [item for item in operations if item["mode"] in {"add", "patch"}]
    if not changes and (project / INTEGRATION_RECEIPT).exists():
        return {"project": str(project), "applied": False, "compatible_skipped": True, "plan_sha256": expected,
                "unity_compiled_or_player_verified": False, "backup_created": False}
    stage: Path = Path(tempfile.mkdtemp(prefix=".mpft-backup-", dir=backup.parent))
    original: dict[str, bytes] = {}
    staged: dict[str, bytes] = {}
    created: list[Path] = []
    written: dict[str, str] = {}
    backup_published: bool = False
    try:
        require_windows_path_budget(project / INTEGRATION_RECEIPT, temporary_file=True)
        require_windows_path_budget(stage / "backup-manifest.json")
        require_windows_path_budget(backup / "result.json")
        for operation in changes:
            name: str = relative_name(operation["path"])
            require_windows_path_budget(project / name, temporary_file=True)
            require_windows_path_budget(stage / "proposed" / name)
            require_windows_path_budget(backup / "proposed" / name)
            if operation["before_sha256"] is not None:
                require_windows_path_budget(stage / "original" / name)
                require_windows_path_budget(backup / "original" / name)
        for operation in changes:
            name: str = relative_name(operation["path"])
            content: bytes = operation_bytes(root, project, operation, expanded, catalog)
            if len(content) != operation["bytes"] or digest(content) != operation["sha256"]:
                raise IntegrityError("接入源在暂存期间变化")
            proposed: Path = stage / "proposed" / name
            proposed.parent.mkdir(parents=True, exist_ok=True)
            write_new(proposed, content)
            staged[name] = content
            if operation["before_sha256"] is not None:
                before: bytes = read_regular(project / name, MAX_UPM_BYTES)
                if digest(before) != operation["before_sha256"]:
                    raise IntegrityError("备份前目标来源变化")
                original[name] = before
                saved: Path = stage / "original" / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                write_new(saved, before)
        backup_manifest: JsonObject = {"schema": "mono-pipeline-unity-backup/1", "project": str(project), "plan_sha256": expected,
                                       "delivery_sha256": plan["delivery_sha256"], "original": [{"path": name, "sha256": digest(content), "bytes": len(content)} for name, content in original.items()],
                                       "proposed": [{"path": name, "sha256": digest(content), "bytes": len(content)} for name, content in staged.items()]}
        write_new(stage / "backup-manifest.json", canonical(backup_manifest))
        if plan_sha256(unity_preview(root, project)) != expected:
            raise IntegrityError("暂存后源/目标/锁/批准计划发生变化")
        if backup.exists():
            raise IntegrityError("外部备份目的地被占用，禁止接管")
        publish_attempts: int = publish_directory(stage, backup)
        backup_published = True
        if publish_attempts > 1 and plan_sha256(unity_preview(root, project)) != expected:
            raise IntegrityError("备份等待发布期间源/目标/批准计划发生变化")
        for operation in changes:
            name = str(operation["path"])
            proposed = backup / "proposed" / name
            content = read_regular(proposed, MAX_FILE_BYTES)
            if digest(content) != operation["sha256"]:
                raise IntegrityError("外部暂存备份被改写")
            target: Path = project / name
            owned_parents(target, project, created)
            publish_file(target, content, cast(str | None, operation["before_sha256"]))
            written[name] = digest(content)
        for operation in operations:
            target = project / str(operation["path"])
            record: JsonObject = file_record(target)
            if record["sha256"] != operation["sha256"] or record["bytes"] != operation["bytes"]:
                raise IntegrityError("接入后的精确成员核验失败")
        if verify_delivery(root)["manifest_sha256"] != plan["delivery_sha256"]:
            raise IntegrityError("接入期间同包源发生变化")
        receipt: JsonObject = {"schema": "mono-pipeline-unity-integration/1", "project": str(project), "delivery_sha256": plan["delivery_sha256"],
                               "plan_sha256": expected, "files": [{"path": item["path"], "bytes": item["bytes"], "sha256": item["sha256"]} for item in operations]}
        receipt_content: bytes = canonical(receipt)
        publish_file(project / INTEGRATION_RECEIPT, receipt_content, None)
        written[INTEGRATION_RECEIPT] = digest(receipt_content)
        write_new(backup / "result.json", canonical({"status": "applied_files_only", "plan_sha256": expected, "written": list(written), "upm_lock_rewritten": False}))
        return {"project": str(project), "applied": True, "plan_sha256": expected, "backup": str(backup), "added_or_patched": len(changes),
                "compatible_skipped": len(operations) - len(changes), "upm_lock_rewritten": False,
                "backup_publish_attempts": publish_attempts,
                "unity_compiled_or_player_verified": False, "acceptance_gaps": plan["acceptance_gaps"]}
    except BaseException:
        preserved: list[JsonValue] = []
        restored: list[JsonValue] = []
        for name, checksum in reversed(list(written.items())):
            target = project / name
            try:
                if not target.is_file() or file_record(target)["sha256"] != checksum:
                    preserved.append(name)
                    continue
                if name in original:
                    saved = backup / "original" / name
                    content = read_regular(saved, MAX_UPM_BYTES)
                    if digest(content) != digest(original[name]):
                        raise IntegrityError("原备份发生变化，停止恢复")
                    replace_known(target, checksum, content)
                else:
                    reject_links(target)
                    target.unlink()
                restored.append(name)
            except (OSError, InputError, IntegrityError):
                preserved.append(name)
        for directory in reversed(created):
            try:
                reject_links(directory)
                directory.rmdir()
            except (OSError, InputError):
                pass
        if backup_published:
            result_path: Path = backup / "result.json"
            if not result_path.exists():
                write_new(result_path, canonical({"status": "failed_restore_attempted", "plan_sha256": expected, "restored": restored,
                                                  "external_changes_preserved": preserved, "transactional_crash_rollback_guaranteed": False}))
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)


# 功能：清点真实静态包全部文件，不读运行描述符；参数仅排除根清单/描述符，不把结构存在当完整游戏。
def package_snapshot(exe: Path) -> tuple[list[JsonValue], list[JsonValue]]:
    reject_links(exe)
    if not exe.is_file() or exe.suffix.casefold() != ".exe":
        raise InputError("静态扫描需要明确存在的 EXE")
    limits: Limits = Limits()
    files, _ = walk_files(exe.parent, limits.package_entries)
    records: list[JsonValue] = []
    gaps: list[JsonValue] = []
    for name, path in sorted(files.items()):
        if name in {PACKAGE_MANIFEST, DESCRIPTOR_NAME}:
            continue
        if DESCRIPTOR_NAME in name.split("/"):
            raise IntegrityError("静态包存在非根运行描述符，不能纳入交付")
        record: JsonObject = file_record(path, limits.package_file_bytes)
        records.append({"path": name, **record})
    data: str = exe.stem + "_Data"
    required: set[str] = {exe.name, "UnityPlayer.dll", data + "/globalgamemanagers", data + "/boot.config",
                          data + "/Managed/Assembly-CSharp.dll", data + "/Managed/Unity.Pipeline.dll",
                          "MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll"}
    declared: set[str] = {str(object_value(item, "package member")["path"]) for item in records}
    gaps.extend("missing_required_member:" + name for name in sorted(required - declared))
    for item in records:
        member: JsonObject = object_value(item, "package member")
        if member["path"] in required and member["bytes"] == 0:
            gaps.append("zero_byte_required_member:" + str(member["path"]))
    if (exe.parent / "GameAssembly.dll").exists() or (exe.parent / data / "il2cpp_data").exists():
        gaps.append("il2cpp_or_conflicting_backend_markers")
    with exe.open("rb") as stream:
        if stream.read(2) != b"MZ":
            gaps.append("exe_has_no_windows_mz_signature")
    return records, gaps


# 功能：无构建来源时只生成 candidate；参数新输出在包/工具之外，不自动 complete=true。
def package_candidate(root: Path, exe: Path, output: Path) -> JsonObject:
    verify_delivery(root)
    new_external(output, (root, exe.parent))
    records, gaps = package_snapshot(exe)
    candidate: JsonObject = {"_comment": "创建日期：2026-10-26；作者：Cyou；功能：无构建来源的实际文件候选库存；参数：真实 EXE/字节/摘要，构建与完整游戏交付未确认。",
                             "schema": "mono-pipeline-package-candidate/1", "exe": exe.name, "build_guid": None, "unity_version": None,
                             "platform": None, "backend": None, "development": None, "complete": False, "files": records,
                             "acceptance_gaps": ["successful_build_report_or_authorized_inventory_missing", "complete_game_delivery_not_explicitly_reviewed", *gaps]}
    write_new(output, canonical(candidate) + b"\n")
    return {"candidate": str(output), "file_count": len(records), "complete": False, "acceptance_gaps": candidate["acceptance_gaps"]}


# 功能：成功 BuildReport 库存+明确完整交付审阅生成宿主静态清单；参数批准绑定库存 SHA，不能只扫描 files 冒充完整。
def prepare_package_manifest(root: Path, exe: Path, inventory_path: Path, inventory_sha256: str, approval_path: Path, output: Path) -> JsonObject:
    verify_delivery(root)
    reject_links(output, missing_leaf=True)
    if output.exists() or not output.parent.is_dir() or output.is_relative_to(root):
        raise InputError("静态清单必须是新文件且不能污染工具")
    if output.is_relative_to(exe.parent) and output != exe.parent / PACKAGE_MANIFEST:
        raise InputError("包内静态清单只允许精确 package-manifest.json 落点")
    inventory_raw, inventory = json_file(inventory_path)
    expected: str = hash_value(inventory_sha256, "inventory_sha256")
    if digest(inventory_raw) != expected:
        raise IntegrityError("构建库存原字节 SHA256 不匹配")
    inventory_fields: set[str] = {"schema", "source", "build_result", "exe", "build_guid", "unity_version", "platform", "backend", "development",
                                 "files", "report_files", "report_total_size", "complete_game_delivery", "acceptance_gaps"}
    keys_only(inventory, inventory_fields, "build inventory", inventory_fields)
    integer(inventory["report_total_size"], "BuildReport total bytes")
    if type(inventory["complete_game_delivery"]) is not bool or not isinstance(inventory["acceptance_gaps"], list):
        raise InputError("构建库存完整交付声明/缺口类型非法")
    required_values: JsonObject = {"schema": "mono-pipeline-build-inventory/1", "source": "BuildReport", "build_result": "Succeeded",
                                   "exe": exe.name, "platform": "WindowsPlayer", "backend": "mono", "development": True}
    if any(inventory[key] != value or (key == "development" and inventory[key] is not True) for key, value in required_values.items()):
        raise EnvironmentBlocked("必须提供成功 Windows Mono Development BuildReport 来源库存")
    build_guid: str = text(inventory["build_guid"], "BuildReport build_guid")
    if re.fullmatch(r"[0-9a-f]{32}", build_guid) is None:
        raise InputError("BuildReport 构建 GUID 必须为实际规范值")
    unity_version: str = text(inventory["unity_version"], "BuildReport unity_version")
    if re.fullmatch(r"2022\.3\.\d+[abfp]\d+", unity_version) is None:
        raise EnvironmentBlocked("该依赖负载只支持待验收的 Unity 2022.3 系列")
    approval_raw, approval = json_file(approval_path)
    approval_fields: set[str] = {"schema", "inventory_sha256", "accepted", "complete_game_delivery", "reviewer", "statement"}
    keys_only(approval, approval_fields, "package approval", approval_fields)
    if (approval["schema"] != "mono-pipeline-package-approval/1" or approval["inventory_sha256"] != expected
            or approval["accepted"] is not True or approval["complete_game_delivery"] is not True or approval["reviewer"] != "current_agent"):
        raise InputError("完整原 App/资源交付必须被当前 Agent 明确审阅并绑定本次库存，不自动批准")
    text(approval["statement"], "complete package review", trim=False)
    records, gaps = package_snapshot(exe)
    if gaps:
        raise EnvironmentBlocked("实际静态包结构存在验收缺口，不能生成 complete 清单")
    actual: dict[str, JsonObject] = entries(records, Limits().package_entries, Limits().package_file_bytes)
    declared: dict[str, JsonObject] = entries(inventory["files"], Limits().package_entries, Limits().package_file_bytes)
    if actual != declared:
        raise IntegrityError("成功构建库存与当前全体实际文件/摘要不一致")
    # 2026-10-30 修正：report_files 是 Unity BuildReport 在构建时刻的记录，不是最终落盘字节。
    # Unity 在 BuildReport 之后仍会写出/回写部分生成文件（典型 ScriptingAssemblies.json），
    # 因此 file.size 与最终磁盘字节存在固有漂移。旧实现把该回显当逐字节断言，导致同一份
    # 逐字节+SHA256 全部匹配的包被反复拒绝。真正完整性断言是上面的 actual == declared。
    # 这里保留 report_files 全部来源职责（路径必须存在、不得重复、EXE 必须被关联），
    # 并把字节漂移显式登记为 report_byte_drift 供审计追溯，而不是静默接受。
    report_files: JsonValue = inventory["report_files"]
    if not isinstance(report_files, list) or not report_files or len(report_files) > Limits().package_entries:
        raise InputError("BuildReport 原始文件范围缺失")
    report_paths: set[str] = set()
    report_byte_drift: list[JsonObject] = []
    for value in report_files:
        item: JsonObject = object_value(value, "BuildReport file")
        keys_only(item, {"path", "bytes", "role"}, "BuildReport file", {"path", "bytes", "role"})
        name: str = relative_name(item["path"])
        text(item["role"], "BuildReport role")
        reported_bytes: int = integer(item["bytes"], "BuildReport file bytes", 0, Limits().package_file_bytes)
        if name.casefold() in report_paths or name not in actual:
            raise IntegrityError("BuildReport 原始文件与实际库存不匹配")
        report_paths.add(name.casefold())
        actual_bytes: int = cast(int, actual[name]["bytes"])
        if reported_bytes != actual_bytes:
            report_byte_drift.append({"path": name, "reported_bytes": reported_bytes, "actual_bytes": actual_bytes})
    if exe.name.casefold() not in report_paths:
        raise IntegrityError("BuildReport 没有关联本次真实 EXE")
    manifest: JsonObject = {"_comment": "创建日期：2026-10-26；作者：Cyou；功能：明确完整交付审阅后的实际静态清单；参数：成功 BuildReport 库存 SHA256=" + expected + "; 仅文件级确认，不代表 Unity/Player/业务验收。",
                            "schema": "mono-pipeline-package/1", "backend": "mono", "development": True, "complete": True,
                            "exe": exe.name, "build_guid": build_guid, "unity_version": unity_version, "platform": "WindowsPlayer", "files": records}
    content: bytes = canonical(manifest) + b"\n"
    write_new(output, content)
    return {"package_manifest": str(output), "manifest_sha256": digest(content), "inventory_sha256": expected,
            "approval_sha256": digest(approval_raw), "file_count": len(records), "complete_delivery_explicitly_reviewed": True,
            "report_byte_drift": report_byte_drift, "runtime_verified": False}


# 功能：准备单目标公开配置，交叉核验静态清单/明确 PID/ACL/描述符但不连接 Player；参数 hooks 仅供隔离内存身份测试。
def prepare_target(root: Path, exe: Path, pid: int, permission_record: Path, output: Path,
                   package_manifest: Path | None = None, hooks: IdentityHooks | None = None,
                   integrity_mode: str = "full") -> JsonObject:
    verify_delivery(root)
    if integrity_mode not in INTEGRITY_MODES:
        raise InputError("integrity_mode 只能为 full 或 identity_only")
    new_external(output, (root, exe.parent))
    integer(pid, "explicit pid")
    permission_raw, permission = json_file(permission_record)
    fields: set[str] = {"schema", "exe", "pid", "license", "permissions", "evidence_roots", "request_root", "reviewer", "statement"}
    keys_only(permission, fields, "target permission record", fields)
    if (permission["schema"] != "mono-pipeline-target-permission/1" or permission["reviewer"] != "current_agent"
            or permission["pid"] != pid or type(permission["pid"]) is not int
            or local_path(text(permission["exe"], "permission exe"), permission_record.parent) != exe):
        raise InputError("当前 Agent 必须明确本次唯一 EXE/PID 和许可记录")
    text(permission["statement"], "permission statement", trim=False)
    license_info: JsonObject = object_value(permission["license"], "license acceptance")
    keys_only(license_info, {"path", "sha256", "accepted", "scope"}, "license acceptance", {"path", "sha256", "accepted", "scope"})
    if license_info["accepted"] is not True:
        raise InputError("没有明确 accepted=true 许可记录，不自动接受")
    license_path: Path = local_path(text(license_info["path"], "license path"), permission_record.parent)
    license_bytes: bytes = read_regular(license_path, Limits().source_bytes)
    if digest(license_bytes) != hash_value(license_info["sha256"], "license digest"):
        raise IntegrityError("本次明确许可文件摘要变化")
    permissions: JsonValue = permission["permissions"]
    if (not isinstance(permissions, list) or any(not isinstance(item, str) or item not in PERMISSIONS for item in permissions)
            or len(set(cast(list[str], permissions))) != len(permissions) or not {"attach", "script_execute"} <= set(cast(list[str], permissions))):
        raise EnvironmentBlocked("目标准备的只读身份/描述符核验也要求明确 attach + script_execute 许可，不自动补权限")
    roots: JsonValue = permission["evidence_roots"]
    if not isinstance(roots, list):
        raise InputError("证据根必须由本次许可明确给定")
    evidence_roots: list[Path] = [local_path(text(value, "evidence root"), permission_record.parent) for value in roots]
    request_root: Path = local_path(text(permission["request_root"], "request root"), permission_record.parent)
    for path in [*evidence_roots, request_root]:
        if not path.is_dir() or path.is_relative_to(exe.parent) or path.is_relative_to(root):
            raise InputError("证据/请求输出根必须已存在且在静态包和工具之外")
    manifest_path: Path = package_manifest if package_manifest is not None else exe.parent / PACKAGE_MANIFEST
    _, manifest = json_file(manifest_path)
    manifest_fields: set[str] = {"schema", "backend", "development", "complete", "exe", "build_guid", "unity_version", "platform", "files"}
    keys_only(manifest, manifest_fields, "static package manifest", manifest_fields)
    if (manifest["schema"] != "mono-pipeline-package/1" or manifest["backend"] != "mono" or manifest["development"] is not True
            or manifest["complete"] is not True or manifest["exe"] != exe.name or manifest["platform"] != "WindowsPlayer"):
        raise EnvironmentBlocked("读取描述符前必须确认完整 Windows Mono Development 静态清单")
    # identity_only 跳过全体静态包字节比对；仍核验清单成员形状与包声明身份，不改写清单。
    if integrity_mode == "full":
        static_records, static_gaps = package_snapshot(exe)
        if static_gaps or entries(static_records, Limits().package_entries, Limits().package_file_bytes) != entries(manifest["files"], Limits().package_entries, Limits().package_file_bytes):
            raise IntegrityError("读取描述符前实际全体静态包/摘要不一致")
    identity_hooks: IdentityHooks = hooks if hooks is not None else IdentityHooks()
    descriptor_path: Path = exe.parent / DESCRIPTOR_NAME
    acl: JsonObject = identity_hooks.acl(descriptor_path, Limits().identity_timeout_ms)
    if acl.get("checked") is not True or acl.get("policy") != "current_user_system_administrators_only":
        raise EnvironmentBlocked("读取描述符前未核验实际 Windows ACL")
    descriptor_raw: bytes = read_regular(descriptor_path, Limits().descriptor_bytes)
    descriptor: JsonObject = object_value(strict_json(descriptor_raw, Limits().descriptor_bytes, bom=True), "runtime descriptor")
    keys_only(descriptor, DESCRIPTOR_KEYS, "runtime descriptor", DESCRIPTOR_KEYS - {"capabilities"})
    process: JsonObject = identity_hooks.process(pid, exe, Limits().identity_timeout_ms)
    document: JsonObject = {"schema": "mono-pipeline-target/1", "exe": str(exe), "pid": pid,
                            "port": descriptor.get("port"), "process_created_utc": process.get("created"), "build_guid": manifest.get("build_guid"),
                            "unity_version": manifest.get("unity_version"), "platform": manifest.get("platform"),
                            "working_directory": descriptor.get("workingDirectory"), "package_manifest": str(manifest_path),
                            "license": {**license_info, "path": str(license_path)}, "permissions": permissions,
                            "evidence_roots": [str(path) for path in evidence_roots], "limits": {},
                            "integrity_mode": integrity_mode}
    target: TargetConfig = parse_target(document, output.parent)
    verified = verify_target_identity(target, identity_hooks)
    SecretGuard((verified.token,)).check(document)
    # 直接保留显式 accepted/permissions 原值；不通过会自动重声明接受的 TargetConfig.to_json 生成批准。
    write_new(output, canonical(document) + b"\n")
    return {"target": str(output), "permission_record_sha256": digest(permission_raw), "pid": pid, "port": target.port,
            "process_created_utc": target.process_created_utc, "build_guid": target.build_guid, "request_root": str(request_root),
            "identity": verified.evidence, "player_connected": False, "heartbeat_handshake_required": True}
