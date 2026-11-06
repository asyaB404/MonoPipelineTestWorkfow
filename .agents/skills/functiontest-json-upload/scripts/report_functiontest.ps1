param(
  [Parameter(Mandatory = $true)]
  [string]$JsonPath,

  [string]$Server = "",

  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ([string]::IsNullOrWhiteSpace($Server)) {
  $endpointConfig = Join-Path $PSScriptRoot "upload-endpoint.json"
  if (-not (Test-Path -LiteralPath $endpointConfig -PathType Leaf)) {
    throw "upload endpoint config is missing: $endpointConfig"
  }
  $endpointText = [System.IO.File]::ReadAllText($endpointConfig, [System.Text.Encoding]::UTF8)
  $endpoint = $endpointText | ConvertFrom-Json
  $Server = [string]$endpoint.server
  if ([string]::IsNullOrWhiteSpace($Server)) {
    throw "upload endpoint config has an empty server value: $endpointConfig"
  }
}
$Server = $Server.TrimEnd("/")

# 相对路径优先按“项目根/工作区根”解析：调用方常用
# Doc\AI开发文档\output\... 相对路径，而本脚本可能在 Skill 目录执行，
# 直接按当前目录解析会找不到文件。先尝试当前目录，再尝试往上回溯到
# 包含 Doc\AI开发文档 的项目根，最后回退为当前目录解析并报明确错误。
$resolvedJsonPath = $null
# .NET GetFullPath 不识别正斜杠分隔符，先统一转换为反斜杠。
$JsonPath = $JsonPath -replace "/", "\"
if ([System.IO.Path]::IsPathRooted($JsonPath)) {
  $resolvedJsonPath = [System.IO.Path]::GetFullPath($JsonPath)
}
else {
  # 相对路径按项目根解析：脚本位于 skills\{skill}\scripts\ 下，
  # 向上回溯到包含 Doc\AI开发文档 的目录即项目根；再从项目根拼接 JsonPath。
  $candidateRoot = $null
  $dirPath = $PSScriptRoot
  while (-not [string]::IsNullOrWhiteSpace($dirPath)) {
    $probe = Join-Path $dirPath "Doc\AI开发文档"
    if (Test-Path -LiteralPath $probe -PathType Container) {
      $candidateRoot = $dirPath
      break
    }
    $parent = [System.IO.Path]::GetDirectoryName($dirPath)
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $dirPath) { break }
    $dirPath = $parent
  }
  if ([string]::IsNullOrWhiteSpace($candidateRoot)) { $candidateRoot = (Get-Location).Path }
  $resolvedJsonPath = [System.IO.Path]::GetFullPath((Join-Path $candidateRoot $JsonPath))
}

if (-not (Test-Path -LiteralPath $resolvedJsonPath -PathType Leaf)) {
  throw "upload json not found: $JsonPath"
}
$runDirectory = [System.IO.Directory]::GetParent($resolvedJsonPath)
$featureDirectory = $runDirectory.Parent
if ($null -eq $runDirectory -or $null -eq $featureDirectory -or $featureDirectory.Name -eq "output" -or $featureDirectory.Parent.Name -ne "output") {
  throw "upload json must be under Doc\AI开发文档\output\{feature_id}\{run_dir}: $resolvedJsonPath"
}
if (-not $runDirectory.Name.StartsWith($featureDirectory.Name + "-") -or $resolvedJsonPath -ne [System.IO.Path]::Combine($runDirectory.FullName, $runDirectory.Name + "-functiontest-upload.json")) {
  throw "upload json path must match output\{feature_id}\{feature_id}-{seq4}\{run_dir}-functiontest-upload.json: $resolvedJsonPath"
}

$data = Get-Content -LiteralPath $resolvedJsonPath -Encoding UTF8 -Raw | ConvertFrom-Json

if (-not $data.tool_stats_payload) {
  throw "missing field: tool_stats_payload"
}
if (-not $data.user_stats_payload) {
  throw "missing field: user_stats_payload"
}

$allowedTopLevel = @("tool_stats_payload", "user_stats_payload")
$actualTopLevel = @($data.PSObject.Properties.Name)
$unexpectedTopLevel = @($actualTopLevel | Where-Object { $_ -notin $allowedTopLevel })
$missingTopLevel = @($allowedTopLevel | Where-Object { $_ -notin $actualTopLevel })
if ($unexpectedTopLevel.Count -gt 0 -or $missingTopLevel.Count -gt 0) {
  throw "invalid upload JSON top-level fields; unexpected=$($unexpectedTopLevel -join ','); missing=$($missingTopLevel -join ',')"
}

$metricItems = @($data.user_stats_payload.items | Where-Object { $null -ne $_.custom_metrics })
if ($metricItems.Count -gt 0) {
  $metrics = $metricItems[0].custom_metrics
  $totalCaseCount = 0
  $blockedCaseCount = 0
  $inconclusiveCaseCount = 0
  [void][int]::TryParse([string]$metrics.total_case_count, [ref]$totalCaseCount)
  [void][int]::TryParse([string]$metrics.block_case_count, [ref]$blockedCaseCount)
  [void][int]::TryParse([string]$metrics.invalid_case_count, [ref]$inconclusiveCaseCount)
  if ($totalCaseCount -gt 0 -and ($blockedCaseCount -eq $totalCaseCount -or $inconclusiveCaseCount -eq $totalCaseCount)) {
    $skipReason = if ($blockedCaseCount -eq $totalCaseCount) { "blocked" } else { "test_inconclusive" }
    throw "upload skipped: all FunctionTest cases are $skipReason; no request was sent; local report and JSON were retained"
  }
}

foreach ($item in @($data.user_stats_payload.items)) {
  if (-not $item.custom_metrics) {
    continue
  }
  foreach ($field in @("tester_account", "project_group")) {
    $value = [string]$item.custom_metrics.$field
    if ([string]::IsNullOrWhiteSpace($value) -or $value -eq "未填写" -or $value -eq "未输入" -or $value.StartsWith("TODO")) {
      $item.custom_metrics.$field = "无"
    }
  }
}

$toolJson = $data.tool_stats_payload | ConvertTo-Json -Depth 20 -Compress
$userJson = $data.user_stats_payload | ConvertTo-Json -Depth 20 -Compress

if ($DryRun) {
  Write-Output "TOOL_STATS_PAYLOAD="
  Write-Output $toolJson
  Write-Output "USER_STATS_PAYLOAD="
  Write-Output $userJson
  exit 0
}

$toolResult = Invoke-RestMethod `
  -Method Post `
  -Uri ($Server + "/api/v1/tool-stats/report") `
  -ContentType "application/json; charset=utf-8" `
  -Body $toolJson

$userResult = Invoke-RestMethod `
  -Method Post `
  -Uri ($Server + "/api/v1/tool-user-stats/report") `
  -ContentType "application/json; charset=utf-8" `
  -Body $userJson

[ordered]@{
  tool_stats = $toolResult
  user_stats = $userResult
} | ConvertTo-Json -Depth 20 -Compress | Write-Output
