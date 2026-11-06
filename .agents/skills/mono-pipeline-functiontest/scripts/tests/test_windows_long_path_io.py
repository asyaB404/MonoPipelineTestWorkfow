"""创建日期：2026-10-27；作者：Cyou。
功能：用当前 Unity 自带 Mono 执行从真实源抽出的文件 I/O 方法，复验长路径扫描/复制/核验与输入守卫。
参数：仅自建临时文件和当前编译引用，不构建、加载 Unity、启动 Player 或修改原始包。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from .test_unity_payload import method_body

SKILL: Path = Path(__file__).resolve().parents[2]
PROJECT: Path = SKILL.parents[2]


# 功能：抽取真实方法声明及完整方法体；参数 declaration 必须唯一，方法内容不手写重实现。
def extract(source: str, declaration: str) -> str:
    return declaration + "\n" + method_body(source, declaration)


class WindowsLongPathIoTests(unittest.TestCase):
    # 功能：编译临时纯 I/O 方法镜像；参数无，引用来自现有响应文件，不调用 Unity 编辑器。
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="mpft-long-io-")
        cls.folder: Path = Path(cls.temporary.name)
        response_path: Path = PROJECT / "Library/Bee/artifacts/1900b0aEDbg.dag/Assembly-CSharp-Editor.rsp"
        if not response_path.is_file():
            cls.temporary.cleanup()
            raise unittest.SkipTest("Optional source I/O integration needs existing Editor references; no editor or dependency is installed")
        response: str = response_path.read_text(encoding="utf-8-sig")
        normalized: str = response.replace("\\", "/")
        match: re.Match[str] | None = re.search(r'"([^"\n]+/Editor/Data)/', normalized)
        if match is None:
            cls.temporary.cleanup()
            raise AssertionError("Actual Unity compiler root unavailable")
        data: Path = Path(match.group(1))
        cls.mono: Path = data / "MonoBleedingEdge/bin/mono.exe"
        support: str = (SKILL / "assets/unity/Editor/MonoPipelineBuildSupport.cs").read_text(encoding="utf-8-sig")
        adapter: str = (SKILL / "assets/adapters/GameClient/GlobalMonoPipelineGameClientBuild.cs").read_text(encoding="utf-8-sig")
        constants: list[str] = [line.strip() for line in support.splitlines() if line.strip().startswith("private const ")]
        methods: list[str] = [extract(support, declaration) for declaration in (
            "public static string GetFileSystemPath(string path)",
            "public static string[] GetFileSystemEntries(string directory)",
            "public static void SafePath(string path, bool requireExisting)",
            "private static List<object> ScanPackage(string root)",
            "private static string FileHash(string path)",
        )]
        copy_methods: list[str] = [extract(adapter, declaration) for declaration in (
            "private static void RequireSafePath(string path)",
            "private static void CopyPackage(string source, string target)",
            "private static void VerifyPackageCopy(string package, string inventoryPath)",
            "private static string FileHash(string path)",
        )]
        program: str = r"""
// 创建日期：2026-10-27；作者：Cyou；功能：纯文件 I/O 回归宿主；参数：自建临时根，不执行构建或游戏。
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
public static class MonoPipelineBuildSupport
{
SUPPORT
    // 功能：只公开本次真实扫描方法；参数 root 为临时测试包目录。
    public static List<object> Scan(string root) { return ScanPackage(root); }
}
public static class FileCopyValidation
{
    private const int MaximumEntries = 16384;
    private const int HashBufferBytes = 1024 * 1024;
COPY
    // 功能：执行临时长路径文件闭环；参数 args[0] 是本例自建根，不是项目/游戏目录。
    public static int Main(string[] args)
    {
        if (args.Length == 2 && args[0] == "read-real")
        {
            string file = args[1];
            MonoPipelineBuildSupport.SafePath(file, true);
            FileInfo information = new FileInfo(MonoPipelineBuildSupport.GetFileSystemPath(file));
            Console.WriteLine("READ_REAL_LONG_PATH_OK characters=" + file.Length + " bytes=" + information.Length + " sha256=" + FileHash(file));
            return 0;
        }
        string root = args[0];
        string source = Path.Combine(root, "source", new string('s', 120), new string('t', 120));
        string target = Path.Combine(root, "target", new string('u', 120), new string('v', 120));
        Directory.CreateDirectory(MonoPipelineBuildSupport.GetFileSystemPath(source));
        string member = Path.Combine(source, "long-member.txt");
        string empty = Path.Combine(source, "empty.marker");
        File.WriteAllBytes(MonoPipelineBuildSupport.GetFileSystemPath(member), new byte[] { 1, 2, 3, 4 });
        File.WriteAllBytes(MonoPipelineBuildSupport.GetFileSystemPath(empty), new byte[0]);
        List<object> files = MonoPipelineBuildSupport.Scan(source);
        if (files.Count != 2) throw new IOException("long_path_scan_dropped_member");
        foreach (Dictionary<string, object> item in files)
        {
            string relative = (string)item["path"];
            if (Path.IsPathRooted(relative) || relative.Contains("?")) throw new IOException("io_prefix_leaked_to_inventory");
        }
        string inventory = Path.Combine(root, "inventory.json");
        File.WriteAllText(inventory, JsonConvert.SerializeObject(new Dictionary<string, object> { { "files", files } }));
        CopyPackage(source, target);
        VerifyPackageCopy(target, inventory);
        if (FileHash(member) != FileHash(Path.Combine(target, "long-member.txt"))) throw new IOException("long_path_copy_hash_mismatch");
        int blocked = 0;
        foreach (string invalid in new string[] { @"\\server\share\file", @"\\?\C:\file", @"\\.\C:\file", Path.Combine(root, "..", "escape") })
        {
            try { MonoPipelineBuildSupport.GetFileSystemPath(invalid); }
            catch (IOException) { blocked++; }
        }
        if (blocked != 4) throw new IOException("long_path_input_guard_weakened");
        bool overwriteBlocked = false;
        try { CopyPackage(source, target); }
        catch (IOException) { overwriteBlocked = true; }
        if (!overwriteBlocked) throw new IOException("existing_target_overwrite_allowed");
        Console.WriteLine("LONG_PATH_IO_OK files=2 guards=4 overwrite_blocked=true max_path=" + Math.Max(member.Length, Path.Combine(target, "long-member.txt").Length));
        return 0;
    }
}
"""
        program = program.replace("SUPPORT", "\n".join(constants + methods)).replace("COPY", "\n".join(copy_methods))
        source_file: Path = cls.folder / "LongPathIoValidation.cs"
        source_file.write_text(program, encoding="utf-8")
        executable: Path = cls.folder / "LongPathIoValidation.exe"
        cls.executable = executable
        flags: list[str] = [line for line in response.splitlines() if line.startswith(("-r:", "-reference:", "-langversion:"))]
        newtonsoft: list[str] = [line for line in flags if line.replace("\\", "/").rsplit("/", 1)[-1].rstrip('"') == "Newtonsoft.Json.dll"]
        if len(newtonsoft) != 1:
            cls.temporary.cleanup()
            raise AssertionError("Actual Newtonsoft reference must be unique")
        dependency: Path = Path(newtonsoft[0].split(":", 1)[1].strip('"'))
        if not dependency.is_absolute():
            dependency = PROJECT / dependency
        shutil.copyfile(dependency, cls.folder / "Newtonsoft.Json.dll")
        compile_rsp: Path = cls.folder / "compile.rsp"
        compile_rsp.write_text("\n".join(["-target:exe", "-nostdlib+", '-out:"' + str(executable) + '"', *flags, '"' + str(source_file) + '"']), encoding="utf-8")
        process: subprocess.CompletedProcess[str] = subprocess.run([str(data / "NetCoreRuntime/dotnet.exe"), str(data / "DotNetSdkRoslyn/csc.dll"), "-noconfig", "@" + str(compile_rsp)], cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if process.returncode != 0:
            cls.temporary.cleanup()
            raise AssertionError(process.stdout + process.stderr)

    # 功能：仅清理本类自己的临时源码/DLL；参数无，不清理任何游戏包。
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree("\\\\?\\" + str(cls.folder))
        cls.temporary.cleanup()

    # 功能：在实际 Editor Mono 中执行真实方法的长路径闭环；参数为自建临时子目录。
    def test_actual_editor_mono_long_path_scan_copy_and_hash(self) -> None:
        root: Path = self.folder / "case"
        process: subprocess.CompletedProcess[str] = subprocess.run([str(self.mono), str(self.executable), str(root)], cwd=self.folder, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn("LONG_PATH_IO_OK files=2 guards=4 overwrite_blocked=true", process.stdout)
        print(process.stdout.strip())
