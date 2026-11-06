#!/usr/bin/env python3
"""Create the package-local UTF-8 BOM PowerShell upload wrapper.

Run this from the directory that contains exactly one current
``*-functiontest-upload.json``.  The generated wrapper uses only its own
directory and walks upward to locate the packaged uploader; no machine path,
console encoding, or environment variable is required.
"""

from __future__ import annotations

import argparse
from pathlib import Path


WRAPPER_NAME = "functiontest-upload-wrapper.ps1"


def select_upload_json(run_dir: Path) -> Path:
    candidates = sorted(run_dir.glob("*-functiontest-upload.json"))
    if len(candidates) != 1:
        raise ValueError(
            "current run directory must contain exactly one *-functiontest-upload.json; "
            f"found={len(candidates)}"
        )
    return candidates[0]


def wrapper_content(upload_name: str) -> str:
    safe_name = upload_name.replace("'", "''")
    return f'''$ErrorActionPreference = "Stop"
$runDir = $PSScriptRoot
$uploadJson = Join-Path $runDir '{safe_name}'
if (-not (Test-Path -LiteralPath $uploadJson -PathType Leaf)) {{
  throw "upload json not found beside wrapper: $uploadJson"
}}

$cursor = $runDir
$uploader = $null
while (-not [string]::IsNullOrWhiteSpace($cursor)) {{
  $candidate = Join-Path $cursor '.agents\\skills\\functiontest-json-upload\\scripts\\report_functiontest.ps1'
  if (Test-Path -LiteralPath $candidate -PathType Leaf) {{
    $uploader = $candidate
    break
  }}
  $parent = [System.IO.Directory]::GetParent($cursor)
  if ($null -eq $parent) {{ break }}
  $cursor = $parent.FullName
}}
if ([string]::IsNullOrWhiteSpace($uploader)) {{
  throw "package uploader script was not found above $runDir"
}}

& $uploader -JsonPath $uploadJson
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a BOM-safe FunctionTest upload wrapper in the current run directory.")
    parser.add_argument("--run-dir", default=".", help="Current run directory; default is the working directory.")
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"[ERROR] run directory not found: {run_dir}")
    upload_json = select_upload_json(run_dir)
    wrapper = run_dir / WRAPPER_NAME
    wrapper.write_text(wrapper_content(upload_json.name), encoding="utf-8-sig", newline="\r\n")
    print(WRAPPER_NAME)


if __name__ == "__main__":
    main()
