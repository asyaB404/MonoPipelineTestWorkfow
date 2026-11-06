"""创建日期：2026-10-26；创建人：Cyou。
功能：用系统已有 .NET 编译器执行真实 EarlyGate 方法体的隔离桩回归。
基础参数：同包门禁源、临时 C# 控制台桩、Windows 已有编译器；不编译 Unity 工程或运行 Player。
边界：桩验证分支和配置关闭顺序，不证明真实 Unity 加载时机、Mono 或 Pipeline 服务已验收。
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .test_unity_payload import method_body

COMPILER_TIMEOUT_SECONDS = 30
FIXTURE_TIMEOUT_SECONDS = 30
ACTIVE_SYMBOLS = "UNITY_STANDALONE_WIN,DEVELOPMENT_BUILD,MONO_PIPELINE_FUNCTIONTEST"

FIXTURE_PREFIX = r"""
// 创建日期：2026-10-26；创建人：Cyou；功能：门禁分支测试桩；基础参数：模拟配置、平台和本进程参数，非 Unity。
using System;
using System.Reflection;
using System.Reflection.Emit;
using UnityEngine;
namespace Mono { internal sealed class Runtime {} }
namespace UnityEngine
{
    public enum RuntimePlatform { WindowsPlayer, Android }
    public static class Application
    {
        public static bool isEditor = false;
        public static RuntimePlatform platform = RuntimePlatform.WindowsPlayer;
    }
    public static class Debug
    {
        public static bool isDebugBuild = true;
        // 功能：桩保留异常可见性；参数 exception 只来自本控制台测试，不执行游戏日志。
        public static void LogException(Exception exception) { Console.Error.WriteLine(exception.GetType().Name); }
    }
}
namespace Unity.Pipeline.Config
{
    public sealed class RuntimePipelineConfig
    {
        public bool enableInBuilds = true;
        public bool autoStart = true;
        public int port = 7901;
        public static RuntimePipelineConfig Shared = new RuntimePipelineConfig();
        // 功能：返回本测试唯一配置；参数无，不使用 Unity Resources 或磁盘配置。
        public static RuntimePipelineConfig Load() { return Shared; }
    }
}
public static class GateFixture
{
    private const string RuntimeSwitch = "-mono-pipeline-test";
    private const int MinimumHostPort = 7900;
    private const int MaximumHostPort = 7949;
    private const int AdditionalAssemblies = 300;
    private static bool s_Active;
    private static string s_GateReason;
    // 功能：执行从交付源提取的完整门禁方法体；参数无。
    private static void EarlyGate()
"""

FIXTURE_SUFFIX = r"""
    // 功能：设置本次测试边界并执行门禁；参数 args 仅本控制台桩的显式标记，不触碰游戏进程。
    public static int Main(string[] args)
    {
        Unity.Pipeline.Config.RuntimePipelineConfig config = Unity.Pipeline.Config.RuntimePipelineConfig.Shared;
        if (Array.IndexOf(args, "--bad-port") >= 0) config.port = 0;
        if (Array.IndexOf(args, "--disabled") >= 0) config.enableInBuilds = false;
        if (Array.IndexOf(args, "--editor") >= 0) Application.isEditor = true;
        if (Array.IndexOf(args, "--not-debug") >= 0) Debug.isDebugBuild = false;
        if (Array.IndexOf(args, "--extra-assemblies") >= 0)
        {
            for (int index = 0; index < AdditionalAssemblies; index++)
            {
                AssemblyName name = new AssemblyName("GateFixtureAssembly" + index.ToString());
                AppDomain.CurrentDomain.DefineDynamicAssembly(name, AssemblyBuilderAccess.Run);
            }
        }
        EarlyGate();
        Console.Write((s_Active ? "1" : "0") + "|" + (config.enableInBuilds ? "1" : "0")
            + "|" + (config.autoStart ? "1" : "0"));
        return 0;
    }
}
"""


class GateExecutionTests(unittest.TestCase):
    """仅运行自有临时 .NET 桩，验证普通包与显式测试分支。"""

    compiler: Path

    # 功能：定位 Windows 已有框架编译器；参数 cls 为测试类，不下载安装工具。
    @classmethod
    def setUpClass(cls) -> None:
        if os.name != "nt":
            raise unittest.SkipTest("隔离门禁桩需要已有 Windows .NET Framework 编译器")
        windows: str | None = os.environ.get("WINDIR")
        if windows is None:
            raise unittest.SkipTest("未找到 Windows 系统根，未执行编译")
        candidates: list[Path] = []
        for name in ("Framework64", "Framework"):
            candidates.extend(sorted((Path(windows) / "Microsoft.NET" / name).glob("v4*/csc.exe")))
        if not candidates:
            raise unittest.SkipTest("系统没有已安装的框架编译器，未安装或执行游戏工具")
        cls.compiler = candidates[-1]

    # 功能：编译来自真实门禁方法体的自有桩；参数 symbols 为本次纯测试编译分支。
    @contextmanager
    def compiled(self, symbols: str) -> Iterator[Path]:
        root: Path = Path(__file__).resolve().parents[2]
        source: str = (root / "assets/unity/GlobalMonoPipelineTest.cs").read_text(encoding="utf-8-sig")
        body: str = method_body(source, "private static void EarlyGate()")
        with tempfile.TemporaryDirectory(prefix="mono-pipeline-gate-unit-") as temporary:
            directory: Path = Path(temporary)
            fixture: Path = directory / "GateFixture.cs"
            executable: Path = directory / "GateFixture.exe"
            fixture.write_text(FIXTURE_PREFIX + body + FIXTURE_SUFFIX, encoding="utf-8")
            result: subprocess.CompletedProcess[str] = subprocess.run(
                [str(self.compiler), "/nologo", "/target:exe", "/out:" + str(executable),
                 "/define:" + symbols, str(fixture)],
                cwd=directory, capture_output=True, text=True, timeout=COMPILER_TIMEOUT_SECONDS,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(executable.is_file())
            yield executable

    # 功能：只执行本测试创建的控制台文件；参数 executable 来自 compiled，args 是测试标记。
    def execute(self, executable: Path, args: list[str]) -> str:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            [str(executable), *args], cwd=executable.parent, capture_output=True, text=True,
            timeout=FIXTURE_TIMEOUT_SECONDS, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout.strip()

    # 功能：普通包即使烘焙配置已启用且程序集很多仍主动关闭；参数无，不执行 Unity。
    def test_normal_package_closes_with_many_loaded_assemblies(self) -> None:
        with self.compiled("UNITY_STANDALONE_WIN") as executable:
            self.assertEqual(self.execute(executable, ["--extra-assemblies", "-mono-pipeline-test"]), "0|0|0")

    # 功能：开发宏、本次开关及真实运行守卫共同满足才能开启；参数无，运行平台来自桩。
    def test_development_gate_requires_switch_and_runtime_guards(self) -> None:
        with self.compiled(ACTIVE_SYMBOLS) as executable:
            self.assertEqual(self.execute(executable, []), "0|0|0")
            self.assertEqual(self.execute(executable, ["-mono-pipeline-test"]), "1|1|1")
            self.assertEqual(self.execute(executable, ["-mono-pipeline-test", "--editor"]), "0|0|0")
            self.assertEqual(self.execute(executable, ["-mono-pipeline-test", "--not-debug"]), "0|0|0")

    # 功能：已关闭配置或无效端口不能打开服务；参数无，检查关闭顺序不依赖发现成功。
    def test_disabled_configuration_and_invalid_port_remain_closed(self) -> None:
        with self.compiled(ACTIVE_SYMBOLS) as executable:
            self.assertEqual(self.execute(executable, ["-mono-pipeline-test", "--disabled"]), "0|0|0")
            self.assertEqual(self.execute(executable, ["-mono-pipeline-test", "--bad-port"]), "0|0|0")

    # 功能：IL2CPP 编译分支即使显式开关和烘焙配置存在仍关闭；参数无，不运行 IL2CPP 包。
    def test_il2cpp_branch_remains_closed(self) -> None:
        with self.compiled(ACTIVE_SYMBOLS + ",ENABLE_IL2CPP") as executable:
            self.assertEqual(self.execute(executable, ["-mono-pipeline-test", "--extra-assemblies"]), "0|0|0")


if __name__ == "__main__":
    unittest.main()
