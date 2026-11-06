<#
.SYNOPSIS
    Locate the Unity Editor opened for a specific project, bring it to the foreground,
    and verify that it is the active window before an MCP compile call.

.DESCRIPTION
    This helper does not start Unity and does not invoke any MCP tool. It only performs
    the Windows window-activation step that execute_compile requires in this setup.
    A project path is mandatory for automatic process matching so a different Unity
    project is never focused by accident.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = (Get-Location).Path,

    [Parameter(Mandatory = $false)]
    [int]$TimeoutSeconds = 10,

    [Parameter(Mandatory = $false)]
    [int]$UnityProcessId = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Normalize-PathText {
    param([AllowNull()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }
    $normalized = $Value.Trim().Trim('"').Replace('/', '\')
    return $normalized.TrimEnd('\').ToLowerInvariant()
}

try {
    $resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path
} catch {
    Write-Output ("PROJECT_ROOT_INVALID|project={0}" -f $ProjectRoot)
    Write-Error ("Cannot resolve project root: {0}" -f $ProjectRoot) -ErrorAction Continue
    exit 1
}

$rootText = Normalize-PathText $resolvedRoot
if ($TimeoutSeconds -lt 1) {
    $TimeoutSeconds = 1
}

function Test-UnityProjectProcess {
    param(
        [Parameter(Mandatory = $true)]$ProcessInfo,
        [Parameter(Mandatory = $true)][string]$ExpectedRoot
    )

    $commandLine = Normalize-PathText ([string]$ProcessInfo.CommandLine)
    if ([string]::IsNullOrWhiteSpace($commandLine)) {
        return $false
    }

    # Prefer the explicit Unity -projectPath argument when present.
    $match = [regex]::Match($commandLine, '(?i)-projectpath(?:=|\s+)(?:"([^"]+)"|([^\s]+))')
    if ($match.Success) {
        $argument = if ($match.Groups[1].Success) { $match.Groups[1].Value } else { $match.Groups[2].Value }
        return ((Normalize-PathText $argument) -eq $ExpectedRoot)
    }

    # Older launchers may omit -projectPath from the visible command line.
    return $commandLine.Contains($ExpectedRoot)
}

if (-not ('UnityWindowFocus.NativeMethods' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace UnityWindowFocus {
    public static class NativeMethods {
        [DllImport("user32.dll")]
        public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        public static extern bool BringWindowToTop(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

        [DllImport("kernel32.dll")]
        public static extern uint GetCurrentThreadId();

        [DllImport("user32.dll")]
        public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

        [DllImport("user32.dll")]
        public static extern IntPtr SetActiveWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern void SwitchToThisWindow(IntPtr hWnd, bool fAltTab);

        public static bool ForceForegroundWindow(IntPtr hWnd) {
            IntPtr foreground = GetForegroundWindow();
            uint foregroundThread = 0;
            if (foreground != IntPtr.Zero) {
                GetWindowThreadProcessId(foreground, out foregroundThread);
            }
            uint currentThread = GetCurrentThreadId();
            bool attached = foregroundThread != 0 && foregroundThread != currentThread &&
                            AttachThreadInput(foregroundThread, currentThread, true);
            try {
                ShowWindowAsync(hWnd, 9);
                BringWindowToTop(hWnd);
                SetActiveWindow(hWnd);
                SwitchToThisWindow(hWnd, true);
                return SetForegroundWindow(hWnd);
            } finally {
                if (attached) {
                    AttachThreadInput(foregroundThread, currentThread, false);
                }
            }
        }
    }
}
'@
}

$candidate = $null
if ($UnityProcessId -gt 0) {
    $candidate = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $UnityProcessId) -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ieq 'Unity.exe' -and (Test-UnityProjectProcess $_ $rootText) } |
        Select-Object -First 1
} else {
    $candidate = Get-CimInstance Win32_Process -Filter "Name = 'Unity.exe'" -ErrorAction SilentlyContinue |
        Where-Object { Test-UnityProjectProcess $_ $rootText } |
        Sort-Object ProcessId -Descending |
        Select-Object -First 1
}

if ($null -eq $candidate) {
    Write-Output ("UNITY_NOT_FOUND|project={0}" -f $resolvedRoot)
    Write-Error ("Unity.exe for project was not found: {0}. Confirm Unity is open or pass -UnityProcessId." -f $resolvedRoot) -ErrorAction Continue
    exit 2
}

$unityPid = [int]$candidate.ProcessId
$editorProcess = $null
$windowHandle = [IntPtr]::Zero
$windowDeadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $windowDeadline) {
    try {
        $editorProcess = [Diagnostics.Process]::GetProcessById($unityPid)
        $editorProcess.Refresh()
        $windowHandle = $editorProcess.MainWindowHandle
    } catch {
        $windowHandle = [IntPtr]::Zero
    }
    if ($windowHandle -ne [IntPtr]::Zero) {
        break
    }
    Start-Sleep -Milliseconds 100
}

if ($windowHandle -eq [IntPtr]::Zero) {
    Write-Output ("UNITY_FOUND_NO_WINDOW|pid={0}|project={1}" -f $unityPid, $resolvedRoot)
    Write-Error ("Unity process found but no focusable main window: pid={0}, project={1}. Caller may use the compile fallback because the Unity process was found." -f $unityPid, $resolvedRoot) -ErrorAction Continue
    exit 3
}

$shell = $null
try {
    $shell = New-Object -ComObject WScript.Shell
} catch {
    # Win32 activation remains the primary path; verification below decides success.
}

# Use both Win32 activation and AppActivate for Unity versions that handle one path better.
[UnityWindowFocus.NativeMethods]::ForceForegroundWindow($windowHandle) | Out-Null
try {
    if ($null -ne $shell) {
        $shell.AppActivate($unityPid) | Out-Null
    }
} catch {
    # Win32 activation above remains the primary path; verification below decides success.
}

$focusDeadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $focusDeadline) {
    $foregroundWindow = [UnityWindowFocus.NativeMethods]::GetForegroundWindow()
    [uint32]$foregroundPid = 0
    if ($foregroundWindow -ne [IntPtr]::Zero) {
        [UnityWindowFocus.NativeMethods]::GetWindowThreadProcessId($foregroundWindow, [ref]$foregroundPid) | Out-Null
    }
    if ([int]$foregroundPid -eq $unityPid) {
        Write-Output ("UNITY_FOCUSED|pid={0}|project={1}" -f $unityPid, $resolvedRoot)
        exit 0
    }
    [UnityWindowFocus.NativeMethods]::ForceForegroundWindow($windowHandle) | Out-Null
    try {
        if ($null -ne $shell) {
            $shell.AppActivate($unityPid) | Out-Null
        }
    } catch {
        # Continue with the Win32 retry path.
    }
    Start-Sleep -Milliseconds 100
}

$foregroundWindow = [UnityWindowFocus.NativeMethods]::GetForegroundWindow()
[uint32]$foregroundPid = 0
if ($foregroundWindow -ne [IntPtr]::Zero) {
    [UnityWindowFocus.NativeMethods]::GetWindowThreadProcessId($foregroundWindow, [ref]$foregroundPid) | Out-Null
}
$foregroundName = 'unknown'
try {
    $foregroundName = (Get-Process -Id ([int]$foregroundPid) -ErrorAction Stop).ProcessName
} catch {
}
Write-Output ("UNITY_FOUND_FOCUS_FAILED|target_pid={0}|foreground_pid={1}|foreground_process={2}|project={3}" -f $unityPid, $foregroundPid, $foregroundName, $resolvedRoot)
Write-Error ("Unity window could not be focused: target_pid={0}, foreground_pid={1}, foreground_process={2}, project={3}. Caller may use the compile fallback because the Unity process was found." -f $unityPid, $foregroundPid, $foregroundName, $resolvedRoot) -ErrorAction Continue
exit 4
